"""Observed-output a posteriori mathematical discrepancy, not native certification."""
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
import time
from sludge_sandbox.water_interval_eos import Interval,I


def need(ok,reason):
    if not ok:raise ValueError(reason)

def maxabs(i):return max(i.lo.copy_abs(),i.hi.copy_abs())

def analyze(query,box,*,pressure,binding,maximum_boxes=256,maximum_wall_seconds=15.,clock=time.monotonic):
    """Generic callback enclosure assumption; real runner supplies pinned EOS.

    Fixed query tuple: T,P,rho_mass,M_public,M_native,Nl,V_host,declared_v_error.
    All query entries exact finite positive binary64; original error cannot change.
    """
    need(type(query) is tuple and len(query)==8 and all(type(v) is float and v>0 and v<float('inf') for v in query),'positive_binary64_query')
    need(type(box) is Interval and type(box.lo) is D and type(box.hi) is D and 0<box.lo<box.hi,'positive_density_box')
    need(type(maximum_boxes) is int and maximum_boxes>=4 and type(maximum_wall_seconds) is float and 0<maximum_wall_seconds<float('inf'),'explicit_budgets')
    def snap():
        v=binding();need(type(v) is tuple and v and all(type(x) is str and x for x in v),'immutable_binding');return v
    begun=clock();before=snap();records=[];leaves=[];pending=[box];attempted=completed=0;out={}
    def guard():
        need(snap()==before,'source_changed');need(clock()-begun<=maximum_wall_seconds,'wall_budget')
    def evaluate(r,role):
        nonlocal attempted,completed
        guard();need(attempted<maximum_boxes,'box_budget');attempted+=1
        record={'role':role,'density':r,'status':'started'};records.append(record)
        p,d=pressure(I(query[0]),r);completed+=1
        need(type(p) is Interval and type(d) is Interval,'typed_eos_enclosure');p.__post_init__();d.__post_init__()
        record.update(pressure=p,derivative=d,status='complete');guard();return p,d
    try:
        with localcontext() as ctx:
            ctx.prec=60
            t,p,rhom,mp,mn,nl,vhost,decl=query
            rn=I(rhom)/I(mn);scale=I(mp)/I(mn)
            need(box.lo<=rn.lo<=rn.hi<=box.hi,'native_density_inside_box')
            out.update(native_density=rn,volume_scale=scale)
            pl,_=evaluate(I(box.lo),'lower_face');ph,_=evaluate(I(box.hi),'upper_face')
            out.update(lower_residual=pl-I(p),upper_residual=ph-I(p))
            need((pl-I(p)).hi<0<(ph-I(p)).lo,'strict_root_faces')
            nativep,_=evaluate(rn,'observed_native_point');res=nativep-I(p);out['observed_residual']=res
            while pending:
                r=pending[0];_,der=evaluate(r,'monotone_leaf_or_split')
                if der.lo>0:leaves.append((r,der));pending.pop(0);continue
                need(der.hi>0,'nonpositive_derivative')
                # Exact Decimal average at deliberately sufficient precision.
                with localcontext() as c:
                    c.prec=max(len(r.lo.as_tuple().digits),len(r.hi.as_tuple().digits))+abs(r.lo.as_tuple().exponent-r.hi.as_tuple().exponent)+abs(r.lo.adjusted()-r.hi.adjusted())+20
                    mid=(r.lo+r.hi)/2
                need(F(mid)==(F(r.lo)+F(r.hi))/2 and r.lo<mid<r.hi,'exact_midpoint')
                pending.pop(0);pending.extend((Interval(r.lo,mid),Interval(mid,r.hi)))
            leaves.sort(key=lambda x:x[0].lo)
            need(leaves[0][0].lo==box.lo and leaves[-1][0].hi==box.hi and all(a[0].hi==b[0].lo for a,b in zip(leaves,leaves[1:])),'exact_coverage')
            slope=min(d.lo for r,d in leaves);density_error=(I(maxabs(res))/I(slope)).hi
            # Root and native density both in original positive box; reciprocal Lipschitz.
            verror=(scale*I(density_error)/(I(box.lo)*rn)).hi
            # Exact native output public volume and literal host n*M/rho rounding.
            exact_native_volume=F(mp)/F(rhom)
            expected_host=(nl*mp)/rhom
            need(expected_host==vhost,'saved_host_volume_rounding_mismatch')
            host_roundoff=F(vhost)-F(nl)*exact_native_volume
            host_permol=(I(D(host_roundoff.numerator))/I(D(host_roundoff.denominator))/I(nl))
            combined=(I(verror)+I(maxabs(host_permol))).hi
            out.update(minimum_slope=slope,density_error_bound=density_error,native_volume_error_bound=verror,host_volume_roundoff_exact=str(host_roundoff),host_per_mol_roundoff=host_permol,combined_volume_error_bound=combined,original_declaration=I(decl))
            need(combined<=D(decl),'original_volume_declaration_exceeded');guard()
        status='passed_observed_query';reason=None
    except Exception as exc:status='failed';reason=type(exc).__name__+': '+str(exc)
    after=snap();elapsed=clock()-begun
    if after!=before or elapsed>maximum_wall_seconds:status='failed';reason='final_source_or_wall'
    return dict(status=status,reason=reason,query=query,density_box=box,metrics=out,visits=tuple(records),accepted_leaves=tuple(leaves),pending=tuple(pending),attempted=attempted,completed=completed,maximum_boxes=maximum_boxes,maximum_wall_seconds=maximum_wall_seconds,elapsed_seconds=elapsed,source_before=before,source_after=after,qualification='conditional_generic_pressure_enclosure_observed_query_only_no_U_phase_or_material_admission')
