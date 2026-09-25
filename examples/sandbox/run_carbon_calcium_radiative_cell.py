"""Record a reactive open cell with separate gas and radiation reservoirs."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from carbon_calcium_inventory_setup import build as build_inventory
from sludge_sandbox.carbon_calcium_radiative_cell import CarbonCalciumRadiativeCell


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--tolerance', choices=['base', 'refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    face = json.loads((root / p['exchange_parameters']).read_text())
    rigid = json.loads((root / face['rigid_parameters']).read_text())
    pressure = json.loads((root / rigid['pressure_parameters']).read_text())
    model, sources, _ = build_inventory(root, pressure)
    cell = CarbonCalciumRadiativeCell(model, p, face, rigid['numerics'])
    policy = p['numerics']
    factor = 1. if args.tolerance == 'base' else policy['refinement_factor']
    atol = np.array([policy['inventory_absolute_tolerance_mol']] * 3
        + [policy['temperature_absolute_tolerance_k'], policy['energy_ledger_absolute_tolerance_j']]
        + [policy['entropy_ledger_absolute_tolerance_j_k']] * 2
        + [policy['energy_ledger_absolute_tolerance_j'], policy['entropy_ledger_absolute_tolerance_j_k']]) * factor
    times = np.arange(policy['observation_interval_s'],
                      p['duration_s'] + policy['observation_interval_s'], policy['observation_interval_s'])
    started = time.monotonic()
    steps = sample = 0
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False) + '\n')
            stream.flush()

        def record(kind, at, values):
            state, contact = cell.observe(values)
            return {'kind': kind, 'time_s': float(at), 'values': values.tolist(),
                    'state': state, 'face': contact, 'radiation': cell.radiation(state)}

        emit({'kind': 'input', 'settings': p, 'face_parameters': face, 'rigid_parameters': rigid,
              'pressure_parameters': pressure, 'sources': sources, 'reservoir': cell.reservoir,
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

        solver = BDF(rates, 0., cell.initial, p['duration_s'],
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
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
              'elapsed_s': time.monotonic() - started, 'final': record('final', solver.t, solver.y)})
    print(json.dumps({'status': 'completed', 'steps': steps, 'elapsed_s': time.monotonic() - started}))


if __name__ == '__main__':
    main()
