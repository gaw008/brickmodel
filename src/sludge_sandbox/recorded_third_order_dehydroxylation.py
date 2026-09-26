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

    def precursor_consumption_mol_s(self, temperature_k, precursor_mol, product_mol):
        """Positive material pool with one product formula unit per precursor.

        The F3 constant is s^-1 and acts on a dimensionless unreacted fraction.
        Multiply by the precursor-plus-product pool to recover a molar rate.
        This conserves the nonvolatile formula-unit pool; it is not a cubic
        concentration law with a volume-independent s^-1 coefficient.
        """
        fraction = precursor_mol / (precursor_mol + product_mol)
        return self.rate_constant_per_s(temperature_k) * precursor_mol * fraction**2

    def conversion_from_exposure(self, exposure, initial_conversion):
        return 1 - ((1 - initial_conversion) ** -2 + 2 * exposure) ** -.5
