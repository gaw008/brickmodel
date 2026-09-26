"""Isothermal spherical pore in a finite incompressible Newtonian shell.

The outer boundary carries prescribed normal traction and has no separate
surface energy. Constant matrix volume, viscosity and pore surface tension
define this restricted creeping-flow model, not a material sintering law.
"""
import math


def spherical_pore_mechanics(radius, gas_pressure, *, matrix_volume, viscosity,
                            surface_tension, outside_pressure):
    pore_volume = 4*math.pi*radius**3/3
    total_volume = matrix_volume+pore_volume
    fraction = pore_volume/total_volume
    outer = (3*total_volume/(4*math.pi))**(1/3)
    rate = (radius*(gas_pressure-outside_pressure)-2*surface_tension)/(4*viscosity*(1-fraction))
    constant = radius**2*rate
    volume_rate = 4*math.pi*constant
    dissipation = 16*math.pi*viscosity*radius*(1-fraction)*rate**2
    surface_energy_rate = 8*math.pi*surface_tension*radius*rate
    return {'radius_m': radius, 'outer_radius_m': outer, 'pore_volume_m3': pore_volume,
            'total_volume_m3': total_volume, 'porosity': fraction,
            'gas_pressure_pa': gas_pressure, 'laplace_pressure_pa': 2*surface_tension/radius,
            'radius_rate_m_s': rate, 'outer_radius_rate_m_s': constant/outer**2,
            'radial_velocity_constant_m3_s': constant,
            'matrix_pressure_pa': outside_pressure-4*viscosity*constant/outer**3,
            'pore_volume_rate_m3_s': volume_rate,
            'porosity_rate_s': matrix_volume*volume_rate/total_volume**2,
            'surface_energy_j': 4*math.pi*surface_tension*radius**2,
            'surface_energy_rate_w': surface_energy_rate,
            'external_work_in_w': -outside_pressure*volume_rate,
            'viscous_dissipation_w': dissipation}


class ViscousSphericalPore:
    def __init__(self, parameters):
        self.p = parameters
        self.matrix_volume = parameters['matrix_volume_m3']
        self.eta = parameters['viscosity_pa_s']
        self.gamma = parameters['surface_tension_n_m']
        self.temperature = parameters['temperature_k']
        self.outside_pressure = parameters['outside_pressure_pa']
        self.r = parameters['gas_constant_j_mol_k']
        self.reference_radius = parameters['reference_radius_m']

    def mechanics(self, radius, gas_pressure):
        state = spherical_pore_mechanics(radius, gas_pressure, matrix_volume=self.matrix_volume,
            viscosity=self.eta, surface_tension=self.gamma, outside_pressure=self.outside_pressure)
        return {**state, 'entropy_production_w_k': state['viscous_dissipation_w']/self.temperature}

    def closed(self, radius, gas_amount):
        volume = 4*math.pi*radius**3/3
        pressure = gas_amount*self.r*self.temperature/volume
        state = self.mechanics(radius, pressure)
        reference_volume = 4*math.pi*self.reference_radius**3/3
        reference_surface = 4*math.pi*self.gamma*self.reference_radius**2
        free_energy = state['surface_energy_j']-reference_surface + self.outside_pressure*(volume-reference_volume)-gas_amount*self.r*self.temperature*math.log(volume/reference_volume)
        gas_entropy_rate = pressure*state['pore_volume_rate_m3_s']/self.temperature
        heat_in = pressure*state['pore_volume_rate_m3_s']-state['viscous_dissipation_w']
        return {**state, 'gas_amount_mol': gas_amount,
                'gas_entropy_change_j_k': gas_amount*self.r*math.log(volume/reference_volume),
                'gas_entropy_rate_w_k': gas_entropy_rate,
                'heat_in_w': heat_in, 'bath_entropy_rate_w_k': -heat_in/self.temperature,
                'free_energy_plus_pressure_work_change_j': free_energy}

    def vented(self, radius, gas_pressure):
        state = self.mechanics(radius, gas_pressure)
        reference_volume = 4*math.pi*self.reference_radius**3/3
        reference_surface = 4*math.pi*self.gamma*self.reference_radius**2
        potential = state['surface_energy_j']-reference_surface + (self.outside_pressure-gas_pressure)*(state['pore_volume_m3']-reference_volume)
        return {**state, 'gas_amount_mol': gas_pressure*state['pore_volume_m3']/(self.r*self.temperature),
                'gas_inflow_mol_s': gas_pressure*state['pore_volume_rate_m3_s']/(self.r*self.temperature),
                'grand_potential_change_j': potential}
