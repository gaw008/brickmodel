from fractions import Fraction as F
import json
import pytest
from sludge_sandbox.exact_event_clock import ExactEventTime as T, ExactTimeInterval
from sludge_sandbox.exact_boundary_program import ExactProgramView
from sludge_sandbox.boundary_program import ScalarProgram, BoundaryProgram, ProgramIdentity


def identity():return ProgramIdentity(program_id='analytic',version='1',classification='virtual_design_choice',source_ids=('declared-analytic',))
def scalar():return ScalarProgram(identity=identity(),knot_times_s=(0.,.5,1.),values=(0.,1.,0.),unit='1')


def test_semantic_identity_is_not_origin_decomposition():
    a=T.from_origin(F(1,2),F(1,4));b=T.from_origin(F(1),F(-1,4))
    assert a==b and hash(a)==hash(b) and len({a,b})==1
    assert a>T(F(1,2)) and a.elapsed_since(T(F(1,2)))==F(1,4)
    assert a.shifted(F(-1,4))==T(F(1,2))
    assert T.from_record(json.loads(json.dumps(a.to_record())))==a


@pytest.mark.parametrize('bad',[True,.5,float('nan'),float('inf'),'0.5',1])
def test_explicit_rational_constructor(bad):
    with pytest.raises(ValueError):T(bad)
    with pytest.raises(ValueError):T.from_origin(F(),bad)


@pytest.mark.parametrize('n,d',[(True,1),(1,True),(1,0),(1,-1),(2,4),(0,2),('1',2),(1.,2)])
def test_noncanonical_serialization_rejected(n,d):
    with pytest.raises(ValueError):T.from_record({'schema':'exact_event_time_v1','numerator':n,'denominator':d})


def test_record_field_and_schema_guards():
    for record in (None,[],{'schema':'wrong','numerator':1,'denominator':1},dict(T(F()).to_record(),extra=1)):
        with pytest.raises(ValueError):T.from_record(record)


def test_float_adoption_and_display_not_semantic_time():
    assert T.from_float(.1).seconds==F(.1)!=F(1,10)
    for bad in (True,1,float('nan'),float('inf')):
        with pytest.raises(ValueError):T.from_float(bad)
    t=T(F(1,2)-F(1,10**20));display=t.display()
    assert display.seconds_binary64==.5 and display.signed_projection_error_s==F(1,10**20)
    assert T(F(10**400)).display().seconds_binary64 is None


def test_exact_interval_bounds_and_width():
    interval=ExactTimeInterval(T(F(1,2)),T(F(1,2)+F(1,10**20)))
    assert interval.width_s==F(1,10**20)
    assert interval.contains(interval.lower) and interval.contains(interval.upper)
    assert not interval.contains(T(F()))
    with pytest.raises(ValueError):ExactTimeInterval(interval.upper,interval.lower)
    with pytest.raises(ValueError):interval.contains(.5)


def test_piecewise_neighbors_keep_segment_even_when_display_is_knot():
    view=ExactProgramView(scalar());eps=F(1,10**20)
    left=T(F(1,2)-eps);right=T(F(1,2)+eps)
    assert left.display().seconds_binary64==right.display().seconds_binary64==.5
    assert view.position(left)==(1,1-2*eps)
    assert view.position(right)==(2,2*eps)
    assert view.position(T(F(1,2)))==(1,None)
    assert view.at(T(F(1,4)))==.5 and view.at(T(F(3,4)))==.5
    assert view.breakpoints(left,right)==(T(F(1,2)),)
    assert view.breakpoints(T(F()),T(F(1,2)))==()


def test_translated_entire_schedule_preserves_outputs_and_exact_weights():
    base=ExactProgramView(scalar());delta=F(10**12)+F(1,10**20)
    shifted=ExactProgramView(base.program,delta)
    for q in (F(),F(1,4),F(1,2)-F(1,10**20),F(1,2),F(3,4),F(1)):
        assert base.position(T(q))==shifted.position(T(q+delta))
        assert base.at(T(q))==shifted.at(T(q+delta))
    assert shifted.program.knot_times_s==(0.,.5,1.)


def test_boundary_state_matches_independent_linear_columns_and_legacy():
    p=BoundaryProgram(identity=identity(),knot_times_s=(0.,1.),gas_temperature_k=(300.,400.),
        radiation_temperature_k=(500.,300.),total_pressure_pa=(100000.,200000.),
        species_order=('A','B'),mole_fractions=((.25,.75),(.75,.25)))
    view=ExactProgramView(p);out=view.at(T(F(1,4)))
    assert (out.gas_temperature_k,out.radiation_temperature_k,out.total_pressure_pa)==(325.,450.,125000.)
    assert dict(out.mole_fractions)=={'A':.375,'B':.625}
    assert out.time==T(F(1,4))
    for f in (0.,.25,.5,1.):
        exact=view.at(T.from_float(f));legacy=p.at(f)
        assert exact.gas_temperature_k==legacy.gas_temperature_k
        assert dict(exact.mole_fractions)==dict(legacy.mole_fractions)
    with pytest.raises(TypeError):out.mole_fractions['A']=0.


def test_program_rejects_implicit_time_and_outside_domain():
    v=ExactProgramView(scalar())
    for q in (.5,True,T(F(-1)),T(F(2))):
        with pytest.raises(ValueError):v.at(q)
    with pytest.raises(ValueError):v.breakpoints(T(F(1)),T(F()))
    with pytest.raises(ValueError):ExactProgramView(v.program,.5)


def test_interval_serialization_rejects_display_and_inverted_records():
    interval=ExactTimeInterval(T(F(1,3)),T(F(2,3)))
    record=interval.to_record()
    assert ExactTimeInterval.from_record(json.loads(json.dumps(record)))==interval
    for bad in (dict(record,display=0.),dict(record,lower=record['upper'],upper=record['lower']),dict(record,lower=.3)):
        with pytest.raises(ValueError):ExactTimeInterval.from_record(bad)
