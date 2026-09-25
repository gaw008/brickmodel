"""Rigid sorptive water/carrier cell on the explicitly selected source branch.

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
        standard = self.fluid.gas_enthalpy_j_mol('H2O', temperature_k)-temperature_k*self.fluid.vapor_standard_entropy_j_mol_k(temperature_k)
        return self.liquid_standard(liquid,temperature_k,standard)

    def liquid_standard(self,liquid,temperature_k,standard):
        mass = liquid.molar_mass_kg_mol
        mu = liquid.enthalpy_j_mol-temperature_k*liquid.native_entropy_j_kg_k*mass
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
        mass = self.excess.record['water_molar_mass_kg_mol']
        liquid_at_pressure = self.fluid.water.liquid_at_temperature(temperature_k)
        standard = self.fluid.gas_enthalpy_j_mol('H2O',temperature_k)-temperature_k*self.fluid.vapor_standard_entropy_j_mol_k(temperature_k)

        @cache
        def partition(pressure):
            liquid, vl, mu, vapor_standard, pure_pressure = self.liquid_standard(liquid_at_pressure(pressure),temperature_k,standard)
            condensed, vapor_pressure = self.partition_amounts(nw, temperature_k, vl, pure_pressure)
            return condensed, liquid, vl, mu, vapor_standard, pure_pressure, vapor_pressure

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
            'condensed_chemical_potential_j_mol': mu_condensed,
            'condensed_partial_enthalpy_j_mol': liquid.enthalpy_j_mol+excess['partial_h_j_mol'],
            'vapor_minus_condensed_chemical_potential_j_mol': mu_vapor-mu_condensed if nc else None,
            'pressure_closure_residual_pa': pressure-gas.pressure_pa,
            'water_pressure_departure_pa': pv-equilibrium_pressure}

    def partition_amounts(self, total_water_mol, temperature_k, liquid_volume_m3_mol, pure_pressure_pa):
        join_w = self.excess.record['join']['moisture_kg_kg']
        join_activity = self.excess.evaluate(temperature_k, join_w)['activity']
        mass = self.excess.record['water_molar_mass_kg_mol']
        rt = self.fluid.thermochemistry.gas_constant_j_mol_k*temperature_k
        coefficient = pure_pressure_pa*join_activity*mass/(self.dry_mass_kg*join_w)
        a = coefficient*liquid_volume_m3_mol/rt
        b = 1+coefficient*self.fluid.available_fluid_volume_m3/rt
        # Stable small root of a*Nc**2-b*Nc+Nw=0; no inventory is clipped.
        condensed = 2*total_water_mol/(b+math.sqrt(b*b-4*a*total_water_mol))
        return condensed, coefficient*condensed

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


@dataclass(frozen=True)
class EquilibriumSourceSorptiveCell(EquilibriumSorptiveCell):
    """Full represented source branch with a monotone water inventory root."""

    def partition_amounts(self, total_water_mol, temperature_k, liquid_volume_m3_mol, pure_pressure_pa):
        mass = self.excess.record['water_molar_mass_kg_mol']
        rt = self.fluid.thermochemistry.gas_constant_j_mol_k*temperature_k
        volume = self.fluid.available_fluid_volume_m3
        low_nc,low_pv = super().partition_amounts(total_water_mol,temperature_k,liquid_volume_m3_mol,pure_pressure_pa)
        join_nc = self.dry_mass_kg*self.excess.record['join']['moisture_kg_kg']/mass
        # The low branch is linear in Nc and its inventory root is analytic.
        # Its root is at/below the join iff the common join residual is >=0.
        # Otherwise the monotone source-branch root is above that same join.
        if low_nc <= join_nc:
            return low_nc,low_pv
        max_w = self.excess.record['model_domain']['moisture_kg_kg'][1]
        upper = min(total_water_mol, self.dry_mass_kg*max_w/mass)

        def vapor_pressure(nc):
            return pure_pressure_pa*self.excess.evaluate(temperature_k,nc*mass/self.dry_mass_kg)['activity']

        def residual(nc):
            return nc+vapor_pressure(nc)*(volume-nc*liquid_volume_m3_mol)/rt-total_water_mol

        policy = self.fluid.numerics['condensed_inventory_inverse']
        nc = brentq(residual,join_nc,upper,xtol=policy['absolute_tolerance_mol'],
                    rtol=policy['relative_tolerance'],maxiter=policy['max_iterations'])
        return nc, vapor_pressure(nc)
