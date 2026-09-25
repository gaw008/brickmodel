"""Independent path integrals and exact binary limits for MS finite faces."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.maxwell_stefan_entropy_face import IsothermalMaxwellStefanFace
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    local_p = json.loads((root/p['local_law_parameters']).read_text())
    transport_p = json.loads((root/local_p['transport_parameters']).read_text())
    names, review = local_p['species_order'], p['review']
    mp.mp.dps = review['decimal_precision']
    constants = local_p['constants']
    gas_constant = float(mp.mpf(constants['boltzmann_j_k'])*mp.mpf(constants['avogadro_mol_inverse']))
    concentration = p['pressure_pa']/(gas_constant*p['temperature_k'])
    masses = [float(transport_p['species'][k]['molar_mass_g_mol'])*float(constants['gram_to_kg']) for k in names]
    source = NonpolarGasTransport(transport_p)
    diffusion = np.zeros((len(names), len(names)))
    for i, j in combinations(range(len(names)), 2):
        diffusion[i, j] = diffusion[j, i] = source.binary_diffusivity_m2_s(p['temperature_k'], p['pressure_pa'], names[i], names[j])
    distance = p['distance_m']
    records, binary = [], []
    for case in p['face_cases']:
        left, right = list(map(float, case['left'])), list(map(float, case['right']))
        left_mp, right_mp = list(map(mp.mpf, left)), list(map(mp.mpf, right))
        jump = [mp.log(right_mp[i]/left_mp[i]) for i in range(len(names))]
        diffusion_mp = mp.matrix(diffusion.tolist())
        n = len(names)

        def point_flux(s):
            geometric = [mp.exp(mp.log(left_mp[i])+s*jump[i]) for i in range(n)]
            total = mp.fsum(geometric)
            x = [a/total for a in geometric]
            mean_jump = mp.fsum(x[i]*jump[i] for i in range(n))
            gradient = [x[i]*(jump[i]-mean_jump)/mp.mpf(distance) for i in range(n)]
            matrix, rhs = mp.matrix(n-1), mp.matrix(n-1, 1)
            for i in range(n-1):
                for j in range(n-1):
                    matrix[i, j] = (mp.fsum(x[k]/diffusion_mp[i, k] for k in range(n) if k != i)
                        if i == j else -x[i]/diffusion_mp[i, j]) + x[i]/diffusion_mp[i, n-1]
                rhs[i] = -mp.mpf(concentration)*gradient[i]
            first = mp.lu_solve(matrix, rhs)
            return [*first, -mp.fsum(first)]

        interval = list(map(mp.mpf, review['reference_integral_subintervals']))
        reference = [mp.quad(lambda s: point_flux(s)[i], interval) for i in range(n)]
        reference_entropy = -mp.mpf(gas_constant)*mp.fsum(reference[i]*jump[i] for i in range(n))
        print(json.dumps({'case': case['name'], 'reference_complete': True}), flush=True)
        for order in p['quadrature_orders']:
            face = IsothermalMaxwellStefanFace(diffusion, concentration, masses, gas_constant, distance, order)
            actual, reverse = face.evaluate(left, right), face.evaluate(right, left)
            flux_error = max(float(abs(mp.mpf(actual['molar_fluxes_mol_m2_s'][i])-reference[i])) for i in range(n))
            entropy_error = float(abs(mp.mpf(actual['entropy_from_jump_w_m2_k'])-reference_entropy))
            path_error = float(abs(mp.mpf(actual['entropy_from_path_w_m2_k'])-reference_entropy))
            flip_error = float(np.max(np.abs(actual['molar_fluxes_mol_m2_s']+reverse['molar_fluxes_mol_m2_s'])))
            flip_entropy = abs(float(actual['entropy_from_jump_w_m2_k']-reverse['entropy_from_jump_w_m2_k']))
            closure = abs(float(sum(actual['molar_fluxes_mol_m2_s'])))
            flux_budget = review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*float(max(abs(v) for v in reference))
            entropy_budget = review['absolute_entropy_budget_w_m2_k']+review['relative_entropy_budget']*float(abs(reference_entropy))
            flags = {'flux': flux_error <= flux_budget, 'entropy_jump': entropy_error <= entropy_budget,
                'entropy_path': path_error <= entropy_budget, 'reversal_flux': flip_error <= flux_budget,
                'reversal_entropy': flip_entropy <= entropy_budget,
                'molar_sum': closure <= review['molar_sum_budget_mol_m2_s'],
                'nonnegative_entropy': float(actual['entropy_from_jump_w_m2_k']) >= -review['absolute_entropy_budget_w_m2_k']}
            records.append({'case': case, 'quadrature_order': order,
                'actual': {k: v.tolist() if isinstance(v, np.ndarray) else float(v) for k, v in actual.items()},
                'reference_flux_decimal': [str(v) for v in reference], 'reference_entropy_decimal': str(reference_entropy),
                'errors': {'flux_mol_m2_s': flux_error, 'entropy_jump_w_m2_k': entropy_error,
                    'entropy_path_w_m2_k': path_error, 'reversal_flux_mol_m2_s': flip_error,
                    'reversal_entropy_w_m2_k': flip_entropy, 'molar_sum_mol_m2_s': closure},
                'within_budgets': flags})
    for i, j in combinations(range(len(names)), 2):
        left, right = list(map(float, p['binary_left_fractions'])), list(map(float, p['binary_right_fractions']))
        d = diffusion[i, j]
        reference = [-mp.mpf(concentration)*mp.mpf(d)*(mp.mpf(right[k])-mp.mpf(left[k]))/mp.mpf(distance) for k in range(2)]
        for order in p['quadrature_orders']:
            face = IsothermalMaxwellStefanFace([[0, d], [d, 0]], concentration, [masses[i], masses[j]], gas_constant, distance, order)
            actual = face.evaluate(left, right)
            error = max(float(abs(mp.mpf(actual['molar_fluxes_mol_m2_s'][k])-reference[k])) for k in range(2))
            budget = review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*float(max(abs(v) for v in reference))
            binary.append({'species': [names[i], names[j]], 'quadrature_order': order,
                'actual_fluxes_mol_m2_s': actual['molar_fluxes_mol_m2_s'].tolist(),
                'exact_fick_fluxes_decimal': [str(v) for v in reference],
                'maximum_error_mol_m2_s': error, 'within_budget': error <= budget})
    by_order = {str(order): all(all(row['within_budgets'].values()) for row in records if row['quadrature_order'] == order)
        and all(row['within_budget'] for row in binary if row['quadrature_order'] == order) for order in p['quadrature_orders']}
    result = {'settings': p, 'local_law_settings': local_p, 'binary_diffusivity_m2_s': diffusion.tolist(),
        'source_transport_settings': transport_p, 'concentration_mol_m3': concentration, 'gas_constant_j_mol_k': gas_constant,
        'four_species_faces': records, 'exact_binary_limits': binary, 'all_requested_budgets_by_order': by_order,
        'material_qualified': False, 'training_eligible': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'all_requested_budgets_by_order': by_order}), flush=True)


if __name__ == '__main__':
    main()
