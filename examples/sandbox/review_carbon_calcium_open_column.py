"""Source and local/global rate qualification before open-column integration."""
import argparse
import json
import math
from pathlib import Path

import mpmath as mp
import numpy as np

from carbon_calcium_inventory_setup import build
from carbon_calcium_radiation_reference import RadiationSource
from carbon_calcium_source_audit import SourceState, independent_exchange
from review_carbon_calcium_open_cell import source_bath
from review_carbon_calcium_program import independent_program
from sludge_sandbox.carbon_calcium_caloric_inventory import caloric_inventory_tangent
from sludge_sandbox.carbon_calcium_open_column import CarbonCalciumOpenColumn
from sludge_sandbox.carbon_calcium_radiative_program import CarbonCalciumRadiativeProgram


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    cell_p = json.loads((root / p['cell_parameters']).read_text())
    face = json.loads((root / cell_p['exchange_parameters']).read_text())
    rigid = json.loads((root / face['rigid_parameters']).read_text())
    pressure = json.loads((root / rigid['pressure_parameters']).read_text())
    model, sources, _ = build(root, pressure)
    source, radiation = SourceState(sources), RadiationSource(cell_p['radiation'])
    single = CarbonCalciumRadiativeProgram(model, cell_p, face, rigid['numerics'])
    policy = p['static_review']
    mp.mp.dps = cell_p['boundary_source_review']['decimal_precision']
    radiation_program = dict(cell_p['boundary_program'], gas_temperature_k=cell_p['boundary_program']['radiation_temperature_k'])
    snapshots = {}
    with (root / policy['reference_trajectory']).open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['kind'] in ('initial', 'sample') and row['time_s'] in policy['times_s']:
                snapshots[row['time_s']] = row
    rows, geometry_rows = [], []
    for count in policy['cell_counts']:
        column = CarbonCalciumOpenColumn(model, p, cell_p, face, rigid['numerics'], count)
        initial = column.initial[:4*count].reshape(count, 4)
        total_initial = np.sum(initial[:, :3], axis=0)
        original = single.initial[:3]
        inventory_error = max(abs(total_initial - original))
        energy_error = abs(math.fsum(s['internal_energy_j'] for s in column.initial_states)
                           - single.state(single.initial)['internal_energy_j'])
        geometry_rows.append({'cell_count': count, 'total_volume_m3': column.volume * count,
            'initial_inventory_error_mol': float(inventory_error), 'initial_energy_error_j': energy_error,
            'within_budgets': {'same_volume': column.volume * count == cell_p['volume_m3'],
                'same_inventories': bool(inventory_error <= policy['initial_inventory_budget_mol']),
                'same_energy': energy_error <= policy['initial_energy_budget_j']}})
        for at in policy['times_s']:
            snapshot = snapshots[at]
            values = column.initial.copy()
            for i in range(count):
                location = (i + .5) / count - .5
                for j, key in enumerate(('carbon_relative_span', 'oxygen_relative_span', 'nitrogen_relative_span')):
                    values[4*i+j] = snapshot['values'][j] / count * (1 + location * policy[key])
                values[4*i+3] = snapshot['state']['temperature_k'] + location * policy['temperature_span_k']
            states, faces, _, contact, rad = column.observe(at, values)
            refs = [source.reconstruct(s, column.volume, [column.calcium, *values[4*i:4*i+3]]) for i, s in enumerate(states)]
            t, pressure, fractions = independent_program(cell_p['boundary_program'], at)
            bath = source_bath(source, float(t), float(pressure), {k: float(v) for k, v in fractions.items()})
            exterior = independent_exchange(bath, refs[-1], face)
            rad_t = float(independent_program(radiation_program, at)[0])
            radiation_flux = radiation.flux(states[-1]['temperature_k'], rad_t)
            reference = np.zeros((count, 5))
            productions = []
            for i in range(count - 1):
                f = independent_exchange(refs[i], refs[i+1], column.face_parameters)
                reference[i, :4] -= np.array([*f['inventory'], f['energy']])
                reference[i+1, :4] += np.array([*f['inventory'], f['energy']])
                reference[i, 4] += f['entropy'][0]
                reference[i+1, 4] += f['entropy'][1]
                productions.append(f['production'])
            incoming_energy = exterior['energy'] + radiation_flux['energy_in_w']
            reference[-1, :4] += np.array([*exterior['inventory'], incoming_energy])
            reference[-1, 4] += exterior['entropy'][1] + radiation_flux['body_entropy_rate_w_k']
            productions.extend([exterior['production'], radiation_flux['entropy_production_w_k']])
            actual = column.rates(at, values)
            reconstructed = np.zeros_like(reference)
            for i, state in enumerate(states):
                tangent = caloric_inventory_tangent(model, state, column.volume, column.calcium,
                    float(values[4*i]), float(values[4*i+1]))
                rates = actual[4*i:4*i+4]
                coordinates = np.array([rates[3], *rates[:3]])
                reconstructed[i, :3] = rates[:3]
                reconstructed[i, 3] = np.array(tangent['internal_energy_derivatives']) @ coordinates
                reconstructed[i, 4] = np.array(tangent['entropy_derivatives']) @ coordinates
            errors = np.max(np.abs(reconstructed - reference), axis=0)
            ledger_reference = np.array([incoming_energy, exterior['entropy'][0], math.fsum(productions),
                radiation_flux['energy_in_w'], radiation_flux['reservoir_entropy_rate_w_k']])
            ledger_errors = np.abs(actual[4*count:] - ledger_reference)
            entropy_identity = float(abs(math.fsum(reconstructed[:, 4]) + actual[-4] + actual[-1] - actual[-3]))
            flags = {'local_inventory': bool(np.all(errors[:3] <= policy['inventory_rate_budget_mol_s'])),
                'local_energy': bool(errors[3] <= policy['energy_rate_budget_w']),
                'local_entropy': bool(errors[4] <= policy['entropy_rate_budget_w_k']),
                'external_energy': bool(np.all(ledger_errors[[0, 3]] <= policy['energy_rate_budget_w'])),
                'external_entropy': bool(np.all(ledger_errors[[1, 2, 4]] <= policy['entropy_rate_budget_w_k'])),
                'global_entropy_identity': entropy_identity <= policy['entropy_rate_budget_w_k'],
                'nonnegative_face_production': min(productions) >= 0.,
                'positive_cv': min(s['equilibrium_cv_j_k'] for s in states) > 0.,
                'source_states': all(all(v <= p['verification'][k] for k, v in r['errors'].items()) for r in refs)}
            result = {'cell_count': count, 'time_s': at, 'values': values.tolist(), 'states': states,
                'faces': faces, 'contact': contact, 'radiation': rad, 'rates': actual.tolist(),
                'independent_local_C_O_N_U_S_rates': reference.tolist(), 'local_rate_errors': errors.tolist(),
                'external_ledger_errors': ledger_errors.tolist(), 'entropy_identity_w_k': entropy_identity,
                'source_errors': [r['errors'] for r in refs], 'within_budgets': flags}
            if count == 1:
                one = single.rates(at, values)
                difference = np.abs(actual - one)
                one_bounds = [policy['inventory_rate_budget_mol_s']] * 3 + [policy['one_cell_temperature_rate_budget_k_s'],
                    policy['energy_rate_budget_w'], policy['entropy_rate_budget_w_k'], policy['entropy_rate_budget_w_k'],
                    policy['energy_rate_budget_w'], policy['entropy_rate_budget_w_k']]
                result['one_cell_rate_differences'] = difference.tolist()
                flags['one_cell_equivalence'] = bool(np.all(difference <= one_bounds))
            rows.append(result)
    result = {'settings': p, 'cell_settings': cell_p, 'source_records': sources,
        'geometry': geometry_rows, 'states': rows,
        'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in rows + geometry_rows),
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'states': len(rows), 'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met']}))


if __name__ == '__main__':
    main()
