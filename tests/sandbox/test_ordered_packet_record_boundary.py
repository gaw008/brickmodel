"""Legacy records cannot authorize an unaudited packet contract."""
from dataclasses import fields, replace
import pytest
from sludge_sandbox.depletion_integration import DepletionResult
from sludge_sandbox import event_record as records
from test_event_record import run


@pytest.fixture(scope='module')
def legacy():
    out, initial, policy, event_policy = run()
    record = records.encode_depletion_result(out, original_interfaces=('existing_liquid',))
    original = replace(out.operator, interfaces=('existing_liquid',))
    return out, record, original


@pytest.mark.parametrize('change', ['schema', 'empty_packet', 'nonempty_packet'])
def test_restore_modes_rejects_packet_record_before_operator_transition(legacy, change):
    _, record, original = legacy
    record = dict(record)
    if change == 'schema':
        record['schema'] = 'ordered_affine_packet_v1'
    else:
        record['packets'] = [] if change == 'empty_packet' else [{'members': [0]}]
    with pytest.raises(records.EventRecordError):
        records.restore_final_operator(original, record)
    assert original.interfaces == ('existing_liquid',)


def test_default_record_still_restores_its_modes(legacy):
    out, record, original = legacy
    restored = records.restore_final_operator(original, record)
    assert restored.interfaces == out.operator.interfaces


def test_result_subclass_is_not_silently_encoded_as_legacy(legacy):
    out, _, _ = legacy
    class PacketLikeResult(DepletionResult):
        pass
    packet = PacketLikeResult(**{f.name: getattr(out, f.name) for f in fields(out)})
    with pytest.raises(records.EventRecordError, match='explicit_depletion_result'):
        records.encode_depletion_result(packet, original_interfaces=('existing_liquid',))


def test_service_rejects_packet_policy_before_snapshot_or_integrator(tmp_path):
    from types import SimpleNamespace
    from sludge_sandbox.run_service import _run_event, RunError
    built = SimpleNamespace(depletion_policy=SimpleNamespace(ordered_event_policy='ordered_affine_packet_v1'))
    with pytest.raises(RunError, match='ordered_packet_service_codec_unavailable'):
        _run_event(built, {}, None, tmp_path, None)


def test_legacy_audit_rejects_packet_policy_even_without_events(legacy):
    from types import SimpleNamespace
    out, record, _ = legacy
    record = dict(record, events=[], corrections=[])
    with pytest.raises(records.EventRecordError, match='ordered_packet_record_audit_unavailable'):
        records.audit_depletion_record(record, out.states[0], None,
            SimpleNamespace(ordered_event_policy='ordered_affine_packet_v1'),
            ('existing_liquid',), operator=out.operator, start_s=0., end_s=.05)
