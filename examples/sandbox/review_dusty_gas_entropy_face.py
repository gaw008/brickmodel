"""MP source integrals and exact single-gas limits for Dusty Gas finite faces."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.dusty_gas_entropy_face import DustyGasEntropyFace
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    local_p = json.loads((root/p['local_law_parameters']).read_text())
    gas_p = json.loads((root/local_p['local_gas_parameters']).read_text())
    transport_p = json.loads((root/gas_p['transport_parameters']).read_text())
    source = NonpolarGasTransport(transport_p)
    names, constants, review = local_p['species_order'], gas_p['constants'], p['review']
    temperature = p['temperature_k']
    gas_constant = float(constants['boltzmann_j_k'])*float(constants['avogadro_mol_inverse'])
    masses = np.array([float(transport_p['species'][name]['molar_mass_g_mol'])*float(constants['gram_to_kg']) for name in names])
    viscosities = np.array([source.viscosity_pa_s(temperature, name) for name in names])
    products = np.zeros((len(names), len(names)))
    reference_pressure = p['binary_property_reference_pressure_pa']
    for i, j in combinations(range(len(names)), 2):
        products[i,j] = products[j,i] = reference_pressure*source.binary_diffusivity_m2_s(temperature, reference_pressure, names[i], names[j])
    pore = [row for row in local_p['virtual_pore_sets'] if row['name'] == p['virtual_pore_name']][0]
    mp.mp.dps = review['decimal_precision']
    rt = mp.mpf(gas_constant)*temperature
    eta, mass = list(map(mp.mpf, viscosities)), list(map(mp.mpf, masses))
    phi = [[(1+mp.sqrt(eta[i]/eta[j])*(mass[j]/mass[i])**mp.mpf('0.25'))**2
        /mp.sqrt(8*(1+mass[i]/mass[j])) for j in range(len(names))] for i in range(len(names))]
    scale = mp.mpf(pore['porosity'])/mp.mpf(pore['tortuosity'])
    knudsen = [mp.mpf(2)/3*mp.mpf(pore['mean_pore_radius_m'])*scale*mp.sqrt(8*rt/(mp.pi*m)) for m in mass]
    interval = list(map(mp.mpf, review['reference_integral_subintervals']))
    records, pure_limits = [], []
    for case in p['face_cases']:
        left = case['left_pressure_pa']/(gas_constant*temperature)*np.array(case['left_fractions'])
        right = case['right_pressure_pa']/(gas_constant*temperature)*np.array(case['right_fractions'])
        left_log = [mp.log(mp.mpf(value)) for value in left]
        jump = [mp.log(mp.mpf(right[i]))-left_log[i] for i in range(len(names))]
        gradient = [value/mp.mpf(p['distance_m']) for value in jump]

        def point_flux(position):
            c = [mp.exp(left_log[i]+position*jump[i]) for i in range(len(names))]
            total = mp.fsum(c)
            x = [value/total for value in c]
            viscosity = mp.fsum(x[i]*eta[i]/mp.fsum(phi[i][j]*x[j] for j in range(len(names))) for i in range(len(names)))
            pressure_gradient = rt*mp.fsum(c[i]*gradient[i] for i in range(len(names)))
            matrix, rhs = mp.matrix(len(names)), mp.matrix(len(names), 1)
            for i in range(len(names)):
                for j in range(len(names)):
                    matrix[i,j] = (1/knudsen[i]+mp.fsum(rt*c[k]/(mp.mpf(products[i,k])*scale) for k in range(len(names)) if k != i)
                        if i == j else -rt*c[i]/(mp.mpf(products[i,j])*scale))
                rhs[i] = -c[i]*(gradient[i]+mp.mpf(pore['permeability_m2'])/(viscosity*knudsen[i])*pressure_gradient)
            return mp.lu_solve(matrix, rhs)

        reference = [mp.quad(lambda s: point_flux(s)[i], interval) for i in range(len(names))]
        reference_entropy = -mp.mpf(gas_constant)*mp.fsum(reference[i]*jump[i] for i in range(len(names)))
        print(json.dumps({'case': case['name'], 'reference_complete': True}), flush=True)
        for order in p['quadrature_orders']:
            face = DustyGasEntropyFace(temperature, gas_constant, masses, viscosities, products, pore, p['distance_m'], order)
            actual, reverse = face.evaluate(left, right), face.evaluate(right, left)
            errors = {'flux_mol_m2_s': max(float(abs(mp.mpf(actual['molar_fluxes_mol_m2_s'][i])-reference[i])) for i in range(len(names))),
                'jump_entropy_w_m2_k': float(abs(mp.mpf(actual['entropy_from_jump_w_m2_k'])-reference_entropy)),
                'path_entropy_w_m2_k': float(abs(mp.mpf(actual['entropy_from_path_w_m2_k'])-reference_entropy)),
                'reversal_flux_mol_m2_s': float(np.max(np.abs(actual['molar_fluxes_mol_m2_s']+reverse['molar_fluxes_mol_m2_s']))),
                'reversal_entropy_w_m2_k': abs(actual['entropy_from_jump_w_m2_k']-reverse['entropy_from_jump_w_m2_k']),
                'flux_decomposition_mol_m2_s': float(np.max(np.abs(actual['molar_fluxes_mol_m2_s']-actual['diffusive_fluxes_mol_m2_s']-actual['darcy_fluxes_mol_m2_s'])))}
            flux_budget = review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*float(max(abs(value) for value in reference))
            entropy_budget = review['absolute_entropy_budget_w_m2_k']+review['relative_entropy_budget']*float(abs(reference_entropy))
            flags = {key: value <= (entropy_budget if 'entropy' in key else flux_budget) for key, value in errors.items()}
            flags['nonnegative_entropy_parts'] = min(actual[key] for key in ['entropy_from_jump_w_m2_k',
                'entropy_molecular_w_m2_k', 'entropy_wall_w_m2_k', 'entropy_darcy_w_m2_k']) >= -review['absolute_entropy_budget_w_m2_k']
            records.append({'case': case, 'quadrature_order': order,
                'left_partial_concentrations_mol_m3': left.tolist(), 'right_partial_concentrations_mol_m3': right.tolist(),
                'actual': {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in actual.items()},
                'reference_fluxes_decimal': list(map(str, reference)), 'reference_entropy_decimal': str(reference_entropy),
                'errors': errors, 'within_budgets': flags})
    for i, name in enumerate(names):
        left, right = [pressure/(gas_constant*temperature) for pressure in p['pure_limit_pressures_pa']]
        exact = -(knudsen[i]*(mp.mpf(right)-mp.mpf(left))
            +mp.mpf(pore['permeability_m2'])*rt/(2*eta[i])*(mp.mpf(right)**2-mp.mpf(left)**2))/mp.mpf(p['distance_m'])
        for order in p['quadrature_orders']:
            face = DustyGasEntropyFace(temperature, gas_constant, [masses[i]], [viscosities[i]], [[0]], pore, p['distance_m'], order)
            actual = float(face.evaluate([left], [right])['molar_fluxes_mol_m2_s'][0])
            error = float(abs(mp.mpf(actual)-exact))
            allowed = review['absolute_flux_budget_mol_m2_s']+review['relative_flux_budget']*float(abs(exact))
            pure_limits.append({'species': name, 'quadrature_order': order, 'actual_flux_mol_m2_s': actual,
                'exact_steady_flux_decimal': str(exact), 'error_mol_m2_s': error, 'within_budget': error <= allowed})
    by_order = {str(order): all(all(row['within_budgets'].values()) for row in records if row['quadrature_order'] == order)
        and all(row['within_budget'] for row in pure_limits if row['quadrature_order'] == order) for order in p['quadrature_orders']}
    result = {'settings': p, 'local_law_settings': local_p, 'gas_settings': gas_p,
        'transport_settings': transport_p, 'gas_constant_j_mol_k': gas_constant,
        'molar_masses_kg_mol': masses.tolist(), 'pure_viscosities_pa_s': viscosities.tolist(),
        'diffusivity_pressure_products_pa_m2_s': products.tolist(), 'pore': pore,
        'face_reviews': records, 'pure_limits': pure_limits,
        'all_requested_budgets_by_order': by_order, 'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'all_requested_budgets_by_order': by_order}), flush=True)


if __name__ == '__main__':
    main()
