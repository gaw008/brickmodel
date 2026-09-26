"""Mass-specific Cp and relative sensible H/S for a fixed material state.

No formation energy, absolute entropy or reaction energy is supplied. The
source temperature and specimen applicability belong to the supplied record.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RecordedSensibleHeatPolynomial:
    constant_j_kg_k: float
    linear_j_kg_k2: float
    inverse_square_j_k_kg: float
    reference_temperature_k: float

    def cp_j_kg_k(self, temperature_k):
        return self.constant_j_kg_k + self.linear_j_kg_k2 * temperature_k + self.inverse_square_j_k_kg / temperature_k**2

    def relative_enthalpy_j_kg(self, temperature_k):
        t0 = self.reference_temperature_k
        return (self.constant_j_kg_k * (temperature_k-t0)
                + self.linear_j_kg_k2 * (temperature_k**2-t0**2) / 2
                - self.inverse_square_j_k_kg * (1/temperature_k-1/t0))

    def relative_entropy_j_kg_k(self, temperature_k):
        t0 = self.reference_temperature_k
        return (self.constant_j_kg_k * math.log(temperature_k/t0)
                + self.linear_j_kg_k2 * (temperature_k-t0)
                - self.inverse_square_j_k_kg * (temperature_k**-2-t0**-2) / 2)
