"""Scientific differential-response comparison of the rigid reactive closure."""
import argparse
import json
from pathlib import Path

import numpy as np

from calcite_rigid_setup import build_rigid
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from sludge_sandbox.rigid_reactive_column import RigidReactiveColumn
from sludge_sandbox.rigid_reactive_exchange import rigid_reactive_face
from sludge_sandbox.rigid_reactive_tangent import inventory_tangent, face_tangents, column_jacobian


def observable(state):
    t = state['temperature_k']
    return np.array([
        t, state['co2_mol'], state['pressure_pa'],
        state['carbon_chemical_potential_j_mol']/t,
        state['nitrogen_chemical_potential_j_mol']/t, 1/t,
        state['co2_partial_enthalpy_j_mol'], state['nitrogen_partial_enthalpy_j_mol'],
        state['co2_mol']/(state['co2_mol']+state['nitrogen_mol']),
    ])


def face_observable(left, right, parameters):
    face = rigid_reactive_face(left, right, parameters)
    return np.array([face[k] for k in ('carbon_flow_mol_s', 'nitrogen_flow_mol_s', 'energy_flow_w', 'entropy_production_w_k')])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); budget = settings['budgets']
    config = json.loads((root/settings['model_parameters']).read_text())
    reaction, nitrogen, _, _, _, _, volume = build_rigid(root, config)
    cell = RigidCalciteMixture(reaction, nitrogen, volume, config, settings['cell'])
    states = [cell.at_inventory(s['temperature_k'], s['carbon_mol'], s['nitrogen_mol']) for s in settings['states']]
    inventories = [np.array([s[k] for k in ('carbon_mol', 'nitrogen_mol', 'internal_energy_j')]) for s in states]
    tangents = [inventory_tangent(cell, state) for state in states]
    records = []
    for specification, state, y, tangent in zip(settings['states'], states, inventories, tangents, strict=True):
        scales = np.array(specification['input_scales']); output_scales = np.array(settings['state_output_scales'])
        derivative = np.vstack((tangent['temperature'], tangent['co2'], tangent['pressure'], tangent['potential_over_temperature'],
                                tangent['inverse_temperature'], tangent['enthalpies'], tangent['fractions'][0]))
        analytic = derivative*scales/output_scales[:, None]
        hessian = scales[:, None]*tangent['entropy_hessian']*scales
        symmetry = float(np.max(np.abs(hessian-hessian.T)))
        eigenvalues = np.linalg.eigvalsh((hessian+hessian.T)/2)
        comparisons = []
        for step in settings['dimensionless_difference_steps']:
            numerical = np.zeros_like(analytic); branches = []
            for j in range(3):
                delta = np.eye(3)[j]*scales[j]*step
                lo, hi = cell.inventory_state(*(y-delta)), cell.inventory_state(*(y+delta))
                branches.extend((lo['phase'], hi['phase']))
                numerical[:, j] = (observable(hi)-observable(lo))/(2*step)/output_scales
            error = float(np.max(np.abs(numerical-analytic)))
            comparisons.append({'dimensionless_step': step, 'maximum_scaled_derivative_error': error,
                                'same_phase_branch': all(p == state['phase'] for p in branches),
                                'within_budget': error <= budget['state_scaled_derivative_absolute']})
        flags = {'derivatives': all(c['within_budget'] and c['same_phase_branch'] for c in comparisons),
                 'hessian_symmetry': symmetry <= budget['entropy_hessian_symmetry_j_k'],
                 'hessian_nonpositive': float(eigenvalues[-1]) <= budget['entropy_hessian_positive_eigenvalue_j_k']}
        records.append({'specification': specification, 'state': state, 'scaled_analytic_derivatives': analytic.tolist(),
                        'scaled_entropy_hessian': hessian.tolist(), 'hessian_symmetry_residual_j_k': symmetry,
                        'hessian_eigenvalues_j_k': eigenvalues.tolist(), 'comparisons': comparisons, 'within_budgets': flags})
    faces = []
    for left_index, right_index in settings['face_pairs']:
        pair = [states[left_index], states[right_index]]; indices = [left_index, right_index]
        analytic_pair = face_tangents(*pair, tangents[left_index], tangents[right_index], settings['face'])
        comparisons = []
        for step in settings['dimensionless_difference_steps']:
            maximum = 0.
            for side, index in enumerate(indices):
                scales = np.array(settings['states'][index]['input_scales'])
                output_scales = np.array(settings['face_output_scales'])
                analytic = analytic_pair[side]*scales/output_scales[:, None]
                numerical = np.zeros_like(analytic)
                for j in range(3):
                    delta = np.eye(3)[j]*scales[j]*step
                    low_pair, high_pair = pair.copy(), pair.copy()
                    low_pair[side] = cell.inventory_state(*(inventories[index]-delta))
                    high_pair[side] = cell.inventory_state(*(inventories[index]+delta))
                    numerical[:, j] = (face_observable(*high_pair, settings['face'])-face_observable(*low_pair, settings['face']))/(2*step)/output_scales
                maximum = max(maximum, float(np.max(np.abs(numerical-analytic))))
            comparisons.append({'dimensionless_step': step, 'maximum_scaled_derivative_error': maximum,
                                'within_budget': maximum <= budget['face_scaled_derivative_absolute']})
        faces.append({'state_indices': indices, 'comparisons': comparisons,
                      'within_budgets': all(c['within_budget'] for c in comparisons)})
    column = RigidReactiveColumn(reaction, nitrogen, volume, config, config['meshes'][settings['column_mesh']])
    scales = np.array(settings['column_inventory_scales']*(2*column.count-1)+[settings['column_entropy_scale_j_k']])
    analytic = column_jacobian(column, 0., column.initial).toarray()*scales/scales[:, None]
    comparisons = []
    for step in settings['dimensionless_difference_steps']:
        numerical = np.zeros_like(analytic)
        for j in range(len(column.initial)):
            delta = np.eye(len(column.initial))[j]*scales[j]*step
            numerical[:, j] = (column.rates(0., column.initial+delta)-column.rates(0., column.initial-delta))/(2*step)/scales
        error = float(np.max(np.abs(numerical-analytic)))
        comparisons.append({'dimensionless_step': step, 'maximum_scaled_derivative_error': error,
                            'within_budget': error <= budget['column_scaled_derivative_absolute']})
    result = {'settings': settings, 'states': records, 'faces': faces, 'column': comparisons,
              'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in records) and all(f['within_budgets'] for f in faces) and all(c['within_budget'] for c in comparisons),
              'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met']}))


if __name__ == '__main__':
    main()
