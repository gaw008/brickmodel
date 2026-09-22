"""Offline open-cell phase exchange; root settings and every step are retained.

The conserved H2O inventory includes liquid and vapor. Only gas crosses the
boundary. Local equilibrium redistributes water at the same total stored U;
no separate latent-heat source is added. This is not a brick material model.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--case', required=True)
    parser.add_argument('--resolution', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    config = json.loads(args.parameters.read_text())
    sys.path.insert(0, str(root/'src'))
    sys.path.insert(0, str(root/'examples'/'sandbox'))
    from run_open_gas_boundary import json_value
    from sludge_sandbox.equilibrium_water_cell import EquilibriumWaterCell
    from sludge_sandbox.gas_transport import ideal_gas_reservoir
    from sludge_sandbox.open_gas_boundary import (
        GasBoundaryTransfer, apply_open_gas_rate, open_gas_boundary_rate,
    )
    from sludge_sandbox.recorded_water import RecordedWaterProperties
    from sludge_sandbox.thermochemistry import load_thermochemistry
    from sludge_sandbox.water_properties import NumericalLimits

    water = RecordedWaterProperties(root/config['water_facts_file'],
                                    NumericalLimits(**config['numerics']['water']))
    thermo = load_thermochemistry(root/config['thermochemistry_file'])
    host = EquilibriumWaterCell(water, thermo, config['molar_masses_kg_mol'],
                                **config['storage'], numerics=config['numerics'])
    case = config['cases'][args.case]
    reservoir = ideal_gas_reservoir(**case['reservoir'],
        molar_masses_kg_mol=host.molar_masses_kg_mol,
        gas_constant_j_mol_k=thermo.gas_constant_j_mol_k)
    transfer = GasBoundaryTransfer(**config['transfer'])
    steps = config['numerics']['steps'][args.resolution]
    duration = Fraction(case['duration_s'])
    step = duration/steps

    def rate(gas):
        return open_gas_boundary_rate(gas, reservoir, transfer, host.gas_enthalpy_j_mol)

    with args.output.open('x') as stream:
        def emit(record):
            stream.write(json.dumps(record, default=json_value, allow_nan=False)+'\n')
            stream.flush()

        emit({'kind': 'input', 'case': args.case, 'resolution': args.resolution,
              'parameters': config, 'water_source': water.source_record,
              'thermochemistry': json.loads((root/config['thermochemistry_file']).read_text()),
              'method': 'explicit midpoint on total inventories and U; equilibrium decode',
              'material_qualified': False, 'training_eligible': False})
        inventories = case['cell']['inventories_mol']
        gas, point = host.at_temperature(inventories, case['cell']['temperature_k'])
        energy = point['constitutive_internal_energy_j']
        point.update(internal_energy_j=energy, energy_inverse_residual_j=0.)
        emit({'kind': 'initial', 'state': point})
        for index in range(steps):
            predictor = apply_open_gas_rate(inventories, energy, rate(gas), step/2)
            midpoint, midpoint_point = host.decode(predictor.amounts_mol, predictor.internal_energy_j)
            accepted_rate = rate(midpoint)
            update = apply_open_gas_rate(inventories, energy, accepted_rate, step)
            gas, following = host.decode(update.amounts_mol, update.internal_energy_j)
            # Net internal phase transfer, positive evaporation. Gas outflow
            # and phase transfer are distinct; only the former changes total W.
            evaporated = point['liquid_water_mol']-following['liquid_water_mol']
            emit({'kind': 'step', 'index': index+1, 'time_s': (index+1)*step,
                  'midpoint': midpoint_point, 'rate': accepted_rate, 'update': update,
                  'internal_evaporation_mol': evaporated, 'state': following})
            inventories, energy, point = update.amounts_mol, update.internal_energy_j, following
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
              'duration_s': duration, 'final': point,
              'material_qualified': False, 'training_eligible': False})
    print(json.dumps({'case': args.case, 'steps': steps, 'status': 'completed',
                      'final_temperature_k': point['temperature_k'],
                      'final_liquid_mol': point['liquid_water_mol'],
                      'final_phase': point['phase']}))


if __name__ == '__main__':
    main()
