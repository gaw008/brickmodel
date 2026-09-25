"""Record isothermal pore relaxation and mechanical, heat, dissipation ledgers."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import BDF

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.viscous_spherical_pore import ViscousSphericalPore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--tolerance', choices=['base', 'refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    source_policy = json.loads((root/p['source_review_parameters']).read_text())
    source = json.loads((root/source_policy['source_file']).read_text())
    model = ViscousSphericalPore(source_policy['model']); case = p['cases'][args.case]
    a0 = model.reference_radius; v0 = 4*math.pi*a0**3/3
    amount = case['initial_gas_pressure_pa']*v0/(model.r*model.temperature)
    e0 = 4*math.pi*model.gamma*a0*a0
    initial = model.closed(a0, amount)
    decode = lambda y: model.closed(a0*float(y[0]), amount)
    policy = p['numerics']; factor = 1. if args.tolerance == 'base' else policy['refinement_factor']
    times = np.arange(1, round(p['duration_s']/policy['observation_interval_s'])+1)*policy['observation_interval_s']
    started, steps, sample = time.monotonic(), 0, 0
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False)+'\n'); stream.flush()

        def record(kind, at, y):
            state = decode(y)
            return {'kind': kind, 'time_s': float(at), 'values': y.tolist(), 'state': state,
                    'outer_linear_ratio': state['outer_radius_m']/initial['outer_radius_m'],
                    'surface_energy_balance_j': state['surface_energy_j']-e0-e0*float(y[1]+y[2]),
                    'free_energy_balance_j': state['free_energy_plus_pressure_work_change_j']+e0*float(y[3]),
                    'entropy_balance_j_k': state['gas_entropy_change_j_k']-e0*float(y[2]+y[3])/model.temperature}

        def rates(at, y):
            state = decode(y)
            return np.array([state['radius_rate_m_s']/a0, state['external_work_in_w']/e0,
                             state['heat_in_w']/e0, state['viscous_dissipation_w']/e0])

        emit({'kind': 'input', 'settings': p, 'source_parameters': source_policy, 'sources': source,
              'case_name': args.case, 'case': case, 'tolerance': args.tolerance,
              'gas_amount_mol': amount, 'reference_surface_energy_j': e0,
              'coordinate_order': ['radius_ratio', 'work_in_over_E0', 'heat_in_over_E0', 'dissipation_over_E0'],
              'material_qualified': False, 'training_eligible': False})
        values = np.array([1., 0., 0., 0.]); emit(record('initial', 0., values))
        solver = BDF(rates, 0., values, p['duration_s'], jac=None,
                     rtol=policy['relative_tolerance']*factor,
                     atol=np.array(policy['absolute_tolerances_normalized'])*factor,
                     first_step=policy['first_step_s'], max_step=policy['maximum_step_s'])
        while solver.status == 'running':
            before = solver.t; message = solver.step()
            if solver.status == 'failed':
                raise RuntimeError(message)
            dense = solver.dense_output(); steps += 1
            row = record('accepted', solver.t, solver.y)
            row['dense_output'] = {'start_time_s': before, 'end_time_s': solver.t,
                'shifts_s': dense.t_shift.tolist(), 'denominators_s': dense.denom.tolist(),
                'differences': dense.D.tolist()}
            emit(row)
            while sample < len(times) and times[sample] <= solver.t:
                at = float(times[sample]); emit(record('sample', at, dense(at))); sample += 1
            if steps % policy['progress_every_steps'] == 0:
                print(json.dumps({'time_s': solver.t, 'steps': steps, 'elapsed_s': time.monotonic()-started}), flush=True)
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps, 'elapsed_s': time.monotonic()-started,
              'final': record('final', solver.t, solver.y)})
    print(json.dumps({'status': 'completed', 'steps': steps, 'elapsed_s': time.monotonic()-started}), flush=True)


if __name__ == '__main__':
    main()
