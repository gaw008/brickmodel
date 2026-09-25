"""Closed isothermal gas inventories in a rigid, explicitly prescribed pore volume."""
import numpy as np
from scipy.sparse import lil_matrix

from .dusty_gas_entropy_face import DustyGasEntropyFace


class IsothermalDustyGasColumn:
    def __init__(self, parameters, count, gas_constant, masses, pure_viscosities, diffusion_pressure):
        self.parameters, self.count, self.species_count = parameters, count, len(masses)
        self.temperature, self.gas_constant = parameters['temperature_k'], gas_constant
        self.width = parameters['geometry']['length_m']/count
        self.area = parameters['geometry']['area_m2']
        self.porosity = parameters['pore']['porosity']
        self.pore_volume = self.porosity*self.area*self.width
        self.face = DustyGasEntropyFace(self.temperature, gas_constant, masses, pure_viscosities,
            diffusion_pressure, parameters['pore'], self.width, parameters['face_quadrature_order'])
        edges = np.linspace(0, parameters['geometry']['length_m'], count+1)
        wave = parameters['initial']['cosine_mode']*np.pi/parameters['geometry']['length_m']
        cosine = np.diff(np.sin(wave*edges))/(wave*self.width)
        initial_pressure = np.asarray(parameters['initial']['mean_partial_pressures_pa'])+np.outer(
            cosine, parameters['initial']['cosine_partial_pressure_amplitudes_pa'])
        self.initial = (initial_pressure/(gas_constant*self.temperature)).ravel()

    def observe(self, values):
        concentrations = np.asarray(values).reshape(self.count, self.species_count)
        faces = [self.face.evaluate(left, right) for left, right in zip(
            concentrations[:-1], concentrations[1:], strict=True)]
        return concentrations, faces

    def rates(self, at, values):
        _, faces = self.observe(values)
        flux = np.zeros((self.count+1, self.species_count))
        for i, face in enumerate(faces):
            flux[i+1] = face['molar_fluxes_mol_m2_s']
        return ((flux[:-1]-flux[1:])/(self.porosity*self.width)).ravel()

    def jacobian_sparsity(self):
        width = self.species_count
        matrix = lil_matrix((self.count*width, self.count*width), dtype=int)
        for i in range(self.count):
            matrix[i*width:(i+1)*width, max(0,i-1)*width:min(self.count,i+2)*width] = 1
        return matrix.tocsc()
