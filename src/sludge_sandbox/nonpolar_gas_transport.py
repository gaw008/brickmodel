"""Direct dilute-gas collision formulas, with source inputs supplied by the caller.

Selected scope: CO/CO2/O2/N2, 300--1200 K, zero-dipole LJ approximation.
These are free-gas properties, not porous-medium or multicomponent flux laws.
Collision tables/formulas are derived from Cantera v3.2.0 (BSD-3-Clause);
the preserved source and license are in research/gas-transport-source-v1/source.
"""
from bisect import bisect_right
import math


class NonpolarGasTransport:
    def __init__(self, parameters):
        constants = parameters['constants']
        self.kb = float(constants['boltzmann_j_k'])
        self.avogadro = float(constants['avogadro_mol_inverse'])
        self.species = {
            name: {
                'mass_kg': float(item['molar_mass_g_mol'])
                    * float(constants['gram_kg']) / self.avogadro,
                'sigma_m': float(item['diameter_angstrom']) * float(constants['angstrom_m']),
                'epsilon_over_kb_k': float(item['well_depth_over_kb_k']),
            }
            for name, item in parameters['species'].items()
        }
        table = parameters['collision_tables']
        self.reduced_temperatures = [float(v) for v in table['reduced_temperature']]
        self.log_temperatures = [math.log(v) for v in self.reduced_temperatures]
        self.omega22_values = [float(v) for v in table['omega22_delta_zero']]
        self.astar_values = [float(v) for v in table['astar_delta_zero']]

    def _interpolate(self, reduced_temperature, values):
        # All selected states lie well inside the source table: no extrapolation
        # or endpoint clamping is part of the admitted calculation.
        start = bisect_right(self.reduced_temperatures, reduced_temperature) - 1
        x0, x1, x2 = self.log_temperatures[start:start+3]
        y0, y1, y2 = values[start:start+3]
        x = math.log(reduced_temperature)
        slope = (y1-y0)/(x1-x0)
        curvature = ((y2-y1)/(x2-x1)-slope)/(x2-x0)
        return y0 + (x-x0)*(slope + (x-x1)*curvature)

    def collision_integrals(self, temperature_k, left, right):
        a, b = self.species[left], self.species[right]
        reduced = temperature_k / math.sqrt(a['epsilon_over_kb_k']*b['epsilon_over_kb_k'])
        omega22 = self._interpolate(reduced, self.omega22_values)
        astar = self._interpolate(reduced, self.astar_values)
        return omega22, omega22/astar

    def viscosity_pa_s(self, temperature_k, species):
        item = self.species[species]
        omega22, _ = self.collision_integrals(temperature_k, species, species)
        return (5/16 * math.sqrt(item['mass_kg']*self.kb*temperature_k/math.pi)
                / (item['sigma_m']**2*omega22))

    def binary_diffusivity_m2_s(self, temperature_k, pressure_pa, left, right):
        a, b = self.species[left], self.species[right]
        sigma = (a['sigma_m']+b['sigma_m'])/2
        reduced_mass = a['mass_kg']*b['mass_kg']/(a['mass_kg']+b['mass_kg'])
        _, omega11 = self.collision_integrals(temperature_k, left, right)
        return (3/16 * math.sqrt(2*math.pi/reduced_mass)
                * (self.kb*temperature_k)**1.5
                / (math.pi*sigma**2*omega11*pressure_pa))
