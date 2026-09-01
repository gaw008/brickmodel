from __future__ import annotations

import math

GAS_CONSTANT_J_MOL_K = 8.31446261815324


def arrhenius_rate_constant(A_1_s: float, E_J_mol: float, temperature_K: float, multiplier: float = 1.0) -> float:
    if A_1_s < 0.0 or E_J_mol < 0.0 or temperature_K <= 0.0 or multiplier < 0.0:
        raise ValueError("Arrhenius inputs must be nonnegative and temperature positive")
    exponent = -float(E_J_mol) / (GAS_CONSTANT_J_MOL_K * float(temperature_K))
    return float(A_1_s) * math.exp(max(exponent, -745.0)) * float(multiplier)


def first_order_extent(time_s: float, temperature_K: float, A_1_s: float, E_J_mol: float, initial_extent: float = 0.0) -> float:
    if time_s < 0.0 or not 0.0 <= initial_extent <= 1.0:
        raise ValueError("time must be nonnegative and initial extent in [0, 1]")
    rate = arrhenius_rate_constant(A_1_s, E_J_mol, temperature_K)
    return 1.0 - (1.0 - initial_extent) * math.exp(-rate * time_s)
