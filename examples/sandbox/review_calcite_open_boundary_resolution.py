"""Resolve the initial boundary trace without integrating very fine columns."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from calcite_rigid_setup import build_rigid
from calcite_rigid_source_review import independent_face
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn
from sludge_sandbox.rigid_reactive_surface import RigidReactiveSurface


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    policy = json.loads((root/settings['column_parameters']).read_text())
    config = json.loads((root/policy['model_parameters']).read_text())
    surface = json.loads((root/policy['surface_parameters']).read_text())['surface']
    reaction, nitrogen, _, _, _, _, volume = build_rigid(root, config)
    column = OpenRigidReactiveColumn(reaction, nitrogen, volume, config, policy, surface, 1)
    segment = settings['segment_index']
    _, states, _, reservoir, _ = column.observe(column.initial, segment)
    bulk = states[0]
    wall = policy['boundary_program'][segment]['radiation_temperature_k']
    budget = policy['verification']
    records = []
    for count in settings['cell_counts']:
        parameters = deepcopy(column.surface_parameters)
        distance = policy['domain']['length_m']/(2*count)
        parameters['interior']['distance_m'] = distance
        contact = RigidReactiveSurface(column.cells[0], parameters)
        solved = contact.solve(bulk, reservoir, wall)
        trace = solved['surface']
        inner = independent_face(bulk, trace, column.cells[0], contact.interior)
        outer = independent_face(trace, reservoir, column.cells[0], contact.exterior)
        radiation = contact.radiation_factor*(wall**4-trace['temperature_k']**4)
        residual = inner[:3]-outer[:3]
        residual[2] += radiation
        entropy = [float(inner[3]+inner[4]), float(outer[3]+outer[4]),
                   float(radiation*(1/trace['temperature_k']-1/wall))]
        difference = float(abs(trace['temperature_k']-records[-1]['surface']['temperature_k'])) if records else None
        records.append({
            'equivalent_uniform_cell_count': count,
            'half_cell_distance_m': distance, 'surface': trace,
            'difference_to_bulk_temperature_k': trace['temperature_k']-bulk['temperature_k'],
            'difference_to_previous_surface_temperature_k': difference,
            'pair_temperature_budget_met': None if difference is None else bool(difference<=settings['surface_temperature_pair_budget_k']),
            'independent_C_N_U_balance_residual': residual.tolist(),
            'independent_entropy_productions_w_k': entropy,
            'inner_flux_C_N_E': inner[:3].tolist(), 'outer_flux_C_N_E': outer[:3].tolist(),
            'radiation_in_w': radiation,
            'root_evaluations': solved['root_evaluations'],
            'root_balance_within_original_budgets': bool(np.max(np.abs(residual[:2]))<=budget['surface_species_mol_s'] and abs(residual[2])<=budget['surface_energy_w'])})
    result = {'settings': settings, 'bulk': bulk, 'reservoir': reservoir, 'records': records,
        'limiting_trace_reason': 'At vanishing positive half-cell distance, finite exterior flux requires the interior positive heat and species forces to vanish. The limiting trace equals the initial bulk T and gas partial pressures. Only the algebraic boundary problem is considered here.',
        'scope': 'Uniform initial intensive state represented using one reference cell; only its half-cell contact resistance varies. Cell storage and time evolution are not approximated or claimed by this diagnostic.',
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps([{k: row[k] for k in ('equivalent_uniform_cell_count', 'difference_to_bulk_temperature_k', 'difference_to_previous_surface_temperature_k', 'pair_temperature_budget_met', 'root_balance_within_original_budgets')} for row in records], indent=2))


if __name__ == '__main__':
    main()
