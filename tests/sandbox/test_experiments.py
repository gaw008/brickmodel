"""Experiment orchestration tests; synthetic records are not physics evidence."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest

from sludge_sandbox import experiments as ex

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT/'data/sandbox/experiments/wet-transport-comparison-v1.json'


@pytest.fixture
def prepared(tmp_path):
    water = tmp_path/'water'
    water.mkdir()
    (water/'fixture.json').write_text('{}')
    spec = json.loads(SPEC.read_text())
    path = tmp_path/'spec.json'
    path.write_text(json.dumps(spec))
    directory = tmp_path/'experiment'
    ex.prepare_experiment(path, directory, water_directory=water)
    return directory


def save(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def supervisor(monkeypatch):
    """Deterministic orchestration clock and sealed records, without native EOS."""
    clock = SimpleNamespace(value=10.0)
    monkeypatch.setattr(ex, 'time', SimpleNamespace(monotonic=lambda: clock.value))
    calls = []

    def run(operation, source, directory, policy, **kwargs):
        calls.append((operation, source, policy))
        directory.mkdir()
        run_dir = directory/'run'
        run_dir.mkdir()
        experiment = directory.parent.parent
        case_raw = (source/'case.json' if source.is_dir() else source).read_bytes()
        (run_dir/'case.json').write_bytes(case_raw)
        frozen = json.loads((experiment/'inputs/runtime.json').read_text())
        (run_dir/'equation_catalog.json').write_bytes(
            (Path(ex.__file__).parent/'catalogs/wet-slab-equations-v1.json').read_bytes())
        for name in ('water', 'evidence'):
            for path in (experiment/'inputs'/name).rglob('*'):
                if path.is_file():
                    target = run_dir/name/path.relative_to(experiment/'inputs'/name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(path.read_bytes())
        for name in frozen['modules']:
            target = run_dir/'implementation'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((Path(ex.__file__).parent/name).read_bytes())
        initial = {'amounts_mol': [[2, 0, 1, 2, .001], [2, 0, 3, 4, .001]],
                   'internal_energy_j': [10, 20]}
        final = {'amounts_mol': [[2, 0, 1, 1, .001], [2, 0, 2, 4, .001]],
                 'internal_energy_j': [12, 21]}
        save(run_dir/'result.json', {'case_sha256': hashlib.sha256(case_raw).hexdigest(),
             'runtime_before': frozen, 'runtime_after': frozen, 'status': 'completed',
             'integration': {'states': [initial, final]},
             'final_snapshot': {'temperature_k': [300, 302], 'pressure_pa': [100, 110]}})
        files = {p.relative_to(run_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in run_dir.rglob('*') if p.is_file()}
        save(run_dir/'manifest.json', {'schema': 'sandbox_run_manifest_v1', 'files': files})
        clock.value += 2
        save(directory/'job.json', {'schema': 'sandbox_job_v1', 'job_id': str(uuid.uuid4()),
             'operation': operation, 'status': 'completed', 'reason': None,
             'elapsed_wall_seconds': 2.0, 'child_reaped': True, 'returncode': 0, 'pid': 123})
    monkeypatch.setattr(ex, 'supervise', run)
    return calls, clock


@pytest.mark.parametrize('raw', [b'{"schema":1,"schema":2}', b'{"x":NaN}', b'{"x":1e999}'])
def test_invalid_json_rejected_before_output(tmp_path, raw):
    path = tmp_path/'spec'
    path.write_bytes(raw)
    with pytest.raises(ex.ExperimentError):
        ex.prepare_experiment(path, tmp_path/'out', water_directory=tmp_path)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('change', ['duplicate_id', 'unknown_field', 'bool_budget', 'real_material'])
def test_spec_contract(tmp_path, change):
    spec = json.loads(SPEC.read_text())
    if change == 'duplicate_id':
        spec['candidates'][1]['id'] = spec['candidates'][0]['id']
    elif change == 'unknown_field':
        spec['extra'] = 1
    elif change == 'bool_budget':
        spec['budget']['maximum_jobs'] = True
    else:
        spec['mode'] = 'evidence_supported'
    path = tmp_path/'spec'
    save(path, spec)
    with pytest.raises(ex.ExperimentError) as error:
        ex.prepare_experiment(path, tmp_path/'out', water_directory=tmp_path)
    if change == 'real_material':
        assert error.value.code == 'evidence_incomplete'


def test_original_sources_do_not_change_frozen_experiment(prepared):
    (prepared.parent/'water/fixture.json').write_text('{"changed":true}')
    assert ex.read_experiment(prepared)['status'] == 'prepared'
    assert (prepared/'inputs/water/fixture.json').read_text() == '{}'


@pytest.mark.parametrize('mutation', ['edit', 'add', 'runtime'])
def test_changed_inputs_refused_before_dispatch(prepared, monkeypatch, mutation):
    monkeypatch.setattr(ex, 'supervise', lambda *a, **k: pytest.fail('dispatched'))
    if mutation == 'runtime':
        monkeypatch.setattr(ex, 'runtime_identity', lambda: {})
    elif mutation == 'add':
        (prepared/'inputs/new.json').write_text('{}')
    else:
        (prepared/'inputs/water/fixture.json').write_text('changed')
    with pytest.raises(ex.ExperimentError):
        ex.run_experiment(prepared)


def test_queue_cancel_then_continue_never_repeats_completed(prepared, supervisor):
    calls, clock = supervisor
    first = ex.run_experiment(prepared, cancel=lambda: len(calls) == 1)
    assert first['status'] == 'paused'
    assert [c['status'] for c in first['candidates']] == ['completed', 'pending']
    assert first['charged_wall_seconds'] == 2
    clock.value += 1000  # Idle time must not consume active compute budget.
    second = ex.run_experiment(prepared)
    assert second['status'] == 'completed'
    assert len(calls) == len(second['attempts']) == 2
    assert second['charged_wall_seconds'] == 4
    assert len({str(call[1]) for call in calls}) == 2
    comparison = ex.compare_experiment(prepared)
    assert not comparison['material_qualified']
    for item in comparison['outcomes']:
        assert item['metrics'] == {'final_temperature_span_k': 2,
            'maximum_final_pressure_pa': 110, 'final_total_water_mol': 8,
            'change_total_water_mol': -2, 'final_total_internal_energy_j': 33,
            'change_total_internal_energy_j': 3}
        assert len(item['result_sha256']) == 64


def test_comparison_rejects_modified_result(prepared, supervisor):
    ex.run_experiment(prepared)
    result = next((prepared/'jobs').glob('*/run/result.json'))
    result.write_text('{}')
    comparison = ex.compare_experiment(prepared)
    bad = [item for item in comparison['outcomes'] if item['outcome'] == 'unverified_result']
    assert len(bad) == 1 and bad[0]['metrics'] is None


def test_cancel_request_is_consumed_once(prepared, supervisor):
    calls, clock = supervisor
    request = ex.request_experiment_cancel(prepared)
    assert request['status'] == 'request_recorded_not_cancellation_confirmation'
    # Real elapsed preflight time is positive; model it without call-count magic.
    original = ex.runtime_identity
    def identity():
        clock.value += .01
        return original()
    from unittest.mock import patch
    with patch.object(ex, 'runtime_identity', identity):
        assert ex.run_experiment(prepared)['status'] == 'paused'
        assert not calls
        assert ex.run_experiment(prepared)['status'] == 'completed'
    assert len(calls) == 2


def test_running_journal_refuses_without_pid_inference(prepared, supervisor):
    path = prepared/'state.json'
    state = json.loads(path.read_text())
    state['invocations'] = [{'id': str(uuid.uuid4()), 'status': 'running', 'elapsed_seconds': None}]
    save(path, state)
    with pytest.raises(ex.ExperimentError, match='unverified_interruption'):
        ex.run_experiment(prepared)
    assert not supervisor[0]


def test_experiment_lock_refuses_second_owner(prepared, supervisor):
    with ex._lock(prepared):
        with pytest.raises(ex.ExperimentError, match='experiment_already_owned'):
            ex.run_experiment(prepared)
    assert not supervisor[0]


def prepare_budget(tmp_path, **budget):
    spec = json.loads(SPEC.read_text())
    spec['budget'].update(budget)
    path = tmp_path/'limited.json'
    save(path, spec)
    water = tmp_path/'water'
    water.mkdir()
    directory = tmp_path/'limited'
    ex.prepare_experiment(path, directory, water_directory=water)
    return directory


def test_attempt_budget_cannot_reset_on_continuation(tmp_path, supervisor):
    directory = prepare_budget(tmp_path, maximum_jobs=1)
    first = ex.run_experiment(directory)
    assert first['status'] == 'resource_limit'
    second = ex.run_experiment(directory)
    assert second['status'] == 'resource_limit'
    assert len(supervisor[0]) == len(second['attempts']) == 1
    assert second['candidates'][0]['status'] == 'completed'
    assert second['candidates'][1]['status'] == 'pending'


def test_total_budget_debits_previous_invocation(tmp_path, supervisor):
    directory = prepare_budget(tmp_path, maximum_total_wall_seconds=8)
    calls, clock = supervisor
    first = ex.run_experiment(directory, cancel=lambda: len(calls) == 1)
    assert first['charged_wall_seconds'] == 2
    ex.run_experiment(directory)
    # Remaining 6 seconds must reserve 5 seconds grace, leaving only 1 work second.
    assert calls[1][2].maximum_wall_seconds == 1


def test_final_accounting_overrun_is_not_completed(tmp_path, supervisor, monkeypatch):
    directory = prepare_budget(tmp_path, maximum_total_wall_seconds=8)
    original = ex.supervise
    def delayed(*args, **kwargs):
        original(*args, **kwargs)
        supervisor[1].value += 10
    monkeypatch.setattr(ex, 'supervise', delayed)
    result = ex.run_experiment(directory)
    assert result['status'] == 'resource_limit'
    assert result['reason'] == 'total_wall_budget_exceeded'
    assert result['charged_wall_seconds'] == 12
    assert result['candidates'][0]['status'] == 'completed'
    assert len(supervisor[0]) == 1


def test_invalid_candidate_does_not_block_valid_candidates(tmp_path, supervisor):
    spec = json.loads(SPEC.read_text())
    spec['candidates'][0]['case']['model_id'] = 'unknown_material'
    path = tmp_path/'spec'
    save(path, spec)
    water = tmp_path/'water'
    water.mkdir()
    directory = tmp_path/'experiment'
    prepared = ex.prepare_experiment(path, directory, water_directory=water)
    assert prepared['candidates'][0]['status'] == 'not_runnable'
    result = ex.run_experiment(directory)
    assert len(supervisor[0]) == 1
    assert result['candidates'][1]['status'] == 'completed'
    comparison = ex.compare_experiment(directory)
    assert comparison['outcomes'][0]['metrics'] is None


@pytest.mark.parametrize('status', ['paused', 'resource_limit', 'failed'])
def test_cli_reports_noncompletion(monkeypatch, capsys, prepared, status):
    from sludge_sandbox.cli import main
    monkeypatch.setattr(ex, 'run_experiment', lambda *a, **kw: {'status': status})
    assert main(['experiment-run', str(prepared)]) == 1
    assert json.loads(capsys.readouterr().out)['status'] == status


@pytest.mark.parametrize('value', [{}, None, [], {'schema': 'sandbox_experiment_state_v1'}])
def test_malformed_journal_is_controlled_error(prepared, value):
    save(prepared/'state.json', value)
    with pytest.raises(ex.ExperimentError, match='malformed_experiment_record'):
        ex.read_experiment(prepared)


def test_catalog_must_match_frozen_runtime_even_after_run_resealed(prepared, supervisor):
    ex.run_experiment(prepared)
    run_dir = next((prepared/'jobs').glob('*/run'))
    (run_dir/'equation_catalog.json').write_text('{}')
    manifest_path = run_dir/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['files']['equation_catalog.json'] = hashlib.sha256(b'{}').hexdigest()
    save(manifest_path, manifest)
    bad = [item for item in ex.compare_experiment(prepared)['outcomes']
           if item['outcome'] == 'unverified_result']
    assert len(bad) == 1
    assert bad[0]['reason'] == 'result_catalog_mismatch'


def test_accepted_cancelled_prefix_dispatches_resume(prepared, supervisor, monkeypatch):
    original = ex.supervise
    def cancel_first(operation, source, directory, policy, **kwargs):
        original(operation, source, directory, policy, **kwargs)
        if len(supervisor[0]) != 1:
            return
        job_path = directory/'job.json'
        job = json.loads(job_path.read_text())
        job['status'] = 'cancelled'
        job['returncode'] = 1
        save(job_path, job)
        run_dir = directory/'run'
        result_path = run_dir/'result.json'
        result = json.loads(result_path.read_text())
        result['status'] = 'cancelled'
        result['integration'].update(status='cancelled', reason='cancel_requested', steps=[{'fixture': True}])
        save(result_path, result)
        manifest_path = run_dir/'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['files']['result.json'] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        save(manifest_path, manifest)
    monkeypatch.setattr(ex, 'supervise', cancel_first)
    first = ex.run_experiment(prepared)
    assert first['status'] == 'paused'
    second = ex.run_experiment(prepared)
    assert second['status'] == 'completed'
    assert [call[0] for call in supervisor[0]] == ['run', 'resume', 'run']
    assert second['attempts'][1]['parent_attempt_id'] == first['attempts'][0]['id']
    assert second['charged_wall_seconds'] == 6
    # This proves dispatch only; checkpoint service owns physical prefix validation.


def test_budget_overrun_preserves_original_exception(prepared, supervisor, monkeypatch):
    def failed(*a, **kw):
        supervisor[1].value += 101
        raise RuntimeError('specific_failure')
    monkeypatch.setattr(ex, 'supervise', failed)
    result = ex.run_experiment(prepared)
    assert result['status'] == 'resource_limit'
    assert result['outcome_before_budget_check'] == {'status': 'failed', 'reason': 'specific_failure'}
