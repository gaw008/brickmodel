"""Pure endpoint/intermediate probes; never load Figure 2 facts or predict 500 C."""
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys

import pytest

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
sys.path.insert(0, str(ROOT/'src'))
from sludge_sandbox import cli
from sludge_sandbox import nowicki_oxidation as model

DATA = ROOT/'data/sandbox/research/nowicki2011-oxygen-interpolation-v1'


def reference_times(temperature):
    with localcontext() as context:
        context.prec = 70
        one, three = Decimal(1), Decimal(3)
        t = Decimal(str(temperature))+Decimal('273.15')
        w = (one/t-one/Decimal('723.15'))/(one/Decimal('823.15')-one/Decimal('723.15'))
        k = ((one-w)*Decimal('.00007044').ln()+w*Decimal('.00070611').ln()).exp()
        times = []
        for alpha in map(Decimal, ('.1', '.2', '.3', '.4', '.5', '.6', '.7', '.8')):
            # Newton cube root provides a different phi evaluation from log1p/expm1.
            cube = one-alpha
            root = one
            for _ in range(40):
                root = (2*root+cube/(root*root))/three
            times.append(float((one-root)/k))
        return float(k), times


@pytest.mark.parametrize('temperature', [450., 475., 525., 550.])
def test_prescribed_times_against_decimal_newton_reference(temperature, tmp_path):
    result = model.calculate_nowicki_oxygen_times(DATA, temperature_c=temperature)
    rate, times = reference_times(temperature)
    assert math.isclose(rate, result['model']['rate_s_inv'], rel_tol=2e-14)
    errors = [abs(row['time_s']-time) for row, time in zip(result['predictions'], times, strict=True)]
    assert max(errors) < 1e-6
    (tmp_path/'precision.json').write_text(json.dumps(dict(temperature_c=temperature, max_abs_time_error_s=max(errors)), indent=2)+'\n')
    for row in result['predictions']:
        assert row['time_s'] > 0 and row['coordinate_rate_s_inv'] > 0
        # Independent derivative of t(alpha): product must equal one.
        dt_da = (1-row['alpha_plot'])**(-2/3)/(3*result['model']['rate_s_inv'])
        assert math.isclose(dt_da*row['coordinate_rate_s_inv'], 1., rel_tol=1e-14)
    if temperature in (450., 550.):
        expected = .00007044 if temperature == 450. else .00070611
        assert result['model']['rate_s_inv'] == expected


@pytest.mark.parametrize('temperature', [449.999, 550.001, float('nan'), float('inf'), '-inf', True, None, 'x', '5'*129, 10**400])
def test_temperature_rejection(temperature):
    with pytest.raises(model.CharOxidationError):
        model.calculate_nowicki_oxygen_times(DATA, temperature_c=temperature)


@pytest.mark.parametrize('levels', [[], [.1]*65, [.09], [.81], [True], [None], ['nan'], ['inf'], ['bad'], [10**400], '.1', None])
def test_conversion_rejection(levels):
    with pytest.raises(model.CharOxidationError):
        model.calculate_nowicki_oxygen_times(DATA, temperature_c=450., conversion_levels=levels)


def test_trace_all_dependencies_resolve_and_qualification_is_not_balance():
    result = model.calculate_nowicki_oxygen_times(DATA, temperature_c=475., conversion_levels=['.8', '.1', '.8'])

    def resolve(path):
        node = result
        for key in path.split('.'):
            node = node[int(key)] if isinstance(node, list) else node[key]
        return node

    for output, definition in result['trace'].items():
        assert resolve(output) is not None
        for dependency in definition['dependencies']:
            assert resolve(dependency) is not None
        if 'source_id' in definition:
            assert definition['source_id'] == result['source']['id']
            assert 'source_locator' in definition or 'source_locators' in definition
    assert [p['alpha_plot'] for p in result['predictions']] == [.8, .1, .8]
    assert result['predictions'][0] == result['predictions'][2]
    qualification = result['qualification']
    assert qualification['oxygen_mole_fraction'] == float(result['conditions']['oxygen_mole_fraction']) == .1
    assert qualification['observations_loaded'] is False
    assert qualification['mass_or_molar_conversion_admitted'] is False
    assert qualification['reaction_heat'] is None and qualification['oxygen_consumption'] is None
    assert qualification['product_gas_stoichiometry'] is None
    assert 'Eq1' in qualification['response']
    json.dumps(result, allow_nan=False)


def copy_inputs(directory):
    for name in ('training.json', 'source_metadata.json'):
        (directory/name).write_bytes((DATA/name).read_bytes())


def test_only_two_frozen_files_opened_without_observation_file(monkeypatch, tmp_path):
    copy_inputs(tmp_path)
    seen = []
    original = model._read

    def tracked(path, expected):
        seen.append(path.name)
        return original(path, expected)

    monkeypatch.setattr(model, '_read', tracked)
    result = model.calculate_nowicki_oxygen_times(tmp_path, temperature_c=450.)
    assert seen == ['training.json', 'source_metadata.json']
    assert result['identity']['training_sha256'] == hashlib.sha256((tmp_path/'training.json').read_bytes()).hexdigest()
    assert result['identity']['source_metadata_sha256'] == hashlib.sha256((tmp_path/'source_metadata.json').read_bytes()).hexdigest()


@pytest.mark.parametrize('name', ['training.json', 'source_metadata.json'])
def test_changed_reviewed_bytes_rejected(tmp_path, name):
    copy_inputs(tmp_path)
    with (tmp_path/name).open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(model.CharOxidationError, match='changed'):
        model.calculate_nowicki_oxygen_times(tmp_path, temperature_c=450.)


def test_oversize_input_rejected(tmp_path):
    copy_inputs(tmp_path)
    (tmp_path/'training.json').write_bytes(b' '*65537)
    with pytest.raises(model.CharOxidationError, match='changed'):
        model.calculate_nowicki_oxygen_times(tmp_path, temperature_c=450.)


def test_fifo_rejected_without_waiting_for_writer(tmp_path):
    os.mkfifo(tmp_path/'training.json')
    previous = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(AssertionError('FIFO blocked')))
    signal.alarm(1)
    try:
        with pytest.raises(model.CharOxidationError, match='regular_training.json_required'):
            model.calculate_nowicki_oxygen_times(tmp_path, temperature_c=450.)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def test_python_cli_share_same_result_and_structured_failure(capsys):
    result = model.calculate_nowicki_oxygen_times(DATA, temperature_c='475', conversion_levels=['.1', '.8'])
    assert cli.main(['char-oxidation-times', '--source-data', str(DATA), '--temperature-c', '475', '--alpha-plot', '.1', '.8']) == 0
    assert json.loads(capsys.readouterr().out) == result
    assert cli.main(['char-oxidation-times', '--source-data', str(DATA), '--temperature-c', '449']) == 1
    failure = json.loads(capsys.readouterr().out)
    assert failure['status'] == 'failed' and failure['error_type'] == 'CharOxidationError'
    assert not any(name in sys.modules for name in ['CoolProp', 'sludge_sandbox.run_service', 'sludge_sandbox.source_trajectory'])
