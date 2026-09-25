"""Ideal gas CO + H2O <=> CO2 + H2 equilibrium, with inert gas inventory.

Only this reaction is admitted. No kinetic rate or complete C/H/O phase
equilibrium is inferred. All species in the declared states are positive.
"""
import math

from scipy.optimize import brentq

from .recorded_gas_reactions import standard_reaction


class RestrictedWaterGasShift:
    def __init__(self, phases, stoichiometry, gas_constant, standard_pressure):
        self.phases = phases
        self.nu = stoichiometry
        self.r = gas_constant
        self.p0 = standard_pressure

    def at_extent(self, temperature, volume, initial_amounts, extent):
        t, r = temperature, self.r
        amounts = {name: amount + self.nu[name] * extent
                   for name, amount in initial_amounts.items()}
        thermal = {name: self.phases[name].standard(t) for name in amounts}
        partials = {name: amount * r * t / volume for name, amount in amounts.items()}
        entropy = {name: thermal[name]['entropy_j_mol_k'] - r * math.log(partial / self.p0)
                   for name, partial in partials.items()}
        chemical = {name: thermal[name]['enthalpy_j_mol'] - t * entropy[name]
                    for name in amounts}
        energy = math.fsum(amount * (thermal[name]['enthalpy_j_mol'] - r * t)
                          for name, amount in amounts.items())
        total_entropy = math.fsum(amount * entropy[name] for name, amount in amounts.items())
        frozen_cv = math.fsum(amount * (thermal[name]['cp_j_mol_k'] - r)
                             for name, amount in amounts.items())
        reaction_gibbs = math.fsum(self.nu[name] * chemical[name] for name in amounts)
        curvature = math.fsum(self.nu[name]**2 / amount for name, amount in amounts.items())
        return {'temperature_k': t, 'volume_m3': volume, 'extent_mol': extent,
                'amounts_mol': amounts, 'partial_pressures_pa': partials,
                'pressure_pa': math.fsum(partials.values()),
                'chemical_potentials_j_mol': chemical, 'internal_energy_j': energy,
                'entropy_j_k': total_entropy, 'helmholtz_j': energy - t * total_entropy,
                'frozen_cv_j_k': frozen_cv, 'reaction_gibbs_j_mol': reaction_gibbs,
                'helmholtz_extent_curvature_j_mol2': r * t * curvature}

    def at_temperature(self, temperature, volume, initial_amounts):
        reaction = standard_reaction(self.phases, self.nu, temperature, self.r)
        k = math.exp(reaction['log_equilibrium'])
        a, b = initial_amounts['CO'], initial_amounts['H2O']
        c, d = initial_amounts['CO2'], initial_amounts['H2']
        quadratic = 1 - k
        linear = c + d + k * (a + b)
        constant = c * d - k * a * b
        extent = -2 * constant / (linear + math.sqrt(linear**2 - 4 * quadratic * constant))
        state = self.at_extent(temperature, volume, initial_amounts, extent)
        curvature = state['helmholtz_extent_curvature_j_mol2'] / (self.r * temperature)
        extent_derivative = reaction['vant_hoff_derivative_per_k'] / curvature
        return {**state, 'standard_reaction': reaction,
                'extent_temperature_derivative_mol_k': extent_derivative,
                'equilibrium_cv_j_k': state['frozen_cv_j_k']
                    + reaction['enthalpy_j_mol'] * extent_derivative}

    def at_energy(self, energy, volume, initial_amounts, numerics):
        residual = lambda t: self.at_temperature(t, volume, initial_amounts)['internal_energy_j'] - energy
        temperature = brentq(residual, *numerics['temperature_bracket_k'],
                             xtol=numerics['temperature_absolute_k'],
                             rtol=numerics['temperature_relative'],
                             maxiter=numerics['temperature_iterations'])
        state = self.at_temperature(temperature, volume, initial_amounts)
        return {**state, 'specified_internal_energy_j': energy,
                'energy_inverse_residual_j': state['internal_energy_j'] - energy}
