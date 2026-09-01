from __future__ import annotations

import math

from .kinetics import GAS_CONSTANT_J_MOL_K


def reduced_sintering_rate(
    temperature_K: float,
    liquid_fraction: float,
    d32_m: float,
    *,
    rate_at_1273K_1_s: float = 2e-6,
    activation_energy_J_mol: float = 120000.0,
) -> float:
    if temperature_K <= 0.0 or not 0.0 <= liquid_fraction <= 1.0 or d32_m <= 0.0:
        raise ValueError("invalid sintering state")
    relative_exponent = -activation_energy_J_mol / GAS_CONSTANT_J_MOL_K * (1.0 / temperature_K - 1.0 / 1273.15)
    relative_exponent = min(50.0, max(-50.0, relative_exponent))
    size_factor = min(5.0, max(0.2, 30e-6 / d32_m))
    liquid_factor = 0.25 + 2.5 * liquid_fraction
    return rate_at_1273K_1_s * math.exp(relative_exponent) * size_factor * liquid_factor
