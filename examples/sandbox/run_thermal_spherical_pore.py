"""Record coupled pore radius, temperature, work, heat and entropy histories."""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from thermal_pore_setup import build


def main(builder):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--tolerance', choices=['base', 'refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text()); model, sources = builder(root, p)
    case = p['cases'][args.case]; a0 = p['model']['reference_radius_m']
    amount = case['initial_gas_pressure_pa']*4*math.pi*a0**3/(3*model.r*case['initial_temperature_k'])
    ts, es, ss = [p['normalization'][k] for k in ['temperature_k', 'energy_j', 'entropy_j_k']]
    policy = p['numerics']; factor = 1. if args.tolerance == 'base' else policy['refinement_factor']
    duration = case['segments'][-1]['end_time_s']
    times = np.arange(1, round(duration/policy['observation_interval_s'])+1)*policy['observation_interval_s']
    started, steps, sample, start = time.monotonic(), 0, 0, 0.
    values = np.array([1., case['initial_temperature_k']/ts, 0., 0., 0., 0., 0.])

    def decode(y, segment):
        boundary = case['segments'][segment]
        return model.at_state(a0*float(y[0]), ts*float(y[1]), amount,
                              boundary['bath_temperature_k'], boundary['conductance_w_k'])

    initial = decode(values, 0)
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False)+'\n'); stream.flush()

        def record(kind, at, y, segment):
            state = decode(y, segment)
            return {'kind': kind, 'time_s': float(at), 'segment_index': segment,
                    'values': y.tolist(), 'state': state,
                    'energy_balance_j': state['internal_energy_j']-initial['internal_energy_j']-es*float(y[2]+y[3]),
                    'entropy_balance_j_k': state['entropy_j_k']-initial['entropy_j_k']+ss*float(y[5]-y[6])}

        emit({'kind': 'input', 'settings': p, 'sources': sources, 'case_name': args.case,
              'case': case, 'gas_amount_mol': amount, 'tolerance': args.tolerance,
              'coordinate_order': ['radius_ratio', 'temperature_over_scale', 'work_in_over_scale',
                                   'heat_in_over_scale', 'dissipation_over_scale',
                                   'bath_entropy_over_scale', 'entropy_production_over_scale'],
              'material_qualified': False, 'training_eligible': False})
        emit(record('initial', 0., values, 0))
        for segment, boundary in enumerate(case['segments']):
            if segment:
                emit(record('boundary_transition', start, values, segment))

            def rates(at, y):
                state = decode(y, segment)
                return np.array([state['radius_rate_m_s']/a0, state['temperature_rate_k_s']/ts,
                    state['external_work_in_w']/es, state['heat_in_w']/es,
                    state['viscous_dissipation_w']/es, state['bath_entropy_rate_w_k']/ss,
                    state['entropy_production_w_k']/ss])

            solver = BDF(rates, start, values, boundary['end_time_s'], jac=None,
                rtol=policy['relative_tolerance']*factor,
                atol=np.array(policy['absolute_tolerances_normalized'])*factor,
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
                    print(json.dumps({'time_s':solver.t, 'steps':steps, 'elapsed_s':time.monotonic()-started}), flush=True)
            values, start = solver.y, boundary['end_time_s']
        emit({'kind':'summary', 'status':'completed', 'steps':steps, 'elapsed_s':time.monotonic()-started,
              'final':record('final', duration, values, len(case['segments'])-1)})
    print(json.dumps({'status':'completed', 'steps':steps, 'elapsed_s':time.monotonic()-started}), flush=True)


if __name__ == '__main__':
    main(build)
