"""Independent source and local entropy review for ideal-gas cross diffusion."""
import argparse
from itertools import combinations, product
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

from review_nonpolar_gas_transport import lagrange, source_array
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.maxwell_stefan_isothermal import local_fluxes
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    source_p = json.loads((root/p['transport_parameters']).read_text())
    review = p['review']
    mp.mp.dps = review['decimal_precision']
    names = p['species_order']
    model = NonpolarGasTransport(source_p)
    constants = p['constants']
    kb, avogadro = mp.mpf(constants['boltzmann_j_k']), mp.mpf(constants['avogadro_mol_inverse'])
    gas_constant = kb*avogadro
    masses = {k: mp.mpf(v['molar_mass_g_mol'])*mp.mpf(constants['gram_to_kg'])
              for k, v in source_p['species'].items()}
    cpp = (root/source_p['source_files']['collision_integrals']).read_text()
    tstar = source_array(cpp, 'tstar22')
    omega22 = source_array(cpp, 'omega22_table')[::8]
    astar = source_array(cpp, 'astar_table')[8:-8:8]

    def reference_diffusivity(t, pressure, left, right):
        a, b = source_p['species'][left], source_p['species'][right]
        reduced = t/mp.sqrt(mp.mpf(a['well_depth_over_kb_k'])*mp.mpf(b['well_depth_over_kb_k']))
        collision = lagrange(reduced, tstar, omega22)/lagrange(reduced, tstar, astar)
        diameter = (mp.mpf(a['diameter_angstrom'])+mp.mpf(b['diameter_angstrom']))/2*mp.mpf(source_p['constants']['angstrom_m'])
        reduced_mass = masses[left]*masses[right]/(masses[left]+masses[right])/avogadro
        return 3*kb*t/(16*pressure*diameter**2*collision)*mp.sqrt(2*kb*t/(mp.pi*reduced_mass))

    def reference_flux(x, gradient, diffusion, concentration):
        n = len(x)
        matrix, rhs = mp.matrix(n), mp.matrix(n, 1)
        for i in range(n-1):
            matrix[i, i] = mp.fsum(x[j]/diffusion[i, j] for j in range(n) if i != j)
            for j in range(n):
                if i != j:
                    matrix[i, j] = -x[i]/diffusion[i, j]
            rhs[i] = -concentration*gradient[i]
        for j in range(n):
            matrix[n-1, j] = 1
        return mp.lu_solve(matrix, rhs)

    rows, binary_rows = [], []
    for temperature, pressure in product(p['conditions']['temperatures_k'], p['conditions']['pressures_pa']):
        n = len(names)
        diffusion, ref_diffusion = np.zeros((n, n)), mp.matrix(n)
        for i, j in combinations(range(n), 2):
            diffusion[i, j] = diffusion[j, i] = model.binary_diffusivity_m2_s(temperature, pressure, names[i], names[j])
            ref_diffusion[i, j] = ref_diffusion[j, i] = reference_diffusivity(mp.mpf(temperature), mp.mpf(pressure), names[i], names[j])
        concentration = mp.mpf(pressure)/(gas_constant*temperature)
        for fractions, gradient_values in product(p['conditions']['mole_fraction_vectors'], p['conditions']['composition_gradients_per_m']):
            x, gradient = list(map(mp.mpf, fractions)), list(map(mp.mpf, gradient_values))
            actual = local_fluxes(list(map(float, x)), list(map(float, gradient)), diffusion,
                float(concentration), [float(masses[k]) for k in names], float(gas_constant))
            expected = reference_flux(x, gradient, ref_diffusion, concentration)
            relative_mass_velocity = mp.fsum(masses[k]*expected[i] for i, k in enumerate(names))/(
                concentration*mp.fsum(masses[k]*x[i] for i, k in enumerate(names)))
            expected_mass_frame = [expected[i]-concentration*x[i]*relative_mass_velocity for i in range(n)]
            entropy = -gas_constant*mp.fsum(expected[i]*gradient[i]/x[i] for i in range(n))
            flux_error = max(float(abs(mp.mpf(actual['molar_frame_fluxes_mol_m2_s'][i])-expected[i])) for i in range(n))
            mass_flux_error = max(float(abs(mp.mpf(actual['mass_frame_molar_fluxes_mol_m2_s'][i])-expected_mass_frame[i])) for i in range(n))
            flux_scale = float(max(abs(v) for v in expected))
            mass_flux_scale = float(max(abs(v) for v in expected_mass_frame))
            errors = {'molar_flux_mol_m2_s': flux_error, 'mass_frame_molar_flux_mol_m2_s': mass_flux_error,
                'entropy_force_w_m3_k': float(abs(mp.mpf(actual['entropy_force_w_m3_k'])-entropy)),
                'entropy_friction_w_m3_k': float(abs(mp.mpf(actual['entropy_friction_w_m3_k'])-entropy))}
            molar_sum = float(abs(sum(actual['molar_frame_fluxes_mol_m2_s'])))
            mass_sum = float(abs(sum(float(masses[k])*actual['mass_frame_molar_fluxes_mol_m2_s'][i] for i, k in enumerate(names))))
            flux = list(map(mp.mpf, actual['molar_frame_fluxes_mol_m2_s']))
            residual = max(float(abs(mp.fsum((x[j]*flux[i]-x[i]*flux[j])/ref_diffusion[i, j]
                for j in range(n) if i != j)+concentration*gradient[i])) for i in range(n))
            mass_entropy = -float(gas_constant)*sum(actual['mass_frame_molar_fluxes_mol_m2_s'][i]*float(gradient[i]/x[i]) for i in range(n))
            entropy_budget = review['absolute_entropy_budget_w_m3_k'] + review['relative_entropy_budget']*float(abs(entropy))
            flags = {
                'molar_flux': flux_error <= review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*flux_scale,
                'mass_frame_flux': mass_flux_error <= review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*mass_flux_scale,
                'entropy_force': errors['entropy_force_w_m3_k'] <= entropy_budget,
                'entropy_friction': errors['entropy_friction_w_m3_k'] <= entropy_budget,
                'entropy_frame_invariance': abs(mass_entropy-actual['entropy_force_w_m3_k']) <= entropy_budget,
                'entropy_nonnegative': actual['entropy_force_w_m3_k'] >= -review['absolute_entropy_budget_w_m3_k'],
                'molar_frame_sum': molar_sum <= review['molar_frame_sum_budget_mol_m2_s'],
                'mass_frame_sum': mass_sum <= review['mass_frame_sum_budget_kg_m2_s'],
                'all_original_equations': residual <= review['equation_residual_budget_mol_m4']}
            rows.append({'temperature_k': temperature, 'pressure_pa': pressure, 'mole_fractions': fractions,
                'gradient_per_m': gradient_values, 'binary_diffusivity_m2_s': diffusion.tolist(),
                'actual': {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in actual.items()},
                'reference_flux_decimal': [str(v) for v in expected], 'reference_entropy_decimal': str(entropy),
                'errors': errors, 'molar_sum_mol_m2_s': molar_sum, 'mass_sum_kg_m2_s': mass_sum,
                'maximum_original_equation_residual_mol_m4': residual,
                'zero_gradient_species_nonzero_flux': [names[i] for i in range(n) if gradient[i] == 0
                    and abs(actual['molar_frame_fluxes_mol_m2_s'][i]) > review['absolute_flux_budget_mol_m2_s']],
                'uphill_species': [names[i] for i in range(n) if actual['molar_frame_fluxes_mol_m2_s'][i]*float(gradient[i]) > 0],
                'within_budgets': {key: bool(value) for key, value in flags.items()}})
        for i, j in combinations(range(n), 2):
            x = list(map(float, review['binary_mole_fractions']))
            gradient = list(map(float, review['binary_gradient_per_m']))
            actual = local_fluxes(x, gradient, [[0, diffusion[i, j]], [diffusion[i, j], 0]],
                float(concentration), [float(masses[names[i]]), float(masses[names[j]])], float(gas_constant))
            expected = [-concentration*ref_diffusion[i, j]*mp.mpf(v) for v in review['binary_gradient_per_m']]
            error = max(float(abs(mp.mpf(actual['molar_frame_fluxes_mol_m2_s'][k])-expected[k])) for k in range(2))
            binary_rows.append({'species': [names[i], names[j]], 'temperature_k': temperature, 'pressure_pa': pressure,
                'fluxes_mol_m2_s': actual['molar_frame_fluxes_mol_m2_s'].tolist(),
                'fick_reference_decimal': [str(v) for v in expected], 'absolute_error_mol_m2_s': error,
                'within_budget': error <= review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*float(max(abs(v) for v in expected))})
    result = {'settings': p, 'transport_source_settings': source_p, 'local_states': rows, 'binary_limits': binary_rows,
        'all_requested_equation_and_source_budgets_met': all(all(row['within_budgets'].values()) for row in rows)
            and all(row['within_budget'] for row in binary_rows),
        'binary_diffusivities_experimentally_validated': False, 'material_qualified': False, 'training_eligible': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'local_states': len(rows), 'binary_limits': len(binary_rows),
        'all_requested_equation_and_source_budgets_met': result['all_requested_equation_and_source_budgets_met']}), flush=True)


if __name__ == '__main__':
    main()
