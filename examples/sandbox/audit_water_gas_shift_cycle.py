"""Independent source inversion, heat/entropy integrals and time refinement."""
import argparse
from bisect import bisect_left
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import time

import mpmath as mp
import numpy as np
from numpy.polynomial.legendre import leggauss

from review_restricted_water_gas_shift import Reference


def polynomial(row, at):
    dense = row['dense_output']; differences = np.asarray(dense['differences'])
    value = differences[0].copy(); product = 1.
    for shift, denominator, coefficient in zip(dense['shifts_s'], dense['denominators_s'], differences[1:], strict=True):
        product *= (at-shift)/denominator; value += coefficient*product
    return value


def audit(path, policy):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream]
    header = rows[0]; p = header['settings']; eq = deepcopy(header['equilibrium_parameters'])
    eq['independent_reference']['root_tolerance'] = policy['independent_root_tolerance']
    eq['independent_reference']['root_maximum_iterations'] = policy['independent_root_iterations']
    mp.mp.dps = policy['independent_decimal_digits']
    source = {name: data for item in header['sources'] for name, data in item['phases'].items() if name in eq['species']}
    reference = Reference(eq, source); case = header['inventory_case']
    initial = {name: mp.mpf(str(value)) for name, value in case['initial_amounts_mol'].items()}
    volume = mp.mpf(str(case['volume_m3'])); t0 = mp.mpf(str(case['initial_temperature_k']))
    origin = reference.equilibrium(t0, volume, initial)
    g = mp.mpf(str(p['heat_conductance_w_k']))
    count = {'recorded': 0, 'dense': 0}
    maxima = {k: 0. for k in ['source_temperature_k', 'source_pressure_pa', 'source_energy_j', 'source_entropy_j_k', 'source_amount_mol', 'entropy_ledger_j_k']}
    minimum_production = float('inf'); minimum_cv = float('inf')

    @lru_cache(maxsize=None)
    def inverse(energy_change, seed):
        target = origin['internal_energy_j']+mp.mpf(energy_change)
        residual = lambda t: reference.equilibrium(t, volume, initial)['internal_energy_j']-target
        start = mp.mpf(seed)
        t = mp.findroot(residual, (start, start+mp.mpf(str(policy['inverse_seed_increment_k']))),
                        tol=mp.mpf(policy['inverse_root_tolerance']), maxsteps=policy['inverse_maximum_iterations'])
        return reference.equilibrium(t, volume, initial)

    accepted = [row for row in rows if row['kind'] == 'accepted']
    ends = [row['time_s'] for row in accepted]
    first = rows[1]

    def at_time(at):
        if at == first['time_s']:
            row, values = first, np.asarray(first['values'])
        else:
            row = accepted[bisect_left(ends, at)]; values = polynomial(row, at)
        return inverse(float(values[0]), row['state']['temperature_k']), values

    def inspect(values, state, segment, category):
        nonlocal minimum_production
        count[category] += 1
        bath = mp.mpf(str(p['program'][segment]['reservoir_temperature_k']))
        q = g*(bath-state['temperature_k']); pi = q*(1/state['temperature_k']-1/bath)
        minimum_production = min(minimum_production, float(pi))
        maxima['entropy_ledger_j_k'] = max(maxima['entropy_ledger_j_k'], float(abs(state['entropy_j_k']-origin['entropy_j_k']+mp.mpf(float(values[1]))-mp.mpf(float(values[2])))))
        balance = np.array([float(state['internal_energy_j']-origin['internal_energy_j']),
                            float(state['entropy_j_k']-origin['entropy_j_k']), float(values[1]), float(values[2])])
        rates = np.array([float(q), float(q/state['temperature_k']), float(-q/bath), float(pi)])
        return balance, rates

    for row in rows:
        if 'state' not in row:
            continue
        recorded = row['state']; state = inverse(float(row['values'][0]), recorded['temperature_k'])
        differences = {'source_temperature_k': abs(mp.mpf(recorded['temperature_k'])-state['temperature_k']),
                       'source_pressure_pa': abs(mp.mpf(recorded['pressure_pa'])-state['pressure_pa']),
                       'source_energy_j': abs(mp.mpf(recorded['internal_energy_j'])-state['internal_energy_j']),
                       'source_entropy_j_k': abs(mp.mpf(recorded['entropy_j_k'])-state['entropy_j_k']),
                       'source_amount_mol': max(abs(mp.mpf(recorded['amounts_mol'][name])-amount) for name, amount in state['amounts_mol'].items())}
        for name, difference in differences.items():
            maxima[name] = max(maxima[name], float(difference))
        minimum_cv = min(minimum_cv, recorded['equilibrium_cv_j_k'])
        inspect(row['values'], state, row['segment_index'], 'recorded')
    integrals, reviews, times = [], [], {row['time_s'] for row in rows if 'state' in row}
    for order in policy['quadrature_orders']:
        nodes, weights = leggauss(order); total = np.zeros(4); previous = np.zeros(4)
        max_local = np.zeros(4); max_cumulative = np.zeros(4); increments = []; minimum_step = float('inf')
        for row in accepted:
            dense = row['dense_output']; left, right = dense['start_time_s'], dense['end_time_s']
            increment = np.zeros(4)
            for node, weight in zip(nodes, weights, strict=True):
                at = (left+right)/2+(right-left)*node/2; times.add(float(at))
                values = polynomial(row, at); state = inverse(float(values[0]), row['state']['temperature_k'])
                _, rates = inspect(values, state, row['segment_index'], 'dense')
                increment += rates*weight*(right-left)/2
            state = inverse(float(row['values'][0]), row['state']['temperature_k'])
            current, _ = inspect(row['values'], state, row['segment_index'], 'recorded')
            total += increment; increments.append(increment)
            max_local = np.maximum(max_local, np.abs(current-previous-increment))
            max_cumulative = np.maximum(max_cumulative, np.abs(current-total))
            minimum_step = min(minimum_step, float(current[1]-previous[1]+current[2]-previous[2]))
            previous = current
        flags = {'local_energy': max_local[0] <= policy['local_energy_j'],
                 'cumulative_energy': max_cumulative[0] <= policy['cumulative_energy_j'],
                 'local_entropy': max(max_local[1:]) <= policy['local_entropy_j_k'],
                 'cumulative_entropy': max(max_cumulative[1:]) <= policy['cumulative_entropy_j_k'],
                 'nonnegative_step_entropy': minimum_step >= -policy['nonnegative_entropy_j_k']}
        reviews.append({'order': order, 'maximum_local_U_Sbody_Sbath_Pi_residuals': max_local.tolist(),
                        'maximum_cumulative_U_Sbody_Sbath_Pi_residuals': max_cumulative.tolist(),
                        'final_integrals_U_Sbody_Sbath_Pi': total.tolist(), 'minimum_step_entropy_j_k': minimum_step,
                        'within_budgets': {k: bool(v) for k, v in flags.items()}})
        integrals.append(np.array(increments))
        print(json.dumps({'trajectory': str(path), 'order': order, 'within_budgets': reviews[-1]['within_budgets']}), flush=True)
    difference = integrals[1]-integrals[0]
    quadrature = np.maximum(np.max(np.abs(difference), axis=0), np.max(np.abs(np.cumsum(difference, axis=0)), axis=0))
    flags = {key: value <= policy[key] for key, value in maxima.items() if key != 'entropy_ledger_j_k'}
    flags.update(completed=rows[-1]['kind'] == 'summary' and rows[-1]['status'] == 'completed',
                 entropy_ledger=maxima['entropy_ledger_j_k'] <= policy['cumulative_entropy_j_k'],
                 positive_recorded_cv=minimum_cv > 0, nonnegative_instantaneous_production=minimum_production >= 0,
                 local_reviews=all(all(item['within_budgets'].values()) for item in reviews),
                 quadrature_energy=bool(quadrature[0] <= policy['cumulative_energy_j']),
                 quadrature_entropy=bool(max(quadrature[1:]) <= policy['cumulative_entropy_j_k']))
    result = {'trajectory': str(path), 'counts': count, 'maxima': maxima,
              'minimum_source_production_w_k': minimum_production, 'minimum_recorded_cv_j_k': minimum_cv,
              'integral_reviews': reviews, 'quadrature_differences_U_Sbody_Sbath_Pi': quadrature.tolist(),
              'within_budgets': flags, 'all_requested_budgets_met': all(flags.values())}
    return result, times, at_time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); policy = settings['review']; started = time.monotonic()
    reviews, times, functions = {}, set(), {}
    for name, path in settings['trajectories'].items():
        reviews[name], nodes, functions[name] = audit(root/path, policy); times.update(nodes)
    maximum = {key: 0. for key in ['time_temperature_k', 'time_pressure_pa', 'time_amount_mol', 'time_entropy_j_k']}
    for at in sorted(times):
        left, ly = functions['base'](at); right, ry = functions['refined'](at)
        difference = {'time_temperature_k': abs(left['temperature_k']-right['temperature_k']),
                      'time_pressure_pa': abs(left['pressure_pa']-right['pressure_pa']),
                      'time_amount_mol': max(abs(value-right['amounts_mol'][name]) for name, value in left['amounts_mol'].items()),
                      'time_entropy_j_k': max(abs(left['entropy_j_k']-right['entropy_j_k']), *map(abs, ly[1:]-ry[1:]))}
        for key, value in difference.items():
            maximum[key] = max(maximum[key], float(value))
    flags = {key: value <= policy[key] for key, value in maximum.items()}
    comparison = {'union_nodes_compared': len(times), 'maximum_differences': maximum, 'within_budgets': flags,
                  'scope': 'All accepted endpoints, observations and 2/4Gauss nodes from both native BDF records; independent source energy inverse. Not a continuous-time supremum.'}
    result = {'settings': settings, 'trajectory_reviews': reviews, 'time_comparison': comparison,
              'all_requested_budgets_met': all(item['all_requested_budgets_met'] for item in reviews.values()) and all(flags.values()),
              'elapsed_s': time.monotonic()-started, 'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'all_requested_budgets_met': result['all_requested_budgets_met'], 'time_comparison': comparison}), flush=True)


if __name__ == '__main__':
    main()
