"""Rigid water/carrier cell with local liquid-vapor equilibrium.

The liquid is pure IAPWS water at total gas pressure. Vapor is ideal, with
IAPWS ideal enthalpy/standard entropy and the mixture gas constant. This is
an explicit approximation, not native IAPWS coexistence or porous material.
Inputs are total species inventories (H2O includes both phases) and total U.
There is no solid, capillarity, sorption, dissolved air, or phase kinetic law.

The supplied domain must keep incipient liquid stable at all evaluated T/P,
with positive carrier inventory, available gas volume, and N_total*v_liquid<V
throughout the pressure bracket (the admitted dilute branch). Root brackets are
explicit caller inputs; root and source-domain errors propagate unchanged.
"""
from dataclasses import dataclass
from functools import cache
import math
from typing import ClassVar

from scipy.optimize import brentq

from .gas_transport import ideal_gas_state


@dataclass(frozen=True)
class EquilibriumWaterCell:
    partition_algorithm: ClassVar[str] = 'pressure_root_analytic_water_inventory_v1'
    water: object
    thermochemistry: object
    molar_masses_kg_mol: dict
    available_fluid_volume_m3: float
    reference_pressure_pa: float
    numerics: dict

    def gas_enthalpy_j_mol(self, species, temperature_k):
        if species == 'H2O':
            return self.water.ideal_vapor(temperature_k).enthalpy_j_mol
        return self.thermochemistry.species(species).enthalpy_j_mol(temperature_k)

    def vapor_standard_entropy_j_mol_k(self, temperature_k):
        """IAPWS Eq. 5 / Table 3 ideal entropy at the declared fixed pressure."""
        facts = self.water.source_record['facts']
        constants = facts['iapws_constants']
        coefficients = facts['ideal_formula_constants']
        tau = constants['T_critical_k']/temperature_k
        delta = self.reference_pressure_pa/(
            constants['R_specific_j_kg_k']*temperature_k*constants['rho_critical_kg_m3'])
        phi = math.fsum((
            math.log(delta), coefficients['n1'], coefficients['n2']*tau,
            coefficients['n3']*math.log(tau),
            *(n*math.log(-math.expm1(-g*tau)) for n, g in
              zip(coefficients['n4_to_n8'], coefficients['gamma4_to_gamma8'], strict=True)),
        ))
        tau_phi_tau = math.fsum((
            coefficients['n2']*tau, coefficients['n3'],
            *(n*g*tau/math.expm1(g*tau) for n, g in
              zip(coefficients['n4_to_n8'], coefficients['gamma4_to_gamma8'], strict=True)),
        ))
        return self.water.reference.native_molar_gas_constant_j_mol_k*(tau_phi_tau-phi)

    def at_temperature(self, inventories_mol, temperature_k):
        """Partition conserved water; the all-vapor branch is a phase condition."""
        r = self.thermochemistry.gas_constant_j_mol_k
        rt = r*temperature_k
        volume = self.available_fluid_volume_m3
        total_water = inventories_mol['H2O']
        carrier = math.fsum(n for species, n in inventories_mol.items() if species != 'H2O')
        h_vapor = self.gas_enthalpy_j_mol('H2O', temperature_k)
        s_standard = self.vapor_standard_entropy_j_mol_k(temperature_k)
        mu_standard = h_vapor-temperature_k*s_standard

        # Exact pressures recur at phase endpoints and in the root solve.
        # This cache lives only for this fixed-T/inventory evaluation; no rounding or EOS
        # interpolation is introduced.
        @cache
        def liquid_at(pressure):
            liquid = self.water.state_tp(temperature_k, pressure, phase='liquid')
            molar_volume = liquid.molar_mass_kg_mol/liquid.density_kg_m3
            mu_liquid = liquid.enthalpy_j_mol-temperature_k*(
                liquid.native_entropy_j_kg_k*liquid.molar_mass_kg_mol)
            equilibrium_pressure = self.reference_pressure_pa*math.exp(
                (mu_liquid-mu_standard)/rt)
            return liquid, molar_volume, mu_liquid, equilibrium_pressure

        pressure = (carrier+total_water)*rt/volume
        liquid, molar_volume, mu_liquid, equilibrium_pressure = liquid_at(pressure)
        all_vapor_pressure_departure = total_water*rt/volume-equilibrium_pressure
        if all_vapor_pressure_departure <= 0:
            # Undersaturated or exactly on the dry endpoint: no liquid remains.
            liquid_mol = 0.
            phase = 'all_vapor'
        else:
            def coexistence_at(p):
                liquid, vl, mu, pe = liquid_at(p)
                # Eliminate vapor inventory using Nv*RT = pe*(V-Nl*vl).
                # This uses the same chemical and volume equations as the
                # nested inventory/pressure solves, with one scalar root.
                nl = (total_water*rt/volume-pe)*volume/(rt-pe*vl)
                return nl, liquid, vl, mu, pe

            def pressure_residual(p):
                nl, _, vl, _, pe = coexistence_at(p)
                return p-pe-carrier*rt/(volume-nl*vl)

            # Carrier-only and all-vapor pressures bound the admitted dilute
            # gas/liquid branch. Intersect numerical root brackets, not state
            # inventories; no phase mass is clipped or supplied afterward.
            setting = self.numerics['pressure_inverse']
            lower = max(setting['bracket_pa'][0], carrier*rt/volume)
            upper = min(setting['bracket_pa'][1], pressure)
            pressure = brentq(pressure_residual, lower, upper,
                              xtol=setting['absolute_tolerance_pa'],
                              rtol=setting['relative_tolerance'],
                              maxiter=setting['max_iterations'])
            liquid_mol, liquid, molar_volume, mu_liquid, equilibrium_pressure = coexistence_at(pressure)
            phase = 'liquid_vapor' if liquid_mol > 0 else 'all_vapor'

        amounts = {**inventories_mol, 'H2O': total_water-liquid_mol}
        liquid_volume = liquid_mol*molar_volume
        gas = ideal_gas_state(amounts, temperature_k=temperature_k,
                              gas_volume_m3=volume-liquid_volume,
                              molar_masses_kg_mol=self.molar_masses_kg_mol,
                              gas_constant_j_mol_k=r)
        species_u = {key: self.gas_enthalpy_j_mol(key, temperature_k)-rt for key in amounts}
        gas_u = math.fsum(amounts[key]*species_u[key] for key in amounts)
        liquid_u = liquid_mol*liquid.internal_energy_j_mol
        vapor_pressure = gas.concentrations_mol_m3['H2O']*rt
        mu_vapor = (mu_standard+rt*math.log(vapor_pressure/self.reference_pressure_pa)
                    if vapor_pressure > 0 else None)
        point = {
            'phase_partition_algorithm': self.partition_algorithm,
            'temperature_k': temperature_k, 'pressure_pa': gas.pressure_pa,
            'liquid_pressure_pa': pressure, 'phase': phase,
            'inventories_mol': dict(inventories_mol), 'amounts_mol': amounts,
            'liquid_water_mol': liquid_mol, 'liquid_volume_m3': liquid_volume,
            'gas_volume_m3': volume-liquid_volume,
            'liquid_density_kg_m3': liquid.density_kg_m3,
            'liquid_molar_u_j_mol': liquid.internal_energy_j_mol,
            'liquid_molar_h_j_mol': liquid.enthalpy_j_mol,
            'liquid_molar_s_j_mol_k': liquid.native_entropy_j_kg_k*liquid.molar_mass_kg_mol,
            'vapor_standard_s_j_mol_k': s_standard,
            'gas_molar_u_j_mol': species_u,
            'liquid_internal_energy_j': liquid_u, 'gas_internal_energy_j': gas_u,
            'constitutive_internal_energy_j': math.fsum((liquid_u, gas_u)),
            'water_partial_pressure_pa': vapor_pressure,
            'equilibrium_partial_pressure_pa': equilibrium_pressure,
            'water_pressure_departure_pa': vapor_pressure-equilibrium_pressure,
            # Signed incipient-liquid criterion using ALL water in the full
            # fluid volume. Actual wet-state vapor departure is near zero
            # throughout coexistence and cannot locate phase transitions.
            'all_vapor_pressure_departure_pa': all_vapor_pressure_departure,
            'liquid_chemical_potential_j_mol': mu_liquid,
            'vapor_chemical_potential_j_mol': mu_vapor,
            'vapor_minus_liquid_chemical_potential_j_mol': (
                mu_vapor-mu_liquid if mu_vapor is not None else None),
            'pressure_closure_residual_pa': pressure-gas.pressure_pa,
        }
        return gas, point

    def decode(self, inventories_mol, internal_energy_j):
        setting = self.numerics['temperature_inverse']

        def residual(temperature):
            _, point = self.at_temperature(inventories_mol, temperature)
            return point['constitutive_internal_energy_j']-internal_energy_j

        temperature = brentq(residual, *setting['bracket_k'],
                             xtol=setting['absolute_tolerance_k'],
                             rtol=setting['relative_tolerance'],
                             maxiter=setting['max_iterations'])
        gas, point = self.at_temperature(inventories_mol, temperature)
        point['internal_energy_j'] = internal_energy_j
        point['energy_inverse_residual_j'] = point['constitutive_internal_energy_j']-internal_energy_j
        return gas, point
