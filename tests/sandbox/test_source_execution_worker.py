"""Closed worker requests and actual cross-process comparison debits; no EOS."""
import json
from pathlib import Path

import pytest

from sludge_sandbox import source_execution_worker as worker
from sludge_sandbox.source_run_service import _Recorder, _SourceWorkflowBudgetStop
from sludge_sandbox.source_run_observer import observer_scope


def request(operation='source-resume'):
    value = dict(schema='source_execution_request_v1', operation=operation,
        source='/tmp/saved', output='/tmp/output', cancel_file='disabled', shared_budget=None)
    if operation == 'source-run':
        value['assets_root'] = '/tmp/assets'
    else:
        value['pause_after_steps'] = 0
    if operation == 'source-advance':
        value.update(end=dict(numerator=3, denominator=64),
            step_sizes=dict(initial_step_s=1/64, maximum_step_s=1/64, rationale='Original step policy.'))
    return value


def shared(**costs):
    counts = dict.fromkeys(worker.COUNTERS, 0)
    counts.update(costs)
    return dict(other_counts=counts, outer_remaining_seconds=400., total_callback_cap=97,
                wet_pressure_request_cap=16)


@pytest.mark.parametrize('operation', ['source-run', 'source-advance', 'source-resume'])
def test_separate_operations_admit_only_data(operation):
    value = request(operation)
    assert worker._load_request(json.dumps(value).encode()) == value


@pytest.mark.parametrize('change', [dict(operation='python'), dict(source='relative'),
    dict(output='/tmp/\x00bad'), dict(cancel_file='relative'), dict(pause_after_steps=True),
    dict(pause_after_steps=-1), dict(end={'numerator': 5, 'denominator': 6}),
    dict(policy={'maximum_wall_seconds': 1000.}), dict(source_resume_authorized=True)])
def test_resume_cannot_replace_problem_or_grant_authority(change):
    value = request()
    value.update(change)
    with pytest.raises(ValueError):
        worker._load_request(json.dumps(value).encode())


@pytest.mark.parametrize('raw', [b'{}', b'[]', b' ' * 65537, b'{"a":1,"a":2}',
    b'{"x":NaN}', b'{"x":' + b'1' * 101 + b'}'])
def test_bounded_closed_request(raw):
    with pytest.raises(ValueError):
        worker._load_request(raw)


@pytest.mark.parametrize('field,value', [('end', dict(numerator=2, denominator=4)),
    ('end', dict(numerator=1, denominator=0)),
    ('step_sizes', dict(initial_step_s=1., maximum_step_s=0.1, rationale='Invalid.')),
    ('step_sizes', dict(initial_step_s=float('inf'), maximum_step_s=1., rationale='Invalid.'))])
def test_advance_exact_clock_and_step_validation(field, value):
    data = request('source-advance'); data[field] = value
    with pytest.raises(ValueError):
        worker._load_request(json.dumps(data).encode())


def test_shared_counts_cannot_hide_returns_or_relax_caps():
    value = request(); value['shared_budget'] = shared(rhs_returned=1)
    with pytest.raises(ValueError, match='shared_counts_order'):
        worker._load_request(json.dumps(value).encode())
    value['shared_budget'] = shared()
    value['shared_budget']['total_callback_cap'] = 98
    with pytest.raises(ValueError, match='shared_budget_range'):
        worker._load_request(json.dumps(value).encode())


def budget(monkeypatch, tmp_path, other=None):
    monkeypatch.setattr(worker.time, 'monotonic', lambda: 100.)
    return worker._ExecutionBudget(10., dict(outer_seconds=510., total_callback_cap=97,
        wet_pressure_request_cap=16), str(tmp_path / 'cancel'), other)


def test_resume_lineage_and_other_branch_counted_once(monkeypatch, tmp_path):
    b = budget(monkeypatch, tmp_path, shared(rhs_started=22, rhs_returned=22, heos_started=4,
        heos_kernel_returned=4, heos_returned=4))
    assert b.counts() is None
    recorder = _Recorder(tmp_path, b.cancel, 10.)
    recorder.counts.update(rhs_started=40, rhs_returned=40, heos_started=12,
        heos_kernel_returned=12, heos_returned=12, wet_started=8, wet_returned=8)
    with observer_scope(recorder):
        assert b.cancel() is False
        assert b.combined_counts()['rhs_started'] == 62
        assert b.combined_counts()['heos_started'] == 16
        recorder.counts['rhs_started'] += 14
        recorder.counts['rhs_returned'] += 14
    assert b.combined_counts()['rhs_started'] == 76
    assert b.counts()['rhs_started'] == 54


def test_partial_construction_counts_survive_observer_exit(monkeypatch, tmp_path):
    b = budget(monkeypatch, tmp_path)
    recorder = _Recorder(tmp_path, b.cancel, 10.)
    recorder.limits = b.limits
    with observer_scope(recorder):
        recorder('heos_started', provider='first')
        recorder('heos_kernel_returned', provider='first')
        recorder('heos_returned', provider='first')
        recorder('heos_started', provider='second')
    assert b.counts()['heos_started'] == 2
    assert b.counts()['heos_returned'] == 1


@pytest.mark.parametrize('kind', ['rhs', 'wet'])
def test_prior_other_cost_blocks_next_real_start(monkeypatch, tmp_path, kind):
    key = kind + '_started'
    b = budget(monkeypatch, tmp_path, shared(**{key: 7}))
    recorder = _Recorder(tmp_path, b.cancel, 10.)
    recorder.limits = b.limits
    cap = 97 if kind == 'rhs' else 16
    recorder.counts[key] = cap - 7
    with observer_scope(recorder):
        assert recorder.cancelled() is True
    assert recorder.stop_status == 'resource_limit'
    assert recorder.counts[key] == cap - 7


def test_other_cost_alone_can_exhaust_before_recorder(monkeypatch, tmp_path):
    b = budget(monkeypatch, tmp_path, shared(rhs_started=97))
    with pytest.raises(_SourceWorkflowBudgetStop):
        b.cancel()
    assert b.counts() is None


def test_wall_debit_and_sticky_cancellation_are_distinct(monkeypatch, tmp_path):
    b = budget(monkeypatch, tmp_path)
    path = tmp_path / 'cancel'; path.touch()
    assert b.cancel() is True
    path.unlink()
    assert b.cancel() is True
    b = budget(monkeypatch, tmp_path, shared())
    monkeypatch.setattr(worker.time, 'monotonic', lambda: 410.)
    with pytest.raises(_SourceWorkflowBudgetStop, match='wall_limit'):
        b.cancel()
    assert b.user_requested is False


def test_plain_import_has_no_native_authority():
    with pytest.raises(RuntimeError, match='isolated_module_process_required'):
        worker._require_isolated_entry()


def test_failure_before_native_admission_is_saved(monkeypatch, tmp_path):
    monkeypatch.setattr(worker, '_require_isolated_entry', lambda: None)
    value = request(); value['source'] = str(tmp_path / 'missing')
    value['output'] = str(tmp_path / 'output')
    path = tmp_path / 'request.json'; path.write_text(json.dumps(value))
    with pytest.raises(FileNotFoundError):
        worker._execute_request(path)
    failure = json.loads((Path(value['output']) / 'FAILURE.json').read_text())
    assert failure['status'] == 'failed'
    assert failure['counts'] is None and failure['count_completeness'] == 'unknown'
    assert not (Path(value['output']) / 'OUTCOME.json').exists()


def test_versioned_resume_profile_keeps_original_physics():
    from sludge_sandbox.source_run_config import load_source_run_config, required_source_assets, RESUME_PROFILE
    from sludge_sandbox.heos_runtime_registry import RESUME_MANIFEST_ASSET
    root = Path(__file__).resolve().parents[2]
    raw = (root/'data/sandbox/cases/source-nonstationary-heos-resume-v5.json').read_bytes()
    value = json.loads(raw)
    original = json.loads((root/'data/sandbox/cases/source-nonstationary-heos-v2.json').read_bytes())
    load_source_run_config(raw).check()
    assert value['profile'] == RESUME_PROFILE
    assert required_source_assets(RESUME_PROFILE)[10] == RESUME_MANIFEST_ASSET
    assert [i for i,(a,b) in enumerate(zip(value['assets'],original['assets'])) if a!=b] == [10]
    value['profile'],value['assets'] = original['profile'],original['assets']
    assert value == original


def test_current_resume_manifest_records_actual_implementation():
    import hashlib
    from sludge_sandbox.heos_runtime_registry import RESUME_MANIFEST_ASSET, WORKFLOW_MANIFEST_ASSET
    root=Path(__file__).resolve().parents[2]
    raw=(root/RESUME_MANIFEST_ASSET[0]).read_bytes()
    assert (len(raw),hashlib.sha256(raw).hexdigest()) == RESUME_MANIFEST_ASSET[1:]
    current=json.loads(raw)
    historical=json.loads((root/WORKFLOW_MANIFEST_ASSET[0]).read_bytes())
    sources=current.pop('execution_sources')
    assert {'source_execution_worker.py','source_trajectory_record.py'} <= sources.keys()
    for name,digest in sources.items():
        assert hashlib.sha256((root/'src/sludge_sandbox'/name).read_bytes()).hexdigest()==digest
    historical.pop('execution_sources')
    assert current.pop('execution_contract')=='isolated_source_execution_and_persistent_ordinary_resume_v1'
    historical.pop('execution_contract')
    assert current==historical
