"""Source quadrature and simultaneous log-mole equations, independent of decoder."""
from mpmath import mp


def source_thermal(model, temperature):
    t=mp.mpf(temperature);thermal={}
    for name,phase in model.phases.items():
        a,b,c,d,e=map(mp.mpf,phase.coefficients);t0=mp.mpf(phase.reference_temperature_k)
        def cp(value):return a+b*value+c/value**2+d/mp.sqrt(value)+e*value**2
        h=mp.mpf(phase.reference_enthalpy_j_mol)+mp.quad(cp,[t0,t])
        s=mp.mpf(phase.reference_entropy_j_mol_k)+mp.quad(lambda value:cp(value)/value,[t0,t])
        thermal[name]=(h,s,h-t*s)
    return thermal


def reconstruct(model, temperature, inventory, phase_name, initial_amounts, settings):
    t=mp.mpf(temperature);r=mp.mpf(model.r);thermal=source_thermal(model,t)
    ct,ot,nn=[mp.mpf(inventory[k]) for k in ['carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
    names=['CO','CO2','O2']
    def decode(*logarithms):
        gases=dict(zip(names,map(mp.exp,logarithms)));gases['N2']=nn;ng=mp.fsum(gases.values())
        mu={name:thermal[name][2]+r*t*mp.log(value/ng) for name,value in gases.items()};mu['C']=thermal['C'][2]
        return gases,mu
    def equations(*logarithms):
        gas,mu=decode(*logarithms);oxygen=(gas['CO']+2*gas['CO2']+2*gas['O2'])/ot-1
        if phase_name=='graphite_present':
            return ((mu['CO']-mu['C']-mu['O2']/2)/(r*t),(mu['CO2']-mu['C']-mu['O2'])/(r*t),oxygen)
        return ((gas['CO']+gas['CO2'])/ct-1,oxygen,(mu['CO2']-mu['CO']-mu['O2']/2)/(r*t))
    initial=tuple(mp.log(mp.mpf(initial_amounts[name])) for name in names)
    solution=mp.findroot(equations,initial,tol=mp.mpf(settings['root_tolerance']),maxsteps=settings['maximum_root_iterations'])
    gas,mu=decode(*solution);carbon=ct-gas['CO']-gas['CO2'] if phase_name=='graphite_present' else mp.mpf(0)
    amounts={'C':carbon,**gas};ng=mp.fsum(gas.values())
    enthalpy=mp.fsum(value*thermal[name][0] for name,value in amounts.items())
    entropy=carbon*thermal['C'][1]+mp.fsum(value*(thermal[name][1]-r*mp.log(value/ng)) for name,value in gas.items())
    return {'amounts':amounts,'enthalpy':enthalpy,'entropy':entropy,'mu':mu,'thermal':thermal,
        'equation_residual':max(abs(value) for value in equations(*solution))}


def caloric_capacity(model,temperature,inventory,phase_name,initial_amounts,settings):
    state=reconstruct(model,temperature,inventory,phase_name,initial_amounts,settings)
    t=mp.mpf(temperature);r=mp.mpf(model.r);n=state['amounts'];names=['CO','CO2','O2'];ng=mp.fsum(n[k] for k in ['CO','CO2','O2','N2'])
    entropy={name:hs[1] if name=='C' else hs[1]-r*mp.log(n[name]/ng) for name,hs in state['thermal'].items()}
    oxygen=mp.mpf(inventory['oxygen_atoms_mol']);carbon=mp.mpf(inventory['carbon_atoms_mol'])
    oxygen_row=[n['CO']/oxygen,2*n['CO2']/oxygen,2*n['O2']/oxygen]
    if phase_name=='graphite_present':
        first=[r*t*(int(name=='CO')-mp.mpf('.5')*int(name=='O2')-n[name]/(2*ng)) for name in names]
        second=[r*t*(int(name=='CO2')-int(name=='O2')) for name in names]
        matrix=mp.matrix([first,second,oxygen_row]);rhs=mp.matrix([entropy['CO']-entropy['C']-entropy['O2']/2,entropy['CO2']-entropy['C']-entropy['O2'],0])
    else:
        carbon_row=[n['CO']/carbon,n['CO2']/carbon,0]
        reaction=[r*t*(int(name=='CO2')-int(name=='CO')-mp.mpf('.5')*int(name=='O2')+n[name]/(2*ng)) for name in names]
        matrix=mp.matrix([carbon_row,oxygen_row,reaction]);rhs=mp.matrix([0,0,entropy['CO2']-entropy['CO']-entropy['O2']/2])
    logarithmic_derivatives=mp.lu_solve(matrix,rhs);dn={name:n[name]*v for name,v in zip(names,logarithmic_derivatives,strict=True)}
    dn['N2']=mp.mpf(0);dn['C']=-dn['CO']-dn['CO2'] if phase_name=='graphite_present' else mp.mpf(0)
    frozen=mp.mpf(0)
    for name,phase in model.phases.items():
        a,b,c,d,e=map(mp.mpf,phase.coefficients);frozen+=n[name]*(a+b*t+c/t**2+d/mp.sqrt(t)+e*t**2)
    state['cp']=frozen+mp.fsum(dn[name]*state['thermal'][name][0] for name in dn)
    return state
