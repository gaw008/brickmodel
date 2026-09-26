"""Source-selected forward first-order conversion at prescribed temperature.

The frequency factor is in s^-1 and the activation energy is in J/mol.
Applicability belongs to the explicitly selected specimen and source domain.
This rate law supplies no reaction enthalpy, product free energy or gas feedback.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RecordedFirstOrderDehydroxylation:
    frequency_factor_per_s: float
    activation_energy_j_mol: float
    gas_constant_j_mol_k: float

    def rate_constant_per_s(self, temperature_k):
        return self.frequency_factor_per_s * math.exp(
            -self.activation_energy_j_mol / (self.gas_constant_j_mol_k * temperature_k))

    def conversion_rate_per_s(self, temperature_k, conversion):
        return self.rate_constant_per_s(temperature_k) * (1 - conversion)

    def conversion_from_exposure(self, exposure):
        return -math.expm1(-exposure)
