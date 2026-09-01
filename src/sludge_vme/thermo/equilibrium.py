from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EquilibriumResult:
    phase_amounts: dict[str, float]
    chemical_potentials_J_mol: dict[str, float] | None
    gibbs_before_J: float
    gibbs_after_J: float
    element_residual: dict[str, float]
    coverage_score: float
    missing_phases: list[str]
    status: str
    source_hash: str


class EquilibriumBackend(Protocol):
    def equilibrate(self, T_K: float, P_Pa: float, element_inventory: dict[str, float], candidate_phases: list[dict]) -> EquilibriumResult: ...
