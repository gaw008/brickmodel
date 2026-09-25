"""Virtual dissipative heat/gas exchange between restricted equilibrium cells."""
import math

import numpy as np


def exchange(model, left, right, parameters):
    tl,tr=left['temperature_k'],right['temperature_k']
    names=parameters['gas_order']
    enthalpy={name:(model.phases[name].standard(tl)['enthalpy_j_mol']
                   +model.phases[name].standard(tr)['enthalpy_j_mol'])/2 for name in names}
    mu_l,mu_r=left['chemical_potentials_j_mol'],right['chemical_potentials_j_mol']
    forces={name:mu_l[name]/tl-mu_r[name]/tr+enthalpy[name]*(1/tr-1/tl) for name in names}
    mobilities=parameters['gas_mobilities_mol2_k_j_s']
    flows={name:mobilities[name]*forces[name] for name in names}
    conduction=parameters['heat_conductance_w_k']*(tl-tr)
    energy=conduction+math.fsum(enthalpy[name]*flows[name] for name in names)
    inventories={key:math.fsum(parameters['inventory_per_gas_molecule'][name][index]*flows[name]
                for name in names) for index,key in enumerate(parameters['transferred_inventory_order'])}
    sl=(-energy+math.fsum(mu_l[name]*flows[name] for name in names))/tl
    sr=(energy-math.fsum(mu_r[name]*flows[name] for name in names))/tr
    production=parameters['heat_conductance_w_k']*(tl-tr)**2/(tl*tr)
    production+=math.fsum(mobilities[name]*forces[name]**2 for name in names)
    return {'gas_flows_mol_s':flows,'inventory_flows_mol_s':inventories,'energy_flow_w':energy,
            'conductive_heat_w':conduction,'face_enthalpies_j_mol':enthalpy,
            'forces_j_mol_k':forces,'left_entropy_rate_w_k':sl,'right_entropy_rate_w_k':sr,
            'entropy_production_w_k':production}


def exchange_jacobian(model,left,right,left_tangent,right_tangent,parameters):
    """Face derivative with respect to left/right (C,O,N2,U), same phases."""
    face=exchange(model,left,right,parameters);names=parameters['gas_order']
    tl,tr=left['temperature_k'],right['temperature_k'];jump=1/tr-1/tl
    dtl=np.concatenate((left_tangent['physical_from_conserved_derivative'][0],np.zeros(4)))
    dtr=np.concatenate((np.zeros(4),right_tangent['physical_from_conserved_derivative'][0]))
    dmu_l={k:np.concatenate((left_tangent['gas_chemical_potential_conserved_derivatives'][k],np.zeros(4))) for k in names}
    dmu_r={k:np.concatenate((np.zeros(4),right_tangent['gas_chemical_potential_conserved_derivatives'][k])) for k in names}
    dh={k:(model.phases[k].standard(tl)['cp_j_mol_k']*dtl+model.phases[k].standard(tr)['cp_j_mol_k']*dtr)/2 for k in names}
    djump=dtl/tl**2-dtr/tr**2
    dforce={k:dmu_l[k]/tl-dmu_r[k]/tr-left['chemical_potentials_j_mol'][k]/tl**2*dtl
              +right['chemical_potentials_j_mol'][k]/tr**2*dtr+dh[k]*jump+face['face_enthalpies_j_mol'][k]*djump for k in names}
    flow={k:parameters['gas_mobilities_mol2_k_j_s'][k]*dforce[k] for k in names}
    de=parameters['heat_conductance_w_k']*(dtl-dtr)
    de+=sum(dh[k]*face['gas_flows_mol_s'][k]+face['face_enthalpies_j_mol'][k]*flow[k] for k in names)
    inventory={key:sum(parameters['inventory_per_gas_molecule'][k][i]*flow[k] for k in names)
               for i,key in enumerate(parameters['transferred_inventory_order'])}
    ds_l=(-de+sum(dmu_l[k]*face['gas_flows_mol_s'][k]+left['chemical_potentials_j_mol'][k]*flow[k] for k in names))/tl
    ds_l-=face['left_entropy_rate_w_k']/tl*dtl
    ds_r=(de-sum(dmu_r[k]*face['gas_flows_mol_s'][k]+right['chemical_potentials_j_mol'][k]*flow[k] for k in names))/tr
    ds_r-=face['right_entropy_rate_w_k']/tr*dtr
    production=parameters['heat_conductance_w_k']*(dtl-dtr)*jump+face['conductive_heat_w']*djump
    production+=sum(2*parameters['gas_mobilities_mol2_k_j_s'][k]*face['forces_j_mol_k'][k]*dforce[k] for k in names)
    return {'gas':{k:v.tolist() for k,v in flow.items()},'inventory':{k:v.tolist() for k,v in inventory.items()},
            'energy':de.tolist(),'entropy_left':ds_l.tolist(),'entropy_right':ds_r.tolist(),
            'production':production.tolist(),
            'coordinate_order':['left_C','left_O','left_N2','left_U','right_C','right_O','right_N2','right_U'],
            'same_phase_only':True}
