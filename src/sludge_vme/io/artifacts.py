from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import uuid
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


def _begin_atomic_output(out: Path | str, overwrite: bool) -> tuple[Path, Path, dict[str, Any]]:
    target = Path(out).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target_is_nonempty = target.exists() and (not target.is_dir() or any(target.iterdir()))
    if target_is_nonempty and not overwrite:
        raise FileExistsError(f"output directory is nonempty: {target}; pass --overwrite explicitly")
    nonce = uuid.uuid4().hex
    temporary = target.parent / f".{target.name}.tmp-{nonce}"
    temporary.mkdir()
    rollback = target.parent / f".{target.name}.rollback-{nonce}" if target_is_nonempty else None
    transaction = {
        "write_strategy": "temporary_directory_then_atomic_rename",
        "overwrite_requested": bool(overwrite),
        "rollback_directory": str(rollback) if rollback is not None else None,
        "manifest_self_hash": "not_applicable_self_reference",
    }
    return target, temporary, transaction


def _finish_atomic_output(target: Path, temporary: Path, transaction: dict[str, Any]) -> Path:
    rollback_value = transaction["rollback_directory"]
    rollback = Path(rollback_value) if rollback_value is not None else None
    if target.exists():
        if rollback is not None:
            os.replace(target, rollback)
        elif target.is_dir():
            target.rmdir()
        else:
            raise FileExistsError(f"refusing to replace existing output file: {target}")
    try:
        os.replace(temporary, target)
    except Exception:
        if rollback is not None and rollback.exists() and not target.exists():
            os.replace(rollback, target)
        raise
    return target


def _artifact_inventory(directory: Path) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name == "run_manifest.json":
            continue
        payload = path.read_bytes()
        inventory[path.name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    return inventory


def write_forward_run(out: Path | str, case: CaseConfig, result: ForwardResult, *, cli_args: list[str], seed: int, uncertainty: Any | None = None, overwrite: bool = False) -> Path:
    target, directory, transaction = _begin_atomic_output(out, overwrite)
    _write_json(directory / "resolved_case.json", case.raw)
    _write_json(directory / "status.json", result.status)
    _write_json(directory / "summary.json", result.summary)
    _write_json(directory / "conservation.json", result.conservation)
    _write_json(directory / "flags.json", {"flags": result.flags, "warnings": result.warnings})
    _write_json(directory / "state_trajectory.json", {"coordinates": result.coordinates, "fields": result.fields})
    _write_json(directory / "uncertainty.json", uncertainty.as_dict() if uncertainty is not None else {"status": "not_requested", "notice": "No uncertainty run requested; interval metadata remain in the parameter pack."})
    manifest = build_manifest(
        root=_root(), case_hash=case.content_hash, parameter_pack_hash=result.provenance.get("parameter_pack_hash", "unavailable"),
        cli_args=cli_args, seed=seed, run_type="forward", fidelity=result.fidelity,
    )
    manifest["solver_statistics"] = result.solver_statistics
    manifest["output_transaction"] = transaction
    _write_trajectory_csv(directory / "state_trajectory.csv", result)
    (directory / "report.md").write_text(_forward_markdown(result), encoding="utf-8")
    manifest["artifacts"] = _artifact_inventory(directory)
    _write_json(directory / "run_manifest.json", manifest)
    return _finish_atomic_output(target, directory, transaction)


def _write_trajectory_csv(path: Path, result: ForwardResult) -> None:
    if not result.coordinates or not result.fields:
        path.write_text("time_s,x_m,temperature_K\n", encoding="utf-8")
        return
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
        if name not in result.summary:
            continue
        item = result.summary[name]
        lines.append(f"- `{name}`: {item['value']} {item['unit']} (status={item['status']}, proxy={item['proxy']})")
    lines.extend(["", "## Conservation", "", f"```json\n{json.dumps(_jsonable(result.conservation), indent=2)}\n```", "", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in result.warnings)
    lines.append("")
    return "\n".join(lines)


def write_inverse_run(out: Path | str, case: CaseConfig, result: Any, *, cli_args: list[str], seed: int, overwrite: bool = False) -> Path:
    target, directory, transaction = _begin_atomic_output(out, overwrite)
    l0_design_count = sum(item.get("fidelity") == "L0" for item in result.all_evaluations)
    _write_json(directory / "resolved_case.json", case.raw)
    _write_json(directory / "status.json", {"code": result.status, "success": result.status == "success"})
    _write_json(directory / "summary.json", {"status": result.status, "evaluated_designs": l0_design_count, "evaluation_records": len(result.all_evaluations), "l0_feasible_designs": len(result.feasible_set), "l1_ranked_candidates": len(result.ranked_candidates), "pareto_candidates": len(result.pareto_set), "environmental_status": result.environmental_status})
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
    manifest["output_transaction"] = transaction
    (directory / "report.md").write_text(_inverse_markdown(result), encoding="utf-8")
    manifest["artifacts"] = _artifact_inventory(directory)
    _write_json(directory / "run_manifest.json", manifest)
    return _finish_atomic_output(target, directory, transaction)


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
    return {
        "status": "observed_candidate_envelope",
        "windows": {name: {"min": min(float(item["decision"][name]) for item in candidates), "max": max(float(item["decision"][name]) for item in candidates)} for name in names},
        "candidate_count": len(candidates),
        "continuity_validated": False,
        "not_for_production": True,
    }


def _inverse_markdown(result: Any) -> str:
    l0_design_count = sum(item.get("fidelity") == "L0" for item in result.all_evaluations)
    lines = [
        "# Synthetic inverse-design report", "",
        "> RESEARCH-ONLY SYNTHETIC OUTPUT. Candidates are not plant recipes, approved speed windows, standards, or guaranteed optima.", "",
        f"Status: `{result.status}`", "",
        f"Evaluated L0 designs: {l0_design_count}", f"Evaluation records including L1: {len(result.all_evaluations)}", f"L0 feasible: {len(result.feasible_set)}", f"L1 ranked: {len(result.ranked_candidates)}", f"Final nondominated: {len(result.pareto_set)}", "",
        "## Ranked candidates", "",
    ]
    for rank, item in enumerate(result.ranked_candidates, start=1):
        lines.append(f"{rank}. design `{item['design_id']}` — q05 margin={item['quality_margin']['q05']:.6g}, q95 risk={item['enabled_risk']['q95']:.6g}, decision={json.dumps(item['decision'], sort_keys=True)}")
    lines.extend(["", "## Uncertainty and warnings", ""])
    lines.extend(f"- {warning}" for warning in result.warnings)
    lines.append("")
    return "\n".join(lines)


def _finite_json_tree(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, list):
        return all(_finite_json_tree(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_json_tree(item) for key, item in value.items())
    return False


def _check_artifact_inventory(directory: Path, manifest: dict[str, Any], errors: list[str], checks: dict[str, bool]) -> None:
    declared = manifest.get("artifacts")
    actual_names = {path.name for path in directory.iterdir() if path.is_file() and path.name != "run_manifest.json"}
    checks["artifact_inventory_complete"] = isinstance(declared, dict) and set(declared) == actual_names
    if not checks["artifact_inventory_complete"]:
        errors.append("artifact inventory does not exactly match run payload files")
        return
    hashes_ok = True
    sizes_ok = True
    for name in sorted(actual_names):
        path = directory / name
        payload = path.read_bytes()
        record = declared.get(name, {})
        expected_hash = record.get("sha256") if isinstance(record, dict) else None
        expected_size = record.get("size_bytes") if isinstance(record, dict) else None
        if expected_hash != hashlib.sha256(payload).hexdigest():
            hashes_ok = False
            errors.append(f"artifact hash mismatch: {name}")
        if expected_size != len(payload):
            sizes_ok = False
            errors.append(f"artifact size mismatch: {name}")
    checks["artifact_hashes"] = hashes_ok
    checks["artifact_sizes"] = sizes_ok


def _safe_json(directory: Path, name: str, errors: list[str]) -> Any | None:
    try:
        value = json.loads((directory / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON artifact {name}: {exc}")
        return None
    if not _finite_json_tree(value):
        errors.append(f"non-finite or unsupported JSON value in {name}")
        return None
    return value


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
    manifest = _safe_json(directory, "run_manifest.json", errors)
    resolved = _safe_json(directory, "resolved_case.json", errors)
    status = _safe_json(directory, "status.json", errors)
    if not isinstance(manifest, dict) or not isinstance(resolved, dict) or not isinstance(status, dict):
        return VerifyResult(False, errors, warnings, checks)
    _check_artifact_inventory(directory, manifest, errors, checks)
    checks["resolved_case_hash"] = sha256_json(resolved) == manifest.get("resolved_case_hash")
    if not checks["resolved_case_hash"]:
        errors.append("resolved case hash mismatch")
    run_type = manifest.get("run_type")
    if run_type == "forward":
        for name in ("conservation.json", "state_trajectory.json", "state_trajectory.csv", "uncertainty.json"):
            if not (directory / name).is_file():
                errors.append(f"missing forward artifact: {name}")
        conservation = _safe_json(directory, "conservation.json", errors)
        summary = _safe_json(directory, "summary.json", errors)
        trajectory = _safe_json(directory, "state_trajectory.json", errors)
        if not isinstance(conservation, dict) or not isinstance(summary, dict) or not isinstance(trajectory, dict):
            return VerifyResult(False, errors, warnings, checks)
        checks["mass_conservation"] = conservation.get("mass_relative_residual", float("inf")) < 1e-8
        checks["element_conservation"] = conservation.get("max_element_relative_residual", float("inf")) < 1e-8
        checks["reduced_effective_enthalpy_ode_numerics"] = conservation.get("reduced_effective_enthalpy_ode_relative_residual", float("inf")) < 1e-4
        checks["oxygen_stoichiometric_cap"] = conservation.get("oxygen_stoichiometric_cap_satisfied") is True
        for name in ("mass_conservation", "element_conservation", "reduced_effective_enthalpy_ode_numerics", "oxygen_stoichiometric_cap"):
            if not checks[name]:
                errors.append(f"failed check: {name}")
        if strict and not status.get("success", False):
            errors.append(f"forward status is not success: {status.get('code')}")
        if status.get("success", False):
            fields = trajectory.get("fields", {})
            coordinates = trajectory.get("coordinates", {})
            try:
                temperature = np.asarray(fields["temperature"]["values"], dtype=float)
                total_porosity = np.asarray(fields["total_porosity"]["values"], dtype=float)
                open_porosity = np.asarray(fields["open_porosity"]["values"], dtype=float)
                volume_ratio = np.asarray(fields["volume_ratio"]["values"], dtype=float)
                liquid_fraction = np.asarray(fields["liquid_fraction"]["values"], dtype=float)
                reaction_extents = [
                    np.asarray(item["values"], dtype=float)
                    for item in fields["reaction_extents"].values()
                ]
                reference_gases = [
                    np.asarray(item["values"], dtype=float)
                    for item in fields["gas_concentrations"].values()
                ]
                current_pore_gases = [
                    np.asarray(item["values"], dtype=float)
                    for item in fields["gas_current_pore_concentrations"].values()
                ]
                gas_overpressure = np.asarray(fields["gas_overpressure"]["values"], dtype=float)
                times = np.asarray(coordinates["time_s"], dtype=float)
                density = float(summary["bulk_density_kg_m3"]["value"])
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"forward semantic structure invalid: {exc}")
            else:
                checks["physical_state_bounds"] = bool(
                    temperature.size > 0
                    and temperature.ndim >= 1
                    and total_porosity.ndim >= 1
                    and open_porosity.ndim >= 1
                    and volume_ratio.ndim >= 1
                    and liquid_fraction.ndim >= 1
                    and np.all((temperature > 0.0) & (temperature < 5000.0))
                    and np.all((total_porosity >= 0.0) & (total_porosity <= 1.0))
                    and np.all((open_porosity >= 0.0) & (open_porosity <= 1.0))
                    and np.all(volume_ratio > 0.0)
                    and np.all((liquid_fraction >= 0.0) & (liquid_fraction <= 1.0))
                    and all(
                        array.ndim >= 1
                        and array.shape[0] == len(times)
                        and np.all((array >= -1e-5) & (array <= 1.0 + 1e-5))
                        for array in reaction_extents
                    )
                    and all(
                        array.ndim >= 1 and array.shape[0] == len(times) and np.all(array >= -1e-8)
                        for array in [*reference_gases, *current_pore_gases]
                    )
                    and gas_overpressure.ndim >= 1
                    and gas_overpressure.shape[0] == len(times)
                    and np.all(gas_overpressure >= -1e-6)
                    and times.ndim == 1
                    and len(times) == temperature.shape[0]
                )
                if not checks["physical_state_bounds"]:
                    errors.append("trajectory violates finite physical state bounds or coordinate shape")
                checks["positive_bulk_density"] = density > 0.0
                if not checks["positive_bulk_density"]:
                    errors.append("bulk_density_kg_m3 must be positive")
                if checks["physical_state_bounds"]:
                    final_open = float(np.mean(open_porosity[-1]))
                    final_liquid = float(np.mean(liquid_fraction[-1]))
                    checks["summary_trajectory_consistency"] = bool(
                        math.isclose(final_open, float(summary["open_porosity"]["value"]), rel_tol=1e-10, abs_tol=1e-12)
                        and math.isclose(final_liquid, float(summary["liquid_fraction"]["value"]), rel_tol=1e-10, abs_tol=1e-12)
                    )
                    if not checks["summary_trajectory_consistency"]:
                        errors.append("summary does not match final trajectory state")
                else:
                    checks["summary_trajectory_consistency"] = False
        if strict and manifest.get("fidelity") == "L1":
            grid = manifest.get("solver_statistics", {}).get("grid_convergence")
            if not grid or not grid.get("converged"):
                errors.append("strict L1 verification requires converged 21/41 grid check")
    elif run_type == "inverse":
        for name in ("pareto.json", "pareto.csv", "all_evaluations.jsonl", "rank_stability.json", "feasible_windows.json"):
            if not (directory / name).is_file():
                errors.append(f"missing inverse artifact: {name}")
        pareto = _safe_json(directory, "pareto.json", errors)
        inverse_summary = _safe_json(directory, "summary.json", errors)
        if not isinstance(pareto, list) or not isinstance(inverse_summary, dict):
            return VerifyResult(False, errors, warnings, checks)
        all_evaluations: list[dict[str, Any]] = []
        try:
            for line in (directory / "all_evaluations.jsonl").read_text(encoding="utf-8").splitlines():
                item = json.loads(line)
                if not isinstance(item, dict) or not _finite_json_tree(item):
                    raise ValueError("evaluation must be a finite JSON object")
                all_evaluations.append(item)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid all_evaluations.jsonl: {exc}")
        checks["pareto_constraints"] = all(item.get("constraints", {}).get("all_hard_constraints") is True for item in pareto)
        checks["pareto_traceability"] = all(
            any(candidate == evaluation for evaluation in all_evaluations)
            for candidate in pareto
        )
        l0_design_count = sum(item.get("fidelity") == "L0" for item in all_evaluations)
        checks["inverse_summary_counts"] = (
            inverse_summary.get("evaluated_designs") == l0_design_count
            and inverse_summary.get("evaluation_records") == len(all_evaluations)
            and inverse_summary.get("pareto_candidates") == len(pareto)
        )
        if pareto:
            objectives = np.asarray([item["objectives"] for item in pareto], dtype=float)
            checks["pareto_nondominated"] = bool(nondominated_mask(objectives, np.ones(len(pareto), dtype=bool)).all())
        else:
            checks["pareto_nondominated"] = True
            warnings.append("Pareto set is empty")
        if strict and status.get("code") != "success":
            errors.append(f"inverse status is not success: {status.get('code')}")
        for name in ("pareto_constraints", "pareto_traceability", "inverse_summary_counts", "pareto_nondominated"):
            if not checks[name]:
                errors.append(f"failed check: {name}")
    else:
        errors.append(f"unknown run_type: {run_type!r}")
    return VerifyResult(not errors, errors, warnings, checks)
