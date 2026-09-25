"""Independent pure-Knudsen flux, pore storage, density entropy and cosine review."""
import argparse
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_maxwell_stefan_binary_column import polynomial


def audit(path):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream]
    header, initial = rows[:2]
    p, count = header['settings'], header['cell_count']
    budget = p['verification']
    area, length, porosity = p['geometry']['area_m2'], p['geometry']['length_m'], p['pore']['porosity']
    width, pore_volume = length/count, porosity*area*length/count
    gas_constant = header['gas_constant_j_mol_k']
    rt = gas_constant*p['temperature_k']
    reference_concentration = p['entropy_reference_pressure_pa']/rt
    knudsen = header['effective_knudsen_diffusivities_m2_s'][0]
    mean = p['initial']['mean_partial_pressures_pa'][0]/rt
    amplitude = p['initial']['cosine_partial_pressure_amplitudes_pa'][0]/rt
    wave = p['initial']['cosine_mode']*np.pi/length
    centers = (np.arange(count)+0.5)*width
    cosine = np.cos(wave*centers)*np.sinc(wave*width/(2*np.pi))
    decay_discrete = 4*(knudsen/porosity)*np.sin(wave*width/2)**2/width**2
    decay_continuum = (knudsen/porosity)*wave**2
    maxima = dict.fromkeys(['concentration_encoding_mol_m3', 'inventory_encoding_mol',
        'pressure_encoding_pa', 'entropy_encoding_j_k', 'face_flux_mol_m2_s',
        'face_entropy_rate_w_k', 'global_species_mol',
        'semidiscrete_exact_concentration_mol_m3', 'continuum_exact_concentration_mol_m3'], 0.0)
    minima = {'concentration_mol_m3': float('inf'), 'face_entropy_rate_w_k': float('inf')}
    counts = {'recorded': 0, 'dense': 0}

    def reference(values, at, category):
        counts[category] += 1
        concentration = np.asarray(values)
        inventory = pore_volume*concentration
        entropy = -gas_constant*inventory*np.log(concentration/reference_concentration)
        flux = np.zeros(count+1)
        flux[1:-1] = -knudsen*np.diff(concentration)/width
        production = -gas_constant*area*flux[1:-1]*np.diff(np.log(concentration/reference_concentration))
        inventory_rate = area*(flux[:-1]-flux[1:])
        entropy_rate = -gas_constant*(np.log(concentration/reference_concentration)+1)*inventory_rate
        minima['concentration_mol_m3'] = min(minima['concentration_mol_m3'], float(concentration.min()))
        minima['face_entropy_rate_w_k'] = min(minima['face_entropy_rate_w_k'], float(production.min()))
        maxima['global_species_mol'] = max(maxima['global_species_mol'], abs(float(np.sum(inventory))-porosity*area*length*mean))
        for name, rate in [('semidiscrete_exact_concentration_mol_m3', decay_discrete), ('continuum_exact_concentration_mol_m3', decay_continuum)]:
            exact = mean+amplitude*cosine*np.exp(-rate*at)
            maxima[name] = max(maxima[name], float(np.max(np.abs(concentration-exact))))
        return concentration, inventory, entropy, flux[1:-1], production, inventory_rate, entropy_rate

    recorded = [row for row in rows if row['kind'] in ('initial', 'accepted', 'sample')]
    recorded.append(rows[-1]['final'])
    for row in recorded:
        concentration, inventory, entropy, flux, production, _, _ = reference(row['values'], row['time_s'], 'recorded')
        for name, error in [
                ('concentration_encoding_mol_m3', np.max(np.abs(concentration-np.asarray(row['partial_concentrations_mol_m3'])[:,0]))),
                ('inventory_encoding_mol', np.max(np.abs(inventory-np.asarray(row['inventories_mol'])[:,0]))),
                ('pressure_encoding_pa', max(np.max(np.abs(rt*concentration-row['pressure_pa'])),
                    np.max(np.abs(rt*concentration-np.asarray(row['partial_pressures_pa'])[:,0])))),
                ('entropy_encoding_j_k', np.max(np.abs(entropy-row['relative_ideal_entropy_j_k']))),
                ('face_flux_mol_m2_s', max(np.max(np.abs(flux-[face['molar_fluxes_mol_m2_s'][0] for face in row['faces']])),
                    np.max(np.abs(flux-[face['diffusive_fluxes_mol_m2_s'][0] for face in row['faces']])),
                    max(abs(face['darcy_fluxes_mol_m2_s'][0]) for face in row['faces']))),
                ('face_entropy_rate_w_k', max(np.max(np.abs(production-area*np.array([face[key] for face in row['faces']])))
                    for key in ['entropy_from_jump_w_m2_k', 'entropy_from_path_w_m2_k', 'entropy_wall_w_m2_k']))]:
            maxima[name] = max(maxima[name], float(error))
    initial_n = np.asarray(initial['inventories_mol'])[:,0]
    initial_s = np.asarray(initial['relative_ideal_entropy_j_k'])
    limits = {'local_species_mol': budget['local_species_budget_mol'],
        'cumulative_species_mol': budget['local_species_budget_mol'],
        'local_entropy_j_k': budget['local_entropy_budget_j_k'],
        'cumulative_local_entropy_j_k': budget['cumulative_entropy_budget_j_k'],
        'local_total_entropy_j_k': budget['local_entropy_budget_j_k'],
        'cumulative_total_entropy_j_k': budget['cumulative_entropy_budget_j_k']}
    reviews, final_integrals = [], []
    for order in budget['entropy_quadrature_orders']:
        nodes, weights = leggauss(order)
        cumulative_n, cumulative_s, cumulative_p = np.zeros(count), np.zeros(count), 0.0
        previous_n, previous_s = initial_n, initial_s
        errors, minimum_step = dict.fromkeys(limits, 0.0), float('inf')
        for row in rows:
            if row['kind'] != 'accepted':
                continue
            dense = row['dense_output']
            left, right = dense['start_time_s'], dense['end_time_s']
            integral_n, integral_s, integral_p = np.zeros(count), np.zeros(count), 0.0
            for node, weight in zip(nodes, weights, strict=True):
                at = (left+right)/2+(right-left)*node/2
                _, _, _, _, production, n_rate, s_rate = reference(polynomial(row, at), at, 'dense')
                factor = weight*(right-left)/2
                integral_n += factor*n_rate
                integral_s += factor*s_rate
                integral_p += factor*float(np.sum(production))
            cumulative_n += integral_n
            cumulative_s += integral_s
            cumulative_p += integral_p
            inventory, entropy = np.asarray(row['inventories_mol'])[:,0], np.asarray(row['relative_ideal_entropy_j_k'])
            residuals = {'local_species_mol': np.max(np.abs(inventory-previous_n-integral_n)),
                'cumulative_species_mol': np.max(np.abs(inventory-initial_n-cumulative_n)),
                'local_entropy_j_k': np.max(np.abs(entropy-previous_s-integral_s)),
                'cumulative_local_entropy_j_k': np.max(np.abs(entropy-initial_s-cumulative_s)),
                'local_total_entropy_j_k': abs(float(np.sum(entropy-previous_s))-integral_p),
                'cumulative_total_entropy_j_k': abs(float(np.sum(entropy-initial_s))-cumulative_p)}
            for name, value in residuals.items():
                errors[name] = max(errors[name], float(value))
            minimum_step = min(minimum_step, float(np.sum(entropy-previous_s)))
            previous_n, previous_s = inventory, entropy
        final_integrals.append((cumulative_n, cumulative_s, float(cumulative_p)))
        flags = {name: value <= limits[name] for name, value in errors.items()}
        flags['nonnegative_step_entropy'] = minimum_step >= -budget['negative_step_entropy_budget_j_k']
        reviews.append({'order': order, 'maximum_residuals': errors, 'minimum_step_total_entropy_j_k': minimum_step,
            'total_entropy_production_j_k': float(cumulative_p), 'within_budgets': flags})
    first, last = final_integrals[0], final_integrals[-1]
    differences = {'species_mol': float(np.max(np.abs(first[0]-last[0]))),
        'local_entropy_j_k': float(np.max(np.abs(first[1]-last[1]))), 'total_entropy_j_k': abs(first[2]-last[2])}
    flags = {'completed': rows[-1]['status'] == 'completed',
        'positive_concentration': minima['concentration_mol_m3'] > 0,
        'nonnegative_face_entropy': minima['face_entropy_rate_w_k'] >= 0,
        'concentration_encoding': maxima['concentration_encoding_mol_m3'] <= budget['source_concentration_budget_mol_m3'],
        'inventory_encoding': maxima['inventory_encoding_mol'] <= budget['global_species_budget_mol'],
        'pressure_encoding': maxima['pressure_encoding_pa'] <= rt*budget['source_concentration_budget_mol_m3'],
        'entropy_encoding': maxima['entropy_encoding_j_k'] <= budget['local_entropy_budget_j_k'],
        'face_flux': maxima['face_flux_mol_m2_s'] <= budget['source_flux_absolute_budget_mol_m2_s'],
        'face_entropy': maxima['face_entropy_rate_w_k'] <= budget['source_entropy_rate_budget_w_k'],
        'global_species': maxima['global_species_mol'] <= budget['global_species_budget_mol'],
        'semidiscrete_exact': maxima['semidiscrete_exact_concentration_mol_m3'] <= budget['semidiscrete_exact_concentration_budget_mol_m3'],
        'whole_trajectory_balances': all(all(row['within_budgets'].values()) for row in reviews),
        'quadrature_species': differences['species_mol'] <= budget['local_species_budget_mol'],
        'quadrature_entropy': max(differences['local_entropy_j_k'], differences['total_entropy_j_k']) <= budget['cumulative_entropy_budget_j_k']}
    return {'trajectory': str(path), 'cell_count': count, 'counts': counts,
        'accepted_steps': rows[-1]['steps'], 'maxima': maxima, 'minima': minima,
        'decay_rates_per_s': {'discrete': decay_discrete, 'continuum': decay_continuum},
        'integral_reviews': reviews, 'quadrature_difference': differences,
        'within_budgets': flags, 'all_trajectory_budgets_met': all(flags.values()),
        'continuum_spatial_budget_met': maxima['continuum_exact_concentration_mol_m3'] <= budget['continuum_exact_cell_average_concentration_budget_mol_m3']}, rows


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
    difference = max(float(np.max(np.abs(np.asarray(a['values'])-b['values']))) for a,b in zip(base, refined, strict=True))
    budget = rows[0]['settings']['verification']['time_concentration_budget_mol_m3']
    comparison = {'observations': len(base), 'same_times': same_times,
        'maximum_concentration_difference_mol_m3': difference, 'budget_mol_m3': budget,
        'within_budget': same_times and difference <= budget}
    output = {'settings': settings, 'reports': reports, 'time_comparison': comparison,
        'all_trajectory_and_time_budgets_met': all(row['all_trajectory_budgets_met'] for row in reports.values()) and comparison['within_budget'],
        'continuum_spatial_budget_met': all(row['continuum_spatial_budget_met'] for row in reports.values()),
        'reference_scope': 'Independent pure Knudsen flux and cosine solutions with transient D_K/porosity, held at previously source-qualified coefficient. Relative density entropy only.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: output[key] for key in ['all_trajectory_and_time_budgets_met', 'continuum_spatial_budget_met', 'time_comparison']}), flush=True)


if __name__ == '__main__':
    main()
