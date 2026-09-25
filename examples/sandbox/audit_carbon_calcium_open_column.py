"""Full source, local and external integrals of programmed reactive columns."""
import argparse
import json
import math
from pathlib import Path

import mpmath as mp
import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_carbon_calcium_column import compare, records
from audit_carbon_gas_cycle import polynomial
from carbon_calcium_inventory_setup import build
from carbon_calcium_radiation_reference import RadiationSource
from carbon_calcium_source_audit import SourceState, independent_exchange
from review_carbon_calcium_open_cell import source_bath
from review_carbon_calcium_program import independent_program


def audit(path, root):
    stream = records(path)
    header, initial = next(stream), next(stream)
    stream.close()
    n, p, cp = header['cell_count'], header['settings'], header['cell_settings']
    body_size, volume, calcium = 4*n, header['cell_volume_m3'], header['cell_calcium_mol']
    budget, rigid = p['verification'], header['rigid_parameters']
    model, _, _ = build(root, header['pressure_parameters'])
    source, radiation_source = SourceState(header['sources']), RadiationSource(cp['radiation'])
    source_ranges = {k: list(map(float, v['source_domain_k']))
                     for k, v in header['sources']['carbon_source']['phases'].items()}
    source_ranges.update({v['id']: list(map(float, v['cp']['selected_single_phase_domain_k']))
        for v in header['sources']['calcite_facts']['species'] if v['id'] in ('calcite', 'lime')})
    common_domain = [max(v[0] for v in source_ranges.values()), min(v[1] for v in source_ranges.values())]
    mp.mp.dps = cp['boundary_source_review']['decimal_precision']
    radiation_program = dict(cp['boundary_program'], gas_temperature_k=cp['boundary_program']['radiation_temperature_k'])
    maxima = {k: 0. for k in ('element_mol', 'pressure_pa', 'volume_m3', 'reaction_gibbs_j_mol',
        'source_energy_j', 'source_entropy_j_k', 'face_species_mol_s', 'face_energy_w', 'face_entropy_w_k',
        'global_energy_j', 'global_entropy_j_k')}
    boundary_maxima = {k: 0. for k in ('temperature_k', 'pressure_pa', 'mole_fraction',
        'chemical_potential_j_mol', 'radiation_temperature_k', 'radiation_energy_w', 'radiation_entropy_w_k')}
    minima = {k: float('inf') for k in ('gas_mol', 'solid_mol', 'cv_j_k', 'production_w_k',
        'carbon_mol', 'oxygen_minus_calcium_mol', 'temperature_k')}
    maximum_temperature = -float('inf')
    counts = {'recorded': 0, 'dense': 0, 'endpoint_repeat': 0}
    phases, samples = {}, {}
    initial_refs = [source.reconstruct(s, volume, [calcium, *initial['values'][4*i:4*i+3]])
                    for i, s in enumerate(initial['states'])]
    initial_energy = math.fsum(r['internal_energy_j'] for r in initial_refs)
    initial_entropy = math.fsum(r['entropy_j_k'] for r in initial_refs)

    def face_review(reference, recorded, parameters):
        maxima['face_entropy_w_k'] = max(maxima['face_entropy_w_k'],
            abs(reference['production'] - reference['dissipation']))
        minima['production_w_k'] = min(minima['production_w_k'], reference['dissipation'])
        if recorded is None:
            return
        maxima['face_species_mol_s'] = max(maxima['face_species_mol_s'],
            *(abs(recorded['gas_flows_mol_s'][k] - v) for k, v in reference['gas'].items()),
            *(abs(recorded['inventory_flows_mol_s'][k] - v)
              for k, v in zip(parameters['transferred_inventory_order'], reference['inventory'], strict=True)))
        maxima['face_energy_w'] = max(maxima['face_energy_w'], abs(recorded['energy_flow_w'] - reference['energy']))
        maxima['face_entropy_w_k'] = max(maxima['face_entropy_w_k'],
            abs(recorded['left_entropy_rate_w_k'] - reference['entropy'][0]),
            abs(recorded['right_entropy_rate_w_k'] - reference['entropy'][1]),
            abs(recorded['entropy_production_w_k'] - reference['dissipation']))

    def review(states, values, at, category, row=None):
        nonlocal maximum_temperature
        y = np.asarray(values)
        counts[category] += n
        refs = []
        for i, state in enumerate(states):
            ref = source.reconstruct(state, volume, [calcium, *y[4*i:4*i+3]])
            refs.append(ref)
            for key, value in ref['errors'].items():
                maxima[key] = max(maxima[key], float(value))
            minima['gas_mol'] = min(minima['gas_mol'], ref['minimum_gas_mol'])
            minima['solid_mol'] = min(minima['solid_mol'], ref['minimum_solid_mol'])
            minima['cv_j_k'] = min(minima['cv_j_k'], state['equilibrium_cv_j_k'])
            minima['carbon_mol'] = min(minima['carbon_mol'], float(y[4*i]))
            minima['oxygen_minus_calcium_mol'] = min(minima['oxygen_minus_calcium_mol'], float(y[4*i+1]) - calcium)
            minima['temperature_k'] = min(minima['temperature_k'], state['temperature_k'])
            maximum_temperature = max(maximum_temperature, state['temperature_k'])
            key = state['calcium_phase'] + '/' + state['carbon_phase']
            phases[key] = phases.get(key, 0) + 1
        body = np.array([[*y[4*i:4*i+3], r['internal_energy_j'], r['entropy_j_k']] for i, r in enumerate(refs)])
        body_rates = np.zeros((n, 5))
        productions = []
        for i in range(n - 1):
            f = independent_exchange(refs[i], refs[i+1], header['internal_face_parameters'])
            face_review(f, row['faces'][i] if row is not None else None, header['internal_face_parameters'])
            transfer = np.array([*f['inventory'], f['energy']])
            body_rates[i, :4] -= transfer
            body_rates[i+1, :4] += transfer
            body_rates[i, 4] += f['entropy'][0]
            body_rates[i+1, 4] += f['entropy'][1]
            productions.append(f['dissipation'])
        t, pressure, fractions = independent_program(cp['boundary_program'], at)
        bath = source_bath(source, float(t), float(pressure), {k: float(v) for k, v in fractions.items()})
        f = independent_exchange(bath, refs[-1], header['exterior_parameters'])
        face_review(f, row['contact'] if row is not None else None, header['exterior_parameters'])
        rad_t = float(independent_program(radiation_program, at)[0])
        rad = radiation_source.flux(states[-1]['temperature_k'], rad_t)
        minima['production_w_k'] = min(minima['production_w_k'], rad['entropy_production_w_k'])
        incoming_energy = f['energy'] + rad['energy_in_w']
        body_rates[-1, :4] += np.array([*f['inventory'], incoming_energy])
        body_rates[-1, 4] += f['entropy'][1] + rad['body_entropy_rate_w_k']
        production = math.fsum(productions + [f['dissipation'], rad['entropy_production_w_k']])
        exterior_rates = np.array([*f['inventory'], incoming_energy, f['entropy'][0], production,
            rad['energy_in_w'], rad['reservoir_entropy_rate_w_k']])
        exterior = np.array([*np.sum(body[:, :3], axis=0), math.fsum(body[:, 3]),
                             *y[body_size+1:]])
        maxima['global_energy_j'] = max(maxima['global_energy_j'],
            float(abs(exterior[3] - initial_energy - y[body_size])))
        maxima['global_entropy_j_k'] = max(maxima['global_entropy_j_k'],
            float(abs(math.fsum(body[:, 4]) - initial_entropy + exterior[4] + exterior[7] - exterior[5])))
        if row is not None:
            recorded = row['reservoir']
            errors = {'temperature_k': abs(recorded['temperature_k'] - float(t)),
                'pressure_pa': abs(recorded['pressure_pa'] - float(pressure)),
                'mole_fraction': max(abs(recorded['mole_fractions'][k] - float(v)) for k, v in fractions.items()),
                'chemical_potential_j_mol': max(abs(recorded['chemical_potentials_j_mol'][k] - v) for k, v in bath['mu'].items()),
                'radiation_temperature_k': abs(row['radiation']['reservoir_temperature_k'] - rad_t),
                'radiation_energy_w': abs(row['radiation']['energy_in_w'] - rad['energy_in_w']),
                'radiation_entropy_w_k': max(abs(row['radiation'][k] - rad[k]) for k in rad if 'entropy' in k)}
            for key, value in errors.items():
                boundary_maxima[key] = max(boundary_maxima[key], value)
        return body, exterior, np.concatenate((body_rates.ravel(), exterior_rates))

    origin_body, origin_ext, _ = review(initial['states'], initial['values'], initial['time_s'], 'recorded', initial)
    for row in records(path):
        terminal = row
        if 'states' not in row or row['kind'] == 'initial':
            continue
        review(row['states'], row['values'], row['time_s'], 'recorded', row)
        if row['kind'] == 'sample':
            samples[row['time_s']] = [{k: s[k] for k in ('temperature_k', 'pressure_pa', 'amounts_mol')} for s in row['states']]
    body_bounds = np.array([budget['inventory_integral_mol']] * 3 + [budget['energy_j'], budget['entropy_j_k']])
    ext_bounds = np.array([budget['inventory_integral_mol']] * 3 + [budget['energy_j']]
        + [budget['entropy_j_k']] * 2 + [budget['energy_j'], budget['entropy_j_k']])
    total_bounds = np.concatenate((np.tile(body_bounds, n), ext_bounds))
    integrals, results = [], []
    for order in budget['quadrature_orders']:
        nodes, weights = leggauss(order)
        total = np.zeros(5*n+8)
        local_max = np.zeros_like(total)
        cumulative_max = np.zeros_like(total)
        previous = np.concatenate((origin_body.ravel(), origin_ext))
        previous_body, previous_ext = origin_body, origin_ext
        minimum_step, ledger_error = float('inf'), 0.
        increments = []
        for row in records(path):
            if row['kind'] != 'accepted':
                continue
            left, right = [row['dense_output'][k] for k in ('start_time_s', 'end_time_s')]
            increment = np.zeros_like(total)
            for node, weight in zip(nodes, weights, strict=True):
                at = (left + right) / 2 + (right - left) * node / 2
                y = polynomial(row, at)
                states = [model.at_temperature_volume(float(y[4*i+3]), volume, calcium,
                    *map(float, y[4*i:4*i+3]), rigid['numerics']) for i in range(n)]
                _, _, rates = review(states, y, at, 'dense')
                increment += weight * (right - left) / 2 * rates
            total += increment
            increments.append(increment)
            body, exterior, _ = review(row['states'], row['values'], row['time_s'], 'endpoint_repeat')
            current = np.concatenate((body.ravel(), exterior))
            origin = np.concatenate((origin_body.ravel(), origin_ext))
            local_max = np.maximum(local_max, np.abs(current - previous - increment))
            cumulative_max = np.maximum(cumulative_max, np.abs(current - origin - total))
            minimum_step = min(minimum_step, float(math.fsum(body[:, 4] - previous_body[:, 4])
                + exterior[4] - previous_ext[4] + exterior[7] - previous_ext[7]))
            ledger_error = max(ledger_error, float(abs(row['values'][body_size] - total[5*n+3])),
                float(abs((row['values'][body_size] - row['values'][body_size+3]) - (total[5*n+3] - total[5*n+6]))))
            previous, previous_body, previous_ext = current, body, exterior
        flags = {'local_body': bool(np.all(local_max[:5*n] <= np.tile(body_bounds, n))),
            'cumulative_body': bool(np.all(cumulative_max[:5*n] <= np.tile(body_bounds, n))),
            'local_exterior': bool(np.all(local_max[5*n:] <= ext_bounds)),
            'cumulative_exterior': bool(np.all(cumulative_max[5*n:] <= ext_bounds)),
            'energy_ledgers': ledger_error <= budget['energy_j'],
            'nonnegative_step_entropy': minimum_step >= -budget['nonnegative_entropy_j_k']}
        results.append({'order': order, 'final_body_integrals_C_O_N_U_S': total[:5*n].reshape(n, 5).tolist(),
            'final_exterior_integrals_C_O_N_E_Sgas_Pi_Erad_Srad': total[5*n:].tolist(),
            'maximum_local_body_residuals_C_O_N_U_S': np.max(local_max[:5*n].reshape(n, 5), axis=0).tolist(),
            'maximum_cumulative_body_residuals_C_O_N_U_S': np.max(cumulative_max[:5*n].reshape(n, 5), axis=0).tolist(),
            'maximum_local_exterior_residuals': local_max[5*n:].tolist(),
            'maximum_cumulative_exterior_residuals': cumulative_max[5*n:].tolist(),
            'maximum_energy_ledger_residual_j': ledger_error, 'minimum_step_entropy_j_k': minimum_step,
            'within_budgets': flags})
        integrals.append(np.array(increments))
        print(json.dumps({'trajectory': str(path), 'order': order, 'within_budgets': flags}), flush=True)
    difference = integrals[1] - integrals[0]
    quadrature = np.maximum(np.max(np.abs(difference), axis=0), np.max(np.abs(np.cumsum(difference, axis=0)), axis=0))
    bp, rp = cp['boundary_source_review'], cp['radiation_review']
    boundary_bounds = {'temperature_k': bp['temperature_budget_k'], 'pressure_pa': bp['pressure_budget_pa'],
        'mole_fraction': bp['mole_fraction_budget'], 'chemical_potential_j_mol': bp['chemical_potential_budget_j_mol'],
        'radiation_temperature_k': bp['temperature_budget_k'], 'radiation_energy_w': rp['energy_budget_w'],
        'radiation_entropy_w_k': rp['entropy_budget_w_k']}
    boundary_flags = {k: v <= boundary_bounds[k] for k, v in boundary_maxima.items()}
    flags = {k: v <= budget[k] for k, v in maxima.items() if k in budget}
    flags.update(completed=terminal['kind'] == 'summary' and terminal['status'] == 'completed',
        global_energy=maxima['global_energy_j'] <= budget['energy_j'], global_entropy=maxima['global_entropy_j_k'] <= budget['entropy_j_k'],
        positive_gas=minima['gas_mol'] > 0., nonnegative_solid=minima['solid_mol'] >= 0., positive_cv=minima['cv_j_k'] > 0.,
        nonnegative_production=minima['production_w_k'] >= 0., positive_carbon=minima['carbon_mol'] > 0., oxygen_domain=minima['oxygen_minus_calcium_mol'] > 0.,
        source_temperature_domain=minima['temperature_k'] >= common_domain[0] and maximum_temperature <= common_domain[1],
        gas_boundary_temperature_domain=min(cp['boundary_program']['gas_temperature_k']) >= common_domain[0]
            and max(cp['boundary_program']['gas_temperature_k']) <= common_domain[1],
        integral_reviews=all(all(r['within_budgets'].values()) for r in results), quadrature=bool(np.all(quadrature <= total_bounds)),
        boundary_sources=all(boundary_flags.values()),
        radiation_constant=abs(radiation_source.sigma - cp['radiation']['stefan_boltzmann_w_m2_k4']) <= rp['sigma_absolute_budget_w_m2_k4'])
    return {'trajectory': str(path), 'cell_count': n, 'counts': counts, 'maxima': maxima, 'minima': minima,
        'maximum_temperature_k': maximum_temperature, 'phase_counts': phases, 'integral_reviews': results,
        'source_phase_temperature_ranges_k': source_ranges, 'common_source_temperature_domain_k': common_domain,
        'boundary_maxima': boundary_maxima, 'boundary_within_budgets': boundary_flags,
        'quadrature_maximum_body_differences_C_O_N_U_S': np.max(quadrature[:5*n].reshape(n, 5), axis=0).tolist(),
        'quadrature_exterior_differences': quadrature[5*n:].tolist(), 'within_budgets': flags,
        'all_requested_numerical_budgets_met': all(flags.values())}, samples, budget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    reviews, samples, budgets = {}, {}, {}
    for name, path in p['trajectories'].items():
        reviews[name], samples[name], budgets[name] = audit(root / path, root)
    left, right = p['time_comparison_pair']
    comparisons = {'time': compare(samples[left], samples[right], budgets[left])}
    if p['reference_kind'] == 'cell':
        reference = {r['time_s']: [r['state']] for r in records(root / p['reference_trajectory']) if r['kind'] == 'sample'}
        comparisons['one_cell_reference'] = compare(reference, samples[right], budgets[right])
    result = {'settings': p, 'trajectory_reviews': reviews, 'comparisons': comparisons,
        'all_requested_numerical_budgets_met': all(r['all_requested_numerical_budgets_met'] for r in reviews.values())
            and all(r['all_requested_budgets_met'] for r in comparisons.values()),
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met'], 'comparisons': comparisons}))


if __name__ == '__main__':
    main()
