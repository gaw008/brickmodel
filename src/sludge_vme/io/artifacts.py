from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..config import sha256_json
from ..inverse.pareto import nondominated_mask
from ..types import CaseConfig, ForwardResult
from .manifest import build_manifest


@dataclass
class VerifyResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    checks: dict[str, bool]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_jsonable(value), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def write_forward_run(out: Path | str, case: CaseConfig, result: ForwardResult, *, cli_args: list[str], seed: int, uncertainty: Any | None = None) -> Path:
    directory = Path(out).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(directory / "resolved_case.json", case.raw)
    _write_json(directory / "status.json", result.status)
    _write_json(directory / "summary.json", result.summary)
    _write_json(directory / "conservation.json", result.conservation)
    _write_json(directory / "flags.json", {"flags": result.flags, "warnings": result.warnings})
    _write_json(directory / "state_trajectory.json", {"coordinates": result.coordinates, "fields": result.fields})
    _write_json(directory / "uncertainty.json", uncertainty.as_dict() if uncertainty is not None else {"status": "not_requested", "notice": "No uncertainty run requested; interval metadata remain in the parameter pack."})
    manifest = build_manifest(
        root=_root(), case_hash=case.content_hash, parameter_pack_hash=result.provenance["parameter_pack_hash"],
        cli_args=cli_args, seed=seed, run_type="forward", fidelity=result.fidelity,
    )
    manifest["solver_statistics"] = result.solver_statistics
    _write_json(directory / "run_manifest.json", manifest)
    _write_trajectory_csv(directory / "state_trajectory.csv", result)
    (directory / "report.md").write_text(_forward_markdown(result), encoding="utf-8")
    return directory


def _write_trajectory_csv(path: Path, result: ForwardResult) -> None:
    times = result.coordinates["time_s"]
    x_values = result.coordinates["x_m"]
    temperatures = result.fields["temperature"]["values"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_s", "x_m", "temperature_K", "total_porosity", "open_porosity", "liquid_fraction", *[f"extent_{name}" for name in result.fields["reaction_extents"]]])
        writer.writeheader()
        for time_index, time_s in enumerate(times):
            temp_row = temperatures[time_index] if isinstance(temperatures[time_index], list) else [temperatures[time_index]]
            for cell_index, temperature in enumerate(temp_row):
                row = {
                    "time_s": time_s,
                    "x_m": x_values[cell_index],
                    "temperature_K": temperature,
                    "total_porosity": _field_cell(result.fields["total_porosity"]["values"], time_index, cell_index),
                    "open_porosity": _field_cell(result.fields["open_porosity"]["values"], time_index, cell_index),
                    "liquid_fraction": _field_cell(result.fields["liquid_fraction"]["values"], time_index, cell_index),
                }
                for name, field in result.fields["reaction_extents"].items():
                    row[f"extent_{name}"] = _field_cell(field["values"], time_index, cell_index)
                writer.writerow(row)


def _field_cell(values: list, time_index: int, cell_index: int):
    row = values[time_index]
    return row[cell_index] if isinstance(row, list) else row


def _forward_markdown(result: ForwardResult) -> str:
    lines = [
        f"# Synthetic forward report — {result.fidelity}", "",
        "> RESEARCH-ONLY SYNTHETIC OUTPUT. Not a plant result, product certificate, compliance result, or production-control instruction.", "",
        f"Status: `{result.status.code}`", "",
        "## Selected fingerprint", "",
    ]
    for name in ("bulk_density_kg_m3", "open_porosity", "linear_shrinkage", "water_absorption_proxy_percent", "strength_proxy_Pa", "liquid_fraction", "max_overpressure_Pa", "cracking_risk", "bloating_risk", "thermo_coverage_score", "environmental_status"):
        item = result.summary[name]
        lines.append(f"- `{name}`: {item['value']} {item['unit']} (status={item['status']}, proxy={item['proxy']})")
    lines.extend(["", "## Conservation", "", f"```json\n{json.dumps(_jsonable(result.conservation), indent=2)}\n```", "", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in result.warnings)
    lines.append("")
    return "\n".join(lines)


def write_inverse_run(out: Path | str, case: CaseConfig, result: Any, *, cli_args: list[str], seed: int) -> Path:
    directory = Path(out).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(directory / "resolved_case.json", case.raw)
    _write_json(directory / "status.json", {"code": result.status, "success": result.status == "success"})
    _write_json(directory / "summary.json", {"status": result.status, "evaluated_designs": len(result.all_evaluations), "l0_feasible_designs": len(result.feasible_set), "l1_ranked_candidates": len(result.ranked_candidates), "pareto_candidates": len(result.pareto_set), "environmental_status": result.environmental_status})
    _write_json(directory / "flags.json", {"warnings": result.warnings, "flags": ["synthetic_demo", "research_only", "environmental_threshold_missing", "thermo_database_gap"]})
    _write_json(directory / "pareto.json", result.pareto_set)
    _write_json(directory / "rank_stability.json", result.rank_stability)
    _write_json(directory / "feasible_windows.json", _feasible_windows(result.ranked_candidates))
    _write_json(directory / "uncertainty.json", {"rank_stability": result.rank_stability, "l0_l1_disagreement": result.l0_l1_disagreement, "notice": "Policy quantiles are not empirical confidence intervals."})
    with (directory / "all_evaluations.jsonl").open("w", encoding="utf-8") as handle:
        for item in result.all_evaluations:
            handle.write(json.dumps(_jsonable(item), sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    _write_pareto_csv(directory / "pareto.csv", result.pareto_set)
    parameter_hash = result.ranked_candidates[0]["source_hashes"]["parameter_pack"] if result.ranked_candidates else "unavailable"
    manifest = build_manifest(root=_root(), case_hash=case.content_hash, parameter_pack_hash=parameter_hash, cli_args=cli_args, seed=seed, run_type="inverse", budget=result.budget)
    manifest["design_space"] = result.design_space
    _write_json(directory / "run_manifest.json", manifest)
    (directory / "report.md").write_text(_inverse_markdown(result), encoding="utf-8")
    return directory


def _write_pareto_csv(path: Path, candidates: list[dict[str, Any]]) -> None:
    decision_names = sorted({name for item in candidates for name in item["decision"]})
    fields = ["rank", "design_id", "fidelity", "quality_q05", "risk_q95", "uncertainty_width", *decision_names]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, item in enumerate(candidates, start=1):
            writer.writerow({
                "rank": rank, "design_id": item["design_id"], "fidelity": item["fidelity"],
                "quality_q05": item["quality_margin"]["q05"], "risk_q95": item["enabled_risk"]["q95"],
                "uncertainty_width": item["uncertainty_width"], **item["decision"],
            })


def _feasible_windows(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {"status": "empty", "windows": {}, "reason": "No L1 robust-feasible candidates"}
    names = sorted(candidates[0]["decision"])
    return {"status": "resolved_synthetic_shortlist", "windows": {name: {"min": min(float(item["decision"][name]) for item in candidates), "max": max(float(item["decision"][name]) for item in candidates)} for name in names}, "candidate_count": len(candidates), "not_for_production": True}


def _inverse_markdown(result: Any) -> str:
    lines = [
        "# Synthetic inverse-design report", "",
        "> RESEARCH-ONLY SYNTHETIC OUTPUT. Candidates are not plant recipes, approved speed windows, standards, or guaranteed optima.", "",
        f"Status: `{result.status}`", "",
        f"Evaluated L0 designs: {len(result.all_evaluations)}", f"L0 feasible: {len(result.feasible_set)}", f"L1 ranked: {len(result.ranked_candidates)}", f"Final nondominated: {len(result.pareto_set)}", "",
        "## Ranked candidates", "",
    ]
    for rank, item in enumerate(result.ranked_candidates, start=1):
        lines.append(f"{rank}. design `{item['design_id']}` — q05 margin={item['quality_margin']['q05']:.6g}, q95 risk={item['enabled_risk']['q95']:.6g}, decision={json.dumps(item['decision'], sort_keys=True)}")
    lines.extend(["", "## Uncertainty and warnings", ""])
    lines.extend(f"- {warning}" for warning in result.warnings)
    lines.append("")
    return "\n".join(lines)


def verify_run(run_dir: Path | str, strict: bool = False) -> VerifyResult:
    directory = Path(run_dir).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}
    common = ["run_manifest.json", "resolved_case.json", "status.json", "summary.json", "flags.json", "report.md"]
    for name in common:
        if not (directory / name).is_file():
            errors.append(f"missing required artifact: {name}")
    if errors:
        return VerifyResult(False, errors, warnings, checks)
    try:
        manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
        resolved = json.loads((directory / "resolved_case.json").read_text(encoding="utf-8"))
        status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return VerifyResult(False, [f"invalid JSON artifact: {exc}"], warnings, checks)
    checks["resolved_case_hash"] = sha256_json(resolved) == manifest.get("resolved_case_hash")
    if not checks["resolved_case_hash"]:
        errors.append("resolved case hash mismatch")
    run_type = manifest.get("run_type")
    if run_type == "forward":
        for name in ("conservation.json", "state_trajectory.json", "state_trajectory.csv", "uncertainty.json"):
            if not (directory / name).is_file():
                errors.append(f"missing forward artifact: {name}")
        conservation = json.loads((directory / "conservation.json").read_text(encoding="utf-8"))
        checks["mass_conservation"] = conservation.get("mass_relative_residual", float("inf")) < 1e-8
        checks["element_conservation"] = conservation.get("max_element_relative_residual", float("inf")) < 1e-8
        checks["energy_conservation"] = conservation.get("energy_relative_residual", float("inf")) < 1e-4
        for name, passed in checks.items():
            if not passed:
                errors.append(f"failed check: {name}")
        if strict and not status.get("success", False):
            errors.append(f"forward status is not success: {status.get('code')}")
        if strict and manifest.get("fidelity") == "L1":
            grid = manifest.get("solver_statistics", {}).get("grid_convergence")
            if not grid or not grid.get("converged"):
                errors.append("strict L1 verification requires converged 21/41 grid check")
    elif run_type == "inverse":
        for name in ("pareto.json", "pareto.csv", "all_evaluations.jsonl", "rank_stability.json", "feasible_windows.json"):
            if not (directory / name).is_file():
                errors.append(f"missing inverse artifact: {name}")
        pareto = json.loads((directory / "pareto.json").read_text(encoding="utf-8"))
        checks["pareto_constraints"] = all(item.get("constraints", {}).get("all_hard_constraints") is True for item in pareto)
        if pareto:
            objectives = np.asarray([item["objectives"] for item in pareto], dtype=float)
            checks["pareto_nondominated"] = bool(nondominated_mask(objectives, np.ones(len(pareto), dtype=bool)).all())
        else:
            checks["pareto_nondominated"] = True
            warnings.append("Pareto set is empty")
        if strict and status.get("code") != "success":
            errors.append(f"inverse status is not success: {status.get('code')}")
        for name, passed in checks.items():
            if not passed:
                errors.append(f"failed check: {name}")
    else:
        errors.append(f"unknown run_type: {run_type!r}")
    return VerifyResult(not errors, errors, warnings, checks)
