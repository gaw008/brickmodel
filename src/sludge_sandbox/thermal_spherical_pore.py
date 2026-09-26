"""Closed ideal gas, constant-gamma viscous pore and uniform matrix temperature.

The matrix is incompressible, with constant total heat capacity. Mechanical
inertia, thermal expansion and an outer-surface energy are absent. These are
declared constitutive assumptions, not measured brick properties.
"""
import math

from .viscous_spherical_pore import spherical_pore_mechanics


class ThermalSphericalPore:
    def __init__(self, parameters, gas_phase):
        self.p = parameters
        self.phase = gas_phase
        self.r = parameters['gas_constant_j_mol_k']
        self.capacity = parameters['matrix_volume_m3'] * parameters['matrix_volumetric_cv_j_m3_k']

    def at_state(self, radius, temperature, gas_amount, bath_temperature, conductance):
        p = self.p
        volume = 4*math.pi*radius**3/3
        pressure = gas_amount*self.r*temperature/volume
        state = spherical_pore_mechanics(radius, pressure, matrix_volume=p['matrix_volume_m3'],
            viscosity=p['viscosity_pa_s'], surface_tension=p['surface_tension_n_m'],
            outside_pressure=p['outside_pressure_pa'])
        gas = self.phase.standard(temperature)
        cv = gas_amount*(gas['cp_j_mol_k']-self.r)+self.capacity
        heat = conductance*(bath_temperature-temperature)
        compression_work = -pressure*state['pore_volume_rate_m3_s']
        temperature_rate = (heat+compression_work+state['viscous_dissipation_w'])/cv
        gas_energy = gas_amount*(gas['enthalpy_j_mol']-self.r*temperature)
        matrix_energy = self.capacity*(temperature-p['reference_temperature_k'])
        gas_entropy = gas_amount*(gas['entropy_j_mol_k']-self.r*math.log(pressure/p['standard_pressure_pa']))
        matrix_entropy = self.capacity*math.log(temperature/p['reference_temperature_k'])
        viscous_entropy = state['viscous_dissipation_w']/temperature
        heat_entropy = heat*(1/temperature-1/bath_temperature)
        return {**state, 'temperature_k': temperature, 'gas_amount_mol': gas_amount,
                'bath_temperature_k': bath_temperature, 'heat_in_w': heat,
                'gas_compression_work_w': compression_work,
                'temperature_rate_k_s': temperature_rate, 'cv_j_k': cv,
                'gas_internal_energy_j': gas_energy, 'matrix_internal_energy_j': matrix_energy,
                'internal_energy_j': gas_energy+matrix_energy+state['surface_energy_j'],
                'gas_entropy_j_k': gas_entropy, 'matrix_entropy_j_k': matrix_entropy,
                'entropy_j_k': gas_entropy+matrix_entropy,
                'entropy_rate_w_k': heat/temperature+viscous_entropy,
                'bath_entropy_rate_w_k': -heat/bath_temperature,
                'viscous_entropy_production_w_k': viscous_entropy,
                'heat_entropy_production_w_k': heat_entropy,
                'entropy_production_w_k': viscous_entropy+heat_entropy}
