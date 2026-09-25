"""Reactive column receiving the inner flux of a zero-storage surface."""
import math

import numpy as np

from .carbon_calcium_caloric_inventory import caloric_inventory_tangent
from .carbon_calcium_integral_surface import surface_exchange
from .carbon_calcium_open_cell import ideal_gas_reservoir
from .carbon_calcium_open_column import CarbonCalciumOpenColumn
from .carbon_calcium_rigid_exchange import exchange


class CarbonCalciumSurfaceColumn(CarbonCalciumOpenColumn):
    def __init__(self, model, settings, cell_settings, face_parameters, rigid_numerics, count, surface_settings):
        super().__init__(model, settings, cell_settings, face_parameters, rigid_numerics, count)
        self.surface_settings = surface_settings
        self.surface_interior = dict(self.face_parameters,
            heat_conductance_w_k=2*self.face_parameters['heat_conductance_w_k'],
            gas_mobilities_mol2_k_j_s={k: 2*v for k,v in self.face_parameters['gas_mobilities_mol2_k_j_s'].items()})

    def observe(self, at, values):
        states = self.states(values)
        faces = [exchange(self.model, left, right, self.face_parameters)
                 for left,right in zip(states[:-1],states[1:],strict=True)]
        external = self.program.at(at)
        reservoir = ideal_gas_reservoir(self.model,external.gas_temperature_k,
            external.total_pressure_pa,external.mole_fractions)
        radiation = dict(self.cell_settings['radiation'],reservoir_temperature_k=external.radiation_temperature_k)
        surface = surface_exchange(self.model,states[-1],reservoir,self.surface_interior,
            self.exterior_parameters,radiation,self.surface_settings)
        return states,faces,reservoir,surface

    def rates(self, at, values):
        return self.rate_components(at, values)[0]

    def rate_components(self, at, values):
        """Return unchanged body/exterior rates and internal/surface production."""
        states,faces,_,surface = self.observe(at,values)
        result = np.zeros((self.count,4))
        keys = self.face_parameters['transferred_inventory_order']
        for i,face in enumerate(faces):
            transfer = np.array([*[face['inventory_flows_mol_s'][k] for k in keys],face['energy_flow_w']])
            result[i] -= transfer
            result[i+1] += transfer
        inner,outer,rad = surface['inner'],surface['outer'],surface['radiation']
        result[-1] += np.array([*[inner['inventory_flows_mol_s'][k] for k in keys],inner['energy_flow_w']])
        for i,state in enumerate(states):
            tangent = caloric_inventory_tangent(self.model,state,self.volume,self.calcium,
                float(values[4*i]),float(values[4*i+1]))
            du = np.array(tangent['internal_energy_derivatives'])
            result[i,3] = (result[i,3]-du[1:]@result[i,:3])/du[0]
        production = math.fsum([f['entropy_production_w_k'] for f in faces]
            +[surface['combined_entropy_production_w_k']])
        external_energy = outer['energy_flow_w']+rad['energy_in_w']
        rates = np.concatenate((result.ravel(),[external_energy,outer['left_entropy_rate_w_k'],
            production,rad['energy_in_w'],rad['reservoir_entropy_rate_w_k']]))
        return rates, np.array([f['entropy_production_w_k'] for f in faces]
                              + [surface['combined_entropy_production_w_k']])
