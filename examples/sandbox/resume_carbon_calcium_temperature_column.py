"""Continue the stored accepted state with a declared BDF history restart."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from carbon_calcium_pressure_setup import build
from sludge_sandbox.carbon_calcium_temperature_column import CarbonCalciumTemperatureColumn
from sludge_sandbox.carbon_calcium_temperature_jacobian import TemperatureColumnJacobian
from sludge_sandbox.research_trajectory import PartitionedTrajectoryWriter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--case', required=True)
    parser.add_argument('--review-only', action='store_true')
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    case = settings['cases'][args.case]
    checkpoint = json.loads((root / case['checkpoint']).read_text())
    header, last = checkpoint['header'], checkpoint['last_accepted']
    p, rigid = header['settings'], header['rigid_parameters']
    face = json.loads((root / p['exchange_parameters']).read_text())
    model, _, _ = build(root, header['pressure_parameters'])
    n = header['cell_count']
    column = CarbonCalciumTemperatureColumn(model, p, face, rigid['numerics'], n)
    values = np.array(last['integration_values'])
    start = last['time_s']
    states, faces = column.observe(values)
    point = {
        'checkpoint': case['checkpoint'], 'restart_time_s': start,
        'states_equal_to_saved': states == last['states'],
        'faces_equal_to_saved': faces == last['faces'],
        'conserved_values_equal_to_saved': column.conserved_values(values, states).tolist() == last['values'],
        'initial_energy_reference_equal': list(column.initial_energies) == header['initial_internal_energies_j'],
        'scope': 'Current-point reconstruction only; does not qualify the continued trajectory.',
    }
    (root / case['point_review']).write_text(json.dumps(point, indent=2) + '\n')
    print(json.dumps(point), flush=True)
    if args.review_only:
        return
    policy = p['numerics']
    atol = np.array(header['absolute_tolerances'])
    times = np.arange(policy['observation_interval_s'], p['duration_s'] + policy['observation_interval_s'], policy['observation_interval_s'])
    sample = checkpoint['counts']['sample']
    steps = checkpoint['counts']['accepted']
    suffix_output = root / case['suffix_output']
    storage_policy = json.loads((root / settings['archive_parameters']).read_text())
    started = time.monotonic()
    with PartitionedTrajectoryWriter(suffix_output, root, storage_policy) as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False) + '\n')
            stream.flush()

        def record(kind, at, y):
            states, faces = column.observe(y)
            return {'kind': kind, 'time_s': float(at),
                    'values': column.conserved_values(y, states).tolist(),
                    'integration_values': y.tolist(), 'states': states, 'faces': faces}

        emit({'kind': 'integration_restart', 'time_s': start,
              'checkpoint': case['checkpoint'], 'prefix_manifest': checkpoint['prefix_manifest'],
              'integration_values': values.tolist(), 'history_policy': 'reinitialize BDF at the saved accepted state',
              'relative_tolerance': header['relative_tolerance'], 'absolute_tolerances': atol.tolist(),
              'reason': 'Old sandbox process lost path write permission during attempted relocation; saved prefix retained.'})
        jacobian_options = {
            'numerical_with_local_sparsity': lambda: {'jac_sparsity': column.numerical_jacobian_sparsity()},
            'numerical_local_body_analytic_entropy': lambda: {'jac': TemperatureColumnJacobian(column, atol[:-1])},
        }[policy['jacobian_method']]()
        solver = BDF(column.rates, start, values, p['duration_s'], **jacobian_options,
                     rtol=header['relative_tolerance'], atol=atol,
                     max_step=policy['maximum_step_s'], first_step=policy['first_step_s'])
        while solver.status == 'running':
            before = solver.t
            message = solver.step()
            if solver.status == 'failed':
                raise RuntimeError(message)
            dense = solver.dense_output()
            steps += 1
            row = record('accepted', solver.t, solver.y)
            row['dense_output'] = {'start_time_s': before, 'end_time_s': solver.t,
                                  'shifts_s': dense.t_shift.tolist(), 'denominators_s': dense.denom.tolist(),
                                  'differences': dense.D.tolist()}
            emit(row)
            while sample < len(times) and times[sample] <= solver.t:
                at = float(times[sample])
                emit(record('sample', at, dense(at)))
                sample += 1
            if steps % policy['progress_every_steps'] == 0:
                print(json.dumps({'time_s': solver.t, 'steps': steps, 'resumed_elapsed_s': time.monotonic() - started}), flush=True)
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
              'resumed_elapsed_s': time.monotonic() - started,
              'final': record('final', solver.t, solver.y)})
    prefix = json.loads((root / checkpoint['prefix_manifest']).read_text())
    suffix = json.loads(suffix_output.read_text())
    counts = Counter(prefix['record_counts']) + Counter(suffix['record_counts'])
    combined = {**suffix, 'parts': prefix['parts'] + suffix['parts'],
                'raw_bytes': prefix['raw_bytes'] + suffix['raw_bytes'],
                'archive_bytes': prefix['archive_bytes'] + suffix['archive_bytes'],
                'record_counts': dict(counts), 'byte_identical_roundtrip': None,
                'prefix_manifest': checkpoint['prefix_manifest'], 'suffix_manifest': case['suffix_output'],
                'integration_history_restart': True,
                'scope': 'Complete recorded prefix plus continued trajectory; numerical and physical audits still required.'}
    with (root / case['combined_output']).open('x') as stream:
        json.dump(combined, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': 'completed', 'steps': steps, 'combined_output': case['combined_output']}))


if __name__ == '__main__':
    main()
