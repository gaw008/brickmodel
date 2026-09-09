"""Exact manufactured arithmetic records; no native water calls."""
from copy import deepcopy
from fractions import Fraction as F
import pytest
from sludge_sandbox import pressure_comparison as m
from sludge_sandbox.paired_pressure import PressureState, SharedVolumes, LiquidEndpoints, certify_paired_pressure
from sludge_sandbox.paired_pressure_host import SharedConstantParameterBox
from sludge_sandbox.integration import ConservedState
from sludge_sandbox.verification_case import encode
from sludge_sandbox.water_properties import WaterState, WaterReference

REFERENCE=WaterReference(1.,1.,1.,0.,300.,0.)

def sample(p):
    return encode(WaterState(300.,0.,0.,1.,1.,REFERENCE,"analytic_fixture",p,"liquid",1.,0.,0.,0.))


def policy():
    return m.PressureComparisonPolicy((SharedConstantParameterBox('a'*64, ('A',), (F(1),),
                                      (F(1,100),), F(10), F(0)),))


def fixture():
    p=policy();source='b'*64
    state=ConservedState([[1.,1.,1.]], [10.], mechanical_stretches=[1.,1.])
    a=PressureState(source,F(300),F(1),F(1),(F(1),),F(10),F(1),F(0),(F(30),F(40)))
    box=p.cell_boxes[0]
    shared=SharedVolumes(source,box.species,box.solid_volume_m3_mol,box.solid_error_m3_mol,
                         box.reference_volume_m3,box.reference_error_m3)
    liquid=LiquidEndpoints(source,F(300),(F(30),F(40)),F(1),F(1),F(1,1000),F(1,1000))
    cert=certify_paired_pressure(a,a,shared,gas_constant_j_mol_k=F(1),pressure_domain_pa=(F(1),F(100)),
                                temperature_domain_k=(F(290),F(310)),liquid_a=liquid,liquid_b=liquid)
    binding={'base_sha256':'c'*64,'operator_sha256':'d'*64,'interfaces':['wet'],
             'boxes':p.to_record()['cell_boxes'],'sources':[source],
             'reference':[m._encode({'area':F(10),'half_thickness':F(1),'cells':1,'additional_bulk_error':F(0)})],
             'water_reference':encode(REFERENCE),'water_implementation':None,
             'domains':[m._encode({'liquid_v_error':F(1,1000),'pressure':(F(1),F(100)),'temperature':(F(290),F(310)),'gas_constant':F(1)})],
             'layout':{'species_order':['A','gas','liquid'],'gas_species_order':['gas'],
                       'solid_species_order':['A'],'liquid_column_id':'liquid'}}
    record={'schema':m.SCHEMA,'policy':p.to_record(),'bindings_a':binding,'bindings_b':binding,
            'states':[encode(state),encode(state)],'bound_pa':cert.bound_pa,
            'original_independent_bound_pa':10.,'endpoint_evaluations':4,
            'material_qualified':False,'temperature_uncertainty_included':False,
            'cells':[{'endpoint_samples':[sample(float(p)) for p in (30,40,30,40)],'cell_index':0,'certificate':cert.to_record(),'endpoint_evaluations':4,
                      'original_pressure_errors_pa':m._encode((F(5),F(5))),
                      'original_temperature_errors_k':m._encode((F(1,100),F(1,100))),
                      'reported_pressures_pa':m._encode((F(35),F(35))),
                      'reported_temperatures_k':m._encode((F(300),F(300)))}]}
    return p,state,binding,record


def test_exact_policy_roundtrip_and_no_implicit_box():
    p=policy()
    assert m.restore_pressure_comparison_policy(p.to_record())==p
    with pytest.raises(m.PressureComparisonError):m.PressureComparisonPolicy(())
    with pytest.raises(m.PressureComparisonError):m.PressureComparisonPolicy(p.cell_boxes*2)
    with pytest.raises(m.PressureComparisonError):m.PressureComparisonPolicy(list(p.cell_boxes))


def test_noncanonical_fraction_refused():
    raw=policy().to_record();raw['cell_boxes'][0]['reference_volume_m3']={'numerator':20,'denominator':2}
    with pytest.raises(m.PressureComparisonError,match='noncanonical'):m.restore_pressure_comparison_policy(raw)


def test_wet_arithmetic_keeps_independent_liquid_errors():
    p,state,binding,record=fixture()
    result=m.audit_pressure_comparison(record,policy=p,state_a=state,state_b=state,bindings_a=binding,bindings_b=binding)
    assert 0<result<record['original_independent_bound_pa']


@pytest.mark.parametrize('field',['bound','inventory','jacobian','temperature','source','root','cost','policy'])
def test_tampered_semantics_rejected(field):
    p,state,binding,record=fixture();record=deepcopy(record)
    cell=record['cells'][0];inputs=cell['certificate']['input_record_json']
    if field=='bound':record['bound_pa']=0.
    elif field=='cost':cell['endpoint_evaluations']=0
    elif field=='policy':record['policy']['schema']='generic'
    else:
        key={'inventory':'gas_mol','jacobian':'jacobian','temperature':'temperature_k','source':'source_identity','root':'root_interval_pa'}[field]
        inputs['a'][key]='e'*64 if field=='source' else (m._encode((F(31),F(40))) if field=='root' else m._encode(F(2)))
    with pytest.raises(ValueError):m.audit_pressure_comparison(record,policy=p,state_a=state,state_b=state,bindings_a=binding,bindings_b=binding)


def test_arbitrary_host_explicitly_refused():
    with pytest.raises(m.PressureComparisonError,match='direct_free'):
        m.compare_pressure_pair(None,None,(),None,None,(),policy=policy())


def test_actual_waterstate_encoding_has_no_computed_mass_property():
    value=sample(30.)
    assert "molar_mass_kg_mol" not in value
    assert value["reference"]["molar_mass_kg_mol"]==1.


@pytest.mark.parametrize("invalid",[True,"1.0",float("nan"),0.])
def test_endpoint_density_requires_positive_finite_real_json_number(invalid):
    p,state,binding,record=fixture()
    record['cells'][0]['endpoint_samples'][0]['density_kg_m3']=invalid
    with pytest.raises(m.PressureComparisonError,match='endpoint_sample_numeric'):
        m.audit_pressure_comparison(record,policy=p,state_a=state,state_b=state,bindings_a=binding,bindings_b=binding)
