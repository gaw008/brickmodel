"""Specified heat additions and phase-boundary states for a closed fluid cell.

This records thermodynamic calculations, not experimental measurements. Source
EOS saturation pressures and the approximate carrier-mixture equilibrium are
reported separately; they are not assumed identical.
"""
import argparse
import json
import math
from pathlib import Path
import sys

from scipy.optimize import brentq


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    config = json.loads(args.parameters.read_text())
    sys.path.insert(0, str(root/'src'))
    from sludge_sandbox.equilibrium_water_cell import EquilibriumWaterCell
    from sludge_sandbox.recorded_water import RecordedWaterProperties
    from sludge_sandbox.thermochemistry import load_thermochemistry
    from sludge_sandbox.water_properties import NumericalLimits

    water = RecordedWaterProperties(root/config['water_facts_file'],
                                    NumericalLimits(**config['numerics']['water']))
    thermo = load_thermochemistry(root/config['thermochemistry_file'])
    host = EquilibriumWaterCell(water, thermo, config['molar_masses_kg_mol'],
                                **config['storage'], numerics=config['numerics'])
    settings = config['verification']
    inventory = config['cases']['liquid_depletion']['cell']['inventories_mol']
    temperature = settings['closed_cell_temperature_k']
    _, initial = host.at_temperature(inventory, temperature)
    initial_u = initial['constitutive_internal_energy_j']
    r = thermo.gas_constant_j_mol_k
    volume = host.available_fluid_volume_m3

    with args.output.open('x') as stream:
        def emit(record):
            stream.write(json.dumps(record, allow_nan=False)+'\n')
            stream.flush()

        emit({'kind': 'input', 'parameters': config, 'water_source': water.source_record,
              'material_qualified': False, 'training_eligible': False})
        emit({'kind': 'initial', 'state': initial})
        for heat in settings['closed_cell_heat_inputs_j']:
            _, point = host.decode(inventory, initial_u+heat)
            emit({'kind': 'closed_heat', 'heat_added_j': heat, 'state': point})
        _, returned = host.decode(inventory, initial_u)
        emit({'kind': 'closed_heat_removed', 'heat_removed_j': heat, 'state': returned})

        carrier_pressure = sum(n for k, n in inventory.items() if k != 'H2O')*r*temperature/volume
        mu_standard = host.gas_enthalpy_j_mol('H2O', temperature)-temperature*(
            host.vapor_standard_entropy_j_mol_k(temperature))
        # At the dry endpoint, P = P_carrier + p_eq(T, P).
        def endpoint_residual(pressure):
            liquid = water.state_tp(temperature, pressure, phase='liquid')
            mu_liquid = liquid.enthalpy_j_mol-temperature*(
                liquid.native_entropy_j_kg_k*liquid.molar_mass_kg_mol)
            pe = host.reference_pressure_pa*math.exp((mu_liquid-mu_standard)/(r*temperature))
            return pressure-carrier_pressure-pe

        setting = config['numerics']['pressure_inverse']
        # Carrier pressure is the zero-water endpoint; the source upper bracket
        # is the other endpoint. No negative water trial is constructed.
        pressure = brentq(endpoint_residual, carrier_pressure, setting['bracket_pa'][1],
                          xtol=setting['absolute_tolerance_pa'],
                          rtol=setting['relative_tolerance'], maxiter=setting['max_iterations'])
        critical_water = (pressure-carrier_pressure)*volume/(r*temperature)
        for relative_offset in settings['phase_boundary_relative_water_offsets']:
            _, point = host.at_temperature(
                {**inventory, 'H2O': critical_water*(1+relative_offset)}, temperature)
            emit({'kind': 'phase_endpoint', 'critical_water_mol': critical_water,
                  'relative_water_offset': relative_offset, 'state': point})
        _, point = host.at_temperature({**inventory, 'H2O': 0.}, temperature)
        emit({'kind': 'zero_water', 'state': point})

        for t in settings['source_reference_temperatures_k']:
            pair = water.saturation_pair(t)
            _, point = host.at_temperature(inventory, t)
            emit({'kind': 'model_comparison', 'temperature_k': t,
                  'native_pure_water_saturation_pressure_pa': pair.pressure_pa,
                  'mixture_equilibrium_water_pressure_pa': point['equilibrium_partial_pressure_pa'],
                  'mixture_total_pressure_pa': point['pressure_pa'],
                  'difference_relative_to_native_saturation': (
                      point['equilibrium_partial_pressure_pa']/pair.pressure_pa-1),
                  'scope': 'approximation difference, not an experimental validation error'})
        emit({'kind': 'summary', 'status': 'completed',
              'material_qualified': False, 'training_eligible': False})


if __name__ == '__main__':
    main()
