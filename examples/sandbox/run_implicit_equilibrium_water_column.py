"""Offline BDF integration of the same shared-face equilibrium-water column.

Exterior species and energy integrals are evolved as additional ODE variables.
They permit a global conservation reconstruction without post hoc corrections.
"""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import signal
import sys
from tempfile import TemporaryDirectory
import time

import numpy as np
import scipy
from scipy.integrate import BDF
from scipy.sparse import lil_matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--parameters', type=Path)
    inputs.add_argument('--resume-from', type=Path)
    parser.add_argument('--mesh')
    parser.add_argument('--tolerance', choices=('base', 'refined'))
    parser.add_argument('--stop-at', help='Name of an explicit root-parameter stop point')
    parser.add_argument('--dense-policy', type=Path,
                        help='Root parameter file requesting reproducible dense polynomials')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.parameters and (args.mesh is None or args.tolerance is None):
        parser.error('new runs require --mesh and --tolerance')
    if args.resume_from and (args.mesh is not None or args.tolerance is not None):
        parser.error('resumed runs use the recorded mesh and tolerance')
    with TemporaryDirectory(prefix='brick-column-sources-') as source_directory:
        run(args, Path(source_directory))


def run(args, source_directory):
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root/'src'))
    sys.path.insert(0, str(root/'examples'/'sandbox'))
    from equilibrium_water_column_setup import build_column
    from run_open_gas_boundary import json_value
    from sludge_sandbox.water_phase_events import locate_crossings, phase_scores
    from water_column_checkpoint import load_checkpoint, restore_sources

    start = time.monotonic()
    stop_requested = []
    def request_stop(number, frame):
        stop_requested.append(signal.Signals(number).name)
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    if args.resume_from:
        header, original_initial, checkpoint, prefix = load_checkpoint(args.resume_from)
        config = header['parameters']
        args.mesh, args.tolerance = header['mesh'], header['tolerance']
        n = header['cell_count']
        model = build_column(source_directory, restore_sources(header, source_directory), n)
    else:
        config = json.loads(args.parameters.read_text())
        n = config['numerics']['meshes'][args.mesh]
        model = build_column(args.parameters.resolve().parent, config, n)
    host = model.host
    order = config['boundary_program']['values']['species_order']
    width = len(order)+1
    policy = config['numerics']['implicit']
    factor = 1. if args.tolerance == 'base' else policy['refinement_tolerance_factor']
    atol = np.tile([policy['inventory_absolute_tolerance_mol']]*len(order)+[
        policy['energy_absolute_tolerance_j']], n+1)*factor
    seed = [config['initial']['temperature_k']]*n
    inventories = {k: v*model.volume for k, v in config['initial']['total_concentrations_mol_m3'].items()}
    initial = []
    for _ in range(n):
        _, point = host.at_temperature(inventories, seed[0])
        point.update(internal_energy_j=point['constitutive_internal_energy_j'], energy_inverse_residual_j=0.)
        initial.append(point)
    y = np.array([[p['inventories_mol'][k] for k in order]+[p['internal_energy_j']]
                  for p in initial]+[[0.]*width]).ravel()
    start_time = config['boundary_program']['values']['knot_times_s'][0]
    if args.resume_from:
        initial = original_initial['states']
        y = np.array(checkpoint['conserved_state'])
        start_time = checkpoint['time_s']
        seed = checkpoint['temperature_seeds_k'].copy()
    sparsity = lil_matrix((len(y), len(y)), dtype=int)
    for i in range(n):
        sparsity[i*width:(i+1)*width, max(0, i-1)*width:min(n, i+2)*width] = 1
    sparsity[n*width:, (n-1)*width:n*width] = 1
    inverse_seed = [seed[0]]

    @lru_cache(maxsize=policy['equilibrium_cache_entries'])
    def equilibrium_from_conserved_state(state):
        # A fixed N/U state has one admitted equilibrium. The seed only starts
        # its numerical inverse; reuse requires exact conserved float inputs.
        # The cache is private to this run and its frozen material/numerics.
        return host.decode(dict(zip(order, state[:-1], strict=True)), state[-1], inverse_seed[0])

    def decode(vector):
        values = vector[:n*width].reshape(n, width)
        gases, points = [], []
        for i, cell in enumerate(values):
            inverse_seed[0] = seed[i]
            gas, point = equilibrium_from_conserved_state(tuple(map(float, cell)))
            seed[i] = point['temperature_k']
            gases.append(gas)
            points.append(point)
        return gases, points

    def rhs(t, vector):
        gases, _ = decode(vector)
        faces, radiation, _, _ = model.rates(gases, t)
        fluxes = np.array([[face.exchange.net_mol_s[k] for k in order]+[face.energy_out_w]
                           for face in faces])
        # Shared interior face cancels exactly in the discrete equations.
        derivative = -fluxes.copy()
        derivative[1:] += fluxes[:-1]
        derivative[-1, -1] -= radiation
        exterior = fluxes[-1].copy()
        exterior[-1] += radiation
        return np.concatenate((derivative.ravel(), exterior))

    knots = config['boundary_program']['values']['knot_times_s']
    stop_time = config['execution']['stop_points_s'][args.stop_at] if args.stop_at else None
    if stop_time is not None and stop_time <= start_time:
        raise ValueError('selected stop point must follow the restart time')
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, default=json_value, allow_nan=False)+'\n')
            stream.flush()

        header = {'kind': 'input', 'parameters': config, 'cell_count': n,
              'cell_fluid_volume_m3': model.volume, 'mesh': args.mesh, 'tolerance': args.tolerance,
              'relative_tolerance': policy['relative_tolerance']*factor, 'absolute_tolerances': atol.tolist(),
              'method': 'BDF; knot-aligned segments; conserved state and exterior flux quadrature',
              'water_source': model.water.source_record, 'solid_source_facts': model.solid,
              'thermochemistry': (header['thermochemistry'] if args.resume_from else
                  json.loads((args.parameters.resolve().parent/config['thermochemistry_file']).read_text())),
              'material_qualified': False, 'training_eligible': False}
        if args.resume_from:
            stream.writelines(prefix)
            stream.flush()
            emit({'kind': 'resume', 'parent_trajectory': str(args.resume_from), 'time_s': start_time,
                  'source_input': 'Original header JSON snapshots restored; no source files reread.',
                  'integrator_history': 'New BDF history; conserved state and exterior integrals retained.'})
        else:
            emit(header)
            emit({'kind': 'initial', 'time_s': knots[0], 'states': initial, 'exterior_integrals': [0.]*width})
        if args.dense_policy:
            emit({'kind': 'dense_recording_policy', 'settings': json.loads(args.dense_policy.read_text()),
                  'scipy_version': scipy.__version__,
                  'representation': 'D0 + sum_k Dk product_j<k((t-shift_j)/denominator_j)',
                  'source': 'scipy.integrate._ivp.bdf.BdfDenseOutput; recorded numeric coefficients'})
        statistics = checkpoint['solver_statistics'].copy() if args.resume_from else []
        samples = checkpoint['samples'] if args.resume_from else 0
        events = checkpoint['phase_events'].copy() if args.resume_from else []
        event_policy = config['numerics']['phase_events']
        _, points = decode(y)
        previous_scores = phase_scores(points)
        for segment, (left, right) in enumerate(zip(knots[:-1], knots[1:], strict=True)):
            if right <= start_time:
                continue
            segment_start = max(left, start_time)
            solver = {'BDF': BDF}[policy['method']](rhs, segment_start, y, right,
                rtol=policy['relative_tolerance']*factor, atol=atol,
                max_step=policy['maximum_step_s'], jac_sparsity=sparsity.tocsr())
            times = np.arange(left+policy['observation_interval_s'], right, policy['observation_interval_s'])
            times = np.append(times, right)
            times = times[times > segment_start]
            next_sample, accepted = 0, 0
            while solver.status == 'running':
                previous_time = float(solver.t)
                message = solver.step()
                if solver.status == 'failed':
                    raise RuntimeError(message)
                accepted += 1
                interpolant = solver.dense_output()
                accepted_record = {'kind': 'accepted', 'segment': segment, 'time_s': float(solver.t),
                      'step_s': float(solver.step_size), 'rhs_evaluations': solver.nfev,
                      'jacobian_evaluations': solver.njev, 'linear_factorizations': solver.nlu,
                      'conserved_state': solver.y.tolist()}
                if args.dense_policy:
                    accepted_record['dense_output'] = {'start_time_s': previous_time,
                        'end_time_s': float(solver.t), 'order': int(interpolant.order),
                        'shifts_s': interpolant.t_shift.tolist(),
                        'denominators_s': interpolant.denom.tolist(),
                        'differences': interpolant.D.tolist()}
                emit(accepted_record)
                def event_points(at_time):
                    return decode(interpolant(at_time))[1]

                def event_cell(at_time, index):
                    cell = interpolant(at_time)[index*width:(index+1)*width]
                    inverse_seed[0] = seed[index]
                    return equilibrium_from_conserved_state(tuple(map(float, cell)))[1]

                def event_score(at_time, index):
                    if index == n:
                        return phase_scores(event_points(at_time))[-1]
                    return event_cell(at_time, index)['all_vapor_pressure_departure_pa']

                scan_times = np.linspace(previous_time, float(solver.t),
                    event_policy['scan_subintervals_per_accepted_step']+1)
                for a, b in zip(scan_times[:-1], scan_times[1:], strict=True):
                    next_scores = phase_scores(event_points(float(b)))
                    located = locate_crossings(event_score, float(a), float(b),
                                               previous_scores, next_scores, event_policy)
                    for event in located:
                        value = interpolant(event['time_s'])
                        gases, points = decode(value)
                        _, _, boundary, surface = model.rates(gases, event['time_s'])
                        indices = range(n) if event['scope'] == 'column' else [event['cell_index']]
                        bracket_states = []
                        for endpoint in event['time_bracket_s']:
                            bracket_states.append({'time_s': endpoint, 'cells': [
                                {'cell_index': i, 'state': event_cell(endpoint, i)} for i in indices]})
                        emit({'kind': 'phase_event', **event, 'states': points,
                              'bracket_states': bracket_states,
                              'exterior_integrals': value[n*width:].tolist(),
                              'boundary': boundary, 'surface': surface})
                        events.append(event)
                    previous_scores = next_scores
                while next_sample < len(times) and times[next_sample] <= solver.t:
                    t = float(times[next_sample])
                    value = interpolant(t)
                    gases, points = decode(value)
                    _, _, boundary, surface = model.rates(gases, t)
                    emit({'kind': 'sample', 'time_s': t, 'states': points,
                          'exterior_integrals': value[n*width:].tolist(),
                          'boundary': boundary, 'surface': surface})
                    samples += 1
                    next_sample += 1
                if accepted % policy['progress_every_accepted_steps'] == 0:
                    print(json.dumps({'cells': n, 'time_s': float(solver.t), 'accepted_steps': accepted,
                                      'rhs_evaluations': solver.nfev, 'elapsed_s': time.monotonic()-start,
                                      'equilibrium_cache': equilibrium_from_conserved_state.cache_info()._asdict()}), flush=True)
                emit({'kind': 'checkpoint', 'segment': segment, 'time_s': float(solver.t),
                      'conserved_state': solver.y.tolist(), 'temperature_seeds_k': seed.copy(),
                      'samples': samples, 'phase_event_count': len(events),
                      'solver_statistics': [*statistics, {'segment': segment,
                          'start_time_s': segment_start, 'end_time_s': float(solver.t),
                          'accepted_steps': accepted, 'rhs_evaluations': solver.nfev,
                          'jacobian_evaluations': solver.njev, 'linear_factorizations': solver.nlu}]})
                if stop_requested or (stop_time is not None and solver.t >= stop_time):
                    _, stopped_points = decode(solver.y)
                    reason = stop_requested[-1] if stop_requested else 'declared_simulation_stop_point'
                    emit({'kind': 'summary', 'status': 'stopped_with_checkpoint', 'reason': reason,
                          'time_s': float(solver.t), 'samples': samples, 'final': stopped_points,
                          'phase_events': events, 'solver_statistics': [*statistics, {
                              'segment': segment, 'start_time_s': segment_start,
                              'end_time_s': float(solver.t), 'accepted_steps': accepted,
                              'rhs_evaluations': solver.nfev, 'jacobian_evaluations': solver.njev,
                              'linear_factorizations': solver.nlu}],
                          'elapsed_s': time.monotonic()-start,
                          'material_qualified': False, 'training_eligible': False})
                    print(json.dumps({'status': 'stopped_with_checkpoint', 'time_s': float(solver.t),
                                      'reason': reason, 'elapsed_s': time.monotonic()-start}), flush=True)
                    return
            statistics.append({'segment': segment, 'start_time_s': segment_start,
                               'end_time_s': right, 'accepted_steps': accepted,
                               'rhs_evaluations': solver.nfev, 'jacobian_evaluations': solver.njev,
                               'linear_factorizations': solver.nlu})
            y = solver.y
            emit({'kind': 'segment', **statistics[-1], 'end_time_s': right,
                  'elapsed_s': time.monotonic()-start})
            print(json.dumps({'segment_completed': segment, 'cells': n, **statistics[-1],
                              'elapsed_s': time.monotonic()-start}), flush=True)
        emit({'kind': 'summary', 'status': 'completed', 'samples': samples, 'final': points,
              'solver_statistics': statistics, 'phase_events': events,
              'elapsed_s': time.monotonic()-start,
              'equilibrium_cache': equilibrium_from_conserved_state.cache_info()._asdict(),
              'material_qualified': False, 'training_eligible': False})
    print(json.dumps({'status': 'completed', 'cells': n, 'elapsed_s': time.monotonic()-start}), flush=True)


if __name__ == '__main__':
    main()
