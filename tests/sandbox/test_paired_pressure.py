"""Independent exact rational wet roots and adversarial certificate inputs."""
import json
from dataclasses import replace,FrozenInstanceError
from fractions import Fraction as F
from itertools import product
import pytest
from sludge_sandbox import paired_pressure as m
ID='a'*64

def fixture():
    shared=m.SharedVolumes(ID,('solid',),(F(1),),(F(1,10),),F(10),F(1,5))
    a=m.PressureState(ID,F(10),F(1),F(1),(F(1),),F(10),F(1),F(0),(F(1),F(2)))
    b=m.PressureState(ID,F(10)+F(1,10**6),F(1)+F(1,10**6),F(1)-F(1,10**6),(F(1)-F(1,10**6),),F(10)*(1+F(1,10**6)),1+F(1,10**6),F(0),(F(1),F(2)))
    return a,b,shared

def liquid(t,p):return F(1,2)+t/F(100)-p/F(10000)

def endpoints(state,interval,error=F(2,10**8)):
    return m.LiquidEndpoints(ID,state.temperature_k,interval,liquid(state.temperature_k,interval[0]),liquid(state.temperature_k,interval[1]),error,error)

def certify(a,b,s,**kwargs):
    args=dict(gas_constant_j_mol_k=F(1),pressure_domain_pa=(F(1,2),F(3)),temperature_domain_k=(F(9),F(12)),liquid_a=endpoints(a,b.root_interval_pa) if a.liquid_mol else None,liquid_b=endpoints(b,b.root_interval_pa) if b.liquid_mol else None)
    args.update(kwargs);return m.certify_paired_pressure(a,b,s,**args)

def root_interval(state,solid_delta,reference_delta,extra=F(0),liquid_shift=F(0)):
    # Independent closure; no production residual or helper used as oracle.
    def residual(p):
        return state.liquid_mol*(liquid(state.temperature_k,p)+liquid_shift)+state.gas_mol*state.temperature_k/p+state.solid_mol[0]*(1+solid_delta)-(state.jacobian*(10+reference_delta)+extra)
    lo,hi=F(1),F(2)
    assert residual(lo)>0>residual(hi)
    for _ in range(180):
        mid=(lo+hi)/2
        if residual(mid)>0:lo=mid
        else:hi=mid
    assert residual(lo)>=0>=residual(hi)
    return lo,hi

def test_wet_analytic_pair_contains_independent_corner_roots_and_improves_bound():
    a,b,s=fixture();cert=certify(a,b,s)
    assert cert.exact_bound_pa<cert.independent_bound_pa/F(1000)
    assert cert.bound_pa>0 and F(cert.bound_pa)>=cert.exact_bound_pa
    for solid_error,reference_error in product((-s.solid_error_m3_mol[0],s.solid_error_m3_mol[0]),(-s.reference_error_m3,s.reference_error_m3)):
        ra=root_interval(a,solid_error,reference_error);rb=root_interval(b,solid_error,reference_error)
        upper=max(abs(ra[0]-rb[1]),abs(ra[1]-rb[0]))
        assert upper<=cert.exact_bound_pa
    record=cert.to_record();json.dumps(record,allow_nan=False)
    assert not record['temperature_uncertainty_included'] and not record['material_qualified']
    assert record['input_record_json']['b']['root_interval_pa'][0]=={'numerator':1,'denominator':1}

def test_point_liquid_errors_and_independent_extra_errors_never_cancel():
    a,b,s=fixture();small=certify(a,b,s)
    larger=certify(a,b,s,liquid_a=endpoints(a,b.root_interval_pa,F(1,100)),liquid_b=endpoints(b,b.root_interval_pa,F(1,100)))
    assert larger.pair_bound_pa>small.pair_bound_pa
    a=replace(a,independent_volume_error_m3=F(1,1000));b=replace(b,independent_volume_error_m3=F(1,1000))
    cert=certify(a,b,s);pieces=dict(cert.decomposition)
    assert pieces['independent_volume_errors']==(-F(2,1000),F(2,1000))
    for solid,reference,ea,eb in product((-F(1,10),F(1,10)),(-F(1,5),F(1,5)),(-F(1,1000),F(1,1000)),(-F(1,1000),F(1,1000))):
        ra=root_interval(a,solid,reference,ea);rb=root_interval(b,solid,reference,eb)
        assert max(abs(ra[0]-rb[1]),abs(ra[1]-rb[0]))<=cert.exact_bound_pa

def test_shared_constant_errors_scale_only_actual_parameter_differences():
    a,b,s=fixture();cert=certify(a,b,s);pieces=dict(cert.decomposition)
    expected=abs(a.solid_mol[0]-b.solid_mol[0])*s.solid_error_m3_mol[0]
    assert pieces['shared_solid_error']==(-expected,expected)
    expected=abs(a.jacobian-b.jacobian)*s.reference_error_m3
    assert pieces['shared_reference_error']==(-expected,expected)
    with pytest.raises(m.PairedPressureError):replace(s,contract='unstructured_pointwise_error')

def test_arbitrary_common_pivot_is_not_a_root_difference_certificate():
    # Same residual at a pivot, distinct roots despite strict monotonicity.
    assert (F(1)-F(0))==(F(1)-2*F(0))
    assert F(1)!=F(1,2)
    a,b,s=fixture()
    bad=replace(endpoints(a,b.root_interval_pa),pressure_interval_pa=(F(3,2),F(3,2)))
    with pytest.raises(m.PairedPressureError,match='entire_b_root_interval'):certify(a,b,s,liquid_a=bad)

@pytest.mark.parametrize('mutation',[
    lambda a,b,s:(replace(a,source_identity='b'*64),b,s),
    lambda a,b,s:(replace(a,temperature_k=F(20)),b,s),
    lambda a,b,s:(replace(a,root_interval_pa=(F(1,4),F(2))),b,s),
    lambda a,b,s:(replace(a,solid_mol=()),b,s),
    lambda a,b,s:(replace(a,bulk_volume_m3=F(11)),b,s),
    lambda a,b,s:(replace(a,independent_volume_error_m3=F(10)),b,s),
])
def test_binding_domain_and_geometry_guards(mutation):
    a,b,s=mutation(*fixture())
    with pytest.raises(m.PairedPressureError):certify(a,b,s)

@pytest.mark.parametrize('bad',[float('nan'),float('inf'),True,0.,-F(1)])
def test_nonexact_nonfinite_and_negative_inputs_refused(bad):
    a,_,_=fixture()
    with pytest.raises(m.PairedPressureError):replace(a,gas_mol=bad)

def test_positive_gas_and_liquid_source_evidence_required():
    a,b,s=fixture()
    with pytest.raises(m.PairedPressureError):replace(a,gas_mol=F(0))
    with pytest.raises(m.PairedPressureError):certify(a,b,s,liquid_a=None)
    with pytest.raises(m.PairedPressureError):certify(a,b,s,liquid_a=replace(endpoints(a,b.root_interval_pa),source_identity='b'*64))
    with pytest.raises(m.PairedPressureError):certify(a,b,s,liquid_a=replace(endpoints(a,b.root_interval_pa),temperature_k=F(11)))
    with pytest.raises(m.PairedPressureError):replace(endpoints(a,b.root_interval_pa),volume_at_upper_m3_mol=F(1))
    with pytest.raises(FrozenInstanceError):a.gas_mol=F(2)

def test_exact_dry_equal_inputs_are_zero_but_no_wet_evidence_is_invented():
    a,_,s=fixture();a=replace(a,liquid_mol=F(0))
    cert=certify(a,a,s)
    assert cert.exact_bound_pa==0 and cert.bound_pa==0
    with pytest.raises(m.PairedPressureError):certify(a,a,s,liquid_a=endpoints(a,a.root_interval_pa))


def test_identical_wet_inputs_retain_endpoint_error_and_pressure_width():
    a,_,s=fixture();cert=certify(a,a,s)
    assert cert.pair_bound_pa>0
    liquid_piece=dict(cert.decomposition)['liquid']
    assert liquid_piece[0]<0<liquid_piece[1]
    assert liquid_piece[1]-liquid_piece[0]>=4*a.liquid_mol*F(2,10**8)


def test_opposite_liquid_point_error_functions_remain_enclosed():
    a,b,s=fixture();error=F(1,1000)
    cert=certify(a,b,s,liquid_a=endpoints(a,b.root_interval_pa,error),liquid_b=endpoints(b,b.root_interval_pa,error))
    for ea,eb in product((-error,error),repeat=2):
        ra=root_interval(a,F(0),F(0),liquid_shift=ea)
        rb=root_interval(b,F(0),F(0),liquid_shift=eb)
        assert max(abs(ra[0]-rb[1]),abs(ra[1]-rb[0]))<=cert.exact_bound_pa
