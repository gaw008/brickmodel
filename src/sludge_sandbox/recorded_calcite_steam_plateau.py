"""Fixed-specimen, initial-plateau law from Giammaria & Lefferts (2019).

The two limiting rates already contain specimen/area effects and are mol/s,
not intrinsic rate constants. Temperature is fixed by each source table row.
Only steady low-CO2 decomposition plateaus are represented. This object does
not describe exhaustion, reverse carbonation, transient surface intermediates,
or variation of the specimen mass/area. See the source contract for the domain.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RecordedCalciteSteamPlateau:
    dry_rate_mol_s: float
    steam_saturated_rate_mol_s: float
    water_adsorption_coefficient_per_pa: float

    def rate_mol_s(self, water_partial_pressure_pa):
        theta = self.water_adsorption_coefficient_per_pa * water_partial_pressure_pa
        return (self.dry_rate_mol_s + self.steam_saturated_rate_mol_s * theta) / (1 + theta)

    def pressure_derivative_mol_s_pa(self, water_partial_pressure_pa):
        theta = self.water_adsorption_coefficient_per_pa * water_partial_pressure_pa
        return (self.steam_saturated_rate_mol_s - self.dry_rate_mol_s) * (
            self.water_adsorption_coefficient_per_pa / (1 + theta) ** 2)
