from __future__ import annotations

import copy
import hashlib
import json
from argparse import Namespace
from pathlib import Path

import pytest
import numpy as np
from scipy.stats import qmc

from sludge_vme import cli as cli_module
from sludge_vme.config import load_case, sha256_json
from sludge_vme.inverse.pareto import nondominated_mask
from sludge_vme.inverse.search import InverseResult, _design_space, _forward_primary_state_hash, _rank_stability, _record_from_results
from sludge_vme.inverse.transforms import design_from_unit
from sludge_vme.io import artifacts as artifact_module
from sludge_vme.io.artifacts import verify_run, write_forward_run, write_inverse_run
from sludge_vme.models import simulate
from sludge_vme.types import CaseConfig


ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "examples" / "tiny_synthetic.json"
BASE = load_case(CASE_PATH)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rehash(directory: Path, *names: str) -> None:
    manifest_path = directory / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in names:
        payload = (directory / name).read_bytes()
        manifest["artifacts"][name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    _write_json(manifest_path, manifest)


def _all_output_text(directory: Path, captured: pytest.CaptureFixture[str]) -> str:
    streams = captured.readouterr()
    payloads = [streams.out, streams.err]
    if directory.parent.exists():
        for path in directory.parent.rglob("*"):
            if path.is_file():
                payloads.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(payloads)


@pytest.mark.parametrize(
    "lane",
    ["forward_L0", "forward_L1", "inverse", "benchmark_L0", "benchmark_L1"],
)
def test_structured_failure_never_persists_exception_text_or_user_controlled_class_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    lane: str,
) -> None:
    sentinels = [
        f"token-canary-{lane}",
        f"key-canary-{lane}",
        f"password-canary-{lane}",
        f"eyJhbGciOiJub25lIn0.{lane}.signature",
        f"Bearer canary-{lane}",
        f"person-{lane}@example.invalid",
        f"+1-202-555-{1000 + len(lane)}",
        f"Authorization: Basic canary-{lane}",
        f"https://example.invalid/callback?credential=canary-{lane}",
        f"«private-canary-{lane}»",
    ]
    message = " | ".join(sentinels)
    controlled_exception = type(f"UserControlled{lane}CredentialError", (Exception,), {})
    out = tmp_path / lane
    original_simulate = simulate

    if lane.startswith("forward"):
        fidelity = lane.removeprefix("forward_")
        monkeypatch.setattr(cli_module, "simulate", lambda *args, **kwargs: (_ for _ in ()).throw(controlled_exception(message)))
        exit_code = cli_module.command_forward(
            Namespace(case=CASE_PATH, fidelity=fidelity, out=out, uq_power=None, seed=41, overwrite=False)
        )
    elif lane == "inverse":
        monkeypatch.setattr(cli_module, "run_inverse", lambda *args, **kwargs: (_ for _ in ()).throw(controlled_exception(message)))
        exit_code = cli_module.command_inverse(
            Namespace(case=CASE_PATH, budget="tiny", out=out, seed=42, overwrite=False)
        )
    else:
        calls = 0

        def benchmark_simulate(case, fidelity):
            nonlocal calls
            calls += 1
            if lane == "benchmark_L0" or calls == 2:
                raise controlled_exception(message)
            return original_simulate(case, fidelity, {"grid_check": False})

        monkeypatch.setattr(cli_module, "simulate", benchmark_simulate)
        exit_code = cli_module.command_benchmark(
            Namespace(case=CASE_PATH, out=out, seed=43, overwrite=False)
        )

    assert exit_code == cli_module.EXIT_SOLVER
    status = json.loads((out / "status.json").read_text(encoding="utf-8"))
    assert status["exception"] == {"category": "unexpected_error"}
    assert set(status) == {"code", "success", "stage", "reason", "exception"}
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["cli_args"] == []
    assert manifest["failure"]["exception_category"] == "unexpected_error"
    joined = _all_output_text(out, capsys)
    assert controlled_exception.__name__ not in joined
    assert all(sentinel not in joined for sentinel in sentinels)


def test_top_level_cli_error_does_not_echo_user_controlled_exception_text(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sentinel = "credential-canary-in-missing-path"
    missing = tmp_path / sentinel / "case.json"
    exit_code = cli_module.main(["validate", str(missing), "--json"])
    captured = capsys.readouterr()

    assert exit_code == cli_module.EXIT_INTERNAL
    assert sentinel not in captured.out + captured.err
    assert "reason=internal_io_error" in captured.err
    assert "category=io_error" in captured.err


def test_forward_manifest_declares_semantic_and_integrity_only_claims(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "contract"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=51)

    trajectory = json.loads((out / "state_trajectory.json").read_text(encoding="utf-8"))
    contract = trajectory["semantic_contract"]
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    claims = manifest["semantic_verification"]

    assert contract["verification_mode"] == "primary_state_recomputation"
    assert "fields.boundary_heat_cumulative" in contract["strict_semantic_claims"]
    assert "fields.gas_overpressure" in contract["strict_semantic_claims"]
    assert contract["integrity_only_fields"] == []
    assert "uncertainty.json" in claims["integrity_only_claims"]
    assert "report.md prose" in claims["integrity_only_claims"]
    assert verify_run(out, strict=True).valid is True


@pytest.mark.parametrize(
    "attack",
    [
        "boundary_heat_interior",
        "reaction_heat_interior",
        "overpressure_interior_and_extrema",
        "mass_unit",
        "molar_basis",
        "current_pore_species",
        "released_conversion",
        "temperature_unit",
        "porosity_basis",
        "declared_shape",
    ],
)
def test_strict_forward_rejects_rehashed_full_trajectory_and_schema_attacks(
    tmp_path: Path,
    attack: str,
) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / attack
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=52)
    assert verify_run(out, strict=True).valid is True
    trajectory_path = out / "state_trajectory.json"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    fields = trajectory["fields"]
    changed = ["state_trajectory.json"]

    if attack in {"boundary_heat_interior", "reaction_heat_interior"}:
        name = attack.removesuffix("_interior") + "_cumulative"
        values = fields[name]["values"]
        index = len(values) // 2
        values[index] = float(values[index]) + max(1.0, abs(float(values[index])) * 0.01)
    elif attack == "overpressure_interior_and_extrema":
        values = fields["gas_overpressure"]["values"]
        index = max(range(len(values)), key=lambda item: float(values[item]))
        values[index] = float(values[index]) * 0.5
        summary_path = out / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        new_max = max(float(value) for value in values)
        summary["max_overpressure_Pa"]["value"] = new_max
        summary["bloating_risk"]["value"] = new_max / 4.5e8
        _write_json(summary_path, summary)
        changed.append("summary.json")
    elif attack == "mass_unit":
        fields["gas_concentrations"]["H2O"]["unit"] = "mol/m3_reference_bulk"
    elif attack == "molar_basis":
        fields["gas_molar_inventories"]["CO2"]["basis"] = "attacker supplied basis"
    elif attack == "current_pore_species":
        fields["gas_current_pore_concentrations"]["N2"]["species"] = "CO2"
    elif attack == "released_conversion":
        fields["released_gas_mass_inventories"]["SO2"]["conversion"] = "attacker supplied conversion"
    elif attack == "temperature_unit":
        fields["temperature"]["unit"] = "degC"
    elif attack == "porosity_basis":
        fields["open_porosity"]["basis"] = "initial volume"
    else:
        trajectory["semantic_contract"]["fields"]["temperature"]["shape"] = ["cell", "time"]

    _write_json(trajectory_path, trajectory)
    _rehash(out, *changed)
    verification = verify_run(out, strict=True)
    assert verification.valid is False, attack
    assert any(
        name in verification.checks and verification.checks[name] is False
        for name in ("forward_field_schema_contract", "recomputed_boundary_heat_trajectory", "recomputed_reaction_heat_trajectory", "recomputed_gas_overpressure_trajectory")
    ), (attack, verification.errors, verification.checks)


@pytest.mark.parametrize("attack", ["unit", "proxy", "status", "validity"])
def test_strict_forward_rejects_rehashed_summary_metadata_attacks(tmp_path: Path, attack: str) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / f"summary_{attack}"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=53)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if attack == "unit":
        summary["max_overpressure_Pa"]["unit"] = "kPa"
    elif attack == "proxy":
        summary["open_porosity"]["proxy"] = False
    elif attack == "status":
        summary["environmental_status"]["status"] = "passed"
    else:
        summary["effective_true_density_kg_m3"]["validity"] = "attacker supplied validity"
    _write_json(summary_path, summary)
    _rehash(out, "summary.json")
    verification = verify_run(out, strict=True)
    assert verification.valid is False
    assert verification.checks["forward_summary_schema_contract"] is False


def test_inverse_policy_record_binds_sampler_and_forward_primary_state_without_solver_message() -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    parameters = {"grid_check": False, "cp_scale": 1.03}
    record = _record_from_results(
        BASE,
        {"sludge_dry_mass_fraction": 0.08},
        7,
        "L0",
        [result],
        policy_provenance=[
            {
                "sample_id": "L0-design-0007-policy-0000",
                "sampler_seed": 4242,
                "parameters": parameters,
                "sampler_algorithm": "scipy_sobol_parameter_policy_v1",
            }
        ],
    )

    sample = record["policy_samples"][0]
    assert sample["sample_id"] == "L0-design-0007-policy-0000"
    assert sample["sampler_seed"] == 4242
    assert sample["parameters"] == parameters
    assert sample["sampler_algorithm"] == "scipy_sobol_parameter_policy_v1"
    assert sample["forward_case_hash"] == BASE.content_hash
    assert sample["forward_parameter_pack_hash"] == result.provenance["parameter_pack_hash"]
    assert len(sample["forward_primary_state_sha256"]) == 64
    assert "message" not in sample


def test_forward_primary_state_hash_is_stable_to_solver_roundoff_but_not_material_changes() -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    roundoff = copy.deepcopy(result)
    roundoff.fields["temperature"]["values"][10] *= 1.0 + 1e-10
    material = copy.deepcopy(result)
    material.fields["temperature"]["values"][10] *= 1.0 + 1e-5

    baseline_hash = _forward_primary_state_hash(result)
    assert _forward_primary_state_hash(roundoff) == baseline_hash
    assert _forward_primary_state_hash(material) != baseline_hash


def test_forward_primary_state_hash_ignores_nonsemantic_mapping_order() -> None:
    reordered_raw = copy.deepcopy(BASE.raw)
    reordered_raw["feedstocks"] = {
        name: reordered_raw["feedstocks"][name]
        for name in sorted(reordered_raw["feedstocks"])
    }
    reordered_case = CaseConfig(reordered_raw, BASE.source_path, sha256_json(reordered_raw))
    assert reordered_case.content_hash == BASE.content_hash

    baseline = simulate(BASE, "L0", {"grid_check": False})
    reordered = simulate(reordered_case, "L0", {"grid_check": False})
    assert _forward_primary_state_hash(reordered) == _forward_primary_state_hash(baseline)


@pytest.fixture(scope="module")
def deterministic_inverse_fixture() -> tuple[CaseConfig, InverseResult, int]:
    seed = 6161
    raw = copy.deepcopy(BASE.raw)
    raw["inverse_design"]["tiny"] = {
        "sobol_designs": 2,
        "l0_uncertainty_samples": 1,
        "l1_shortlist": 2,
        "l1_uncertainty_samples": 1,
    }
    case = CaseConfig(raw, BASE.source_path, sha256_json(raw))
    points = qmc.Sobol(d=12, scramble=True, seed=seed).random_base2(1)
    l0_records = []
    l1_records = []
    for design_id, point in enumerate(points):
        design_case, decision = design_from_unit(case, point, design_id)
        parameters = {"grid_check": False}
        forward = simulate(design_case, "L0", parameters)
        l0_records.append(_record_from_results(
            design_case,
            decision,
            design_id,
            "L0",
            [forward],
            policy_provenance=[{
                "sample_id": f"L0-design-{design_id:04d}-policy-0000",
                "sampler_seed": seed + 31 * (design_id + 1),
                "parameters": parameters,
                "sampler_algorithm": "scipy_sobol_parameter_policy_v1",
            }],
        ))
        l1_records.append(_record_from_results(
            design_case,
            decision,
            design_id,
            "L1",
            [forward],
            grid_converged=True,
            policy_provenance=[{
                "sample_id": f"L1-design-{design_id:04d}-grid-baseline",
                "sampler_seed": None,
                "parameters": {"grid_check": True},
                "sampler_algorithm": "fixed_grid_convergence_baseline_v1",
            }],
        ))
    ranked = sorted(l1_records, key=lambda record: sum(float(value) for value in record["objectives"]))
    mask = nondominated_mask(
        np.asarray([record["objectives"] for record in ranked], dtype=float),
        np.ones(len(ranked), dtype=bool),
    )
    pareto = [record for record, keep in zip(ranked, mask) if keep]
    result = InverseResult(
        status="success",
        seed=seed,
        budget="tiny",
        all_evaluations=[*l0_records, *l1_records],
        feasible_set=l0_records,
        pareto_set=pareto,
        ranked_candidates=ranked,
        rank_stability=_rank_stability(
            [record["quality_margin"]["q05"] for record in l0_records],
            [record["quality_margin"]["q05"] for record in l1_records],
        ),
        active_constraints=sorted({name for record in ranked for name in record["active_constraints"]}),
        l0_l1_disagreement=[],
        environmental_status="not_evaluated",
        warnings=[
            "Inverse output is a robust synthetic screening set, not a unique optimum or plant recipe.",
            "Policy-distribution quantiles are not empirical confidence intervals.",
            "Environmental thresholds are absent and therefore not_evaluated, never passed.",
            "Any real recipe, speed window, trial or control connection requires independent validation and human approval.",
        ],
        design_space=_design_space(case),
    )
    return case, result, seed


def _write_evaluations(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "attack",
    ["delete_l0", "add_l0", "reorder_l0", "nonpareto_source", "coherent_pareto_decision", "constraint", "nondominance"],
)
def test_strict_inverse_replay_rejects_rehashed_record_and_pareto_attacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    deterministic_inverse_fixture: tuple[CaseConfig, InverseResult, int],
    attack: str,
) -> None:
    case, expected_result, seed = deterministic_inverse_fixture
    monkeypatch.setattr(artifact_module, "run_inverse", lambda *args, **kwargs: copy.deepcopy(expected_result))
    artifact_module._INVERSE_REPLAY_CACHE.clear()
    out = tmp_path / attack
    write_inverse_run(out, case, copy.deepcopy(expected_result), cli_args=["inverse"], seed=seed)
    original = verify_run(out, strict=True)
    assert original.valid is True, original.errors

    evaluations_path = out / "all_evaluations.jsonl"
    evaluations = [json.loads(line) for line in evaluations_path.read_text(encoding="utf-8").splitlines()]
    changed = ["all_evaluations.jsonl"]
    if attack == "delete_l0":
        removed = next(index for index, record in enumerate(evaluations) if record["fidelity"] == "L0")
        record = evaluations.pop(removed)
        summary_path = out / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["evaluated_designs"] -= 1
        summary["evaluation_records"] -= 1
        if record["constraints"]["all_hard_constraints"]:
            summary["l0_feasible_designs"] -= 1
        _write_json(summary_path, summary)
        changed.append("summary.json")
    elif attack == "add_l0":
        added = copy.deepcopy(next(record for record in evaluations if record["fidelity"] == "L0"))
        added["design_id"] = 99
        evaluations.insert(2, added)
        summary_path = out / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["evaluated_designs"] += 1
        summary["evaluation_records"] += 1
        summary["l0_feasible_designs"] += 1
        _write_json(summary_path, summary)
        changed.append("summary.json")
    elif attack == "reorder_l0":
        evaluations[0], evaluations[1] = evaluations[1], evaluations[0]
    elif attack == "nonpareto_source":
        source = next(record for record in evaluations if record["fidelity"] == "L0")
        source["model_flags"].append("attacker_modified_nonpareto_source")
    elif attack == "coherent_pareto_decision":
        pareto_path = out / "pareto.json"
        pareto = json.loads(pareto_path.read_text(encoding="utf-8"))
        candidate = pareto[0]
        old_speed = float(candidate["decision"]["speed_ratio"])
        low, high = case.raw["inverse_design"]["speed_ratio_bounds"]
        new_speed = float(low + high - old_speed)
        candidate["decision"]["speed_ratio"] = new_speed
        source = next(record for record in evaluations if record["design_id"] == candidate["design_id"] and record["fidelity"] == "L1")
        source["decision"]["speed_ratio"] = new_speed
        source["source_hashes"]["case"] = artifact_module._inverse_case_hash(case.raw, source)
        candidate["source_hashes"]["case"] = source["source_hashes"]["case"]
        _write_json(pareto_path, pareto)
        artifact_module._write_pareto_csv(out / "pareto.csv", pareto)
        l1_ranked = [record for record in evaluations if record["fidelity"] == "L1" and record["constraints"]["all_hard_constraints"]]
        _write_json(out / "feasible_windows.json", artifact_module._feasible_windows(l1_ranked))
        changed.extend(["pareto.json", "pareto.csv", "feasible_windows.json"])
    elif attack == "constraint":
        source = next(record for record in evaluations if record["fidelity"] == "L1")
        source["constraint_slacks"]["q95_enabled_risk"] += 0.25
        pareto_path = out / "pareto.json"
        pareto = json.loads(pareto_path.read_text(encoding="utf-8"))
        for candidate in pareto:
            if candidate["design_id"] == source["design_id"]:
                candidate["constraint_slacks"]["q95_enabled_risk"] += 0.25
        _write_json(pareto_path, pareto)
        changed.append("pareto.json")
    else:
        source = next(record for record in evaluations if record["fidelity"] == "L1")
        source["objectives"] = [float(value) + 0.25 for value in source["objectives"]]
        pareto_path = out / "pareto.json"
        pareto = json.loads(pareto_path.read_text(encoding="utf-8"))
        for candidate in pareto:
            if candidate["design_id"] == source["design_id"]:
                candidate["objectives"] = list(source["objectives"])
        _write_json(pareto_path, pareto)
        changed.append("pareto.json")

    _write_evaluations(evaluations_path, evaluations)
    _rehash(out, *changed)
    verification = verify_run(out, strict=True)
    assert verification.valid is False, attack
    assert verification.checks.get("inverse_deterministic_replay") is False
