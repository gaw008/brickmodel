"""Restricted water-gas-shift equilibrium inside a closed viscous pore.

CO+H2O <=> CO2+H2 conserves total gas moles and its ideal equilibrium
composition is independent of volume. This restriction permits using the
equilibrium Cv in the existing caloric balance. No kinetic rate is supplied.
"""
import math

from .thermal_spherical_pore import pore_caloric_balance
from .viscous_spherical_pore import spherical_pore_mechanics


class EquilibriumSphericalPore:
    def __init__(self, parameters, gas_equilibrium, feed_fractions):
        self.p = parameters
        self.equilibrium = gas_equilibrium
        self.r = parameters['gas_constant_j_mol_k']
        self.feed_fractions = feed_fractions

    def at_state(self, radius, temperature, gas_amount, bath_temperature, conductance):
        p = self.p; volume = 4*math.pi*radius**3/3
        initial_amounts = {name:gas_amount*fraction for name,fraction in self.feed_fractions.items()}
        gas = self.equilibrium.at_temperature(temperature, volume, initial_amounts)
        mechanical = spherical_pore_mechanics(radius, gas['pressure_pa'],
            matrix_volume=p['matrix_volume_m3'], viscosity=p['viscosity_pa_s'],
            surface_tension=p['surface_tension_n_m'], outside_pressure=p['outside_pressure_pa'])
        thermal = pore_caloric_balance(mechanical, p, temperature, bath_temperature, conductance,
            gas['internal_energy_j'], gas['entropy_j_k'], gas['equilibrium_cv_j_k'])
        return {**thermal, 'gas_equilibrium': gas,
                'gas_reference_amounts_mol': initial_amounts,
                'gas_amount_mol': math.fsum(gas['amounts_mol'].values()),
                'gas_amounts_mol': gas['amounts_mol'],
                'reaction_extent_mol': gas['extent_mol'],
                'reaction_gibbs_j_mol': gas['reaction_gibbs_j_mol'],
                'reaction_extent_rate_mol_s': gas['extent_temperature_derivative_mol_k']*thermal['temperature_rate_k_s']}
