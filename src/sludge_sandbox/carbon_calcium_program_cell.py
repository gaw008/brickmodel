"""Restricted reactive capsule with a continuous externally prescribed gas bath."""
import numpy as np

from .boundary_program import BoundaryProgram, ProgramIdentity
from .carbon_calcium_open_cell import ideal_gas_reservoir
from .carbon_calcium_rigid_exchange import exchange
from .carbon_calcium_rigid_tangent import rigid_tangent


class CarbonCalciumProgramCell:
    def __init__(self, model, settings, face_parameters, rigid_numerics):
        self.model, self.settings = model, settings
        self.face_parameters, self.rigid_numerics = face_parameters, rigid_numerics
        self.volume = settings['volume_m3']
        initial = settings['initial']
        self.calcium = initial['calcium_atoms_mol']
        self.initial = np.array([
            initial['carbon_atoms_mol'], initial['oxygen_atoms_mol'],
            initial['nitrogen_molecules_mol'], initial['temperature_k'], 0., 0., 0.])
        specification = dict(settings['boundary_program'])
        specification['identity'] = ProgramIdentity(**specification['identity'])
        self.program = BoundaryProgram(**specification)

    def reservoir_at(self, at):
        external = self.program.at(at)
        return ideal_gas_reservoir(self.model, external.gas_temperature_k,
                                   external.total_pressure_pa, external.mole_fractions)

    def state(self, values):
        return self.model.at_temperature_volume(float(values[3]), self.volume, self.calcium,
                                                *map(float, values[:3]), self.rigid_numerics)

    def observe(self, at, values):
        state, reservoir = self.state(values), self.reservoir_at(at)
        return state, reservoir, exchange(self.model, reservoir, state, self.face_parameters)

    def rates(self, at, values):
        state, _, face = self.observe(at, values)
        inventories = np.array([face['inventory_flows_mol_s'][key]
                                for key in self.face_parameters['transferred_inventory_order']])
        tangent = rigid_tangent(self.model, state, self.volume, self.calcium,
                                float(values[0]), float(values[1]))
        du = np.array(tangent['internal_energy_derivatives'])
        temperature_rate = (face['energy_flow_w'] - du[1:] @ inventories) / du[0]
        return np.array([*inventories, temperature_rate, face['energy_flow_w'],
                         face['left_entropy_rate_w_k'], face['entropy_production_w_k']])
