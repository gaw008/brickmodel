"""Fixed-temperature pore-gas column with two prescribed ideal reservoirs.

Gas inventory and stream enthalpy are explicit. The bath supplies the heat
needed to maintain the imposed common temperature; no heat equation is solved.
"""
import numpy as np

from .dusty_gas_entropy_face import DustyGasEntropyFace
from .dusty_gas_isothermal_column import IsothermalDustyGasColumn


class OpenIsothermalDustyGasColumn(IsothermalDustyGasColumn):
    def __init__(self, parameters, count, gas_constant, masses, pure_viscosities, diffusion_pressure):
        super().__init__(parameters, count, gas_constant, masses, pure_viscosities, diffusion_pressure)
        self.rt = self.gas_constant*self.temperature
        self.reservoirs = {key: np.asarray(values)/self.rt
            for key, values in parameters['boundary_partial_pressures_pa'].items()}
        self.boundary_face = DustyGasEntropyFace(self.temperature, gas_constant, masses, pure_viscosities,
            diffusion_pressure, parameters['pore'], self.width/2, parameters['face_quadrature_order'])
        self.internal_energy_reference = np.asarray(parameters['fixed_temperature_molar_internal_energy_reference_j_mol'])
        self.enthalpy_reference = self.internal_energy_reference+self.rt
        self.concentration_reference = parameters['entropy_reference_pressure_pa']/self.rt

    def observe(self, values):
        concentration = np.asarray(values).reshape(self.count, self.species_count)
        faces = [self.boundary_face.evaluate(self.reservoirs['left'], concentration[0])]
        faces.extend(self.face.evaluate(left, right) for left, right in zip(concentration[:-1], concentration[1:], strict=True))
        faces.append(self.boundary_face.evaluate(concentration[-1], self.reservoirs['right']))
        return concentration, faces

    def balances(self, concentration, faces):
        flux = np.asarray([face['molar_fluxes_mol_m2_s'] for face in faces])
        inventory_rate = self.area*(flux[:-1]-flux[1:])
        energy_flux = self.area*(flux@self.enthalpy_reference)
        bath_heat = -self.rt*np.sum(inventory_rate, axis=1)
        entropy_rate = -self.gas_constant*np.sum(
            (np.log(concentration/self.concentration_reference)+1)*inventory_rate, axis=1)
        stream_entropy = {key: -self.gas_constant*np.log(value/self.concentration_reference)
            for key, value in self.reservoirs.items()}
        reservoir_entropy = self.area*(-float(np.dot(stream_entropy['left'], flux[0]))
            +float(np.dot(stream_entropy['right'], flux[-1])))
        return {'inventory_rates_mol_s': inventory_rate,
            'stream_energy_fluxes_w': energy_flux, 'bath_heat_into_cells_w': bath_heat,
            'internal_energy_rates_w': inventory_rate@self.internal_energy_reference,
            'cell_entropy_rates_w_k': entropy_rate,
            'material_reservoir_entropy_rate_w_k': reservoir_entropy,
            'bath_entropy_rate_w_k': float(-np.sum(bath_heat)/self.temperature),
            'all_faces_entropy_production_w_k': self.area*sum(face['entropy_from_jump_w_m2_k'] for face in faces)}

    def rates(self, at, values):
        concentration, faces = self.observe(values)
        return (self.balances(concentration, faces)['inventory_rates_mol_s']/self.pore_volume).ravel()
