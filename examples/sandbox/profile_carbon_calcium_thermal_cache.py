"""Profile repeated phase thermochemistry in recorded reactive-column states."""
import argparse
import cProfile
import io
import json
from pathlib import Path
import pstats
import time

import numpy as np

from carbon_calcium_inventory_setup import build
from carbon_calcium_exact_thermal_cache import cached_inventory_model
from sludge_sandbox.carbon_calcium_open_column import CarbonCalciumOpenColumn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    out = root / settings['output_directory']
    out.mkdir(parents=True, exist_ok=True)
    selected, times = [], set()
    started = time.monotonic()
    with (root / settings['trajectory']).open('rb') as stream:
        header = json.loads(next(stream))
        for line in stream:
            if not any(('"kind": "' + kind + '"').encode() in line[:100]
                       for kind in settings['observation_kinds']):
                continue
            row = json.loads(line)
            if row['time_s'] in settings['selected_times_s'] and row['time_s'] not in times:
                selected.append(row)
                times.add(row['time_s'])
                if len(times) == len(settings['selected_times_s']):
                    break
    with (out / 'selected-observations.json').open('x') as stream:
        json.dump({'header': header, 'observations': selected}, stream, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'selected_times_s': sorted(times), 'selection_elapsed_s': time.monotonic()-started}), flush=True)
    routes = []
    fields = ['states', 'faces', 'reservoir', 'contact', 'radiation']
    for capacity in settings['cache_capacities_per_phase']:
        original, _, _ = build(root, header['pressure_parameters'])
        model = cached_inventory_model(original, capacity)
        column = CarbonCalciumOpenColumn(model, header['settings'], header['cell_settings'],
            header['exterior_parameters'], header['rigid_parameters']['numerics'], header['cell_count'])
        profile, rows = cProfile.Profile(), []
        for recorded in selected:
            values = np.asarray(recorded['values'])
            started = time.monotonic()
            profile.enable()
            observation = dict(zip(fields, column.observe(recorded['time_s'], values), strict=True))
            rates, production = column.rate_components(recorded['time_s'], values)
            profile.disable()
            rows.append({'time_s': recorded['time_s'], 'elapsed_s': time.monotonic()-started,
                'observation': observation, 'rates': rates.tolist(), 'production_parts': production.tolist(),
                'observation_exactly_matches_recorded': all(observation[key] == recorded[key] for key in fields)})
        buffer = io.StringIO()
        pstats.Stats(profile, stream=buffer).sort_stats('cumulative').print_stats(settings['profile_top_entries'])
        (out / f'capacity-{capacity}-profile.txt').write_text(buffer.getvalue().rstrip()+'\n')
        routes.append({'capacity_per_phase': capacity, 'records': rows,
            'cache_information': {name: phase.standard.cache_info()._asdict() for name, phase in model.phases.items()}})
        print(json.dumps({'capacity': capacity, 'elapsed_s': sum(row['elapsed_s'] for row in rows)}), flush=True)
    baseline = routes[0]['records']
    equal = {str(route['capacity_per_phase']): all(
        all(a[key] == b[key] for key in ['observation', 'rates', 'production_parts'])
        for a, b in zip(baseline, route['records'], strict=True)) for route in routes[1:]}
    result = {'settings': settings, 'selected_times_s': sorted(times),
        'all_requested_observations_present': times == set(settings['selected_times_s']),
        'all_physical_fields_exactly_equal': equal,
        'all_observations_exactly_match_original_records': all(
            row['observation_exactly_matches_recorded'] for route in routes for row in route['records']),
        'routes': routes, 'material_qualified': False, 'training_eligible': False}
    with (out / 'review.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ['all_requested_observations_present',
        'all_physical_fields_exactly_equal', 'all_observations_exactly_match_original_records']}), flush=True)


if __name__ == '__main__':
    main()
