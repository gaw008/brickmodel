"""Conservative positive-inventory chain with one gas/radiation contact."""
import math

import numpy as np
from scipy.sparse import lil_matrix

from .boundary_program import BoundaryProgram, ProgramIdentity
from .carbon_calcium_caloric_inventory import caloric_inventory_tangent
from .carbon_calcium_open_cell import ideal_gas_reservoir
from .carbon_calcium_radiative_cell import black_enclosure_exchange
from .carbon_calcium_rigid_exchange import exchange


class CarbonCalciumOpenColumn:
    def __init__(self, model, settings, cell_settings, face_parameters, rigid_numerics, count):
        self.model, self.settings, self.cell_settings = model, settings, cell_settings
        self.count, self.rigid_numerics = count, rigid_numerics
        geometry = settings['geometry']
        self.width = geometry['length_m'] / count
        self.volume = self.width * geometry['area_m2']
        self.centers = [(i + .5) * self.width for i in range(count)]
        initial = cell_settings['initial']
        self.calcium = initial['calcium_atoms_mol'] / count
        inventory = [initial[k] / count for k in ('carbon_atoms_mol', 'oxygen_atoms_mol', 'nitrogen_molecules_mol')]
        self.initial = np.array((inventory + [initial['temperature_k']]) * count + [0.] * 5)
        transport = settings['transport']
        self.face_parameters = dict(face_parameters,
            heat_conductance_w_k=transport['thermal_conductivity_w_m_k'] * geometry['area_m2'] / self.width,
            gas_mobilities_mol2_k_j_s={k: v * geometry['area_m2'] / self.width
                for k, v in transport['gas_mobility_density_mol2_k_j_m_s'].items()})
        self.exterior_parameters = face_parameters
        specification = dict(cell_settings['boundary_program'])
        specification['identity'] = ProgramIdentity(**specification['identity'])
        self.program = BoundaryProgram(**specification)
        self.initial_states = self.states(self.initial)

    def states(self, values):
        return [self.model.at_temperature_volume(float(values[4*i+3]), self.volume, self.calcium,
            *map(float, values[4*i:4*i+3]), self.rigid_numerics) for i in range(self.count)]

    def observe(self, at, values):
        states = self.states(values)
        faces = [exchange(self.model, left, right, self.face_parameters)
                 for left, right in zip(states[:-1], states[1:], strict=True)]
        external = self.program.at(at)
        reservoir = ideal_gas_reservoir(self.model, external.gas_temperature_k,
                                       external.total_pressure_pa, external.mole_fractions)
        contact = exchange(self.model, reservoir, states[-1], self.exterior_parameters)
        radiation = black_enclosure_exchange(states[-1]['temperature_k'], dict(
            self.cell_settings['radiation'], reservoir_temperature_k=external.radiation_temperature_k))
        return states, faces, reservoir, contact, radiation

    def rates(self, at, values):
        states, faces, _, contact, radiation = self.observe(at, values)
        result = np.zeros((self.count, 4))
        keys = self.face_parameters['transferred_inventory_order']
        for i, face in enumerate(faces):
            transfer = np.array([*[face['inventory_flows_mol_s'][k] for k in keys], face['energy_flow_w']])
            result[i] -= transfer
            result[i+1] += transfer
        incoming_energy = contact['energy_flow_w'] + radiation['energy_in_w']
        result[-1] += np.array([*[contact['inventory_flows_mol_s'][k] for k in keys], incoming_energy])
        for i, state in enumerate(states):
            tangent = caloric_inventory_tangent(self.model, state, self.volume, self.calcium,
                                                float(values[4*i]), float(values[4*i+1]))
            du = np.array(tangent['internal_energy_derivatives'])
            result[i, 3] = (result[i, 3] - du[1:] @ result[i, :3]) / du[0]
        production = math.fsum([f['entropy_production_w_k'] for f in faces]
            + [contact['entropy_production_w_k'], radiation['entropy_production_w_k']])
        return np.concatenate((result.ravel(), [incoming_energy, contact['left_entropy_rate_w_k'],
            production, radiation['energy_in_w'], radiation['reservoir_entropy_rate_w_k']]))

    def numerical_jacobian_sparsity(self):
        body = 4 * self.count
        pattern = lil_matrix((body + 5, body + 5))
        for i in range(self.count):
            pattern[4*i:4*i+4, 4*max(0, i-1):4*min(self.count, i+2)] = 1
        pattern[body:, body-4:body] = 1
        pattern[body+2, :body] = 1
        return pattern.tocsc()
