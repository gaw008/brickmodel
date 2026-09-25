"""Original-equation, entropy, reversal and pure-limit review of Dusty Gas."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.dusty_gas_isothermal import effective_knudsen_diffusivities, isothermal_dusty_gas_fluxes
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport
from sludge_sandbox.wilke_gas_mixture import wilke_viscosity_pa_s


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    local_p = json.loads((root/p['local_gas_parameters']).read_text())
    transport_p = json.loads((root/local_p['transport_parameters']).read_text())
    viscosity_p = json.loads((root/p['viscosity_parameters']).read_text())
    provider = NonpolarGasTransport(transport_p)
    names, review = p['species_order'], p['review']
    mp.mp.dps = review['decimal_precision']
    constants = local_p['constants']
    gas_constant = float(constants['boltzmann_j_k'])*float(constants['avogadro_mol_inverse'])
    masses = np.array([float(transport_p['species'][name]['molar_mass_g_mol'])*float(constants['gram_to_kg']) for name in names])
    permutation = review['species_permutation']
    states, records, pure_limits, knudsen_reviews = [], [], [], []
    for temperature in p['temperatures_k']:
        pure_viscosities = np.array([provider.viscosity_pa_s(temperature, name) for name in names])
        for pore in p['virtual_pore_sets']:
            knudsen = effective_knudsen_diffusivities(temperature, gas_constant, masses,
                pore['mean_pore_radius_m'], pore['porosity'], pore['tortuosity'])
            exact = [mp.mpf(2)/3*mp.mpf(pore['mean_pore_radius_m'])*mp.mpf(pore['porosity'])/mp.mpf(pore['tortuosity'])
                *mp.sqrt(8*mp.mpf(gas_constant)*temperature/(mp.pi*mp.mpf(mass))) for mass in masses]
            errors = [float(abs(mp.mpf(value)-target)/target) for value, target in zip(knudsen, exact, strict=True)]
            knudsen_reviews.append({'temperature_k': temperature, 'pore': pore['name'],
                'actual_m2_s': knudsen.tolist(), 'reference_decimal': list(map(str, exact)),
                'relative_errors': errors, 'within_budget': max(errors) <= review['knudsen_relative_budget']})
        for pressure in p['pressures_pa']:
            concentration = pressure/(gas_constant*temperature)
            diffusion = np.zeros((len(names), len(names)))
            for i, j in combinations(range(len(names)), 2):
                diffusion[i, j] = diffusion[j, i] = provider.binary_diffusivity_m2_s(temperature, pressure, names[i], names[j])
            for composition in p['compositions']:
                fractions = np.array(composition)
                viscosity = wilke_viscosity_pa_s(fractions, pure_viscosities, masses)['viscosity_pa_s']
                state_index = len(states)
                states.append({'temperature_k': temperature, 'pressure_pa': pressure, 'mole_fractions': composition,
                    'concentration_mol_m3': concentration, 'free_binary_diffusivities_m2_s': diffusion.tolist(),
                    'pure_viscosities_pa_s': pure_viscosities.tolist(), 'mixture_viscosity_pa_s': viscosity})
                for pore in p['virtual_pore_sets']:
                    effective = diffusion*pore['porosity']/pore['tortuosity']
                    knudsen = effective_knudsen_diffusivities(temperature, gas_constant, masses,
                        pore['mean_pore_radius_m'], pore['porosity'], pore['tortuosity'])
                    permeability_cases = [('specified_geometry', pore['permeability_m2'])]
                    if review['include_zero_permeability_limit']:
                        permeability_cases.append(('zero_Darcy_mathematical_limit', 0.0))
                    for permeability_case, permeability in permeability_cases:
                        for force in p['force_cases']:
                            gradient = np.array(force['composition_gradient_per_m'])/fractions+force['log_pressure_gradient_per_m']
                            def evaluate(x, g, d, k):
                                return isothermal_dusty_gas_fluxes(x, g, temperature, pressure, gas_constant,
                                    d, k, viscosity, permeability)
                            actual = evaluate(fractions, gradient, effective, knudsen)
                            reverse = evaluate(fractions, -gradient, effective, knudsen)
                            permuted = evaluate(fractions[permutation], gradient[permutation],
                                effective[np.ix_(permutation, permutation)], knudsen[permutation])
                            x, g, dk = list(map(mp.mpf, fractions)), list(map(mp.mpf, gradient)), list(map(mp.mpf, knudsen))
                            matrix, rhs = mp.matrix(len(names)), mp.matrix(len(names), 1)
                            pressure_gradient = mp.mpf(pressure)*mp.fsum(xi*gi for xi, gi in zip(x, g, strict=True))
                            for i in range(len(names)):
                                for j in range(len(names)):
                                    matrix[i, j] = (1/dk[i]+mp.fsum(x[k]/mp.mpf(effective[i,k]) for k in range(len(names)) if k != i)
                                        if i == j else -x[i]/mp.mpf(effective[i,j]))
                                rhs[i] = -mp.mpf(concentration)*x[i]*(g[i]+mp.mpf(permeability)/(mp.mpf(viscosity)*dk[i])*pressure_gradient)
                            reference = mp.lu_solve(matrix, rhs)
                            reference_entropy = -mp.mpf(gas_constant)*mp.fsum(reference[i]*g[i] for i in range(len(names)))
                            flux_error = max(float(abs(mp.mpf(actual['molar_fluxes_mol_m2_s'][i])-reference[i])) for i in range(len(names)))
                            residual = max(float(abs(mp.fsum(matrix[i,j]*mp.mpf(actual['molar_fluxes_mol_m2_s'][j]) for j in range(len(names)))-rhs[i])) for i in range(len(names)))
                            entropy_error = float(abs(mp.mpf(actual['entropy_force_w_m3_k'])-reference_entropy))
                            decomposition_error = float(abs(mp.mpf(actual['entropy_sum_w_m3_k'])-reference_entropy))
                            reversal_error = float(np.max(np.abs(actual['molar_fluxes_mol_m2_s']+reverse['molar_fluxes_mol_m2_s'])))
                            permutation_error = float(np.max(np.abs(actual['molar_fluxes_mol_m2_s'][permutation]-permuted['molar_fluxes_mol_m2_s'])))
                            flux_budget = review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*float(max(abs(value) for value in reference))
                            entropy_budget = review['absolute_entropy_budget_w_m3_k']+review['relative_entropy_budget']*float(abs(reference_entropy))
                            flags = {'original_flux': flux_error <= flux_budget,
                                'original_equations': residual <= review['original_equation_residual_budget_mol_m4'],
                                'force_entropy': entropy_error <= entropy_budget,
                                'entropy_decomposition': decomposition_error <= entropy_budget,
                                'reversal': reversal_error <= flux_budget, 'permutation': permutation_error <= flux_budget,
                                'nonnegative_entropy': min(actual[key] for key in ['entropy_force_w_m3_k',
                                    'entropy_molecular_w_m3_k', 'entropy_wall_w_m3_k', 'entropy_darcy_w_m3_k']) >= -review['absolute_entropy_budget_w_m3_k']}
                            records.append({'source_state_index': state_index, 'pore': pore['name'],
                                'permeability_case': permeability_case, 'permeability_m2': permeability,
                                'force': force, 'log_partial_concentration_gradient_per_m': gradient.tolist(),
                                'actual': {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in actual.items()},
                                'reference_fluxes_decimal': list(map(str, reference)), 'reference_entropy_decimal': str(reference_entropy),
                                'errors': {'flux_mol_m2_s': flux_error, 'original_equation_mol_m4': residual,
                                    'force_entropy_w_m3_k': entropy_error, 'decomposed_entropy_w_m3_k': decomposition_error,
                                    'reversal_flux_mol_m2_s': reversal_error, 'permutation_flux_mol_m2_s': permutation_error},
                                'within_budgets': flags})
            for pore in p['virtual_pore_sets']:
                knudsen = effective_knudsen_diffusivities(temperature, gas_constant, masses,
                    pore['mean_pore_radius_m'], pore['porosity'], pore['tortuosity'])
                for i, name in enumerate(names):
                    gradient = review['pure_log_pressure_gradient_per_m']
                    actual = isothermal_dusty_gas_fluxes([1.0], [gradient], temperature, pressure, gas_constant,
                        [[0.0]], [knudsen[i]], pure_viscosities[i], pore['permeability_m2'])
                    reference = -mp.mpf(concentration)*(mp.mpf(knudsen[i])+mp.mpf(pore['permeability_m2'])*pressure/mp.mpf(pure_viscosities[i]))*gradient
                    error = float(abs(mp.mpf(actual['molar_fluxes_mol_m2_s'][0])-reference))
                    allowed = review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*float(abs(reference))
                    pure_limits.append({'species': name, 'temperature_k': temperature, 'pressure_pa': pressure,
                        'pore': pore['name'], 'actual_flux_mol_m2_s': float(actual['molar_fluxes_mol_m2_s'][0]),
                        'reference_flux_decimal': str(reference), 'error_mol_m2_s': error, 'within_budget': error <= allowed})
    output = {'settings': p, 'local_gas_settings': local_p, 'transport_settings': transport_p,
        'viscosity_settings': viscosity_p, 'gas_constant_j_mol_k': gas_constant, 'molar_masses_kg_mol': masses.tolist(),
        'source_states': states, 'knudsen_reviews': knudsen_reviews, 'local_reviews': records, 'pure_limits': pure_limits,
        'all_requested_budgets_met': all(all(row['within_budgets'].values()) for row in records)
            and all(row['within_budget'] for row in pure_limits+knudsen_reviews),
        'reference_scope': '80-digit original nonsymmetric concentration equations on actual coefficient inputs. Knudsen formula independently evaluated; pure-fluid and Wilke qualifications retained separately.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'local_cases': len(records), 'pure_cases': len(pure_limits),
        'all_requested_budgets_met': output['all_requested_budgets_met']}), flush=True)


if __name__ == '__main__':
    main()
