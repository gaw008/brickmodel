"""Independent Fick, cosine-mode, inventory and mixing-entropy trajectory review.

The reference does not call the production Maxwell–Stefan law, face or column.
Binary diffusivity is held at the recorded source-qualified input value.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss


def polynomial(record, at):
    dense = record['dense_output']
    differences = np.asarray(dense['differences'])
    result, product = differences[0].copy(), 1.0
    for index, (shift, denominator) in enumerate(zip(
            dense['shifts_s'], dense['denominators_s'], strict=True)):
        product *= (at-shift)/denominator
        result += product*differences[index+1]
    return result


def audit(path):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream]
    header, initial = rows[:2]
    settings = header['settings']
    budget = settings['verification']
    count = header['cell_count']
    area = settings['geometry']['area_m2']
    length = settings['geometry']['length_m']
    width, volume = length/count, area*length/count
    concentration, gas_constant = header['concentration_mol_m3'], header['gas_constant_j_mol_k']
    diffusivity = header['binary_diffusivity_m2_s'][0][1]
    mean = np.asarray(settings['initial']['mean_mole_fractions'])
    amplitude = np.asarray(settings['initial']['cosine_amplitudes'])
    wave_number = settings['initial']['cosine_mode']*np.pi/length
    centers = (np.arange(count)+0.5)*width
    cell_cosine = np.cos(wave_number*centers)*np.sinc(wave_number*width/(2*np.pi))
    continuum_rate = diffusivity*wave_number**2
    discrete_rate = 4*diffusivity*np.sin(wave_number*width/2)**2/width**2
    maxima = {name: 0.0 for name in [
        'fraction_encoding', 'inventory_encoding_mol', 'entropy_encoding_j_k',
        'face_flux_mol_m2_s', 'face_entropy_rate_w_k', 'global_species_mol',
        'semidiscrete_exact_fraction', 'continuum_exact_cell_average_fraction']}
    minima = {'mole_fraction': float('inf'), 'face_entropy_rate_w_k': float('inf')}
    counts = {'recorded': 0, 'dense': 0}

    def reference(values, at, category):
        counts[category] += 1
        first = np.asarray(values)
        fractions = np.column_stack((first, 1-first))
        inventories = concentration*volume*fractions
        entropy = -gas_constant*np.sum(inventories*np.log(fractions), axis=1)
        flux = np.zeros((count+1, 2))
        flux[1:-1, 0] = -concentration*diffusivity*np.diff(first)/width
        flux[1:-1, 1] = -flux[1:-1, 0]
        production = -gas_constant*area*np.sum(
            flux[1:-1]*np.diff(np.log(fractions), axis=0), axis=1)
        inventory_rate = area*(flux[:-1]-flux[1:])
        entropy_rate = -gas_constant*np.sum((np.log(fractions)+1)*inventory_rate, axis=1)
        minima['mole_fraction'] = min(minima['mole_fraction'], float(fractions.min()))
        minima['face_entropy_rate_w_k'] = min(minima['face_entropy_rate_w_k'], float(production.min()))
        maxima['global_species_mol'] = max(maxima['global_species_mol'],
            float(np.max(np.abs(np.sum(inventories, axis=0)-concentration*area*length*mean))))
        for key, decay in [('semidiscrete_exact_fraction', discrete_rate),
                ('continuum_exact_cell_average_fraction', continuum_rate)]:
            exact = mean+np.outer(cell_cosine, amplitude)*np.exp(-decay*at)
            maxima[key] = max(maxima[key], float(np.max(np.abs(fractions-exact))))
        return fractions, inventories, entropy, flux[1:-1], production, inventory_rate, entropy_rate

    recorded = [row for row in rows if row['kind'] in ('initial', 'accepted', 'sample')]
    recorded.append(rows[-1]['final'])
    for row in recorded:
        fractions, inventories, entropy, flux, production, _, _ = reference(row['values'], row['time_s'], 'recorded')
        for name, error in [
                ('fraction_encoding', np.max(np.abs(fractions-row['mole_fractions']))),
                ('inventory_encoding_mol', np.max(np.abs(inventories-row['inventories_mol']))),
                ('entropy_encoding_j_k', np.max(np.abs(entropy-row['mixing_entropy_j_k']))),
                ('face_flux_mol_m2_s', np.max(np.abs(flux-[face['molar_fluxes_mol_m2_s'] for face in row['faces']]))),
                ('face_entropy_rate_w_k', max(np.max(np.abs(production-area*np.array([face[key] for face in row['faces']])))
                    for key in ('entropy_from_jump_w_m2_k', 'entropy_from_path_w_m2_k')))]:
            maxima[name] = max(maxima[name], float(error))
    initial_inventory = np.asarray(initial['inventories_mol'])
    initial_entropy = np.asarray(initial['mixing_entropy_j_k'])
    reviews, final_integrals = [], []
    for order in budget['entropy_quadrature_orders']:
        nodes, weights = leggauss(order)
        cumulative_n, cumulative_s, cumulative_production = np.zeros((count, 2)), np.zeros(count), 0.0
        previous_n, previous_s = initial_inventory, initial_entropy
        errors = {key: 0.0 for key in ['local_species_mol', 'cumulative_species_mol',
            'local_mixing_entropy_j_k', 'cumulative_local_mixing_entropy_j_k',
            'local_total_mixing_entropy_j_k', 'cumulative_total_mixing_entropy_j_k']}
        minimum_step = float('inf')
        for row in rows:
            if row['kind'] != 'accepted':
                continue
            dense = row['dense_output']
            left, right = dense['start_time_s'], dense['end_time_s']
            integral_n, integral_s, integral_production = np.zeros((count, 2)), np.zeros(count), 0.0
            for node, weight in zip(nodes, weights, strict=True):
                at = (left+right)/2+(right-left)*node/2
                _, _, _, _, production, n_rate, s_rate = reference(polynomial(row, at), at, 'dense')
                factor = weight*(right-left)/2
                integral_n += factor*n_rate
                integral_s += factor*s_rate
                integral_production += factor*float(np.sum(production))
            cumulative_n += integral_n
            cumulative_s += integral_s
            cumulative_production += integral_production
            inventory, entropy = np.asarray(row['inventories_mol']), np.asarray(row['mixing_entropy_j_k'])
            changes = {'local_species_mol': np.max(np.abs(inventory-previous_n-integral_n)),
                'cumulative_species_mol': np.max(np.abs(inventory-initial_inventory-cumulative_n)),
                'local_mixing_entropy_j_k': np.max(np.abs(entropy-previous_s-integral_s)),
                'cumulative_local_mixing_entropy_j_k': np.max(np.abs(entropy-initial_entropy-cumulative_s)),
                'local_total_mixing_entropy_j_k': abs(float(np.sum(entropy-previous_s))-integral_production),
                'cumulative_total_mixing_entropy_j_k': abs(float(np.sum(entropy-initial_entropy))-cumulative_production)}
            for key, value in changes.items():
                errors[key] = max(errors[key], float(value))
            minimum_step = min(minimum_step, float(np.sum(entropy-previous_s)))
            previous_n, previous_s = inventory, entropy
        limits = {'local_species_mol': budget['local_species_budget_mol'],
            'cumulative_species_mol': budget['local_species_budget_mol'],
            'local_mixing_entropy_j_k': budget['local_mixing_entropy_budget_j_k'],
            'cumulative_local_mixing_entropy_j_k': budget['cumulative_mixing_entropy_budget_j_k'],
            'local_total_mixing_entropy_j_k': budget['local_mixing_entropy_budget_j_k'],
            'cumulative_total_mixing_entropy_j_k': budget['cumulative_mixing_entropy_budget_j_k']}
        flags = {key: value <= limits[key] for key, value in errors.items()}
        flags['nonnegative_step_total_mixing_entropy'] = minimum_step >= -budget['negative_step_mixing_entropy_budget_j_k']
        final_integrals.append((cumulative_n, cumulative_s, cumulative_production))
        reviews.append({'order': order, 'maximum_residuals': errors,
            'minimum_step_total_mixing_entropy_j_k': minimum_step,
            'total_mixing_entropy_production_j_k': cumulative_production, 'within_budgets': flags})
    first, last = final_integrals[0], final_integrals[-1]
    quadrature_difference = {'species_mol': float(np.max(np.abs(first[0]-last[0]))),
        'local_mixing_entropy_j_k': float(np.max(np.abs(first[1]-last[1]))),
        'total_mixing_entropy_j_k': float(abs(first[2]-last[2]))}
    flags = {'completed': rows[-1]['status'] == 'completed',
        'positive_fractions': minima['mole_fraction'] > 0,
        'nonnegative_face_entropy': minima['face_entropy_rate_w_k'] >= 0,
        'fraction_encoding': maxima['fraction_encoding'] == 0,
        'inventory_encoding': maxima['inventory_encoding_mol'] <= budget['global_species_budget_mol'],
        'entropy_encoding': maxima['entropy_encoding_j_k'] <= budget['local_mixing_entropy_budget_j_k'],
        'face_fick_flux': maxima['face_flux_mol_m2_s'] <= budget['source_flux_absolute_budget_mol_m2_s'],
        'face_entropy': maxima['face_entropy_rate_w_k'] <= budget['source_entropy_rate_budget_w_k'],
        'global_species': maxima['global_species_mol'] <= budget['global_species_budget_mol'],
        'semidiscrete_exact': maxima['semidiscrete_exact_fraction'] <= budget['semidiscrete_exact_fraction_budget'],
        'whole_trajectory_balances': all(all(item['within_budgets'].values()) for item in reviews),
        'quadrature_species': quadrature_difference['species_mol'] <= budget['local_species_budget_mol'],
        'quadrature_entropy': max(quadrature_difference['local_mixing_entropy_j_k'], quadrature_difference['total_mixing_entropy_j_k']) <= budget['cumulative_mixing_entropy_budget_j_k']}
    return {'trajectory': str(path), 'cell_count': count, 'accepted_steps': rows[-1]['steps'],
        'counts': counts, 'maxima': maxima, 'minima': minima, 'integral_reviews': reviews,
        'quadrature_difference': quadrature_difference,
        'decay_rates_per_s': {'semidiscrete': discrete_rate, 'continuum': continuum_rate},
        'within_budgets': flags, 'all_trajectory_budgets_met': all(flags.values()),
        'continuum_spatial_budget_met': maxima['continuum_exact_cell_average_fraction'] <= budget['continuum_exact_cell_average_fraction_budget']}, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    reports, observations = {}, {}
    for name, path in settings['trajectories'].items():
        reports[name], rows = audit(root/path)
        observations[name] = [row for row in rows if row['kind'] in ('initial', 'sample')]
        print(json.dumps({'trajectory': name, 'all_trajectory_budgets_met': reports[name]['all_trajectory_budgets_met'],
            'continuum_spatial_budget_met': reports[name]['continuum_spatial_budget_met']}), flush=True)
    base, refined = observations['base'], observations['refined']
    same_times = [row['time_s'] for row in base] == [row['time_s'] for row in refined]
    difference = max(float(np.max(np.abs(np.asarray(a['mole_fractions'])-b['mole_fractions'])))
        for a, b in zip(base, refined, strict=True))
    budget = rows[0]['settings']['verification']['time_fraction_budget']
    comparison = {'observations': len(base), 'same_times': same_times,
        'maximum_fraction_difference': difference, 'budget': budget,
        'within_budget': same_times and difference <= budget}
    output = {'settings': settings, 'reports': reports, 'time_comparison': comparison,
        'all_trajectory_and_time_budgets_met': all(item['all_trajectory_budgets_met'] for item in reports.values()) and comparison['within_budget'],
        'continuum_spatial_budget_met': all(item['continuum_spatial_budget_met'] for item in reports.values()),
        'reference_scope': 'Independent binary Fick flux and semidiscrete/continuum cosine cell averages. Recorded previously source-qualified diffusivity held fixed. Mixing entropy only.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: output[key] for key in ['all_trajectory_and_time_budgets_met', 'continuum_spatial_budget_met', 'time_comparison']}), flush=True)


if __name__ == '__main__':
    main()
