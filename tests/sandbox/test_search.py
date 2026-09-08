"""Search lifecycle tests over synthetic sealed jobs; not material validation."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from sludge_sandbox import search
from sludge_sandbox import experiments
from test_experiments import supervisor  # Existing sealed-job/controlled-clock fixture.

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT/'data/sandbox/search/initial-temperature-search-v1.json'


@pytest.fixture
def spec():
    return json.loads(SPEC.read_text())


def prepare(tmp_path, spec):
    path = tmp_path/'spec.json'
    path.write_text(json.dumps(spec))
    water = tmp_path/'water'
    water.mkdir(exist_ok=True)
    directory = tmp_path/'search'
    returned = search.prepare_search(path, directory, water_directory=water)
    return directory, returned


@pytest.fixture
def backend(supervisor, monkeypatch):
    calls, clock = supervisor
    def monotonic():
        clock.value += .0001  # Positive deterministic orchestration overhead.
        return clock.value
    monkeypatch.setattr(experiments.time, 'monotonic', monotonic)
    monkeypatch.setattr(search, 'time', experiments.time)
    original = experiments.supervise
    def run(operation, source, directory, policy, **kwargs):
        original(operation, source, directory, policy, **kwargs)
        run_dir = directory/'run'
        case = json.loads((run_dir/'case.json').read_text())
        result_path = run_dir/'result.json'
        result = json.loads(result_path.read_text())
        # Declared analytic test objective abs(T1-T0); no EOS result is fabricated.
        result['final_snapshot']['temperature_k'] = case['initial']['parent_temperatures_k']
        result_path.write_text(json.dumps(result))
        manifest_path = run_dir/'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['files']['result.json'] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(experiments, 'supervise', run)
    return calls, clock


@pytest.mark.parametrize('change', ['mode', 'units', 'objective', 'constraint_classification', 'factor', 'policy'])
def test_invalid_search_contract(tmp_path, spec, change):
    if change == 'mode':
        spec['mode'] = 'evidence_supported'
    elif change == 'units':
        spec['objective']['units'] = 'MPa'
    elif change == 'objective':
        spec['objective']['metric'] = 'compressive_strength_mpa'
    elif change == 'constraint_classification':
        spec['constraints'][0]['classification'] = 'measured_public_data'
    elif change == 'factor':
        spec['factors'][0]['path'] = '/refinement'
    else:
        spec['policy']['contraction'] = 1.5
    with pytest.raises(ValueError):
        prepare(tmp_path, spec)


def test_initial_parent_outside_bounds_is_refused(tmp_path, spec):
    spec['factors'][0]['low'] = 300.5
    with pytest.raises(ValueError):
        prepare(tmp_path, spec)


def test_search_runs_two_generations(tmp_path, spec, backend):
    directory, _ = prepare(tmp_path, spec)
    state = search.run_search(directory)
    assert state['status'] == 'completed'
    assert len(state['generations']) == 2
    assert len(backend[0]) == 5
    # Two first-generation points, then parent and two half-step neighbours.
    values = []
    for _, source, _ in backend[0]:
        case = json.loads(source.read_text())
        values.append(case['initial']['parent_temperatures_k'][0])
    assert values[:2] == [300, 300.25]
    assert values[2] == 300.25
    assert set(values[3:]) == {300.125, 300.375}
    assert state['charged_wall_seconds'] >= 10


def test_all_constraints_infeasible_never_yields_material_failure(tmp_path, spec, backend):
    spec['constraints'][0]['value'] = 1
    directory, _ = prepare(tmp_path, spec)
    state = search.run_search(directory)
    assert len(backend[0]) == 2
    assert state['status'] != 'failed'
    assert not state.get('material_qualified', False)


def test_global_attempt_budget_cannot_reset_on_resume(tmp_path, spec, backend):
    spec['budget']['maximum_jobs'] = 2
    directory, _ = prepare(tmp_path, spec)
    first = search.run_search(directory)
    second = search.run_search(directory)
    assert len(backend[0]) == 2
    assert first['status'] == second['status'] == 'resource_limit'


def test_original_spec_change_does_not_mutate_search(tmp_path, spec):
    directory, prepared = prepare(tmp_path, spec)
    (tmp_path/'spec.json').write_text('{}')
    assert search.read_search(directory)['status'] == prepared['status']


def test_saved_best_cannot_be_changed_without_evidence(tmp_path, spec, backend):
    directory, _ = prepare(tmp_path, spec)
    result = search.run_search(directory)
    assert result['best'] is not None
    path = directory/'state.json'
    saved = json.loads(path.read_text())
    saved['best']['objective_value'] = -123456
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError):
        search.read_search(directory)


def test_cancel_and_continue_does_not_repeat_finished_candidates(tmp_path, spec, backend):
    directory, _ = prepare(tmp_path, spec)
    calls, clock = backend
    first = search.run_search(directory, cancel=lambda: len(calls) >= 2)
    assert first['status'] == 'paused'
    second = search.run_search(directory)
    assert second['status'] == 'completed'
    assert len(calls) == 5
    assert second['attempts_used'] == 5
    assert second['charged_wall_seconds'] >= first['charged_wall_seconds'] + 6


def test_no_improvement_preserves_parent_and_stops(tmp_path, spec, backend):
    # This objective is constant in the synthetic records, so no improvement can be invented.
    spec['objective'] = {'metric': 'final_total_water_mol', 'direction': 'minimize', 'units': 'mol'}
    spec['policy']['stagnation_generations'] = 1
    directory, _ = prepare(tmp_path, spec)
    result = search.run_search(directory)
    assert result['status'] == 'completed'
    assert len(result['generations']) == 1
    assert result['best']['factor_values'] == [300]


def test_negative_invocation_cannot_offset_positive_time(tmp_path, spec):
    directory, _ = prepare(tmp_path, spec)
    path = directory/'state.json'
    state = json.loads(path.read_text())
    state['invocations'] = [
        {'status': 'finished', 'elapsed_seconds': -1},
        {'status': 'finished', 'elapsed_seconds': 2},
    ]
    state['charged_wall_seconds'] = 1
    path.write_text(json.dumps(state))
    with pytest.raises(search.SearchError, match='invalid_invocation_elapsed_seconds'):
        search.run_search(directory)


def test_preparation_failure_survives_final_audit_failure(tmp_path, spec, backend, monkeypatch):
    directory, _ = prepare(tmp_path, spec)
    def fail(*args, **kwargs):
        raise OSError('source_read_failed')
    monkeypatch.setattr(search, 'prepare_experiment', fail)
    state = search.run_search(directory)
    assert state['status'] == 'failed'
    assert state['outcome_before_final_audit'] == {
        'status': 'failed', 'reason': 'source_read_failed', 'error_type': 'OSError'}


@pytest.mark.parametrize('state', [{}, {'invocations': [None]}])
def test_malformed_record_raises_controlled_error(tmp_path, spec, state):
    directory, _ = prepare(tmp_path, spec)
    path = directory/'state.json'
    original = json.loads(path.read_text())
    if state:
        original.update(state)
    else:
        original = state
    path.write_text(json.dumps(original))
    with pytest.raises(search.SearchError):
        search.run_search(directory)


def test_cli_noncompletion(tmp_path, monkeypatch, capsys):
    from sludge_sandbox.cli import main
    monkeypatch.setattr(search, 'run_search', lambda *a, **k: {'status': 'paused'})
    assert main(['search-run', str(tmp_path)]) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'paused'
