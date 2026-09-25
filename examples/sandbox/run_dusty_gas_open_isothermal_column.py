"""Record open isothermal pore-gas concentrations, bath/stream rates and BDF polynomials."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import BDF

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.dusty_gas_open_isothermal_column import OpenIsothermalDustyGasColumn
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
    gas_p = json.loads((root/local_p['local_gas_parameters']).read_text())
    transport_p = json.loads((root/gas_p['transport_parameters']).read_text())
    source = NonpolarGasTransport(transport_p)
    names, constants = p['species_order'], gas_p['constants']
    gas_constant = float(constants['boltzmann_j_k'])*float(constants['avogadro_mol_inverse'])
    masses = np.array([float(transport_p['species'][name]['molar_mass_g_mol'])*float(constants['gram_to_kg']) for name in names])
    viscosities = np.array([source.viscosity_pa_s(p['temperature_k'], name) for name in names])
    products = np.zeros((len(names), len(names)))
    reference_pressure = p['binary_property_reference_pressure_pa']
    for i, j in combinations(range(len(names)), 2):
        products[i,j] = products[j,i] = reference_pressure*source.binary_diffusivity_m2_s(p['temperature_k'], reference_pressure, names[i], names[j])
    count = p['meshes'][args.mesh]
    column = OpenIsothermalDustyGasColumn(p, count, gas_constant, masses, viscosities, products)
    concentration_reference = p['entropy_reference_pressure_pa']/(gas_constant*p['temperature_k'])
    policy = p['numerics']
    factor = {'base': 1.0, 'refined': policy['refinement_factor']}[args.tolerance]
    times = np.arange(1, round(p['duration_s']/policy['observation_interval_s'])+1)*policy['observation_interval_s']
    steps, sample = 0, 0
    started = time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row, allow_nan=False)+'\n')
            stream.flush()

        def record(kind, at, values):
            concentrations, faces = column.observe(values)
            inventories = column.pore_volume*concentrations
            entropy = -gas_constant*np.sum(inventories*np.log(concentrations/concentration_reference), axis=1)
            partial_pressures = gas_constant*p['temperature_k']*concentrations
            balances = column.balances(concentrations, faces)
            return {'kind': kind, 'time_s': float(at), 'values': values.tolist(),
                'partial_concentrations_mol_m3': concentrations.tolist(),
                'inventories_mol': inventories.tolist(), 'relative_ideal_entropy_j_k': entropy.tolist(),
                'internal_energy_j': (inventories@column.internal_energy_reference).tolist(),
                'rates': {key: value.tolist() if isinstance(value, np.ndarray) else float(value) for key, value in balances.items()},
                'partial_pressures_pa': partial_pressures.tolist(), 'pressure_pa': partial_pressures.sum(axis=1).tolist(),
                'faces': [{key: value.tolist() if isinstance(value, np.ndarray) else float(value) for key, value in face.items()} for face in faces]}

        emit({'kind': 'input', 'settings': p, 'local_law_settings': local_p,
            'gas_settings': gas_p, 'transport_settings': transport_p,
            'gas_constant_j_mol_k': gas_constant, 'molar_masses_kg_mol': masses.tolist(),
            'pure_viscosities_pa_s': viscosities.tolist(), 'diffusivity_pressure_products_pa_m2_s': products.tolist(),
            'effective_knudsen_diffusivities_m2_s': column.face.knudsen.tolist(),
            'cell_count': count, 'cell_width_m': column.width,
            'cell_bulk_volume_m3': column.area*column.width, 'cell_pore_volume_m3': column.pore_volume,
            'relative_tolerance': policy['relative_tolerance']*factor,
            'absolute_concentration_tolerance_mol_m3': policy['absolute_concentration_tolerance_mol_m3']*factor,
            'material_qualified': False, 'training_eligible': False})
        emit(record('initial', 0.0, column.initial))
        solver = BDF(column.rates, 0.0, column.initial, p['duration_s'],
            rtol=policy['relative_tolerance']*factor, atol=policy['absolute_concentration_tolerance_mol_m3']*factor,
            first_step=policy['first_step_s'], max_step=policy['maximum_step_s'],
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
            if steps % policy['progress_every_steps'] == 0:
                print(json.dumps({'time_s': solver.t, 'steps': steps, 'elapsed_s': time.monotonic()-started}), flush=True)
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
            'elapsed_s': time.monotonic()-started, 'final': record('final', solver.t, solver.y)})
    print(json.dumps({'status': 'completed', 'steps': steps, 'elapsed_s': time.monotonic()-started}), flush=True)


if __name__ == '__main__':
    main()
