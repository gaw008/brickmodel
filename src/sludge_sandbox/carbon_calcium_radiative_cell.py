"""Positive-inventory open cell with a separate prescribed black enclosure."""
import numpy as np

from .carbon_calcium_caloric_inventory import caloric_inventory_tangent
from .carbon_calcium_inventory_open_cell import CarbonCalciumInventoryOpenCell


def black_enclosure_exchange(temperature, parameters):
    reservoir = parameters['reservoir_temperature_k']
    coefficient = (parameters['emissivity'] * parameters['area_m2']
                   * parameters['stefan_boltzmann_w_m2_k4'])
    heat = coefficient * (reservoir - temperature) * (reservoir + temperature) * (
        reservoir * reservoir + temperature * temperature)
    return {
        'energy_in_w': heat,
        'body_entropy_rate_w_k': heat / temperature,
        'reservoir_entropy_rate_w_k': -heat / reservoir,
        'entropy_production_w_k': heat * (reservoir - temperature) / (reservoir * temperature),
        'temperature_derivative_w_k': -4 * coefficient * temperature ** 3,
        'reservoir_temperature_k': reservoir,
    }


class CarbonCalciumRadiativeCell(CarbonCalciumInventoryOpenCell):
    def __init__(self, model, settings, face_parameters, rigid_numerics):
        super().__init__(model, settings, face_parameters, rigid_numerics)
        self.initial = np.concatenate((self.initial, [0., 0.]))

    def radiation(self, state):
        return black_enclosure_exchange(state['temperature_k'], self.settings['radiation'])

    def rates(self, at, values):
        state, gas = self.observe(values)
        radiation = self.radiation(state)
        return combined_rates(self, state, gas, radiation, values)


def combined_rates(cell, state, gas, radiation, values):
    inventories = np.array([gas['inventory_flows_mol_s'][key]
                            for key in cell.face_parameters['transferred_inventory_order']])
    tangent = caloric_inventory_tangent(cell.model, state, cell.volume, cell.calcium,
                                        float(values[0]), float(values[1]))
    du = np.array(tangent['internal_energy_derivatives'])
    energy = gas['energy_flow_w'] + radiation['energy_in_w']
    temperature_rate = (energy - du[1:] @ inventories) / du[0]
    return np.array([
        *inventories, temperature_rate, energy, gas['left_entropy_rate_w_k'],
        gas['entropy_production_w_k'] + radiation['entropy_production_w_k'],
        radiation['energy_in_w'], radiation['reservoir_entropy_rate_w_k']])
