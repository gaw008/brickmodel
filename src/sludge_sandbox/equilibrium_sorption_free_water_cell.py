"""Shared vapor, sorbed liquid-standard water, and free water in a rigid cell."""
from dataclasses import dataclass

from .equilibrium_sorptive_cell import EquilibriumSourceSorptiveCell


@dataclass(frozen=True)
class EquilibriumSorptionFreeWaterCell(EquilibriumSourceSorptiveCell):
    def partition_amounts(self, total_water_mol, temperature_k, liquid_volume_m3_mol, pure_pressure_pa):
        mass = self.excess.record['water_molar_mass_kg_mol']
        rt = self.fluid.thermochemistry.gas_constant_j_mol_k*temperature_k
        density = pure_pressure_pa/rt
        condensed = (total_water_mol-density*self.fluid.available_fluid_volume_m3)/(1-density*liquid_volume_m3_mol)
        saturation = self.excess.saturation(temperature_k)['moisture_kg_kg']*self.dry_mass_kg/mass
        if condensed >= saturation:
            return condensed, pure_pressure_pa
        return super().partition_amounts(total_water_mol, temperature_k, liquid_volume_m3_mol, pure_pressure_pa)

    def at_temperature(self, inventories_mol, temperature_k):
        gas, state = super().at_temperature(inventories_mol, temperature_k)
        excess = state['excess']
        scale = self.dry_mass_kg/self.excess.record['water_molar_mass_kg_mol']
        state.update(sorbed_water_mol=excess['sorbed_moisture_kg_kg']*scale,
                     free_water_mol=excess['free_moisture_kg_kg']*scale,
                     sorption_phase=excess['branch'])
        return gas, state
