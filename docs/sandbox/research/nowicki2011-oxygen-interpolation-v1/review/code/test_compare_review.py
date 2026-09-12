"""Manufactured comparison checks; no actual prediction or figure facts read."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[2]/'compare.py'
spec = importlib.util.spec_from_file_location('review_compare', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def manufactured():
    levels = [i/10 for i in range(1, 9)]
    errors = [-3., -2., -1., 0., 1., 2., 3., 4.]
    prediction = dict(schema='nowicki_oxygen_times_result_v1', temperature_c=500.,
        predictions=[dict(alpha_plot=alpha, time_s=i*10+error)
                     for i, (alpha, error) in enumerate(zip(levels, errors, strict=True), start=1)],
        model=dict(rate_s_inv=.002))
    facts = dict(observations=[dict(alpha_plot=alpha, time_s=i*10,
                 time_bounds_s=[i*10-2, i*10+2], locator='manufactured')
                 for i, alpha in enumerate(levels, start=1)])
    table = [dict(gas='O2', temperature_C='500', model='shrinking_core',
                  gas_mole_fraction='0.1', rate_constant_s_inv='.004')]
    return prediction, facts, table


def test_metrics_closed_intervals_and_secondary_constant_are_separate():
    result = module.compare(*manufactured())
    assert [p['residual_s'] for p in result['points']] == [-3., -2., -1., 0., 1., 2., 3., 4.]
    assert [p['outside_interval_s'] for p in result['points']] == [1., 0., 0., 0., 0., 0., 1., 2.]
    assert result['overall'] == dict(n=8, mae_s=2., rmse_s=math.sqrt(5.5),
        max_abs_s=4., bias_s=.5, inside_reading_intervals=5)
    secondary = result['secondary_author_fitted_constant']
    assert secondary['relative_difference'] == -.5
    assert secondary['residual_s_inv'] == -.002
    assert secondary['used_for_prediction'] is False
    assert result['qualification']['material_acceptance_threshold'] is None
    assert result['qualification']['new_blind_holdout'] is False


@pytest.mark.parametrize('fault', ['wrong_temperature', 'shuffled_prediction', 'shuffled_observation', 'missing_level', 'inverted_interval', 'nan_interval', 'duplicate_secondary'])
def test_declared_pairing_and_intervals_are_required(fault):
    prediction, facts, table = manufactured()
    if fault == 'wrong_temperature':
        prediction['temperature_c'] = 450.
    elif fault == 'shuffled_prediction':
        prediction['predictions'].reverse()
    elif fault == 'shuffled_observation':
        facts['observations'].reverse()
    elif fault == 'missing_level':
        prediction['predictions'].pop()
    elif fault == 'inverted_interval':
        facts['observations'][0]['time_bounds_s'] = [12., 8.]
    elif fault == 'nan_interval':
        facts['observations'][0]['time_bounds_s'][0] = float('nan')
    else:
        table.append(table[0].copy())
    with pytest.raises(ValueError):
        module.compare(prediction, facts, table)


def fixture_files(tmp_path, monkeypatch):
    prediction, facts, table = manufactured()
    table_raw = (','.join(table[0])+'\n'+','.join(table[0].values())+'\n').encode()
    prediction['training'] = dict(upstream_table_csv=dict(sha256=hashlib.sha256(table_raw).hexdigest()))
    prediction_raw, facts_raw = json.dumps(prediction).encode(), json.dumps(facts).encode()
    paths = {key: tmp_path/(key+'.json') for key in ('prediction', 'facts', 'table', 'output')}
    paths['prediction'].write_bytes(prediction_raw)
    paths['facts'].write_bytes(facts_raw)
    paths['table'].write_bytes(table_raw)
    monkeypatch.setattr(module, 'FACTS_SHA256', hashlib.sha256(facts_raw).hexdigest())
    argv = ['compare', '--prediction', str(paths['prediction']), '--prediction-sha256', hashlib.sha256(prediction_raw).hexdigest(),
            '--facts', str(paths['facts']), '--table', str(paths['table']), '--output', str(paths['output'])]
    monkeypatch.setattr(sys, 'argv', argv)
    return paths


@pytest.mark.parametrize('changed', ['prediction', 'facts', 'table'])
def test_manifest_changes_prevent_output(tmp_path, monkeypatch, changed):
    paths = fixture_files(tmp_path, monkeypatch)
    paths[changed].write_bytes(paths[changed].read_bytes()+b' ')
    with pytest.raises(ValueError, match='changed'):
        module.main()
    assert not paths['output'].exists()


def test_new_output_and_existing_output_is_preserved(tmp_path, monkeypatch):
    paths = fixture_files(tmp_path, monkeypatch)
    module.main()
    raw = paths['output'].read_bytes()
    report = json.loads(raw)
    assert report['overall']['inside_reading_intervals'] == 5
    assert report['inputs']['comparison_script_sha256'] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        module.main()
    assert paths['output'].read_bytes() == raw
