"""Rigid reacting cell coupled to zero-storage gas and radiation contacts."""
import numpy as np

from .rigid_reactive_surface import RigidReactiveSurface, gas_contact_state


class OpenRigidCalciteCell:
    def __init__(self, cell, surface_parameters, program):
        self.cell = cell
        self.surface = RigidReactiveSurface(cell, surface_parameters)
        self.program = program
        self.reservoirs = [gas_contact_state(cell, p['gas_temperature_k'], p['pressure_pa'], p['co2_mole_fraction']) for p in program]

    def observe(self, values, segment_index, carbon_offset_mol=None):
        state = (self.cell.inventory_state(*values[:3]) if carbon_offset_mol is None
                 else self.cell.offset_inventory_state(carbon_offset_mol,*values[1:3]))
        reservoir = self.reservoirs[segment_index]
        contact = self.surface.solve(state, reservoir, self.program[segment_index]['radiation_temperature_k'])
        return state, reservoir, contact

    def rates(self, time_s, values, segment_index, carbon_offset_mol=None):
        _, reservoir, contact = self.observe(values, segment_index, carbon_offset_mol)
        inner = np.array([contact['interior_face'][k] for k in ('carbon_flow_mol_s','nitrogen_flow_mol_s','energy_flow_w')])
        outer = np.array([contact['exterior_face'][k] for k in ('carbon_flow_mol_s','nitrogen_flow_mol_s','energy_flow_w')])
        radiation = contact['radiation_in_w']
        gas_entropy = (outer[2]-reservoir['carbon_chemical_potential_j_mol']*outer[0]-reservoir['nitrogen_chemical_potential_j_mol']*outer[1])/reservoir['temperature_k']
        radiation_entropy = -radiation/self.program[segment_index]['radiation_temperature_k']
        return np.concatenate((-inner, inner, outer, [radiation, gas_entropy, radiation_entropy, contact['entropy_production_w_k']]))
