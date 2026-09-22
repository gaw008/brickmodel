"""Finite-volume water/carrier channel with local thermal ballast.

Liquid is locally retained; gas transports water between cells. A single face
transaction updates both neighboring total inventories and energies. Thermal
ballast lies outside the specified fluid-channel volume and has fixed amount.
This is a conditional low-temperature apparatus, not a porous-brick model.
"""
from dataclasses import dataclass
from fractions import Fraction
import math

from scipy.optimize import root_scalar

from .open_gas_boundary import open_gas_boundary_rate


@dataclass(frozen=True)
class BallastWaterCell:
    fluid: object
    solid_facts: dict
    solid_mol: float
    solid_segment_index: int
    reference_temperature_k: float
    temperature_inverse: dict

    def solid_energy_j(self, temperature_k):
        segment = self.solid_facts['segments'][self.solid_segment_index]
        lower, upper = segment['temperature_range_k']
        if not lower <= temperature_k <= upper:
            raise ValueError('temperature outside selected solid caloric phase')
        a, b, c, d, e, _, _, _ = map(float, segment['coefficients'])
        x, y = self.reference_temperature_k/1000, temperature_k/1000
        # Fixed amount and constant-volume approximation: Δu = Δh_standard.
        # The constant reference-pressure volume correction cancels exactly.
        return self.solid_mol*1000*(a*(y-x)+b*(y*y-x*x)/2+c*(y**3-x**3)/3
                                    +d*(y**4-x**4)/4+e*(1/x-1/y))

    def at_temperature(self, inventories_mol, temperature_k):
        gas, point = self.fluid.at_temperature(inventories_mol, temperature_k)
        point['fluid_internal_energy_j'] = point['constitutive_internal_energy_j']
        point['solid_internal_energy_j'] = self.solid_energy_j(temperature_k)
        point['constitutive_internal_energy_j'] = math.fsum((
            point['fluid_internal_energy_j'], point['solid_internal_energy_j']))
        return gas, point

    def decode(self, inventories_mol, internal_energy_j, temperature_seed_k):
        setting = self.temperature_inverse

        def residual(temperature):
            return self.at_temperature(inventories_mol, float(temperature))[1][
                'constitutive_internal_energy_j']-internal_energy_j

        # Explicit warm-start secant policy. No alternate solver or clipped
        # temperature is substituted when the solve fails.
        result = root_scalar(residual, method='secant', x0=temperature_seed_k,
                             x1=temperature_seed_k+setting['seed_increment_k'],
                             xtol=setting['absolute_tolerance_k'],
                             rtol=setting['relative_tolerance'],
                             maxiter=setting['max_iterations'])
        if not result.converged:
            raise RuntimeError('temperature secant did not converge: '+result.flag)
        gas, point = self.at_temperature(inventories_mol, float(result.root))
        point.update(internal_energy_j=internal_energy_j,
                     energy_inverse_residual_j=point['constitutive_internal_energy_j']-internal_energy_j,
                     temperature_inverse_iterations=result.iterations)
        return gas, point


def column_face_rates(gases, reservoir, internal_transfer, surface_transfer, enthalpy):
    """Left end sealed; internal faces left→right; right surface outward."""
    internal = [open_gas_boundary_rate(left, right, internal_transfer, enthalpy)
                for left, right in zip(gases[:-1], gases[1:], strict=True)]
    surface = open_gas_boundary_rate(gases[-1], reservoir, surface_transfer, enthalpy)
    return [*internal, surface]


def apply_column_rates(points, rates, duration_s, surface_radiation_out_w):
    """Shared exact face packets and final binary projections, without clipping."""
    packets = [{
        'amounts_mol': {key: duration_s*Fraction(value) for key, value in rate.exchange.net_mol_s.items()},
        'energy_j': duration_s*Fraction(rate.energy_out_w),
    } for rate in rates]
    radiation = duration_s*Fraction(surface_radiation_out_w)
    updated = []
    for index, point in enumerate(points):
        outward = packets[index]
        incoming = packets[index-1] if index else None
        targets = {key: Fraction(value)-outward['amounts_mol'][key]+(
            incoming['amounts_mol'][key] if incoming else 0)
            for key, value in point['inventories_mol'].items()}
        target_u = Fraction(point['internal_energy_j'])-outward['energy_j']+(
            incoming['energy_j'] if incoming else 0)
        if index == len(points)-1:
            target_u -= radiation
        inventories = {key: float(value) for key, value in targets.items()}
        energy = float(target_u)
        updated.append({
            'inventories_mol': inventories, 'internal_energy_j': energy,
            'inventory_projection_mol': {key: Fraction(inventories[key])-value for key, value in targets.items()},
            'energy_projection_j': Fraction(energy)-target_u,
        })
    return updated, {'faces': packets, 'surface_radiation_out_j': radiation}
