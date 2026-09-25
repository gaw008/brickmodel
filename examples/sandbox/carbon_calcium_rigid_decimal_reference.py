"""Independent simultaneous log-pressure, log-gas and phase-fraction flash."""
from mpmath import mp

from carbon_gas_decimal_reference import source_thermal


def reconstruct(model, temperature, volume, inventory, candidate, settings):
    t, total_v, r, p0 = map(mp.mpf, (temperature, volume, model.r, model.p0))
    thermal = source_thermal(model, t)
    volumes = {name: mp.mpf(value) for name, value in model.volumes.items()}
    ca, ct, ot, nn = [mp.mpf(inventory[name]) for name in
        ['calcium_atoms_mol', 'carbon_atoms_mol', 'oxygen_atoms_mol', 'nitrogen_molecules_mol']]
    calcium_phase, carbon_phase = candidate['calcium_phase'], candidate['carbon_phase']
    names = ['CO', 'CO2', 'O2']

    def decode(*coordinates):
        gas = dict(zip(names, map(mp.exp, coordinates[:3]), strict=True))
        gas['N2'] = nn
        p = mp.exp(coordinates[-1])
        ng = mp.fsum(gas.values())
        a = ca * coordinates[3] if calcium_phase == 'coexistence' else (
            ca if calcium_phase == 'calcite' else mp.mpf(0))
        carbon = ct - a - gas['CO'] - gas['CO2'] if carbon_phase == 'graphite_present' else mp.mpf(0)
        amounts = {'calcite': a, 'lime': ca - a, 'C': carbon, **gas}
        mu = {name: thermal[name][2] + r*t*mp.log(p/p0*value/ng) for name,value in gas.items()}
        mu.update({name: thermal[name][2] + (p-p0)*v for name,v in volumes.items()})
        v = mp.fsum(amounts[name]*v for name,v in volumes.items()) + ng*r*t/p
        return amounts, mu, p, v

    def equations(*coordinates):
        n, mu, _, v = decode(*coordinates)
        oxygen = (3*n['calcite']+n['lime']+n['CO']+2*n['CO2']+2*n['O2'])/ot-1
        if carbon_phase == 'graphite_present':
            result = [(mu['CO']-mu['C']-mu['O2']/2)/(r*t),
                      (mu['CO2']-mu['C']-mu['O2'])/(r*t), oxygen]
        else:
            result = [(n['calcite']+n['CO']+n['CO2'])/ct-1, oxygen,
                      (mu['CO2']-mu['CO']-mu['O2']/2)/(r*t)]
        if calcium_phase == 'coexistence':
            result.append((mu['lime']+mu['CO2']-mu['calcite'])/(r*t))
        result.append(v/total_v-1)
        return tuple(result)

    initial = [mp.log(mp.mpf(candidate['amounts_mol'][name])) for name in names]
    if calcium_phase == 'coexistence':
        initial.append(mp.mpf(candidate['calcite_fraction']))
    initial.append(mp.log(mp.mpf(candidate['pressure_pa'])))
    solution = mp.findroot(equations,tuple(initial),tol=mp.mpf(settings['root_tolerance']),
                           maxsteps=settings['maximum_root_iterations'])
    n, mu, p, v = decode(*solution)
    gas = {name:n[name] for name in ['CO','CO2','O2','N2']}
    ng = mp.fsum(gas.values())
    h = mp.fsum(value*thermal[name][0] for name,value in n.items())
    h += (p-p0)*mp.fsum(n[name]*v for name,v in volumes.items())
    s = mp.fsum(value*thermal[name][1] for name,value in n.items())
    s -= r*mp.fsum(value*mp.log(p/p0*value/ng) for value in gas.values())
    return {'amounts':n,'mu':mu,'pressure':p,'volume':v,'enthalpy':h,'entropy':s,
            'internal_energy':h-p*v,'helmholtz':h-p*v-t*s,'thermal':thermal,
            'equation_residual':max(abs(v) for v in equations(*solution))}


def caloric_capacity(model, temperature, volume, inventory, candidate, settings):
    """Differentiate independent log-pressure/mole/volume constraints at fixed V."""
    state=reconstruct(model,temperature,volume,inventory,candidate,settings)
    t,r,p,p0=map(mp.mpf,(temperature,model.r,state['pressure'],model.p0))
    n=state['amounts'];thermal=state['thermal'];names=['CO','CO2','O2']
    gas_names=['CO','CO2','O2','N2'];ng=mp.fsum(n[k] for k in gas_names)
    volumes={name:mp.mpf(v) for name,v in model.volumes.items()}
    entropy={name:hs[1] if name in volumes else hs[1]-r*mp.log(p/p0*n[name]/ng)
             for name,hs in thermal.items()}
    ca,carbon,oxygen=[mp.mpf(inventory[k]) for k in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol']]
    coexist=candidate['calcium_phase']=='coexistence';present=candidate['carbon_phase']=='graphite_present'
    oxygen_row=[n['CO']/oxygen,2*n['CO2']/oxygen,2*n['O2']/oxygen]+([2*ca/oxygen] if coexist else [])+[0]
    if present:
        first=[r*t*(int(name=='CO')-mp.mpf('.5')*int(name=='O2')-n[name]/(2*ng)) for name in names]+([0] if coexist else [])+[r*t/2-p*volumes['C']]
        second=[r*t*(int(name=='CO2')-int(name=='O2')) for name in names]+([0] if coexist else [])+[-p*volumes['C']]
        matrix=[first,second,oxygen_row]
        rhs=[entropy['CO']-entropy['C']-entropy['O2']/2,entropy['CO2']-entropy['C']-entropy['O2'],0]
    else:
        carbon_row=[n['CO']/carbon,n['CO2']/carbon,0]+([ca/carbon] if coexist else [])+[0]
        reaction=[r*t*(int(name=='CO2')-int(name=='CO')-mp.mpf('.5')*int(name=='O2')+n[name]/(2*ng)) for name in names]+([0] if coexist else [])+[-r*t/2]
        matrix=[carbon_row,oxygen_row,reaction]
        rhs=[0,0,entropy['CO2']-entropy['CO']-entropy['O2']/2]
    if coexist:
        matrix.append([r*t*(int(name=='CO2')-n[name]/ng) for name in names]+[0,r*t+p*(volumes['lime']-volumes['calcite'])])
        rhs.append(entropy['lime']+entropy['CO2']-entropy['calcite'])
    volume_row=[n[name]*(r*t/p-(volumes['C'] if present and name in ['CO','CO2'] else 0)) for name in names]
    if coexist:volume_row.append(ca*(volumes['calcite']-volumes['lime']-(volumes['C'] if present else 0)))
    volume_row.append(-ng*r*t/p)
    matrix.append([v/mp.mpf(volume) for v in volume_row]);rhs.append(-ng*r/p/mp.mpf(volume))
    rates=mp.lu_solve(mp.matrix(matrix),mp.matrix(rhs))
    dn={name:n[name]*rates[i] for i,name in enumerate(names)}
    dn['N2']=mp.mpf(0);dn['calcite']=ca*rates[3] if coexist else mp.mpf(0);dn['lime']=-dn['calcite']
    dn['C']=-dn['calcite']-dn['CO']-dn['CO2'] if present else mp.mpf(0)
    frozen=-ng*r
    for name,phase in model.phases.items():
        a,b,c,d,e=map(mp.mpf,phase.coefficients)
        frozen+=n[name]*(a+b*t+c/t**2+d/mp.sqrt(t)+e*t**2)
    internal={name:hs[0]-(p0*volumes[name] if name in volumes else r*t) for name,hs in thermal.items()}
    state['cv']=frozen+mp.fsum(dn[name]*internal[name] for name in dn)
    state['amount_temperature_derivatives']=dn
    state['pressure_temperature_derivative']=p*rates[len(rates)-1]
    return state
