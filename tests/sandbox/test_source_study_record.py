"""Complete passive study records; native EOS and model reconstruction forbidden."""

def test_study_codec_has_installable_entry_points():
    from sludge_sandbox.source_study_record import (
        encode_source_study, decode_source_study, import_saved_source_study,
    )
    assert all(callable(f) for f in (encode_source_study,decode_source_study,import_saved_source_study))


def minimal_saved_study():
    """Cheap declared partial study around one actual archived N3 observation.

    Only the outer stopped-study envelope is manufactured for codec tests; the
    original observation and index 0/ordinal 1 are unchanged. No EOS is called.
    """
    import json
    from pathlib import Path
    fixture=Path(__file__).parent/'fixtures/source-observation-v1/native-captures.json'
    saved=json.loads(fixture.read_bytes())
    return json.dumps(dict(status='cancelled',reason='manufactured codec fixture stopped after saved probe',
        material_qualified=False,scope='test_only_partial_study_envelope_actual_saved_observation',
        cell_count=3,captures=[saved['captures'][0]],adapter_provenance=saved['adapter_provenance']),
        allow_nan=False).encode()

import json
from dataclasses import replace
from fractions import Fraction as F
from types import MappingProxyType

import pytest

from sludge_sandbox.source_observation_record import SourceObservationContext
from sludge_sandbox.source_study_record import (
    encode_source_study,decode_source_study,import_saved_source_study,SourceStudyRecordError,
)
from sludge_sandbox.source_study_schema import SourceStudyNode


def changed(node,**values):
    return replace(node,values=MappingProxyType(dict(node.values,**values)))


@pytest.fixture(scope='module')
def actual_studies():
    from test_source_prefix_trial import fixture,run,POLICY
    from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
    from sludge_sandbox.exact_event_clock import ExactEventTime as T
    with pytest.MonkeyPatch.context() as patch:
        adapter,state=fixture(patch)
        successful=run(adapter,state)
        failed=evaluate_source_prefix_trial(adapter,state,start=T(F()),end=T(F(1,16384)),
            integration_policy=POLICY,maximum_callbacks=4)
        context=SourceObservationContext(successful.operator_identity,successful.energy_identity,
            successful.fixed_dry_mass_kg,adapter.interfaces)
        results=[]
        for trial in (successful,failed):
            captures=tuple(dict(ordinal=c.ordinal,phase=c.role,packed_input=c.state,time=c.time,
                operator_identity=trial.operator_identity,energy_identity=trial.energy_identity,
                interface_modes=adapter.interfaces,evaluation=c.evaluation,failure=c.failure,
                failure_kind=c.failure_kind) for c in trial.captures)
            results.append(decode_source_study(encode_source_study({'seed':trial},contexts=(context,),
                captures=captures,metadata={'status':trial.status,'material_qualified':False})))
        return tuple(results)


def encode_record(record,**changes):
    fields=dict(roots=record.roots,contexts=record.contexts,captures=record.captures,
                metadata=record.metadata,provenance=record.provenance)
    fields.update(changes)
    return encode_source_study(**fields)


def test_complete_actual_trial_and_failure_roundtrip_no_EOS(actual_studies,monkeypatch):
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    def forbidden(*args,**kwargs): pytest.fail('codec attempted new physics')
    monkeypatch.setattr(WaterProperties,'state_tp',forbidden)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    for record in actual_studies:
        assert encode_record(record)==record.canonical_bytes
        record.check()
        assert len(record.observations)==len(record.captures)
        assert record.roots['seed'].adapter.available is True
        assert not record.resume_authorized and not record.material_qualified
        assert record.audit['source_assets_verified'] is False
        assert all(not c['packed_input'].amounts_mol.flags.writeable for c in record.captures)
    good,bad=actual_studies
    assert good.roots['seed'].status=='validated_positive_numerical_trial'
    assert good.audit['checks']['completed_reference_replays']==1
    assert bad.roots['seed'].status=='resource_limit'
    assert bad.audit['checks']['preserved_failed_trials']==1
    assert bad.roots['seed'].reference.status!='completed'


def test_minimal_legacy_import_preserves_every_capture_and_metadata_field():
    data=json.loads(minimal_saved_study())
    data['new_pressure_study']={'status':'failed','extra_requests':[
        {'ordinal':1,'status':'failed','temperature_k':325.,'pressure_pa':100000.,
         'failure':'explicit manufactured timeout','source_marker':'source:original'}],
        'extra_request_cap':16,'exception_type':'TimeoutError','original_unknown_field':'preserved_as_metadata'}
    raw=json.dumps(data,allow_nan=False).encode()
    record=import_saved_source_study(raw)
    assert len(record.observations)==1 and record.observations[0].context.interface_modes==('existing_liquid',)*3
    assert record.metadata['new_pressure_study']['extra_requests'][0]['failure']=='explicit manufactured timeout'
    assert record.metadata['new_pressure_study']['original_unknown_field']=='preserved_as_metadata'
    assert record.provenance['original_file_sha256']
    record.check()


def test_failed_top_capture_keeps_position_without_fake_observation():
    data=json.loads(minimal_saved_study()); first=data['captures'][0]
    failure=dict(first,ordinal=2,failure='empty return after timeout',exception_type='TimeoutError')
    del failure['evaluation'];data['captures'].append(failure)
    record=import_saved_source_study(json.dumps(data).encode())
    assert len(record.captures)==len(record.observations)==2
    assert record.observations[0] is not None and record.observations[1] is None
    assert record.captures[1]['failure']=='empty return after timeout'


@pytest.mark.parametrize('field,value',[
    ('ordinal',True),('ordinal',2),('operator_identity',('exact_source_column_v1','0'*64,('liquid_water','O2','N2','H2O'))),
    ('interface_modes',('depleted_no_nucleation',)*3),
])
def test_top_capture_associations_rejected_with_valid_new_hash(field,value):
    record=import_saved_source_study(minimal_saved_study())
    capture=dict(record.captures[0],**{field:value})
    with pytest.raises(SourceStudyRecordError): encode_record(record,captures=(capture,))


def test_original_trial_policy_outcome_and_ledger_cannot_be_rebound_by_file_hash(actual_studies):
    record=actual_studies[0];trial=record.roots['seed']
    altered_policy=changed(trial.policy,amount_absolute_tolerance_mol=1.)
    for bad in (changed(trial,policy=altered_policy),changed(trial,status='cancelled'),
                changed(trial,maximum_callbacks=1),changed(trial,terminal_bounds=())):
        with pytest.raises(SourceStudyRecordError): encode_record(record,roots={'seed':bad})
    ledger=trial.reference.steps[0]
    energy=ledger.cell_work_j.copy();energy[0]+=1.
    wrong=changed(ledger,cell_work_j=energy)
    reference=changed(trial.reference,steps=(wrong,)+trial.reference.steps[1:])
    with pytest.raises(SourceStudyRecordError):encode_record(record,roots={'seed':changed(trial,reference=reference)})


def test_unknown_class_extra_fields_and_noncanonical_fraction_are_rejected():
    raw=minimal_saved_study();data=json.loads(raw)
    for mutator in (
        lambda d:d['captures'][0]['packed_input'].update(type='os.system'),
        lambda d:d['captures'][0]['packed_input']['fields'].update(unexpected_field=1),
        lambda d:d['captures'][0]['time']['fields'].update(seconds={'numerator':0,'denominator':2}),
        lambda d:d['captures'][0]['time']['fields'].update(seconds={'numerator':True,'denominator':1}),
    ):
        value=json.loads(raw);mutator(value)
        with pytest.raises(SourceStudyRecordError):import_saved_source_study(json.dumps(value).encode())


def test_duplicate_keys_nonfinite_unknown_format_and_partial_roots_rejected():
    for raw in (b'{"captures":[],"captures":[]}',b'{"captures":[],"bad":NaN}'):
        with pytest.raises(SourceStudyRecordError):import_saved_source_study(raw)
    with pytest.raises(SourceStudyRecordError):import_saved_source_study(minimal_saved_study(),source_format='auto')
    with pytest.raises(SourceStudyRecordError):encode_source_study({'seed':'just-a-hash'},contexts=())


def test_array_allocation_guard_precedes_numpy_allocation(monkeypatch):
    import numpy as np
    data=json.loads(minimal_saved_study())
    data['captures'][0]['packed_input']['fields']['amounts_mol']['shape']=[1000000,1000000]
    def forbidden(*args,**kwargs):pytest.fail('oversized array allocated')
    monkeypatch.setattr(np,'asarray',forbidden)
    with pytest.raises(SourceStudyRecordError,match='array_limit'):
        import_saved_source_study(json.dumps(data).encode())


def test_dag_digest_missing_reference_and_unreachable_node_rejected():
    record=import_saved_source_study(minimal_saved_study())
    data=json.loads(record.canonical_bytes)
    for mode in ('digest','missing','unused'):
        value=json.loads(record.canonical_bytes)
        key=next(iter(value['nodes']))
        if mode=='digest':value['nodes'][key]={'mapping':{}}
        elif mode=='missing':del value['nodes'][value['root']['ref']]
        else:value['nodes']['0'*64]={'mapping':{}}
        with pytest.raises(SourceStudyRecordError):decode_source_study(json.dumps(value).encode())
    assert len(data['nodes'])<250


def test_scope_mutation_and_mutable_inputs_do_not_change_snapshot():
    record=import_saved_source_study(minimal_saved_study())
    for bad in (replace(record,resume_authorized=True),replace(record,audit={}),
                replace(record,observations=()),replace(record,metadata={'status':'fabricated'})):
        with pytest.raises(SourceStudyRecordError):bad.check()
    capture=dict(record.captures[0]);source=dict(record.metadata)
    result=decode_source_study(encode_record(record,captures=(capture,),metadata=source))
    capture['ordinal']=99;source['status']='changed'
    assert result.captures[0]['ordinal']==1 and result.metadata['status']=='cancelled'


@pytest.fixture(scope='module')
def actual_event_study():
    from test_source_multicell_terminal import prepare_multicell
    from sludge_sandbox.source_dry_transition import evaluate_source_dry_transition
    from sludge_sandbox.source_dry_shared_pressure import declare_source_shared_dry_volume
    from sludge_sandbox.source_root_comparison import evaluate_source_common_endpoint,positive_source_common_end
    with pytest.MonkeyPatch.context() as patch:
        refinement,end=prepare_multicell(patch)
        adapter=refinement.approach.proposal.original_trial.adapter
        event=evaluate_source_dry_transition(refinement,end=end,maximum_callbacks_per_path=24,
            shared_volume=declare_source_shared_dry_volume(adapter.column.storages[1]))
        common=evaluate_source_common_endpoint(refinement,end=positive_source_common_end(refinement),
            maximum_callbacks_per_trial=16)
        contexts=tuple(SourceObservationContext(a.operator_identity,a.energy_model_identity,
            refinement.approach.proposal.original_trial.fixed_dry_mass_kg,a.interfaces) for a in (adapter,event.candidates[0].terminal.dry_adapter))
        raw=encode_source_study({'transition':event,'common_endpoint':common},contexts=contexts,
            metadata={'material_qualified':False,'numerical_event_accepted':event.numerical_event_accepted})
        return decode_source_study(raw)


def test_complete_multicell_event_and_common_paths_preserve_pure_accounts(actual_event_study,monkeypatch):
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    def forbidden(*args,**kwargs):pytest.fail('saved event attempted fresh physics')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    record=actual_event_study
    record.check()
    assert record.audit['checks']['complete_transition_balance_rows']==7
    assert record.audit['checks']['common_reference_balance_rows']>=3
    assert record.roots['transition'].selected_cell_index==1
    assert not record.roots['transition'].numerical_event_accepted
    assert record.roots['transition'].cell_selected_pressure_gates[0]==(False,True,False)
    assert all(len(row.cell_balances)==3 for path in record.roots['transition'].balance_paths for row in path)


def test_event_balances_prior_clock_pressure_and_stage_associations_reject_new_hash(actual_event_study):
    record=actual_event_study;event=record.roots['transition']
    row=event.balance_paths[0][0]
    bad_balance=changed(row,full_energy_residual_j=row.full_energy_residual_j+F(1))
    bad_paths=((bad_balance,)+event.balance_paths[0][1:],event.balance_paths[1])
    first=event.candidates[0]
    mutations=(changed(event,balance_paths=bad_paths),
        changed(event,candidates=(changed(first,terminal=changed(first.terminal,root_index=1)),event.candidates[1])),
        changed(event,candidates=(changed(first,terminal=changed(first.terminal,reused_clock_rounds=0)),event.candidates[1])),
        changed(event,numerical_event_accepted=True,status='conditional_numerical_event_accepted'),
        changed(event,cell_selected_pressure_bounds_pa=((F(),)*3,)*2),
        changed(event,refinement=changed(event.refinement,new_evaluations=0)),
        changed(event,shared_volume=changed(event.shared_volume,volume_interval_m3=(F(1),F(1)))))
    for value in mutations:
        with pytest.raises(SourceStudyRecordError):encode_record(record,roots={'transition':value})
    common=record.roots['common_endpoint']
    with pytest.raises(SourceStudyRecordError):encode_record(record,roots={
        'common_endpoint':changed(common,cumulative_residuals=())})


def test_complete_failure_exception_retains_returned_nested_records(actual_studies):
    from sludge_sandbox.source_approach import SourceApproachAssessmentError
    trial=actual_studies[0].roots['seed']
    cause=ValueError('saved postprocessing failure')
    failure=SourceApproachAssessmentError('comparison',None,trial,None,None,cause)
    record=decode_source_study(encode_source_study({'failure':failure},contexts=actual_studies[0].contexts))
    node=record.roots['failure']
    assert node.exception_type.endswith('SourceApproachAssessmentError') and node.stage=='comparison'
    assert node.records['trial'].status=='validated_positive_numerical_trial'
    assert record.audit['checks']['completed_reference_replays']==1


def test_shared_deep_dag_depth_and_huge_integer_guards():
    from sludge_sandbox.source_study_record import MAX_DEPTH
    value=('leaf',)
    for _ in range(MAX_DEPTH+1):value=(value,)
    with pytest.raises(SourceStudyRecordError,match='resource_limit'):
        encode_source_study({},contexts=(),metadata={'deep':value})
    with pytest.raises(SourceStudyRecordError,match='integer_limit'):
        encode_source_study({},contexts=(),metadata={'integer':2**5000})
    # The same immutable child is used twice and remains finite to inspect.
    shared=('leaf',)
    for _ in range(20):shared=(shared,shared)
    record=decode_source_study(encode_source_study({},contexts=(),metadata={'shared':shared}))
    assert len(json.loads(record.canonical_bytes)['nodes'])<30
    record.check()


def test_exact_dag_comparison_does_not_expand_repeated_nodes():
    from sludge_sandbox.source_study_audit import _same
    a=b=('leaf',)
    for _ in range(70):a=(a,a);b=(b,b)
    assert _same(a,b)
    assert not _same(a,('different',))


def test_original_pressure_gates_and_strategy_remain_bound_after_rehash(actual_event_study):
    record=actual_event_study;event=record.roots['transition']
    assert event.conditional_pressure_gates==(False,False)
    assert any(value is False for row in event.cell_conditional_pressure_gates for value in row)
    for mutation in (
        {'cell_conditional_pressure_gates':((True,)*3,)*2},
        {'conditional_pressure_bounds_pa':(F(),F())},
        {'conditional_pressure_gates':(True,True)},
        {'pressure_strategy':'original_independent_source_pressure'},
    ):
        with pytest.raises(SourceStudyRecordError):
            encode_record(record,roots={'transition':changed(event,**mutation)})


def test_returned_validation_failure_keeps_raw_return_without_success_qualification():
    data=json.loads(minimal_saved_study());capture=data['captures'][0]
    capture['evaluation']['fields']['time']['fields']['seconds']={'numerator':1,'denominator':1}
    capture.update(failure='captured return has the wrong exact time',failure_kind='IntegrationError')
    record=import_saved_source_study(json.dumps(data).encode())
    assert record.observations==(None,) and len(record.captures)==1
    assert record.captures[0]['evaluation'].time.seconds==F(1)
    assert record.captures[0]['time'].seconds==0
    assert record.audit['checks']['unvalidated_returned_top_captures']==1
    assert record.audit['checks'].get('top_source_observations',0)==0
    record.check()
    del capture['failure'];del capture['failure_kind']
    with pytest.raises(SourceStudyRecordError,match='capture_return_binding'):
        import_saved_source_study(json.dumps(data).encode())


def test_failed_return_still_checks_closed_types_and_original_input_context():
    data=json.loads(minimal_saved_study());capture=data['captures'][0]
    capture.update(failure='',failure_kind='IntegrationError')
    capture['packed_input']['fields']['amounts_mol']['shape']=[1,12]
    with pytest.raises(SourceStudyRecordError):import_saved_source_study(json.dumps(data).encode())
    data=json.loads(minimal_saved_study());capture=data['captures'][0]
    capture.update(failure='bad return',failure_kind='IntegrationError')
    capture['evaluation']['type']='untrusted.dynamic.Callback'
    with pytest.raises(SourceStudyRecordError):import_saved_source_study(json.dumps(data).encode())
