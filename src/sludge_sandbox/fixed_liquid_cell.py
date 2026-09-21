"""Rigid, common-T/P wet storage with explicitly fixed liquid inventory.

This constrained-phase model permits gas exchange, not evaporation/condensation.
Liquid is pure IAPWS water; gas water uses ideal IAPWS enthalpy and mixture R.
The fixed dry mass has an explicit linear Cp fit and temperature-independent
solid volume. Available fluid volume excludes that unspecified solid volume.
"""
from dataclasses import dataclass
import math

from scipy.optimize import brentq

from .gas_transport import ideal_gas_state


@dataclass(frozen=True)
class FixedLiquidCell:
    water: object
    thermochemistry: object
    molar_masses_kg_mol: dict
    available_fluid_volume_m3: float
    liquid_water_mol: float
    dry_mass_kg: float
    dry_caloric: dict
    numerics: dict

    def gas_enthalpy_j_mol(self, species, temperature_k):
        if species == 'H2O':
            return self.water.ideal_vapor(temperature_k).enthalpy_j_mol
        return self.thermochemistry.species(species).enthalpy_j_mol(temperature_k)

    def solid_energy_j(self, temperature_k):
        c = self.dry_caloric
        lo, hi = c['temperature_domain_k']
        if not lo <= temperature_k <= hi:
            raise ValueError('temperature outside supplied dry-Cp source domain')
        a = c['reference_temperature_k'] - c['celsius_zero_k']
        b = temperature_k - c['celsius_zero_k']
        return self.dry_mass_kg * (
            c['intercept_j_kg_k'] * (b-a)
            + c['slope_j_kg_k2'] * (b*b-a*a)/2
        )

    def liquid_at(self, temperature_k, pressure_pa):
        liquid = self.water.state_tp(temperature_k, pressure_pa, phase='liquid')
        volume = self.liquid_water_mol * liquid.molar_mass_kg_mol / liquid.density_kg_m3
        return liquid, volume

    def at_temperature(self, amounts_mol, temperature_k):
        r = self.thermochemistry.gas_constant_j_mol_k
        ntotal = math.fsum(amounts_mol.values())

        def pressure_residual(pressure):
            _, volume = self.liquid_at(temperature_k, pressure)
            gas_volume = self.available_fluid_volume_m3-volume
            return pressure-ntotal*r*temperature_k/gas_volume

        p = self.numerics['pressure_inverse']
        pressure = brentq(pressure_residual, *p['bracket_pa'],
                          xtol=p['absolute_tolerance_pa'], rtol=p['relative_tolerance'],
                          maxiter=p['max_iterations'])
        liquid, liquid_volume = self.liquid_at(temperature_k, pressure)
        gas_volume = self.available_fluid_volume_m3-liquid_volume
        gas = ideal_gas_state(
            amounts_mol, temperature_k=temperature_k, gas_volume_m3=gas_volume,
            molar_masses_kg_mol=self.molar_masses_kg_mol, gas_constant_j_mol_k=r,
        )
        species_u = {key: self.gas_enthalpy_j_mol(key, temperature_k)-r*temperature_k
                     for key in amounts_mol}
        liquid_u = self.liquid_water_mol*liquid.internal_energy_j_mol
        solid_u = self.solid_energy_j(temperature_k)
        gas_u = math.fsum(amounts_mol[key]*species_u[key] for key in amounts_mol)
        energy = math.fsum((liquid_u, solid_u, gas_u))
        point = {
            'temperature_k': temperature_k, 'pressure_pa': gas.pressure_pa,
            'liquid_pressure_pa': pressure,
            'pressure_closure_residual_pa': pressure-gas.pressure_pa,
            'liquid_water_mol': self.liquid_water_mol, 'amounts_mol': dict(amounts_mol),
            'liquid_volume_m3': liquid_volume, 'gas_volume_m3': gas_volume,
            'liquid_density_kg_m3': liquid.density_kg_m3,
            'liquid_molar_u_j_mol': liquid.internal_energy_j_mol,
            'liquid_molar_h_j_mol': liquid.enthalpy_j_mol,
            'gas_molar_u_j_mol': species_u,
            'liquid_internal_energy_j': liquid_u, 'solid_internal_energy_j': solid_u,
            'gas_internal_energy_j': gas_u, 'constitutive_internal_energy_j': energy,
        }
        return gas, point

    def decode(self, amounts_mol, internal_energy_j):
        p = self.numerics['temperature_inverse']

        def residual(temperature):
            _, point = self.at_temperature(amounts_mol, temperature)
            return point['constitutive_internal_energy_j']-internal_energy_j

        temperature = brentq(residual, *p['bracket_k'],
                             xtol=p['absolute_tolerance_k'], rtol=p['relative_tolerance'],
                             maxiter=p['max_iterations'])
        gas, point = self.at_temperature(amounts_mol, temperature)
        point['internal_energy_j'] = internal_energy_j
        point['energy_inverse_residual_j'] = point['constitutive_internal_energy_j']-internal_energy_j
        return gas, point
