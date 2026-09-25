"""Closed, rigid, isothermal/isobaric column with shared molar-frame MS faces.

Only composition is evolved. Reported entropy is the ideal mixing contribution,
not a complete absolute thermochemical state or a reacting-brick energy model.
"""
import numpy as np
from scipy.sparse import lil_matrix

from .maxwell_stefan_entropy_face import IsothermalMaxwellStefanFace


class IsothermalMaxwellStefanColumn:
    def __init__(self, parameters, count, diffusion, concentration, masses, gas_constant):
        self.parameters, self.count = parameters, count
        self.species_count = len(masses)
        self.independent_count = self.species_count-1
        self.width = parameters['geometry']['length_m']/count
        self.area = parameters['geometry']['area_m2']
        self.volume = self.area*self.width
        self.concentration, self.gas_constant = concentration, gas_constant
        self.face = IsothermalMaxwellStefanFace(diffusion, concentration, masses,
            gas_constant, self.width, parameters['face_quadrature_order'])
        edges = np.linspace(0.0, parameters['geometry']['length_m'], count+1)
        wave_number = parameters['initial']['cosine_mode']*np.pi/parameters['geometry']['length_m']
        cell_cosine = np.diff(np.sin(wave_number*edges))/(wave_number*self.width)
        fractions = np.array(parameters['initial']['mean_mole_fractions']) + np.outer(
            cell_cosine, parameters['initial']['cosine_amplitudes'])
        self.initial = fractions[:, :self.independent_count].ravel()

    def fractions(self, values):
        first = np.asarray(values).reshape(self.count, self.independent_count)
        return np.column_stack((first, 1-np.sum(first, axis=1)))

    def observe(self, values):
        fractions = self.fractions(values)
        faces = [self.face.evaluate(left, right)
                 for left, right in zip(fractions[:-1], fractions[1:], strict=True)]
        return fractions, faces

    def rates(self, at, values):
        fractions, faces = self.observe(values)
        flux = np.zeros((self.count+1, self.species_count))
        for i, face in enumerate(faces):
            flux[i+1] = face['molar_fluxes_mol_m2_s']
        rates = (flux[:-1]-flux[1:])/(self.concentration*self.width)
        return rates[:, :self.independent_count].ravel()

    def jacobian_sparsity(self):
        width = self.independent_count
        matrix = lil_matrix((self.count*width, self.count*width), dtype=int)
        for i in range(self.count):
            matrix[i*width:(i+1)*width, max(0, i-1)*width:min(self.count, i+2)*width] = 1
        return matrix.tocsc()
