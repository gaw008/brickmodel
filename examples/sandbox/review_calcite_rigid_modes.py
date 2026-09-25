"""Recompose continuum diffusion from entropy and compare discrete cosine modes."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from calcite_rigid_setup import build_rigid
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from sludge_sandbox.rigid_reactive_column import RigidReactiveColumn
from sludge_sandbox.rigid_reactive_tangent import inventory_tangent, column_jacobian


def uniform_config(config, specification):
    result = deepcopy(config)
    result['domain']['initial_regions'] = [{'start_fraction': 0., 'end_fraction': 1., **{k: specification[k] for k in
        ('temperature_k', 'carbon_density_mol_m3', 'nitrogen_density_mol_m3')}}]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); config = json.loads((root/settings['model_parameters']).read_text())
    reaction, nitrogen, _, _, _, _, volume = build_rigid(root, config)
    budget = settings['budgets']; scales = np.array(settings['density_scales_carbon_nitrogen_energy'])
    transport = config['transport']; records = []; stationary = None
    for specification in settings['states']:
        v = settings['cell_volume_m3']
        cell = RigidCalciteMixture(reaction, nitrogen, volume, config, {'calcium_mol': settings['calcium_density_mol_m3']*v,
            'nitrogen_mol': specification['nitrogen_density_mol_m3']*v, 'total_volume_m3': v})
        state = cell.at_inventory(specification['temperature_k'], specification['carbon_density_mol_m3']*v,
                                  specification['nitrogen_density_mol_m3']*v)
        tangent = inventory_tangent(cell, state); hessian = tangent['entropy_hessian']*v
        h = np.array([state['co2_partial_enthalpy_j_mol'], state['nitrogen_partial_enthalpy_j_mol']])
        fractions = np.array([state['co2_mol'], state['nitrogen_mol']]); fractions /= fractions.sum()
        counter = np.array([1., -1.])
        mobility = transport['bulk_mobility_mol2_k_j_m_s']*np.outer(fractions, fractions) + transport['counter_mobility_mol2_k_j_m_s']*np.outer(counter, counter)
        lift = np.vstack((np.eye(2), h))
        complete = lift@mobility@lift.T
        complete[2, 2] += transport['thermal_conductivity_w_m_k']*state['temperature_k']**2
        diffusion = -complete@hessian; scaled = diffusion*scales/scales[:, None]
        eigenvalues = np.linalg.eigvals(scaled)
        mode_reviews = []
        for mesh in settings['mesh_names']:
            column = RigidReactiveColumn(reaction, nitrogen, volume, uniform_config(config, specification), config['meshes'][mesh])
            jacobian = column_jacobian(column, 0., column.initial); n = column.count
            for wave in settings['cosine_wave_numbers']:
                profile = np.cos(wave*np.pi*(np.arange(n)+.5)/n)*np.sinc(wave/(2*n))
                discrete = 4*np.sin(wave*np.pi/(2*n))**2/column.width**2
                continuous = (wave*np.pi/config['domain']['length_m'])**2
                errors = []
                for coordinate in range(3):
                    amplitude = np.eye(3)[coordinate]*scales[coordinate]
                    direction = np.zeros_like(column.initial)
                    direction[:3*n] = (profile[:, None]*amplitude*column.volume).ravel()
                    actual = (jacobian@direction)[:3*n].reshape(n, 3)/column.volume
                    expected = -discrete*profile[:, None]*(diffusion@amplitude)
                    errors.append(float(np.max(np.abs(actual-expected)/scales)))
                mode_reviews.append({'mesh': mesh, 'wave_number': wave, 'discrete_wavenumber_squared_per_m2': discrete,
                    'continuous_wavenumber_squared_per_m2': continuous, 'relative_spectral_error': abs(discrete/continuous-1),
                    'scaled_operator_errors_per_s': errors,
                    'within_budget': max(errors) <= budget['dispersion_operator_scaled_absolute_per_s']})
        flags = {'real_spectrum': float(np.max(np.abs(eigenvalues.imag))) <= budget['diffusivity_imaginary_allowance_m2_s'],
            'nonnegative_spectrum': float(np.min(eigenvalues.real)) >= -budget['diffusivity_negative_allowance_m2_s'],
            'discrete_modes': all(m['within_budget'] for m in mode_reviews)}
        record = {'specification': specification, 'phase': state['phase'], 'reference_state': state,
            'density_entropy_hessian': hessian.tolist(), 'complete_mobility': complete.tolist(), 'diffusion_matrix_m2_s': diffusion.tolist(),
            'scaled_diffusion_matrix_m2_s': scaled.tolist(), 'diffusion_eigenvalues_real_m2_s': eigenvalues.real.tolist(),
            'diffusion_eigenvalues_imaginary_m2_s': eigenvalues.imag.tolist(), 'mode_reviews': mode_reviews, 'within_budgets': flags}
        if state['phase'] == 'coexistence':
            rho_g = state['co2_mol']/state['gas_volume_m3']; rho_n = state['nitrogen_mol']/state['gas_volume_m3']
            dgdc = -rho_g*cell.dv/(1-rho_g*cell.dv); dndc = -rho_n*cell.dv/(1-rho_g*cell.dv)
            uc = cell.reactant.standard(state['temperature_k'])['enthalpy_j_mol']-cell.p0*cell.vc
            ul = cell.product.standard(state['temperature_k'])['enthalpy_j_mol']-cell.p0*cell.vl
            un = cell.nitrogen.standard(state['temperature_k'])['enthalpy_j_mol']-cell.reaction.gas_constant_j_mol_k*state['temperature_k']
            null = np.array([1., dndc, uc-ul+state['reaction_internal_energy_j_mol']*dgdc+un*dndc])
            scaled_null = null/scales; scaled_null /= np.max(np.abs(scaled_null))
            null_error = float(np.max(np.abs(scaled@scaled_null)))
            record['coexistence_null_inventory_direction'] = null.tolist()
            record['scaled_null_error_m2_s'] = null_error
            flags['null_direction'] = null_error <= budget['coexistence_null_scaled_absolute_m2_s']
            case = settings['stationary_profile']; n = config['meshes'][case['mesh']]
            column = RigidReactiveColumn(reaction, nitrogen, volume, uniform_config(config, specification), n)
            profile = np.cos(case['wave_number']*np.pi*(np.arange(n)+.5)/n)*np.sinc(case['wave_number']/(2*n))
            amplitude = null*case['carbon_density_amplitude_mol_m3']
            values = column.initial.copy(); values[:3*n] += (profile[:, None]*amplitude*column.volume).ravel()
            states = column.states(values); faces = column.faces(states)
            metrics = {'temperature_range_k': float(np.ptp([s['temperature_k'] for s in states])),
                'pressure_range_pa': float(np.ptp([s['pressure_pa'] for s in states])),
                'species_flow_mol_s': max(abs(f[k]) for f in faces for k in ('carbon_flow_mol_s', 'nitrogen_flow_mol_s')),
                'energy_flow_w': max(abs(f['energy_flow_w']) for f in faces)}
            stationary_flags = {k: value <= budget['stationary_'+k] for k, value in metrics.items()}
            stationary_flags['all_coexistence'] = all(s['phase'] == 'coexistence' for s in states)
            stationary = {'inventory_density_amplitude': amplitude.tolist(), 'states': states, 'maximum_residuals': metrics, 'within_budgets': stationary_flags}
        records.append(record)
    result = {'settings': settings, 'records': records, 'stationary_profile': stationary,
        'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in records) and all(stationary['within_budgets'].values()),
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met']}))


if __name__ == '__main__':
    main()
