"""Research parametric coexistence enclosures; no native or phase admission."""
from dataclasses import dataclass
from decimal import Decimal as D, localcontext
from fractions import Fraction
from pathlib import Path
import hashlib,json
from sludge_sandbox.water_interval_eos import Interval, I, Jet, residual


def require(ok, reason):
    if not ok: raise ValueError(reason)


def interval(x):
    require(type(x) is Interval and type(x.lo) is D and type(x.hi) is D,'typed_decimal_interval')
    x.__post_init__()
    return x


@dataclass(frozen=True)
class ResidualBox:
    temperature: Interval
    log_density: tuple
    density: tuple
    residual: tuple
    jacobian: tuple
    stability: tuple
    pressure: tuple


def evaluate_box(temperature, box, *, reducing_density, reducing_temperature, gas_constant, jet):
    """jet(delta,tau) must enclose alphar and its first two delta derivatives.

    Public mathematical helper: arbitrary supplied callbacks are NOT EOS proof.
    The pinned-source entrypoint below supplies the actual reviewed residual.
    """
    interval(temperature)
    require(type(box) is tuple and len(box)==2,'two_log_density_intervals')
    for x in box: interval(x)
    rc,tc,rg=map(I,(reducing_density,reducing_temperature,gas_constant))
    require(rc.lo>0 and tc.lo>0 and rg.lo>0 and 0<temperature.lo<=temperature.hi<tc.lo,'positive_subcritical_domain')
    rho=tuple(x.exp() for x in box)
    require(rho[0].lo>rc.hi and rc.lo>rho[1].hi and rho[1].lo>0,'strict_separated_phases_away_from_critical')
    tau=tc/temperature; ars=[];q=[];stability=[]
    for r in rho:
        delta=r/rc; ar=jet(delta,tau)
        require(type(ar) is Jet,'typed_residual_jet')
        for v in (ar.value,ar.first,ar.second):interval(v)
        ars.append(ar);q.append(delta*ar.first)
        stability.append(1+2*delta*ar.first+delta*delta*ar.second)
    f=(rho[0]*(1+q[0])-rho[1]*(1+q[1]),box[0]-box[1]+ars[0].value-ars[1].value+q[0]-q[1])
    jac=((rho[0]*stability[0],-rho[1]*stability[1]),(stability[0],-stability[1]))
    pressure=tuple(r*rg*temperature*(1+z) for r,z in zip(rho,q))
    return ResidualBox(temperature,box,rho,f,jac,tuple(stability),pressure)


@dataclass(frozen=True)
class KrawczykEvidence:
    box: tuple
    center: tuple
    preconditioner: tuple
    center_residual: tuple
    jacobian: tuple
    image: tuple
    contraction_upper: D
    strict_margins: tuple
    proved: bool
    reason: str
    weights: tuple | None = None
    unweighted_contraction_upper: D | None = None
    norm_name: str = 'unweighted_infinity'


def krawczyk(box, center, matrix, center_residual, jacobian, *, weights=None):
    """Given sound whole-box J and parameter-wide F(center), test K subset int X.

    Also require infinity-norm ||I-CJ||<1, a sufficient uniqueness condition.
    Caller-supplied algebra alone is not a function/Jacobian authenticity proof.
    """
    require(type(box) is tuple and len(box)==2 and type(center) is tuple and len(center)==2,'two_coordinates')
    for x,c in zip(box,center):
        interval(x);require(type(c) is D and c.is_finite() and x.lo<c<x.hi,'strict_point_center')
    require(type(matrix) is tuple and len(matrix)==2 and all(type(row) is tuple and len(row)==2 for row in matrix),'two_by_two_preconditioner')
    require(all(type(v) is D and v.is_finite() for row in matrix for v in row),'finite_point_preconditioner')
    require(Fraction(matrix[0][0])*Fraction(matrix[1][1])!=Fraction(matrix[0][1])*Fraction(matrix[1][0]),'nonsingular_preconditioner')
    require(type(center_residual) is tuple and len(center_residual)==2 and type(jacobian) is tuple and len(jacobian)==2 and all(type(row) is tuple and len(row)==2 for row in jacobian),'complete_residual_jacobian')
    for x in (*center_residual,*jacobian[0],*jacobian[1]):interval(x)
    require(weights is None or (type(weights) is tuple and len(weights)==2 and all(type(w) is D and w.is_finite() and w>0 for w in weights)),'explicit_positive_decimal_weights')
    defect=tuple(tuple(I(int(i==j))-sum((I(matrix[i][k])*jacobian[k][j] for k in range(2)),I(0)) for j in range(2)) for i in range(2))
    image=tuple(I(center[i])-sum((I(matrix[i][j])*center_residual[j] for j in range(2)),I(0))+sum((defect[i][j]*(box[j]-I(center[j])) for j in range(2)),I(0)) for i in range(2))
    norm=max(sum((I(max(v.lo.copy_abs(),v.hi.copy_abs())) for v in row),I(0)).hi for row in defect)
    unweighted=norm
    if weights is not None:
        norm=max(sum((I(max(v.lo.copy_abs(),v.hi.copy_abs()))*I(weights[j])/I(weights[i]) for j,v in enumerate(row)),I(0)).hi for i,row in enumerate(defect))
    margins=tuple(((image[i]-I(box[i].lo)).lo,(I(box[i].hi)-image[i]).lo) for i in range(2))
    proved=all(a>0 and b>0 for a,b in margins) and norm<1
    return KrawczykEvidence(box,center,matrix,center_residual,jacobian,image,norm,margins,proved,'strict_inclusion_and_contraction' if proved else 'unresolved_inclusion_or_contraction',weights,unweighted,'weighted_infinity' if weights is not None else 'unweighted_infinity')


@dataclass(frozen=True)
class CoexistenceAttempt:
    source_sha256: str
    precision: int
    domain: ResidualBox
    center: ResidualBox
    krawczyk: KrawczykEvidence
    pressure: Interval | None
    proved: bool
    reason: str
    qualification: str='local_parametric_mathematical_coexistence_only_no_global_phase_or_native_correspondence'


def enclose_coexistence(source, expected_sha256, temperature, box, center, matrix, *, precision=60, weights=None):
    require(type(precision) is int and 40<=precision<=1000,'bounded_decimal_precision')
    require(type(expected_sha256) is str and len(expected_sha256)==64,'explicit_source_hash')
    raw=Path(source).read_bytes();require(hashlib.sha256(raw).hexdigest()==expected_sha256,'source_bytes_changed')
    eos=json.loads(raw)[0]['EOS'][0]
    require(eos['BibTeX_EOS']=='Wagner-JPCRD-2002','unsupported_eos')
    with localcontext() as ctx:
        ctx.prec=precision
        kw=dict(reducing_density=eos['STATES']['reducing']['rhomolar'],reducing_temperature=eos['STATES']['reducing']['T'],gas_constant=eos['gas_constant'],jet=lambda d,t:residual(d,t,eos['alphar']))
        whole=evaluate_box(temperature,box,**kw)
        require(type(center) is tuple and len(center)==2 and all(type(c) is D and c.is_finite() for c in center),'explicit_center')
        at_center=evaluate_box(temperature,tuple(I(c) for c in center),**kw)
        proof=krawczyk(box,center,matrix,at_center.residual,whole.jacobian,weights=weights)
        stable=all(d.lo>0 for d in whole.stability)
        lo=max(p.lo for p in whole.pressure);hi=min(p.hi for p in whole.pressure)
        pressure=Interval(lo,hi) if lo<=hi else None
        proved=proof.proved and stable and pressure is not None and pressure.lo>0
        reason='proved_local_parametric_coexistence' if proved else ('unresolved_stability_or_pressure' if proof.proved else proof.reason)
        return CoexistenceAttempt(expected_sha256,precision,whole,at_center,proof,pressure,proved,reason)
