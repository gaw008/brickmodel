"""Conservative closed column assembled from qualified reactive gas faces."""
import math

import numpy as np
from scipy.sparse import lil_matrix

from .carbon_calcium_rigid_exchange import exchange,exchange_jacobian
from .carbon_calcium_rigid_tangent import rigid_tangent


class CarbonCalciumRigidColumn:
    def __init__(self,model,settings,face_parameters,rigid_numerics,count):
        self.model,self.settings,self.rigid_numerics,self.count=model,settings,rigid_numerics,count
        geometry=settings['geometry'];self.width=geometry['length_m']/count;self.volume=self.width*geometry['area_m2']
        self.centers=[(i+.5)*self.width for i in range(count)];initial=settings['initial'];transport=settings['transport']
        self.face_parameters={**face_parameters,'heat_conductance_w_k':transport['thermal_conductivity_w_m_k']*geometry['area_m2']/self.width,
            'gas_mobilities_mol2_k_j_s':{k:v*geometry['area_m2']/self.width for k,v in transport['gas_mobility_density_mol2_k_j_m_s'].items()}}
        self.inventories=[{key:initial[density]*self.volume for key,density in
            [('calcium_atoms_mol','calcium_density_mol_m3'),('carbon_atoms_mol','carbon_density_mol_m3'),
             ('oxygen_atoms_mol','oxygen_density_mol_m3'),('nitrogen_molecules_mol','nitrogen_density_mol_m3')]} for _ in range(count)]
        self.initial_states=[]
        for center,inventory in zip(self.centers,self.inventories,strict=True):
            t=initial['temperature_left_k'] if center<initial['interface_length_fraction']*geometry['length_m'] else initial['temperature_right_k']
            self.initial_states.append(model.at_temperature_volume(t,self.volume,*inventory.values(),rigid_numerics))
        self.initial_energies=[s['internal_energy_j'] for s in self.initial_states]
        self.initial=np.array([x for inv in self.inventories for x in [inv['carbon_atoms_mol'],inv['oxygen_atoms_mol'],inv['nitrogen_molecules_mol'],0.]]+[0.])

    def states(self,values):
        return [self.model.from_internal_energy(self.initial_energies[i]+float(values[4*i+3]),self.volume,
            self.inventories[i]['calcium_atoms_mol'],*map(float,values[4*i:4*i+3]),self.rigid_numerics) for i in range(self.count)]

    def observe(self,values):
        states=self.states(values)
        faces=[exchange(self.model,left,right,self.face_parameters) for left,right in zip(states[:-1],states[1:],strict=True)]
        return states,faces

    def rates(self,at,values):
        _,faces=self.observe(values);result=np.zeros((self.count,4))
        keys=self.face_parameters['transferred_inventory_order']
        for i,face in enumerate(faces):
            flow=np.array([*[face['inventory_flows_mol_s'][k] for k in keys],face['energy_flow_w']])
            result[i]-=flow;result[i+1]+=flow
        return np.concatenate((result.ravel(),[math.fsum(f['entropy_production_w_k'] for f in faces)]))

    def jacobian(self,at,values):
        states=self.states(values);tangents=[rigid_tangent(self.model,s,self.volume,self.inventories[i]['calcium_atoms_mol'],
            float(values[4*i]),float(values[4*i+1])) for i,s in enumerate(states)]
        result=lil_matrix((4*self.count+1,4*self.count+1));keys=self.face_parameters['transferred_inventory_order']
        for i in range(self.count-1):
            face=exchange_jacobian(self.model,states[i],states[i+1],tangents[i],tangents[i+1],self.face_parameters)
            derivative=np.array([*[face['inventory'][k] for k in keys],face['energy']]);start=4*i
            result[start:start+4,start:start+8]-=derivative
            result[start+4:start+8,start:start+8]+=derivative
            result[-1,start:start+8]+=np.array(face['production'])
        return result.tocsc()
