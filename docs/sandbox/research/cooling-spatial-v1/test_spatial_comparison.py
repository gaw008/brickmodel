"""Fabricated saved arrays test reporting; none are physical run evidence."""
import copy
import importlib.util
import math
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('spatial_comparison', Path(__file__).with_name('compare_spatial.py'))
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def fixture_records():
    reference = float(comparison.continuous_rate()['rate_k_s'])
    records, summaries, executions = {}, {}, {}
    for n in comparison.GRIDS:
        x = math.pi/(2*n)
        initial = [302+2*math.sin(x)/x*math.cos(math.pi*(i+.5)/n) for i in range(n)]
        rows = []
        stress = []
        for time in comparison.TIMES:
            # An intentionally synthetic O(h^2) common-mode error with zero at t=0.
            temperature = [value + time*.005/n**2 for value in initial]
            rows.append(temperature + [0.]*(2*n+1))
            mean = math.fsum(temperature)/n
            stress.append([1e5*(mean-value) for value in temperature])
        records[n] = {}
        for name, policy in comparison.POLICIES.items():
            records[n][name] = {'cells': n, 'policy_name': name, 'policy': policy,
                                'status': 'completed', 'times_s': comparison.TIMES,
                                'samples': copy.deepcopy(rows), 'reported_stress_pa': copy.deepcopy(stress),
                                'initial_temperatures_k': initial,
                                'initial_mean_rate': {'temperature_rates_k_s': [reference+1e-5/n**2]*n},
                                'gates': {key: True for key in comparison.REQUIRED_GATES}, 'material_qualified': False,
                                'source_material_qualified': False, 'real_time_integration': True}
        summaries[n] = {'cells': n, 'status': 'completed', 'completed_policies': ['coarse', 'fine'],
                        'coarse': {'status': 'completed'}, 'fine': {'status': 'completed'},
                        'time_comparison': {'passed': True}, 'real_time_integration': True,
                        'scientific_validated': False, 'material_qualified': False,
                        'source_material_qualified': False}
        executions[n] = {'cells': n, 'elapsed_s': 1., 'passed': True, 'within_wall_limit': True,
                         'inputs_unchanged': True, 'child_reaped': True, 'timed_out': False, 'returncode': 0}
    return records, summaries, executions


def test_synthetic_second_order_and_independent_continuous_reference():
    records, summaries, executions = fixture_records()
    result = comparison.compare(records, summaries, executions)
    assert result['status'] == 'passed'
    for norm in ('infinity', 'two'):
        assert abs(result['spatial']['fine']['norms'][norm]['order']-2) < 1e-6
    assert all(abs(p-2) < 1e-6 for p in result['initial_rate_orders'])
    assert result['material_qualified'] is False
    assert comparison.continuous_rate()['pi'].startswith('3.14159265358979323846264338327950288419716939937510')


def test_failed_saved_gate_cannot_be_overridden_by_good_spatial_order():
    records, summaries, executions = fixture_records()
    records[32]['fine']['gates']['local_energy'] = False
    result = comparison.compare(records, summaries, executions)
    assert result['status'] == 'failed_or_unresolved'
    assert result['gates']['N32_fine_local_energy'] is False


def test_roundoff_does_not_report_zero_error_as_pass():
    records, summaries, executions = fixture_records()
    for n in comparison.GRIDS:
        for record in records[n].values():
            for row in record['samples']:
                row[:n] = record['initial_temperatures_k']
    result = comparison.compare(records, summaries, executions)
    assert result['spatial']['fine']['norms']['infinity']['order'] is None
    assert result['spatial']['fine']['norms']['infinity']['conditional_projected_richardson'] is None
    assert result['status'] == 'failed_or_unresolved'


def test_temporal_contamination_preserves_fine_policy():
    records, summaries, executions = fixture_records()
    for row in records[32]['coarse']['samples'][1:]:
        row[0] += .01
    result = comparison.compare(records, summaries, executions)
    assert result['gates']['N32_time_refinement'] is False
    assert result['spatial']['fine']['norms']['infinity']['diagnosis'] == 'temporal_contamination'
    assert result['spatial']['fine']['norms']['infinity']['conditional_projected_richardson'] is None


def test_actual_reported_stress_is_used():
    records, summaries, executions = fixture_records()
    records[64]['fine']['reported_stress_pa'][50][0] += 1234
    result = comparison.compare(records, summaries, executions)
    assert result['physical_summaries'][64]['fine']['max_reported_stress_reconstruction_residual_pa'] > 1233
    assert result['spatial']['fine']['stress_normalized_differences'][32]['infinity'] > 1e-4


@pytest.mark.parametrize('mutation', ['time', 'policy', 'initial', 'nan', 'missing_gate', 'not_actual'])
def test_invalid_saved_arrays_rejected(mutation):
    records, summaries, executions = fixture_records()
    record = records[16]['fine']
    if mutation == 'time':
        record['times_s'] = record['times_s'][:-1]
    elif mutation == 'policy':
        record['policy'] = {**record['policy'], 'rtol': 1e-5}
    elif mutation == 'initial':
        record['samples'][0][0] += .001
    elif mutation == 'nan':
        record['samples'][5][4] = float('nan')
    elif mutation == 'missing_gate':
        record['gates'] = {}
    else:
        record['real_time_integration'] = False
    with pytest.raises(ValueError):
        comparison.compare(records, summaries, executions)


@pytest.mark.parametrize("field,value", [("elapsed_s", 31.), ("child_reaped", False), ("timed_out", True)])
def test_supervision_failure_cannot_pass(field, value):
    records, summaries, executions = fixture_records()
    executions[32][field] = value
    result = comparison.compare(records, summaries, executions)
    assert result['status'] == 'failed_or_unresolved'
    assert result['gates']['N32_supervision'] is False


@pytest.mark.parametrize("gate", sorted(comparison.REQUIRED_GATES))
def test_missing_required_gate_is_unknown(gate):
    records, summaries, executions = fixture_records()
    del records[16]['fine']['gates'][gate]
    with pytest.raises(ValueError, match='gates'):
        comparison.compare(records, summaries, executions)
