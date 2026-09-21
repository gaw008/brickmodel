"""Offline constrained-phase wet-cell exchange, with explicit root parameters.

Liquid cannot evaporate or condense in this stage. JSONL records completed
steps, actual local source facts and energy/volume closure residuals.
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
    from sludge_sandbox.fixed_liquid_cell import FixedLiquidCell
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
    host = FixedLiquidCell(water, thermo, config['molar_masses_kg_mol'],
                          **config['storage'], dry_caloric=config['dry_caloric'],
                          numerics=config['numerics'])
    case = config['cases'][args.case]
    reservoir = ideal_gas_reservoir(
        **case['reservoir'], molar_masses_kg_mol=host.molar_masses_kg_mol,
        gas_constant_j_mol_k=thermo.gas_constant_j_mol_k,
    )
    initial = ideal_gas_reservoir(
        **case['cell'], molar_masses_kg_mol=host.molar_masses_kg_mol,
        gas_constant_j_mol_k=thermo.gas_constant_j_mol_k,
    )
    transfer = GasBoundaryTransfer(**config['transfer'])
    steps = config['numerics']['steps'][args.resolution]
    duration = Fraction(config['numerics']['duration_s'])
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
              'method': 'explicit midpoint, rigid common-T/P storage, fixed liquid inventory',
              'phase_transfer_mol_s': 0, 'material_qualified': False, 'training_eligible': False})
        _, liquid_volume = host.liquid_at(initial.temperature_k, initial.pressure_pa)
        gas_volume = host.available_fluid_volume_m3-liquid_volume
        amounts = {key: value*gas_volume for key, value in initial.concentrations_mol_m3.items()}
        gas, point = host.at_temperature(amounts, initial.temperature_k)
        energy = point['constitutive_internal_energy_j']
        point.update(internal_energy_j=energy, energy_inverse_residual_j=0.)
        emit({'kind': 'initial', 'state': point})
        for index in range(steps):
            predictor = apply_open_gas_rate(amounts, energy, rate(gas), step/2)
            midpoint, midpoint_point = host.decode(predictor.amounts_mol, predictor.internal_energy_j)
            accepted_rate = rate(midpoint)
            update = apply_open_gas_rate(amounts, energy, accepted_rate, step)
            gas, point = host.decode(update.amounts_mol, update.internal_energy_j)
            emit({'kind': 'step', 'index': index+1, 'time_s': (index+1)*step,
                  'midpoint': midpoint_point, 'rate': accepted_rate,
                  'update': update, 'state': point})
            amounts, energy = update.amounts_mol, update.internal_energy_j
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
              'duration_s': duration, 'final': point,
              'phase_transfer_mol_s': 0, 'material_qualified': False, 'training_eligible': False})
    print(json.dumps({'case': args.case, 'steps': steps, 'status': 'completed',
                      'final_temperature_k': point['temperature_k'],
                      'final_pressure_pa': point['pressure_pa']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
