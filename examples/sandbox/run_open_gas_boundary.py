"""Offline gas-volume exchange example using explicit project-root parameters.

This exercises the common boundary kernel without constructing the legacy wet
host or its digest-based records. It is a gas-only conditional calculation,
not a wet-brick drying simulation. JSONL retains completed steps on failure.
"""
import argparse
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction
import json
from pathlib import Path
import sys


def json_value(value):
    if isinstance(value, Fraction):
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if is_dataclass(value):
        return {item.name: getattr(value, item.name) for item in fields(value)}
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(type(value).__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--case', required=True)
    parser.add_argument('--resolution', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    parameter_path = args.parameters.resolve()
    root = parameter_path.parent
    config = json.loads(parameter_path.read_text())
    # The parameter file explicitly lives at the checked-out project root.
    sys.path.insert(0, str(root/'src'))
    from sludge_sandbox.gas_transport import ideal_gas_reservoir, ideal_gas_state
    from sludge_sandbox.open_gas_boundary import (
        GasBoundaryTransfer, apply_open_gas_rate, open_gas_boundary_rate,
    )
    from sludge_sandbox.thermochemistry import load_thermochemistry

    pack_path = root/config['thermochemistry_file']
    thermo = load_thermochemistry(pack_path)
    case = config['cases'][args.case]
    masses = config['molar_masses_kg_mol']
    transfer = GasBoundaryTransfer(**config['transfer'])
    reservoir = ideal_gas_reservoir(
        **case['reservoir'], molar_masses_kg_mol=masses,
        gas_constant_j_mol_k=thermo.gas_constant_j_mol_k,
    )
    initial = ideal_gas_reservoir(
        **case['cell'], molar_masses_kg_mol=masses,
        gas_constant_j_mol_k=thermo.gas_constant_j_mol_k,
    )
    volume = config['cell_volume_m3']
    amounts = {key: value*volume for key, value in initial.concentrations_mol_m3.items()}
    energy = thermo.mixture_internal_energy_j(amounts, initial.temperature_k)
    numerics = config['numerics']
    steps = numerics['steps'][args.resolution]
    duration = Fraction(str(numerics['duration_s']))
    if type(steps) is not int or steps <= 0 or duration <= 0:
        raise ValueError('duration_s and integer step count must be positive')
    step = duration/steps

    def decode(amounts, energy):
        temperature = thermo.temperature_from_internal_energy_j(
            energy, amounts, **numerics['inverse'],
        )
        return ideal_gas_state(
            amounts, temperature_k=temperature, gas_volume_m3=volume,
            molar_masses_kg_mol=masses,
            gas_constant_j_mol_k=thermo.gas_constant_j_mol_k,
        )

    def rate(gas):
        return open_gas_boundary_rate(
            gas, reservoir, transfer,
            lambda key, temperature: thermo.species(key).enthalpy_j_mol(temperature),
        )

    def state(amounts, energy, gas):
        return {'amounts_mol': amounts, 'internal_energy_j': energy,
                'temperature_k': gas.temperature_k, 'pressure_pa': gas.pressure_pa}

    with args.output.open('x') as stream:
        def emit(record):
            stream.write(json.dumps(record, default=json_value, allow_nan=False)+'\n')
            stream.flush()

        emit({'kind': 'input', 'case': args.case, 'resolution': args.resolution,
              'parameters': config, 'thermochemistry': json.loads(pack_path.read_text()),
              'method': 'explicit midpoint; no reactions or phase change; fixed gas volume',
              'material_qualified': False, 'training_eligible': False})
        gas = decode(amounts, energy)
        emit({'kind': 'initial', 'state': state(amounts, energy, gas)})
        for index in range(steps):
            predictor = apply_open_gas_rate(amounts, energy, rate(gas), step/2)
            midpoint = decode(predictor.amounts_mol, predictor.internal_energy_j)
            accepted_rate = rate(midpoint)
            update = apply_open_gas_rate(amounts, energy, accepted_rate, step)
            gas = decode(update.amounts_mol, update.internal_energy_j)
            emit({'kind': 'step', 'index': index+1, 'time_s': (index+1)*step,
                  'midpoint': state(predictor.amounts_mol, predictor.internal_energy_j, midpoint),
                  'rate': accepted_rate, 'update': update,
                  'state': state(update.amounts_mol, update.internal_energy_j, gas)})
            amounts, energy = update.amounts_mol, update.internal_energy_j
        emit({'kind': 'summary', 'status': 'completed', 'steps': steps,
              'duration_s': duration, 'final': state(amounts, energy, gas),
              'material_qualified': False, 'training_eligible': False})
    print(json.dumps({'case': args.case, 'steps': steps, 'status': 'completed',
                      'final': state(amounts, energy, gas)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
