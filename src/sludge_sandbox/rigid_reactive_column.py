"""Conservative sealed one-dimensional assembly of recorded rigid reactive cells."""
import numpy as np

from .equilibrium_calcite_rigid import RigidCalciteMixture
from .rigid_reactive_exchange import rigid_reactive_face


class RigidReactiveColumn:
    def __init__(self,reaction,nitrogen,volume_source,config,cell_count):
        self.config=config;self.count=cell_count;domain=config['domain']
        self.width=domain['length_m']/cell_count;self.volume=domain['area_m2']*self.width
        conductance=domain['area_m2']/self.width;transport=config['transport']
        self.face_parameters={'heat_conductance_w_k':transport['thermal_conductivity_w_m_k']*conductance,
            'bulk_mobility_mol2_k_j_s':transport['bulk_mobility_mol2_k_j_m_s']*conductance,
            'counter_mobility_mol2_k_j_s':transport['counter_mobility_mol2_k_j_m_s']*conductance}
        self.cells=[];initial=[]
        for i in range(cell_count):
            position=(i+.5)/cell_count
            region=next(r for r in domain['initial_regions'] if r['start_fraction']<=position<r['end_fraction'])
            cell=RigidCalciteMixture(reaction,nitrogen,volume_source,config,{'calcium_mol':domain['calcium_density_mol_m3']*self.volume,
                'nitrogen_mol':region['nitrogen_density_mol_m3']*self.volume,'total_volume_m3':self.volume})
            state=cell.at_temperature(region['temperature_k'],region['carbon_density_mol_m3']*self.volume)
            self.cells.append(cell);initial.extend((state['carbon_mol'],state['nitrogen_mol'],state['internal_energy_j']))
        self.initial=np.array(initial+[0.]*(3*(cell_count-1)+1))

    def states(self,values):
        return [cell.inventory_state(*[float(v) for v in values[3*i:3*i+3]]) for i,cell in enumerate(self.cells)]

    def faces(self,states):
        return [rigid_reactive_face(left,right,self.face_parameters) for left,right in zip(states[:-1],states[1:],strict=True)]

    def rates(self,time_s,values):
        faces=self.faces(self.states(values));out=np.zeros_like(values)
        for i,face in enumerate(faces):
            flow=np.array([face['carbon_flow_mol_s'],face['nitrogen_flow_mol_s'],face['energy_flow_w']])
            out[3*i:3*i+3]-=flow;out[3*i+3:3*i+6]+=flow
            out[3*self.count+3*i:3*self.count+3*i+3]=flow
            out[-1]+=face['entropy_production_w_k']
        return out
