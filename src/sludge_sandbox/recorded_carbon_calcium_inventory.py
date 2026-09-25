"""Positive-inventory Ca/C/O equilibrium with independently qualified calorics.

Domain: C>0, O>Ca and N2>0, fixed positive Ca; ideal gases and pure,
constant-volume solids retain the existing source and approximation boundaries.
Trace gas chemical-potential inventory Jacobians are not qualified here.
"""
import math

from scipy.optimize import brentq

from .recorded_carbon_calcium_pressure import RecordedCarbonCalciumPressure


def _inventory_equilibrium(model, temperature, pressure, inventory):
    t, p, rt, pi = temperature, pressure, model.r * temperature, pressure / model.p0
    ca, ct, ot, nn = [inventory[name] for name in
        ['calcium_atoms_mol', 'carbon_atoms_mol', 'oxygen_atoms_mol', 'nitrogen_molecules_mol']]
    thermal = {name: phase.standard(t) for name, phase in model.phases.items()}
    h = {name: value['enthalpy_j_mol'] for name, value in thermal.items()}
    g = {name: value['gibbs_j_mol'] for name, value in thermal.items()}
    for name, volume in model.volumes.items():
        h[name] += (p - model.p0) * volume
        g[name] += (p - model.p0) * volume
    ln_k1 = -(g['CO'] - g['C'] - g['O2'] / 2) / rt
    ln_k2 = -(g['CO2'] - g['C'] - g['O2']) / rt
    ln_k3 = ln_k2 - ln_k1
    k1, k2 = math.exp(ln_k1), math.exp(ln_k2)
    policy = model.parameters['equilibrium_numerics']

    def log_root(function, lower, upper):
        return math.exp(brentq(lambda value: function(math.exp(value)),
            math.log(lower), math.log(upper),
            xtol=policy['log_oxygen_absolute_tolerance'],
            rtol=policy['log_oxygen_relative_tolerance'],
            maxiter=policy['maximum_root_iterations']))

    def quantities(calcite, lime, carbon, gas, partial, calcium_phase, carbon_phase):
        n = {'calcite': calcite, 'lime': lime, 'C': carbon, **gas}
        mu = {name: g[name] + rt * math.log(value) for name, value in partial.items()}
        mu.update({name: g[name] for name in model.volumes})
        return n, partial, mu, calcium_phase, carbon_phase

    def fixed_calcium(calcite, calcium_phase):
        carbon, oxygen = ct - calcite, ot - ca - 2 * calcite
        c, o = carbon / nn, oxygen / nn
        a, b = (o + 2) * (k2 + 1), (o + 1) * k1
        q = 2 * o * pi / (b + math.sqrt(b*b + 4*a*o*pi))
        partial = {'CO': k1*q, 'CO2': k2*q*q, 'O2': q*q}
        partial['N2'] = (partial['CO'] + 2*partial['CO2'] + 2*partial['O2']) / o
        gas = {name: nn * value / partial['N2'] for name, value in partial.items()}
        gas['N2'] = nn
        required = math.fsum((gas['CO'], gas['CO2']))
        if carbon >= required:
            solid_carbon, carbon_phase = carbon - required, 'graphite_present'
        else:
            solid_carbon, carbon_phase = 0., 'graphite_exhausted'
            delta = o - c
            lower = min(math.log(delta/8), 2*math.log(delta) + math.log1p(c)
                        - math.log(16) - 2*math.log(c) - 2*ln_k3 - math.log(pi))
            upper = math.log(delta/2)

            def residual(log_z):
                z = math.exp(log_z)
                w = math.exp(ln_k3) * math.sqrt(pi*z/(1+c+z))
                return c*(1+w/(1+w)) + 2*z - o

            z = math.exp(brentq(residual, lower, upper,
                xtol=policy['log_oxygen_absolute_tolerance'],
                rtol=policy['log_oxygen_relative_tolerance'],
                maxiter=policy['maximum_root_iterations']))
            w = math.exp(ln_k3) * math.sqrt(pi*z/(1+c+z))
            gas = {'CO': carbon/(1+w), 'CO2': carbon*w/(1+w), 'O2': nn*z, 'N2': nn}
            ng = math.fsum(gas.values())
            partial = {name: pi*value/ng for name, value in gas.items()}
        return quantities(calcite, ca-calcite, solid_carbon, gas, partial, calcium_phase, carbon_phase)

    def affinity(state):
        mu = state[2]
        return mu['lime'] + mu['CO2'] - mu['calcite']

    def coexistence():
        b2 = math.exp((g['calcite'] - g['lime'] - g['CO2']) / rt)
        d = math.fsum((ot, -ca, -ct, -ct)) / nn
        partial = {'CO2': b2, 'O2': b2/k2}
        partial['CO'] = k1 * math.sqrt(partial['O2'])
        partial['N2'] = pi - math.fsum(partial.values())
        if partial['N2'] > 0:
            gas = {name: nn*value/partial['N2'] for name, value in partial.items()}
            gas['N2'] = nn
            carbon = (2*gas['O2'] - gas['CO'] - d*nn) / 2
            calcite = math.fsum((ot, -ca, -gas['CO'], -2*gas['CO2'], -2*gas['O2'])) / 2
            lime = math.fsum((ca, ca, ca, -ot, gas['CO'], 2*gas['CO2'], 2*gas['O2'])) / 2
            if carbon >= 0 and calcite >= 0 and lime >= 0:
                return quantities(calcite, lime, carbon, gas, partial, 'coexistence', 'graphite_present')
        # The graphite-free phase uses O - Ca - 2 C to remove the calcium
        # fraction entirely from the gas equation. Each root is monotone on
        # its physical branch. Log coordinates resolve trace partial pressures.
        b = math.exp(math.log(b2) - ln_k3)
        z0 = math.exp(2*(math.log(b) - math.log(2))/3)
        s = pi - b2
        if d > 0:
            oxygen = log_root(lambda z: (2+d)*z - d*s + (d-1)*b/math.sqrt(z), z0, s)
            monoxide = b / math.sqrt(oxygen)
        elif d < 0:
            monoxide = log_root(lambda w: (d-1)*w - d*s + (2+d)*(b/w)**2, 2*z0, s)
            oxygen = (b/monoxide)**2
        else:
            oxygen, monoxide = z0, 2*z0
        partial = {'CO': monoxide, 'CO2': b2, 'O2': oxygen}
        partial['N2'] = pi - math.fsum(partial.values())
        gas = {name: nn*value/partial['N2'] for name, value in partial.items()}
        gas['N2'] = nn
        calcite = math.fsum((ct, -gas['CO'], -gas['CO2']))
        lime = math.fsum((ca, -ct, gas['CO'], gas['CO2']))
        return quantities(calcite, lime, 0., gas, partial, 'coexistence', 'graphite_exhausted')

    state = fixed_calcium(0., 'lime')
    if affinity(state) > 0:
        if ct > ca and ot > 3*ca:
            state = fixed_calcium(ca, 'calcite')
            if affinity(state) < 0:
                state = coexistence()
        else:
            state = coexistence()
    n, partial, mu, calcium_phase, carbon_phase = state
    gas_names = ['CO', 'CO2', 'O2', 'N2']
    ng = math.fsum(n[name] for name in gas_names)
    solid_volume = math.fsum(n[name]*volume for name, volume in model.volumes.items())
    gas_volume = ng*rt/p
    volume = gas_volume + solid_volume
    enthalpy = math.fsum(n[name]*h[name] for name in n)
    entropy = math.fsum(n[name]*thermal[name]['entropy_j_mol_k'] for name in n)
    entropy -= model.r * math.fsum(n[name]*math.log(partial[name]) for name in gas_names)
    state = {'temperature_k': t, 'pressure_pa': p, 'calcium_phase': calcium_phase,
        'carbon_phase': carbon_phase, 'calcite_fraction': n['calcite']/ca, 'amounts_mol': n,
        'partial_pressures_pa': {name: model.p0*value for name, value in partial.items()},
        'chemical_potentials_j_mol': mu, 'calcination_gibbs_j_mol': affinity(state),
        'enthalpy_j': enthalpy, 'entropy_j_k': entropy, 'gibbs_j': enthalpy-t*entropy,
        'internal_energy_j': enthalpy-p*volume, 'helmholtz_j': enthalpy-p*volume-t*entropy,
        'gas_volume_m3': gas_volume, 'solid_volume_m3': solid_volume, 'total_volume_m3': volume}
    return state, thermal, h


class RecordedCarbonCalciumInventory(RecordedCarbonCalciumPressure):
    def _equilibrium_at_pressure(self, temperature_k, pressure_pa,
                                calcium_atoms_mol, carbon_atoms_mol,
                                oxygen_atoms_mol, nitrogen_molecules_mol):
        inventory = {'calcium_atoms_mol': calcium_atoms_mol,
            'carbon_atoms_mol': carbon_atoms_mol, 'oxygen_atoms_mol': oxygen_atoms_mol,
            'nitrogen_molecules_mol': nitrogen_molecules_mol}
        return _inventory_equilibrium(self, temperature_k, pressure_pa, inventory)
