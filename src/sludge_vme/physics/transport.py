from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConductivityClosure:
    value_W_m_K: float
    source_kind: str
    validity: str


def kozeny_carman_permeability(d32_m: float, porosity: float, constant: float, *, sphericity: float = 1.0) -> float:
    if d32_m <= 0.0 or constant <= 0.0 or not 0.0 < porosity < 1.0 or not 0.0 < sphericity <= 1.0:
        raise ValueError("d32, constant and sphericity must be positive; porosity must be in (0, 1)")
    effective_diameter = d32_m * sphericity
    return effective_diameter**2 * porosity**3 / (constant * (1.0 - porosity) ** 2)


def effective_conductivity_ensemble(solid_W_m_K: float, gas_W_m_K: float, porosity: float) -> dict[str, ConductivityClosure]:
    if solid_W_m_K <= 0.0 or gas_W_m_K <= 0.0 or not 0.0 <= porosity < 1.0:
        raise ValueError("conductivities must be positive and porosity in [0, 1)")
    numerator = 2.0 * solid_W_m_K + gas_W_m_K - 2.0 * porosity * (solid_W_m_K - gas_W_m_K)
    denominator = 2.0 * solid_W_m_K + gas_W_m_K + porosity * (solid_W_m_K - gas_W_m_K)
    maxwell = solid_W_m_K * numerator / denominator
    parallel = (1.0 - porosity) * solid_W_m_K + porosity * gas_W_m_K
    series = 1.0 / ((1.0 - porosity) / solid_W_m_K + porosity / gas_W_m_K)
    return {
        "maxwell_eucken": ConductivityClosure(maxwell, "effective_medium_closure", "isotropic dispersed pores"),
        "parallel_series_midpoint": ConductivityClosure(0.5 * (parallel + series), "closure_ensemble", "morphology bound midpoint"),
    }
