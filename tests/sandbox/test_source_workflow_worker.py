"""Data admission, real counter accounting and deadline seams; zero EOS."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import sludge_sandbox.source_workflow_worker as worker
import sludge_sandbox._heos_rhs_scope as scope
from sludge_sandbox.source_run_service import _Recorder
from sludge_sandbox.source_run_journal import SourceRunJournal
from sludge_sandbox.water_properties import WaterSourceError


def request():
    return dict(schema='source_workflow_request_v1', operation='fresh_parent_three_step_comparison',
        case_path='/tmp/case.json', assets_root='/tmp/assets', output='/tmp/output',
        cancel_file='disabled', material_qualified=False, segment=dict(duration_numerator=3,
        duration_denominator=64, step_numerator=1, step_denominator=64, pause_after_steps=1))


def test_original_three_step_data_request():
    value = request()
    assert worker._load_request(json.dumps(value).encode()) == value


@pytest.mark.parametrize('key,value', [('operation', 'run_python'), ('material_qualified', True),
    ('case_path', 'relative'), ('output', '/tmp/a\x00b'), ('cancel_file', 'relative')])
def test_reject_request_before_native_import(key, value):
    data = request()
    data[key] = value
    with pytest.raises(ValueError):
        worker._load_request(json.dumps(data).encode())


@pytest.mark.parametrize('key,value', [('duration_numerator', 2), ('step_denominator', 32),
    ('pause_after_steps', True), ('pause_after_steps', 2), ('step_numerator', 1.0)])
def test_cannot_weaken_original_gate(key, value):
    data = request()
    data['segment'][key] = value
    with pytest.raises(ValueError):
        worker._load_request(json.dumps(data).encode())


@pytest.mark.parametrize('raw', [b'{}', b' ' * 65537, b'{"a":1,"a":2}', b'{"python":"pass"}'])
def test_request_is_closed_bounded_json(raw):
    with pytest.raises(ValueError):
        worker._load_request(raw)


def test_plain_import_is_not_managed_admission():
    with pytest.raises(RuntimeError, match='isolated_module_process_required'):
        worker._require_isolated_entry()
    with pytest.raises(WaterSourceError, match='dedicated_isolated_worker_required'):
        scope._require_workflow_entry()


def budget(monkeypatch):
    monkeypatch.setattr(worker.time, 'monotonic', lambda: 100.)
    return worker._WorkflowBudget(10., dict(outer_seconds=510., total_callback_cap=97,
                                          wet_pressure_request_cap=16), '')


def test_actual_counts_parent_once_and_no_double_charge_on_pause(monkeypatch):
    b = budget(monkeypatch)
    assert b.counts() is None
    b.parent = dict(counts=dict(rhs_started=32, wet_started=8, heos_started=4))
    continuous = SimpleNamespace(recorder=SimpleNamespace(counts=dict(rhs_started=54, wet_started=8, heos_started=8)))
    paused = SimpleNamespace(recorder=SimpleNamespace(counts=dict(rhs_started=40, wet_started=8, heos_started=8)))
    b.sessions.extend((continuous, paused))
    assert b.counts() == dict(rhs_started=62, wet_started=8, heos_started=12)
    paused.recorder.counts['rhs_started'] = 54
    assert b.counts() == dict(rhs_started=76, wet_started=8, heos_started=12)
    assert b.cancel() is False


@pytest.mark.parametrize('reason,counts,now', [
    ('combined_outer_seconds', dict(rhs_started=0, wet_started=0), 520.),
    ('combined_total_callback_cap', dict(rhs_started=97, wet_started=0), 100.),
    ('combined_wet_pressure_request_cap', dict(rhs_started=0, wet_started=16), 100.)])
def test_common_budget_is_resource_stop_not_user_cancel(monkeypatch, tmp_path, reason, counts, now):
    b = budget(monkeypatch)
    b.parent = dict(counts=counts)
    monkeypatch.setattr(worker.time, 'monotonic', lambda: now)
    recorder = _Recorder(tmp_path, b.cancel, 10.)
    assert recorder.cancelled() is True
    assert recorder.stop_status == 'resource_limit' and recorder.stop_reason == reason
    assert recorder.cancel_error is None


def test_user_cancel_file_has_separate_sticky_status(monkeypatch, tmp_path):
    b = budget(monkeypatch)
    path = tmp_path / 'cancel'
    b.cancel_file = str(path)
    assert b.cancel() is False
    path.touch()
    assert b.cancel() is True and b.user_requested and b.stop_reason is None
    path.unlink()
    assert b.cancel() is True


def test_partial_constructor_failure_retains_saved_actual_counts(tmp_path):
    journal = SourceRunJournal(tmp_path)
    counts = dict(heos_started=6, heos_kernel_returned=5, heos_returned=5, rhs_started=32)
    journal.append('source_trajectory_admission_failed', dict(exception=RuntimeError('native failed'), counts=counts))
    assert worker._partial_admission_counts(tmp_path) == counts


def test_missing_partial_failure_journal_is_unknown_not_zero(tmp_path):
    SourceRunJournal(tmp_path).append('heos_started', {})
    assert worker._partial_admission_counts(tmp_path) is None


@pytest.fixture
def workflow_clock(monkeypatch):
    monkeypatch.setattr(scope, '_require_entry', lambda names: None)
    monkeypatch.setattr(scope, '_workflow_deadline', None)
    monkeypatch.setattr(scope, '_worker', None)
    monkeypatch.setattr(scope, '_active', None)
    monkeypatch.setattr(scope, 'monotonic', lambda: 10.)


def test_deadline_fixed_once_and_admission_clamped(workflow_clock, monkeypatch):
    calls = []
    monkeypatch.setattr(scope, '_admit_worker', lambda adapter, **kw: calls.append(kw) or 'lease')
    scope._configure_workflow_deadline(100.)
    with pytest.raises(WaterSourceError, match='already_configured'):
        scope._configure_workflow_deadline(200.)
    assert scope._admit_workflow_worker(object(), deadline_monotonic=200.) == 'lease'
    assert calls[-1]['deadline_monotonic'] == 100.
    scope._admit_workflow_worker(object(), deadline_monotonic=50.)
    assert calls[-1]['deadline_monotonic'] == 50.
    scope._clear_workflow_deadline()
    with pytest.raises(WaterSourceError, match='deadline_unavailable'):
        scope._require_workflow_entry()


def test_deadline_cannot_clear_active_lease(workflow_clock, monkeypatch):
    scope._configure_workflow_deadline(100.)
    monkeypatch.setattr(scope, '_worker', object())
    with pytest.raises(WaterSourceError, match='cannot_clear_active'):
        scope._clear_workflow_deadline()


@pytest.mark.parametrize('value', [True, 10., float('inf'), float('nan')])
def test_deadline_must_be_finite_future_float(workflow_clock, value):
    with pytest.raises(WaterSourceError, match='finite_future_deadline'):
        scope._configure_workflow_deadline(value)


def test_wrong_thread_rejected_before_managed_constructor(workflow_clock, monkeypatch):
    scope._configure_workflow_deadline(100.)
    monkeypatch.setattr(scope, 'current_thread', lambda: object())
    with pytest.raises(WaterSourceError, match='synchronous_main_thread'):
        scope._require_workflow_entry()


def test_new_workflow_changes_only_runtime_identity():
    from sludge_sandbox.source_run_config import load_source_run_config, required_source_assets, WORKFLOW_PROFILE
    from sludge_sandbox.heos_runtime_registry import WORKFLOW_MANIFEST_ASSET
    root = Path(__file__).resolve().parents[2]
    original = json.loads((root / 'data/sandbox/cases/source-nonstationary-heos-v2.json').read_bytes())
    raw = (root / 'data/sandbox/cases/source-nonstationary-heos-workflow-v4.json').read_bytes()
    config = load_source_run_config(raw)
    config.check()
    new = json.loads(raw)
    assert new['profile'] == WORKFLOW_PROFILE
    assert required_source_assets(WORKFLOW_PROFILE)[10] == WORKFLOW_MANIFEST_ASSET
    assert [i for i, (a, b) in enumerate(zip(new['assets'], original['assets'])) if a != b] == [10]
    new['profile'], new['assets'] = original['profile'], original['assets']
    assert new == original


def test_current_workflow_manifest_sources_and_native_constants():
    from sludge_sandbox.heos_runtime_registry import WORKFLOW_MANIFEST_ASSET, RHS_MANIFEST_ASSET
    root = Path(__file__).resolve().parents[2]
    raw = (root / WORKFLOW_MANIFEST_ASSET[0]).read_bytes()
    assert (len(raw), hashlib.sha256(raw).hexdigest()) == WORKFLOW_MANIFEST_ASSET[1:]
    new = json.loads(raw)
    old = json.loads((root / RHS_MANIFEST_ASSET[0]).read_bytes())
    for name, sha in new.pop('execution_sources').items():
        assert hashlib.sha256((root / 'src/sludge_sandbox' / name).read_bytes()).hexdigest() == sha
    old.pop('execution_sources')
    assert new.pop('execution_contract') == 'isolated_fresh_parent_and_per_advance_lease_workflow_v1'
    old.pop('execution_contract')
    assert new == old


@pytest.mark.parametrize('failure_kind', ['native', 'cancel', 'journal_missing', 'resource'])
def test_worker_open_failure_reports_real_partial_work(monkeypatch, tmp_path, failure_kind):
    """Run the worker control flow with a failed constructor seam, no EOS."""
    from fractions import Fraction
    import sludge_sandbox.run_service as runs
    import sludge_sandbox.source_run_service as service
    import sludge_sandbox.source_trajectory as trajectory
    from sludge_sandbox.exact_event_clock import ExactEventTime
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setattr(worker, '_require_isolated_entry', lambda: None)
    monkeypatch.setattr(scope, '_configure_workflow_deadline', lambda value: None)
    monkeypatch.setattr(scope, '_clear_workflow_deadline', lambda: None)
    monkeypatch.setattr(runs, 'runtime_identity', lambda: {'test': 'pure-control-seam'})
    original = dict(heos_started=4, heos_kernel_returned=4, heos_returned=4,
        initial_energy_started=3, initial_energy_returned=3, rhs_started=32,
        rhs_returned=32, wet_started=8, wet_returned=8)
    parent = dict(status='completed', numerical_event_accepted=True, counts=original)
    monkeypatch.setattr(service, 'run_source_case', lambda *args, **kwargs: parent)
    record = SimpleNamespace(roots={'transition': SimpleNamespace(candidates=[None,
        SimpleNamespace(end=ExactEventTime(Fraction(1, 1000000)))])})
    monkeypatch.setattr(runs, 'read_run_with_source_record', lambda path: (parent, None, record))
    value = request()
    value.update(case_path=str(root / 'data/sandbox/cases/source-nonstationary-heos-workflow-v4.json'),
                 output=str(tmp_path / 'output'), cancel_file=str(tmp_path / 'cancel'))
    expected = dict(original, heos_started=6, heos_kernel_returned=5, heos_returned=5)
    error = RuntimeError('actual failed construction seam')

    def opening(parent_dir, output, **kwargs):
        output.mkdir()
        journal = SourceRunJournal(output)
        callback = kwargs['cancel']
        if failure_kind == 'cancel':
            Path(value['cancel_file']).touch()
            assert callback() is True
        if failure_kind == 'resource':
            callback.__self__.stop_reason = 'combined_outer_seconds'
        if failure_kind != 'journal_missing':
            journal.append('source_trajectory_admission_failed', dict(exception=error, counts=expected))
        raise error

    monkeypatch.setattr(trajectory, 'open_source_trajectory', opening)
    path = tmp_path / 'request.json'
    path.write_text(json.dumps(value))
    with pytest.raises(RuntimeError) as caught:
        worker._execute_request(path)
    assert caught.value is error
    failure = json.loads((tmp_path / 'output/FAILURE.json').read_bytes())
    assert failure['status'] == {'cancel': 'cancelled', 'resource': 'resource_limit'}.get(failure_kind, 'failed')
    assert failure['total_known_actual_counts'] == (original if failure_kind == 'journal_missing' else expected)
    assert failure['count_completeness'] == ('unknown_or_lower_bound' if failure_kind == 'journal_missing'
                                           else 'complete_observed_counts')
    assert failure['material_qualified'] is False
    assert not (tmp_path / 'output/ACCEPTANCE.json').exists()
