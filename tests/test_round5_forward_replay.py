from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from sludge_vme.config import load_case, sha256_json
from sludge_vme.io import artifacts
from sludge_vme.io.artifacts import verify_run, write_forward_run
from sludge_vme.io.manifest import file_sha256
from sludge_vme.models import simulate
from sludge_vme.models.common import R_GAS, boundary, build_context, liquid_fraction
from sludge_vme.types import CaseConfig


ROOT = Path(__file__).resolve().parents[1]
BASE = load_case(ROOT / "examples" / "tiny_synthetic.json")


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


def _rebuild_forward_descriptor(directory: Path) -> None:
    manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
    resolved = json.loads((directory / "resolved_case.json").read_text(encoding="utf-8"))
    provenance_path = directory / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    case = CaseConfig(resolved, directory / "resolved_case.json", sha256_json(resolved))
    context = build_context(case, provenance["parameter_overrides"])
    provenance["forward_semantic_replay"] = artifacts._forward_replay_descriptor(
        case_hash=case.content_hash,
        fidelity=manifest["fidelity"],
        seed=manifest["seed"],
        parameter_overrides=provenance["parameter_overrides"],
        parameter_invocation=provenance["parameter_invocation"],
        parameter_pack_hash=context.parameter_pack_hash,
        source_pack_hash=file_sha256(ROOT / "data" / "sources.json"),
    )
    _write_json(provenance_path, provenance)
    _rehash(directory, "provenance.json")


def _coherently_mutate_l0_temperature(directory: Path, delta_K: float) -> int:
    trajectory_path = directory / "state_trajectory.json"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    fields = trajectory["fields"]
    times = [float(value) for value in trajectory["coordinates"]["time_s"]]
    temperatures = fields["temperature"]["values"]
    gas_molar = fields["gas_molar_inventories"]
    open_porosity = fields["open_porosity"]["values"]
    volume_ratio = fields["volume_ratio"]["values"]
    resolved = json.loads((directory / "resolved_case.json").read_text(encoding="utf-8"))
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    case = CaseConfig(resolved, directory / "resolved_case.json", sha256_json(resolved))
    ctx = build_context(case, provenance["parameter_overrides"])

    index = 1
    temperature = float(temperatures[index]) + delta_K
    temperatures[index] = temperature
    moles = sum(float(gas_molar[name]["values"][index]) for name in gas_molar)
    fields["gas_overpressure"]["values"][index] = (
        R_GAS * temperature * moles
        / max(float(open_porosity[index]) * float(volume_ratio[index]), 1e-6)
    )
    fields["boundary_heat_cumulative"]["values"][index] = (
        float(fields["boundary_heat_cumulative"]["values"][index])
        + ctx.rho_dry * (1.0 + ctx.water_ratio) * ctx.cp * delta_K
    )
    fields["liquid_fraction"]["values"][index] = float(
        liquid_fraction(np.asarray([temperature]), ctx.oxide_flux_index)[0]
    )
    gradient = abs(boundary(ctx, times[index])["gas_temperature_K"] - temperature) * 0.12
    fields["stress_proxy"]["values"][index] = gradient * 1e6 * 1e-5 / 0.75
    _write_json(trajectory_path, trajectory)

    csv_path = directory / "state_trajectory.csv"
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    rows[index]["temperature_K"] = str(temperature)
    rows[index]["liquid_fraction"] = str(fields["liquid_fraction"]["values"][index])
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    _rehash(directory, "state_trajectory.json", "state_trajectory.csv")
    return index


def _coherently_mutate_l1_temperature(directory: Path, delta_K: float) -> tuple[int, int]:
    trajectory_path = directory / "state_trajectory.json"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    fields = trajectory["fields"]
    temperatures = fields["temperature"]["values"]
    gas_molar = fields["gas_molar_inventories"]
    resolved = json.loads((directory / "resolved_case.json").read_text(encoding="utf-8"))
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    case = CaseConfig(resolved, directory / "resolved_case.json", sha256_json(resolved))
    ctx = build_context(case, provenance["parameter_overrides"])

    time_index = 1
    cell_index = len(temperatures[time_index]) // 2
    temperature = float(temperatures[time_index][cell_index]) + delta_K
    temperatures[time_index][cell_index] = temperature
    moles = sum(
        float(gas_molar[name]["values"][time_index][cell_index])
        for name in gas_molar
    )
    pore_volume = (
        float(fields["open_porosity"]["values"][time_index][cell_index])
        * float(fields["volume_ratio"]["values"][time_index][cell_index])
    )
    fields["gas_overpressure"]["values"][time_index][cell_index] = (
        R_GAS * temperature * moles / max(pore_volume, 1e-6)
    )
    fields["boundary_heat_cumulative"]["values"][time_index] = (
        float(fields["boundary_heat_cumulative"]["values"][time_index])
        + ctx.rho_dry
        * (1.0 + ctx.water_ratio)
        * ctx.cp
        * delta_K
        / len(temperatures[time_index])
    )
    fields["liquid_fraction"]["values"][time_index][cell_index] = float(
        liquid_fraction(np.asarray([temperature]), ctx.oxide_flux_index)[0]
    )
    csv_path = directory / "state_trajectory.csv"
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    row_index = time_index * len(temperatures[time_index]) + cell_index
    rows[row_index]["temperature_K"] = str(temperature)
    rows[row_index]["liquid_fraction"] = str(
        fields["liquid_fraction"]["values"][time_index][cell_index]
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    _write_json(trajectory_path, trajectory)
    _rehash(directory, "state_trajectory.json", "state_trajectory.csv")
    return time_index, cell_index


def _coherently_mutate_l0_molar_inventory(directory: Path) -> int:
    trajectory_path = directory / "state_trajectory.json"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    fields = trajectory["fields"]
    index = len(trajectory["coordinates"]["time_s"]) // 2
    species = "H2O"
    molar_field = fields["gas_molar_inventories"][species]
    mass_field = fields["gas_concentrations"][species]
    released_field = fields["released_gas_mass_inventories"][species]
    current_field = fields["gas_current_pore_concentrations"][species]
    molar_mass = float(molar_field["molar_mass_kg_mol"])
    original_molar = float(molar_field["values"][index])
    delta_molar = max(original_molar * 0.01, 1e-6)
    delta_mass = delta_molar * molar_mass
    molar_field["values"][index] = original_molar + delta_molar
    mass_field["values"][index] = float(mass_field["values"][index]) + delta_mass
    released_field["values"][index] = float(released_field["values"][index]) - delta_mass
    pore_volume = (
        float(fields["open_porosity"]["values"][index])
        * float(fields["volume_ratio"]["values"][index])
    )
    current_field["values"][index] = (original_molar + delta_molar) / pore_volume
    total_moles = sum(
        float(item["values"][index])
        for item in fields["gas_molar_inventories"].values()
    )
    fields["gas_overpressure"]["values"][index] = (
        R_GAS
        * float(fields["temperature"]["values"][index])
        * total_moles
        / max(pore_volume, 1e-6)
    )
    _write_json(trajectory_path, trajectory)
    _rehash(directory, "state_trajectory.json")
    return index


def test_strict_forward_replay_rejects_coherently_rehashed_primary_temperature(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "coherent_temperature"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=701)
    original = verify_run(out, strict=True)
    assert original.valid is True, original.errors

    _coherently_mutate_l0_temperature(out, 10.0)
    verification = verify_run(out, strict=True)

    assert verification.valid is False
    assert verification.checks["forward_semantic_replay"] is False
    assert verification.checks["forward_replay_primary_temperature"] is False


def test_strict_forward_replay_rejects_coherent_molar_inventory_attack(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "coherent_molar_inventory"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=702)

    _coherently_mutate_l0_molar_inventory(out)
    verification = verify_run(out, strict=True)

    assert verification.valid is False
    assert verification.checks["forward_cross_artifact_semantics"] is True
    assert verification.checks["forward_replay_primary_gas_molar_inventories"] is False
    assert verification.checks["forward_semantic_replay"] is False


def test_forward_replay_tolerance_accepts_machine_roundoff_not_material_change(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "roundoff"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=703)
    temperature = float(result.fields["temperature"]["values"][1])

    _coherently_mutate_l0_temperature(out, temperature * 1e-10)
    verification = verify_run(out, strict=True)

    assert verification.valid is True, verification.errors
    assert verification.checks["forward_semantic_replay"] is True


def test_forward_replay_descriptor_separates_solver_and_semantic_tolerances(tmp_path: Path) -> None:
    parameters = {
        "grid_check": False,
        "solver_rtol": 1e-8,
        "solver_atol": 1e-11,
    }
    result = simulate(BASE, "L0", parameters)
    out = tmp_path / "trusted_tolerance_policy"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=7030)

    provenance = json.loads((out / "provenance.json").read_text(encoding="utf-8"))
    descriptor = provenance["forward_semantic_replay"]

    assert descriptor["solver_configuration"]["rtol"] == 1e-8
    assert descriptor["solver_configuration"]["atol"] == 1e-11
    assert descriptor["solver_tolerance_policy"] == {
        "policy_version": "1.0-trusted-forward-solver-tolerance-range",
        "trust_source": "verifier-owned constants in sludge_vme.io.artifacts",
        "solver_rtol": {"minimum": 1e-10, "maximum": 1e-5},
        "solver_atol": {"minimum": 1e-13, "maximum": 1e-7},
    }
    assert descriptor["comparison"]["policy_version"] == (
        "1.0-verifier-owned-forward-semantic-tolerance"
    )
    assert descriptor["comparison"]["relative_tolerance"] == 5e-6
    assert descriptor["comparison"]["absolute_tolerance"] == 5e-8
    assert "independent" in descriptor["comparison"]["basis"]

    verification = verify_run(out, strict=True)
    assert verification.valid is True, verification.errors
    assert verification.checks["forward_replay_solver_tolerance_policy"] is True


@pytest.mark.parametrize(
    ("tolerance_name", "tolerance_value"),
    [
        ("solver_rtol", 1.0),
        ("solver_atol", 1e100),
        ("solver_rtol", float("nan")),
        ("solver_atol", float("nan")),
        ("solver_rtol", float("inf")),
        ("solver_atol", float("inf")),
        ("solver_rtol", -1.0),
        ("solver_atol", -1.0),
        ("solver_rtol", 0.0),
        ("solver_atol", 0.0),
        ("solver_rtol", 1e-20),
        ("solver_atol", 1e-30),
        ("solver_rtol", "1e-6"),
        ("solver_atol", "1e-8"),
    ],
)
@pytest.mark.parametrize("material_attack", ["temperature", "molar_inventory"])
def test_strict_forward_replay_rejects_unsupported_tolerance_before_solver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tolerance_name: str,
    tolerance_value: object,
    material_attack: str,
) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / f"{material_attack}_{tolerance_name}_{tolerance_value}"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=7031)
    if material_attack == "temperature":
        _coherently_mutate_l0_temperature(out, 10.0)
    else:
        _coherently_mutate_l0_molar_inventory(out)

    provenance_path = out / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["parameter_overrides"][tolerance_name] = tolerance_value
    _write_json(provenance_path, provenance)
    _rebuild_forward_descriptor(out)

    replay_calls = 0
    real_simulate = artifacts.simulate

    def counted_simulate(*args, **kwargs):
        nonlocal replay_calls
        replay_calls += 1
        return real_simulate(*args, **kwargs)

    monkeypatch.setattr(artifacts, "simulate", counted_simulate)
    verification = verify_run(out, strict=True)

    assert verification.valid is False
    assert verification.checks["forward_semantic_replay"] is False
    assert verification.checks.get("forward_replay_solver_tolerance_policy", False) is False
    assert replay_calls == 0


def test_forward_seed_is_self_declared_integrity_metadata_not_semantic_binding(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "coherent_seed"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=7032)
    manifest_path = out / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance_path = out / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    claims = manifest["semantic_verification"]
    assert not any("seed" in claim.lower() for claim in claims["strict_semantic_claims"])
    assert any("seed" in claim.lower() for claim in claims["integrity_only_claims"])
    assert provenance["forward_semantic_replay"]["seed_role"] == (
        "self-declared run/UQ provenance only; baseline forward ODE is deterministic; "
        "coherent rewrite requires external authenticity"
    )

    manifest["seed"] += 1
    _write_json(manifest_path, manifest)
    provenance["forward_semantic_replay"]["seed"] = manifest["seed"]
    _write_json(provenance_path, provenance)
    _rehash(out, "provenance.json")

    verification = verify_run(out, strict=True)

    assert verification.valid is True, verification.errors
    assert verification.checks["forward_semantic_replay"] is True


@pytest.mark.parametrize("target", ["manifest", "descriptor"])
def test_forward_seed_one_sided_rewrite_fails_consistency_check(
    tmp_path: Path,
    target: str,
) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / f"one_sided_seed_{target}"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=7033)
    if target == "manifest":
        path = out / "run_manifest.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["seed"] += 1
        _write_json(path, payload)
    else:
        path = out / "provenance.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["forward_semantic_replay"]["seed"] += 1
        _write_json(path, payload)
        _rehash(out, "provenance.json")

    verification = verify_run(out, strict=True)

    assert verification.valid is False
    assert verification.checks["forward_semantic_replay"] is False


def test_forward_replay_ignores_mapping_order(tmp_path: Path) -> None:
    parameters = {"grid_check": False, "cp_scale": 1.01, "h_scale": 0.99}
    result = simulate(BASE, "L0", parameters)
    out = tmp_path / "mapping_order"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=704)
    provenance_path = out / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["parameter_overrides"] = {
        key: provenance["parameter_overrides"][key]
        for key in reversed(list(provenance["parameter_overrides"]))
    }
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    _rehash(out, "provenance.json")

    verification = verify_run(out, strict=True)

    assert verification.valid is True, verification.errors
    assert verification.checks["forward_semantic_replay"] is True


def test_standard_l1_strict_replays_full_solver_and_grid_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = simulate(BASE, "L1")
    out = tmp_path / "l1"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=7041)

    replay_calls = 0
    real_simulate = artifacts.simulate

    def counted_simulate(*args, **kwargs):
        nonlocal replay_calls
        replay_calls += 1
        return real_simulate(*args, **kwargs)

    monkeypatch.setattr(artifacts, "simulate", counted_simulate)
    verification = verify_run(out, strict=True)
    provenance = json.loads((out / "provenance.json").read_text(encoding="utf-8"))

    assert verification.valid is True, verification.errors
    assert verification.checks["forward_semantic_replay"] is True
    assert verification.checks["forward_replay_primary_temperature"] is True
    assert replay_calls == 1
    assert provenance["forward_semantic_replay"]["solver_configuration"]["grid_check"] is True
    assert provenance["forward_semantic_replay"]["solver_configuration"]["grid_check_cells"] == [21, 41]

    default_attack = tmp_path / "l1_default_plus_10K"
    shutil.copytree(out, default_attack)
    _coherently_mutate_l1_temperature(default_attack, 10.0)
    replay_calls = 0
    attacked = verify_run(default_attack, strict=True)
    assert attacked.valid is False
    assert attacked.checks["forward_replay_primary_temperature"] is False
    assert replay_calls == 1

    invalid_tolerances = [
        ("solver_rtol", 1.0),
        ("solver_atol", 1e100),
        ("solver_rtol", float("nan")),
        ("solver_atol", float("nan")),
        ("solver_rtol", float("inf")),
        ("solver_atol", float("inf")),
        ("solver_rtol", -1.0),
        ("solver_atol", -1.0),
        ("solver_rtol", 0.0),
        ("solver_atol", 0.0),
        ("solver_rtol", 1e-20),
        ("solver_atol", 1e-30),
        ("solver_rtol", "1e-6"),
        ("solver_atol", "1e-8"),
    ]
    for attack_index, (tolerance_name, tolerance_value) in enumerate(invalid_tolerances):
        tolerance_attack = tmp_path / f"l1_tolerance_attack_{attack_index}"
        shutil.copytree(out, tolerance_attack)
        _coherently_mutate_l1_temperature(tolerance_attack, 10.0)
        provenance_path = tolerance_attack / "provenance.json"
        attack_provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        attack_provenance["parameter_overrides"][tolerance_name] = tolerance_value
        _write_json(provenance_path, attack_provenance)
        _rebuild_forward_descriptor(tolerance_attack)
        replay_calls = 0

        rejected = verify_run(tolerance_attack, strict=True)

        assert rejected.valid is False
        assert rejected.checks["forward_semantic_replay"] is False
        assert rejected.checks.get("forward_replay_solver_tolerance_policy", False) is False
        assert replay_calls == 0


@pytest.mark.parametrize(
    ("target", "mutation"),
    [
        ("provenance", "remove_descriptor"),
        ("provenance", "solver_digest"),
        ("manifest", "source_digest"),
        ("manifest", "solver_version"),
        ("manifest", "solver_statistics"),
        ("manifest", "malformed_software"),
    ],
)
def test_strict_forward_replay_rejects_missing_or_tampered_provenance(
    tmp_path: Path,
    target: str,
    mutation: str,
) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / mutation
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=705)
    path = out / ("provenance.json" if target == "provenance" else "run_manifest.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "remove_descriptor":
        del payload["forward_semantic_replay"]
    elif mutation == "solver_digest":
        payload["forward_semantic_replay"]["solver_configuration_sha256"] = "0" * 64
    elif mutation == "source_digest":
        payload["source_pack_hash"] = "0" * 64
    elif mutation == "solver_statistics":
        payload["solver_statistics"]["rtol"] *= 100.0
    elif mutation == "malformed_software":
        payload["software"] = []
    else:
        payload["software"]["scipy"] = "0.0-forged"
    _write_json(path, payload)
    if target == "provenance":
        _rehash(out, "provenance.json")

    verification = verify_run(out, strict=True)

    assert verification.valid is False
    assert verification.checks["forward_semantic_replay"] is False


def test_explicit_custom_fixture_is_labeled_not_evaluated_without_ode_claim(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "manufactured"
    write_forward_run(
        out,
        BASE,
        result,
        cli_args=["forward"],
        seed=706,
        semantic_replay="not_evaluated",
    )

    verification = verify_run(out, strict=True)
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))

    assert verification.valid is False
    assert verification.checks["forward_semantic_replay"] == "not_evaluated"
    assert any("not evaluated" in error for error in verification.errors)
    assert manifest["semantic_verification"]["forward_semantic_replay"] == "not_evaluated"
    assert "complete forward ODE primary trajectory" in manifest["semantic_verification"]["integrity_only_claims"]
    assert "complete L0/L1 ODE primary trajectory" not in manifest["semantic_verification"]["strict_semantic_claims"]
