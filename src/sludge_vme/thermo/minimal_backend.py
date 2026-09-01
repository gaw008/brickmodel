from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

from .equilibrium import EquilibriumResult


class MinimalGibbsBackend:
    """Pure-phase linear Gibbs minimizer; no oxide-solution claim is made."""

    def __init__(self, source_hash: str):
        self.source_hash = source_hash

    def equilibrate(self, T_K: float, P_Pa: float, element_inventory: dict[str, float], candidate_phases: list[dict]) -> EquilibriumResult:
        if T_K <= 0.0 or P_Pa <= 0.0:
            raise ValueError("temperature and pressure must be positive")
        known = [item for item in candidate_phases if isinstance(item.get("formula"), dict) and "gibbs_J_mol" in item]
        missing = [str(item.get("id", "unknown")) for item in candidate_phases if item not in known]
        coverage = len(known) / max(len(candidate_phases), 1)
        if not known:
            return EquilibriumResult({}, None, 0.0, 0.0, dict(element_inventory), coverage, missing, "failure_no_covered_phases", self.source_hash)
        elements = sorted(element_inventory)
        matrix = np.array([[float(phase["formula"].get(element, 0.0)) for phase in known] for element in elements], dtype=float)
        inventory = np.array([float(element_inventory[element]) for element in elements], dtype=float)
        gibbs = np.array([float(phase["gibbs_J_mol"]) for phase in known], dtype=float)
        solution = linprog(gibbs, A_eq=matrix, b_eq=inventory, bounds=(0.0, None), method="highs")
        if not solution.success:
            return EquilibriumResult({}, None, float("nan"), float("nan"), dict(element_inventory), coverage, missing, "solver_failure", self.source_hash)
        amounts = np.asarray(solution.x)
        residual = matrix @ amounts - inventory
        phase_amounts = {str(phase["id"]): float(amount) for phase, amount in zip(known, amounts)}
        feasible_reference = np.zeros_like(amounts)
        reference_result = linprog(np.zeros_like(gibbs), A_eq=matrix, b_eq=inventory, bounds=(0.0, None), method="highs")
        if reference_result.success:
            feasible_reference = np.asarray(reference_result.x)
        gibbs_before = float(gibbs @ feasible_reference)
        gibbs_after = float(gibbs @ amounts)
        status = "success" if not missing else "success_with_coverage_gap"
        return EquilibriumResult(
            phase_amounts, {str(phase["id"]): float(mu) for phase, mu in zip(known, gibbs)}, gibbs_before,
            gibbs_after, {element: float(value) for element, value in zip(elements, residual)}, coverage, missing, status, self.source_hash,
        )
