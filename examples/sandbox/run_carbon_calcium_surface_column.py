"""Record a reactive column with an independently qualified zero-storage surface."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from carbon_calcium_inventory_setup import build
from sludge_sandbox.carbon_calcium_surface_column import CarbonCalciumSurfaceColumn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--mesh', required=True)
    parser.add_argument('--tolerance', choices=['base', 'refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    cell_p = json.loads((root / p['cell_parameters']).read_text())
    face = json.loads((root / cell_p['exchange_parameters']).read_text())
    rigid = json.loads((root / face['rigid_parameters']).read_text())
    pressure = json.loads((root / rigid['pressure_parameters']).read_text())
    model, sources, _ = build(root, pressure)
    count = p['meshes'][args.mesh]
    surface_p = json.loads((root / p['surface_parameters']).read_text())
    cell = CarbonCalciumSurfaceColumn(model, p, cell_p, face, rigid['numerics'], count, surface_p)
    policy = p['numerics']
    factor = 1. if args.tolerance == 'base' else policy['refinement_factor']
    cell_atol = [policy['inventory_absolute_tolerance_mol'] / count] * 3 + [policy['temperature_absolute_tolerance_k']]
    ledger_atol = [policy['energy_ledger_absolute_tolerance_j'], policy['entropy_ledger_absolute_tolerance_j_k'],
        policy['entropy_ledger_absolute_tolerance_j_k'], policy['energy_ledger_absolute_tolerance_j'], policy['entropy_ledger_absolute_tolerance_j_k']]
    atol = np.array(cell_atol * count + ledger_atol) * factor
    times = np.arange(policy['observation_interval_s'],
                      cell_p['duration_s'] + policy['observation_interval_s'], policy['observation_interval_s'])
    started = time.monotonic()
    steps = sample = 0
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False) + '\n')
            stream.flush()

        def record(kind, at, values):
            states, faces, reservoir, surface = cell.observe(at, values)
            return {'kind': kind, 'time_s': float(at), 'values': values.tolist(),
                    'states': states, 'faces': faces, 'reservoir': reservoir, 'surface_exchange': surface,
                    'radiation': surface['radiation']}

        emit({'kind': 'input', 'settings': p, 'cell_settings': cell_p, 'internal_face_parameters': cell.face_parameters,
              'exterior_parameters': face, 'rigid_parameters': rigid, 'cell_count': count,
              'surface_parameters': surface_p, 'surface_interior_parameters': cell.surface_interior,
              'cell_volume_m3': cell.volume, 'cell_width_m': cell.width, 'cell_centers_m': cell.centers,
              'cell_calcium_mol': cell.calcium,
              'pressure_parameters': pressure, 'sources': sources, 'boundary_program': cell_p['boundary_program'],
              'relative_tolerance': policy['relative_tolerance'] * factor,
              'absolute_tolerances': atol.tolist(), 'material_qualified': False, 'training_eligible': False})
        emit(record('initial', 0., cell.initial))

        def rates(at, values):
            try:
                return cell.rates(at, values)
            except Exception as error:
                emit({'kind': 'evaluation_failure', 'time_s': float(at), 'values': values.tolist(),
                      'error_type': type(error).__name__, 'error': str(error)})
                raise

        values = cell.initial.copy()
        knots = cell_p['boundary_program']['knot_times_s']
        for segment, (start, end) in enumerate(zip(knots[:-1], knots[1:], strict=True)):
            solver = BDF(rates, start, values, end, jac_sparsity=cell.numerical_jacobian_sparsity(),
                         rtol=policy['relative_tolerance'] * factor, atol=atol,
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
                    print(json.dumps({'time_s': solver.t, 'steps': steps,
                                      'elapsed_s': time.monotonic() - started}), flush=True)
            values = solver.y.copy()
            if segment < len(knots) - 2:
                emit(record('boundary_transition', end, values))
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
              'elapsed_s': time.monotonic() - started, 'final': record('final', solver.t, solver.y)})
    print(json.dumps({'status': 'completed', 'steps': steps, 'elapsed_s': time.monotonic() - started}))


if __name__ == '__main__':
    main()
