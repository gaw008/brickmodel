"""Full-temperature local monotonicity tube. No stable-phase admission."""
from dataclasses import dataclass
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,time
from sludge_sandbox import water_interval_eos as eos

PIN='28bcfac0829a4d7cf55a58a71a5ddf9383687872808525841f3f1395a90cedc0'


def check(ok,reason):
    if not ok:raise ValueError(reason)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def binding_snapshot(binding):
    value=binding()
    check(type(value) is tuple and bool(value) and all(type(v) is str and bool(v) and v.strip()==v for v in value),'immutable_nonempty_string_binding_required')
    return value

def valid(i):
    check(type(i) is eos.Interval and type(i.lo) is D and type(i.hi) is D,'typed_interval')
    i.__post_init__()


@dataclass(frozen=True)
class Visit:
    density: eos.Interval
    derivative: eos.Interval | None
    decision: str


@dataclass(frozen=True)
class TubeResult:
    temperature: eos.Interval
    density: eos.Interval
    visits: tuple
    leaves: tuple
    pending: tuple
    evaluations_attempted: int
    evaluations_completed: int
    maximum_boxes: int
    maximum_wall_seconds: float
    elapsed_seconds: float
    proved: bool
    reason: str
    source_before: tuple
    source_after: tuple | None
    qualification: str
    reducing_density: D
    reducing_temperature: D
    precision: int | None = None


def prove_generic(temperature,density,*,derivative,binding,reducing_density,reducing_temperature,maximum_boxes,maximum_wall_seconds,clock=time.monotonic):
    """Generic proof conditional on callback enclosure truth; not an EOS certificate."""
    valid(temperature);valid(density)
    check(type(reducing_density) is D and type(reducing_temperature) is D and reducing_density.is_finite() and reducing_temperature.is_finite(),'explicit_reducing_constants')
    check(0<temperature.lo<=temperature.hi<reducing_temperature and 0<reducing_density<density.lo<density.hi,'strict_high_density_subcritical_domain')
    check(type(maximum_boxes) is int and maximum_boxes>0,'positive_box_budget')
    check(type(maximum_wall_seconds) is float and 0<maximum_wall_seconds<float('inf'),'positive_wall_budget')
    begun=clock();before=binding_snapshot(binding);after=None;visits=[];leaves=[];pending=[density];attempted=completed=0;reason='proved_monotone_tube'
    try:
        while pending:
            after=binding_snapshot(binding);check(after==before,'source_changed')
            check(clock()-begun<=maximum_wall_seconds,'wall_budget')
            check(attempted<maximum_boxes,'box_budget')
            box=pending[0];attempted+=1
            try:d=derivative(temperature,box);completed+=1;valid(d)
            except Exception:
                visits.append(Visit(box,None,'callback_failed'));raise
            visits.append(Visit(box,d,'evaluated_not_accepted'))
            after=binding_snapshot(binding);check(after==before,'source_changed')
            check(clock()-begun<=maximum_wall_seconds,'wall_budget')
            if d.lo>0:
                pending.pop(0);leaves.append(box);visits[-1]=Visit(box,d,'positive');continue
            if d.hi<=0:
                visits[-1]=Visit(box,d,'nonpositive');reason='nonpositive_derivative';break
            # Exact finite-Decimal midpoint, independent of ambient precision.
            f=(F(box.lo)+F(box.hi))/2
            with localcontext() as ctx:
                ctx.prec=max(len(box.lo.as_tuple().digits),len(box.hi.as_tuple().digits))+abs(box.lo.adjusted()-box.hi.adjusted())+abs(box.lo.as_tuple().exponent-box.hi.as_tuple().exponent)+20
                m=D(f.numerator)/D(f.denominator)
            check(F(m)==f and box.lo<m<box.hi,'exact_midpoint_unavailable')
            visits[-1]=Visit(box,d,'split');pending.pop(0)
            pending.extend((eos.Interval(m,box.hi),eos.Interval(box.lo,m)))
        after=binding_snapshot(binding);check(after==before,'source_changed')
    except Exception as exc:reason=type(exc).__name__+': '+str(exc)
    elapsed=clock()-begun
    ordered=tuple(sorted(leaves,key=lambda x:x.lo))
    coverage=bool(ordered) and ordered[0].lo==density.lo and ordered[-1].hi==density.hi and all(a.hi==b.lo for a,b in zip(ordered,ordered[1:]))
    proved=not pending and coverage and reason=='proved_monotone_tube' and elapsed<=maximum_wall_seconds and after==before
    if reason=='proved_monotone_tube' and not proved:reason='incomplete_coverage_or_wall'
    return TubeResult(temperature,density,tuple(visits),ordered,tuple(pending),attempted,completed,maximum_boxes,maximum_wall_seconds,elapsed,proved,reason,before,after,'conditional_generic_enclosure_only_no_phase_admission',reducing_density,reducing_temperature)


def prove_density_tube(source,expected_sha256,temperature,density,*,precision=60,maximum_boxes=256,maximum_wall_seconds=30.):
    """Pinned reviewed mathematical EOS, full T on every density rectangle."""
    check(type(precision) is int and 40<=precision<=1000,'bounded_precision')
    implementation=Path(eos.__file__)
    def binding():return (sha(source),sha(implementation))
    check(binding()==(expected_sha256,PIN),'source_or_implementation_mismatch')
    raw=Path(source).read_bytes();check(hashlib.sha256(raw).hexdigest()==expected_sha256,'source_changed')
    data=json.loads(raw)[0]['EOS'][0]
    check(data['BibTeX_EOS']=='Wagner-JPCRD-2002','unsupported_eos')
    def derivative(t,r):return eos.pressure_interval(source,expected_sha256,t,r,precision=precision)[1]
    result=prove_generic(temperature,density,derivative=derivative,binding=binding,reducing_density=D(data['STATES']['reducing']['rhomolar']),reducing_temperature=D(data['STATES']['reducing']['T']),maximum_boxes=maximum_boxes,maximum_wall_seconds=maximum_wall_seconds)
    from dataclasses import replace
    return replace(result,precision=precision,qualification='pinned_mathematical_EOS_local_monotonicity_only_no_stable_phase_or_native_correspondence')
