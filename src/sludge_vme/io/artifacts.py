from __future__ import annotations

import csv
import copy
import hashlib
import json
import math
import os
import uuid
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..chemistry.formula import formula_element_moles, formula_molar_mass
from ..chemistry.stoichiometry import GAS_FORMULAS, initial_element_inventory
from ..config import sha256_json
from ..inverse.pareto import nondominated_mask
from ..inverse.search import _rank_stability
from ..models.common import GAS_MOLAR_MASS_KG_MOL, GASES, REACTIONS, R_GAS, boundary, build_context, liquid_fraction, oxygen_available_mol_m3
from ..thermo.coverage import assess_thermo_coverage
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
    _write_json(directory / "provenance.json", result.provenance)
    _write_json(directory / "flags.json", {"flags": result.flags, "warnings": result.warnings})
    _write_json(
        directory / "state_trajectory.json",
        {
            "schema_version": "2.0-independent-semantic-verification",
            "coordinates": result.coordinates,
            "fields": result.fields,
            "state_counts": {
                "time_points": len(result.coordinates.get("time_s", [])),
                "cells": len(result.coordinates.get("x_m", [])),
                "reaction_species": len(result.fields.get("reaction_extents", {})),
                "gas_species": len(result.fields.get("gas_concentrations", {})),
            },
            "transport_contract": {
                "species": list(result.fields.get("gas_molar_inventories", {})),
                "molar_masses_kg_mol": {
                    name: field.get("molar_mass_kg_mol")
                    for name, field in result.fields.get("gas_molar_inventories", {}).items()
                },
                "storage": "mol/m3_reference_bulk conservative molar inventory (with explicit kg/mol mass mapping)",
                "driving_concentration": "mol/m3_current_pore",
                "geometry": "current phi_open and J with isotropic reference/current area mapping",
            },
        },
    )
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


def _safe_exception_summary(exc: Exception) -> str:
    message = " ".join(str(exc).split())[:240]
    sensitive_markers = (
        "api_key",
        "authorization",
        "bearer ",
        "connection string",
        "oauth",
        "password",
        "refresh_token",
        "secret",
        "token=",
    )
    if any(marker in message.lower() for marker in sensitive_markers):
        return "[REDACTED]"
    return message or "runtime exception without a message"


def write_structured_failure(
    out: Path | str,
    case: CaseConfig,
    exc: Exception,
    *,
    stage: str,
    cli_args: list[str],
    seed: int,
    overwrite: bool = False,
    fidelity: str | None = None,
    budget: str | None = None,
) -> Path:
    """Atomically record a solver failure without clobbering occupied output."""
    requested = Path(out).resolve()
    requested.parent.mkdir(parents=True, exist_ok=True)
    occupied = requested.exists() and (not requested.is_dir() or any(requested.iterdir()))
    preserved = bool(occupied and not overwrite)
    target_out = requested.parent / f".{requested.name}.failure-{uuid.uuid4().hex}" if preserved else requested
    target, directory, transaction = _begin_atomic_output(target_out, overwrite and not preserved)
    exception = {"class": type(exc).__name__, "summary": _safe_exception_summary(exc)}
    status = {
        "code": "solver_exception",
        "success": False,
        "stage": stage,
        "reason": "solver_runtime_exception",
        "exception": exception,
    }
    provenance = {
        "case_hash": case.content_hash,
        "spec_version": case.raw.get("spec_version") if isinstance(case.raw, dict) else None,
        "stage": stage,
        "requested_output": str(requested),
        "actual_failure_output": str(target),
        "requested_output_preserved": preserved,
        "output_transaction": transaction,
        "network_used_by_solver": False,
        "paid_services": False,
        "production_control_side_effects": False,
    }
    _write_json(directory / "resolved_case.json", case.raw)
    _write_json(directory / "status.json", status)
    _write_json(directory / "provenance.json", provenance)
    _write_json(directory / "flags.json", {"flags": ["solver_exception", "no_physical_result"], "warnings": []})
    (directory / "report.md").write_text(
        "# Structured solver failure\n\n"
        "> No physical or optimization result was produced.\n\n"
        f"- stage: `{stage}`\n"
        f"- exception class: `{exception['class']}`\n"
        f"- safe summary: `{exception['summary']}`\n",
        encoding="utf-8",
    )
    manifest = build_manifest(
        root=_root(),
        case_hash=case.content_hash,
        parameter_pack_hash="unavailable_solver_exception",
        cli_args=cli_args,
        seed=seed,
        run_type="structured_failure",
        fidelity=fidelity,
        budget=budget,
    )
    manifest["failure"] = {"stage": stage, "reason": "solver_runtime_exception", "exception_class": exception["class"]}
    manifest["output_transaction"] = transaction
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


def _semantic_close(actual: Any, expected: Any, *, rtol: float = 1e-9, atol: float = 1e-13) -> bool:
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        return actual == expected and type(actual) is type(expected)
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isclose(
            float(actual), float(expected), rel_tol=rtol, abs_tol=atol
        )
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(
            _semantic_close(actual[key], value, rtol=rtol, atol=atol) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _semantic_close(a, e, rtol=rtol, atol=atol) for a, e in zip(actual, expected)
        )
    return actual == expected


def _semantic_check(
    checks: dict[str, bool], errors: list[str], name: str, actual: Any, expected: Any, *, rtol: float = 1e-9, atol: float = 1e-13
) -> bool:
    ok = _semantic_close(actual, expected, rtol=rtol, atol=atol)
    checks[name] = ok
    if not ok:
        errors.append(f"independent semantic mismatch: {name}")
    return ok


def _time_cell(values: Any, time_count: int, cell_count: int, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.shape == (time_count,) and cell_count == 1:
        return array[:, None]
    if array.shape != (time_count, cell_count):
        raise ValueError(f"{name} must have shape ({time_count}, {cell_count})")
    return array


def _forward_independent_semantics(
    directory: Path,
    manifest: dict[str, Any],
    resolved: dict[str, Any],
    status: dict[str, Any],
    summary: dict[str, Any],
    conservation: dict[str, Any],
    trajectory: dict[str, Any],
    errors: list[str],
    checks: dict[str, bool],
) -> None:
    provenance = _safe_json(directory, "provenance.json", errors)
    if not isinstance(provenance, dict):
        checks["forward_cross_artifact_semantics"] = False
        return
    try:
        fields = trajectory["fields"]
        coordinates = trajectory["coordinates"]
        times = np.asarray(coordinates["time_s"], dtype=float)
        x_values = np.asarray(coordinates["x_m"], dtype=float)
        if times.ndim != 1 or x_values.ndim != 1 or len(times) < 2 or len(x_values) < 1:
            raise ValueError("coordinates must contain at least two times and one cell")
        time_count, cell_count = len(times), len(x_values)
        if not np.all(np.diff(times) > 0.0):
            raise ValueError("time coordinate must be strictly increasing")
        temperature = _time_cell(fields["temperature"]["values"], time_count, cell_count, "temperature")
        projected_extents = np.stack(
            [_time_cell(fields["reaction_extents"][name]["values"], time_count, cell_count, f"extent {name}") for name in REACTIONS],
            axis=1,
        )
        raw_extents = np.stack(
            [_time_cell(fields["raw_reaction_extents"][name]["values"], time_count, cell_count, f"raw extent {name}") for name in REACTIONS],
            axis=1,
        )
        gas_mass = np.stack(
            [_time_cell(fields["gas_concentrations"][name]["values"], time_count, cell_count, f"gas mass {name}") for name in GASES],
            axis=1,
        )
        gas_molar = np.stack(
            [_time_cell(fields["gas_molar_inventories"][name]["values"], time_count, cell_count, f"gas molar {name}") for name in GASES],
            axis=1,
        )
        current_pore_molar = np.stack(
            [_time_cell(fields["gas_current_pore_concentrations"][name]["values"], time_count, cell_count, f"current gas {name}") for name in GASES],
            axis=1,
        )
        released_mass = np.stack(
            [np.asarray(fields["released_gas_mass_inventories"][name]["values"], dtype=float) for name in GASES],
            axis=1,
        )
        if released_mass.shape != (time_count, len(GASES)):
            raise ValueError("released gas inventory shape mismatch")
        volume_ratio = _time_cell(fields["volume_ratio"]["values"], time_count, cell_count, "volume ratio")
        total_porosity = _time_cell(fields["total_porosity"]["values"], time_count, cell_count, "total porosity")
        open_porosity = _time_cell(fields["open_porosity"]["values"], time_count, cell_count, "open porosity")
        boundary_heat = np.asarray(fields["boundary_heat_cumulative"]["values"], dtype=float)
        reaction_heat = np.asarray(fields["reaction_heat_cumulative"]["values"], dtype=float)
        if boundary_heat.shape != (time_count,) or reaction_heat.shape != (time_count,):
            raise ValueError("cumulative heat state shape mismatch")
        overrides = provenance.get("parameter_overrides")
        if not isinstance(overrides, dict):
            raise ValueError("parameter_overrides provenance must be an object")
        case = CaseConfig(resolved, directory / "resolved_case.json", sha256_json(resolved))
        ctx = build_context(case, overrides)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        checks["forward_cross_artifact_semantics"] = False
        errors.append(f"forward independent semantic inputs invalid: {exc}")
        return

    semantic_results: list[bool] = []
    expected_counts = {
        "time_points": time_count,
        "cells": cell_count,
        "reaction_species": len(REACTIONS),
        "gas_species": len(GASES),
    }
    semantic_results.append(_semantic_check(checks, errors, "trajectory_schema", trajectory.get("schema_version"), "2.0-independent-semantic-verification"))
    semantic_results.append(_semantic_check(checks, errors, "trajectory_counts", trajectory.get("state_counts"), expected_counts))
    semantic_results.append(_semantic_check(checks, errors, "provenance_case_hash", provenance.get("case_hash"), manifest.get("resolved_case_hash")))
    semantic_results.append(_semantic_check(checks, errors, "provenance_parameter_pack_hash", provenance.get("parameter_pack_hash"), manifest.get("parameter_pack_hash")))
    expected_transport = {
        "species": list(GASES),
        "molar_masses_kg_mol": GAS_MOLAR_MASS_KG_MOL,
        "storage": "mol/m3_reference_bulk conservative molar inventory (with explicit kg/mol mass mapping)",
        "driving_concentration": "mol/m3_current_pore",
        "geometry": "current phi_open and J with isotropic reference/current area mapping",
    }
    semantic_results.append(_semantic_check(checks, errors, "molar_transport_contract", trajectory.get("transport_contract"), expected_transport))

    molar_masses = np.asarray([GAS_MOLAR_MASS_KG_MOL[name] for name in GASES], dtype=float)
    expected_gas_molar = gas_mass / molar_masses[None, :, None]
    expected_current_pore = expected_gas_molar / np.maximum(open_porosity[:, None, :] * volume_ratio[:, None, :], 1e-12)
    semantic_results.append(_semantic_check(checks, errors, "mass_to_molar_inventory", gas_molar.tolist(), expected_gas_molar.tolist()))
    semantic_results.append(_semantic_check(checks, errors, "molar_to_current_pore", current_pore_molar.tolist(), expected_current_pore.tolist()))
    for name in GASES:
        expected_metadata = {
            "unit": "mol/m3_current_pore",
            "basis": "current pore volume; molar_inventory/(phi_open*J)",
            "species": name,
            "molar_mass_kg_mol": GAS_MOLAR_MASS_KG_MOL[name],
            "conversion": "mass_storage / molar_mass / (phi_open * J)",
        }
        actual_field = fields["gas_current_pore_concentrations"][name]
        actual_metadata = {key: actual_field.get(key) for key in expected_metadata}
        semantic_results.append(_semantic_check(checks, errors, f"molar_metadata_{name}", actual_metadata, expected_metadata))

    dry_loss = np.array([
        0.0,
        ctx.potentials[1].reactant_mass_kg_per_kg_dry,
        ctx.potentials[2].gas_mass_kg_per_kg_dry,
        ctx.potentials[3].gas_mass_kg_per_kg_dry,
    ])
    local_feed_loss = ctx.rho_dry * np.tensordot(projected_extents, dry_loss, axes=(1, 0))
    solid_mass_density = ctx.rho_dry - local_feed_loss
    expected_total_porosity = np.clip(1.0 - solid_mass_density / (ctx.true_density * volume_ratio), 0.0, 1.0)
    expected_open_porosity = expected_total_porosity * ctx.connectivity
    semantic_results.append(_semantic_check(checks, errors, "derived_total_porosity", total_porosity.tolist(), expected_total_porosity.tolist()))
    semantic_results.append(_semantic_check(checks, errors, "derived_open_porosity", open_porosity.tolist(), expected_open_porosity.tolist()))

    mean_raw_extents = raw_extents[-1].mean(axis=1)
    bounded_mean_extents = projected_extents[-1].mean(axis=1)
    actual_gas_density = gas_mass[-1].mean(axis=1) + released_mass[-1]
    generated_gas_density = ctx.rho_dry * (mean_raw_extents @ ctx.gas_mass_matrix)
    gas_residual = generated_gas_density - actual_gas_density
    feed_loss_density = ctx.rho_dry * float(mean_raw_extents @ dry_loss)
    water_remaining = ctx.rho_dry * ctx.water_ratio * (1.0 - mean_raw_extents[0])
    oxygen_in_density = ctx.rho_dry * mean_raw_extents[1] * ctx.potentials[1].oxygen_in_mol_O2_per_kg_dry * formula_molar_mass("O2")
    initial_mass_density = ctx.rho_dry * (1.0 + ctx.water_ratio)
    final_condensed_density = ctx.rho_dry - feed_loss_density + water_remaining
    mass_residual = initial_mass_density + oxygen_in_density - final_condensed_density - float(actual_gas_density.sum())
    mass_relative = abs(mass_residual) / max(initial_mass_density + oxygen_in_density, 1.0)
    gas_relative = float(np.max(np.abs(gas_residual))) / max(float(generated_gas_density.sum()), 1.0)

    initial_elements = {key: value * ctx.rho_dry for key, value in initial_element_inventory(case).items()}
    initial_water_moles = ctx.rho_dry * ctx.water_ratio / formula_molar_mass("H2O")
    for element, value in formula_element_moles("H2O", initial_water_moles).items():
        initial_elements[element] = initial_elements.get(element, 0.0) + value
    reactant_elements = dict(initial_elements)
    reactant_elements["O"] = reactant_elements.get("O", 0.0) + 2.0 * ctx.rho_dry * mean_raw_extents[1] * ctx.potentials[1].oxygen_in_mol_O2_per_kg_dry
    condensed_elements = dict(initial_elements)
    for index, potential in enumerate(ctx.potentials):
        for element, value in potential.feed_elements_released_mol_per_kg_dry.items():
            condensed_elements[element] = condensed_elements.get(element, 0.0) - ctx.rho_dry * mean_raw_extents[index] * value
    gas_elements: dict[str, float] = {}
    for species, mass in zip(GASES, actual_gas_density):
        for element, value in formula_element_moles(GAS_FORMULAS[species], mass / GAS_MOLAR_MASS_KG_MOL[species]).items():
            gas_elements[element] = gas_elements.get(element, 0.0) + value
    element_residual = {
        element: reactant_elements.get(element, 0.0) - condensed_elements.get(element, 0.0) - gas_elements.get(element, 0.0)
        for element in set(reactant_elements) | set(condensed_elements) | set(gas_elements)
    }
    element_relative = {
        element: abs(value) / max(abs(reactant_elements.get(element, 0.0)), 1e-12)
        for element, value in element_residual.items()
    }
    max_element = max(element_relative.values(), default=0.0)

    stored_energy = ctx.rho_dry * (1.0 + ctx.water_ratio) * ctx.cp * (float(temperature[-1].mean()) - float(temperature[0].mean()))
    supplied_energy = float(boundary_heat[-1] + reaction_heat[-1])
    reduced_enthalpy_residual = stored_energy - supplied_energy
    reduced_enthalpy_relative = abs(reduced_enthalpy_residual) / max(abs(boundary_heat[-1]) + abs(reaction_heat[-1]), 1.0)
    oxygen_available_final = oxygen_available_mol_m3(ctx, ctx.residence_time_s)
    oxygen_boundary_supplied = float(ctx.oxygen_boundary_cumulative_mol_m3[-1])
    oxygen_consumed = ctx.rho_dry * max(float(mean_raw_extents[1]), 0.0) * ctx.potentials[1].oxygen_in_mol_O2_per_kg_dry
    oxygen_residual = oxygen_available_final - oxygen_consumed
    oxygen_demand_complete = ctx.rho_dry * ctx.potentials[1].oxygen_in_mol_O2_per_kg_dry
    oxygen_cap = min(1.0, oxygen_available_final / max(oxygen_demand_complete, 1e-30))
    final_volume_ratio = float(volume_ratio[-1].mean())
    initial_bulk_volume = float(resolved["geometry"]["initial_bulk_volume_m3"])
    expected_conservation = {
        "mass_relative_residual": mass_relative,
        "gas_species_relative_residual": gas_relative,
        "element_relative_residual_by_element": element_relative,
        "max_element_relative_residual": max_element,
        "reduced_effective_enthalpy_ode_relative_residual": reduced_enthalpy_relative,
        "reduced_effective_enthalpy_ode_residual_J_m3": reduced_enthalpy_residual,
        "oxygen_inventory_residual_mol_m3_reference": oxygen_residual,
        "oxygen_stoichiometric_cap_satisfied": oxygen_residual >= -1e-8,
        "extent_projection_max": float(np.max(np.abs(projected_extents - raw_extents))),
        "mass_ledger_kg_m3_reference": {
            "initial_wet_feed": initial_mass_density,
            "oxygen_reactant_in": oxygen_in_density,
            "final_condensed": final_condensed_density,
            "final_internal_and_released_gas": float(actual_gas_density.sum()),
            "residual": mass_residual,
        },
        "bulk_volume_ledger_m3": {
            "initial": initial_bulk_volume,
            "final": initial_bulk_volume * final_volume_ratio,
            "final_to_initial_ratio": final_volume_ratio,
        },
        "element_inventory_mol_m3_reference": {
            "initial": initial_elements,
            "reactant_side_with_oxygen": reactant_elements,
            "final_condensed": condensed_elements,
            "final_internal_and_released_gas": gas_elements,
            "residual": element_residual,
        },
    }
    for key, expected in expected_conservation.items():
        semantic_results.append(_semantic_check(checks, errors, f"recomputed_conservation_{key}", conservation.get(key), expected))

    liquid = liquid_fraction(temperature, ctx.oxide_flux_index)
    try:
        with (directory / "state_trajectory.csv").open("r", encoding="utf-8", newline="") as handle:
            trajectory_rows = list(csv.DictReader(handle))
        csv_ok = len(trajectory_rows) == time_count * cell_count
        for time_index in range(time_count):
            for cell_index in range(cell_count):
                row = trajectory_rows[time_index * cell_count + cell_index]
                csv_ok = csv_ok and all((
                    _semantic_close(float(row["time_s"]), float(times[time_index])),
                    _semantic_close(float(row["x_m"]), float(x_values[cell_index])),
                    _semantic_close(float(row["temperature_K"]), float(temperature[time_index, cell_index])),
                    _semantic_close(float(row["total_porosity"]), float(total_porosity[time_index, cell_index])),
                    _semantic_close(float(row["open_porosity"]), float(open_porosity[time_index, cell_index])),
                    _semantic_close(float(row["liquid_fraction"]), float(liquid[time_index, cell_index])),
                    all(
                        _semantic_close(float(row[f"extent_{name}"]), float(projected_extents[time_index, index, cell_index]))
                        for index, name in enumerate(REACTIONS)
                    ),
                ))
        checks["trajectory_csv_cross_artifact"] = csv_ok
    except (OSError, KeyError, TypeError, ValueError, IndexError):
        checks["trajectory_csv_cross_artifact"] = False
    if not checks["trajectory_csv_cross_artifact"]:
        errors.append("failed check: trajectory_csv_cross_artifact")
    semantic_results.append(checks["trajectory_csv_cross_artifact"])
    gas_moles = gas_mass / molar_masses[None, :, None]
    generated_pressure = R_GAS * temperature * gas_moles.sum(axis=1) / np.maximum(open_porosity * volume_ratio, 1e-6)
    overpressure = float(np.max(generated_pressure))
    fidelity = manifest.get("fidelity")
    if cell_count == 1:
        gradient = np.array([abs(boundary(ctx, time_s)["gas_temperature_K"] - row[0]) for time_s, row in zip(times, temperature)]) * 0.12
    else:
        gradient = np.abs(temperature[:, 0] - temperature[:, -1])
    max_gradient = float(np.max(gradient))
    final_dry_mass = ctx.rho_dry - feed_loss_density
    bulk_density = final_dry_mass / final_volume_ratio
    final_open = float(open_porosity[-1].mean())
    shrinkage = 1.0 - final_volume_ratio ** (1.0 / 3.0)
    absorption = 100.0 * 1000.0 * final_open / max(bulk_density, 1.0)
    crack_risk = max_gradient / 600.0
    bloating_risk = overpressure / ctx.bloating_pressure_scale_Pa
    underfire_risk = float(np.max(1.0 - bounded_mean_extents[1:]))
    overfire_risk = float(np.max(liquid)) / 0.45
    strength = ctx.dense_strength * math.exp(-ctx.strength_coefficient * final_open) * max(0.2, 1.0 - 0.2 * min(crack_risk, 1.0))
    thermo = assess_thermo_coverage(case, float(temperature[-1].mean()), boundary(ctx, ctx.residence_time_s)["ambient_pressure_Pa"])
    expected_summary_values = {
        "residence_time_s": ctx.residence_time_s,
        "as_received_water_kg_per_kg_dry": ctx.as_received_water_ratio,
        "forming_added_water_kg_per_kg_dry": ctx.forming_water_ratio,
        "total_initial_water_kg_per_kg_dry": ctx.water_ratio,
        "effective_true_density_kg_m3": ctx.true_density,
        "effective_specific_heat_J_kg_K": ctx.cp,
        "effective_thermal_conductivity_W_m_K": ctx.conductivity,
        "effective_gas_diffusivity_m2_s": ctx.diffusivity,
        "effective_permeability_m2": ctx.effective_permeability_m2,
        "oxide_flux_index": ctx.oxide_flux_index,
        "bulk_density_kg_m3": bulk_density,
        "open_porosity": final_open,
        "linear_shrinkage": shrinkage,
        "water_absorption_proxy_percent": absorption,
        "strength_proxy_Pa": strength,
        "liquid_fraction": float(liquid[-1].mean()),
        "phase_amounts": {"solid_screening_proxy": float(1.0 - liquid[-1].mean()), "oxide_liquid_unresolved_screening_proxy": float(liquid[-1].mean())},
        "released_gas_kg_per_kg_dry": {name: float(value / ctx.rho_dry) for name, value in zip(GASES, released_mass[-1])},
        "max_overpressure_Pa": overpressure,
        "max_center_surface_temperature_difference_K": max_gradient,
        "stress_proxy_Pa": max_gradient * 1e6 * 1e-5 / 0.75,
        "reaction_completion": {name: float(value) for name, value in zip(REACTIONS, bounded_mean_extents)},
        "oxygen_ledger_mol_O2_per_m3_reference": {
            "initial_inventory": ctx.oxygen_initial_inventory_mol_m3,
            "boundary_supplied": oxygen_boundary_supplied,
            "available_total": oxygen_available_final,
            "consumed": oxygen_consumed,
            "residual": oxygen_residual,
            "demand_if_complete": oxygen_demand_complete,
            "stoichiometric_completion_cap": oxygen_cap,
        },
        "emissions_coverage": {"covered_products": list(GASES), "coverage_gaps": ["CO", "VOC", "NOx"]},
        "enthalpy_coverage": {
            "included": ["wet-feed and forming water in fixed effective heat capacity", "boundary convection and radiation", "effective reaction enthalpy including evaporation latent heat"],
            "excluded": ["variable condensed and gas heat capacities", "escaped-gas sensible enthalpy", "diffusive gas sensible-enthalpy transport"],
        },
        "cracking_risk": crack_risk,
        "bloating_risk": bloating_risk,
        "underfiring_risk": underfire_risk,
        "overfiring_risk": overfire_risk,
        "warpage_risk": max_gradient / 800.0,
        "efflorescence_risk": None,
        "thermo_coverage_score": thermo["mapping_coverage_score"],
        "environmental_status": None,
    }
    semantic_results.append(_semantic_check(checks, errors, "summary_key_set", sorted(summary), sorted(expected_summary_values)))
    for key, expected in expected_summary_values.items():
        actual = summary.get(key)
        semantic_results.append(_semantic_check(checks, errors, f"recomputed_summary_{key}", actual.get("value") if isinstance(actual, dict) else None, expected))
    expected_statuses = {
        "strength_proxy_Pa": "unresolved_for_certification",
        "liquid_fraction": "unresolved_oxide_liquid_database",
        "phase_amounts": "unresolved_oxide_liquid_database",
        "emissions_coverage": "not_evaluated",
        "enthalpy_coverage": "reduced_model_not_full_energy_conservation",
        "efflorescence_risk": "unresolved",
        "thermo_coverage_score": thermo["status"],
        "environmental_status": "not_evaluated",
    }
    for key, expected in expected_statuses.items():
        semantic_results.append(_semantic_check(checks, errors, f"summary_status_{key}", summary.get(key, {}).get("status"), expected))
    semantic_results.append(_semantic_check(checks, errors, "forward_status_success", status.get("success"), True))
    checks["forward_cross_artifact_semantics"] = all(semantic_results)


def _inverse_case_hash(resolved: dict[str, Any], record: dict[str, Any]) -> str:
    raw = copy.deepcopy(resolved)
    decision = record["decision"]
    sludge_fraction = float(decision["sludge_dry_mass_fraction"])
    matrix_total = 1.0 - sludge_fraction
    matrix_reference = float(resolved["feedstocks"]["shale"]["dry_mass_fraction"]) + float(resolved["feedstocks"]["coal_gangue"]["dry_mass_fraction"])
    raw["feedstocks"]["shale"]["dry_mass_fraction"] = matrix_total * float(resolved["feedstocks"]["shale"]["dry_mass_fraction"]) / matrix_reference
    raw["feedstocks"]["coal_gangue"]["dry_mass_fraction"] = matrix_total * float(resolved["feedstocks"]["coal_gangue"]["dry_mass_fraction"]) / matrix_reference
    raw["feedstocks"]["sludge"]["dry_mass_fraction"] = sludge_fraction
    components = {item["id"]: item for item in raw["feedstocks"]["sludge"]["components"]}
    organic = float(decision["sludge_organic_fraction"])
    calcite = float(decision["sludge_calcite_fraction"])
    amorphous = float(decision["sludge_amorphous_fraction"])
    components["organic_pseudo_A"]["fraction"] = organic
    components["calcite"]["fraction"] = calcite
    components["amorphous_oxide_pool"]["fraction"] = amorphous
    remaining = 1.0 - organic - calcite - amorphous
    for name, share in {"quartz": 0.30, "kaolinite": 0.30, "illite_pseudo": 0.25, "hematite": 0.15}.items():
        components[name]["fraction"] = remaining * share
    d50 = float(decision["sludge_d50_m"])
    raw["feedstocks"]["sludge"]["particle_size_distribution"] = {"d10_m": 0.2 * d50, "d50_m": d50, "d90_m": 5.0 * d50}
    sphericity = float(decision["sludge_sphericity"])
    raw["feedstocks"]["sludge"]["morphology"] = {"sphericity": sphericity, "aspect_ratio": 1.0 + 4.0 * (1.0 - sphericity)}
    raw["feedstocks"]["sludge"]["free_moisture_wet_basis"] = float(decision["sludge_free_moisture_wet_basis"])
    raw["kiln"]["speed_ratio"] = float(decision["speed_ratio"])
    for property_name in (
        "true_density_kg_m3", "specific_heat_J_kg_K", "thermal_conductivity_W_m_K", "effective_gas_diffusivity_m2_s"
    ):
        raw["feedstocks"]["sludge"]["material_properties"][property_name] = float(decision[f"sludge_{property_name}"])
    raw["case_id"] = f"inverse_design_{int(record['design_id']):04d}"
    return sha256_json(raw)


def _inverse_record_semantics(record: dict[str, Any], manifest: dict[str, Any], resolved: dict[str, Any]) -> bool:
    try:
        samples = record["policy_samples"]
        if not isinstance(samples, list) or not samples:
            return False
        successful = [sample for sample in samples if sample.get("success") is True]
        failure_rate = (len(samples) - len(successful)) / len(samples)
        maximum = float(record["robust_failure_policy"]["maximum_failure_rate"])
        required_success = failure_rate <= maximum
        if not successful:
            return (
                record.get("status") == "infeasible"
                and _semantic_close(record.get("failure_rate"), failure_rate)
                and record.get("constraints", {}).get("all_hard_constraints") is False
            )
        qualities = [float(sample["quality_margin"]) for sample in successful]
        risks = [float(sample["enabled_risk"]) for sample in successful]
        quality_q = {name: float(value) for name, value in zip(("q05", "q50", "q95"), np.quantile(qualities, (0.05, 0.5, 0.95)))}
        risk_q = {name: float(value) for name, value in zip(("q05", "q50", "q95"), np.quantile(risks, (0.05, 0.5, 0.95)))}
        verification_inputs = record["verification_inputs"]
        representative = samples[int(verification_inputs["representative_sample_index"])]
        representative_conservation = representative["conservation"]
        grid_value = verification_inputs.get("grid_converged")
        grid_ok = True if grid_value is None else bool(grid_value)
        constraints = {
            "forward_success": representative.get("success") is True,
            "mass_conservation": float(representative_conservation["mass_relative_residual"]) < 1e-8,
            "element_conservation": float(representative_conservation["max_element_relative_residual"]) < 1e-8,
            "energy_conservation": "not_evaluated",
            "reduced_effective_enthalpy_ode_numerics": float(representative_conservation["reduced_effective_enthalpy_ode_relative_residual"]) < 1e-4,
            "thermo_coverage": "not_evaluated",
            "thermo_hard_pass": False,
            "q05_synthetic_quality_margin": quality_q["q05"] >= 0.0,
            "q95_enabled_risk": risk_q["q95"] <= 1.0,
            "grid_convergence": grid_ok,
            "environmental_threshold": "not_evaluated",
            "required_policy_samples_successful": required_success,
        }
        constraints["all_hard_constraints"] = all(
            constraints[name] is True
            for name in (
                "forward_success", "mass_conservation", "element_conservation", "reduced_effective_enthalpy_ode_numerics",
                "q05_synthetic_quality_margin", "q95_enabled_risk", "grid_convergence", "required_policy_samples_successful",
            )
        )
        slacks = {
            "forward_success": 1.0 if constraints["forward_success"] else -1.0,
            "mass_conservation": (1e-8 - float(representative_conservation["mass_relative_residual"])) / 1e-8,
            "element_conservation": (1e-8 - float(representative_conservation["max_element_relative_residual"])) / 1e-8,
            "reduced_effective_enthalpy_ode_numerics": (1e-4 - float(representative_conservation["reduced_effective_enthalpy_ode_relative_residual"])) / 1e-4,
            "q05_synthetic_quality_margin": quality_q["q05"],
            "q95_enabled_risk": 1.0 - risk_q["q95"],
            "grid_convergence": 1.0 if grid_ok else -1.0,
            "required_policy_sample_failure_rate": maximum - failure_rate,
        }
        active = sorted(name for name, slack in slacks.items() if slack <= 0.05)
        uncertainty_width = quality_q["q95"] - quality_q["q05"]
        decision = record["decision"]
        objectives = [
            -quality_q["q05"], risk_q["q95"], float(record["summary"]["residence_time_s"]["value"]) / 150000.0,
            uncertainty_width, -float(decision["sludge_dry_mass_fraction"]),
        ]
        return all((
            _semantic_close(record.get("failure_rate"), failure_rate),
            _semantic_close(record.get("quality_margin"), quality_q),
            _semantic_close(record.get("enabled_risk"), risk_q),
            _semantic_close(record.get("uncertainty_width"), uncertainty_width),
            _semantic_close(record.get("constraints"), constraints),
            _semantic_close(record.get("constraint_slacks"), slacks),
            record.get("active_constraints") == active,
            _semantic_close(record.get("objectives"), objectives),
            record.get("status") == ("feasible" if constraints["all_hard_constraints"] else "infeasible"),
            record.get("source_hashes", {}).get("parameter_pack") == manifest.get("parameter_pack_hash"),
            record.get("source_hashes", {}).get("case") == _inverse_case_hash(resolved, record),
        ))
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def _inverse_independent_semantics(
    directory: Path,
    manifest: dict[str, Any],
    resolved: dict[str, Any],
    status: dict[str, Any],
    summary: dict[str, Any],
    pareto: list[dict[str, Any]],
    all_evaluations: list[dict[str, Any]],
    errors: list[str],
    checks: dict[str, bool],
) -> None:
    record_semantics = all(_inverse_record_semantics(record, manifest, resolved) for record in all_evaluations)
    checks["inverse_record_semantics"] = record_semantics
    if not record_semantics:
        errors.append("independent inverse record/constraint recomputation failed")
    keys = [(record.get("design_id"), record.get("fidelity")) for record in all_evaluations]
    checks["inverse_record_keys_unique"] = len(keys) == len(set(keys))
    if not checks["inverse_record_keys_unique"]:
        errors.append("inverse evaluation design/fidelity keys are not unique")
    checks["pareto_traceability"] = all(any(candidate == evaluation for evaluation in all_evaluations) for candidate in pareto)
    checks["pareto_constraints"] = all(candidate.get("constraints", {}).get("all_hard_constraints") is True for candidate in pareto)
    l0_records = [record for record in all_evaluations if record.get("fidelity") == "L0"]
    l1_ranked = [
        record for record in all_evaluations
        if record.get("fidelity") == "L1" and record.get("constraints", {}).get("all_hard_constraints") is True
    ]
    if l1_ranked:
        objectives = np.asarray([record["objectives"] for record in l1_ranked], dtype=float)
        mask = nondominated_mask(objectives, np.ones(len(l1_ranked), dtype=bool))
        expected_pareto = [record for record, keep in zip(l1_ranked, mask) if keep]
    else:
        expected_pareto = []
    sorted_actual = sorted(pareto, key=lambda record: (record.get("design_id"), record.get("fidelity")))
    sorted_expected = sorted(expected_pareto, key=lambda record: (record.get("design_id"), record.get("fidelity")))
    checks["pareto_nondominated_from_all_l1"] = _semantic_close(sorted_actual, sorted_expected)
    checks["pareto_nondominated"] = checks["pareto_nondominated_from_all_l1"]
    expected_summary = {
        "status": status.get("code"),
        "evaluated_designs": len(l0_records),
        "evaluation_records": len(all_evaluations),
        "l0_feasible_designs": sum(record.get("constraints", {}).get("all_hard_constraints") is True for record in l0_records),
        "l1_ranked_candidates": len(l1_ranked),
        "pareto_candidates": len(expected_pareto),
        "environmental_status": "not_evaluated",
    }
    checks["inverse_summary_counts"] = _semantic_close(summary, expected_summary)
    envelope = _safe_json(directory, "feasible_windows.json", errors)
    checks["observed_envelope_sources"] = isinstance(envelope, dict) and _semantic_close(envelope, _feasible_windows(l1_ranked))
    paired_l0: list[float] = []
    paired_l1: list[float] = []
    for l1_record in [record for record in all_evaluations if record.get("fidelity") == "L1"]:
        l0_record = next(
            (record for record in l0_records if record.get("design_id") == l1_record.get("design_id")),
            None,
        )
        if l0_record is None or "quality_margin" not in l0_record or "quality_margin" not in l1_record:
            continue
        paired_l0.append(float(l0_record["quality_margin"]["q05"]))
        paired_l1.append(float(l1_record["quality_margin"]["q05"]))
    expected_rank = _rank_stability(paired_l0, paired_l1)
    rank_stability = _safe_json(directory, "rank_stability.json", errors)
    uncertainty = _safe_json(directory, "uncertainty.json", errors)
    checks["rank_stability_sources"] = (
        isinstance(rank_stability, dict)
        and _semantic_close(rank_stability, expected_rank)
        and isinstance(uncertainty, dict)
        and _semantic_close(uncertainty.get("rank_stability"), expected_rank)
    )
    try:
        with (directory / "pareto.csv").open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        csv_ok = len(rows) == len(pareto)
        for rank, (row, record) in enumerate(zip(rows, pareto), start=1):
            csv_ok = csv_ok and all((
                int(row["rank"]) == rank,
                int(row["design_id"]) == int(record["design_id"]),
                row["fidelity"] == record["fidelity"],
                _semantic_close(float(row["quality_q05"]), record["quality_margin"]["q05"]),
                _semantic_close(float(row["risk_q95"]), record["enabled_risk"]["q95"]),
                _semantic_close(float(row["uncertainty_width"]), record["uncertainty_width"]),
                all(_semantic_close(float(row[name]), value) for name, value in record["decision"].items()),
            ))
        checks["pareto_csv_cross_artifact"] = csv_ok
    except (OSError, KeyError, TypeError, ValueError):
        checks["pareto_csv_cross_artifact"] = False
    for name in (
        "pareto_traceability", "pareto_constraints", "pareto_nondominated_from_all_l1", "inverse_summary_counts",
        "observed_envelope_sources", "rank_stability_sources", "pareto_csv_cross_artifact",
    ):
        if not checks[name]:
            errors.append(f"failed check: {name}")


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
        for name in ("conservation.json", "state_trajectory.json", "state_trajectory.csv", "uncertainty.json", "provenance.json"):
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
        _forward_independent_semantics(
            directory,
            manifest,
            resolved,
            status,
            summary,
            conservation,
            trajectory,
            errors,
            checks,
        )
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
        _inverse_independent_semantics(
            directory,
            manifest,
            resolved,
            status,
            inverse_summary,
            pareto,
            all_evaluations,
            errors,
            checks,
        )
    else:
        errors.append(f"unknown run_type: {run_type!r}")
    return VerifyResult(not errors, errors, warnings, checks)
