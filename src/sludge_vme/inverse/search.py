from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from scipy.stats import qmc, spearmanr

from ..models import simulate
from ..types import CaseConfig
from ..uq.sampling import sample_parameters
from .constraints import constraint_record, quality_margin
from .pareto import nondominated_mask
from .transforms import design_from_unit

_L0_CACHE: dict[tuple[str, str, int], list[tuple[CaseConfig, dict[str, Any]]]] = {}


@dataclass
class InverseResult:
    status: str
    seed: int
    budget: str
    all_evaluations: list[dict[str, Any]]
    feasible_set: list[dict[str, Any]]
    pareto_set: list[dict[str, Any]]
    ranked_candidates: list[dict[str, Any]]
    rank_stability: dict[str, Any]
    active_constraints: list[str]
    l0_l1_disagreement: list[dict[str, Any]]
    environmental_status: str
    warnings: list[str]
    design_space: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "seed": self.seed,
            "budget": self.budget,
            "all_evaluations": self.all_evaluations,
            "feasible_set": self.feasible_set,
            "pareto_set": self.pareto_set,
            "ranked_candidates": self.ranked_candidates,
            "rank_stability": self.rank_stability,
            "active_constraints": self.active_constraints,
            "l0_l1_disagreement": self.l0_l1_disagreement,
            "environmental_status": self.environmental_status,
            "warnings": self.warnings,
            "design_space": self.design_space,
        }


def _risk(summary: dict[str, Any]) -> float:
    return max(float(summary[name]["value"]) for name in ("cracking_risk", "bloating_risk", "underfiring_risk", "overfiring_risk"))


def _quantiles(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {name: float(value) for name, value in zip(("q05", "q50", "q95"), np.quantile(array, (0.05, 0.5, 0.95)))}


def _record_from_results(case: CaseConfig, decision: dict[str, float], design_id: int, fidelity: str, results: list, *, grid_converged: bool | None = None) -> dict[str, Any]:
    successes = [item for item in results if item.status.success]
    if not successes:
        return {
            "design_id": design_id,
            "decision": decision,
            "fidelity": fidelity,
            "status": "failed",
            "failure_reason": "; ".join(item.status.code for item in results),
            "constraints": {"all_hard_constraints": False},
            "objectives": [None] * 5,
            "source_hashes": {"case": case.content_hash},
        }
    margins = [quality_margin(item.summary, case.raw["quality_targets"]) for item in successes]
    risks = [_risk(item.summary) for item in successes]
    quality_q = _quantiles(margins)
    risk_q = _quantiles(risks)
    representative = successes[0]
    constraints = constraint_record(representative, quality_q["q05"], risk_q["q95"], grid_converged=grid_converged)
    uncertainty_width = quality_q["q95"] - quality_q["q05"]
    objectives = [
        -quality_q["q05"],
        risk_q["q95"],
        float(representative.summary["residence_time_s"]["value"]) / 150000.0,
        uncertainty_width,
        -float(decision["sludge_dry_mass_fraction"]),
    ]
    status = "feasible" if constraints["all_hard_constraints"] else "infeasible"
    return {
        "design_id": design_id,
        "decision": decision,
        "fidelity": fidelity,
        "status": status,
        "failure_reason": None,
        "quality_margin": quality_q,
        "enabled_risk": risk_q,
        "uncertainty_width": uncertainty_width,
        "constraints": constraints,
        "objectives": objectives,
        "summary": {key: representative.summary[key] for key in (
            "bulk_density_kg_m3", "open_porosity", "linear_shrinkage", "water_absorption_proxy_percent",
            "strength_proxy_Pa", "cracking_risk", "bloating_risk", "underfiring_risk", "overfiring_risk",
            "thermo_coverage_score", "residence_time_s",
        )},
        "source_hashes": {
            "case": case.content_hash,
            "parameter_pack": representative.provenance["parameter_pack_hash"],
        },
        "model_flags": representative.flags,
        "solver_statistics": representative.solver_statistics,
    }


def _l0_library(case: CaseConfig, budget: str, seed: int) -> list[tuple[CaseConfig, dict[str, Any]]]:
    key = (case.content_hash, budget, seed)
    if key in _L0_CACHE:
        return _L0_CACHE[key]
    budget_config = case.raw["inverse_design"].get(budget)
    if not budget_config:
        raise ValueError(f"unknown inverse budget {budget!r}")
    count = int(budget_config["sobol_designs"])
    power = int(round(np.log2(count)))
    if 2**power != count:
        raise ValueError("Sobol design count must be a power of two")
    points = qmc.Sobol(d=8, scramble=True, seed=seed).random_base2(power)
    library: list[tuple[CaseConfig, dict[str, Any]]] = []
    uq_count = int(budget_config["l0_uncertainty_samples"])
    uq_power = int(round(np.log2(uq_count)))
    for index, point in enumerate(points):
        design_case, decision = design_from_unit(case, point, index)
        samples = sample_parameters(uq_power, seed + 31 * (index + 1))
        results = [simulate(design_case, "L0", sample) for sample in samples]
        library.append((design_case, _record_from_results(design_case, decision, index, "L0", results)))
    _L0_CACHE[key] = library
    return library


def _diverse_shortlist(feasible: list[tuple[CaseConfig, dict[str, Any]]], count: int) -> list[tuple[CaseConfig, dict[str, Any]]]:
    """Select low gas-pressure-risk points, then retain composition diversity.

    L1 resolves diffusion gradients absent from L0, so extreme sludge utilization is
    not used as the primary selector: that previously promoted optimizer-exploiting
    points with large L1 overpressure.  The first half of the shortlist is the
    lowest L0 bloating-risk set; remaining slots maximize sludge-fraction distance.
    """
    ordered = sorted(
        feasible,
        key=lambda item: (
            float(item[1]["summary"]["bloating_risk"]["value"]),
            -float(item[1]["quality_margin"]["q05"]),
        ),
    )
    if len(ordered) <= count:
        return ordered
    selected = [ordered[0]]
    while len(selected) < count:
        anchor_fractions = [item[1]["decision"]["sludge_dry_mass_fraction"] for item in selected]
        pool = ordered[: max(count * 3, len(ordered) // 2)]
        remaining = [item for item in pool if item not in selected]
        candidate = max(
            remaining,
            key=lambda item: min(abs(item[1]["decision"]["sludge_dry_mass_fraction"] - anchor) for anchor in anchor_fractions)
            - 0.25 * float(item[1]["summary"]["bloating_risk"]["value"]),
        )
        selected.append(candidate)
    return selected


def run_inverse(case: CaseConfig, budget: Literal["tiny", "default"] = "tiny", seed: int = 20260831, *, refine_l1: bool = True) -> InverseResult:
    library = _l0_library(case, budget, int(seed))
    all_evaluations = [record for _, record in library]
    feasible_pairs = [(design_case, record) for design_case, record in library if record["constraints"].get("all_hard_constraints")]
    feasible_records = [record for _, record in feasible_pairs]
    if not refine_l1:
        objectives = np.asarray([record["objectives"] for record in feasible_records], dtype=float) if feasible_records else np.empty((0, 5))
        pareto = [record for record, keep in zip(feasible_records, nondominated_mask(objectives, np.ones(len(feasible_records), dtype=bool)))] if feasible_records else []
        return InverseResult(
            "success_l0_only" if feasible_records else "no_feasible_designs", seed, budget, all_evaluations, feasible_records,
            pareto, feasible_records, {"status": "insufficient_points"}, [], [], "not_evaluated",
            ["L1 refinement was explicitly disabled; results are screening-only."], _design_space(case),
        )

    shortlist_count = int(case.raw["inverse_design"][budget]["l1_shortlist"])
    shortlist = _diverse_shortlist(feasible_pairs, shortlist_count)
    refined: list[dict[str, Any]] = []
    disagreement: list[dict[str, Any]] = []
    for position, (design_case, l0_record) in enumerate(shortlist):
        base_result = simulate(design_case, "L1", {"grid_check": True})
        l1_sample_count = int(case.raw["inverse_design"][budget]["l1_uncertainty_samples"])
        l1_power = int(round(np.log2(l1_sample_count)))
        if 2**l1_power != l1_sample_count:
            raise ValueError("L1 uncertainty sample count must be a power of two")
        extra_samples = sample_parameters(l1_power, seed + 10007 + position)[: max(0, l1_sample_count - 1)]
        extra_results = [simulate(design_case, "L1", sample) for sample in extra_samples]
        grid = base_result.solver_statistics.get("grid_convergence", {})
        grid_converged = bool(grid.get("converged", False))
        record = _record_from_results(design_case, l0_record["decision"], l0_record["design_id"], "L1", [base_result, *extra_results], grid_converged=grid_converged)
        refined.append(record)
        disagreement.append({
            "design_id": record["design_id"],
            "quality_q05_absolute_difference": abs(float(record.get("quality_margin", {}).get("q05", float("nan"))) - float(l0_record["quality_margin"]["q05"])),
            "risk_q95_absolute_difference": abs(float(record.get("enabled_risk", {}).get("q95", float("nan"))) - float(l0_record["enabled_risk"]["q95"])),
            "grid_converged": grid_converged,
            "l1_status": record["status"],
            "l1_constraints": record["constraints"],
            "l1_quality_margin": record.get("quality_margin"),
            "l1_enabled_risk": record.get("enabled_risk"),
        })
    ranked = [record for record in refined if record["constraints"].get("all_hard_constraints")]
    ranked.sort(key=lambda record: sum(float(value) for value in record["objectives"]))
    if ranked:
        objective_array = np.asarray([record["objectives"] for record in ranked], dtype=float)
        mask = nondominated_mask(objective_array, np.ones(len(ranked), dtype=bool))
        pareto = [record for record, keep in zip(ranked, mask) if keep]
    else:
        pareto = []
    rank_stability: dict[str, Any]
    if len(refined) >= 2:
        l0_quality = [next(record for record in feasible_records if record["design_id"] == item["design_id"])["quality_margin"]["q05"] for item in refined]
        l1_quality = [item.get("quality_margin", {}).get("q05", float("nan")) for item in refined]
        coefficient = float(spearmanr(l0_quality, l1_quality).statistic)
        if np.isfinite(coefficient):
            rank_stability = {"status": "stable" if coefficient >= 0.5 else "unstable", "spearman_quality_rank": coefficient, "design_count": len(refined)}
        else:
            rank_stability = {"status": "insufficient_points", "spearman_quality_rank": None, "design_count": len(refined), "reason": "constant or undefined ranks"}
    else:
        rank_stability = {"status": "insufficient_points", "design_count": len(refined)}
    active = sorted({
        name
        for record in ranked
        for name, value in record["constraints"].items()
        if name not in {"all_hard_constraints", "environmental_threshold"} and value is True
    })
    status = "success" if len(ranked) >= 2 else ("partial_refinement" if ranked else "no_l1_feasible_designs")
    warnings = [
        "Inverse output is a robust synthetic screening set, not a unique optimum or plant recipe.",
        "Policy-distribution quantiles are not empirical confidence intervals.",
        "Environmental thresholds are absent and therefore not_evaluated, never passed.",
        "Any real recipe, speed window, trial or control connection requires independent validation and human approval.",
    ]
    return InverseResult(status, seed, budget, all_evaluations, feasible_records, pareto, ranked, rank_stability, active, disagreement, "not_evaluated", warnings, _design_space(case))


def _design_space(case: CaseConfig) -> dict[str, Any]:
    bounds = case.raw["inverse_design"]
    return {
        "sludge_dry_mass_fraction": bounds["sludge_dry_mass_fraction_bounds"],
        "sludge_free_moisture_wet_basis": bounds["sludge_free_moisture_bounds"],
        "speed_ratio": bounds["speed_ratio_bounds"],
        "sludge_component_simplex": {"organic": [0.12, 0.35], "calcite": [0.04, 0.18], "amorphous": [0.12, 0.35], "remaining_minerals": "positive fixed-ratio partition"},
        "particle_size": {"d50_m": [1e-5, 1.2e-4], "ordering": "d10=0.2*d50 < d50 < d90=5*d50"},
        "morphology": {"sphericity": [0.4, 0.95], "aspect_ratio": "1+4*(1-sphericity)"},
        "realizability": "simplex, PSD ordering, morphology, moisture and human-declared synthetic speed bounds enforced before simulation",
    }
