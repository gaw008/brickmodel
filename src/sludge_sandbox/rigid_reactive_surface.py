"""Zero-storage gas/heat contact with a prescribed radiating enclosure.

The surface gas is not a reactive solid cell. Its T, pressure and composition
are solved from two species balances and one energy balance. Both adjoining
gas contacts retain the declared finite-force Onsager extension.
"""
import math

import numpy as np
from scipy.optimize import least_squares
from scipy.special import expit

from .rigid_reactive_exchange import rigid_reactive_face
from .rigid_reactive_source_force import source_integral_rigid_face
from .rigid_reactive_tangent import inventory_tangent, face_tangents


def gas_contact_state(cell, temperature_k, pressure_pa, carbon_fraction):
    t, p, x = temperature_k, pressure_pa, carbon_fraction
    r = cell.reaction.gas_constant_j_mol_k
    gas, carrier = cell.gas.standard(t), cell.nitrogen.standard(t)
    return {
        'temperature_k': t, 'pressure_pa': p, 'co2_mol': x, 'nitrogen_mol': 1-x,
        'co2_partial_pressure_pa': p*x, 'nitrogen_partial_pressure_pa': p*(1-x),
        'carbon_chemical_potential_j_mol': gas['gibbs_j_mol']+r*t*math.log(p*x/cell.p0),
        'nitrogen_chemical_potential_j_mol': carrier['gibbs_j_mol']+r*t*math.log(p*(1-x)/cell.p0),
        'co2_partial_enthalpy_j_mol': gas['enthalpy_j_mol'],
        'nitrogen_partial_enthalpy_j_mol': carrier['enthalpy_j_mol'],
        'scope': 'Normalized gas composition only; no assigned storage volume or inventory.',
    }


def gas_contact_tangent(cell, state):
    t = state['temperature_k']; x = state['co2_mol']; r = cell.reaction.gas_constant_j_mol_k
    dt = np.array([1., 0., 0.]); dlogp = np.array([0., 1., 0.]); dx = np.array([0., 0., x*(1-x)])
    gas, carrier = cell.gas.standard(t), cell.nitrogen.standard(t)
    return {'temperature': dt, 'inverse_temperature': -dt/t**2,
        'potential_over_temperature': np.array([
            -gas['enthalpy_j_mol']*dt/t**2+r*(dlogp+dx/x),
            -carrier['enthalpy_j_mol']*dt/t**2+r*(dlogp-dx/(1-x)),
        ]),
        'enthalpies': np.array([gas['cp_j_mol_k']*dt, carrier['cp_j_mol_k']*dt]),
        'fractions': np.array([dx, -dx])}


class RigidReactiveSurface:
    def __init__(self, cell, parameters):
        self.cell = cell; self.parameters = parameters
        p = parameters['interior']; a = parameters['area_m2']; distance = p['distance_m']
        self.interior = {'heat_conductance_w_k': p['conductivity_w_m_k']*a/distance,
            'bulk_mobility_mol2_k_j_s': p['bulk_mobility_mol2_k_j_m_s']*a/distance,
            'counter_mobility_mol2_k_j_s': p['counter_mobility_mol2_k_j_m_s']*a/distance}
        p = parameters['exterior']
        self.exterior = {'heat_conductance_w_k': p['heat_transfer_w_m2_k']*a,
            'bulk_mobility_mol2_k_j_s': p['bulk_mobility_mol2_k_j_m2_s']*a,
            'counter_mobility_mol2_k_j_s': p['counter_mobility_mol2_k_j_m2_s']*a}
        self.radiation_factor = a*parameters['radiation']['emissivity']*parameters['radiation']['stefan_boltzmann_w_m2_k4']
        self.face = rigid_reactive_face
        if 'species_force_evaluation' in parameters:
            self.face = {'source_integral_differences': lambda left,right,params:
                source_integral_rigid_face(left,right,params,self.cell)}[parameters['species_force_evaluation']]

    def solve(self, bulk, reservoir, radiation_temperature_k):
        policy = self.parameters['numerics']; scales = np.array(policy['balance_scales_carbon_nitrogen_energy'])
        t0 = policy['initial_reservoir_weight']*reservoir['temperature_k']+(1-policy['initial_reservoir_weight'])*bulk['temperature_k']
        x0 = policy['initial_reservoir_weight']*reservoir['co2_mol']+(1-policy['initial_reservoir_weight'])*bulk['co2_mol']/(bulk['co2_mol']+bulk['nitrogen_mol'])
        logp0 = policy['initial_reservoir_weight']*math.log(reservoir['pressure_pa']/self.cell.p0)+(1-policy['initial_reservoir_weight'])*math.log(bulk['pressure_pa']/self.cell.p0)
        initial = [t0, logp0, math.log(x0/(1-x0))]
        bulk_tangent = inventory_tangent(self.cell, bulk); gas_tangent = gas_contact_tangent(self.cell, reservoir)

        def evaluate(coordinates):
            t, logp, logitx = coordinates
            surface = gas_contact_state(self.cell, t, self.cell.p0*math.exp(logp), float(expit(logitx)))
            inner = self.face(bulk, surface, self.interior)
            outer = self.face(surface, reservoir, self.exterior)
            radiation = self.radiation_factor*(radiation_temperature_k**4-t**4)
            residual = np.array([inner[k]-outer[k] for k in ('carbon_flow_mol_s', 'nitrogen_flow_mol_s', 'energy_flow_w')])
            residual[2] += radiation
            tangent = gas_contact_tangent(self.cell, surface)
            inner_derivatives = face_tangents(bulk, surface, bulk_tangent, tangent, self.interior,
                inner if 'species_force_evaluation' in self.parameters else None)
            outer_derivatives = face_tangents(surface, reservoir, tangent, gas_tangent, self.exterior,
                outer if 'species_force_evaluation' in self.parameters else None)
            matrix = inner_derivatives[1][:3]-outer_derivatives[0][:3]
            matrix[2, 0] -= 4*self.radiation_factor*t**3
            return surface, inner, outer, radiation, residual, matrix, inner_derivatives, outer_derivatives

        solution = least_squares(lambda q: evaluate(q)[4]/scales, initial,
            jac=lambda q: evaluate(q)[5]/scales[:, None],
            bounds=([self.cell.domain[0], -np.inf, -np.inf], [self.cell.domain[1], np.inf, np.inf]),
            x_scale=policy['coordinate_scales_temperature_logpressure_logitfraction'],
            ftol=policy['function_relative_tolerance'], xtol=policy['coordinate_relative_tolerance'],
            gtol=policy['gradient_absolute_tolerance'], max_nfev=policy['maximum_function_evaluations'])
        if not solution.success:
            raise RuntimeError('Surface balance solve failed: '+solution.message)
        surface, inner, outer, radiation, residual, matrix, inner_d, outer_d = evaluate(solution.x)
        response = -np.linalg.solve(matrix, inner_d[0][:3])
        flux_response = inner_d[0][:3]+inner_d[1][:3]@response
        radiation_entropy = radiation*(1/surface['temperature_k']-1/radiation_temperature_k)
        return {'surface': surface, 'interior_face': inner, 'exterior_face': outer,
            'radiation_in_w': radiation, 'balance_residual_carbon_nitrogen_energy': residual.tolist(),
            'entropy_production_w_k': inner['entropy_production_w_k']+outer['entropy_production_w_k']+radiation_entropy,
            'radiation_entropy_production_w_k': radiation_entropy,
            'surface_coordinate_inventory_derivative': response.tolist(), 'interior_flux_inventory_derivative': flux_response.tolist(),
            'root_coordinates': solution.x.tolist(), 'root_evaluations': solution.nfev, 'root_status': solution.status,
            'root_message': solution.message, 'root_scaled_residual_norm': float(np.linalg.norm(residual/scales)),
            'material_qualified': False, 'training_eligible': False}
