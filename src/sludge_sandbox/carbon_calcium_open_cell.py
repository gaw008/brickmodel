"""Restricted reactive rigid cell exchanging with a prescribed ideal gas bath.

The bath composition is externally maintained, not locally equilibrated. The
existing virtual face law defines heat and gas transport, including bath entropy.
"""
import math

import numpy as np

from .carbon_calcium_rigid_exchange import exchange
from .carbon_calcium_rigid_tangent import rigid_tangent


def ideal_gas_reservoir(model, temperature, pressure, mole_fractions):
    chemical = {}
    for name, fraction in mole_fractions.items():
        standard = model.phases[name].standard(temperature)
        chemical[name] = standard['gibbs_j_mol'] + model.r * temperature * math.log(
            fraction * pressure / model.p0)
    return {
        'temperature_k': temperature,
        'pressure_pa': pressure,
        'mole_fractions': dict(mole_fractions),
        'chemical_potentials_j_mol': chemical,
    }


class CarbonCalciumOpenCell:
    def __init__(self, model, settings, face_parameters, rigid_numerics):
        self.model, self.settings = model, settings
        self.face_parameters, self.rigid_numerics = face_parameters, rigid_numerics
        self.volume = settings['volume_m3']
        initial = settings['initial']
        self.calcium = initial['calcium_atoms_mol']
        self.initial = np.array([
            initial['carbon_atoms_mol'], initial['oxygen_atoms_mol'],
            initial['nitrogen_molecules_mol'], initial['temperature_k'],
            0., 0., 0.])
        bath = settings['reservoir']
        self.reservoir = ideal_gas_reservoir(
            model, bath['temperature_k'], bath['pressure_pa'], bath['mole_fractions'])
        self.initial_state = self.state(self.initial)

    def state(self, values):
        return self.model.at_temperature_volume(
            float(values[3]), self.volume, self.calcium,
            *map(float, values[:3]), self.rigid_numerics)

    def observe(self, values):
        state = self.state(values)
        return state, exchange(self.model, self.reservoir, state, self.face_parameters)

    def rates(self, at, values):
        state, face = self.observe(values)
        inventories = np.array([face['inventory_flows_mol_s'][key]
                                for key in self.face_parameters['transferred_inventory_order']])
        tangent = rigid_tangent(self.model, state, self.volume, self.calcium,
                                float(values[0]), float(values[1]))
        du = np.array(tangent['internal_energy_derivatives'])
        temperature_rate = (face['energy_flow_w'] - du[1:] @ inventories) / du[0]
        return np.array([
            *inventories, temperature_rate, face['energy_flow_w'],
            face['left_entropy_rate_w_k'], face['entropy_production_w_k']])
