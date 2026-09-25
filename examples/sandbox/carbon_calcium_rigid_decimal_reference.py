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
            'internal_energy':h-p*v,'helmholtz':h-p*v-t*s,
            'equation_residual':max(abs(v) for v in equations(*solution))}
