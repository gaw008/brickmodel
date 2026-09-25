"""Equivalent reactive transport in elemental-inventory/temperature coordinates."""
import math

import numpy as np
from scipy.sparse import lil_matrix

from .carbon_calcium_rigid_column import CarbonCalciumRigidColumn
from .carbon_calcium_rigid_exchange import exchange
from .carbon_calcium_rigid_tangent import rigid_tangent


class CarbonCalciumTemperatureColumn:
    def __init__(self,model,settings,face_parameters,rigid_numerics,count):
        geometry=CarbonCalciumRigidColumn(model,settings,face_parameters,rigid_numerics,count)
        self.model,self.rigid_numerics,self.count=model,rigid_numerics,count
        self.width,self.volume,self.centers=geometry.width,geometry.volume,geometry.centers
        self.face_parameters,self.inventories=geometry.face_parameters,geometry.inventories
        self.initial_energies=geometry.initial_energies;self.initial=geometry.initial.copy()
        for i,state in enumerate(geometry.initial_states):self.initial[4*i+3]=state['temperature_k']

    def states(self,values):
        return [self.model.at_temperature_volume(float(values[4*i+3]),self.volume,self.inventories[i]['calcium_atoms_mol'],
            *map(float,values[4*i:4*i+3]),self.rigid_numerics) for i in range(self.count)]

    def conserved_values(self,values,states):
        physical=values.copy()
        for i,state in enumerate(states):physical[4*i+3]=state['internal_energy_j']-self.initial_energies[i]
        return physical

    def observe(self,values):
        states=self.states(values)
        faces=[exchange(self.model,a,b,self.face_parameters) for a,b in zip(states[:-1],states[1:],strict=True)]
        return states,faces

    def rates(self,at,values):
        states,faces=self.observe(values);result=np.zeros((self.count,4));keys=self.face_parameters['transferred_inventory_order']
        for i,face in enumerate(faces):
            flow=np.array([*[face['inventory_flows_mol_s'][k] for k in keys],face['energy_flow_w']])
            result[i]-=flow;result[i+1]+=flow
        for i,state in enumerate(states):
            tangent=rigid_tangent(self.model,state,self.volume,self.inventories[i]['calcium_atoms_mol'],values[4*i],values[4*i+1])
            du=np.array(tangent['internal_energy_derivatives'])
            result[i,3]=(result[i,3]-du[1:]@result[i,:3])/du[0]
        return np.concatenate((result.ravel(),[math.fsum(f['entropy_production_w_k'] for f in faces)]))

    def numerical_jacobian_sparsity(self):
        size=4*self.count+1;pattern=lil_matrix((size,size))
        for i in range(self.count):pattern[4*i:4*i+4,4*max(0,i-1):4*min(self.count,i+2)]=1
        pattern[-1,:-1]=1
        return pattern.tocsc()
