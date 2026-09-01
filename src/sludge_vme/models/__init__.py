from __future__ import annotations

from typing import Literal

from ..types import CaseConfig, ForwardResult, RunStatus
from ..validation import validate_case
from .common import build_context
from .l0 import run_l0
from .l1 import run_l1


def simulate(case: CaseConfig, fidelity: Literal["L0", "L1"], parameters: dict | None = None) -> ForwardResult:
    report = validate_case(case)
    if not report.valid:
        return ForwardResult(
            fidelity,
            RunStatus("validation_failure", "; ".join(f"{item.path}: {item.message}" for item in report.errors), False),
            {}, {}, {}, {}, ["validation_failure"], [], {"case_hash": case.content_hash}, {},
        )
    if fidelity not in {"L0", "L1"}:
        raise ValueError("fidelity must be L0 or L1")
    context = build_context(case, parameters)
    if fidelity == "L0":
        result = run_l0(context)
        result.provenance["parameter_invocation"] = (
            "model_defaults" if parameters is None else "explicit_overrides"
        )
        return result
    cells = int((parameters or {}).get("cells", 21))
    result = run_l1(context, cells)
    if (parameters or {}).get("grid_check", parameters is None) and cells == 21 and result.status.success:
        refined = run_l1(context, 41)
        metrics = ("open_porosity", "linear_shrinkage", "max_center_surface_temperature_difference_K")
        differences = {}
        for metric in metrics:
            coarse_value = float(result.summary[metric]["value"])
            fine_value = float(refined.summary[metric]["value"])
            differences[metric] = abs(coarse_value - fine_value) / max(abs(fine_value), 1e-8)
        converged = refined.status.success and differences["open_porosity"] < 0.05 and differences["linear_shrinkage"] < 0.08 and differences["max_center_surface_temperature_difference_K"] < 0.12
        result.solver_statistics["grid_convergence"] = {"cells": [21, 41], "relative_differences": differences, "converged": converged, "refined_status": refined.status.code}
        if not converged:
            result.flags.append("fidelity_warning")
            result.warnings.append("21/41-cell convergence tolerance was not met; this point must not be treated as inverse-feasible at L1.")
    result.provenance["parameter_invocation"] = (
        "model_defaults" if parameters is None else "explicit_overrides"
    )
    return result


__all__ = ["simulate"]
