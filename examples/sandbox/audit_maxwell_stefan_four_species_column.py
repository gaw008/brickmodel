"""Full independent multicomponent diffusion and mixing-entropy review."""
import argparse
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_maxwell_stefan_binary_column import polynomial
from maxwell_stefan_column_reference import ColumnReference


def audit(path):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream]
    header, initial = rows[:2]
    p = header['settings']
    budget = p['verification']
    reference = ColumnReference(header)
    maxima = {key: 0.0 for key in ['fraction_encoding', 'inventory_encoding_mol',
        'entropy_encoding_j_k', 'face_flux_mol_m2_s', 'face_entropy_rate_w_k',
        'original_equation_mol_m4', 'molar_flux_sum_mol_m2_s', 'global_species_mol',
        'reference_entropy_identity_w_k']}
    minima = {'mole_fraction': float('inf'), 'face_entropy_rate_w_k': float('inf')}
    counts = {'recorded': 0, 'dense': 0}
    total_inventory = (reference.concentration*p['geometry']['area_m2']*p['geometry']['length_m']
        *np.asarray(p['initial']['mean_mole_fractions']))

    def observe(values, category):
        counts[category] += 1
        state = reference.evaluate(values)
        minima['mole_fraction'] = min(minima['mole_fraction'], float(state['fractions'].min()))
        minima['face_entropy_rate_w_k'] = min(minima['face_entropy_rate_w_k'], float(state['production'].min()))
        for key, value in [
                ('original_equation_mol_m4', state['original_equation_residual_mol_m4']),
                ('molar_flux_sum_mol_m2_s', state['molar_flux_sum_mol_m2_s']),
                ('global_species_mol', np.max(np.abs(np.sum(state['inventories'], axis=0)-total_inventory))),
                ('reference_entropy_identity_w_k', max(np.max(np.abs(state['production']-state['path_production'])),
                    abs(np.sum(state['entropy_rate'])-np.sum(state['production']))))]:
            maxima[key] = max(maxima[key], float(value))
        return state

    recorded = [row for row in rows if row['kind'] in ('initial', 'accepted', 'sample')]
    recorded.append(rows[-1]['final'])
    for row in recorded:
        state = observe(row['values'], 'recorded')
        for key, error in [
                ('fraction_encoding', np.max(np.abs(state['fractions']-row['mole_fractions']))),
                ('inventory_encoding_mol', np.max(np.abs(state['inventories']-row['inventories_mol']))),
                ('entropy_encoding_j_k', np.max(np.abs(state['entropy']-row['mixing_entropy_j_k']))),
                ('face_flux_mol_m2_s', np.max(np.abs(state['flux']-[face['molar_fluxes_mol_m2_s'] for face in row['faces']]))),
                ('face_entropy_rate_w_k', max(np.max(np.abs(state['production']-reference.area*np.array([face[k] for face in row['faces']])))
                    for k in ['entropy_from_jump_w_m2_k', 'entropy_from_path_w_m2_k']))]:
            maxima[key] = max(maxima[key], float(error))
    wave = p['initial']['cosine_mode']*np.pi/p['geometry']['length_m']
    centers = (np.arange(reference.count)+0.5)*reference.width
    exact_initial = np.asarray(p['initial']['mean_mole_fractions'])+np.outer(
        np.cos(wave*centers)*np.sinc(wave*reference.width/(2*np.pi)), p['initial']['cosine_amplitudes'])
    initial_error = float(np.max(np.abs(exact_initial-initial['mole_fractions'])))
    initial_n, initial_s = np.asarray(initial['inventories_mol']), np.asarray(initial['mixing_entropy_j_k'])
    reviews, final_integrals = [], []
    limits = {'local_species_mol': budget['local_species_budget_mol'],
        'cumulative_species_mol': budget['local_species_budget_mol'],
        'local_mixing_entropy_j_k': budget['local_mixing_entropy_budget_j_k'],
        'cumulative_local_mixing_entropy_j_k': budget['cumulative_mixing_entropy_budget_j_k'],
        'local_total_mixing_entropy_j_k': budget['local_mixing_entropy_budget_j_k'],
        'cumulative_total_mixing_entropy_j_k': budget['cumulative_mixing_entropy_budget_j_k']}
    for order in budget['entropy_quadrature_orders']:
        nodes, weights = leggauss(order)
        cumulative_n, cumulative_s, cumulative_p = np.zeros_like(initial_n), np.zeros_like(initial_s), 0.0
        previous_n, previous_s = initial_n, initial_s
        errors = dict.fromkeys(limits, 0.0)
        minimum_step = float('inf')
        for row in rows:
            if row['kind'] != 'accepted':
                continue
            dense = row['dense_output']
            left, right = dense['start_time_s'], dense['end_time_s']
            integral_n, integral_s, integral_p = np.zeros_like(initial_n), np.zeros_like(initial_s), 0.0
            for node, weight in zip(nodes, weights, strict=True):
                at = (left+right)/2+(right-left)*node/2
                state = observe(polynomial(row, at), 'dense')
                factor = weight*(right-left)/2
                integral_n += factor*state['inventory_rate']
                integral_s += factor*state['entropy_rate']
                integral_p += factor*float(np.sum(state['production']))
            cumulative_n += integral_n
            cumulative_s += integral_s
            cumulative_p += integral_p
            inventory, entropy = np.asarray(row['inventories_mol']), np.asarray(row['mixing_entropy_j_k'])
            residuals = {'local_species_mol': np.max(np.abs(inventory-previous_n-integral_n)),
                'cumulative_species_mol': np.max(np.abs(inventory-initial_n-cumulative_n)),
                'local_mixing_entropy_j_k': np.max(np.abs(entropy-previous_s-integral_s)),
                'cumulative_local_mixing_entropy_j_k': np.max(np.abs(entropy-initial_s-cumulative_s)),
                'local_total_mixing_entropy_j_k': abs(float(np.sum(entropy-previous_s))-integral_p),
                'cumulative_total_mixing_entropy_j_k': abs(float(np.sum(entropy-initial_s))-cumulative_p)}
            for key, value in residuals.items():
                errors[key] = max(errors[key], float(value))
            minimum_step = min(minimum_step, float(np.sum(entropy-previous_s)))
            previous_n, previous_s = inventory, entropy
        final_integrals.append((cumulative_n, cumulative_s, float(cumulative_p)))
        flags = {key: value <= limits[key] for key, value in errors.items()}
        flags['nonnegative_step_total_mixing_entropy'] = minimum_step >= -budget['negative_step_mixing_entropy_budget_j_k']
        reviews.append({'order': order, 'maximum_residuals': errors,
            'minimum_step_total_mixing_entropy_j_k': minimum_step,
            'total_mixing_entropy_production_j_k': float(cumulative_p), 'within_budgets': flags})
    first, last = final_integrals[0], final_integrals[-1]
    differences = {'species_mol': float(np.max(np.abs(first[0]-last[0]))),
        'local_mixing_entropy_j_k': float(np.max(np.abs(first[1]-last[1]))),
        'total_mixing_entropy_j_k': abs(first[2]-last[2])}
    flags = {'completed': rows[-1]['status'] == 'completed',
        'positive_fractions': minima['mole_fraction'] > 0,
        'nonnegative_face_entropy': minima['face_entropy_rate_w_k'] >= 0,
        'initial_profile': initial_error <= budget['time_fraction_budget'],
        'fraction_encoding': maxima['fraction_encoding'] == 0,
        'inventory_encoding': maxima['inventory_encoding_mol'] <= budget['global_species_budget_mol'],
        'entropy_encoding': maxima['entropy_encoding_j_k'] <= budget['local_mixing_entropy_budget_j_k'],
        'face_flux': maxima['face_flux_mol_m2_s'] <= budget['source_flux_absolute_budget_mol_m2_s'],
        'face_entropy': maxima['face_entropy_rate_w_k'] <= budget['source_entropy_rate_budget_w_k'],
        'original_equations': maxima['original_equation_mol_m4'] <= budget['reference_equation_residual_budget_mol_m4'],
        'molar_frame': maxima['molar_flux_sum_mol_m2_s'] <= budget['molar_frame_flux_sum_budget_mol_m2_s'],
        'global_species': maxima['global_species_mol'] <= budget['global_species_budget_mol'],
        'reference_entropy_identity': maxima['reference_entropy_identity_w_k'] <= budget['source_entropy_rate_budget_w_k'],
        'whole_trajectory_balances': all(all(review['within_budgets'].values()) for review in reviews),
        'quadrature_species': differences['species_mol'] <= budget['local_species_budget_mol'],
        'quadrature_entropy': max(differences['local_mixing_entropy_j_k'], differences['total_mixing_entropy_j_k']) <= budget['cumulative_mixing_entropy_budget_j_k']}
    return {'trajectory': str(path), 'cell_count': reference.count, 'counts': counts,
        'accepted_steps': rows[-1]['steps'], 'maxima': maxima, 'minima': minima,
        'initial_profile_error': initial_error, 'integral_reviews': reviews,
        'quadrature_difference': differences, 'within_budgets': flags,
        'all_requested_budgets_met': all(flags.values())}, rows


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
        print(json.dumps({'trajectory': name, 'all_requested_budgets_met': reports[name]['all_requested_budgets_met']}), flush=True)
    base, refined = observations['base'], observations['refined']
    same_times = [row['time_s'] for row in base] == [row['time_s'] for row in refined]
    difference = max(float(np.max(np.abs(np.asarray(a['mole_fractions'])-b['mole_fractions'])))
        for a, b in zip(base, refined, strict=True))
    budget = rows[0]['settings']['verification']['time_fraction_budget']
    comparison = {'observations': len(base), 'same_times': same_times,
        'maximum_fraction_difference': difference, 'budget': budget,
        'within_budget': same_times and difference <= budget}
    output = {'settings': settings, 'reports': reports, 'time_comparison': comparison,
        'all_requested_budgets_met': all(item['all_requested_budgets_met'] for item in reports.values()) and comparison['within_budget'],
        'reference_scope': 'Independent original MS molar-flux equations with 64-node face integration and 2/4-node accepted-step integration. Previously source-qualified free-gas D held fixed. Mixing entropy only.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'all_requested_budgets_met': output['all_requested_budgets_met'], 'time_comparison': comparison}), flush=True)


if __name__ == '__main__':
    main()
