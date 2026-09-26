"""Prescribed-temperature F3 conversion for a separately documented specimen.

The model provides no reaction enthalpy, metakaolin state function, steam
inhibition or transport closure. Source applicability is attached to its data.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RecordedThirdOrderDehydroxylation:
    frequency_factor_per_s: float
    activation_energy_j_mol: float
    gas_constant_j_mol_k: float

    def rate_constant_per_s(self, temperature_k):
        return self.frequency_factor_per_s * math.exp(
            -self.activation_energy_j_mol / (self.gas_constant_j_mol_k * temperature_k))

    def conversion_rate_per_s(self, temperature_k, conversion):
        return self.rate_constant_per_s(temperature_k) * (1 - conversion) ** 3

    def conversion_from_exposure(self, exposure, initial_conversion):
        return 1 - ((1 - initial_conversion) ** -2 + 2 * exposure) ** -.5
