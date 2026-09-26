"""Measure repeated exact thermochemical evaluations in a saved 128-cell path."""
import argparse
import cProfile
import io
import json
from pathlib import Path
import pstats
import time

import numpy as np

from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from calcite_rigid_source_review import source_cell_errors, independent_face
from calcite_exact_thermal_cache import cached_thermochemistry
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--observations', type=Path)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    out = root / settings['output_directory']
    out.mkdir(parents=True, exist_ok=True)
    selected = []
    selected_times = set()
    started = time.monotonic()
    if args.observations is not None:
        recorded = json.loads(args.observations.read_text())
        header = recorded['header']
        selected = recorded['observations']
        selected_times = {row['time_s'] for row in selected}
    else:
        with (root / settings['trajectory']).open('rb') as stream:
            header = json.loads(next(stream))
            for line in stream:
                # Selection avoids decoding irrelevant records; selected
                # physical observations are evaluated without subsampling.
                prefix = line[:100]
                if not any(('"kind": "' + kind + '"').encode() in prefix for kind in settings['observation_kinds']):
                    continue
                row = json.loads(line)
                t = row['time_s']
                if t in settings['selected_times_s'] and t not in selected_times:
                    selected.append(row)
                    selected_times.add(t)
                    print(json.dumps({'selected_time_s': t, 'selection_elapsed_s': time.monotonic()-started}), flush=True)
                    if len(selected_times) == len(settings['selected_times_s']):
                        break
    with (out / 'selected-observations.json').open('x') as stream:
        json.dump({'header': header, 'observations': selected}, stream, allow_nan=False)
        stream.write('\n')
    routes = []
    for capacity in settings['cache_capacities_per_phase']:
        reaction = from_records(header['affinity_parameters'], header['source'], header['reference_facts'])
        nitrogen = nitrogen_from_record(header['nitrogen_source'])
        reaction_capacity = capacity if settings['memoize_reaction_standard'] else 0
        reaction, nitrogen = cached_thermochemistry(reaction, nitrogen, capacity, reaction_capacity)
        phases = {**reaction.phases, 'nitrogen': nitrogen}
        model = OpenRigidReactiveColumn(reaction, nitrogen, header['volume_source'],
            header['model_parameters'], header['settings'], header['surface_parameters'],
            header['cell_count'], header.get('cell_widths_m'))
        profile = cProfile.Profile()
        records = []
        for row in selected:
            started = time.monotonic()
            profile.enable()
            n = model.count
            values = np.asarray(row['values'][:3*n]).reshape(n, 3)
            sources = [source_cell_errors(cell, state, value) for cell, state, value in zip(model.cells, row['states'], values, strict=True)]
            independent = [independent_face(left, right, model.cells[i], model.internal_face_parameters[i]).tolist()
                for i, (left, right) in enumerate(zip(row['states'][:-1], row['states'][1:], strict=True))]
            physical, states, faces, reservoir, contact = model.observe(np.asarray(row['integration_values']), row['segment_index'], row['time_s'])
            profile.disable()
            records.append({'time_s': row['time_s'], 'elapsed_s': time.monotonic()-started,
                'source_residuals': sources, 'independent_internal_faces': independent,
                'reconstruction': {'physical_values': physical.tolist(), 'states': states,
                    'faces': faces, 'reservoir': reservoir, 'contact': contact}})
        profile_text = io.StringIO()
        pstats.Stats(profile, stream=profile_text).sort_stats('cumulative').print_stats(settings['profile_top_entries'])
        with (out / f'capacity-{capacity}-profile.txt').open('x') as stream:
            stream.write(profile_text.getvalue().rstrip() + '\n')
        routes.append({'capacity_per_phase': capacity, 'records': records,
            'reaction_cache_information': reaction.standard.cache_info()._asdict(),
            'cache_information': {name: phase.standard.cache_info()._asdict() for name, phase in phases.items()}})
        print(json.dumps({'capacity': capacity, 'elapsed_s': sum(row['elapsed_s'] for row in records)}), flush=True)
    first = routes[0]['records']
    equality = {str(route['capacity_per_phase']): all(
        all(a[key] == b[key] for key in ['source_residuals', 'independent_internal_faces', 'reconstruction'])
        for a, b in zip(first, route['records'], strict=True)) for route in routes[1:]}
    result = {'settings': settings, 'observations_argument': str(args.observations), 'selected_times_s': [r['time_s'] for r in selected],
        'all_requested_observations_present': selected_times == set(settings['selected_times_s']),
        'routes': routes, 'all_physical_fields_exactly_equal': equality,
        'scope': settings['scope'], 'material_qualified': False, 'training_eligible': False}
    with (out / 'review.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_physical_fields_exactly_equal': equality}), flush=True)


if __name__ == '__main__':
    main()
