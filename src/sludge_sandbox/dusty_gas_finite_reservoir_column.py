"""Isothermal rigid pore column coupled to two well-mixed finite gas reservoirs."""
import numpy as np
from scipy.sparse import lil_matrix

from .dusty_gas_entropy_face import DustyGasEntropyFace


class FiniteReservoirDustyGasColumn:
    def __init__(self, parameters, count, gas_constant, masses, pure_viscosities, diffusion_pressure):
        self.count, self.species_count = count, len(masses)
        self.temperature, self.gas_constant = parameters['temperature_k'], gas_constant
        self.rt = gas_constant*self.temperature
        self.area = parameters['geometry']['area_m2']
        self.width = parameters['geometry']['length_m']/count
        self.pore_volume = parameters['pore']['porosity']*self.area*self.width
        self.volumes = np.concatenate(([parameters['reservoir_volumes_m3']['left']],
            np.full(count, self.pore_volume), [parameters['reservoir_volumes_m3']['right']]))
        self.face = DustyGasEntropyFace(self.temperature, gas_constant, masses, pure_viscosities,
            diffusion_pressure, parameters['pore'], self.width, parameters['face_quadrature_order'])
        self.boundary_face = DustyGasEntropyFace(self.temperature, gas_constant, masses, pure_viscosities,
            diffusion_pressure, parameters['pore'], self.width/2, parameters['face_quadrature_order'])
        ends = np.asarray([parameters['initial_reservoir_partial_pressures_pa'][key] for key in ['left','right']])
        centers = (np.arange(count)+0.5)/count
        profile = ends[0]+centers[:,None]*(ends[1]-ends[0])
        self.initial = (np.vstack((ends[0],profile,ends[1]))/self.rt).ravel()
        self.internal_energy_reference = np.asarray(parameters['fixed_temperature_molar_internal_energy_reference_j_mol'])
        self.enthalpy_reference = self.internal_energy_reference+self.rt
        self.concentration_reference = parameters['entropy_reference_pressure_pa']/self.rt

    def observe(self, values):
        concentrations = np.asarray(values).reshape(self.count+2,self.species_count)
        faces = []
        for i,(left,right) in enumerate(zip(concentrations[:-1],concentrations[1:],strict=True)):
            law = self.boundary_face if i in (0,self.count) else self.face
            faces.append(law.evaluate(left,right))
        return concentrations,faces

    def balances(self, concentrations, faces):
        flux = np.zeros((self.count+3,self.species_count))
        flux[1:-1] = [face['molar_fluxes_mol_m2_s'] for face in faces]
        inventory_rate = self.area*(flux[:-1]-flux[1:])
        stream_energy = self.area*(flux@self.enthalpy_reference)
        bath_heat = -self.rt*np.sum(inventory_rate,axis=1)
        entropy_rate = -self.gas_constant*np.sum(
            (np.log(concentrations/self.concentration_reference)+1)*inventory_rate,axis=1)
        return {'inventory_rates_mol_s':inventory_rate,
            'stream_energy_fluxes_w':stream_energy, 'bath_heat_into_cells_w':bath_heat,
            'internal_energy_rates_w':inventory_rate@self.internal_energy_reference,
            'cell_entropy_rates_w_k':entropy_rate,
            'bath_entropy_rate_w_k':float(-bath_heat.sum()/self.temperature),
            'all_faces_entropy_production_w_k':self.area*sum(face['entropy_from_jump_w_m2_k'] for face in faces)}

    def rates(self, at, values):
        concentration,faces = self.observe(values)
        return (self.balances(concentration,faces)['inventory_rates_mol_s']/self.volumes[:,None]).ravel()

    def jacobian_sparsity(self):
        count,width = self.count+2,self.species_count
        matrix = lil_matrix((count*width,count*width),dtype=int)
        for i in range(count):
            matrix[i*width:(i+1)*width,max(0,i-1)*width:min(count,i+2)*width] = 1
        return matrix.tocsc()
