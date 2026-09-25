"""Virtual dissipative heat/gas exchange between restricted equilibrium cells."""
import math


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
