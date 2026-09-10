from dataclasses import replace
from fractions import Fraction as F
import json
import pytest
from test_mass_wet_exact_controller import setup
from test_mass_wet_exact_stage import fixture,policy
from sludge_sandbox.mass_wet_exact_controller import integrate_mixed_exact
from sludge_sandbox.mass_wet_exact_record import (
    MixedRecordError, capture_binding, encode_mixed_run, read_mixed_run,
    export_mixed_record, audit_mixed_record, equal, unpack, pack, canonical,
)
from sludge_sandbox.exact_event_clock import ExactEventTime as T


def capture(monkeypatch,maximum=0):
    pair,initial,rp,cp=setup(monkeypatch);cp=replace(cp,maximum_evaluations=maximum)
    args=dict(start=T(F()),end=T(F(1,2000)),stage_policy=policy(),roundoff_policy=rp,original_liquid_fraction_limit=F('1e-8'),controller_policy=cp,constant_liquid_fixture=fixture(pair))
    binding=capture_binding(pair,initial,case_sha256='a'*64,runtime_identity={'modules':{'actual':'b'*64},'qualification':'synthetic-runtime-test'},**args)
    result=integrate_mixed_exact(pair,initial,**args)
    return result,binding


def test_real_resource_failure_roundtrip_raw_and_partial_audit(monkeypatch):
    result,binding=capture(monkeypatch)
    raw=encode_mixed_run(result,original_binding=binding)
    record=read_mixed_run(raw,expected_binding=binding)
    assert export_mixed_record(record).encode()==raw
    audit=audit_mixed_record(record,expected_binding=binding)
    assert audit.status=='partial_audit' and not audit.resume_allowed and audit.accepted_steps==0
    assert audit.unknown_checks
    assert equal(record.result,unpack(pack(result)))


def test_actual_sample_and_uncommitted_stage_failure_captured(monkeypatch):
    result,binding=capture(monkeypatch,3)
    assert result.costs and result.refinements[0].path.attempts
    raw=encode_mixed_run(result,original_binding=binding)
    record=read_mixed_run(raw)
    assert record.result.refinements[0].path.attempts
    assert audit_mixed_record(record,expected_binding=binding).accepted_steps==0


def test_status_cannot_be_relabelled_success(monkeypatch):
    result,binding=capture(monkeypatch)
    fake=replace(result,status='completed',reason=None)
    raw=encode_mixed_run(fake,original_binding=binding)
    with pytest.raises(MixedRecordError):audit_mixed_record(read_mixed_run(raw),expected_binding=binding)


def test_external_binding_and_frozen_wrapper_reaudit(monkeypatch):
    result,binding=capture(monkeypatch)
    raw=encode_mixed_run(result,original_binding=binding);record=read_mixed_run(raw)
    other=unpack(json.loads(binding));other=dict(other);other['case_sha256']='c'*64
    with pytest.raises(MixedRecordError,match='external_original'):audit_mixed_record(record,expected_binding=canonical(pack(other)))
    obj=json.loads(raw);obj['result']['fields']['costs']['tuple'][0]['tuple'][1]=-1
    poisoned=replace(record,canonical_bytes=canonical(obj))
    with pytest.raises(MixedRecordError):audit_mixed_record(poisoned,expected_binding=binding)


@pytest.mark.parametrize('bad',[{'fraction':[True,2]},{'fraction':[2,4]},{'float_hex':'nan'},{'record':'os.system','fields':{}},1.0])
def test_invalid_tagged_values_refused(bad):
    with pytest.raises(MixedRecordError):unpack(bad)


def test_no_loss_of_large_integer_fraction_and_negative_zero():
    value=(2**1000,F(1,3),-0.0,T(F(10**12)+F(1,10**20)))
    decoded=unpack(pack(value))
    assert canonical(pack(decoded))==canonical(pack(value))
    assert decoded[2].hex()=='-0x0.0p+0'


def test_actual_failed_terminal_projection_and_ledger_replayed(monkeypatch):
    from sludge_sandbox.mass_wet_transport import WetPair
    from sludge_sandbox.integration import DomainExit
    pair,initial,rp,cp=setup(monkeypatch)
    old=WetPair.evaluate
    def fail(self,states):
        if self.interfaces==('depleted_no_nucleation','existing_liquid'):
            raise DomainExit('record_test_mixed_endpoint_exit')
        return old(self,states)
    monkeypatch.setattr(WetPair,'evaluate',fail)
    cp=replace(cp,terminal_window_s=F(1))
    args=dict(start=T(F()),end=T(F(1,2000)),stage_policy=policy(),roundoff_policy=rp,original_liquid_fraction_limit=F('1e-8'),controller_policy=cp,constant_liquid_fixture=fixture(pair))
    binding=capture_binding(pair,initial,case_sha256='a'*64,runtime_identity={'qualification':'manufactured-test'},**args)
    result=integrate_mixed_exact(pair,initial,**args)
    assert result.status=='domain_exit' and not result.steps and result.refinements[0].path.frames
    record=read_mixed_run(encode_mixed_run(result,original_binding=binding))
    audit=audit_mixed_record(record,expected_binding=binding)
    assert audit.checked_projections==1 and audit.checked_path_steps==1 and audit.accepted_steps==0
    raw=json.loads(record.canonical_bytes)
    path=raw['result']['fields']['refinements']['tuple'][0]['fields']['path']['fields']
    path['states']['tuple'][1]['tuple'][0]['fields']['internal_energy_j']={'float_hex':(1000.0).hex()}
    with pytest.raises(MixedRecordError):
        audit_mixed_record(read_mixed_run(canonical(raw)),expected_binding=binding)


def test_duplicate_keys_and_boolean_counter_are_rejected(monkeypatch):
    result,binding=capture(monkeypatch)
    raw=encode_mixed_run(result,original_binding=binding)
    with pytest.raises(MixedRecordError,match='invalid_json'):
        read_mixed_run(b'{"schema":"a","schema":"b"}')
    obj=json.loads(raw)
    obj['result']['fields']['costs']['tuple'][0]['tuple'][1]=False
    with pytest.raises(MixedRecordError,match='nonnegative_costs'):
        audit_mixed_record(read_mixed_run(canonical(obj)),expected_binding=binding)


def test_original_policy_and_input_must_not_be_omitted(monkeypatch):
    result,binding=capture(monkeypatch)
    obj=json.loads(encode_mixed_run(result,original_binding=binding))
    del obj['binding']['mapping']['request']['mapping']['roundoff_policy']
    with pytest.raises(MixedRecordError,match='complete_original_request'):
        read_mixed_run(canonical(obj))
    with pytest.raises(MixedRecordError,match='original_request_changed'):
        encode_mixed_run(replace(result,original_end=T(F(1))),original_binding=binding)


@pytest.mark.parametrize('field,value',[
    ('original_liquid_fraction_limit',F('1e-9')),
    ('original_time',T(F(1,10))),
    ('source_ids',('invented_source',)),
])
def test_failed_global_context_retains_all_original_fields(monkeypatch,field,value):
    from sludge_sandbox.mass_wet_writeback import MixedWritebackTotals
    result,binding=capture(monkeypatch)
    ctx=replace(result.roundoff_totals.context,**{field:value})
    fake=replace(result,roundoff_totals=MixedWritebackTotals.empty(ctx))
    with pytest.raises(MixedRecordError):
        audit_mixed_record(read_mixed_run(encode_mixed_run(fake,original_binding=binding)),expected_binding=binding)


def test_failed_global_context_preserves_policy_and_water_mass(monkeypatch):
    from sludge_sandbox.mass_wet_writeback import MixedWritebackTotals
    result,binding=capture(monkeypatch)
    ctx=result.roundoff_totals.context
    changed=replace(ctx.policy,molar_mass_kg_mol=ctx.water_molar_mass_kg_mol*2)
    ctx=replace(ctx,water_molar_mass_kg_mol=changed.molar_mass_kg_mol,policy=changed)
    fake=replace(result,roundoff_totals=MixedWritebackTotals.empty(ctx))
    with pytest.raises(MixedRecordError):
        audit_mixed_record(read_mixed_run(encode_mixed_run(fake,original_binding=binding)),expected_binding=binding)


def test_ordinary_prefix_model_identity_is_original_per_cell(monkeypatch):
    result,binding=capture(monkeypatch,10)
    ref=result.refinements[0];path=ref.path
    assert len(path.states)>1
    states=list(path.states);row=list(states[-1])
    row[0]=replace(row[0],energy_model_identity='f'*64);states[-1]=tuple(row)
    fake=replace(result,refinements=(replace(ref,path=replace(path,states=tuple(states))),*result.refinements[1:]))
    with pytest.raises(MixedRecordError):
        audit_mixed_record(read_mixed_run(encode_mixed_run(fake,original_binding=binding)),expected_binding=binding)
