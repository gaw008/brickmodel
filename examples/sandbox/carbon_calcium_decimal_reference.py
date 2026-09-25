"""Simultaneous phase-constrained elemental/chemical-potential reference."""
from mpmath import mp

from carbon_gas_decimal_reference import source_thermal


def reconstruct(model,temperature,inventory,candidate,settings):
    t=mp.mpf(temperature);r=mp.mpf(model.r);thermal=source_thermal(model,t)
    ca,ct,ot,nn=[mp.mpf(inventory[name]) for name in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
    calcium_phase=candidate['calcium_phase'];carbon_phase=candidate['carbon_phase'];names=['CO','CO2','O2']
    def decode(*coordinates):
        gas=dict(zip(names,map(mp.exp,coordinates[:3])));gas['N2']=nn;ng=mp.fsum(gas.values())
        a=ca*coordinates[3] if calcium_phase=='coexistence' else (ca if calcium_phase=='calcite' else mp.mpf(0))
        carbon=ct-a-gas['CO']-gas['CO2'] if carbon_phase=='graphite_present' else mp.mpf(0)
        mu={name:thermal[name][2]+r*t*mp.log(value/ng) for name,value in gas.items()}
        mu.update({name:thermal[name][2] for name in ['C','calcite','lime']})
        return {'calcite':a,'lime':ca-a,'C':carbon,**gas},mu
    def equations(*coordinates):
        n,mu=decode(*coordinates);oxygen=(3*n['calcite']+n['lime']+n['CO']+2*n['CO2']+2*n['O2'])/ot-1
        if carbon_phase=='graphite_present':
            result=[(mu['CO']-mu['C']-mu['O2']/2)/(r*t),(mu['CO2']-mu['C']-mu['O2'])/(r*t),oxygen]
        else:
            result=[(n['calcite']+n['CO']+n['CO2'])/ct-1,oxygen,(mu['CO2']-mu['CO']-mu['O2']/2)/(r*t)]
        if calcium_phase=='coexistence':result.append((mu['lime']+mu['CO2']-mu['calcite'])/(r*t))
        return tuple(result)
    initial=[mp.log(mp.mpf(candidate['amounts_mol'][name])) for name in names]
    if calcium_phase=='coexistence':initial.append(mp.mpf(candidate['calcite_fraction']))
    solution=mp.findroot(equations,tuple(initial),tol=mp.mpf(settings['root_tolerance']),maxsteps=settings['maximum_root_iterations'])
    amounts,mu=decode(*solution);gas={name:amounts[name] for name in ['CO','CO2','O2','N2']};ng=mp.fsum(gas.values())
    h=mp.fsum(n*thermal[name][0] for name,n in amounts.items())
    s=mp.fsum(amounts[name]*thermal[name][1] for name in ['calcite','lime','C'])+mp.fsum(n*(thermal[name][1]-r*mp.log(n/ng)) for name,n in gas.items())
    return {'amounts':amounts,'mu':mu,'enthalpy':h,'entropy':s,'thermal':thermal,
        'equation_residual':max(abs(value) for value in equations(*solution))}
