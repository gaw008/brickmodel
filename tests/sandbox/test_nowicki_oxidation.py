"""Source-condition math, truthful response scope, and CLI/Python alignment."""
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path
import shutil

import pytest
from scipy.integrate import quad

from sludge_sandbox.nowicki_oxidation import CharOxidationError, calculate_nowicki_oxygen_times

DATA = Path(__file__).resolve().parents[2]/'data/sandbox/research/nowicki2011-oxygen-interpolation-v1'


@pytest.mark.parametrize('temperature,expected', [(450, .00007044), (550, .00070611)])
def test_original_endpoint_slopes_are_preserved(temperature, expected):
    result = calculate_nowicki_oxygen_times(DATA, temperature_c=temperature)
    assert result['model']['rate_s_inv'] == expected
    assert result['conditions']['oxygen_mole_fraction'] == '0.1'
    assert result['qualification']['table3_A_or_concentration_power_used'] is False


def test_interpolation_and_times_match_independent_high_precision_and_quadrature():
    result = calculate_nowicki_oxygen_times(DATA)
    # Solve the 2x2 line coefficients using Decimal, not the binary64 weighted formula.
    with localcontext() as context:
        context.prec = 60
        t0, t1, t = map(Decimal, ('723.15', '823.15', '773.15'))
        k0, k1 = map(Decimal, ('.00007044', '.00070611'))
        slope = (k1.ln()-k0.ln())/(1/t1-1/t0)
        intercept = k0.ln()-slope/t0
        rate = (intercept+slope/t).exp()
        assert abs(result['model']['rate_s_inv']-float(rate)) < 1e-16
        for row in result['predictions']:
            alpha = Decimal(str(row['alpha_plot']))
            expected = (1-((1-alpha).ln()/3).exp())/rate
            assert abs(row['time_s']-float(expected)) < 1e-6
            integral, error = quad(lambda a: 1/(3*float(rate)*(1-a)**(2/3)),
                                   0, float(alpha), epsabs=1e-8, epsrel=1e-12)
            assert abs(row['time_s']-integral) < max(1e-7, 4*error)
            assert row['coordinate_rate_s_inv'] > 0


def test_increasing_levels_give_increasing_times_without_mass_or_energy_claims():
    result = calculate_nowicki_oxygen_times(DATA)
    times = [r['time_s'] for r in result['predictions']]
    assert all(a < b for a,b in zip(times,times[1:]))
    qualification = result['qualification']
    assert qualification['reaction_heat'] is None
    assert qualification['oxygen_consumption'] is None
    assert not qualification['mass_or_molar_conversion_admitted']
    assert not qualification['experimental_validation_performed']
    assert not qualification['full_firing_cycle']
    assert result['uncertainty']['parameter_confidence_interval'] is None


@pytest.mark.parametrize('temperature', [True, None, 'NaN', 'inf', 449.99, 550.01, '500 C'])
def test_source_temperature_domain_is_not_silently_extended(temperature):
    with pytest.raises(CharOxidationError):
        calculate_nowicki_oxygen_times(DATA, temperature_c=temperature)


@pytest.mark.parametrize('levels', [[], [.09], [.81], [True], ['NaN'], None, '.1', [.1]*65])
def test_levels_reject_invalid_or_unbounded_responses(levels):
    with pytest.raises(CharOxidationError):
        calculate_nowicki_oxygen_times(DATA, conversion_levels=levels)


def test_only_training_and_metadata_are_read_and_altered_training_is_rejected(tmp_path):
    for name in ('training.json', 'source_metadata.json'):
        shutil.copyfile(DATA/name, tmp_path/name)
    # No facts.json or original PDF is present: the held-out curve is not a dependency.
    result = calculate_nowicki_oxygen_times(tmp_path)
    assert result['qualification']['observations_loaded'] is False
    path = tmp_path/'training.json'
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(CharOxidationError, match='training.json'):
        calculate_nowicki_oxygen_times(tmp_path)


def test_trace_dependencies_resolve_to_real_result_paths():
    result = calculate_nowicki_oxygen_times(DATA)
    for target, entry in result['trace'].items():
        for path in [target, *entry['dependencies']]:
            value = result
            for token in path.split('.'):
                value = value[int(token)] if isinstance(value,list) else value[token]
            assert value is not None
    assert result['source']['sha256'] == 'b1970f72bb595e31c67276860886545d337130587991a88d8c321c6d25aebb23'


def test_cli_is_same_python_calculation_and_rejects_outside_domain(capsys):
    from sludge_sandbox.cli import main
    args = ['char-oxidation-times', '--source-data', str(DATA),
            '--temperature-c', '500', '--alpha-plot', '.1', '.8']
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out) == calculate_nowicki_oxygen_times(
        DATA, conversion_levels=[.1,.8])
    assert main(['char-oxidation-times', '--source-data', str(DATA), '--temperature-c', '600']) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'
