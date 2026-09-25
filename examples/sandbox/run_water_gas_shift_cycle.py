"""Record heat-driven rigid equilibrium gas composition, energy and entropy."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from water_gas_shift_setup import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--tolerance', choices=['base', 'refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    equilibrium = json.loads((root / p['equilibrium_parameters']).read_text())
    model, sources = build(root, equilibrium)
    case = next(case for case in equilibrium['cases'] if case['id'] == p['inventory_case'])
    volume, amounts = case['volume_m3'], case['initial_amounts_mol']
    initial = model.at_temperature(case['initial_temperature_k'], volume, amounts)
    origin_u, origin_s = initial['internal_energy_j'], initial['entropy_j_k']
    decode = lambda y: model.at_energy(origin_u+float(y[0]), volume, amounts, equilibrium['numerics'])
    g, policy = p['heat_conductance_w_k'], p['numerics']
    factor = 1. if args.tolerance == 'base' else policy['refinement_factor']
    times = np.arange(1, round(p['program'][-1]['end_s']/policy['observation_interval_s'])+1)*policy['observation_interval_s']
    started, steps, sample = time.monotonic(), 0, 0
    values = np.zeros(3)
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False)+'\n'); stream.flush()

        def record(kind, at, y, segment):
            state = decode(y); bath = p['program'][segment]['reservoir_temperature_k']
            q = g*(bath-state['temperature_k'])
            return {'kind': kind, 'time_s': float(at), 'segment_index': segment,
                    'values': y.tolist(), 'state': state, 'reservoir_temperature_k': bath,
                    'heat_in_w': q, 'entropy_production_w_k': q*(1/state['temperature_k']-1/bath),
                    'entropy_balance_residual_j_k': state['entropy_j_k']-origin_s+float(y[1])-float(y[2])}

        emit({'kind': 'input', 'settings': p, 'equilibrium_parameters': equilibrium,
              'sources': sources, 'inventory_case': case, 'tolerance': args.tolerance,
              'initial_energy_j': origin_u, 'initial_entropy_j_k': origin_s,
              'coordinate_order': ['internal_energy_change_j', 'reservoir_entropy_j_k', 'entropy_production_j_k'],
              'material_qualified': False, 'training_eligible': False})
        emit(record('initial', p['program'][0]['start_s'], values, 0))
        for segment, boundary in enumerate(p['program']):
            bath = boundary['reservoir_temperature_k']
            if segment:
                emit(record('boundary_transition', boundary['start_s'], values, segment))

            def rates(at, y):
                t = decode(y)['temperature_k']; q = g*(bath-t)
                return np.array([q, -q/bath, q*(1/t-1/bath)])

            def jacobian(at, y):
                state = decode(y); t = state['temperature_k']
                slope = g/state['equilibrium_cv_j_k']; matrix = np.zeros((3, 3))
                matrix[:, 0] = [-slope, slope/bath, slope*(1/bath-bath/t**2)]
                return matrix

            solver = BDF(rates, boundary['start_s'], values, boundary['end_s'], jac=jacobian,
                         rtol=policy['relative_tolerance']*factor,
                         atol=np.array(policy['absolute_tolerances_energy_entropy_production'])*factor,
                         first_step=policy['first_step_s'], max_step=policy['maximum_step_s'])
            while solver.status == 'running':
                before = solver.t; message = solver.step()
                if solver.status == 'failed':
                    raise RuntimeError(message)
                dense = solver.dense_output(); steps += 1
                row = record('accepted', solver.t, solver.y, segment)
                row['dense_output'] = {'start_time_s': before, 'end_time_s': solver.t,
                    'shifts_s': dense.t_shift.tolist(), 'denominators_s': dense.denom.tolist(),
                    'differences': dense.D.tolist()}
                emit(row)
                while sample < len(times) and times[sample] <= solver.t:
                    at = float(times[sample]); emit(record('sample', at, dense(at), segment)); sample += 1
                if steps % policy['progress_every_steps'] == 0:
                    print(json.dumps({'time_s': solver.t, 'steps': steps, 'elapsed_s': time.monotonic()-started}), flush=True)
            values = solver.y
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
              'elapsed_s': time.monotonic()-started,
              'final': record('final', p['program'][-1]['end_s'], values, len(p['program'])-1)})
    print(json.dumps({'status': 'completed', 'steps': steps, 'elapsed_s': time.monotonic()-started}), flush=True)


if __name__ == '__main__':
    main()
