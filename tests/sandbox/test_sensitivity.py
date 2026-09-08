"""Factorial design contracts; no synthetic response is physical validation."""
import copy
import json
from pathlib import Path

import pytest

from sludge_sandbox import sensitivity as sensitivity

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT/'data/sandbox/sensitivity/initial-temperature-contrast-v1.json'


@pytest.fixture
def spec():
    return json.loads(SPEC.read_text())


def prepare(tmp_path, spec):
    path = tmp_path/'spec.json'
    path.write_text(json.dumps(spec))
    water = tmp_path/'water'
    water.mkdir(exist_ok=True)
    (water/'fixture.json').write_text('{}')
    output = tmp_path/'design'
    returned = sensitivity.prepare_sensitivity(path, output, water_directory=water)
    return output, returned


@pytest.mark.parametrize('change', ['mode', 'numerics', 'classification', 'units', 'duplicate', 'same', 'bool', 'unknown', 'inactive'])
def test_invalid_design_refused(tmp_path, spec, change):
    factor = spec['factors'][0]
    if change == 'mode':
        spec['mode'] = 'evidence_supported'
    elif change == 'numerics':
        factor['path'] = '/refinement'
    elif change == 'classification':
        factor['classification'] = 'measured_public_data'
    elif change == 'units':
        factor['units'] = 'Celsius'
    elif change == 'duplicate':
        spec['factors'].append(copy.deepcopy(factor))
    elif change == 'same':
        factor['high'] = factor['low']
    elif change == 'bool':
        factor['low'] = True
    elif change == 'unknown':
        factor['extra'] = 'ignored?'
    else:
        spec['baseline_case']['profile'] = 'uniform'
    with pytest.raises(ValueError):
        prepare(tmp_path, spec)


def test_design_changes_only_requested_scalar(tmp_path, spec):
    directory, returned = prepare(tmp_path, spec)
    generated = json.loads((directory/'generated-experiment.json').read_text())
    assert len(generated['candidates']) == 2
    assert generated['budget'] == spec['budget']
    for candidate, value in zip(generated['candidates'], [300, 300.5]):
        expected = copy.deepcopy(spec['baseline_case'])
        expected['initial']['parent_temperatures_k'][0] = value
        assert candidate['case'] == expected
    assert generated['candidates'][0]['id'] != generated['candidates'][1]['id']


def test_factorial_cartesian_endpoints(tmp_path, spec):
    spec['factors'].append({'id': 'cell1', 'path': '/initial/parent_temperatures_k/1',
        'low': 301, 'high': 302, 'units': 'K', 'classification': 'virtual_design_choice'})
    directory, _ = prepare(tmp_path, spec)
    generated = json.loads((directory/'generated-experiment.json').read_text())
    assert [item['case']['initial']['parent_temperatures_k'] for item in generated['candidates']] == [
        [300, 301], [300, 302], [300.5, 301], [300.5, 302]]
    assert len({item['id'] for item in generated['candidates']}) == 4


@pytest.mark.parametrize('filename', ['design.json', 'generated-experiment.json', 'design-manifest.json'])
def test_tampered_design_rejected(tmp_path, spec, filename):
    directory, _ = prepare(tmp_path, spec)
    (directory/filename).write_text('{}')
    with pytest.raises(ValueError):
        sensitivity.analyze_sensitivity(directory)


def test_unknown_candidate_values_retained(tmp_path, spec):
    spec['factors'][0]['high'] = 999
    directory, _ = prepare(tmp_path, spec)
    state = json.loads((directory/'experiment/state.json').read_text())
    assert [item['status'] for item in state['candidates']] == ['pending', 'not_runnable']
    assert state['candidates'][1]['classification'] == 'invalid_case'


def synthetic_responses(directory, values, *, missing=None):
    state = json.loads((directory/'experiment/state.json').read_text())
    outcomes = []
    for index, candidate in enumerate(state['candidates']):
        outcomes.append({'id': candidate['id'], 'case_sha256': candidate['case_sha256'],
            'outcome': 'failed' if index == missing else 'completed',
            'reason': 'test_failure' if index == missing else None,
            'result_sha256': None if index == missing else str(index)*64,
            'metrics': None if index == missing else {'final_temperature_span_k': values[index]}})
    return {'outcomes': outcomes}


def test_two_factor_main_contrasts_keep_interactions_in_average(tmp_path, spec, monkeypatch):
    spec['factors'].append({'id': 'cell1', 'path': '/initial/parent_temperatures_k/1',
        'low': 301, 'high': 302, 'units': 'K', 'classification': 'virtual_design_choice'})
    directory, _ = prepare(tmp_path, spec)
    # Independently constructed response Y=3*x+2*z+5*x*z, coded x,z=-1,+1.
    # Cartesian (-,-),(-,+),(+,-),(+,+) gives0,-6,-4,10.
    response = synthetic_responses(directory, [0, -6, -4, 10])
    monkeypatch.setattr(sensitivity, 'compare_experiment', lambda _: response)
    result = sensitivity.analyze_sensitivity(directory)
    assert [item['method'] for item in result['contrasts']] == ['averaged_factorial_contrast']*2
    metrics = [item['metrics']['final_temperature_span_k'] for item in result['contrasts']]
    assert [item['contrast'] for item in metrics] == [6, 4]
    assert [item['per_unit_slope'] for item in metrics] == [12, 4]
    assert all(item['required_candidates'] == 4 for item in metrics)
    assert all(item['metrics']['maximum_final_pressure_pa']['status'] == 'unknown'
               for item in result['contrasts'])


@pytest.mark.parametrize('missing', [0, 1])
def test_failed_endpoint_never_computes_success_subset(tmp_path, spec, monkeypatch, missing):
    directory, _ = prepare(tmp_path, spec)
    response = synthetic_responses(directory, [2, 5], missing=missing)
    monkeypatch.setattr(sensitivity, 'compare_experiment', lambda _: response)
    metric = sensitivity.analyze_sensitivity(directory)['contrasts'][0]['metrics']['final_temperature_span_k']
    assert metric['status'] == 'unknown'
    assert metric['contrast'] is metric['per_unit_slope'] is None
    assert metric['reasons'][0]['reason'] == 'test_failure'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True])
def test_invalid_response_is_unknown(tmp_path, spec, monkeypatch, value):
    directory, _ = prepare(tmp_path, spec)
    response = synthetic_responses(directory, [1, value])
    monkeypatch.setattr(sensitivity, 'compare_experiment', lambda _: response)
    metric = sensitivity.analyze_sensitivity(directory)['contrasts'][0]['metrics']['final_temperature_span_k']
    assert metric['status'] == 'unknown'
    assert metric['contrast'] is None


def test_substituted_comparison_case_refused(tmp_path, spec, monkeypatch):
    directory, _ = prepare(tmp_path, spec)
    response = synthetic_responses(directory, [1, 2])
    response['outcomes'][1]['case_sha256'] = 'wrong'
    monkeypatch.setattr(sensitivity, 'compare_experiment', lambda _: response)
    with pytest.raises(ValueError, match='comparison_case_binding_mismatch'):
        sensitivity.analyze_sensitivity(directory)


def test_unrun_experiment_reports_unknown_not_zero(tmp_path, spec):
    directory, _ = prepare(tmp_path, spec)
    result = sensitivity.analyze_sensitivity(directory)
    assert all(m['status'] == 'unknown' and m['contrast'] is None
               for m in result['contrasts'][0]['metrics'].values())


def test_cli_prepare_and_analyze_json(tmp_path, spec, capsys):
    from sludge_sandbox.cli import main
    directory, _ = prepare(tmp_path, spec)
    assert main(['sensitivity-analyze', str(directory)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == sensitivity.analyze_sensitivity(directory)


def test_three_factors_have_eight_distinct_cells(tmp_path, spec):
    spec['factors'] += [
        {'id': 'cell1', 'path': '/initial/parent_temperatures_k/1', 'low': 301, 'high': 302,
         'units': 'K', 'classification': 'virtual_design_choice'},
        {'id': 'rate', 'path': '/reaction/prefactor_mol_m3_s', 'low': .1, 'high': .2,
         'units': 'mol/(m3*s)', 'classification': 'manufactured_test_fixture'}]
    directory, returned = prepare(tmp_path, spec)
    generated = json.loads((directory/'generated-experiment.json').read_text())
    assert returned['candidate_count'] == 8
    points = {(tuple(c['case']['initial']['parent_temperatures_k']),
               c['case']['reaction']['prefactor_mol_m3_s']) for c in generated['candidates']}
    assert len(points) == 8


def test_float_identical_integer_levels_rejected(tmp_path, spec):
    spec['factors'][0].update(low=2**54, high=2**54+1)
    with pytest.raises(ValueError, match='levels_not_strictly_ordered_representable'):
        prepare(tmp_path, spec)


def test_overflow_contrast_is_unknown(tmp_path, spec, monkeypatch):
    directory, _ = prepare(tmp_path, spec)
    response = synthetic_responses(directory, [-1e308, 1e308])
    monkeypatch.setattr(sensitivity, 'compare_experiment', lambda _: response)
    metric = sensitivity.analyze_sensitivity(directory)['contrasts'][0]['metrics']['final_temperature_span_k']
    assert metric['status'] == 'unknown'
    assert metric['contrast'] is metric['per_unit_slope'] is None


def test_overflow_slope_is_unknown(tmp_path, spec, monkeypatch):
    spec['factors'] = [{'id': 'tiny', 'path': '/reaction/prefactor_mol_m3_s',
        'low': 1e-300, 'high': 2e-300, 'units': 'mol/(m3*s)',
        'classification': 'manufactured_test_fixture'}]
    directory, _ = prepare(tmp_path, spec)
    response = synthetic_responses(directory, [0, 1e300])
    monkeypatch.setattr(sensitivity, 'compare_experiment', lambda _: response)
    metric = sensitivity.analyze_sensitivity(directory)['contrasts'][0]['metrics']['final_temperature_span_k']
    assert metric['status'] == 'unknown'
    assert metric['contrast'] is metric['per_unit_slope'] is None


def test_analysis_implementation_is_recorded(tmp_path, spec):
    import hashlib
    directory, _ = prepare(tmp_path, spec)
    result = sensitivity.analyze_sensitivity(directory)
    assert result['analysis_implementation_sha256'] == hashlib.sha256(Path(sensitivity.__file__).read_bytes()).hexdigest()
    assert result['metric_provider_implementation_sha256'] == hashlib.sha256(
        Path(sensitivity.experiment_module.__file__).read_bytes()).hexdigest()
