"""Full source, elemental, energy and entropy integrals for an open capsule."""
import argparse
import json
from pathlib import Path

import numpy as np
import mpmath as mp
from numpy.polynomial.legendre import leggauss

from audit_carbon_calcium_column import compare, records
from audit_carbon_gas_cycle import polynomial
from carbon_calcium_pressure_setup import build as build_restricted
from carbon_calcium_inventory_setup import build as build_inventory
from carbon_calcium_source_audit import SourceState, independent_exchange
from review_carbon_calcium_open_cell import source_bath
from review_carbon_calcium_program import independent_program
from carbon_calcium_radiation_reference import RadiationSource


def audit(path, root, reservoir_kind, equilibrium_formulation, radiation_kind):
    stream = records(path)
    header, initial = next(stream), next(stream)
    stream.close()
    p, face_policy, rigid = header['settings'], header['face_parameters'], header['rigid_parameters']
    budget = p['verification']
    build = {'restricted': build_restricted, 'positive_inventory': build_inventory}[equilibrium_formulation]
    model, _, _ = build(root, header['pressure_parameters'])
    source = SourceState(header['sources'])
    radiative = {'none': False, 'black_enclosure': True, 'programmed_black_enclosure': True}[radiation_kind]
    radiation_source = RadiationSource(p['radiation']) if radiative else None
    radiation_maxima = {'energy_w': 0., 'entropy_w_k': 0., 'reservoir_temperature_k': 0.}
    radiation_minimum_production = float('inf')
    boundary_maxima = {k: 0. for k in ('temperature_k', 'pressure_pa', 'mole_fraction', 'chemical_potential_j_mol')}

    def constant_bath(at):
        bath = p['reservoir']
        return bath['temperature_k'], bath['pressure_pa'], bath['mole_fractions']

    def programmed_bath(at):
        temperature, pressure, fractions = independent_program(p['boundary_program'], at)
        return float(temperature), float(pressure), {k: float(v) for k, v in fractions.items()}

    bath_inputs = {'constant': constant_bath, 'program': programmed_bath}[reservoir_kind]
    if reservoir_kind == 'program':
        mp.mp.dps = p['boundary_source_review']['decimal_precision']

    def radiation_temperature(at):
        if radiation_kind == 'black_enclosure':
            return p['radiation']['reservoir_temperature_k']
        program = dict(p['boundary_program'], gas_temperature_k=p['boundary_program']['radiation_temperature_k'])
        return float(independent_program(program, at)[0])
    ca, volume = p['initial']['calcium_atoms_mol'], p['volume_m3']
    carbon_lower, oxygen_lower = {'restricted': (ca, 3*ca),
        'positive_inventory': (0., ca)}[equilibrium_formulation]
    maxima = {k: 0. for k in ('element_mol', 'pressure_pa', 'volume_m3', 'reaction_gibbs_j_mol',
        'source_energy_j', 'source_entropy_j_k', 'face_species_mol_s', 'face_energy_w', 'face_entropy_w_k',
        'global_energy_j', 'global_entropy_j_k')}
    minima = {k: float('inf') for k in ('gas_mol', 'solid_mol', 'cv_j_k', 'production_w_k',
                                       'carbon_domain_margin_mol', 'oxygen_domain_margin_mol')}
    counts = {'recorded': 0, 'dense': 0, 'endpoint_repeat': 0}
    phases, samples = {}, {}
    initial_source = source.reconstruct(initial['state'], volume, [ca, *initial['values'][:3]])

    def review(state, y, category, at, contact=None, recorded_bath=None, recorded_radiation=None):
        nonlocal radiation_minimum_production
        counts[category] += 1
        bath_t, bath_p, bath_y = bath_inputs(at)
        reservoir = source_bath(source, bath_t, bath_p, bath_y)
        if recorded_bath is not None:
            errors = {'temperature_k': abs(recorded_bath['temperature_k'] - bath_t),
                'pressure_pa': abs(recorded_bath['pressure_pa'] - bath_p),
                'mole_fraction': max(abs(recorded_bath['mole_fractions'][k] - v) for k, v in bath_y.items()),
                'chemical_potential_j_mol': max(abs(recorded_bath['chemical_potentials_j_mol'][k] - v) for k, v in reservoir['mu'].items())}
            for key, value in errors.items():
                boundary_maxima[key] = max(boundary_maxima[key], value)
        ref = source.reconstruct(state, volume, [ca, *y[:3]])
        for key, value in ref['errors'].items():
            maxima[key] = max(maxima[key], value)
        maxima['global_energy_j'] = max(maxima['global_energy_j'],
            abs(ref['internal_energy_j'] - initial_source['internal_energy_j'] - y[4]))
        maxima['global_entropy_j_k'] = max(maxima['global_entropy_j_k'],
            abs(ref['entropy_j_k'] - initial_source['entropy_j_k'] + y[5] - y[6] + (y[8] if radiative else 0.)))
        flux = independent_exchange(reservoir, ref, face_policy)
        minima['gas_mol'] = min(minima['gas_mol'], ref['minimum_gas_mol'])
        minima['solid_mol'] = min(minima['solid_mol'], ref['minimum_solid_mol'])
        minima['cv_j_k'] = min(minima['cv_j_k'], state['equilibrium_cv_j_k'])
        minima['production_w_k'] = min(minima['production_w_k'], flux['production'])
        minima['carbon_domain_margin_mol'] = min(minima['carbon_domain_margin_mol'], y[0] - carbon_lower)
        minima['oxygen_domain_margin_mol'] = min(minima['oxygen_domain_margin_mol'], y[1] - oxygen_lower)
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
        if radiative:
            radiation = radiation_source.flux(state['temperature_k'], radiation_temperature(at))
            heat, body, bath, production = [radiation[k] for k in (
                'energy_in_w', 'body_entropy_rate_w_k', 'reservoir_entropy_rate_w_k', 'entropy_production_w_k')]
            radiation_minimum_production = min(radiation_minimum_production, production)
            if recorded_radiation is not None:
                radiation_maxima['reservoir_temperature_k'] = max(radiation_maxima['reservoir_temperature_k'],
                    abs(recorded_radiation['reservoir_temperature_k'] - radiation['reservoir_temperature_k']))
                radiation_maxima['energy_w'] = max(radiation_maxima['energy_w'],
                    abs(recorded_radiation['energy_in_w'] - heat))
                radiation_maxima['entropy_w_k'] = max(radiation_maxima['entropy_w_k'],
                    *(abs(recorded_radiation[k] - radiation[k]) for k in (
                        'body_entropy_rate_w_k', 'reservoir_entropy_rate_w_k', 'entropy_production_w_k')))
            physical = np.concatenate((physical, [y[7], y[8]]))
            rates[3] += heat
            rates[4] += body
            rates[6] += production
            rates = np.concatenate((rates, [heat, bath]))
        return physical, rates

    boundary_record = {'constant': lambda row: None, 'program': lambda row: row['reservoir']}[reservoir_kind]
    radiation_record = {'none': lambda row: None, 'black_enclosure': lambda row: row['radiation'],
                        'programmed_black_enclosure': lambda row: row['radiation']}[radiation_kind]
    origin, _ = review(initial['state'], initial['values'], 'recorded', initial['time_s'], initial['face'], boundary_record(initial), radiation_record(initial))
    for row in records(path):
        terminal = row
        if 'state' not in row or row['kind'] == 'initial':
            continue
        y = row['values']
        physical, _ = review(row['state'], y, 'recorded', row['time_s'], row['face'], boundary_record(row), radiation_record(row))
        if row['kind'] == 'sample':
            samples[row['time_s']] = [row['state']]
    integrals, results = [], []
    bounds = np.array([budget['inventory_integral_mol']] * 3 + [budget['energy_j']] + [budget['entropy_j_k']] * 3)
    if radiative:
        bounds = np.concatenate((bounds, [budget['energy_j'], budget['entropy_j_k']]))
    entropy_indices = [4, 5, 6, 8] if radiative else [4, 5, 6]
    for order in budget['quadrature_orders']:
        nodes, weights = leggauss(order)
        total = np.zeros(len(bounds))
        local_max, cumulative_max = np.zeros(len(bounds)), np.zeros(len(bounds))
        previous, previous_y = origin, np.array(initial['values'])
        min_step, ledger_error, gas_ledger_error = float('inf'), 0., 0.
        increments = []
        for row in records(path):
            if row['kind'] != 'accepted':
                continue
            dense = row['dense_output']
            left, right = dense['start_time_s'], dense['end_time_s']
            increment = np.zeros(len(bounds))
            for node, weight in zip(nodes, weights, strict=True):
                at = (left + right) / 2 + (right - left) * node / 2
                y = polynomial(row, at)
                state = model.at_temperature_volume(float(y[3]), volume, ca, *map(float, y[:3]), rigid['numerics'])
                _, rate = review(state, y, 'dense', at)
                increment += weight * (right - left) / 2 * rate
            total += increment
            increments.append(increment)
            current, _ = review(row['state'], row['values'], 'endpoint_repeat', row['time_s'])
            local_max = np.maximum(local_max, np.abs(current - previous - increment))
            cumulative_max = np.maximum(cumulative_max, np.abs(current - origin - total))
            y = np.array(row['values'])
            min_step = min(min_step, current[4] - previous[4] + y[5] - previous_y[5]
                           + (y[8] - previous_y[8] if radiative else 0.))
            ledger_error = max(ledger_error, abs(y[4] - total[3]))
            if radiative:
                gas_ledger_error = max(gas_ledger_error, abs((y[4] - y[7]) - (total[3] - total[7])))
            previous, previous_y = current, y
        flags = {'local_inventory': bool(np.all(local_max[:3] <= bounds[:3])),
            'cumulative_inventory': bool(np.all(cumulative_max[:3] <= bounds[:3])),
            'local_energy': bool(local_max[3] <= bounds[3]), 'cumulative_energy': bool(cumulative_max[3] <= bounds[3]),
            'local_entropy': bool(np.all(local_max[entropy_indices] <= bounds[entropy_indices])),
            'cumulative_entropy': bool(np.all(cumulative_max[entropy_indices] <= bounds[entropy_indices])),
            'energy_ledger': ledger_error <= budget['energy_j'],
            'nonnegative_total_step_entropy': min_step >= -budget['nonnegative_entropy_j_k']}
        flags = {k: bool(v) for k, v in flags.items()}
        if radiative:
            flags.update(local_radiation_energy=bool(local_max[7] <= bounds[7]),
                cumulative_radiation_energy=bool(cumulative_max[7] <= bounds[7]),
                gas_energy_ledger=bool(gas_ledger_error <= budget['energy_j']))
        results.append({'order': order, 'final_integrals_C_O_N_U_Sbody_Sbath_Pi': total[:7].tolist(),
            'maximum_local_residuals': local_max.tolist(), 'maximum_cumulative_residuals': cumulative_max.tolist(),
            'maximum_energy_ledger_residual_j': ledger_error, 'minimum_total_step_entropy_j_k': float(min_step),
            'within_budgets': flags})
        if radiative:
            results[-1].update(final_radiation_energy_j=float(total[7]),
                final_radiation_reservoir_entropy_j_k=float(total[8]),
                final_gas_energy_j=float(total[3] - total[7]),
                maximum_gas_energy_ledger_residual_j=gas_ledger_error,
                residual_coordinate_order=['C', 'O', 'N2', 'U', 'Sbody', 'Sgas', 'Pi', 'Eradiation', 'Sradiation'])
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
    boundary_review = {'kind': reservoir_kind}
    if radiative:
        policy = p['radiation_review']
        radiation_flags = {'energy': radiation_maxima['energy_w'] <= policy['energy_budget_w'],
            'entropy': radiation_maxima['entropy_w_k'] <= policy['entropy_budget_w_k'],
            'nonnegative_production': radiation_minimum_production >= 0.,
            'source_sigma': abs(radiation_source.sigma - p['radiation']['stefan_boltzmann_w_m2_k4']) <= policy['sigma_absolute_budget_w_m2_k4']}
        if radiation_kind == 'programmed_black_enclosure':
            radiation_flags['reservoir_temperature'] = radiation_maxima['reservoir_temperature_k'] <= p['boundary_source_review']['temperature_budget_k']
        boundary_review['radiation'] = {'kind': radiation_kind, 'maxima': radiation_maxima,
                                         'minimum_production_w_k': radiation_minimum_production,
                                         'within_budgets': radiation_flags}
        flags['radiation_source'] = all(radiation_flags.values())
    if reservoir_kind == 'program':
        policy = p['boundary_source_review']
        boundary_bounds = {'temperature_k': policy['temperature_budget_k'], 'pressure_pa': policy['pressure_budget_pa'],
            'mole_fraction': policy['mole_fraction_budget'], 'chemical_potential_j_mol': policy['chemical_potential_budget_j_mol']}
        boundary_flags = {k: v <= boundary_bounds[k] for k, v in boundary_maxima.items()}
        boundary_review.update(maxima=boundary_maxima, within_budgets=boundary_flags)
        flags['boundary_source'] = all(boundary_flags.values())
    return {'trajectory': str(path), 'counts': counts, 'phase_counts': phases, 'maxima': maxima,
        'minima': {k: float(v) for k, v in minima.items()}, 'integral_reviews': results,
        'boundary_review': boundary_review,
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
        reviews[name], samples[name], budgets[name] = audit(args.parameters.resolve().parent / path,
            args.parameters.resolve().parent, settings['reservoir_kind'], settings['equilibrium_formulation'], settings['radiation_kind'])
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
