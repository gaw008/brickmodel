from dataclasses import replace
from fractions import Fraction as F
import json
import pytest
from test_exact_depletion_integration import setup
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_depletion_integration import integrate_exact_depletion
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.exact_record import encode_exact_run,read_exact_run,validate_binding,ExactRecordError,pack


def make(monkeypatch,cancelled=False):
    s,v,p,e,calls=setup(monkeypatch)
    # Existing algebra fixture constructs an intentionally partial native host.
    # Permit only dataclass reconstruction in this test; source digests stay real.
    monkeypatch.setattr(WaterPhaseTransfer,'__post_init__',lambda self:None)
    start,end=T(F()),T(F(3,100))
    result=integrate_exact_depletion(s,v,start=start,end=end,integration_policy=p,event_policy=e,
        cancel=(lambda:len(calls)>15) if cancelled else None)
    raw=encode_exact_run(result,original_operator=v,start=start,end=end,case_sha256='a'*64,runtime_identity={'modules':{'test':'b'*64}})
    return raw,v,result


def test_full_roundtrip_and_live_binding(monkeypatch):
    raw,v,result=make(monkeypatch)
    record=read_exact_run(raw)
    assert record.result.status=='completed'
    assert record.canonical_bytes==raw
    assert len(record.ledgers)==len(result.steps)
    assert pack(record.states[-1])==pack(result.states[-1])
    assert sum(map(len,record.result.packets))==2
    validate_binding(record,v,case_sha256='a'*64,runtime_identity={'modules':{'test':'b'*64}})
    with pytest.raises(ExactRecordError):validate_binding(record,v,case_sha256='c'*64,runtime_identity={'modules':{'test':'b'*64}})
    with pytest.raises(ValueError):record.states[0].amounts_mol[0,0]=0


def test_cancelled_prefix_and_no_live_getter_during_capture(monkeypatch):
    raw,v,result=make(monkeypatch,True)
    assert result.status=='cancelled' and result.steps
    assert read_exact_run(raw).result.status=='cancelled'
    object.__setattr__(v.operator,'coefficient_version','mutated')
    raw2=encode_exact_run(result,original_operator=v,start=result.times_s[0],end=T(F(3,100)),case_sha256='a'*64,runtime_identity={})
    assert read_exact_run(raw2).result.status=='cancelled'
    with pytest.raises(ValueError):validate_binding(read_exact_run(raw2),v,case_sha256='a'*64,runtime_identity={})


@pytest.mark.parametrize('mutation', ['bool_cost','fraction','extra','compact','ledger_time','event_cell','mode','observation_error'])
def test_tampered_records_refused(monkeypatch,mutation):
    raw,_,_=make(monkeypatch);d=json.loads(raw);r=d['result']['fields']
    if mutation=='bool_cost':r['costs']['mapping']['ordinary_trials']=True
    elif mutation=='fraction':d['start']['exact_time']['denominator']=True
    elif mutation=='extra':d['unlisted']=0
    elif mutation=='compact':d['capture_kind']='research_compact'
    elif mutation=='ledger_time':r['steps']['sequence'][0]['fields']['end_s']=d['start']
    elif mutation=='event_cell':r['packets']['sequence'][0]['sequence'][0]['fields']['terminal']['fields']['root_order']['fields']['selected_cell']=True
    elif mutation=='observation_error':
        obs=r['terminal_attempts']['sequence'][0]['fields']['observations']['sequence'][0]['fields']['evaluation']
        obs['fields']['pressure_errors_pa']['sequence'][0]={'float_hex':(-1.).hex()}
    elif mutation=='mode':r['operator']['fields']['modes']['sequence'][0]='existing_liquid'
    with pytest.raises(ExactRecordError):read_exact_run(json.dumps(d).encode())


def test_duplicate_and_nonfinite_json():
    for raw in (b'{"schema":1,"schema":2}',b'{"x":NaN}',b'{"x":Infinity}'):
        with pytest.raises(ExactRecordError):read_exact_run(raw)


def test_decoded_evidence_array_cannot_restore_writeability():
    import numpy as np
    from sludge_sandbox.exact_record import unpack
    array=unpack(pack(np.array([[1.,2.]])))
    with pytest.raises(ValueError):array.setflags(write=True)
    with pytest.raises(ValueError):array.base.setflags(write=True)


def test_actual_saved_native_equilibrium_data_closure():
    from pathlib import Path
    from sludge_sandbox.water_properties import WaterState,WaterReference
    from sludge_sandbox.water_implementation import WaterImplementation
    from sludge_sandbox.water_chemical_potential import WaterLiquidChemicalState,WaterVaporChemicalState,WaterPhaseEquilibrium
    from sludge_sandbox.exact_record import unpack
    d=json.loads(Path(__file__).with_name('exact-record-native-equilibrium.json').read_text())
    st=d['liquid']['state'];ref=st['reference'];ref['source_ids']=tuple(ref['source_ids'])
    impl=st['implementation'];impl['source_ids']=tuple(impl['source_ids'])
    st['reference']=WaterReference(**ref);st['implementation']=WaterImplementation(**impl)
    d['liquid']['state']=WaterState(**st)
    for part,cls in [('liquid',WaterLiquidChemicalState),('vapor',WaterVaporChemicalState)]:
        d[part]['source_ids']=tuple(d[part]['source_ids']);d[part]=cls(**d[part])
    d['source_ids']=tuple(d['source_ids']);equilibrium=WaterPhaseEquilibrium(**d)
    encoded=pack(equilibrium)
    assert pack(unpack(encoded))==encoded


def test_validation_returns_reparsed_record_not_manual_replacement(monkeypatch):
    raw,v,_=make(monkeypatch);record=read_exact_run(raw)
    forged=replace(record,result=None,states=())
    checked=validate_binding(forged,v,case_sha256='a'*64,runtime_identity={'modules':{'test':'b'*64}})
    assert checked is not forged and checked.result.status=='completed' and checked.states


def test_nested_rates_shape_rejected(monkeypatch):
    raw,_,_=make(monkeypatch);d=json.loads(raw)
    rates=d['result']['fields']['terminal_attempts']['sequence'][0]['fields']['observations']['sequence'][0]['fields']['evaluation']['fields']['rates']['fields']
    a=rates['reaction_species_mol_s']['array'];a['shape']=[2];a['values']=a['values'][:2]
    with pytest.raises(ExactRecordError):read_exact_run(json.dumps(d).encode())


def test_final_mechanics_cannot_disappear(monkeypatch):
    raw,_,_=make(monkeypatch);d=json.loads(raw)
    d['result']['fields']['states']['sequence'][-1]['fields']['mechanical_stretches']=None
    with pytest.raises(ExactRecordError):read_exact_run(json.dumps(d).encode())


def test_committed_correction_selected_cell_binding(monkeypatch):
    # Inject a structurally valid but wrong-cell correction into an exact-zero
    # event. This is a saved-record attack, not a new physical test fixture.
    from sludge_sandbox.exact_affine_depletion import ExactDepletionWritebackRecord
    raw,_,_=make(monkeypatch);d=json.loads(raw)
    terminal=d['result']['fields']['packets']['sequence'][0]['sequence'][0]['fields']['terminal']['fields']
    selected=terminal['root_order']['fields']['selected_cell']
    c=ExactDepletionWritebackRecord(1-selected,0,1,0.,0.,0.,F(),F(),F(),F(),F(),F(1,10**12),0.,F())
    terminal['correction']=pack(c)
    d['result']['fields']['roundoff_totals']['fields']['events']=1
    with pytest.raises(ExactRecordError,match='correction_selected_indices'):read_exact_run(json.dumps(d).encode())


def test_six_gate_booleans_rejected(monkeypatch):
    raw,_,_=make(monkeypatch);d=json.loads(raw)
    d['result']['fields']['packets']['sequence'][0]['sequence'][0]['fields']['packet_maximum_differences']={'sequence':[True]*6}
    with pytest.raises(ExactRecordError):read_exact_run(json.dumps(d).encode())


def test_actual_case_integer_policy_roundtrip_without_coercion():
    from pathlib import Path
    from sludge_sandbox.integration import IntegrationPolicy
    from sludge_sandbox.exact_record import unpack
    case=json.loads(Path(__file__).with_name('exact-record-integer-policy-case.json').read_text())
    policy=IntegrationPolicy(**case['numerics']['integration'])
    assert type(policy.energy_scale_j) is int and policy.energy_scale_j==1
    encoded=pack(policy)
    restored=unpack(encoded)
    assert type(restored.energy_scale_j) is int and restored.energy_scale_j==1
    assert pack(restored)==encoded
    encoded['fields']['energy_scale_j']=True
    with pytest.raises(ExactRecordError,match='field_type'):unpack(encoded)
