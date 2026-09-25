"""An entropy-variable path discretization of isothermal/isobaric MS diffusion.

This is a declared finite-face approximation to the local law, not an exact
steady diffusion profile. One returned molar-frame flux is shared by both cells.
"""
import numpy as np
from numpy.polynomial.legendre import leggauss

from .maxwell_stefan_isothermal import local_fluxes


class IsothermalMaxwellStefanFace:
    def __init__(self, binary_diffusivities_m2_s, concentration_mol_m3,
                 molar_masses_kg_mol, gas_constant_j_mol_k, distance_m,
                 quadrature_order):
        self.diffusivities = np.asarray(binary_diffusivities_m2_s)
        self.concentration = concentration_mol_m3
        self.masses = np.asarray(molar_masses_kg_mol)
        self.gas_constant = gas_constant_j_mol_k
        self.distance = distance_m
        nodes, weights = leggauss(quadrature_order)
        self.nodes, self.weights = (nodes+1)/2, weights/2

    def evaluate(self, left_fractions, right_fractions):
        left_log, right_log = np.log(left_fractions), np.log(right_fractions)
        difference = right_log-left_log
        flux = np.zeros_like(left_log)
        integrated_production = 0.0
        for node, weight in zip(self.nodes, self.weights, strict=True):
            geometric = np.exp(left_log+node*difference)
            fractions = geometric/sum(geometric)
            gradient = fractions*(difference-np.dot(fractions, difference))/self.distance
            local = local_fluxes(fractions, gradient, self.diffusivities,
                self.concentration, self.masses, self.gas_constant)
            flux += weight*local['molar_frame_fluxes_mol_m2_s']
            integrated_production += weight*local['entropy_friction_w_m3_k']*self.distance
        return {'molar_fluxes_mol_m2_s': flux,
                'entropy_from_jump_w_m2_k': -self.gas_constant*np.dot(flux, difference),
                'entropy_from_path_w_m2_k': integrated_production}
