from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from sludge_vme import cli
from sludge_vme.io.artifacts import verify_run


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def rehash(directory: Path, name: str) -> None:
    path = directory / name
    manifest_path = directory / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = path.read_bytes()
    manifest["artifacts"][name] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    write_json(manifest_path, manifest)


def clone_attack(source: Path, probes: Path, name: str) -> Path:
    target = probes / name
    shutil.copytree(source, target)
    return target


def verification_record(directory: Path) -> dict[str, object]:
    result = verify_run(directory, strict=True)
    return {"valid": result.valid, "errors": result.errors, "checks": result.checks}


def malformed_matrix(root: Path, probes: Path) -> dict[str, object]:
    base = json.loads((root / "examples" / "tiny_synthetic.json").read_text(encoding="utf-8"))
    payloads = {
        "top_level_list": [],
        "kiln_list": {**copy.deepcopy(base), "kiln": []},
        "profile_null": {**copy.deepcopy(base), "kiln": {**copy.deepcopy(base["kiln"]), "profile": None}},
        "profile_scalar_items": {**copy.deepcopy(base), "kiln": {**copy.deepcopy(base["kiln"]), "profile": [1, 2]}},
        "inverse_list": {**copy.deepcopy(base), "inverse_design": []},
        "inverse_null": {**copy.deepcopy(base), "inverse_design": None},
    }
    results: dict[str, object] = {}
    malformed_dir = probes / "malformed"
    malformed_dir.mkdir()
    for name, payload in payloads.items():
        path = malformed_dir / f"{name}.json"
        write_json(path, payload)
        completed = subprocess.run(
            [sys.executable, "-m", "sludge_vme.cli", "validate", str(path), "--json"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        results[name] = {
            "exit": completed.returncode,
            "traceback": "Traceback" in completed.stderr,
            "structured_validation": '"valid": false' in completed.stdout.lower(),
        }
    return results


def injected_failures(root: Path, probes: Path) -> dict[str, object]:
    case = root / "examples" / "tiny_synthetic.json"
    results: dict[str, object] = {}

    def fail(*args, **kwargs):
        raise RuntimeError("round3 manufactured solver failure")

    commands = {
        "forward_L0": (
            "simulate",
            cli.command_forward,
            Namespace(case=case, fidelity="L0", out=probes / "failure_forward_L0", uq_power=None, seed=31, overwrite=False),
        ),
        "forward_L1": (
            "simulate",
            cli.command_forward,
            Namespace(case=case, fidelity="L1", out=probes / "failure_forward_L1", uq_power=None, seed=32, overwrite=False),
        ),
        "inverse": (
            "run_inverse",
            cli.command_inverse,
            Namespace(case=case, budget="tiny", out=probes / "failure_inverse", seed=33, overwrite=False),
        ),
        "benchmark_L0": (
            "simulate",
            cli.command_benchmark,
            Namespace(case=case, out=probes / "failure_benchmark", seed=34, overwrite=False),
        ),
    }
    for name, (symbol, command, command_args) in commands.items():
        stderr = io.StringIO()
        with patch.object(cli, symbol, side_effect=fail), contextlib.redirect_stderr(stderr):
            exit_code = command(command_args)
        failure_dirs = [command_args.out]
        if not command_args.out.exists():
            failure_dirs = list(command_args.out.parent.glob(f".{command_args.out.name}.failure-*"))
        status_path = failure_dirs[0] / "status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        results[name] = {
            "exit": exit_code,
            "traceback": "Traceback" in stderr.getvalue(),
            "status": status,
            "manifest_present": (failure_dirs[0] / "run_manifest.json").is_file(),
            "provenance_present": (failure_dirs[0] / "provenance.json").is_file(),
        }
    return results


def forward_attacks(source: Path, probes: Path) -> dict[str, object]:
    records: dict[str, object] = {"original": verification_record(source)}

    target = clone_attack(source, probes, "forward_density_doubled")
    path = target / "summary.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["bulk_density_kg_m3"]["value"] *= 2.0
    write_json(path, payload)
    rehash(target, "summary.json")
    records["density_doubled"] = verification_record(target)

    target = clone_attack(source, probes, "forward_summary_legal")
    path = target / "summary.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["linear_shrinkage"]["value"] += 0.01
    write_json(path, payload)
    rehash(target, "summary.json")
    records["summary_legal_range"] = verification_record(target)

    target = clone_attack(source, probes, "forward_conservation_zeroed")
    path = target / "conservation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["mass_relative_residual"] = 0.0
    payload["max_element_relative_residual"] = 0.0
    payload["element_relative_residual_by_element"] = {
        key: 0.0 for key in payload["element_relative_residual_by_element"]
    }
    write_json(path, payload)
    rehash(target, "conservation.json")
    records["mass_element_zeroed"] = verification_record(target)

    target = clone_attack(source, probes, "forward_oxygen_zeroed")
    path = target / "summary.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["oxygen_ledger_mol_O2_per_m3_reference"]["value"]["residual"] = 0.0
    write_json(path, payload)
    rehash(target, "summary.json")
    records["oxygen_residual_zeroed"] = verification_record(target)

    target = clone_attack(source, probes, "forward_enthalpy_zeroed")
    path = target / "conservation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["reduced_effective_enthalpy_ode_relative_residual"] = 0.0
    payload["reduced_effective_enthalpy_ode_residual_J_m3"] = 0.0
    write_json(path, payload)
    rehash(target, "conservation.json")
    records["reduced_enthalpy_zeroed"] = verification_record(target)

    target = clone_attack(source, probes, "forward_counts_changed")
    path = target / "state_trajectory.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state_counts"]["time_points"] += 1
    write_json(path, payload)
    rehash(target, "state_trajectory.json")
    records["trajectory_counts_changed"] = verification_record(target)

    target = clone_attack(source, probes, "forward_csv_changed")
    path = target / "state_trajectory.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["temperature_K"] = str(float(rows[0]["temperature_K"]) + 1.0)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    rehash(target, "state_trajectory.csv")
    records["trajectory_csv_changed"] = verification_record(target)
    return records


def mutate_inverse_record_pair(target: Path, mutation) -> None:
    pareto_path = target / "pareto.json"
    pareto = json.loads(pareto_path.read_text(encoding="utf-8"))
    mutation(pareto[0])
    write_json(pareto_path, pareto)
    rehash(target, "pareto.json")
    evaluations_path = target / "all_evaluations.jsonl"
    evaluations = [json.loads(line) for line in evaluations_path.read_text(encoding="utf-8").splitlines()]
    source = next(
        record for record in evaluations
        if record.get("design_id") == pareto[0].get("design_id") and record.get("fidelity") == pareto[0].get("fidelity")
    )
    mutation(source)
    evaluations_path.write_text(
        "".join(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in evaluations),
        encoding="utf-8",
    )
    rehash(target, "all_evaluations.jsonl")


def inverse_attacks(source: Path, probes: Path) -> dict[str, object]:
    records: dict[str, object] = {"original": verification_record(source)}

    target = clone_attack(source, probes, "inverse_summary_count")
    path = target / "summary.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pareto_candidates"] += 1
    write_json(path, payload)
    rehash(target, "summary.json")
    records["summary_count_changed"] = verification_record(target)

    target = clone_attack(source, probes, "inverse_constraint")
    mutate_inverse_record_pair(target, lambda record: record["constraints"].__setitem__("q95_enabled_risk", False))
    records["constraint_changed_both_sources"] = verification_record(target)

    target = clone_attack(source, probes, "inverse_source")
    mutate_inverse_record_pair(target, lambda record: record["source_hashes"].__setitem__("case", "forged-source"))
    records["source_changed_both_sources"] = verification_record(target)

    target = clone_attack(source, probes, "inverse_envelope")
    path = target / "feasible_windows.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    first_name = sorted(payload["windows"])[0]
    payload["windows"][first_name]["max"] += 0.01
    write_json(path, payload)
    rehash(target, "feasible_windows.json")
    records["envelope_changed"] = verification_record(target)

    target = clone_attack(source, probes, "inverse_csv")
    path = target / "pareto.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["quality_q05"] = str(float(rows[0]["quality_q05"]) + 0.5)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    rehash(target, "pareto.csv")
    records["pareto_csv_changed"] = verification_record(target)

    target = clone_attack(source, probes, "inverse_rank")
    path = target / "rank_stability.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "stable" if payload.get("status") != "stable" else "unstable"
    write_json(path, payload)
    rehash(target, "rank_stability.json")
    records["rank_status_changed"] = verification_record(target)

    target = clone_attack(source, probes, "inverse_pareto_replaced")
    evaluations = [json.loads(line) for line in (target / "all_evaluations.jsonl").read_text(encoding="utf-8").splitlines()]
    wrong_source = next(record for record in evaluations if record.get("fidelity") == "L0" and record.get("constraints", {}).get("all_hard_constraints") is True)
    write_json(target / "pareto.json", [wrong_source])
    rehash(target, "pareto.json")
    records["pareto_replaced_with_traceable_l0"] = verification_record(target)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--round-dir", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    round_dir = (args.round_dir or root / "runs" / "safety_review_round3").resolve()
    probes = round_dir / "hostile_probes"
    if probes.exists():
        raise FileExistsError(f"refusing to replace existing hostile probe directory: {probes}")
    probes.mkdir(parents=True)
    forward = round_dir / "e2e" / "L0"
    inverse = round_dir / "e2e" / "inverse"
    l1 = round_dir / "e2e" / "L1"
    if not all(path.is_dir() for path in (forward, inverse, l1)):
        raise FileNotFoundError("fresh round3 L0/L1/inverse artifacts must exist before hostile probes")
    l1_trajectory = json.loads((l1 / "state_trajectory.json").read_text(encoding="utf-8"))
    transport = l1_trajectory["transport_contract"]
    results = {
        "B3": {
            "transport_contract": transport,
            "H2O_field": {
                key: l1_trajectory["fields"]["gas_current_pore_concentrations"]["H2O"][key]
                for key in ("unit", "basis", "species", "molar_mass_kg_mol", "conversion")
            },
            "CO2_field": {
                key: l1_trajectory["fields"]["gas_current_pore_concentrations"]["CO2"][key]
                for key in ("unit", "basis", "species", "molar_mass_kg_mol", "conversion")
            },
        },
        "B5": {
            "malformed": malformed_matrix(root, probes),
            "injected_failures": injected_failures(root, probes),
        },
        "B8": {
            "forward": forward_attacks(forward, probes),
            "inverse": inverse_attacks(inverse, probes),
        },
    }
    results["acceptance"] = {
        "malformed_all_exit_2_no_traceback": all(
            item["exit"] == 2 and item["traceback"] is False
            for item in results["B5"]["malformed"].values()
        ),
        "solver_failures_all_exit_3_structured": all(
            item["exit"] == 3 and item["traceback"] is False and item["manifest_present"] and item["provenance_present"]
            for item in results["B5"]["injected_failures"].values()
        ),
        "originals_strict_valid": results["B8"]["forward"]["original"]["valid"] and results["B8"]["inverse"]["original"]["valid"],
        "all_rehashed_attacks_rejected": all(
            item["valid"] is False
            for group in (results["B8"]["forward"], results["B8"]["inverse"])
            for name, item in group.items()
            if name != "original"
        ),
    }
    write_json(round_dir / "hostile_probe_results.json", results)
    print(json.dumps(results["acceptance"], indent=2, sort_keys=True))
    return 0 if all(results["acceptance"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
