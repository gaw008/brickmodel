"""Rigid sorptive water/carrier cell on the declared low-moisture branch.

Pure-liquid volume/caloric properties plus a zero-volume excess potential are
the existing constitutive approximation. Dry mass is fixed. The hypothetical
pure liquid standard is not free bulk water, and the cell is not a brick model.
"""
from dataclasses import dataclass
from functools import cache
import math

from scipy.optimize import brentq, root_scalar

from .gas_transport import ideal_gas_state


@dataclass(frozen=True)
class EquilibriumSorptiveCell:
    fluid: object
    excess: object
    dry_mass_kg: float
    dry_reference_temperature_k: float
    temperature_inverse: dict

    def pure_liquid(self, temperature_k, pressure_pa):
        liquid = self.fluid.water.state_tp(temperature_k, pressure_pa, phase='liquid')
        mass = liquid.molar_mass_kg_mol
        mu = liquid.enthalpy_j_mol-temperature_k*liquid.native_entropy_j_kg_k*mass
        standard = self.fluid.gas_enthalpy_j_mol('H2O', temperature_k)-temperature_k*self.fluid.vapor_standard_entropy_j_mol_k(temperature_k)
        rt = self.fluid.thermochemistry.gas_constant_j_mol_k*temperature_k
        pressure = self.fluid.reference_pressure_pa*math.exp((mu-standard)/rt)
        return liquid, mass/liquid.density_kg_m3, mu, standard, pressure

    def inventories_at_tp_moisture(self, temperature_k, pressure_pa, moisture_kg_kg, carrier_fractions):
        liquid, volume, _, _, pure_pressure = self.pure_liquid(temperature_k, pressure_pa)
        condensed = moisture_kg_kg*self.dry_mass_kg/liquid.molar_mass_kg_mol
        gas_volume = self.fluid.available_fluid_volume_m3-condensed*volume
        vapor_pressure = self.excess.evaluate(temperature_k, moisture_kg_kg)['activity']*pure_pressure
        rt = self.fluid.thermochemistry.gas_constant_j_mol_k*temperature_k
        carrier = (pressure_pa-vapor_pressure)*gas_volume/rt
        return {**{key: value*carrier for key, value in carrier_fractions.items()},
                'H2O': condensed+vapor_pressure*gas_volume/rt}

    def at_temperature(self, inventories_mol, temperature_k):
        r = self.fluid.thermochemistry.gas_constant_j_mol_k
        rt, volume = r*temperature_k, self.fluid.available_fluid_volume_m3
        nw = inventories_mol['H2O']
        carrier = math.fsum(value for key, value in inventories_mol.items() if key != 'H2O')
        join_w = self.excess.record['join']['moisture_kg_kg']
        join_activity = self.excess.evaluate(temperature_k, join_w)['activity']
        mass = self.excess.record['water_molar_mass_kg_mol']

        @cache
        def partition(pressure):
            liquid, vl, mu, standard, pure_pressure = self.pure_liquid(temperature_k, pressure)
            coefficient = pure_pressure*join_activity*mass/(self.dry_mass_kg*join_w)
            a, b = coefficient*vl/rt, 1+coefficient*volume/rt
            # Stable small root of a*Nc**2-b*Nc+Nw=0. All water inventory
            # remains in Nc+Nv; no phase stock or pressure is clipped.
            condensed = 2*nw/(b+math.sqrt(b*b-4*a*nw))
            vapor_pressure = coefficient*condensed
            return condensed, liquid, vl, mu, standard, pure_pressure, vapor_pressure

        def residual(pressure):
            nc, _, vl, _, _, _, pv = partition(pressure)
            return pressure-pv-carrier*rt/(volume-nc*vl)

        policy = self.fluid.numerics['pressure_inverse']
        pressure = brentq(residual, *policy['bracket_pa'], xtol=policy['absolute_tolerance_pa'],
                          rtol=policy['relative_tolerance'], maxiter=policy['max_iterations'])
        nc, liquid, vl, mu_liquid, mu_standard, pure_pressure, equilibrium_pressure = partition(pressure)
        w = nc*mass/self.dry_mass_kg
        excess = self.excess.evaluate(temperature_k, w)
        amounts = {**inventories_mol, 'H2O': nw-nc}
        vg = volume-nc*vl
        gas = ideal_gas_state(amounts, temperature_k=temperature_k, gas_volume_m3=vg,
            molar_masses_kg_mol=self.fluid.molar_masses_kg_mol, gas_constant_j_mol_k=r)
        gas_u = math.fsum(value*(self.fluid.gas_enthalpy_j_mol(key, temperature_k)-rt)
                         for key, value in amounts.items())
        condensed_u = nc*liquid.internal_energy_j_mol
        dry_u = self.dry_mass_kg*self.excess.dry_energy_difference_j_kg(temperature_k, self.dry_reference_temperature_k)
        excess_u = self.dry_mass_kg*excess['h_j_kg_dry']
        pv = amounts['H2O']*rt/vg
        mu_vapor = mu_standard+rt*math.log(pv/self.fluid.reference_pressure_pa) if pv else None
        mu_condensed = mu_liquid+excess['mu_j_mol'] if nc else None
        return gas, {'temperature_k': temperature_k, 'pressure_pa': gas.pressure_pa,
            'inventories_mol': dict(inventories_mol), 'amounts_mol': amounts,
            'condensed_water_mol': nc, 'moisture_kg_kg_dry': w, 'gas_volume_m3': vg,
            'condensed_volume_m3': nc*vl, 'water_partial_pressure_pa': pv,
            'equilibrium_partial_pressure_pa': equilibrium_pressure, 'pure_equilibrium_partial_pressure_pa': pure_pressure,
            'water_activity': excess['activity'], 'excess': excess,
            'gas_internal_energy_j': gas_u, 'condensed_internal_energy_j': condensed_u,
            'dry_internal_energy_j': dry_u, 'excess_internal_energy_j': excess_u,
            'constitutive_internal_energy_j': math.fsum((gas_u, condensed_u, dry_u, excess_u)),
            'condensed_standard_molar_entropy_j_mol_k': liquid.native_entropy_j_kg_k*mass,
            'vapor_minus_condensed_chemical_potential_j_mol': mu_vapor-mu_condensed if nc else None,
            'pressure_closure_residual_pa': pressure-gas.pressure_pa,
            'water_pressure_departure_pa': pv-equilibrium_pressure}

    def decode(self, inventories_mol, internal_energy_j, temperature_seed_k):
        policy = self.temperature_inverse
        def residual(temperature):
            return self.at_temperature(inventories_mol, float(temperature))[1]['constitutive_internal_energy_j']-internal_energy_j
        result = root_scalar(residual, method='secant', x0=temperature_seed_k,
            x1=temperature_seed_k+policy['seed_increment_k'], xtol=policy['absolute_tolerance_k'],
            rtol=policy['relative_tolerance'], maxiter=policy['max_iterations'])
        if not result.converged:
            raise RuntimeError('sorptive temperature inverse did not converge: '+result.flag)
        gas, point = self.at_temperature(inventories_mol, float(result.root))
        point.update(internal_energy_j=internal_energy_j,
            energy_inverse_residual_j=point['constitutive_internal_energy_j']-internal_energy_j)
        return gas, point
