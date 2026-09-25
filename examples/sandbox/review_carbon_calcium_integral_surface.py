"""Source-based simultaneous surface balances, entropy and series limits."""
import argparse
import json
import math
from pathlib import Path

import mpmath as mp

from carbon_calcium_inventory_setup import build
from carbon_calcium_source_audit import SourceState
from carbon_calcium_surface_reference import solve, uniqueness_certificate
from carbon_calcium_surface_source_flux import solve_float
from review_carbon_calcium_open_cell import source_bath
from sludge_sandbox.carbon_calcium_integral_surface import surface_exchange
from sludge_sandbox.carbon_calcium_open_cell import ideal_gas_reservoir
from sludge_sandbox.carbon_calcium_open_column import CarbonCalciumOpenColumn


def difference(actual, reference):
    return float(abs(mp.mpf(actual)-reference))


def decimal_record(value):
    if isinstance(value, dict):
        return {k: decimal_record(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [decimal_record(v) for v in value]
    return str(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    column_p = json.loads((root/p['column_parameters']).read_text())
    cell_p = json.loads((root/column_p['cell_parameters']).read_text())
    exterior = json.loads((root/cell_p['exchange_parameters']).read_text())
    rigid = json.loads((root/exterior['rigid_parameters']).read_text())
    pressure = json.loads((root/rigid['pressure_parameters']).read_text())
    model, sources, _ = build(root, pressure)
    source = SourceState(sources)
    mp.mp.dps = p['independent_review']['decimal_precision']
    snapshots = {}
    with (root/p['reference_trajectory']).open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['kind'] in ('initial','sample') and row['time_s'] in p['reference_times_s']:
                snapshots[row['time_s']] = row
    cases = [{'name': 'program_snapshot', 'mesh_count': n, 'reference_time_s': at}
             for n in p['mesh_counts'] for at in p['reference_times_s']] + p['limiting_cases']
    rows = []
    for case in cases:
        n, at = case['mesh_count'], case['reference_time_s']
        column = CarbonCalciumOpenColumn(model, column_p, cell_p, exterior, rigid['numerics'], n)
        snapshot = snapshots[at]
        inventory = [column.calcium, *[v/n for v in snapshot['values'][:3]]]
        bulk = model.at_temperature_volume(snapshot['state']['temperature_k'], column.volume, *inventory, rigid['numerics'])
        bulk_source = source.reconstruct(bulk, column.volume, inventory)
        prescribed = column.program.at(at)
        bath_t, bath_p, fractions = prescribed.gas_temperature_k, prescribed.total_pressure_pa, prescribed.mole_fractions
        radiation = dict(cell_p['radiation'], reservoir_temperature_k=prescribed.radiation_temperature_k)
        outer_p = dict(exterior)
        inner_p = dict(column.face_parameters,
            heat_conductance_w_k=2*column.face_parameters['heat_conductance_w_k'],
            gas_mobilities_mol2_k_j_s={k: 2*v for k,v in column.face_parameters['gas_mobilities_mol2_k_j_s'].items()})
        if case['name'] in ('matched','isothermal_series'):
            bath_t = bulk['temperature_k']
            radiation['reservoir_temperature_k'] = bath_t
        if case['name'] == 'matched':
            bath_p = bulk['pressure_pa']
            fractions = {k: v/bath_p for k,v in bulk['partial_pressures_pa'].items()}
        if case['name'] == 'conduction_only_series':
            bath_t = case['gas_temperature_k']
            radiation['area_m2'] = 0.
            outer_p['gas_mobilities_mol2_k_j_s'] = {k: 0. for k in exterior['gas_order']}
        bath = ideal_gas_reservoir(model, bath_t, bath_p, fractions)
        actual = surface_exchange(model, bulk, bath, inner_p, outer_p, radiation, p)
        ref = solve(source, bulk, bath, inner_p, outer_p, radiation, p, actual['surface'])
        float_ref = solve_float(source, bulk_source,
            source_bath(source,bath_t,bath_p,fractions),inner_p,outer_p,radiation,p)
        certificate = uniqueness_certificate(source, bulk, bath, inner_p, outer_p, radiation, p)
        names = exterior['gas_order']
        errors = {
            'temperature_k': difference(actual['surface']['temperature_k'], ref['surface']['temperature']),
            'pressure_pa': difference(actual['surface']['pressure_pa'], ref['surface']['pressure']),
            'chemical_potential_j_mol': max(difference(actual['surface']['chemical_potentials_j_mol'][k], ref['surface']['mu'][k]) for k in names),
            'species_mol_s': max(difference(actual[side]['gas_flows_mol_s'][k],ref[side]['flow'][k]) for side in ('inner','outer') for k in names),
            'energy_w': max(difference(actual[side]['energy_flow_w'],ref[side]['energy']) for side in ('inner','outer')),
            'entropy_w_k': max(difference(actual[side][key+'_rate_w_k'],ref[side][refkey])
                for side in ('inner','outer') for key,refkey in (('left_entropy','entropy_left'),('right_entropy','entropy_right'))),
        }
        errors['energy_w'] = max(errors['energy_w'],difference(actual['radiation']['energy_in_w'],ref['radiation_energy']))
        errors['entropy_w_k'] = max(errors['entropy_w_k'],difference(actual['combined_entropy_production_w_k'],ref['production']))
        entropy_identity = abs(actual['body_plus_reservoir_entropy_rate_w_k'] + actual['surface_entropy_balance_w_k']
                               - actual['combined_entropy_production_w_k'])
        balance_entropy = (actual['energy_balance_residual_w'] - math.fsum(
            actual['surface']['chemical_potentials_j_mol'][k]*actual['species_balance_residuals_mol_s'][k] for k in names))/actual['surface']['temperature_k']
        flags = {k: v <= p['verification'][k] for k,v in errors.items()}
        flags.update(
            source_bulk=all(v <= column_p['verification'][k] for k,v in bulk_source['errors'].items()),
            species_stationarity=max(abs(v) for v in actual['species_balance_residuals_mol_s'].values()) <= p['verification']['species_mol_s'],
            energy_stationarity=abs(actual['energy_balance_residual_w']) <= p['verification']['energy_w'],
            surface_entropy=abs(actual['surface_entropy_balance_w_k']) <= p['verification']['entropy_w_k'],
            surface_entropy_from_balances=abs(balance_entropy-actual['surface_entropy_balance_w_k']) <= p['verification']['entropy_w_k'],
            total_entropy_identity=entropy_identity <= p['verification']['entropy_w_k'],
            nonnegative_production=actual['combined_entropy_production_w_k'] >= 0.,
            independent_root=bool(ref['scaled_root_residual'] <= mp.mpf(p['independent_review']['root_tolerance'])),
            unique_source_domain_root=certificate['strictly_decreasing_on_entire_source_domain'] and certificate['opposite_endpoint_signs'])
        limits = {}
        if case['name'] == 'matched':
            limits = {'temperature_k': abs(actual['surface']['temperature_k']-bath_t),
                'equal_species_mol_s': max(abs(actual[side]['gas_flows_mol_s'][k]) for side in ('outer','inner') for k in names),
                'equal_energy_w': max(abs(actual[side]['energy_flow_w']) for side in ('outer','inner'))}
        if case['name'] == 'isothermal_series':
            flows = {k: outer_p['gas_mobilities_mol2_k_j_s'][k]*inner_p['gas_mobilities_mol2_k_j_s'][k]
                /(outer_p['gas_mobilities_mol2_k_j_s'][k]+inner_p['gas_mobilities_mol2_k_j_s'][k])
                *(bath['chemical_potentials_j_mol'][k]-bulk['chemical_potentials_j_mol'][k])/bath_t for k in names}
            limits = {'temperature_k': abs(actual['surface']['temperature_k']-bath_t),
                'species_mol_s': max(abs(actual[side]['gas_flows_mol_s'][k]-flows[k]) for side in ('outer','inner') for k in names)}
        if case['name'] == 'conduction_only_series':
            go, gi = outer_p['heat_conductance_w_k'], inner_p['heat_conductance_w_k']
            expected_t = (go*bath_t+gi*bulk['temperature_k'])/(go+gi)
            expected_q = go*gi/(go+gi)*(bath_t-bulk['temperature_k'])
            limits = {'temperature_k': abs(actual['surface']['temperature_k']-expected_t),
                'equal_species_mol_s': max(abs(actual[side]['gas_flows_mol_s'][k]) for side in ('outer','inner') for k in names),
                'energy_w': max(abs(actual[side]['energy_flow_w']-expected_q) for side in ('outer','inner'))}
        flags.update({'limit_'+k: value <= p['verification'][k] for k,value in limits.items()})
        float_errors = {
            'temperature_k': difference(float_ref['surface']['temperature_k'],ref['surface']['temperature']),
            'pressure_pa': difference(float_ref['surface']['pressure_pa'],ref['surface']['pressure']),
            'chemical_potential_j_mol': max(difference(float_ref['surface']['mu'][k],ref['surface']['mu'][k]) for k in names),
            'species_mol_s': max(difference(float_ref[side]['gas'][k],ref[side]['flow'][k]) for side in ('inner','outer') for k in names),
            'energy_w': max(difference(float_ref[side]['energy'],ref[side]['energy']) for side in ('inner','outer')),
            'entropy_w_k': max(difference(float_ref[side]['entropy'][i],ref[side][key]) for side in ('inner','outer')
                for i,key in enumerate(('entropy_left','entropy_right')))}
        flags.update({'source_float_'+k:v<=p['verification'][k] for k,v in float_errors.items()})
        rows.append({'case': case, 'bulk': bulk, 'reservoir': bath, 'interior_parameters': inner_p,
            'exterior_parameters': outer_p, 'radiation_parameters': radiation,
            'actual': actual, 'independent': decimal_record(ref), 'source_errors': bulk_source['errors'],
            'source_float_reference': float_ref, 'source_float_errors': float_errors,
            'uniqueness_certificate': certificate, 'errors': errors, 'limit_errors': limits,
            'total_entropy_identity_w_k': entropy_identity, 'within_budgets': flags})
    result = {'settings': p, 'source_records': sources, 'states': rows,
        'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in rows),
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'states': len(rows), 'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met'],
        'maxima': {k: max(r['errors'][k] for r in rows) for k in rows[0]['errors']},
        'failed_cases': [{'case':r['case'],'failed':[k for k,v in r['within_budgets'].items() if not v]} for r in rows if not all(r['within_budgets'].values())]}))


if __name__ == '__main__':
    main()
