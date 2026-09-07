"""Read-only, independently encoded B2-AUDIT-1 inventory/derived-data audit.

Does not import solver, temperature, diagnostics, screening or verification.
This is NOT full ODE replay and cannot detect arbitrary coordinated rewriting.
"""
import csv
import json
import math
from pathlib import Path
import sys
from model import ROOT, Scenario, strict_json
from paths import safe_directory, safe_file, relative

TOL=1e-6


class AuditMismatch(ValueError):
    """Only internally computed, finite comparison data may reach the report."""
    def __init__(self,label,observed,expected,scale,error):
        super().__init__('audit_'+label)
        self.details = dict(check=label,observed=observed,expected=expected,
                            normalization_scale=max(1,abs(scale)),scaled_error=error)


def read_json(p):
    return strict_json(p.read_text(encoding='utf-8'),size_limit=20*1024*1024,depth_limit=32)


def read_csv(p,fields):
    with p.open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=fields.split(): raise ValueError('csv_fields')
        rows=[]
        for r in reader:
            if None in r: raise ValueError('csv_extra')
            for k,v in r.items():
                if k=='scenario_id': continue
                if v=='': r[k]=None; continue
                r[k]=float(v)
                if not math.isfinite(r[k]): raise ValueError('nonfinite')
            rows.append(r)
    return rows


def coefficients(d,t):
    knots=d['temperature']['knots']
    a,b=next((a,b) for a,b in zip(knots,knots[1:]) if a['tau']<=t<=b['tau'])
    T=a['T_K']+(b['T_K']-a['T_K'])*(t-a['tau'])/(b['tau']-a['tau'])
    k=d['reaction']['K_ref']*math.exp(d['reaction']['theta']*(1-600/T))
    diff=d['transport']['d_ref']*(T/600)**d['transport']['m']; ell=d['geometry']['length_ratio']
    ad=diff/ell**2; b=d['transport']['Bi_ref']/ell; n=d['numerics']['n_cells']
    g=0 if b==0 else 1/(1/b+1/(2*n*ad))
    return T,k,diff,ad,b,g


def threshold(times,values,q,upper):
    if values[0]<=q: return {'tau':times[0],'bracket_tau':[times[0],times[0]],'status':'initially_reached'}
    for i in range(1,len(times)):
        if values[i]<=q:
            t=times[i-1]+(times[i]-times[i-1])*(values[i-1]-q)/(values[i-1]-values[i])
            return {'tau':t,'bracket_tau':[times[i-1],times[i]],'status':'reached_diagnostic_threshold'}
    return {'tau':None,'bracket_tau':None,'status':'excluded_by_oxygen_budget' if upper is not None and upper<1-q else 'not_reached_by_horizon'}


def audit_exports(run_directory):
    checks=0; maxima={}; per_case={}; context={}
    def close(a,b,scale=1.,label='derived'):
        nonlocal checks
        checks+=1
        if a is None or b is None:
            if a is not b: raise ValueError('null_mismatch')
            return
        if not math.isfinite(a) or not math.isfinite(b): raise ValueError('nonfinite')
        err=abs(a-b)/max(1,abs(scale))
        if not math.isfinite(err): raise ValueError('nonfinite_difference')
        maxima[label]=max(maxima.get(label,0),err)
        if err>TOL: raise AuditMismatch(label,a,b,scale,err)
    try:
        out=safe_directory(run_directory)
        def local(name): return safe_file(relative(out/name))
        index=read_json(local('raw_index.json'))
        if index['kind']!='raw_inventory_exports' or len(index['cases'])>40: raise ValueError('raw_index')
        ts=read_csv(local('timeseries.csv'),'scenario_id tau T_K K_tau d_tau a_D b g H S_D S_B Da_O2 u_core u_surface f_mean f_max co2_body co2_generated co2_net_out u_res v_res source_rate')
        pr=read_csv(local('profiles.csv'),'scenario_id tau cell_index xi_left xi_right u v f')
        fl=read_csv(local('flux_intervals.csv'),'scenario_id tau_left tau_right integral_J_u integral_J_v integral_q_body')
        ids=[x['scenario_id'] for x in index['cases']]
        if len(ids)!=len(set(ids)) or not ids: raise ValueError('duplicate_case')
        if any(r['scenario_id'] not in ids for r in ts+pr+fl): raise ValueError('unexpected_case')
        summary=read_json(local('summary.json')) if (out/'summary.json').exists() else None
        summaries={d['scenario_id']:d for d in summary['scenarios']} if summary else {}
        for case in index['cases']:
            sid=case['scenario_id']; d=read_json(local(case['input_file'])); Scenario.from_dict(d)
            if d['scenario_id']!=sid: raise ValueError('input_identity')
            context={'scenario_id':sid}
            n=d['numerics']['n_cells']; gamma=d['reaction']['Gamma']; rho=d['boundary']['reservoir_ratio']; mode=d['boundary']['mode']
            rows=[r for r in ts if r['scenario_id']==sid]; cells=[r for r in pr if r['scenario_id']==sid]; intervals=[r for r in fl if r['scenario_id']==sid]
            end=d['numerics']['tau_end']; times=[0.]+[min(.1*i,end) for i in range(1,math.ceil(end/.1)+1)]
            if len(rows)!=len(times) or len(cells)!=n*len(times) or len(intervals)!=len(times)-1: raise ValueError('coverage_count')
            grouped={}
            for p in cells:
                key=(p['tau'],p['cell_index'])
                if key in grouped: raise ValueError('duplicate_profile')
                grouped[key]=p
            netu=netv=generated=0.; means=[]; locals_=[]; actual_rows=[]
            u0=0 if case['test_only_dirichlet'] else 1; v0=1-u0
            C0=gamma+v0; O0=1.; M0=12*gamma+32*u0+44*v0
            upper=None if mode=='infinite' else min(1,(1+(rho or 0))/gamma)
            for j,(t,r) in enumerate(zip(times,rows)):
                context['tau']=t
                close(r['tau'],t,label='sample_time')
                if j:
                    f=intervals[j-1]; close(f['tau_left'],times[j-1]); close(f['tau_right'],t)
                    if f['integral_q_body']<0: raise ValueError('negative_generation')
                    netu+=f['integral_J_u']; netv+=f['integral_J_v']; generated+=f['integral_q_body']
                prof=[grouped[(r['tau'],i)] for i in range(n)]
                for i,p in enumerate(prof):
                    close(p['xi_left'],i/n); close(p['xi_right'],(i+1)/n)
                    for k in ('u','v','f'):
                        if p[k] is None or p[k]<0: raise ValueError('negative_inventory')
                    if p['f']>1: raise ValueError('carbon_increase')
                    if d['reaction']['K_ref']==0 and not case['test_only_dirichlet']:
                        if max(abs(p['u']-1),abs(p['v']),abs(p['f']-1))>1e-10: raise ValueError('no_reaction_uniform')
                    close(p['u']+p['v'],1,label='local_equimolar')
                    if j==0:
                        close(p['u'],u0,label='initial'); close(p['v'],v0,label='initial'); close(p['f'],1,label='initial')
                u=sum(p['u'] for p in prof)/n; v=sum(p['v'] for p in prof)/n; f=sum(p['f'] for p in prof)/n; fmax=max(p['f'] for p in prof)
                means.append(f); locals_.append(fmax)
                close(gamma*f+v+netv,C0,C0,'carbon_inventory')
                close(u+v+netu+netv,O0,O0,'oxygen_inventory')
                close(12*gamma*f+32*u+44*v+32*netu+44*netv,M0,M0,'nominal_mass')
                close(gamma*(1-f),generated,gamma,'reaction_extent')
                close(u+netu+generated,u0,1,'oxygen_reaction')
                close(v+netv-generated,v0,1,'carbon_dioxide_reaction')
                ur,vr=r['u_res'],r['v_res']
                if mode=='finite':
                    if ur is None or vr is None or ur<0 or vr<0: raise ValueError('reservoir_inventory')
                    close(ur+vr,1,label='reservoir_equimolar'); close(rho*(ur-1),netu,label='reservoir_exchange'); close(rho*vr,netv,label='reservoir_exchange')
                    close(gamma*f+v+rho*vr,gamma,gamma,'finite_carbon')
                    close(u+v+rho*(ur+vr),1+rho,1+rho,'finite_oxygen')
                elif ur is not None or vr is not None: raise ValueError('nonfinite_null')
                if upper is not None and 1-f>upper+TOL: raise ValueError('oxygen_budget')
                T,K,diff,ad,b,g=coefficients(d,t)
                surface=prof[-1]['u'] if b==0 else (ur if ur is not None else 1)+g*(prof[-1]['u']-(ur if ur is not None else 1))/b
                if case['test_only_dirichlet']: g=2*ad*n; surface=1.
                expected=dict(T_K=T,K_tau=K,d_tau=diff,a_D=ad,b=b,g=g,Da_O2=gamma*K/ad,u_core=prof[0]['u'],u_surface=surface,
                              f_mean=f,f_max=fmax,co2_body=v,co2_generated=generated,co2_net_out=netv,
                              source_rate=sum(gamma*K*p['f']*p['u'] for p in prof)/n)
                for k,vv in expected.items(): close(r[k],vv,max(1,abs(vv)),k)
                from reference.oracle import exposure, diffusion_time
                H,_=exposure(d['temperature']['knots'],t,d['reaction']['K_ref'],d['reaction']['theta'])
                SD=diffusion_time(d['temperature']['knots'],t,d['transport']['d_ref'],d['transport']['m'],d['geometry']['length_ratio'])
                close(r['H'],H,max(1,H),'reaction_exposure')
                close(r['S_D'],SD,max(1,SD),'diffusion_exposure')
                close(r['S_B'],b*t,max(1,b*t),'film_exposure')
                if min(p['f'] for p in prof)<math.exp(-H)-TOL: raise ValueError('ideal_oxygen_lower_bound')
                if mode=='sealed': close(netu,0,label='sealed_flux'); close(netv,0,label='sealed_flux')
                actual_rows.append(expected)
            if sid in summaries:
                sm=summaries[sid]
                if sm['input']!=d: raise ValueError('summary_input')
                if sm['material_mapping']!='unknown_real_material' or sm['physical_time_seconds'] is not None or sm['physical_time_status']!='uncalibrated': raise ValueError('scientific_scope')
                required={'energy','pressure','pore_closure','thermal_expansion_flow','equation_of_state','shrinkage','strength','emissions','t_close','t_escape'}
                if set(sm['not_modelled'])!=required or any(x!={'status':'not_modelled','value':None} for x in sm['not_modelled'].values()): raise ValueError('fake_model_claim')
                for name,values in (('mean',means),('local',locals_)):
                    for percent,q in ((95,.05),(99,.01)):
                        expected=threshold(times,values,q,upper); got=sm['events'][name+str(percent)]
                        if got['status']!=expected['status'] or got['bracket_tau']!=expected['bracket_tau']: raise ValueError('event_semantics')
                        close(got['tau'],expected['tau'],label='event_time')
                for k,vv in actual_rows[-1].items(): close(sm['at_end'][k],vv,max(1,abs(vv)),k)
                rates=[r['source_rate'] for r in rows]; peak=max(rates); peak_tau=times[rates.index(peak)] if peak else None
                close(sm['tau_source_peak'],peak_tau,label='sampled_peak')
                close(sm['conversion_upper_bound'],upper,label='budget_bound')
                if sm['verification_scope'] not in ('frozen_suite','audit_only') or sm['numerical_validation'] not in ('passed_frozen_suite','not_verified_for_custom_case','failed','not_run'): raise ValueError('validation_enum')
                if sm['verification_scope']=='audit_only' and sm['numerical_validation']!='not_verified_for_custom_case': raise ValueError('custom_validation')
            per_case[sid]={'result':'passed','samples':len(times),'profiles':n*len(times)}
        return {'passed':True,'policy':'B2-AUDIT-1','fixed_tolerance':TOL,'checks':checks,'max_scaled_errors':maxima,'per_case':per_case,
                'limitation':'Inventory/derived consistency only; not full ODE replay or arbitrary coordinated-tamper detection'}
    except AuditMismatch as exc:
        return {'passed':False,'policy':'B2-AUDIT-1','fixed_tolerance':TOL,'checks':checks,
                'reason':'export_audit_rejected','per_case':per_case,'max_scaled_errors':maxima,
                'failure':{**context,**exc.details}}
    except (ValueError,KeyError,TypeError,IndexError,OSError,StopIteration,OverflowError):
        return {'passed':False,'policy':'B2-AUDIT-1','fixed_tolerance':TOL,'checks':checks,'reason':'export_audit_rejected','per_case':per_case}


if __name__=='__main__':
    if len(sys.argv)!=2:
        print(json.dumps({'passed':False,'reason':'audit_arguments'})); sys.exit(2)
    result=audit_exports(sys.argv[1]); print(json.dumps(result,allow_nan=False)); sys.exit(0 if result['passed'] else 1)
