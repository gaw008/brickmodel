from __future__ import annotations

from typing import Any


def quality_margin(summary: dict[str, Any], targets: dict[str, Any]) -> float:
    margins: list[float] = []
    two_sided = {
        "bulk_density_kg_m3": "bulk_density_kg_m3",
        "open_porosity": "open_porosity",
        "linear_shrinkage": "linear_shrinkage",
    }
    for metric, target in two_sided.items():
        value = float(summary[metric]["value"])
        lower, upper = float(targets[target]["min"]), float(targets[target]["max"])
        margins.extend([(value - lower) / max(upper - lower, 1e-12), (upper - value) / max(upper - lower, 1e-12)])
    absorption = float(summary["water_absorption_proxy_percent"]["value"])
    margins.append((float(targets["water_absorption_proxy_percent"]["max"]) - absorption) / float(targets["water_absorption_proxy_percent"]["max"]))
    strength = float(summary["strength_proxy_Pa"]["value"])
    margins.append((strength - float(targets["strength_proxy_Pa"]["min"])) / float(targets["strength_proxy_Pa"]["min"]))
    return min(margins)


def constraint_record(result, q05_quality: float, q95_risk: float, *, grid_converged: bool | None = None) -> dict[str, Any]:
    constraints = {
        "forward_success": bool(result.status.success),
        "mass_conservation": bool(result.conservation.get("mass_relative_residual", float("inf")) < 1e-8),
        "element_conservation": bool(result.conservation.get("max_element_relative_residual", float("inf")) < 1e-8),
        "energy_conservation": bool(result.conservation.get("energy_relative_residual", float("inf")) < 1e-4),
        "thermo_coverage": float(result.summary["thermo_coverage_score"]["value"]) >= 0.70,
        "q05_synthetic_quality_margin": q05_quality >= 0.0,
        "q95_enabled_risk": q95_risk <= 1.0,
        "grid_convergence": True if grid_converged is None else grid_converged,
        "environmental_threshold": "not_evaluated",
    }
    constraints["all_hard_constraints"] = all(bool(value) for key, value in constraints.items() if key != "environmental_threshold")
    return constraints
