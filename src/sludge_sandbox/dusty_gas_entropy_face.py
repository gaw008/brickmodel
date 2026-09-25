"""A declared entropy-variable path approximation for isothermal Dusty Gas.

The log partial concentrations follow a straight path. Pressure and composition
therefore vary together along that numerical path; it is not a solved steady
pore profile, even when both endpoint pressures happen to be equal.
"""
import numpy as np
from numpy.polynomial.legendre import leggauss

from .dusty_gas_isothermal import effective_knudsen_diffusivities, isothermal_dusty_gas_fluxes
from .wilke_gas_mixture import wilke_viscosity_pa_s


class DustyGasEntropyFace:
    def __init__(self, temperature_k, gas_constant_j_mol_k, molar_masses_kg_mol,
            pure_viscosities_pa_s, diffusivity_pressure_products_pa_m2_s,
            pore_parameters, distance_m, quadrature_order):
        self.temperature, self.gas_constant = temperature_k, gas_constant_j_mol_k
        self.masses = np.asarray(molar_masses_kg_mol)
        self.viscosities = np.asarray(pure_viscosities_pa_s)
        self.diffusion_pressure = np.asarray(diffusivity_pressure_products_pa_m2_s)
        self.pore, self.distance = pore_parameters, distance_m
        self.knudsen = effective_knudsen_diffusivities(temperature_k, gas_constant_j_mol_k,
            self.masses, pore_parameters['mean_pore_radius_m'], pore_parameters['porosity'], pore_parameters['tortuosity'])
        nodes, weights = leggauss(quadrature_order)
        self.nodes, self.weights = (nodes+1)/2, weights/2

    def mixture_viscosity(self, fractions):
        return wilke_viscosity_pa_s(fractions, self.viscosities, self.masses)['viscosity_pa_s']

    def evaluate(self, left_partial_concentrations_mol_m3, right_partial_concentrations_mol_m3):
        left_log = np.log(left_partial_concentrations_mol_m3)
        jump = np.log(right_partial_concentrations_mol_m3)-left_log
        flux, diffusive, darcy = np.zeros_like(jump), np.zeros_like(jump), np.zeros_like(jump)
        entropy = np.zeros(3)
        for node, weight in zip(self.nodes, self.weights, strict=True):
            concentrations = np.exp(left_log+node*jump)
            total = np.sum(concentrations)
            fractions = concentrations/total
            pressure = total*self.gas_constant*self.temperature
            effective = self.diffusion_pressure/pressure*self.pore['porosity']/self.pore['tortuosity']
            viscosity = self.mixture_viscosity(fractions)
            local = isothermal_dusty_gas_fluxes(fractions, jump/self.distance,
                self.temperature, pressure, self.gas_constant, effective, self.knudsen,
                viscosity, self.pore['permeability_m2'])
            flux += weight*local['molar_fluxes_mol_m2_s']
            diffusive += weight*local['diffusive_fluxes_mol_m2_s']
            darcy += weight*local['darcy_fluxes_mol_m2_s']
            entropy += weight*self.distance*np.array([local['entropy_molecular_w_m3_k'],
                local['entropy_wall_w_m3_k'], local['entropy_darcy_w_m3_k']])
        return {'molar_fluxes_mol_m2_s': flux, 'diffusive_fluxes_mol_m2_s': diffusive,
            'darcy_fluxes_mol_m2_s': darcy,
            'entropy_from_jump_w_m2_k': float(-self.gas_constant*np.dot(flux, jump)),
            'entropy_from_path_w_m2_k': float(np.sum(entropy)),
            'entropy_molecular_w_m2_k': float(entropy[0]), 'entropy_wall_w_m2_k': float(entropy[1]),
            'entropy_darcy_w_m2_k': float(entropy[2])}
