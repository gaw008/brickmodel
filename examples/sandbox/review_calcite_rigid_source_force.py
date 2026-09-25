"""Compare equivalent face force arithmetic against a 50-digit source reference."""
import argparse
import json
from pathlib import Path

from mpmath import mp

from calcite_open_decimal_reference import DecimalOpenColumn
from calcite_rigid_setup import build_rigid
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn
from sludge_sandbox.rigid_reactive_exchange import rigid_reactive_face
from sludge_sandbox.rigid_reactive_source_force import source_integral_rigid_face
from sludge_sandbox.rigid_reactive_surface import gas_contact_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); mp.dps = settings['decimal_digits']
    policy = json.loads((root/settings['column_parameters']).read_text())
    config = json.loads((root/policy['model_parameters']).read_text())
    surface = json.loads((root/policy['surface_parameters']).read_text())['surface']
    reaction, nitrogen, _, _, _, _, volume = build_rigid(root, config)
    column = OpenRigidReactiveColumn(reaction, nitrogen, volume, config, policy, surface, 1)
    _, states, _, _, contact = column.observe(column.initial, 0)
    cell = column.cells[0]
    reference = DecimalOpenColumn(column, states, contact, 0, settings)
    pairs = []
    for case in settings['gas_pairs']:
        left = gas_contact_state(cell, *case['left']); right = gas_contact_state(cell, *case['right'])
        for direction, a, b in [('forward', left, right), ('reverse', right, left)]:
            pairs.append({'name': case['name']+'_'+direction, 'left': a, 'right': b,
                          'face_parameters': settings['gas_pair_face_parameters']})
    selections = []
    for prefix in settings['prefixes']:
        targets = prefix['target_times_s']; selected = [None]*len(targets)
        with (root/prefix['path']).open() as stream:
            header = json.loads(next(stream))
            for line in stream:
                row = json.loads(line)
                if row['kind'] not in ('initial', 'accepted'): continue
                for i, target in enumerate(targets):
                    if selected[i] is None or abs(row['time_s']-target)<abs(selected[i]['time_s']-target): selected[i] = row
        interior = header['surface_parameters']['interior']; area = header['surface_parameters']['area_m2']
        inner = {'heat_conductance_w_k': interior['conductivity_w_m_k']*area/interior['distance_m'],
            'bulk_mobility_mol2_k_j_s': interior['bulk_mobility_mol2_k_j_m_s']*area/interior['distance_m'],
            'counter_mobility_mol2_k_j_s': interior['counter_mobility_mol2_k_j_m_s']*area/interior['distance_m']}
        exterior = header['surface_parameters']['exterior']
        outer = {'heat_conductance_w_k': exterior['heat_transfer_w_m2_k']*area,
            'bulk_mobility_mol2_k_j_s': exterior['bulk_mobility_mol2_k_j_m2_s']*area,
            'counter_mobility_mol2_k_j_s': exterior['counter_mobility_mol2_k_j_m2_s']*area}
        for target, row in zip(targets, selected, strict=True):
            identity = {'source': prefix['path'], 'target_time_s': target, 'recorded_time_s': row['time_s']}
            selections.append(identity)
            for i in range(len(row['faces'])-settings['last_internal_faces'], len(row['faces'])):
                pairs.append({**identity, 'name': 'internal_'+str(i), 'left': row['states'][i],
                    'right': row['states'][i+1], 'face_parameters': header['internal_face_parameters'][i]})
            pairs.extend([{**identity, 'name': 'surface_inner', 'left': row['states'][-1], 'right': row['contact']['surface'], 'face_parameters': inner},
                          {**identity, 'name': 'surface_outer', 'left': row['contact']['surface'], 'right': row['reservoir'], 'face_parameters': outer}])
    records = []
    for pair in pairs:
        left, right, params = [pair[k] for k in ('left', 'right', 'face_parameters')]
        a, b = [reference.gas_state(cell, *[mp.mpf(s[k]) for k in (
            'temperature_k', 'co2_partial_pressure_pa', 'nitrogen_partial_pressure_pa', 'co2_mol', 'nitrogen_mol')]) for s in (left, right)]
        expected = reference.face(a, b, params)
        forces = [a[m]/a['t']-b[m]/b['t']+(a[h]+b[h])/2*(1/b['t']-1/a['t']) for m,h in [('mc','hc'), ('mn','hn')]]
        row = {**pair, 'reference_forces_j_mol_k': [str(v) for v in forces]}
        for name, face in [('potential_subtraction', rigid_reactive_face(left, right, params)),
                           ('source_integral', source_integral_rigid_face(left, right, params, cell))]:
            errors = {'force_j_mol_k': max(float(abs(mp.mpf(v)-w)) for v,w in zip(face['species_forces_j_mol_k'], forces, strict=True)),
                'species_mol_s': max(float(abs(mp.mpf(face[k])-v)) for k,v in zip(('carbon_flow_mol_s','nitrogen_flow_mol_s'), expected[:2], strict=True)),
                'energy_w': float(abs(mp.mpf(face['energy_flow_w'])-expected[2])),
                'entropy_w_k': float(abs(mp.mpf(face['entropy_production_w_k'])-expected[3]-expected[4]))}
            row[name] = {'face': face, 'absolute_errors': errors,
                'within_budgets': {k: value<=settings['budgets'][k] for k,value in errors.items()}}
        records.append(row)
    maxima = {name: {k: max(r[name]['absolute_errors'][k] for r in records) for k in settings['budgets']}
              for name in ('potential_subtraction', 'source_integral')}
    result = {'settings': settings, 'selections': selections, 'records': records, 'maximum_absolute_errors': maxima,
        'all_source_integral_budgets_met': all(all(r['source_integral']['within_budgets'].values()) for r in records),
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'pair_count': len(records), 'maxima': maxima, 'all_source_integral_budgets_met': result['all_source_integral_budgets_met']}))


if __name__ == '__main__': main()
