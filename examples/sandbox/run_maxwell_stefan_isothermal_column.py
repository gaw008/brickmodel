"""Record a closed isothermal MS diffusion column and accepted BDF polynomials."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import BDF

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.maxwell_stefan_isothermal_column import IsothermalMaxwellStefanColumn
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--mesh', required=True)
    parser.add_argument('--tolerance', choices=['base', 'refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    local_p = json.loads((root/p['local_law_parameters']).read_text())
    transport_p = json.loads((root/local_p['transport_parameters']).read_text())
    names, constants = p['species_order'], local_p['constants']
    gas_constant = float(constants['boltzmann_j_k'])*float(constants['avogadro_mol_inverse'])
    concentration = p['pressure_pa']/(gas_constant*p['temperature_k'])
    masses = [float(transport_p['species'][k]['molar_mass_g_mol'])*float(constants['gram_to_kg']) for k in names]
    transport = NonpolarGasTransport(transport_p)
    diffusion = np.zeros((len(names), len(names)))
    for i, j in combinations(range(len(names)), 2):
        diffusion[i, j] = diffusion[j, i] = transport.binary_diffusivity_m2_s(
            p['temperature_k'], p['pressure_pa'], names[i], names[j])
    count = p['meshes'][args.mesh]
    column = IsothermalMaxwellStefanColumn(p, count, diffusion, concentration, masses, gas_constant)
    numerics = p['numerics']
    factor = {'base': 1.0, 'refined': numerics['refinement_factor']}[args.tolerance]
    times = np.arange(1, round(p['duration_s']/numerics['observation_interval_s'])+1)*numerics['observation_interval_s']
    steps, sample = 0, 0
    started = time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False)+'\n')
            stream.flush()

        def record(kind, at, values):
            fractions, faces = column.observe(values)
            inventories = concentration*column.volume*fractions
            entropy = -concentration*column.volume*gas_constant*np.sum(fractions*np.log(fractions), axis=1)
            return {'kind': kind, 'time_s': float(at), 'values': values.tolist(),
                'mole_fractions': fractions.tolist(), 'inventories_mol': inventories.tolist(),
                'mixing_entropy_j_k': entropy.tolist(),
                'faces': [{k: v.tolist() if isinstance(v, np.ndarray) else float(v) for k, v in face.items()} for face in faces]}

        emit({'kind': 'input', 'settings': p, 'local_law_settings': local_p,
            'transport_source_settings': transport_p, 'binary_diffusivity_m2_s': diffusion.tolist(),
            'gas_constant_j_mol_k': gas_constant, 'concentration_mol_m3': concentration,
            'molar_masses_kg_mol': masses, 'cell_count': count, 'cell_width_m': column.width,
            'cell_volume_m3': column.volume, 'relative_tolerance': numerics['relative_tolerance']*factor,
            'absolute_fraction_tolerance': numerics['absolute_fraction_tolerance']*factor,
            'material_qualified': False, 'training_eligible': False})
        emit(record('initial', 0.0, column.initial))
        solver = BDF(column.rates, 0.0, column.initial, p['duration_s'],
            rtol=numerics['relative_tolerance']*factor, atol=numerics['absolute_fraction_tolerance']*factor,
            first_step=numerics['first_step_s'], max_step=numerics['maximum_step_s'],
            jac_sparsity=column.jacobian_sparsity())
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
            if steps % numerics['progress_every_steps'] == 0:
                print(json.dumps({'time_s': solver.t, 'steps': steps, 'elapsed_s': time.monotonic()-started}), flush=True)
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
            'elapsed_s': time.monotonic()-started, 'final': record('final', solver.t, solver.y)})
    print(json.dumps({'status': 'completed', 'steps': steps, 'elapsed_s': time.monotonic()-started}), flush=True)


if __name__ == '__main__':
    main()
