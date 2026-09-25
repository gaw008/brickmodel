"""Full source, elemental, energy and entropy integrals for an open capsule."""
import argparse
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_carbon_calcium_column import compare, records
from audit_carbon_gas_cycle import polynomial
from carbon_calcium_pressure_setup import build
from carbon_calcium_source_audit import SourceState, independent_exchange
from review_carbon_calcium_open_cell import source_bath


def audit(path, root):
    stream = records(path)
    header, initial = next(stream), next(stream)
    stream.close()
    p, face_policy, rigid = header['settings'], header['face_parameters'], header['rigid_parameters']
    budget = p['verification']
    model, _, _ = build(root, header['pressure_parameters'])
    source = SourceState(header['sources'])
    bath = p['reservoir']
    reservoir = source_bath(source, bath['temperature_k'], bath['pressure_pa'], bath['mole_fractions'])
    ca, volume = p['initial']['calcium_atoms_mol'], p['volume_m3']
    maxima = {k: 0. for k in ('element_mol', 'pressure_pa', 'volume_m3', 'reaction_gibbs_j_mol',
        'source_energy_j', 'source_entropy_j_k', 'face_species_mol_s', 'face_energy_w', 'face_entropy_w_k',
        'global_energy_j', 'global_entropy_j_k')}
    minima = {k: float('inf') for k in ('gas_mol', 'solid_mol', 'cv_j_k', 'production_w_k',
                                       'carbon_domain_margin_mol', 'oxygen_domain_margin_mol')}
    counts = {'recorded': 0, 'dense': 0, 'endpoint_repeat': 0}
    phases, samples = {}, {}
    initial_source = source.reconstruct(initial['state'], volume, [ca, *initial['values'][:3]])

    def review(state, y, category, contact=None):
        counts[category] += 1
        ref = source.reconstruct(state, volume, [ca, *y[:3]])
        for key, value in ref['errors'].items():
            maxima[key] = max(maxima[key], value)
        maxima['global_energy_j'] = max(maxima['global_energy_j'],
            abs(ref['internal_energy_j'] - initial_source['internal_energy_j'] - y[4]))
        maxima['global_entropy_j_k'] = max(maxima['global_entropy_j_k'],
            abs(ref['entropy_j_k'] - initial_source['entropy_j_k'] + y[5] - y[6]))
        flux = independent_exchange(reservoir, ref, face_policy)
        minima['gas_mol'] = min(minima['gas_mol'], ref['minimum_gas_mol'])
        minima['solid_mol'] = min(minima['solid_mol'], ref['minimum_solid_mol'])
        minima['cv_j_k'] = min(minima['cv_j_k'], state['equilibrium_cv_j_k'])
        minima['production_w_k'] = min(minima['production_w_k'], flux['production'])
        minima['carbon_domain_margin_mol'] = min(minima['carbon_domain_margin_mol'], y[0] - ca)
        minima['oxygen_domain_margin_mol'] = min(minima['oxygen_domain_margin_mol'], y[1] - 3 * ca)
        key = state['calcium_phase'] + '/' + state['carbon_phase']
        phases[key] = phases.get(key, 0) + 1
        maxima['face_entropy_w_k'] = max(maxima['face_entropy_w_k'], abs(flux['production'] - flux['dissipation']))
        if contact is not None:
            maxima['face_species_mol_s'] = max(maxima['face_species_mol_s'],
                *(abs(contact['gas_flows_mol_s'][k] - v) for k, v in flux['gas'].items()),
                *(abs(contact['inventory_flows_mol_s'][k] - v)
                  for k, v in zip(face_policy['transferred_inventory_order'], flux['inventory'], strict=True)))
            maxima['face_energy_w'] = max(maxima['face_energy_w'], abs(contact['energy_flow_w'] - flux['energy']))
            maxima['face_entropy_w_k'] = max(maxima['face_entropy_w_k'],
                abs(contact['left_entropy_rate_w_k'] - flux['entropy'][0]),
                abs(contact['right_entropy_rate_w_k'] - flux['entropy'][1]),
                abs(contact['entropy_production_w_k'] - flux['production']))
        physical = np.array([*y[:3], ref['internal_energy_j'], ref['entropy_j_k'], y[5], y[6]])
        rates = np.array([*flux['inventory'], flux['energy'], flux['entropy'][1],
                          flux['entropy'][0], flux['production']])
        return physical, rates

    origin, _ = review(initial['state'], initial['values'], 'recorded', initial['face'])
    for row in records(path):
        terminal = row
        if 'state' not in row or row['kind'] == 'initial':
            continue
        y = row['values']
        physical, _ = review(row['state'], y, 'recorded', row['face'])
        if row['kind'] == 'sample':
            samples[row['time_s']] = [row['state']]
    integrals, results = [], []
    bounds = np.array([budget['inventory_integral_mol']] * 3 + [budget['energy_j']] + [budget['entropy_j_k']] * 3)
    for order in budget['quadrature_orders']:
        nodes, weights = leggauss(order)
        total = np.zeros(7)
        local_max, cumulative_max = np.zeros(7), np.zeros(7)
        previous, previous_y = origin, np.array(initial['values'])
        min_step, ledger_error = float('inf'), 0.
        increments = []
        for row in records(path):
            if row['kind'] != 'accepted':
                continue
            dense = row['dense_output']
            left, right = dense['start_time_s'], dense['end_time_s']
            increment = np.zeros(7)
            for node, weight in zip(nodes, weights, strict=True):
                at = (left + right) / 2 + (right - left) * node / 2
                y = polynomial(row, at)
                state = model.at_temperature_volume(float(y[3]), volume, ca, *map(float, y[:3]), rigid['numerics'])
                _, rate = review(state, y, 'dense')
                increment += weight * (right - left) / 2 * rate
            total += increment
            increments.append(increment)
            current, _ = review(row['state'], row['values'], 'endpoint_repeat')
            local_max = np.maximum(local_max, np.abs(current - previous - increment))
            cumulative_max = np.maximum(cumulative_max, np.abs(current - origin - total))
            y = np.array(row['values'])
            min_step = min(min_step, current[4] - previous[4] + y[5] - previous_y[5])
            ledger_error = max(ledger_error, abs(y[4] - total[3]))
            previous, previous_y = current, y
        flags = {'local_inventory': bool(np.all(local_max[:3] <= bounds[:3])),
            'cumulative_inventory': bool(np.all(cumulative_max[:3] <= bounds[:3])),
            'local_energy': bool(local_max[3] <= bounds[3]), 'cumulative_energy': bool(cumulative_max[3] <= bounds[3]),
            'local_entropy': bool(np.all(local_max[4:] <= bounds[4:])),
            'cumulative_entropy': bool(np.all(cumulative_max[4:] <= bounds[4:])),
            'energy_ledger': ledger_error <= budget['energy_j'],
            'nonnegative_total_step_entropy': min_step >= -budget['nonnegative_entropy_j_k']}
        flags = {k: bool(v) for k, v in flags.items()}
        results.append({'order': order, 'final_integrals_C_O_N_U_Sbody_Sbath_Pi': total.tolist(),
            'maximum_local_residuals': local_max.tolist(), 'maximum_cumulative_residuals': cumulative_max.tolist(),
            'maximum_energy_ledger_residual_j': ledger_error, 'minimum_total_step_entropy_j_k': float(min_step),
            'within_budgets': flags})
        integrals.append(np.array(increments))
        print(json.dumps({'trajectory': str(path), 'order': order, 'within_budgets': flags}), flush=True)
    delta = integrals[1] - integrals[0]
    quadrature = np.maximum(np.max(np.abs(delta), axis=0), np.max(np.abs(np.cumsum(delta, axis=0)), axis=0))
    flags = {k: v <= budget[k] for k, v in maxima.items() if k in budget}
    flags.update(completed=terminal['kind'] == 'summary' and terminal['status'] == 'completed',
        global_energy=maxima['global_energy_j'] <= budget['energy_j'],
        global_entropy=maxima['global_entropy_j_k'] <= budget['entropy_j_k'],
        positive_gas=minima['gas_mol'] > 0., nonnegative_solids=minima['solid_mol'] >= 0.,
        positive_cv=minima['cv_j_k'] > 0., nonnegative_production=minima['production_w_k'] >= 0.,
        elemental_domain=minima['carbon_domain_margin_mol'] > 0. and minima['oxygen_domain_margin_mol'] > 0.,
        integral_reviews=all(all(r['within_budgets'].values()) for r in results),
        quadrature=bool(np.all(quadrature <= bounds)))
    flags = {k: bool(v) for k, v in flags.items()}
    return {'trajectory': str(path), 'counts': counts, 'phase_counts': phases, 'maxima': maxima,
        'minima': {k: float(v) for k, v in minima.items()}, 'integral_reviews': results,
        'maximum_quadrature_differences': quadrature.tolist(), 'within_budgets': flags,
        'all_requested_numerical_budgets_met': all(flags.values())}, samples, budget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    reviews, samples, budgets = {}, {}, {}
    for name, path in settings['trajectories'].items():
        reviews[name], samples[name], budgets[name] = audit(args.parameters.resolve().parent / path, args.parameters.resolve().parent)
    left, right = settings['time_comparison_pair']
    comparison = compare(samples[left], samples[right], budgets[left])
    result = {'settings': settings, 'trajectory_reviews': reviews, 'time_comparison': comparison,
        'all_requested_numerical_budgets_met': all(r['all_requested_numerical_budgets_met'] for r in reviews.values()) and comparison['all_requested_budgets_met'],
        'material_qualified': False, 'training_eligible': False,
        'scope': 'Full recorded and Gauss-node source/flux qualification of this virtual bath path; bath maintenance apparatus is outside the system boundary.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met'], 'time_comparison': comparison}))


if __name__ == '__main__':
    main()
