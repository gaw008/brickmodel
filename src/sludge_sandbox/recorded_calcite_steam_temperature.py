"""Conditional temperature extension of a fixed-specimen plateau rate.

Reference rates contain the specimen's area and history. The three temperature
slopes must be supplied with their own provenance; no amplitude, barrier, area
or domain is inferred here. This does not model depletion or CO2 inhibition.
"""
from dataclasses import dataclass
from math import exp

from .recorded_calcite_steam_plateau import RecordedCalciteSteamPlateau


@dataclass(frozen=True)
class RecordedCalciteSteamTemperature:
    reference_temperature_k: float
    reference_plateau: RecordedCalciteSteamPlateau
    dry_activation_energy_j_mol: float
    wet_activation_energy_j_mol: float
    water_adsorption_enthalpy_j_mol: float
    gas_constant_j_mol_k: float

    def at_temperature(self, temperature_k):
        coordinate = (1 / self.reference_temperature_k - 1 / temperature_k) / self.gas_constant_j_mol_k
        reference = self.reference_plateau
        return RecordedCalciteSteamPlateau(
            reference.dry_rate_mol_s * exp(self.dry_activation_energy_j_mol * coordinate),
            reference.steam_saturated_rate_mol_s * exp(self.wet_activation_energy_j_mol * coordinate),
            reference.water_adsorption_coefficient_per_pa * exp(self.water_adsorption_enthalpy_j_mol * coordinate),
        )

    def rate_and_derivatives(self, temperature_k, water_partial_pressure_pa):
        plateau = self.at_temperature(temperature_k)
        z = plateau.water_adsorption_coefficient_per_pa * water_partial_pressure_pa
        a = plateau.dry_rate_mol_s
        b = plateau.steam_saturated_rate_mol_s
        denominator = self.gas_constant_j_mol_k * temperature_k**2
        da = a * self.dry_activation_energy_j_mol / denominator
        db = b * self.wet_activation_energy_j_mol / denominator
        dz = z * self.water_adsorption_enthalpy_j_mol / denominator
        return {
            'rate_mol_s': plateau.rate_mol_s(water_partial_pressure_pa),
            'temperature_derivative_mol_s_k': (da + db * z) / (1 + z) + (b - a) * dz / (1 + z)**2,
            'pressure_derivative_mol_s_pa': plateau.pressure_derivative_mol_s_pa(water_partial_pressure_pa),
        }
