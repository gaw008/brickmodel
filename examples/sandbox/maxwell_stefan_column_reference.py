"""Independent reduced molar-flux equations for isothermal column reviews.

Production solves a bordered symmetric velocity-friction matrix. This review
eliminates the last molar flux in the original nonsymmetric MS equations.
Only stored previously source-qualified D, c, R and mesh inputs are shared.
"""
import numpy as np
from numpy.polynomial.legendre import leggauss


class ColumnReference:
    def __init__(self, header):
        self.settings = header['settings']
        self.count = header['cell_count']
        self.diffusion = np.asarray(header['binary_diffusivity_m2_s'])
        self.species_count = len(self.diffusion)
        self.concentration = header['concentration_mol_m3']
        self.gas_constant = header['gas_constant_j_mol_k']
        self.area = self.settings['geometry']['area_m2']
        self.width = self.settings['geometry']['length_m']/self.count
        self.volume = self.area*self.width
        nodes, weights = leggauss(self.settings['verification']['reference_face_quadrature_order'])
        self.nodes, self.weights = (nodes+1)/2, weights/2

    def evaluate(self, values):
        species = self.species_count
        first = np.asarray(values).reshape(self.count, species-1)
        fractions = np.column_stack((first, 1-np.sum(first, axis=1)))
        inventories = self.concentration*self.volume*fractions
        entropy = -self.gas_constant*np.sum(inventories*np.log(fractions), axis=1)
        jump = np.diff(np.log(fractions), axis=0)
        geometric = np.exp(np.log(fractions[:-1])[:, None, :]+self.nodes[None, :, None]*jump[:, None, :])
        x = geometric/np.sum(geometric, axis=2, keepdims=True)
        gradient = x*(jump[:, None, :]-np.sum(x*jump[:, None, :], axis=2, keepdims=True))/self.width
        matrix = np.zeros((*x.shape[:2], species-1, species-1))
        for i in range(species-1):
            for j in range(species-1):
                coefficient = (sum(x[:, :, k]/self.diffusion[i, k] for k in range(species) if k != i)
                    if i == j else -x[:, :, i]/self.diffusion[i, j])
                matrix[:, :, i, j] = coefficient+x[:, :, i]/self.diffusion[i, -1]
        solved = np.linalg.solve(matrix, -self.concentration*gradient[:, :, :-1, None])[:, :, :, 0]
        point_flux = np.concatenate((solved, -np.sum(solved, axis=2, keepdims=True)), axis=2)
        original_residual = self.concentration*gradient.copy()
        friction = np.zeros(x.shape[:2])
        for i in range(species):
            for j in range(i+1, species):
                numerator = x[:, :, j]*point_flux[:, :, i]-x[:, :, i]*point_flux[:, :, j]
                original_residual[:, :, i] += numerator/self.diffusion[i, j]
                original_residual[:, :, j] -= numerator/self.diffusion[i, j]
                friction += self.gas_constant/self.concentration*numerator**2/(x[:, :, i]*x[:, :, j]*self.diffusion[i, j])
        internal_flux = np.sum(point_flux*self.weights[None, :, None], axis=1)
        flux = np.zeros((self.count+1, species))
        flux[1:-1] = internal_flux
        inventory_rate = self.area*(flux[:-1]-flux[1:])
        entropy_rate = -self.gas_constant*np.sum((np.log(fractions)+1)*inventory_rate, axis=1)
        production = -self.gas_constant*self.area*np.sum(internal_flux*jump, axis=1)
        path_production = self.area*self.width*np.sum(friction*self.weights[None, :], axis=1)
        return {'fractions': fractions, 'inventories': inventories, 'entropy': entropy,
            'flux': internal_flux, 'inventory_rate': inventory_rate, 'entropy_rate': entropy_rate,
            'production': production, 'path_production': path_production,
            'original_equation_residual_mol_m4': float(np.max(np.abs(original_residual))),
            'molar_flux_sum_mol_m2_s': float(np.max(np.abs(np.sum(internal_flux, axis=1))))}
