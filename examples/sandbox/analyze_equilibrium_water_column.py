"""Scientific postprocessing of saved spatial trajectories; no host is run.

Shared packets are audited with exact rational arithmetic. Surface observations
are reconstructed independently with a Brent root of the film/radiation balance.
Comparisons use the shared recorded interval and restrict fine cells by volume
averaging. Partial records cannot establish a complete-trajectory comparison.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from column_review_geometry import review_geometry


def exact(value):
    return (Fraction(value['numerator'], value['denominator'])
            if isinstance(value, dict) else Fraction(value))


def surface_temperature(c, count, t, temperature):
    program, geometry = c['boundary_program']['values'], c['geometry']
    transfer, radiation = c['transfer'], c['radiation']
    spatial = review_geometry(c, count)
    tg = float(np.interp(t, program['knot_times_s'], program['gas_temperature_k']))
    tr = float(np.interp(t, program['knot_times_s'], program['radiation_temperature_k']))
    conductance = spatial['wall_conductivity_w_m_k']*geometry['area_m2']/spatial['wall_distance_m']
    film = transfer['external_conductivity_w_m_k']*geometry['area_m2']/transfer['external_distance_m']
    factor = radiation['effective_emissivity']*radiation['stefan_boltzmann_w_m2_k4']*geometry['area_m2']

    def residual(ts):
        return conductance*(ts-temperature)-film*(tg-ts)-factor*(tr**4-ts**4)

    low, high = min(temperature, tg, tr), max(temperature, tg, tr)
    policy = c['numerics']['temperature_inverse']
    return low if low == high else brentq(residual, low, high,
        xtol=policy['absolute_tolerance_k'], rtol=policy['relative_tolerance'],
        maxiter=policy['max_iterations'])


def analyze_implicit(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    header, initial = rows[0], rows[1]['states']
    c, n = header['parameters'], header['cell_count']
    order = c['boundary_program']['values']['species_order']
    baseline = [sum(exact(p['inventories_mol'][k]) for p in initial) for k in order]
    baseline.append(sum(exact(p['internal_energy_j']) for p in initial))
    observations = [r for r in rows if r['kind'] in ('initial', 'sample')]
    balances, phases, inverse, surface_error, surface_balance = [0.]*(len(order)+1), 0., 0., 0., 0.
    times, profiles, waters, liquids, surfaces = [], [], [], [], []
    minimum_inventory = min(v for p in initial for v in p['inventories_mol'].values())
    minimum_liquid = min(p['liquid_water_mol'] for p in initial)
    minimum_gas_water = min(p['amounts_mol']['H2O'] for p in initial)
    for row in observations:
        points, t = row['states'], row['time_s']
        current = [sum(exact(p['inventories_mol'][k]) for p in points) for k in order]
        current.append(sum(exact(p['internal_energy_j']) for p in points))
        for i, (new, old, integrated) in enumerate(zip(current, baseline, row['exterior_integrals'], strict=True)):
            balances[i] = max(balances[i], abs(float(new-old+exact(integrated))))
        for p in points:
            phases = max(phases, abs(float(exact(p['liquid_water_mol'])+exact(p['amounts_mol']['H2O'])-
                                          exact(p['inventories_mol']['H2O']))))
            inverse = max(inverse, abs(p['energy_inverse_residual_j']))
            minimum_inventory = min(minimum_inventory, *p['inventories_mol'].values())
            minimum_liquid = min(minimum_liquid, p['liquid_water_mol'])
            minimum_gas_water = min(minimum_gas_water, p['amounts_mol']['H2O'])
        ts = surface_temperature(c, n, t, points[-1]['temperature_k'])
        if row['kind'] == 'sample':
            surface_error = max(surface_error, abs(ts-row['surface']['temperature_k']))
            surface_balance = max(surface_balance, abs(row['surface']['balance_residual_w']))
        times.append(t)
        profiles.append([p['temperature_k'] for p in points])
        waters.append(sum(p['inventories_mol']['H2O'] for p in points))
        liquids.append(sum(p['liquid_water_mol'] for p in points))
        surfaces.append(ts)
    event = next((i for i, amount in enumerate(liquids) if amount == 0), None)
    summary = rows[-1] if rows[-1]['kind'] == 'summary' else None
    checkpoint = next((r for r in reversed(rows) if r['kind'] == 'checkpoint'), None)
    return {'file': path.name, 'completed': rows[-1]['kind'] == 'summary' and rows[-1]['status'] == 'completed', 'cells': n,
            'spatial_model': c['schema'], 'geometry': review_geometry(c, n),
            'run_status': summary['status'] if summary is not None else 'no_completion_summary',
            'samples': len(times)-1, 'elapsed_s': summary['elapsed_s'] if summary is not None else None,
            'solver_statistics': (summary['solver_statistics'] if summary is not None else
                checkpoint['solver_statistics'] if checkpoint is not None else None),
            'global_balance_observations': len(times)*len(balances),
            'max_absolute_residuals': {'global_inventory_mol': max(balances[:-1]),
                'global_energy_j': balances[-1], 'phase_water_mol': phases, 'inverse_energy_j': inverse,
                'surface_temperature_reconstruction_k': surface_error, 'surface_balance_w': surface_balance},
            'minimum_inventory_mol': minimum_inventory, 'minimum_liquid_mol': minimum_liquid,
            'minimum_gas_water_mol': minimum_gas_water,
            'liquid_depletion_sample_bracket_s': [times[event-1], times[event]] if event else None,
            'program_knots_present': [t in times for t in c['boundary_program']['values']['knot_times_s']],
            'time_s': times, 'temperature_profiles_k': profiles, 'total_water_mol': waters,
            'total_liquid_mol': liquids, 'surface_temperature_k': surfaces,
            'budgets': c['observation']['comparison_budgets']}


def analyze(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    header = rows[0]
    c = header['parameters']
    n = header['cell_count']
    program = c['boundary_program']['values']
    maxima = {key: 0. for key in ('cell_inventory_mol', 'cell_energy_j', 'global_inventory_mol',
        'global_energy_j', 'inventory_projection_mol', 'energy_projection_j',
        'phase_water_mol', 'inverse_energy_j', 'surface_balance_w', 'surface_temperature_reconstruction_k')}
    previous = rows[1]['states']
    times = [0.]
    profiles = [[p['temperature_k'] for p in previous]]
    waters = [sum(p['inventories_mol']['H2O'] for p in previous)]
    liquids = [sum(p['liquid_water_mol'] for p in previous)]
    minimum_inventory = min(v for p in previous for v in p['inventories_mol'].values())
    minimum_liquid = min(p['liquid_water_mol'] for p in previous)
    minimum_gas_water = min(p['amounts_mol']['H2O'] for p in previous)

    def keep(key, value):
        maxima[key] = max(maxima[key], abs(float(value)))

    def surface(t, temperature):
        return surface_temperature(c, n, t, temperature)

    surfaces = [surface(0., previous[-1]['temperature_k'])]
    for row in rows:
        if row['kind'] != 'step':
            continue
        current, packets, updates = row['states'], row['ledger']['faces'], row['updates']
        for i, (old, point, update) in enumerate(zip(previous, current, updates, strict=True)):
            for key in old['inventories_mol']:
                residual = exact(point['inventories_mol'][key])-exact(old['inventories_mol'][key])+exact(
                    packets[i]['amounts_mol'][key])-(exact(packets[i-1]['amounts_mol'][key]) if i else 0)
                projection = exact(update['inventory_projection_mol'][key])
                keep('cell_inventory_mol', residual-projection)
                keep('inventory_projection_mol', projection)
            energy = exact(point['internal_energy_j'])-exact(old['internal_energy_j'])+exact(
                packets[i]['energy_j'])-(exact(packets[i-1]['energy_j']) if i else 0)
            if i == n-1:
                energy += exact(row['ledger']['surface_radiation_out_j'])
            keep('cell_energy_j', energy-exact(update['energy_projection_j']))
            keep('energy_projection_j', exact(update['energy_projection_j']))
        for key in previous[0]['inventories_mol']:
            residual = sum(exact(p['inventories_mol'][key])-exact(q['inventories_mol'][key])
                           for p, q in zip(current, previous, strict=True))
            residual += exact(packets[-1]['amounts_mol'][key])
            residual -= sum(exact(u['inventory_projection_mol'][key]) for u in updates)
            keep('global_inventory_mol', residual)
        energy = sum(exact(p['internal_energy_j'])-exact(q['internal_energy_j'])
                     for p, q in zip(current, previous, strict=True))
        energy += exact(packets[-1]['energy_j'])+exact(row['ledger']['surface_radiation_out_j'])
        energy -= sum(exact(u['energy_projection_j']) for u in updates)
        keep('global_energy_j', energy)
        for p in current+row['midpoint_states']:
            keep('phase_water_mol', exact(p['liquid_water_mol'])+exact(p['amounts_mol']['H2O'])-
                 exact(p['inventories_mol']['H2O']))
            keep('inverse_energy_j', p['energy_inverse_residual_j'])
            minimum_inventory = min(minimum_inventory, *p['inventories_mol'].values())
            minimum_liquid = min(minimum_liquid, p['liquid_water_mol'])
            minimum_gas_water = min(minimum_gas_water, p['amounts_mol']['H2O'])
        end = float(exact(row['time_s']))
        midpoint = (times[-1]+end)/2
        midpoint_surface = surface(midpoint, row['midpoint_states'][-1]['temperature_k'])
        keep('surface_temperature_reconstruction_k', midpoint_surface-row['surface_midpoint']['temperature_k'])
        keep('surface_balance_w', row['surface_midpoint']['balance_residual_w'])
        times.append(end)
        profiles.append([p['temperature_k'] for p in current])
        waters.append(sum(p['inventories_mol']['H2O'] for p in current))
        liquids.append(sum(p['liquid_water_mol'] for p in current))
        surfaces.append(surface(end, current[-1]['temperature_k']))
        previous = current

    event = next((i for i, amount in enumerate(liquids) if amount == 0), None)
    return {'file': path.name, 'completed': rows[-1]['kind'] == 'summary', 'cells': n,
            'spatial_model': c['schema'], 'geometry': review_geometry(c, n),
            'steps': len(times)-1, 'elapsed_s': rows[-1]['elapsed_s'],
            'corrected_balance_count': (len(times)-1)*(n+1)*4,
            'max_absolute_residuals': maxima,
            'minimum_inventory_mol': minimum_inventory, 'minimum_liquid_mol': minimum_liquid,
            'minimum_gas_water_mol': minimum_gas_water,
            'liquid_depletion_sample_bracket_s': [times[event-1], times[event]] if event else None,
            'program_knots_present': [t in times for t in program['knot_times_s']],
            'time_s': times, 'temperature_profiles_k': profiles, 'total_water_mol': waters,
            'total_liquid_mol': liquids, 'surface_temperature_k': surfaces,
            'budgets': c['observation']['comparison_budgets']}


def compare(coarse, fine, kind):
    indices = [i for i,t in enumerate(coarse['time_s']) if fine['time_s'][0] <= t <= fine['time_s'][-1]]
    times = [coarse['time_s'][i] for i in indices]
    nc, nf = coarse['cells'], fine['cells']
    fine_profiles = np.asarray(fine['temperature_profiles_k'])
    chamber_error = None
    if (coarse['spatial_model'] == 'fixed_surface_storage_column_v1' and
            fine['spatial_model'] == 'fixed_surface_storage_column_v1'):
        # Only the bulk is refined; the last control volume is a fixed chamber.
        # Overlap averaging also handles non-nested bulk grids. Temperatures are
        # geometric observations, not reconstructed thermodynamic mixed states.
        cg, fg = coarse['geometry'], fine['geometry']
        cb, fb = cg['bulk_cells'], fg['bulk_cells']
        ce = np.linspace(0., 1., cb+1)
        fe = np.linspace(0., 1., fb+1)
        overlap = np.maximum(0., np.minimum(ce[1:, None], fe[None, 1:])-
                             np.maximum(ce[:-1, None], fe[None, :-1]))
        restricted_bulk = fine_profiles[:, :fb]@(overlap*cb).T
        restricted = np.column_stack((restricted_bulk, fine_profiles[:, -1]))
        chamber_error = float(np.max(np.abs(np.interp(times, fine['time_s'], fine_profiles[:, -1])-
                                          np.asarray(coarse['temperature_profiles_k'])[indices, -1])))
    else:
        # Original uniform meshes in this study divide one another.
        restricted = fine_profiles.reshape(len(fine_profiles), nc, nf//nc).mean(axis=2)
    errors = [abs(np.interp(times, fine['time_s'], restricted[:, i])-
                  np.asarray(coarse['temperature_profiles_k'])[indices, i]) for i in range(nc)]
    t_error = float(np.max(errors))
    bulk_error = float(np.max(errors[:-1])) if chamber_error is not None else t_error
    surface_error = float(np.max(np.abs(np.interp(times, fine['time_s'], fine['surface_temperature_k'])-
                                        np.asarray(coarse['surface_temperature_k'])[indices])))
    water_error = float(np.max(np.abs(np.interp(times, fine['time_s'], fine['total_water_mol'])-
                                      np.asarray(coarse['total_water_mol'])[indices])))
    budgets = coarse['budgets']
    complete = (coarse['completed'] and fine['completed'] and
                coarse['time_s'][0] == fine['time_s'][0] and coarse['time_s'][-1] == fine['time_s'][-1])
    within = (max(t_error, surface_error)<=budgets[kind+'_temperature_k'] and
              water_error<=budgets[kind+'_total_water_mol'])
    return {'kind': kind, 'coarse': coarse['file'], 'fine': fine['file'],
            'comparison_time_nodes': len(times),
            'comparison_time_interval_s': [times[0], times[-1]],
            'complete_trajectories_compared': complete,
            'interpolated_comparison_nodes': sum(t not in set(fine['time_s']) for t in times),
            'max_cell_volume_temperature_difference_k': t_error,
            'max_bulk_volume_temperature_difference_k': bulk_error,
            'max_fixed_chamber_temperature_difference_k': chamber_error,
            'max_surface_temperature_difference_k': surface_error,
            'max_total_water_difference_mol': water_error,
            'shared_interval_within_budget': within,
            'within_declared_comparison_budget': complete and within,
            'qualification': ('complete-trace' if complete else 'partial shared-interval')+
                 ' sampled difference, not a rigorous error bound'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    runs = [(analyze_implicit(path) if '-bdf' in path.stem else analyze(path))
            for path in sorted(args.directory.glob('*.jsonl'))]
    by_name = {run['file']: run for run in runs}
    comparisons = []
    for a, b, kind in [('two-coarse.jsonl', 'two-fine.jsonl', 'time'),
                       ('four-fine.jsonl', 'four-refined.jsonl', 'time'),
                       ('one-fine.jsonl', 'two-fine.jsonl', 'space'),
                       ('two-fine.jsonl', 'four-fine.jsonl', 'space'),
                       ('four-bdf.jsonl', 'four-refined.jsonl', 'time'),
                       ('four-bdf.jsonl', 'eight-bdf.jsonl', 'space'),
                       ('eight-bdf.jsonl', 'sixteen-bdf.jsonl', 'space'),
                       ('sixteen-bdf.jsonl', 'thirty_two-bdf.jsonl', 'space'),
                       ('thirty_two-bdf.jsonl', 'sixty_four-bdf.jsonl', 'space'),
                       ('sixteen-bdf.jsonl', 'sixteen-bdf-refined.jsonl', 'time'),
                       ('four-bdf.jsonl', 'four-bdf-cached.jsonl', 'time'),
                       ('four-bdf-cached.jsonl', 'four-bdf-gibbs.jsonl', 'time'),
                       ('four-bdf-gibbs.jsonl', 'eight-bdf-gibbs.jsonl', 'space'),
                       ('eight-bdf-gibbs.jsonl', 'sixteen-bdf-gibbs.jsonl', 'space'),
                       ('sixteen-bdf-gibbs.jsonl', 'thirty_two-bdf-gibbs.jsonl', 'space'),
                       ('thirty_two-bdf-gibbs.jsonl', 'sixty_four-bdf-gibbs.jsonl', 'space'),
                       ('eight-bdf-gibbs.jsonl', 'eight-bdf-gibbs-refined.jsonl', 'time'),
                       ('sixteen-bdf-gibbs.jsonl', 'sixteen-bdf-gibbs-refined.jsonl', 'time'),
                       ('thirty_two-bdf-gibbs.jsonl', 'thirty_two-bdf-gibbs-refined.jsonl', 'time')]:
        if a in by_name and b in by_name:
            comparisons.append(compare(by_name[a], by_name[b], kind))
    with args.output.open('x') as stream:
        json.dump({'scope': 'conditional fluid channel; no material validation', 'runs': runs,
                   'comparisons': comparisons}, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'runs': len(runs), 'comparisons': comparisons}, indent=2))


if __name__ == '__main__':
    main()
