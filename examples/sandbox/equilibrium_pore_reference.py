"""Independent source extent bisection inside the thermal pore reference."""
from copy import deepcopy
from functools import lru_cache

import mpmath as mp

from review_restricted_water_gas_shift import Reference
from thermal_pore_reference import ThermalPoreReference


class EquilibriumPoreReference(ThermalPoreReference):
    def __init__(self, settings, sources, amounts):
        self.p = {key:mp.mpf(str(value)) for key,value in settings['model'].items()}
        self.initial = {key:mp.mpf(value) for key,value in amounts.items()}
        self.n = mp.fsum(self.initial.values()); self.r = self.p['gas_constant_j_mol_k']
        self.t0 = self.p['reference_temperature_k']
        self.capacity = self.p['matrix_volume_m3']*self.p['matrix_volumetric_cv_j_m3_k']
        eq = deepcopy(sources['equilibrium_parameters']); policy = settings['independent_reference']
        eq['independent_reference']['root_tolerance'] = policy['gas_extent_tolerance']
        eq['independent_reference']['root_maximum_iterations'] = policy['gas_extent_iterations']
        source = {name:data for item in sources['thermal_sources'] for name,data in item['phases'].items() if name in eq['species']}
        self.gas = Reference(eq,source); self.nu = eq['stoichiometry']
        self.gas_at_temperature = lru_cache(maxsize=policy['gas_cache_entries'])(self._gas_at_temperature)

    def _gas_at_temperature(self, t):
        # Unit volume only selects the entropy reference here. Equilibrium
        # composition is volume-independent because the reaction has Delta-nu=0.
        state = self.gas.equilibrium(t,mp.mpf(1),self.initial)
        thermal = {name:self.gas.thermal(name,t) for name in self.initial}
        cp = {}
        for name,data in self.gas.source.items():
            a,b,c,d,e = map(mp.mpf,data['cp_coefficient_strings'])
            cp[name] = a+b*t+c/t**2+d/mp.sqrt(t)+e*t*t
        dh = mp.fsum(self.nu[name]*thermal[name][0] for name in self.initial)
        dg = mp.fsum(self.nu[name]*(thermal[name][0]-t*thermal[name][1]) for name in self.initial)
        k = mp.exp(-dg/(self.r*t)); x = state['extent_mol']
        a,b,c,d = [self.initial[name] for name in ['CO','H2O','CO2','H2']]
        # Differentiate the polynomial reaction quotient directly.
        dxdt = k*dh/(self.r*t*t)*(a-x)*(b-x)/(c+d+2*x+k*(a+b-2*x))
        frozen = mp.fsum(amount*(cp[name]-self.r) for name,amount in state['amounts_mol'].items())
        return {**state,'equilibrium_cv_j_k':frozen+dh*dxdt,'extent_temperature_derivative_mol_k':dxdt}

    def cp(self,t):
        return self.gas_at_temperature(t)['equilibrium_cv_j_k']/self.n+self.r

    def energy_entropy(self,a,t):
        gas = self.gas_at_temperature(t); v = 4*mp.pi*a**3/3
        energy = gas['internal_energy_j']+self.capacity*(t-self.t0)+4*mp.pi*self.p['surface_tension_n_m']*a*a
        entropy = gas['entropy_j_k']+self.n*self.r*mp.log(v)+self.capacity*mp.log(t/self.t0)
        return energy,entropy

    def at_state(self,a,t,bath,conductance):
        state = super().at_state(a,t,bath,conductance)
        gas = self.gas_at_temperature(t)
        return {**state,'gas_amounts_mol':gas['amounts_mol'],
                'reaction_extent_mol':gas['extent_mol'],
                'reaction_gibbs_j_mol':gas['reaction_gibbs_j_mol'],
                'gas_equilibrium_cv_j_k':gas['equilibrium_cv_j_k']}
