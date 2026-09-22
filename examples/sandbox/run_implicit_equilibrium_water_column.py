"""Offline BDF integration of the same shared-face equilibrium-water column.

Exterior species and energy integrals are evolved as additional ODE variables.
They permit a global conservation reconstruction without post hoc corrections.
"""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import BDF
from scipy.sparse import lil_matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--mesh', required=True)
    parser.add_argument('--tolerance', required=True, choices=('base', 'refined'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    config = json.loads(args.parameters.read_text())
    sys.path.insert(0, str(root/'src'))
    sys.path.insert(0, str(root/'examples'/'sandbox'))
    from equilibrium_water_column_setup import build_column
    from run_open_gas_boundary import json_value

    start = time.monotonic()
    n = config['numerics']['meshes'][args.mesh]
    model = build_column(root, config, n)
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
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, default=json_value, allow_nan=False)+'\n')
            stream.flush()

        emit({'kind': 'input', 'parameters': config, 'cell_count': n,
              'cell_fluid_volume_m3': model.volume, 'mesh': args.mesh, 'tolerance': args.tolerance,
              'relative_tolerance': policy['relative_tolerance']*factor, 'absolute_tolerances': atol.tolist(),
              'method': 'BDF; knot-aligned segments; conserved state and exterior flux quadrature',
              'water_source': model.water.source_record, 'solid_source_facts': model.solid,
              'thermochemistry': json.loads((root/config['thermochemistry_file']).read_text()),
              'material_qualified': False, 'training_eligible': False})
        emit({'kind': 'initial', 'time_s': knots[0], 'states': initial, 'exterior_integrals': [0.]*width})
        statistics = []
        samples = 0
        for segment, (left, right) in enumerate(zip(knots[:-1], knots[1:], strict=True)):
            solver = {'BDF': BDF}[policy['method']](rhs, left, y, right,
                rtol=policy['relative_tolerance']*factor, atol=atol,
                max_step=policy['maximum_step_s'], jac_sparsity=sparsity.tocsr())
            times = np.arange(left+policy['observation_interval_s'], right, policy['observation_interval_s'])
            times = np.append(times, right)
            next_sample, accepted = 0, 0
            while solver.status == 'running':
                message = solver.step()
                if solver.status == 'failed':
                    raise RuntimeError(message)
                accepted += 1
                emit({'kind': 'accepted', 'segment': segment, 'time_s': float(solver.t),
                      'step_s': float(solver.step_size), 'rhs_evaluations': solver.nfev,
                      'jacobian_evaluations': solver.njev, 'linear_factorizations': solver.nlu})
                interpolant = solver.dense_output()
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
            statistics.append({'segment': segment, 'accepted_steps': accepted,
                               'rhs_evaluations': solver.nfev, 'jacobian_evaluations': solver.njev,
                               'linear_factorizations': solver.nlu})
            y = solver.y
            emit({'kind': 'segment', **statistics[-1], 'end_time_s': right,
                  'elapsed_s': time.monotonic()-start})
            print(json.dumps({'segment_completed': segment, 'cells': n, **statistics[-1],
                              'elapsed_s': time.monotonic()-start}), flush=True)
        emit({'kind': 'summary', 'status': 'completed', 'samples': samples, 'final': points,
              'solver_statistics': statistics, 'elapsed_s': time.monotonic()-start,
              'equilibrium_cache': equilibrium_from_conserved_state.cache_info()._asdict(),
              'material_qualified': False, 'training_eligible': False})
    print(json.dumps({'status': 'completed', 'cells': n, 'elapsed_s': time.monotonic()-start}), flush=True)


if __name__ == '__main__':
    main()
