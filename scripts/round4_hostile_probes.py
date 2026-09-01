from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
import io
import json
import shutil
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from sludge_vme import cli
from sludge_vme.io import artifacts as artifact_module
from sludge_vme.io.artifacts import verify_run
from sludge_vme.models import simulate as original_simulate


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def rehash(directory: Path, *names: str) -> None:
    manifest_path = directory / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in names:
        payload = (directory / name).read_bytes()
        manifest["artifacts"][name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    write_json(manifest_path, manifest)


def clone(source: Path, root: Path, name: str) -> Path:
    target = root / name
    shutil.copytree(source, target)
    return target


def verification(directory: Path) -> dict[str, object]:
    result = verify_run(directory, strict=True)
    return {
        "valid": result.valid,
        "errors": result.errors,
        "failed_checks": sorted(name for name, ok in result.checks.items() if not ok),
    }


def forward_attacks(source: Path, root: Path) -> dict[str, object]:
    root.mkdir(parents=True)
    records: dict[str, object] = {"original": verification(source)}

    def trajectory_attack(name: str, mutate) -> None:
        target = clone(source, root, name)
        path = target / "state_trajectory.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        mutate(payload)
        write_json(path, payload)
        rehash(target, "state_trajectory.json")
        records[name] = verification(target)

    def summary_attack(name: str, mutate) -> None:
        target = clone(source, root, name)
        path = target / "summary.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        mutate(payload)
        write_json(path, payload)
        rehash(target, "summary.json")
        records[name] = verification(target)

    def change_interior_heat(payload: dict) -> None:
        values = payload["fields"]["boundary_heat_cumulative"]["values"]
        index = len(values) // 2
        values[index] = float(values[index]) + max(1.0, abs(float(values[index])) * 0.01)

    def change_reaction_heat(payload: dict) -> None:
        values = payload["fields"]["reaction_heat_cumulative"]["values"]
        index = len(values) // 2
        values[index] = float(values[index]) + max(1.0, abs(float(values[index])) * 0.01)

    def change_pressure(payload: dict) -> None:
        values = payload["fields"]["gas_overpressure"]["values"]
        index = max(range(len(values)), key=lambda item: float(values[item]))
        values[index] = float(values[index]) * 0.5

    trajectory_attack("forward_boundary_heat_interior", change_interior_heat)
    trajectory_attack("forward_reaction_heat_interior", change_reaction_heat)
    trajectory_attack("forward_overpressure_interior_extrema", change_pressure)
    trajectory_attack(
        "forward_mass_unit",
        lambda payload: payload["fields"]["gas_concentrations"]["H2O"].__setitem__(
            "unit", "mol/m3_reference_bulk"
        ),
    )
    trajectory_attack(
        "forward_molar_basis",
        lambda payload: payload["fields"]["gas_molar_inventories"]["CO2"].__setitem__(
            "basis", "attacker supplied basis"
        ),
    )
    trajectory_attack(
        "forward_current_pore_species",
        lambda payload: payload["fields"]["gas_current_pore_concentrations"]["N2"].__setitem__(
            "species", "CO2"
        ),
    )
    trajectory_attack(
        "forward_released_conversion",
        lambda payload: payload["fields"]["released_gas_mass_inventories"]["SO2"].__setitem__(
            "conversion", "attacker supplied conversion"
        ),
    )
    trajectory_attack(
        "forward_declared_shape",
        lambda payload: payload["semantic_contract"]["fields"]["temperature"].__setitem__(
            "shape", ["cell", "time"]
        ),
    )
    summary_attack(
        "forward_summary_unit",
        lambda payload: payload["max_overpressure_Pa"].__setitem__("unit", "kPa"),
    )
    summary_attack(
        "forward_summary_validity",
        lambda payload: payload["effective_true_density_kg_m3"].__setitem__(
            "validity", "attacker supplied validity"
        ),
    )
    return records


def read_evaluations(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_evaluations(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def inverse_attacks(source: Path, root: Path) -> dict[str, object]:
    root.mkdir(parents=True)
    records: dict[str, object] = {"original": verification(source)}

    target = clone(source, root, "inverse_delete_l0_coherent_counts")
    path = target / "all_evaluations.jsonl"
    evaluations = read_evaluations(path)
    removed_index = next(index for index, record in enumerate(evaluations) if record["fidelity"] == "L0")
    removed = evaluations.pop(removed_index)
    write_evaluations(path, evaluations)
    summary_path = target / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["evaluated_designs"] -= 1
    summary["evaluation_records"] -= 1
    if removed["constraints"]["all_hard_constraints"]:
        summary["l0_feasible_designs"] -= 1
    write_json(summary_path, summary)
    rehash(target, "all_evaluations.jsonl", "summary.json")
    records["delete_l0_coherent_counts"] = verification(target)

    target = clone(source, root, "inverse_add_l0_coherent_counts")
    path = target / "all_evaluations.jsonl"
    evaluations = read_evaluations(path)
    added = copy.deepcopy(next(record for record in evaluations if record["fidelity"] == "L0"))
    added["design_id"] = 999
    evaluations.insert(sum(record["fidelity"] == "L0" for record in evaluations), added)
    write_evaluations(path, evaluations)
    summary_path = target / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["evaluated_designs"] += 1
    summary["evaluation_records"] += 1
    summary["l0_feasible_designs"] += 1
    write_json(summary_path, summary)
    rehash(target, "all_evaluations.jsonl", "summary.json")
    records["add_l0_coherent_counts"] = verification(target)

    target = clone(source, root, "inverse_reorder_l0")
    path = target / "all_evaluations.jsonl"
    evaluations = read_evaluations(path)
    evaluations[0], evaluations[1] = evaluations[1], evaluations[0]
    write_evaluations(path, evaluations)
    rehash(target, "all_evaluations.jsonl")
    records["reorder_l0"] = verification(target)

    target = clone(source, root, "inverse_nonpareto_source")
    path = target / "all_evaluations.jsonl"
    evaluations = read_evaluations(path)
    source_record = next(record for record in evaluations if record["fidelity"] == "L0")
    source_record["model_flags"].append("attacker_modified_source_record")
    write_evaluations(path, evaluations)
    rehash(target, "all_evaluations.jsonl")
    records["nonpareto_source"] = verification(target)

    target = clone(source, root, "inverse_coherent_pareto_decision")
    pareto_path = target / "pareto.json"
    evaluation_path = target / "all_evaluations.jsonl"
    pareto = json.loads(pareto_path.read_text(encoding="utf-8"))
    evaluations = read_evaluations(evaluation_path)
    candidate = pareto[0]
    old_speed = float(candidate["decision"]["speed_ratio"])
    resolved = json.loads((target / "resolved_case.json").read_text(encoding="utf-8"))
    low, high = resolved["inverse_design"]["speed_ratio_bounds"]
    new_speed = float(low + high - old_speed)
    source_record = next(
        record
        for record in evaluations
        if record["design_id"] == candidate["design_id"] and record["fidelity"] == "L1"
    )
    for record in (candidate, source_record):
        record["decision"]["speed_ratio"] = new_speed
    forged_case_hash = artifact_module._inverse_case_hash(resolved, source_record)
    candidate["source_hashes"]["case"] = forged_case_hash
    source_record["source_hashes"]["case"] = forged_case_hash
    write_json(pareto_path, pareto)
    write_evaluations(evaluation_path, evaluations)
    artifact_module._write_pareto_csv(target / "pareto.csv", pareto)
    ranked = [
        record
        for record in evaluations
        if record["fidelity"] == "L1" and record["constraints"]["all_hard_constraints"]
    ]
    write_json(target / "feasible_windows.json", artifact_module._feasible_windows(ranked))
    rehash(
        target,
        "pareto.json",
        "all_evaluations.jsonl",
        "pareto.csv",
        "feasible_windows.json",
    )
    records["coherent_pareto_decision"] = verification(target)

    target = clone(source, root, "inverse_constraint")
    pareto_path = target / "pareto.json"
    evaluation_path = target / "all_evaluations.jsonl"
    pareto = json.loads(pareto_path.read_text(encoding="utf-8"))
    evaluations = read_evaluations(evaluation_path)
    candidate = pareto[0]
    source_record = next(
        record
        for record in evaluations
        if record["design_id"] == candidate["design_id"] and record["fidelity"] == "L1"
    )
    for record in (candidate, source_record):
        record["constraint_slacks"]["q95_enabled_risk"] += 0.25
    write_json(pareto_path, pareto)
    write_evaluations(evaluation_path, evaluations)
    rehash(target, "pareto.json", "all_evaluations.jsonl")
    records["constraint"] = verification(target)

    target = clone(source, root, "inverse_nondominance")
    pareto_path = target / "pareto.json"
    evaluation_path = target / "all_evaluations.jsonl"
    pareto = json.loads(pareto_path.read_text(encoding="utf-8"))
    evaluations = read_evaluations(evaluation_path)
    candidate = pareto[0]
    source_record = next(
        record
        for record in evaluations
        if record["design_id"] == candidate["design_id"] and record["fidelity"] == "L1"
    )
    forged_objectives = [float(value) + 0.25 for value in source_record["objectives"]]
    candidate["objectives"] = forged_objectives
    source_record["objectives"] = forged_objectives
    write_json(pareto_path, pareto)
    write_evaluations(evaluation_path, evaluations)
    rehash(target, "pareto.json", "all_evaluations.jsonl")
    records["nondominance"] = verification(target)
    return records


def credential_failure_matrix(root: Path) -> dict[str, object]:
    root.mkdir(parents=True)
    case_path = Path(__file__).resolve().parents[1] / "examples" / "tiny_synthetic.json"
    records: dict[str, object] = {}
    for lane in ("forward_L0", "forward_L1", "inverse", "benchmark_L0", "benchmark_L1"):
        sentinels = [
            f"token-canary-{lane}",
            f"password-canary-{lane}",
            f"eyJhbGciOiJub25lIn0.{lane}.signature",
            f"Bearer canary-{lane}",
            f"person-{lane}@example.invalid",
            f"+1-202-555-{1000 + len(lane)}",
            f"Authorization: Basic canary-{lane}",
            f"https://example.invalid/?credential=canary-{lane}",
            f"«private-canary-{lane}»",
        ]
        exception_type = type(f"UserControlled{lane}CredentialError", (Exception,), {})
        message = " | ".join(sentinels)
        out = root / lane
        stdout = io.StringIO()
        stderr = io.StringIO()
        if lane.startswith("forward"):
            fidelity = lane.removeprefix("forward_")
            args = Namespace(
                case=case_path,
                fidelity=fidelity,
                out=out,
                uq_power=None,
                seed=71,
                overwrite=False,
            )
            with patch.object(cli, "simulate", side_effect=exception_type(message)), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli.command_forward(args)
        elif lane == "inverse":
            args = Namespace(case=case_path, budget="tiny", out=out, seed=72, overwrite=False)
            with patch.object(cli, "run_inverse", side_effect=exception_type(message)), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli.command_inverse(args)
        else:
            calls = 0

            def benchmark_simulate(case, fidelity):
                nonlocal calls
                calls += 1
                if lane == "benchmark_L0" or calls == 2:
                    raise exception_type(message)
                return original_simulate(case, fidelity, {"grid_check": False})

            args = Namespace(case=case_path, out=out, seed=73, overwrite=False)
            with patch.object(cli, "simulate", side_effect=benchmark_simulate), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli.command_benchmark(args)
        joined = stdout.getvalue() + stderr.getvalue()
        joined += "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in out.rglob("*")
            if path.is_file()
        )
        status = json.loads((out / "status.json").read_text(encoding="utf-8"))
        records[lane] = {
            "exit": exit_code,
            "category": status["exception"]["category"],
            "sentinel_plaintext_absent": all(sentinel not in joined for sentinel in sentinels),
            "class_name_absent": exception_type.__name__ not in joined,
            "traceback_absent": "Traceback" not in joined,
            "atomic_manifest_present": (out / "run_manifest.json").is_file(),
        }
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward", type=Path, required=True)
    parser.add_argument("--inverse", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(f"refusing to replace hostile-probe directory: {out}")
    out.mkdir(parents=True)
    results = {
        "B5_credential_failures": credential_failure_matrix(out / "credential_failures"),
        "B8_forward": forward_attacks(args.forward.resolve(), out / "forward"),
        "B8_inverse": inverse_attacks(args.inverse.resolve(), out / "inverse"),
    }
    credential_records = results["B5_credential_failures"]
    results["acceptance"] = {
        "credential_matrix_secure": all(
            record["exit"] == 3
            and record["category"] == "unexpected_error"
            and record["sentinel_plaintext_absent"]
            and record["class_name_absent"]
            and record["traceback_absent"]
            and record["atomic_manifest_present"]
            for record in credential_records.values()
        ),
        "forward_original_valid": results["B8_forward"]["original"]["valid"],
        "all_forward_attacks_rejected": all(
            not record["valid"]
            for name, record in results["B8_forward"].items()
            if name != "original"
        ),
        "inverse_original_valid": results["B8_inverse"]["original"]["valid"],
        "all_inverse_attacks_rejected": all(
            not record["valid"]
            for name, record in results["B8_inverse"].items()
            if name != "original"
        ),
    }
    write_json(out / "round4_hostile_results.json", results)
    print(json.dumps(results["acceptance"], indent=2, sort_keys=True))
    return 0 if all(results["acceptance"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
