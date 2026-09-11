"""Pure lifecycle seams; these tests neither construct nor invoke an EOS."""
from copy import deepcopy
from fractions import Fraction as F
import json
from types import SimpleNamespace

import pytest

from sludge_sandbox.integration import IntegrationError
from sludge_sandbox.source_run_service import (
    run_source_case, _Recorder, _managed_operation, _managed_request,
    _SourceWorkflowBudgetStop,
)
from sludge_sandbox.source_trajectory import open_source_trajectory


@pytest.mark.parametrize('value', [None, 0, 1, 'true'])
@pytest.mark.parametrize('entry', ['run', 'trajectory'])
def test_explicit_managed_flag_is_strict_bool_before_io(tmp_path, entry, value):
    output = tmp_path / 'must-not-exist'
    with pytest.raises(IntegrationError, match='managed_execution_must_be_bool'):
        if entry == 'run':
            run_source_case(tmp_path / 'missing', tmp_path, output, managed_execution=value)
        else:
            open_source_trajectory(tmp_path / 'missing', output, end=None, managed_execution=value)
    assert not output.exists()


def test_managed_entry_rejected_before_case_io_or_construction(tmp_path):
    with pytest.raises(Exception, match='dedicated_isolated_worker_required'):
        run_source_case(tmp_path / 'missing', tmp_path, tmp_path / 'out', managed_execution=True)
    assert not (tmp_path / 'out').exists()


@pytest.fixture
def lease_seam(monkeypatch):
    """Replace only bootstrap/close/audit; no scientific operator is made."""
    import sludge_sandbox._heos_rhs_scope as scope
    import sludge_sandbox.source_run_config as config
    monkeypatch.setattr(config, 'WORKFLOW_PROFILE',
                        'source_multicell_wet_to_dry_heos_workflow_v3', raising=False)
    current = dict(leases=[], active=None, closed=[], deadline=[], admission_cost=0., clock=None,
                   close_error=None, audit_error=None, admission_error=None, close_cost=0.)

    def admit(adapter, *, deadline_monotonic):
        assert current['active'] is None
        if current['admission_error'] is not None:
            raise current['admission_error']
        if current['clock'] is not None:
            current['clock'][0] += current['admission_cost']
        lease = SimpleNamespace(adapter=adapter, closed=False, records=[])
        current['leases'].append(lease)
        current['deadline'].append(deadline_monotonic)
        current['active'] = lease
        return lease

    def close(lease):
        assert current['active'] is lease
        lease.closed = True
        current['active'] = None
        current['closed'].append(lease)
        if current['clock'] is not None:
            current['clock'][0] += current['close_cost']
        if current['close_error'] is not None:
            raise current['close_error']

    def audit(lease):
        if current['audit_error'] is not None:
            raise current['audit_error']
        return deepcopy(dict(mode='manufactured_lifecycle_seam_only', closed=lease.closed,
                             rhs=lease.records, material_qualified=False))

    monkeypatch.setattr(scope, '_require_workflow_entry', lambda: None)
    monkeypatch.setattr(scope, '_admit_workflow_worker', admit)
    monkeypatch.setattr(scope, '_close_worker', close)
    monkeypatch.setattr(scope, '_worker_audit', audit)
    return current


def recorder_at(tmp_path, cancel=None):
    recorder = _Recorder(tmp_path, cancel, 0.)
    recorder.phase = 'pure_lifecycle_test'
    return recorder


def test_default_operation_never_admits_or_writes_audit(tmp_path, lease_seam):
    recorder = recorder_at(tmp_path)
    with _managed_operation(recorder, object(), enabled=False, deadline_monotonic=1.):
        assert lease_seam['active'] is None
    assert lease_seam['leases'] == [] and recorder.managed_audits == []
    assert recorder.journal.count == 0


def test_managed_profile_is_explicit(lease_seam):
    with pytest.raises(IntegrationError, match='workflow_profile_required'):
        _managed_request(True, SimpleNamespace(values={'profile': 'source_multicell_wet_to_dry_heos_v1'}))


def test_operation_audit_is_closed_and_saved_before_caller_publication(tmp_path, lease_seam):
    recorder = recorder_at(tmp_path)
    adapter = object()
    with _managed_operation(recorder, adapter, enabled=True, deadline_monotonic=73.):
        assert lease_seam['active'].adapter is adapter
        lease_seam['active'].records.append({'status': 'verified', 'native_operations': 0})
    assert lease_seam['active'] is None
    assert lease_seam['deadline'] == [73.]
    saved = recorder.managed_audits[0]
    assert saved['status'] == 'closed' and saved['audit']['closed']
    assert saved['audit']['rhs'] == [{'status': 'verified', 'native_operations': 0}]
    lease_seam['leases'][0].records.clear()
    assert saved['audit']['rhs']
    assert [json.loads(p.read_bytes())['event'] for p in sorted(recorder.journal.directory.glob('*.json'))] == [
        'managed_lease_started', 'managed_lease_closed']


@pytest.mark.parametrize('failure', ['body', 'admission', 'close', 'audit', 'journal'])
def test_all_failure_positions_close_and_retain_evidence(tmp_path, lease_seam, monkeypatch, failure):
    recorder = recorder_at(tmp_path)
    original = ValueError('original ' + failure)
    if failure in ('admission', 'close', 'audit'):
        lease_seam[failure + '_error'] = original
    if failure == 'journal':
        append = recorder.journal.append
        def write(event, value):
            if event == 'managed_lease_closed':
                raise original
            return append(event, value)
        monkeypatch.setattr(recorder.journal, 'append', write)
    with pytest.raises(ValueError) as caught:
        with _managed_operation(recorder, object(), enabled=True, deadline_monotonic=100.):
            if failure == 'body':
                raise original
    assert caught.value is original
    assert lease_seam['active'] is None
    assert len(lease_seam['closed']) == (0 if failure == 'admission' else 1)
    assert recorder.managed_audits[0]['status'] == 'failed'
    if failure not in ('admission', 'audit'):
        assert recorder.managed_audits[0]['audit']['closed']


def test_original_exception_wins_over_close_audit_and_publication_errors(tmp_path, lease_seam, monkeypatch):
    recorder = recorder_at(tmp_path)
    primary = KeyboardInterrupt('original stop')
    lease_seam['close_error'] = RuntimeError('close')
    lease_seam['audit_error'] = ValueError('audit')
    append = recorder.journal.append
    def write(event, value):
        if event == 'managed_lease_closed':
            raise OSError('journal')
        return append(event, value)
    monkeypatch.setattr(recorder.journal, 'append', write)
    with pytest.raises(KeyboardInterrupt) as caught:
        with _managed_operation(recorder, object(), enabled=True, deadline_monotonic=100.):
            raise primary
    assert caught.value is primary
    assert len(primary.__notes__) == 3
    assert [x['stage'] for x in recorder.managed_audits[0]['secondary_errors']] == ['close', 'audit', 'journal']
    assert lease_seam['active'] is None


@pytest.mark.parametrize('exception,status', [(_SourceWorkflowBudgetStop('common 97 cap'), 'resource_limit'),
                                           (ValueError('broken callback'), 'failed')])
def test_shared_budget_signal_is_not_user_cancel_or_broken_callback(tmp_path, exception, status):
    def cancel():
        raise exception
    recorder = recorder_at(tmp_path, cancel)
    assert recorder.cancelled()
    assert recorder.stop_status == status
    if status == 'resource_limit':
        assert recorder.stop_reason == 'common 97 cap' and recorder.cancel_error is None
    else:
        assert recorder.cancel_error is exception


@pytest.fixture
def pure_session(tmp_path, lease_seam, monkeypatch):
    """Actual exact integrator with manufactured rates and a lifecycle-only host.

    This bypasses source reconstruction/identity preflight explicitly. It cannot
    be used as source/EOS evidence; the operator is the existing exact test case.
    """
    import sludge_sandbox.source_trajectory as trajectory
    import sludge_sandbox.source_run_service as service
    from sludge_sandbox.exact_event_clock import ExactEventTime as T
    from test_exact_integration import initial, policy, rates, audit
    clock = [100.]
    lease_seam['clock'] = clock
    monkeypatch.setattr(trajectory, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(service, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    recorder = _Recorder(tmp_path, None, clock[0])
    recorder.limits = {'outer_seconds': 500.}
    recorder.counts['rhs_started'] = recorder.counts['rhs_returned'] = 3
    session = trajectory.SourceTrajectorySession()
    session.managed_execution = True
    session.recorder, session.begin = recorder, clock[0]
    session.initial, session.policy = initial(), policy()
    session.reference_policy = session.policy
    session.start, session.end = T(F()), T(3 * F(session.policy.initial_step_s))
    session.parent_elapsed_seconds = 10.
    session.parent_counts = tuple(sorted(recorder.counts.items()))
    session.record = SimpleNamespace(sha256='manufactured-lifecycle-parent')
    session.selected_candidate_index = 1
    session.checkpoint = session.last_result = session.last_execution = None
    session.closed, session.balances = False, ()
    session.last_counts = tuple(sorted(recorder.counts.items()))
    session._last_managed_audits = trajectory._snapshot(())
    session._continuation_state = (None, None, False)
    session._check = lambda: None

    def balance(reference):
        audit(reference, session.policy)
        return ('manufactured exact ledger audit',)
    session._audit = balance
    actual_calls = []

    class Operator:
        def breakpoints(self, start, end):
            return ()

        def __call__(self, state, when):
            assert (lease_seam['active'] is not None) is session.managed_execution
            actual_calls.append(when)
            recorder.counts['rhs_started'] += 1
            answer = rates(state)
            recorder.counts['rhs_returned'] += 1
            if session.managed_execution:
                lease_seam['active'].records.append({'status': 'manufactured_operator_return'})
            return answer

    session.adapter = Operator()
    return session, clock, actual_calls


def test_pause_closes_lease_resume_renews_and_passive_replay_does_not_add_rhs(pure_session, lease_seam):
    session, clock, calls = pure_session
    lease_seam['admission_cost'] = .25
    first = session.advance(pause_after_steps=1)
    assert first.status == 'paused' and len(first.execution.result.steps) == 1
    assert lease_seam['active'] is None and len(lease_seam['closed']) == 1
    assert first.execution.result.elapsed_seconds >= .25
    first_count = len(calls)
    first.execution.checkpoint.check()
    assert len(calls) == first_count
    clock[0] += 2.
    second = session.advance()
    assert second.status == 'completed' and second.execution.result.times_s[-1] == session.end
    assert lease_seam['active'] is None and len(lease_seam['closed']) == 2
    assert lease_seam['leases'][0] is not lease_seam['leases'][1]
    assert lease_seam['deadline'] == [590., 590.]
    assert len(calls) == second.execution.result.evaluations == 22
    assert dict(second.counts)['rhs_started'] == 3 + len(calls)
    assert second.execution.result.elapsed_seconds >= 2.5
    assert second.cumulative_outer_seconds == 12.5
    assert len(first.managed_audits) == 1 and len(second.managed_audits) == 2
    assert all(item['audit']['closed'] for item in second.managed_audits)
    assert not any(value is lease for value in vars(session).values() for lease in lease_seam['leases'])


@pytest.mark.parametrize('failure', ['close', 'audit', 'journal'])
def test_late_failure_retains_actual_committed_execution_and_disables_resume(
        pure_session, lease_seam, monkeypatch, failure):
    session, _, calls = pure_session
    original = OSError('late ' + failure)
    if failure in ('close', 'audit'):
        lease_seam[failure + '_error'] = original
    else:
        append = session.recorder.journal.append
        def write(event, payload):
            if event == 'managed_lease_closed':
                raise original
            return append(event, payload)
        monkeypatch.setattr(session.recorder.journal, 'append', write)
    with pytest.raises(OSError) as caught:
        session.advance(pause_after_steps=1)
    assert caught.value is original and session.last_failure is original
    assert session.last_execution.result.steps and session.last_execution.observations
    assert len(calls) == 8
    assert session.checkpoint is None and session.closed
    events = [json.loads(p.read_bytes()) for p in session.recorder.journal.directory.glob('*.json')]
    saved = next(e for e in events if e['event'] == 'ordinary_segment_failed')['payload']
    fields = saved['nodes'][saved['root']['ref']]['fields']
    assert fields['execution'] is not None
    with pytest.raises(IntegrationError, match='not_resumable'):
        session.advance()


def test_default_trajectory_does_not_admit_lease(pure_session, lease_seam):
    session, _, calls = pure_session
    session.managed_execution = False
    result = session.advance()
    assert result.status == 'completed' and len(calls) == 22
    assert lease_seam['leases'] == [] and result.managed_audits == ()


def test_paused_audit_cannot_be_cleared_before_new_operation(pure_session, lease_seam):
    session, _, _ = pure_session
    session.advance(pause_after_steps=1)
    session.recorder.managed_audits.clear()
    with pytest.raises(IntegrationError, match='managed_audit_changed'):
        session.advance()
    assert len(lease_seam['leases']) == 1


def test_close_cost_keeps_original_segment_wall_cap_and_retains_prefix(pure_session, lease_seam):
    session, _, _ = pure_session
    lease_seam['close_cost'] = session.policy.maximum_wall_seconds
    result = session.advance(pause_after_steps=1)
    assert result.status == 'resource_limit'
    assert result.reason == 'source_trajectory_original_segment_wall_limit'
    assert result.execution.result.steps and result.execution.observations
    assert session.checkpoint is None and session.closed
    assert result.cumulative_outer_seconds == 10. + session.policy.maximum_wall_seconds


def test_parent_failure_closes_before_real_record_encoding_and_binds_audit(tmp_path, lease_seam, monkeypatch):
    """Replace assembly/execution only; use the real failure record encoder."""
    import sludge_sandbox.source_run_service as service
    import sludge_sandbox.source_run_builder as builder
    import sludge_sandbox.source_run_config as config_module
    from sludge_sandbox.integration import DomainExit
    from sludge_sandbox.run_service import read_run, _seal, RunError
    from sludge_sandbox.source_study_record import decode_source_study
    from test_source_run_service import CASE
    config = SimpleNamespace(values={'resources': {'outer_seconds': 500.}, 'assets': [],
        'profile': config_module.WORKFLOW_PROFILE}, sha256='c'*64, canonical_bytes=b'{}')
    monkeypatch.setattr(config_module, 'load_source_run_config', lambda raw: config)
    monkeypatch.setattr(config_module, 'validate_source_run_assets',
                        lambda *args, **kw: SimpleNamespace(root=tmp_path, sha256='a'*64))
    observed = []
    def build(*args):
        assert lease_seam['active'] is None
        observed.append('build_outside_lease')
        return SimpleNamespace(adapter=SimpleNamespace(provenance=lambda: {}))
    monkeypatch.setattr(builder, 'build_source_run', build)
    primary = DomainExit('original manufactured execution failure')
    def execute(built, recorder, configuration):
        assert lease_seam['active'] is not None
        observed.append('operation_has_lease')
        raise primary
    monkeypatch.setattr(service, '_execute', execute)
    encode = service.encode_source_study
    def encoding(*args, **kwargs):
        assert lease_seam['active'] is None
        observed.append('record_encoding_outside_lease')
        return encode(*args, **kwargs)
    monkeypatch.setattr(service, 'encode_source_study', encoding)
    lease_seam['close_error'] = OSError('secondary manufactured close failure')
    output = tmp_path / 'parent'
    result = run_source_case(CASE, tmp_path, output, managed_execution=True)
    assert result['status'] == 'domain_exit' and result['reason'] == str(primary)
    assert observed == ['build_outside_lease', 'operation_has_lease', 'record_encoding_outside_lease']
    assert result['managed_audits'][0]['audit']['closed']
    assert result['managed_audits'][0]['secondary_errors'][0]['stage'] == 'close'
    assert result['counts']['heos_started'] == result['counts']['rhs_started'] == 0
    record = decode_source_study((output / service.RECORD).read_bytes())
    assert record.metadata['managed_execution'] is True
    assert record.metadata['managed_audits'][0]['audit']['closed']
    assert read_run(output)[0] == result
    result['managed_audits'][0]['audit']['closed'] = False
    (output / 'result.json').write_text(json.dumps(result))
    _seal(output)
    with pytest.raises(RunError, match='managed_audit_binding_changed'):
        read_run(output)
