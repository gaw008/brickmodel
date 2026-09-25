"""Rigid ideal CO2/N2 inventory with source formation energy and mixing entropy."""
import math

from scipy.optimize import brentq


class RecordedIdealGasCell:
    def __init__(self, phases, gas_constant, standard_pressure, volume, inverse_policy):
        self.phases = phases
        self.r = gas_constant
        self.p0 = standard_pressure
        self.volume = volume
        self.inverse_policy = inverse_policy

    def at_temperature(self, carbon, nitrogen, temperature):
        r,t = self.r,temperature
        quantities = {}; energies = []; entropies = []
        for name,potential,amount in [('co2','carbon',carbon),('nitrogen','nitrogen',nitrogen)]:
            thermal = self.phases[name].standard(t)
            partial = amount*r*t/self.volume
            entropy = thermal['entropy_j_mol_k']-r*math.log(partial/self.p0)
            chemical = thermal['enthalpy_j_mol']-t*entropy
            energies.append(amount*(thermal['enthalpy_j_mol']-r*t));entropies.append(amount*entropy)
            quantities.update({name+'_mol':amount,name+'_partial_pressure_pa':partial,
                name+'_partial_enthalpy_j_mol':thermal['enthalpy_j_mol'],
                potential+'_chemical_potential_j_mol':chemical})
        return {**quantities,'temperature_k':t,'pressure_pa':(carbon+nitrogen)*r*t/self.volume,
            'internal_energy_j':math.fsum(energies),'entropy_j_k':math.fsum(entropies)}

    def inventory_state(self, carbon, nitrogen, energy):
        policy = self.inverse_policy
        residual = lambda t:self.at_temperature(carbon,nitrogen,t)['internal_energy_j']-energy
        t = brentq(residual,*policy['temperature_bracket_k'],xtol=policy['temperature_absolute_k'],
            rtol=policy['temperature_relative'],maxiter=policy['temperature_iterations'])
        state = self.at_temperature(carbon,nitrogen,t)
        state['energy_inverse_residual_j'] = state['internal_energy_j']-energy
        state['internal_energy_j'] = energy
        return state
