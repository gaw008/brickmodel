"""Independent arithmetic/adversarial saved-array tests; no time integration.

Every array is explicitly synthetic. Imports are limited to the comparison
module and ordinary Python/pytest utilities; the scientific driver is not
imported, and a synthetic 'completed' marker never becomes experiment evidence.
"""
import copy
from decimal import Decimal, localcontext
from fractions import Fraction
import importlib.util
import math
from pathlib import Path

import pytest

STUDY = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('independent_compare_target', STUDY / 'compare_spatial.py')
COMPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPARE)


def independent_reference():
    """Machin pi with an alternating remainder, unlike the target Chudnovsky."""
    with localcontext() as context:
        context.prec = 100
        def atan_inverse(n):
            x = Decimal(1) / n
            power = x
            total = Decimal(0)
            sign = 1
            for i in range(1000):
                term = power / (2 * i + 1)
                total += sign * term
                power *= x * x
                sign *= -1
                if abs(term) < Decimal('1e-105'):
                    return total
            raise AssertionError('bounded reference series did not finish')
        pi = 16 * atan_inverse(5) - 4 * atan_inverse(239)
        # Obtain the rationalized expression directly from the continuum
        # integral: I0=1/sqrt(d0²-d1²), Icos=(d0*I0-1)/d1.
        d0, d1 = Decimal(93960), Decimal(40)
        integral_inverse_ce = 1 / (d0 * d0 - d1 * d1).sqrt()
        integral_cosine_over_ce = (d0 * integral_inverse_ce - 1) / d1
        rate = -(pi / Decimal('.02')) ** 2 * 2 * integral_cosine_over_ce / (
            Decimal(100000) * integral_inverse_ce)
        return pi, rate


def synthetic_records():
    reference = float(independent_reference()[1])
    records, summaries, executions = {}, {}, {}
    for n in (16, 32, 64):
        x = math.pi / (2 * n)
        initial = [302 + 2 * (math.sin(x) / x) * math.cos(math.pi * (i + .5) / n) for i in range(n)]
        records[n] = {}
        for name, policy in COMPARE.POLICIES.items():
            samples, stresses = [], []
            for time in COMPARE.TIMES:
                t = [v + .005 * time / n**2 for v in initial]
                samples.append(t + [0.] * (2 * n + 1))
                mean = math.fsum(t) / n
                stresses.append([1e5 * (mean - value) for value in t])
            records[n][name] = dict(cells=n, policy_name=name, policy=copy.deepcopy(policy),
                status='completed', times_s=list(COMPARE.TIMES), samples=samples,
                reported_stress_pa=stresses, initial_temperatures_k=list(initial),
                initial_mean_rate=dict(temperature_rates_k_s=[reference + 1e-5 / n**2] * n),
                gates={key: True for key in ['completed_interval', 'all_dense_segments_in_domain',
                    'local_energy', 'global_energy', 'entropy']},
                material_qualified=False, source_material_qualified=False, real_time_integration=True)
        summaries[n] = dict(cells=n, status='completed', completed_policies=['coarse', 'fine'],
            coarse=dict(status='completed'), fine=dict(status='completed'),
            time_comparison=dict(passed=True), real_time_integration=True,
            scientific_validated=False, material_qualified=False, source_material_qualified=False)
        executions[n] = dict(cells=n, elapsed_s=1., passed=True, within_wall_limit=True,
            inputs_unchanged=True, child_reaped=True, timed_out=False, returncode=0)
    return records, summaries, executions


def test_continuous_reference_independent_pi_and_integral_form():
    pi, rate = independent_reference()
    actual = COMPARE.continuous_rate()
    assert abs(Decimal(actual['pi']) - pi) < Decimal('1e-77')
    assert abs(Decimal(actual['rate_k_s']) - rate) < Decimal('1e-80')
    assert rate < 0


def test_conservative_restriction_with_exact_fraction_oracle():
    row = [Fraction((-1)**i * i + i % 3, 8) for i in range(64)]
    actual = COMPARE.restrict([[float(v) for v in row]])[0]
    expected = [(row[i] + row[i + 1]) / 2 for i in range(0, 64, 2)]
    assert [Fraction(v) for v in actual] == expected
    assert sum(Fraction(v) for v in actual) / 32 == sum(row) / 64


def test_both_differences_are_on_sixteen_cells_with_correct_sign():
    fields = {16: [[16.] * 16], 32: [[float(i) for i in range(32)]],
              64: [[float(i) for i in range(64)]]}
    actual = COMPARE.pair_differences(fields)
    assert actual[16] == [[15.5 - 2 * i for i in range(16)]]
    assert actual[32] == [[-1. - 2 * i for i in range(16)]]


def test_norms_include_all_times_cells_and_the_frozen_scale():
    values = [[1., 3.] * 8 for _ in range(101)]
    result = COMPARE.norms(values)
    assert result['infinity'] == .75
    assert result['two'] == math.sqrt(5) / 4


def test_reported_stress_single_fine_cell_survives_both_restrictions():
    records, summaries, executions = synthetic_records()
    baseline = COMPARE.compare(records, summaries, executions)
    records[64]['fine']['reported_stress_pa'][50][0] += 1234.
    result = COMPARE.compare(records, summaries, executions)
    actual = result['spatial']['fine']['stress_normalized_differences'][32]['infinity']
    assert actual == pytest.approx(1234 / 4 / 400000, abs=2e-13)
    assert result['physical_summaries'][64]['fine']['max_reported_stress_reconstruction_residual_pa'] > 1233.
    assert result['spatial']['fine']['normalized_differences'] == baseline['spatial']['fine']['normalized_differences']
    # No stress-accuracy threshold was preregistered. This is deliberately a
    # diagnostic sentinel, not a scientific stress-validation success case.
    assert all('stress' not in key for key in result['gates'])


def test_fine_policy_is_not_replaced_by_better_coarse_order():
    records, summaries, executions = synthetic_records()
    for n in (16, 32, 64):
        record = records[n]['fine']
        for time, row in zip(COMPARE.TIMES, record['samples'], strict=True):
            row[:n] = [t + .005 * time / n for t in record['initial_temperatures_k']]
    result = COMPARE.compare(records, summaries, executions)
    assert result['spatial']['coarse']['norms']['infinity']['order'] == pytest.approx(2, abs=1e-6)
    assert result['spatial']['fine']['norms']['infinity']['order'] == pytest.approx(1, abs=1e-6)
    assert result['gates']['infinity_second_order'] is False
    assert result['status'] != 'passed'


def test_policy_name_swap_rejected():
    records, summaries, executions = synthetic_records()
    records[32]['coarse'], records[32]['fine'] = records[32]['fine'], records[32]['coarse']
    with pytest.raises(ValueError, match='identity'):
        COMPARE.compare(records, summaries, executions)


@pytest.mark.parametrize('mode', ['zero_rate_error', 'too_small_spatial_error'])
def test_unresolved_rate_or_spatial_error_cannot_pass(mode):
    records, summaries, executions = synthetic_records()
    for n in (16, 32, 64):
        if mode == 'zero_rate_error':
            records[n]['fine']['initial_mean_rate']['temperature_rates_k_s'] = [float(independent_reference()[1])] * n
        else:
            for record in records[n].values():
                for row in record['samples']:
                    row[:n] = record['initial_temperatures_k']
    result = COMPARE.compare(records, summaries, executions)
    assert result['status'] != 'passed'
    if mode == 'zero_rate_error':
        assert result['initial_rate_orders'] == [None, None]
        assert not result['gates']['N16_initial_mean_rate_resolved']
    else:
        assert result['spatial']['fine']['norms']['infinity']['order'] is None


@pytest.mark.parametrize('mutation', ['missing_dense_gate', 'unknown_entropy_gate',
    'summary_missing_fine', 'summary_failed_fine', 'summary_time_unknown',
    'summary_not_actual', 'policy_failed', 'supervision_unknown'])
def test_required_unknown_or_failed_evidence_cannot_pass(mutation):
    records, summaries, executions = synthetic_records()
    if mutation == 'missing_dense_gate':
        del records[32]['fine']['gates']['all_dense_segments_in_domain']
    elif mutation == 'unknown_entropy_gate':
        records[32]['fine']['gates']['entropy'] = None
    elif mutation == 'summary_missing_fine':
        summaries[32]['completed_policies'] = ['coarse']
    elif mutation == 'summary_failed_fine':
        summaries[32]['fine']['status'] = 'failed'
    elif mutation == 'summary_time_unknown':
        summaries[32]['time_comparison']['passed'] = None
    elif mutation == 'summary_not_actual':
        summaries[32]['real_time_integration'] = False
    elif mutation == 'policy_failed':
        records[32]['fine']['status'] = 'failed'
    else:
        del executions[32]['child_reaped']
    try:
        result = COMPARE.compare(records, summaries, executions)
    except ValueError:
        return
    assert result['status'] != 'passed'


def test_initial_projection_energy_is_not_forced_to_continuum():
    records, summaries, executions = synthetic_records()
    result = COMPARE.compare(records, summaries, executions)
    errors = []
    for n in (16, 32, 64):
        fields = result['physical_summaries'][n]['fine']
        errors.append(fields['initial_projection_difference_j'])
        assert fields['initial_projection_difference_j'] > 0
        assert abs(fields['initial_energy_formula_residual_j']) < 1e-10
        assert fields['initial_continuum_energy_j'] == 39.996
    assert errors[0] / errors[1] == pytest.approx(4., rel=.002)
    assert errors[1] / errors[2] == pytest.approx(4., rel=.002)
