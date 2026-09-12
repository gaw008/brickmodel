"""Read-only comparison of the six preregistered saved spatial trajectories.

No candidate imports, forward integration, fitted parameters, or extra grids.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path

GRIDS = (16, 32, 64)
TIMES = [i / 10 for i in range(101)]
ROUND_T = 128 * 2**-53 * 310 / 4
POLICIES = {
    'coarse': {'method': 'BDF', 'rtol': 1e-9, 'atol': 1e-11, 'max_step': .05},
    'fine': {'method': 'BDF', 'rtol': 1e-11, 'atol': 1e-13, 'max_step': .025},
}
REQUIRED_GATES = {'completed_interval', 'all_dense_segments_in_domain',
                  'local_energy', 'global_energy', 'entropy'}


def continuous_rate():
    """Independent 80-digit Chudnovsky pi and continuous initial mean rate."""
    with localcontext() as context:
        context.prec = 80
        series = Decimal(0)
        for k in range(8):
            numerator = math.factorial(6*k) * (13591409 + 545140134*k)
            denominator = math.factorial(3*k) * math.factorial(k)**3 * (-640320)**(3*k)
            series += Decimal(numerator) / denominator
        pi = 426880 * Decimal(10005).sqrt() / series
        d0 = Decimal(93960)
        rate = -Decimal(80) * (pi / Decimal('.02'))**2 / (
            Decimal(100000) * (d0 + (d0*d0 - 1600).sqrt()))
        return {'precision': 80, 'method': 'Chudnovsky 8 terms and Decimal sqrt',
                'pi': str(pi), 'rate_k_s': str(rate)}


def finite_matrix(values, rows, columns, label):
    if not isinstance(values, list) or len(values) != rows:
        raise ValueError(f'{label}: wrong row count')
    if any(not isinstance(row, list) or len(row) != columns for row in values):
        raise ValueError(f'{label}: wrong column count')
    if any(type(x) not in (float, int) or not math.isfinite(x) for row in values for x in row):
        raise ValueError(f'{label}: nonfinite or nonnumeric value')
    return values


def validate_policy(record, n, name):
    if record.get('cells') != n or record.get('policy_name') != name:
        raise ValueError('grid or policy identity mismatch')
    if record.get('policy') != POLICIES[name] or record.get('times_s') != TIMES:
        raise ValueError('unregistered policy or time grid')
    finite_matrix(record.get('samples'), 101, 3*n+1, 'samples')
    finite_matrix(record.get('reported_stress_pa'), 101, n, 'reported stress')
    initial = finite_matrix([record.get('initial_temperatures_k')], 1, n, 'initial')[0]
    if record['samples'][0][:n] != initial:
        raise ValueError('saved initial state mismatch')
    expected = [302 + 2*math.sin(math.pi/(2*n))/(math.pi/(2*n))
                * math.cos(math.pi*(i+.5)/n) for i in range(n)]
    if max(abs(a-b) for a, b in zip(initial, expected))/4 > ROUND_T:
        raise ValueError('initial cell averages differ from frozen continuous formula')
    if any(not 290 <= x <= 310 for row in record['samples'] for x in row[:n]):
        raise ValueError('saved temperature outside registered domain')
    gates = record.get('gates')
    if (not isinstance(gates, dict) or not REQUIRED_GATES <= gates.keys()
            or any(type(x) is not bool for x in gates.values())):
        raise ValueError('missing or nonboolean per-policy gates')
    if record.get('material_qualified') is not False or record.get('source_material_qualified') is not False:
        raise ValueError('manufactured material boundary changed')
    if record.get('real_time_integration') is not True:
        raise ValueError('not an actual registered integration')
    rate = record.get('initial_mean_rate', {})
    finite_matrix([rate.get('temperature_rates_k_s')], 1, n, 'initial actual rates')
    return [row[:n] for row in record['samples']]


def restrict(values):
    return [[math.fsum(row[i:i+2])/2 for i in range(0, len(row), 2)] for row in values]


def differences(left, right):
    return [[a-b for a, b in zip(x, y)] for x, y in zip(left, right)]


def norms(values, scale=4):
    flat = [x for row in values for x in row]
    return {'infinity': max(map(abs, flat))/scale,
            'two': math.sqrt(math.fsum(x*x for x in flat)/len(flat))/scale}


def pair_differences(fields):
    middle = restrict(fields[32])
    high = restrict(restrict(fields[64]))
    return {16: differences(fields[16], middle), 32: differences(middle, high)}


def physical_summaries(record, n):
    result = []
    v = .0002/n
    max_stress_residual = 0.
    for time, state, reported in zip(TIMES, record['samples'], record['reported_stress_pa']):
        temperatures = state[:n]
        mean = math.fsum(temperatures)/n
        variance = math.fsum((t-mean)**2 for t in temperatures)/n
        stress = [1e5*(mean-t) for t in temperatures]
        max_stress_residual = max(max_stress_residual, max(abs(a-b) for a, b in zip(stress, reported)))
        strain = 1e-4*(mean-300)
        free_energy = v*math.fsum(1e5*((t-300)-t*math.log(t/300))
                                  + 1e9*(strain-1e-4*(t-300))**2 for t in temperatures)
        entropy = v*math.fsum(1e5*math.log(t/300)
                              + 2e5*(strain-1e-4*(t-300)) for t in temperatures)
        result.append({'time_s': time, 'mean_temperature_k': mean, 'variance_k2': variance,
                       'internal_energy_j': .0002*(1e5*(mean-300)-10*variance),
                       'helmholtz_energy_j': free_energy, 'entropy_j_k': entropy,
                       'max_tension_pa': max(reported), 'max_compression_pa': min(reported),
                       'sum_heat_j': math.fsum(state[n:2*n]),
                       'sum_work_j': math.fsum(state[2*n:3*n]),
                       'max_abs_local_work_j': max(map(abs, state[2*n:3*n]))})
    initial_theory = 40-.004*(math.sin(math.pi/(2*n))/(math.pi/(2*n)))**2
    return {'samples': result, 'max_reported_stress_reconstruction_residual_pa': max_stress_residual,
            'initial_discrete_energy_formula_j': initial_theory,
            'initial_continuum_energy_j': 39.996,
            'initial_projection_difference_j': initial_theory-39.996,
            'initial_energy_formula_residual_j': result[0]['internal_energy_j']-initial_theory}


def compare(records, summaries, executions):
    temperatures = {name: {n: validate_policy(records[n][name], n, name) for n in GRIDS}
                    for name in POLICIES}
    gates = {}
    for n in GRIDS:
        summary = summaries[n]
        execution = executions[n]
        if summary.get('cells') != n:
            raise ValueError('summary grid mismatch')
        elapsed = execution.get('elapsed_s')
        if (execution.get('cells') != n or type(elapsed) not in (int, float)
                or not math.isfinite(elapsed) or elapsed < 0):
            raise ValueError('invalid supervision evidence')
        gates[f'N{n}_supervision'] = (
            all(execution.get(key) is True for key in
                ('passed', 'within_wall_limit', 'inputs_unchanged', 'child_reaped'))
            and execution.get('timed_out') is False and execution.get('returncode') == 0
            and elapsed <= 30.)
        gates[f'N{n}_completed'] = summary.get('status') == 'completed'
        gates[f'N{n}_completion_record'] = (
            summary.get('completed_policies') == ['coarse', 'fine']
            and all(summary.get(name, {}).get('status') == records[n][name].get('status')
                    for name in POLICIES)
            and summary.get('time_comparison', {}).get('passed') is True
            and summary.get('real_time_integration') is True
            and summary.get('scientific_validated') is False
            and summary.get('material_qualified') is False
            and summary.get('source_material_qualified') is False)
        for name in POLICIES:
            policy = records[n][name]
            gates[f'N{n}_{name}_completed'] = policy.get('status') == 'completed'
            for gate, value in policy['gates'].items():
                gates[f'N{n}_{name}_{gate}'] = value
    gates['total_wall_limit'] = math.fsum(executions[n]['elapsed_s'] for n in GRIDS) <= 90.
    temporal = {n: norms(differences(temperatures['coarse'][n], temperatures['fine'][n])) for n in GRIDS}
    for n in GRIDS:
        gates[f'N{n}_time_refinement'] = temporal[n]['infinity'] <= 1e-7
    spatial = {}
    for name in POLICIES:
        delta = pair_differences(temperatures[name])
        size = {n: norms(delta[n]) for n in (16, 32)}
        result = {'normalized_differences': size, 'temperature_differences_k': delta, 'norms': {}}
        for norm in ('infinity', 'two'):
            low, high = size[16][norm], size[32][norm]
            resolved = min(low, high) > 100*ROUND_T
            separated = (temporal[16][norm]+temporal[32][norm] <= .02*low
                         and temporal[32][norm]+temporal[64][norm] <= .02*high)
            order = math.log2(low/high) if resolved else None
            order_ok = order is not None and 1.8 <= order <= 2.2
            estimate = high/3 if resolved and separated and order_ok else None
            result['norms'][norm] = {'resolved': resolved, 'order': order,
                                    'time_separated': separated,
                                    'conditional_projected_richardson': estimate,
                                    'diagnosis': ('roundoff_stop/no_resolved_spatial_order' if not resolved
                                                  else 'temporal_contamination' if not separated
                                                  else 'second_order' if order_ok else 'order_failed')}
            if name == 'fine':
                gates[f'{norm}_resolved'] = resolved
                gates[f'{norm}_time_separated'] = separated
                gates[f'{norm}_second_order'] = order_ok
                gates[f'{norm}_richardson'] = estimate is not None and estimate <= 1e-4
        initial_difference = max(abs(x) for pair in delta.values() for x in pair[0])/4
        result['initial_restriction_normalized_max'] = initial_difference
        gates[f'{name}_initial_restriction'] = initial_difference <= ROUND_T
        actual_stress = {n: records[n][name]['reported_stress_pa'] for n in GRIDS}
        result['stress_normalized_differences'] = {n: norms(d, 400000)
                                                   for n, d in pair_differences(actual_stress).items()}
        spatial[name] = result
    reference = continuous_rate()
    reference_float = float(reference['rate_k_s'])
    initial_rates = {}
    for n in GRIDS:
        rates = records[n]['fine']['initial_mean_rate']['temperature_rates_k_s']
        observed = math.fsum(rates)/n
        error = abs(observed-reference_float)
        floor = 128*2**-53*max(1., max(map(abs, rates)))/.4
        initial_rates[n] = {'observed_k_s': observed, 'error_k_s': error,
                            'normalized_error': error/.4, 'normalized_roundoff': floor,
                            'diagnosis': 'resolved' if error/.4 > 100*floor else 'roundoff_stop'}
        gates[f'N{n}_initial_mean_rate_negative'] = observed < 0
        gates[f'N{n}_initial_mean_rate_resolved'] = error/.4 > 100*floor
    rate_orders = []
    for low, high in ((16, 32), (32, 64)):
        resolved = gates[f'N{low}_initial_mean_rate_resolved'] and gates[f'N{high}_initial_mean_rate_resolved']
        order = math.log2(initial_rates[low]['error_k_s']/initial_rates[high]['error_k_s']) if resolved else None
        rate_orders.append(order)
        gates[f'initial_mean_rate_order_{low}_{high}'] = order is not None and 1.8 <= order <= 2.2
    return {'status': 'passed' if all(gates.values()) else 'failed_or_unresolved',
            'gates': gates, 'temperature_scale_k': 4., 'roundoff_normalized': ROUND_T,
            'temporal_norms': temporal, 'spatial': spatial,
            'supervision_elapsed_s': {n: executions[n]['elapsed_s'] for n in GRIDS},
            'initial_continuous_reference': reference, 'initial_rates': initial_rates,
            'initial_rate_orders': rate_orders,
            'physical_summaries': {n: {name: physical_summaries(records[n][name], n) for name in POLICIES}
                                   for n in GRIDS},
            'material_qualified': False, 'source_material_qualified': False,
            'full_cycle_qualified': False,
            'stress_claim': 'actual output comparison only; no independently registered stress accuracy gate',
            'scope': 'registered manufactured smooth adiabatic half plate only'}


def main():
    parser = argparse.ArgumentParser(__doc__)
    for n in GRIDS:
        parser.add_argument(f'--n{n}', required=True, type=Path, help='completed worker directory')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    records, summaries, executions, inputs = {}, {}, {}, []
    for n in GRIDS:
        directory = getattr(args, f'n{n}')
        def read(relative):
            path = directory/relative
            raw = path.read_bytes()
            inputs.append({'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest()})
            return json.loads(raw)
        summaries[n] = read('result.json')
        executions[n] = read('../EXECUTION.json')
        records[n] = {name: read(f'{name}/policy.json') for name in POLICIES}
    result = compare(records, summaries, executions)
    result['inputs'] = inputs
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
