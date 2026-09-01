from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from scipy.stats import spearmanr

from ..models import simulate
from ..types import CaseConfig

METRICS = (
    "bulk_density_kg_m3",
    "open_porosity",
    "linear_shrinkage",
    "water_absorption_proxy_percent",
    "strength_proxy_Pa",
    "cracking_risk",
    "bloating_risk",
    "thermo_coverage_score",
)


@dataclass
class UncertaintyResult:
    fidelity: str
    sample_count: int
    statistics: dict[str, dict[str, float]]
    failure_rate: float
    failures: list[dict[str, Any]]
    sensitivity: dict[str, Any]
    model_discrepancy: dict[str, Any]
    policy_notice: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "fidelity": self.fidelity,
            "sample_count": self.sample_count,
            "statistics": self.statistics,
            "failure_rate": self.failure_rate,
            "failures": self.failures,
            "sensitivity": self.sensitivity,
            "model_discrepancy": self.model_discrepancy,
            "policy_notice": self.policy_notice,
        }


def propagate(case: CaseConfig, fidelity: Literal["L0", "L1"], samples: list[dict[str, float]]) -> UncertaintyResult:
    if not samples:
        raise ValueError("at least one parameter sample is required")
    successes: list[tuple[dict[str, float], Any]] = []
    failures: list[dict[str, Any]] = []
    for index, sample in enumerate(samples):
        result = simulate(case, fidelity, sample)
        if result.status.success:
            successes.append((sample, result))
        else:
            failures.append({"sample_index": index, "status": result.status.code, "message": result.status.message})
    statistics: dict[str, dict[str, float]] = {}
    if successes:
        for metric in METRICS:
            values = np.array([float(result.summary[metric]["value"]) for _, result in successes], dtype=float)
            statistics[metric] = {
                "min": float(np.min(values)),
                "q05": float(np.quantile(values, 0.05)),
                "q50": float(np.quantile(values, 0.50)),
                "q95": float(np.quantile(values, 0.95)),
                "max": float(np.max(values)),
            }
    sensitivity: dict[str, Any] = {}
    if len(successes) >= 3:
        output = np.array([float(result.summary["open_porosity"]["value"]) for _, result in successes])
        for name in samples[0]:
            if name == "grid_check":
                continue
            inputs = np.array([float(sample[name]) for sample, _ in successes])
            if np.ptp(inputs) == 0.0:
                sensitivity[name] = {"status": "unresolved_constant_input", "spearman": None}
            else:
                coefficient = spearmanr(inputs, output).statistic
                sensitivity[name] = {"status": "resolved", "spearman": float(coefficient)}
    else:
        sensitivity["status"] = "unresolved_insufficient_samples"
    return UncertaintyResult(
        fidelity,
        len(samples),
        statistics,
        len(failures) / len(samples),
        failures,
        sensitivity,
        {"status": "reported_separately", "one_dimensional_model_form_interval": [-1.0, 1.0], "combined_with_parameter_quantiles": False},
        "Bounds and policy distributions are sampling policies, not measured probability distributions or confidence intervals.",
    )
