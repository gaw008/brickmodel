"""One-dimensional rigid equilibrium cells with one open radiating surface.

Integrate per-cell carbon excess, log-N2 and U. Internal faces enter adjacent
cells with opposite signs. Only exterior ledgers are additional ODE states;
local conservation is reviewed by independent full-trajectory face integrals.
"""
from copy import deepcopy

import numpy as np
from scipy.sparse import coo_matrix, diags

from .rigid_reactive_offset import OffsetRigidCalciteMixture
from .rigid_reactive_open_cell import OpenRigidCalciteCell
from .rigid_reactive_exchange import rigid_reactive_face
from .rigid_reactive_source_force import source_integral_rigid_face
from .rigid_reactive_tangent import inventory_tangent, face_tangents


class OpenRigidReactiveColumn:
    def __init__(self,reaction,nitrogen,volume_source,model_parameters,settings,surface_parameters,cell_count,cell_widths_m=None):
        self.settings = settings;self.count = cell_count;domain = settings['domain']
        self.width = domain['length_m']/cell_count;self.volume = domain['area_m2']*self.width
        self.widths = np.full(cell_count,self.width) if cell_widths_m is None else np.asarray(cell_widths_m,dtype=float)
        self.volumes = domain['area_m2']*self.widths
        self.reference_nitrogen = settings['coordinates']['reference_nitrogen_density_mol_m3']*self.volume
        self.log_carbon = settings['coordinates']['carbon']=='log_total_over_calcium_with_expm1_offset'
        self.cells = [];initial = [];condition = settings['initial']
        for volume in self.volumes:
            cell = OffsetRigidCalciteMixture(reaction,nitrogen,volume_source,model_parameters,{
                'calcium_mol':domain['calcium_density_mol_m3']*volume,
                'nitrogen_mol':condition['nitrogen_density_mol_m3']*volume,'total_volume_m3':volume})
            offset = condition['excess_carbon_density_mol_m3']*volume
            state = cell.at_carbon_offset(condition['temperature_k'],offset,cell.carrier)
            initial.extend((self.carbon_coordinate(cell,offset),np.log(state['nitrogen_mol']/self.reference_nitrogen),state['internal_energy_j']))
            self.cells.append(cell)
        self.initial = np.array(initial+[0.]*10)
        transport = settings['transport'];conductance = domain['area_m2']/self.width
        self.face_parameters = {
            'heat_conductance_w_k':transport['thermal_conductivity_w_m_k']*conductance,
            'bulk_mobility_mol2_k_j_s':transport['bulk_mobility_mol2_k_j_m_s']*conductance,
            'counter_mobility_mol2_k_j_s':transport['counter_mobility_mol2_k_j_m_s']*conductance}
        self.internal_face_parameters = [self.face_parameters]*(cell_count-1) if cell_widths_m is None else [
            {'heat_conductance_w_k':transport['thermal_conductivity_w_m_k']*domain['area_m2']/distance,
             'bulk_mobility_mol2_k_j_s':transport['bulk_mobility_mol2_k_j_m_s']*domain['area_m2']/distance,
             'counter_mobility_mol2_k_j_s':transport['counter_mobility_mol2_k_j_m_s']*domain['area_m2']/distance}
            for distance in (self.widths[:-1]+self.widths[1:])/2]
        self.surface_parameters = deepcopy(surface_parameters)
        self.surface_parameters['area_m2'] = domain['area_m2']
        self.surface_parameters['interior'] = {
            'distance_m':float(self.widths[-1]/2),'conductivity_w_m_k':transport['thermal_conductivity_w_m_k'],
            'bulk_mobility_mol2_k_j_m_s':transport['bulk_mobility_mol2_k_j_m_s'],
            'counter_mobility_mol2_k_j_m_s':transport['counter_mobility_mol2_k_j_m_s']}
        self.boundary = OpenRigidCalciteCell(self.cells[-1],self.surface_parameters,settings['boundary_program'])
        self.face = rigid_reactive_face
        if 'species_force_evaluation' in settings:
            self.face = {'source_integral_differences': lambda left,right,params:
                source_integral_rigid_face(left,right,params,self.cells[0])}[settings['species_force_evaluation']]

    def carbon_coordinate(self,cell,offset):
        return np.log1p(offset/cell.calcium) if self.log_carbon else offset

    def physical_values(self,values):
        result = values.copy()
        for i,cell in enumerate(self.cells):
            result[3*i] = cell.calcium*np.exp(values[3*i]) if self.log_carbon else values[3*i]+cell.calcium
            result[3*i+1] = self.reference_nitrogen*np.exp(values[3*i+1])
        return result

    def observe(self,values,segment):
        physical = self.physical_values(values)
        states = [cell.offset_inventory_state(cell.calcium*np.expm1(values[3*i]),*physical[3*i+1:3*i+3],physical[3*i])
                  if self.log_carbon else cell.offset_inventory_state(values[3*i],*physical[3*i+1:3*i+3])
                  for i,cell in enumerate(self.cells)]
        faces = [self.face(left,right,parameters) for left,right,parameters in zip(states[:-1],states[1:],self.internal_face_parameters,strict=True)]
        reservoir = self.boundary.reservoirs[segment]
        contact = self.boundary.surface.solve(states[-1],reservoir,self.settings['boundary_program'][segment]['radiation_temperature_k'])
        return physical,states,faces,reservoir,contact

    def physical_rates(self,physical,faces,reservoir,contact,segment):
        out = np.zeros_like(physical)
        for i,face in enumerate(faces):
            flux = np.array([face[k] for k in ('carbon_flow_mol_s','nitrogen_flow_mol_s','energy_flow_w')])
            out[3*i:3*i+3] -= flux;out[3*i+3:3*i+6] += flux
            out[-1] += face['entropy_production_w_k']
        inner = np.array([contact['interior_face'][k] for k in ('carbon_flow_mol_s','nitrogen_flow_mol_s','energy_flow_w')])
        outer = np.array([contact['exterior_face'][k] for k in ('carbon_flow_mol_s','nitrogen_flow_mol_s','energy_flow_w')])
        radiation = contact['radiation_in_w'];base = 3*self.count
        out[base-3:base] -= inner
        gas_entropy = (outer[2]-reservoir['carbon_chemical_potential_j_mol']*outer[0]-reservoir['nitrogen_chemical_potential_j_mol']*outer[1])/reservoir['temperature_k']
        wall_entropy = -radiation/self.settings['boundary_program'][segment]['radiation_temperature_k']
        out[base:base+9] = np.concatenate((inner,outer,[radiation,gas_entropy,wall_entropy]))
        out[-1] += contact['entropy_production_w_k']
        return out

    def rates(self,time_s,values,segment):
        physical,_,faces,reservoir,contact = self.observe(values,segment)
        out = self.physical_rates(physical,faces,reservoir,contact,segment)
        if self.log_carbon:out[0:3*self.count:3] /= physical[0:3*self.count:3]
        out[1:3*self.count:3] /= physical[1:3*self.count:3]
        return out

    def jacobian(self,time_s,values,segment):
        physical,states,faces,reservoir,contact = self.observe(values,segment)
        tangents = [inventory_tangent(c,s) for c,s in zip(self.cells,states,strict=True)]
        rows,columns,entries = [],[],[]
        def block(row,column,matrix):
            for i in range(matrix.shape[0]):
                for j in range(matrix.shape[1]):
                    rows.append(row+i);columns.append(column+j);entries.append(matrix[i,j])
        for i in range(self.count-1):
            pair = face_tangents(states[i],states[i+1],tangents[i],tangents[i+1],self.internal_face_parameters[i],
                faces[i] if 'species_force_evaluation' in self.settings else None)
            for side,derivative in enumerate(pair):
                column = 3*(i+side)
                block(3*i,column,-derivative[:3]);block(3*i+3,column,derivative[:3])
                block(len(values)-1,column,derivative[3:4])
        last = 3*(self.count-1);base = 3*self.count
        inner_d = np.array(contact['interior_flux_inventory_derivative'])
        surface_d = np.array(contact['surface_coordinate_inventory_derivative'])
        radiation_d = -4*self.boundary.surface.radiation_factor*contact['surface']['temperature_k']**3*surface_d[0]
        outer_d = inner_d.copy();outer_d[2] += radiation_d
        reservoir_entropy_gradient = np.array([-reservoir['carbon_chemical_potential_j_mol'],
            -reservoir['nitrogen_chemical_potential_j_mol'],1.])/reservoir['temperature_k']
        gas_s_d = reservoir_entropy_gradient@outer_d
        wall_s_d = -radiation_d/self.settings['boundary_program'][segment]['radiation_temperature_k']
        state = states[-1];body_entropy_gradient = np.array([-state['carbon_chemical_potential_j_mol'],
            -state['nitrogen_chemical_potential_j_mol'],1.])/state['temperature_k']
        inner = np.array([contact['interior_face'][k] for k in ('carbon_flow_mol_s','nitrogen_flow_mol_s','energy_flow_w')])
        production_d = -inner@tangents[-1]['entropy_hessian']-body_entropy_gradient@inner_d+gas_s_d+wall_s_d
        block(last,last,-inner_d)
        block(base,last,np.vstack((inner_d,outer_d,radiation_d,gas_s_d,wall_s_d,production_d)))
        matrix = coo_matrix((entries,(rows,columns)),shape=(len(values),len(values))).tocsc()
        chart = np.ones(len(values));chart[1:base:3] = physical[1:base:3]
        if self.log_carbon:chart[0:base:3] = physical[0:base:3]
        # dz_N/dt=f_N/N: differentiate both f_N and the row factor 1/N.
        diagonal = np.zeros(len(values))
        physical_rate = self.physical_rates(physical,faces,reservoir,contact,segment)
        diagonal[1:base:3] = -physical_rate[1:base:3]/physical[1:base:3]
        if self.log_carbon:diagonal[0:base:3] = -physical_rate[0:base:3]/physical[0:base:3]
        return (diags(1/chart)@matrix@diags(chart)+diags(diagonal)).tocsc()
