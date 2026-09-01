from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest
import numpy as np

from sludge_vme.config import load_case, sha256_json
from sludge_vme import cli as cli_module
from sludge_vme.inverse.search import _record_from_results
from sludge_vme.inverse.search import _rank_stability
from sludge_vme.inverse.constraints import constraint_record
from sludge_vme.inverse.pareto import nondominated_mask
from sludge_vme.inverse.transforms import design_from_unit
from sludge_vme.models import simulate
from sludge_vme.models.common import GAS_MOLAR_MASS_KG_MOL, build_context
from sludge_vme.models.fvm import conservative_molar_fick_rate, current_pore_molar_concentration
from sludge_vme.io.artifacts import _feasible_windows, verify_run, write_forward_run, write_inverse_run
from sludge_vme.types import CaseConfig, RunStatus
from sludge_vme.validation import validate_case


ROOT = Path(__file__).resolve().parents[1]
BASE = load_case(ROOT / "examples" / "tiny_synthetic.json")


def mutated_case(mutator) -> CaseConfig:
    raw = copy.deepcopy(BASE.raw)
    mutator(raw)
    return CaseConfig(raw, BASE.source_path, sha256_json(raw))


def rehash_artifact(directory: Path, name: str) -> None:
    path = directory / name
    manifest_path = directory / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    payload = path.read_bytes()
    manifest["artifacts"][name] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


@pytest.mark.parametrize(
    "mutator, expected_code",
    [
        (lambda raw: raw["forming"].update(moisture_wet_basis=1.0), "invalid_forming_moisture"),
        (lambda raw: raw["geometry"].update(brick_half_thickness_m=0.0), "invalid_positive_value"),
        (lambda raw: raw["kiln"].update(reference_speed_m_s=0.0), "invalid_positive_value"),
        (lambda raw: raw["kiln"]["profile"][1].update(h_W_m2_K=-1.0), "invalid_positive_value"),
        (lambda raw: raw["kiln"]["profile"][1].update(km_m_s=-1.0), "invalid_positive_value"),
        (lambda raw: raw["kiln"]["profile"][1].update(ambient_pressure_Pa=-1.0), "invalid_positive_value"),
        (lambda raw: raw["kiln"]["profile"][1].update(gas_temperature_K=float("nan")), "missing_boundary_value"),
        (lambda raw: raw["kiln"].update(length_m=99.0), "kiln_profile_endpoint_mismatch"),
        (lambda raw: raw["kiln"].update(speed_ratio_bounds=[1.2, 0.8]), "invalid_bounds"),
        (lambda raw: raw["quality_targets"]["bulk_density_kg_m3"].update(min=2200.0, max=1400.0), "invalid_bounds"),
        (lambda raw: raw["inverse_design"]["tiny"].update(sobol_designs=3), "invalid_power_of_two_count"),
        (lambda raw: raw["inverse_design"]["tiny"].update(l1_shortlist=0), "invalid_positive_count"),
    ],
)
def test_validator_rejects_cross_field_and_positive_invariant_mutations(mutator, expected_code: str) -> None:
    report = validate_case(mutated_case(mutator))
    assert report.valid is False
    assert expected_code in {issue.code for issue in report.errors}


@pytest.mark.parametrize("failed_count", [1, 3, 4])
def test_inverse_required_policy_sample_failures_are_fail_safe_and_auditable(failed_count: int) -> None:
    successful = simulate(BASE, "L0", {"grid_check": False})
    results = []
    for sample_index in range(4):
        item = copy.deepcopy(successful)
        if sample_index < failed_count:
            item.status = RunStatus("solver_failure", f"manufactured failure {sample_index}", False)
        results.append(item)

    record = _record_from_results(
        BASE,
        {"sludge_dry_mass_fraction": 0.08},
        17,
        "L0",
        results,
    )

    assert record["status"] == "infeasible"
    assert record["constraints"]["all_hard_constraints"] is False
    assert record["constraints"]["required_policy_samples_successful"] is False
    assert record["failure_rate"] == pytest.approx(failed_count / 4)
    assert len(record["policy_samples"]) == 4
    assert sum(item["success"] is False for item in record["policy_samples"]) == failed_count
    assert all(item["status"] for item in record["policy_samples"])
    assert all("message" not in item for item in record["policy_samples"])
    assert all(item["forward_primary_state_sha256"] for item in record["policy_samples"])


def test_feed_moisture_morphology_and_oxide_fingerprint_are_not_phantom() -> None:
    base = simulate(BASE, "L0", {"grid_check": False})
    wetter = simulate(
        mutated_case(lambda raw: raw["feedstocks"]["sludge"].update(free_moisture_wet_basis=0.59)),
        "L0",
        {"grid_check": False},
    )
    rounder = simulate(
        mutated_case(
            lambda raw: raw["feedstocks"]["sludge"].update(
                morphology={"sphericity": 0.95, "aspect_ratio": 1.2}
            )
        ),
        "L0",
        {"grid_check": False},
    )

    def all_hematite(raw) -> None:
        raw["feedstocks"]["sludge"]["components"][-1]["oxide_fractions"] = {"Fe2O3": 1.0}

    hematite = simulate(mutated_case(all_hematite), "L0", {"grid_check": False})

    assert wetter.summary["as_received_water_kg_per_kg_dry"]["value"] != pytest.approx(
        base.summary["as_received_water_kg_per_kg_dry"]["value"]
    )
    assert wetter.fields["temperature"]["values"][-1] != pytest.approx(
        base.fields["temperature"]["values"][-1]
    )
    assert rounder.summary["effective_permeability_m2"]["value"] != pytest.approx(
        base.summary["effective_permeability_m2"]["value"], rel=1e-6, abs=0.0
    )
    assert rounder.summary["max_overpressure_Pa"]["value"] != pytest.approx(
        base.summary["max_overpressure_Pa"]["value"]
    )
    assert hematite.summary["oxide_flux_index"]["value"] != pytest.approx(
        base.summary["oxide_flux_index"]["value"]
    )
    assert hematite.summary["liquid_fraction"]["value"] != pytest.approx(
        base.summary["liquid_fraction"]["value"]
    )
    assert hematite.summary["liquid_fraction"]["status"] == "unresolved_oxide_liquid_database"


@pytest.mark.parametrize("oxygen_fraction", [0.0, 1.0e-5, 1.0])
def test_organic_oxidation_is_bounded_by_finite_oxygen_inventory_and_flux(oxygen_fraction: float) -> None:
    def set_oxygen(raw) -> None:
        for knot in raw["kiln"]["profile"]:
            knot["oxygen_mole_fraction"] = oxygen_fraction

    result = simulate(mutated_case(set_oxygen), "L0", {"grid_check": False})
    assert result.status.success, result.status.message
    ledger = result.summary["oxygen_ledger_mol_O2_per_m3_reference"]["value"]
    completion = result.summary["reaction_completion"]["value"]["organic_oxidation"]

    assert ledger["consumed"] <= ledger["initial_inventory"] + ledger["boundary_supplied"] + 1e-8
    assert ledger["residual"] >= -1e-8
    assert completion <= ledger["stoichiometric_completion_cap"] + 1e-8
    assert result.conservation["max_element_relative_residual"] < 1e-8
    assert result.summary["emissions_coverage"]["status"] == "not_evaluated"
    assert result.summary["emissions_coverage"]["value"]["coverage_gaps"] == ["CO", "VOC", "NOx"]
    if oxygen_fraction == 0.0:
        assert completion == pytest.approx(0.0, abs=1e-12)
        assert ledger["consumed"] == pytest.approx(0.0, abs=1e-12)
        assert ledger["initial_inventory"] == pytest.approx(0.0, abs=1e-12)
        assert ledger["boundary_supplied"] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("species", ["H2O", "CO2"])
def test_current_pore_molar_fick_flux_uses_phi_and_deforming_geometry_conservatively(species: str) -> None:
    porosity = np.array([0.20, 0.30, 0.40, 0.50])
    volume_ratio = np.array([0.80, 0.90, 1.00, 1.10])
    uniform_current_molar_concentration = 2.5
    reference_molar_inventory = uniform_current_molar_concentration * porosity * volume_ratio

    recovered = current_pore_molar_concentration(reference_molar_inventory, porosity, volume_ratio)
    rate, surface_outflow = conservative_molar_fick_rate(
        reference_molar_inventory,
        porosity,
        volume_ratio,
        diffusivity_m2_s=2.0e-7,
        dx_reference_m=0.01,
        surface_transfer_m_s=0.0,
    )

    assert GAS_MOLAR_MASS_KG_MOL[species] > 0.0
    assert recovered == pytest.approx(np.full(4, uniform_current_molar_concentration))
    assert rate == pytest.approx(np.zeros(4), abs=1e-18)
    assert surface_outflow == pytest.approx(0.0, abs=1e-18)

    gradient_molar_inventory = np.array([0.2, 0.4, 0.9, 1.6])
    gradient_rate, surface_outflow = conservative_molar_fick_rate(
        gradient_molar_inventory,
        porosity,
        volume_ratio,
        diffusivity_m2_s=2.0e-7,
        dx_reference_m=0.01,
        surface_transfer_m_s=1.0e-5,
    )
    assert np.max(np.abs(gradient_rate)) > 0.0
    assert float(np.sum(gradient_rate) * 0.01 + surface_outflow) == pytest.approx(0.0, abs=1e-14)

    changed_geometry_rate, _ = conservative_molar_fick_rate(
        gradient_molar_inventory,
        porosity * 0.8,
        volume_ratio * 0.9,
        diffusivity_m2_s=2.0e-7,
        dx_reference_m=0.01,
        surface_transfer_m_s=1.0e-5,
    )
    assert changed_geometry_rate != pytest.approx(gradient_rate)


def test_equal_molar_gradients_have_equal_molar_flux_for_different_molar_mass_species() -> None:
    porosity = np.array([0.25, 0.30, 0.35])
    volume_ratio = np.array([0.90, 1.00, 1.10])
    current_molar_concentration = np.array([1.0, 1.5, 2.25])
    reference_molar_inventory = current_molar_concentration * porosity * volume_ratio

    species_fluxes = {}
    mass_storage_rates = {}
    for species in ("H2O", "CO2"):
        molar_mass = GAS_MOLAR_MASS_KG_MOL[species]
        reference_mass_inventory = reference_molar_inventory * molar_mass
        recovered_moles = reference_mass_inventory / molar_mass
        molar_rate, molar_outflow = conservative_molar_fick_rate(
            recovered_moles,
            porosity,
            volume_ratio,
            diffusivity_m2_s=3.0e-7,
            dx_reference_m=0.02,
            surface_transfer_m_s=2.0e-5,
        )
        species_fluxes[species] = molar_outflow
        mass_storage_rates[species] = molar_rate * molar_mass

    assert GAS_MOLAR_MASS_KG_MOL["H2O"] != pytest.approx(GAS_MOLAR_MASS_KG_MOL["CO2"])
    assert species_fluxes["H2O"] == pytest.approx(species_fluxes["CO2"])
    assert mass_storage_rates["H2O"] != pytest.approx(mass_storage_rates["CO2"])


def test_l1_serializes_current_pore_concentration_and_agrees_with_l0_at_low_gradient(recwarn) -> None:
    parameters = {
        "grid_check": False,
        "cells": 5,
        "conductivity_scale": 100.0,
        "diffusivity_scale": 100.0,
        "mass_transfer_scale": 0.0,
        "solver_rtol": 1e-7,
        "solver_atol": 1e-10,
    }
    l0 = simulate(BASE, "L0", parameters)
    l1 = simulate(BASE, "L1", parameters)
    assert l0.status.success, l0.status.message
    assert l1.status.success, l1.status.message
    mass_inventory = l1.fields["gas_concentrations"]["H2O"]
    molar_inventory = l1.fields["gas_molar_inventories"]["H2O"]
    current_pore = l1.fields["gas_current_pore_concentrations"]["H2O"]
    assert mass_inventory["basis"] == "conservative species mass inventory per reference bulk volume"
    assert mass_inventory["unit"] == "kg/m3_reference_bulk"
    assert molar_inventory["basis"] == "conservative species molar inventory per reference bulk volume; mass_inventory/molar_mass"
    assert molar_inventory["unit"] == "mol/m3_reference_bulk"
    assert current_pore["basis"] == "current pore volume; molar_inventory/(phi_open*J)"
    assert current_pore["unit"] == "mol/m3_current_pore"
    assert current_pore["species"] == "H2O"
    assert current_pore["molar_mass_kg_mol"] == pytest.approx(GAS_MOLAR_MASS_KG_MOL["H2O"])
    assert current_pore["conversion"] == "mass_storage / molar_mass / (phi_open * J)"
    assert l1.conservation["gas_species_relative_residual"] < 1e-8
    assert l1.summary["reaction_completion"]["value"]["organic_oxidation"] == pytest.approx(
        l0.summary["reaction_completion"]["value"]["organic_oxidation"], rel=0.05, abs=1e-6
    )
    assert not [warning for warning in recwarn if warning.category is RuntimeWarning]


def test_thermo_coverage_is_traceable_composition_sensitive_and_never_fake_hard_pass() -> None:
    base = simulate(BASE, "L0", {"grid_check": False})
    assert "oxide_liquid_ideal_pseudo" not in base.summary["phase_amounts"]["value"]
    assert "oxide_liquid_unresolved_screening_proxy" in base.summary["phase_amounts"]["value"]
    assert not any("Ideal pseudo-liquid" in warning for warning in base.warnings)
    assert any("unresolved oxide-liquid screening proxy" in warning for warning in base.warnings)

    def remove_quartz(raw) -> None:
        components = raw["feedstocks"]["sludge"]["components"]
        quartz = next(item for item in components if item["id"] == "quartz")
        removed = quartz["fraction"]
        components.remove(quartz)
        next(item for item in components if item["id"] == "amorphous_oxide_pool")["fraction"] += removed

    without_phase = simulate(mutated_case(remove_quartz), "L0", {"grid_check": False})

    def all_hematite(raw) -> None:
        raw["feedstocks"]["sludge"]["components"][-1]["oxide_fractions"] = {"Fe2O3": 1.0}

    out_of_domain = simulate(mutated_case(all_hematite), "L0", {"grid_check": False})

    base_coverage = base.summary["thermo_coverage_score"]
    assert base_coverage["status"] == "not_evaluated_missing_oxide_liquid_database"
    assert base.provenance["thermo_backend_call"]["backend"] == "MinimalGibbsBackend"
    assert base.provenance["thermo_backend_call"]["source_hash"]
    assert base.provenance["thermo_backend_call"]["status"] == "failure_no_covered_phases"
    assert without_phase.summary["thermo_coverage_score"]["value"] != pytest.approx(base_coverage["value"])
    assert out_of_domain.summary["thermo_coverage_score"]["status"] == "not_evaluated_outside_composition_domain"
    assert out_of_domain.summary["thermo_coverage_score"]["value"] < base_coverage["value"]
    assert out_of_domain.conservation["max_element_relative_residual"] < 1e-8

    constraints = constraint_record(base, q05_quality=0.1, q95_risk=0.5)
    assert constraints["thermo_coverage"] == "not_evaluated"
    assert constraints["thermo_hard_pass"] is False


def test_reduced_enthalpy_ode_residual_is_not_mislabeled_full_energy_conservation() -> None:
    adiabatic = simulate(
        BASE,
        "L0",
        {
            "grid_check": False,
            "h_scale": 0.0,
            "emissivity_scale": 0.0,
            "reactions_enabled": False,
        },
    )
    assert adiabatic.status.success, adiabatic.status.message
    assert "energy_relative_residual" not in adiabatic.conservation
    assert adiabatic.conservation["reduced_effective_enthalpy_ode_relative_residual"] < 1e-10
    coverage = adiabatic.summary["enthalpy_coverage"]
    assert coverage["status"] == "reduced_model_not_full_energy_conservation"
    assert "wet-feed and forming water in fixed effective heat capacity" in coverage["value"]["included"]
    assert "escaped-gas sensible enthalpy" in coverage["value"]["excluded"]

    constraints = constraint_record(adiabatic, q05_quality=0.1, q95_risk=0.5)
    assert constraints["energy_conservation"] == "not_evaluated"
    assert constraints["reduced_effective_enthalpy_ode_numerics"] is True


def test_every_inverse_coordinate_changes_an_interpretable_physical_quantity() -> None:
    baseline_point = np.full(12, 0.5)
    baseline_case, baseline_decision = design_from_unit(BASE, baseline_point, 0)
    baseline = simulate(baseline_case, "L0", {"grid_check": False})

    extractors = [
        lambda result: result.summary["bulk_density_kg_m3"]["value"],
        lambda result: result.summary["released_gas_kg_per_kg_dry"]["value"]["CO2"],
        lambda result: result.summary["released_gas_kg_per_kg_dry"]["value"]["CO2"],
        lambda result: result.summary["oxide_flux_index"]["value"],
        lambda result: result.summary["effective_permeability_m2"]["value"],
        lambda result: result.summary["effective_permeability_m2"]["value"],
        lambda result: result.summary["as_received_water_kg_per_kg_dry"]["value"],
        lambda result: result.summary["residence_time_s"]["value"],
        lambda result: result.summary["effective_true_density_kg_m3"]["value"],
        lambda result: result.summary["effective_specific_heat_J_kg_K"]["value"],
        lambda result: result.fields["temperature"]["values"][-1],
        lambda result: result.summary["max_overpressure_Pa"]["value"],
    ]

    assert len(baseline_decision) == 12
    for coordinate, extractor in enumerate(extractors):
        point = baseline_point.copy()
        point[coordinate] = 0.8
        changed_case, changed_decision = design_from_unit(BASE, point, coordinate + 1)
        changed = simulate(changed_case, "L0", {"grid_check": False})
        assert changed.status.success, (coordinate, changed.status.message)
        assert changed_decision != baseline_decision
        assert extractor(changed) != pytest.approx(extractor(baseline), rel=1e-7, abs=1e-14), coordinate


def test_manifest_hashes_every_payload_and_strict_verify_rejects_hash_and_semantic_tampering(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "forward"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=7)
    manifest = json.loads((out / "run_manifest.json").read_text())
    payload_names = {path.name for path in out.iterdir() if path.name != "run_manifest.json"}
    assert set(manifest["artifacts"]) == payload_names
    for name, record in manifest["artifacts"].items():
        payload = (out / name).read_bytes()
        assert record["size_bytes"] == len(payload)
        assert record["sha256"] == hashlib.sha256(payload).hexdigest()

    (out / "summary.json").write_bytes((out / "summary.json").read_bytes() + b" ")
    hash_tamper = verify_run(out, strict=True)
    assert hash_tamper.valid is False
    assert any("artifact hash mismatch: summary.json" in error for error in hash_tamper.errors)

    semantic_out = tmp_path / "semantic"
    write_forward_run(semantic_out, BASE, result, cli_args=["forward"], seed=8)
    summary_path = semantic_out / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["bulk_density_kg_m3"]["value"] = -999.0
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    semantic_manifest_path = semantic_out / "run_manifest.json"
    semantic_manifest = json.loads(semantic_manifest_path.read_text())
    payload = summary_path.read_bytes()
    semantic_manifest["artifacts"]["summary.json"] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    semantic_manifest_path.write_text(json.dumps(semantic_manifest, indent=2, sort_keys=True) + "\n")
    semantic_tamper = verify_run(semantic_out, strict=True)
    assert semantic_tamper.valid is False
    assert any("bulk_density_kg_m3 must be positive" in error for error in semantic_tamper.errors)

    trajectory_out = tmp_path / "semantic_trajectory"
    write_forward_run(trajectory_out, BASE, result, cli_args=["forward"], seed=9)
    trajectory_path = trajectory_out / "state_trajectory.json"
    trajectory = json.loads(trajectory_path.read_text())
    trajectory["fields"]["temperature"]["values"][0] = -500.0
    trajectory_path.write_text(json.dumps(trajectory, indent=2, sort_keys=True) + "\n")
    trajectory_manifest_path = trajectory_out / "run_manifest.json"
    trajectory_manifest = json.loads(trajectory_manifest_path.read_text())
    payload = trajectory_path.read_bytes()
    trajectory_manifest["artifacts"]["state_trajectory.json"] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    trajectory_manifest_path.write_text(json.dumps(trajectory_manifest, indent=2, sort_keys=True) + "\n")
    trajectory_tamper = verify_run(trajectory_out, strict=True)
    assert trajectory_tamper.valid is False
    assert any("trajectory violates finite physical state bounds" in error for error in trajectory_tamper.errors)


def test_forward_artifact_serializes_sufficient_extensive_states_for_independent_verification(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "extensive_states"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=91)
    trajectory = json.loads((out / "state_trajectory.json").read_text())
    conservation = json.loads((out / "conservation.json").read_text())
    provenance = json.loads((out / "provenance.json").read_text())

    assert trajectory["schema_version"] == "2.0-independent-semantic-verification"
    assert trajectory["state_counts"]["time_points"] == len(trajectory["coordinates"]["time_s"])
    assert set(trajectory["fields"]["raw_reaction_extents"]) == {
        "free_water_removal", "organic_oxidation", "kaolinite_dehydroxylation", "carbonate_decomposition"
    }
    assert set(trajectory["fields"]["released_gas_mass_inventories"]) == {"H2O", "CO2", "N2", "SO2"}
    assert trajectory["fields"]["boundary_heat_cumulative"]["unit"] == "J/m3_reference_bulk"
    assert trajectory["fields"]["reaction_heat_cumulative"]["unit"] == "J/m3_reference_bulk"
    assert conservation["mass_ledger_kg_m3_reference"]["initial_wet_feed"] > 0.0
    assert conservation["element_inventory_mol_m3_reference"]["initial"]
    assert provenance["parameter_overrides"] == {"grid_check": False}
    assert verify_run(out, strict=True).valid is True


@pytest.mark.parametrize("attack", ["density", "summary_legal", "conservation", "oxygen", "reduced_enthalpy", "counts", "csv"])
def test_strict_verify_rejects_rehashed_forward_derived_semantic_attacks(tmp_path: Path, attack: str) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / attack
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=92)
    assert verify_run(out, strict=True).valid is True

    if attack in {"density", "summary_legal", "oxygen"}:
        path = out / "summary.json"
        payload = json.loads(path.read_text())
        if attack == "density":
            payload["bulk_density_kg_m3"]["value"] *= 2.0
        elif attack == "summary_legal":
            payload["linear_shrinkage"]["value"] += 0.01
        else:
            payload["oxygen_ledger_mol_O2_per_m3_reference"]["value"]["residual"] = 0.0
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        rehash_artifact(out, "summary.json")
    elif attack in {"conservation", "reduced_enthalpy"}:
        path = out / "conservation.json"
        payload = json.loads(path.read_text())
        if attack == "conservation":
            payload["mass_relative_residual"] = 0.0
            payload["max_element_relative_residual"] = 0.0
            payload["element_relative_residual_by_element"] = {
                name: 0.0 for name in payload["element_relative_residual_by_element"]
            }
        else:
            payload["reduced_effective_enthalpy_ode_relative_residual"] = 0.0
            payload["reduced_effective_enthalpy_ode_residual_J_m3"] = 0.0
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        rehash_artifact(out, "conservation.json")
    elif attack == "counts":
        path = out / "state_trajectory.json"
        payload = json.loads(path.read_text())
        payload["state_counts"]["time_points"] += 1
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        rehash_artifact(out, "state_trajectory.json")
    else:
        path = out / "state_trajectory.csv"
        with path.open("r", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fieldnames = list(rows[0])
        rows[0]["temperature_K"] = str(float(rows[0]["temperature_K"]) + 1.0)
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        rehash_artifact(out, "state_trajectory.csv")

    verification = verify_run(out, strict=True)
    assert verification.valid is False, attack
    assert verification.errors


def test_output_directory_rejects_nonempty_by_default_and_overwrite_keeps_rollback(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "forward"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=1)
    with pytest.raises(FileExistsError):
        write_forward_run(out, BASE, result, cli_args=["forward"], seed=2)

    write_forward_run(out, BASE, result, cli_args=["forward", "--overwrite"], seed=3, overwrite=True)
    manifest = json.loads((out / "run_manifest.json").read_text())
    transaction = manifest["output_transaction"]
    assert transaction["overwrite_requested"] is True
    assert transaction["rollback_directory"] is not None
    assert Path(transaction["rollback_directory"]).is_dir()


def test_strict_verify_rejects_rehashed_negative_gas_state(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "negative_gas"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=10)
    trajectory_path = out / "state_trajectory.json"
    trajectory = json.loads(trajectory_path.read_text())
    trajectory["fields"]["gas_concentrations"]["CO2"]["values"][0] = -1.0
    trajectory_path.write_text(json.dumps(trajectory, indent=2, sort_keys=True) + "\n")
    manifest_path = out / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    payload = trajectory_path.read_bytes()
    manifest["artifacts"]["state_trajectory.json"] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    verification = verify_run(out, strict=True)
    assert verification.valid is False
    assert any("trajectory violates finite physical state bounds" in error for error in verification.errors)


def test_strict_verify_returns_structured_invalid_for_scalar_trajectory_state(tmp_path: Path) -> None:
    result = simulate(BASE, "L0", {"grid_check": False})
    out = tmp_path / "scalar_state"
    write_forward_run(out, BASE, result, cli_args=["forward"], seed=11)
    trajectory_path = out / "state_trajectory.json"
    trajectory = json.loads(trajectory_path.read_text())
    trajectory["fields"]["temperature"]["values"] = 300.0
    trajectory_path.write_text(json.dumps(trajectory, indent=2, sort_keys=True) + "\n")
    manifest_path = out / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    payload = trajectory_path.read_bytes()
    manifest["artifacts"]["state_trajectory.json"] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    verification = verify_run(out, strict=True)
    assert verification.valid is False
    assert any("trajectory violates finite physical state bounds" in error for error in verification.errors)


def test_inverse_traceability_requires_exact_pareto_record_match(tmp_path: Path) -> None:
    record = {
        "design_id": 1,
        "fidelity": "L1",
        "decision": {"speed_ratio": 1.0},
        "quality_margin": {"q05": 0.1, "q50": 0.2, "q95": 0.3},
        "enabled_risk": {"q05": 0.1, "q50": 0.2, "q95": 0.3},
        "uncertainty_width": 0.2,
        "objectives": [-0.1, 0.3, 0.2, 0.0, 1.0],
        "constraints": {"all_hard_constraints": True},
        "source_hashes": {"parameter_pack": "manufactured"},
    }
    result = SimpleNamespace(
        status="success",
        all_evaluations=[record],
        feasible_set=[],
        ranked_candidates=[record],
        pareto_set=[record],
        rank_stability={"status": "insufficient_points"},
        l0_l1_disagreement=[],
        environmental_status="not_evaluated",
        warnings=[],
        budget="manufactured",
        design_space={"speed_ratio": [0.7, 1.3]},
    )
    out = tmp_path / "inverse_trace"
    write_inverse_run(out, BASE, result, cli_args=["inverse"], seed=12)
    pareto_path = out / "pareto.json"
    pareto = json.loads(pareto_path.read_text())
    pareto[0]["objectives"][0] = -999.0
    pareto_path.write_text(json.dumps(pareto, indent=2, sort_keys=True) + "\n")
    manifest_path = out / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    payload = pareto_path.read_bytes()
    manifest["artifacts"]["pareto.json"] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    verification = verify_run(out, strict=True)
    assert verification.valid is False
    assert verification.checks["pareto_traceability"] is False


def _manufactured_inverse_result(records: list[dict]) -> SimpleNamespace:
    pareto_mask = nondominated_mask(
        np.asarray([record["objectives"] for record in records], dtype=float),
        np.ones(len(records), dtype=bool),
    )
    pareto = [record for record, keep in zip(records, pareto_mask) if keep]
    return SimpleNamespace(
        status="success",
        all_evaluations=records,
        feasible_set=[],
        ranked_candidates=records,
        pareto_set=pareto,
        rank_stability=_rank_stability([], []),
        l0_l1_disagreement=[],
        environmental_status="not_evaluated",
        warnings=[],
        budget="manufactured",
        design_space={"speed_ratio": [0.7, 1.3]},
    )


def test_inverse_strict_verify_recomputes_constraints_and_observed_envelope(tmp_path: Path) -> None:
    design_case, decision = design_from_unit(BASE, np.full(12, 0.5), 101)
    successful = simulate(design_case, "L0", {"grid_check": False})
    record = _record_from_results(
        design_case,
        decision,
        101,
        "L1",
        [successful, successful],
        grid_converged=True,
    )
    out = tmp_path / "inverse_semantics"
    write_inverse_run(out, BASE, _manufactured_inverse_result([record]), cli_args=["inverse"], seed=93)
    assert verify_run(out, strict=True).valid is True

    pareto_path = out / "pareto.json"
    pareto = json.loads(pareto_path.read_text())
    pareto[0]["constraints"]["q95_enabled_risk"] = False
    pareto_path.write_text(json.dumps(pareto, indent=2, sort_keys=True) + "\n")
    rehash_artifact(out, "pareto.json")
    evaluations_path = out / "all_evaluations.jsonl"
    evaluation = json.loads(evaluations_path.read_text().strip())
    evaluation["constraints"]["q95_enabled_risk"] = False
    evaluations_path.write_text(json.dumps(evaluation, sort_keys=True) + "\n")
    rehash_artifact(out, "all_evaluations.jsonl")
    assert verify_run(out, strict=True).valid is False

    fresh = tmp_path / "inverse_envelope"
    write_inverse_run(fresh, BASE, _manufactured_inverse_result([record]), cli_args=["inverse"], seed=94)
    envelope_path = fresh / "feasible_windows.json"
    envelope = json.loads(envelope_path.read_text())
    envelope["windows"]["speed_ratio"]["max"] += 0.01
    envelope_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    rehash_artifact(fresh, "feasible_windows.json")
    assert verify_run(fresh, strict=True).valid is False

    csv_attack = tmp_path / "inverse_csv"
    write_inverse_run(csv_attack, BASE, _manufactured_inverse_result([record]), cli_args=["inverse"], seed=96)
    csv_path = csv_attack / "pareto.csv"
    csv_payload = csv_path.read_text()
    original_value = str(record["quality_margin"]["q05"])
    csv_path.write_text(csv_payload.replace(original_value, str(float(original_value) + 0.5), 1))
    rehash_artifact(csv_attack, "pareto.csv")
    assert verify_run(csv_attack, strict=True).valid is False

    source_attack = tmp_path / "inverse_source"
    write_inverse_run(source_attack, BASE, _manufactured_inverse_result([record]), cli_args=["inverse"], seed=97)
    source_pareto_path = source_attack / "pareto.json"
    source_pareto = json.loads(source_pareto_path.read_text())
    source_pareto[0]["source_hashes"]["case"] = "forged-source"
    source_pareto_path.write_text(json.dumps(source_pareto, indent=2, sort_keys=True) + "\n")
    rehash_artifact(source_attack, "pareto.json")
    source_evaluations_path = source_attack / "all_evaluations.jsonl"
    source_evaluation = json.loads(source_evaluations_path.read_text().strip())
    source_evaluation["source_hashes"]["case"] = "forged-source"
    source_evaluations_path.write_text(json.dumps(source_evaluation, sort_keys=True) + "\n")
    rehash_artifact(source_attack, "all_evaluations.jsonl")
    assert verify_run(source_attack, strict=True).valid is False

    rank_attack = tmp_path / "inverse_rank"
    write_inverse_run(rank_attack, BASE, _manufactured_inverse_result([record]), cli_args=["inverse"], seed=98)
    rank_path = rank_attack / "rank_stability.json"
    rank = json.loads(rank_path.read_text())
    rank["status"] = "stable"
    rank_path.write_text(json.dumps(rank, indent=2, sort_keys=True) + "\n")
    rehash_artifact(rank_attack, "rank_stability.json")
    assert verify_run(rank_attack, strict=True).valid is False


def test_inverse_strict_verify_rejects_traceable_but_dominated_pareto_source(tmp_path: Path) -> None:
    first_case, first_decision = design_from_unit(BASE, np.full(12, 0.45), 201)
    first_successful = simulate(first_case, "L0", {"grid_check": False})
    first = _record_from_results(
        first_case,
        first_decision,
        201,
        "L1",
        [first_successful, first_successful],
        grid_converged=True,
    )
    second_case, second_decision = design_from_unit(BASE, np.full(12, 0.65), 202)
    second_successful = simulate(second_case, "L0", {"grid_check": False})
    second = _record_from_results(
        second_case,
        second_decision,
        202,
        "L1",
        [second_successful, second_successful],
        grid_converged=True,
    )
    second["objectives"] = [value + 1.0 for value in first["objectives"]]
    out = tmp_path / "dominated_pareto"
    result = _manufactured_inverse_result([first, second])
    result.pareto_set = [second]
    write_inverse_run(out, BASE, result, cli_args=["inverse"], seed=95)
    verification = verify_run(out, strict=True)
    assert verification.valid is False
    assert verification.checks["pareto_nondominated_from_all_l1"] is False


def test_small_rank_samples_and_candidate_envelopes_are_labeled_honestly() -> None:
    rank = _rank_stability([0.1, 0.2], [0.2, 0.1])
    assert rank["status"] == "insufficient_points"
    assert rank["design_count"] == 2

    candidates = [
        {"decision": {"speed_ratio": 0.9}},
        {"decision": {"speed_ratio": 1.1}},
    ]
    envelope = _feasible_windows(candidates)
    assert envelope["status"] == "observed_candidate_envelope"
    assert envelope["continuity_validated"] is False


def test_inverse_record_serializes_constraint_slacks_and_defines_active_by_slack() -> None:
    successful = simulate(BASE, "L0", {"grid_check": False})
    record = _record_from_results(
        BASE,
        {"sludge_dry_mass_fraction": 0.08},
        23,
        "L0",
        [successful, successful],
    )
    assert record["constraint_slacks"]
    assert record["active_constraints"] == sorted(
        name for name, slack in record["constraint_slacks"].items() if slack <= 0.05
    )


@pytest.mark.parametrize("fidelity", ["L0", "L1"])
def test_forward_solver_exception_writes_structured_failure_artifact_and_returns_exit_3(
    tmp_path: Path, monkeypatch, capsys, fidelity: str
) -> None:
    def fail_solver(*args, **kwargs):
        raise RuntimeError("manufactured solver failure")

    monkeypatch.setattr(cli_module, "simulate", fail_solver)
    out = tmp_path / f"structured_failure_{fidelity}"
    exit_code = cli_module.command_forward(
        Namespace(
            case=ROOT / "examples" / "tiny_synthetic.json",
            fidelity=fidelity,
            out=out,
            uq_power=None,
            seed=1,
            overwrite=False,
        )
    )
    assert exit_code == 3
    status = json.loads((out / "status.json").read_text())
    assert status["code"] == "solver_exception"
    assert status["success"] is False
    assert status["stage"] == f"forward_{fidelity}"
    assert status["reason"] == "solver_runtime_exception"
    assert status["exception"] == {"category": "runtime_error"}
    assert json.loads((out / "provenance.json").read_text())["case_hash"] == BASE.content_hash
    assert json.loads((out / "run_manifest.json").read_text())["run_type"] == "structured_failure"
    assert "Traceback" not in capsys.readouterr().err


def test_inverse_solver_exception_writes_structured_failure_artifact_and_returns_exit_3(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    def fail_solver(*args, **kwargs):
        raise RuntimeError("manufactured inverse failure")

    monkeypatch.setattr(cli_module, "run_inverse", fail_solver)
    out = tmp_path / "inverse_failure"
    exit_code = cli_module.command_inverse(
        Namespace(
            case=ROOT / "examples" / "tiny_synthetic.json",
            budget="tiny",
            out=out,
            seed=2,
            overwrite=False,
        )
    )
    assert exit_code == 3
    status = json.loads((out / "status.json").read_text())
    assert status["stage"] == "inverse"
    assert status["exception"] == {"category": "runtime_error"}
    assert "Traceback" not in capsys.readouterr().err


def test_benchmark_solver_exception_writes_structured_failure_artifact_and_returns_exit_3(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    def fail_solver(*args, **kwargs):
        raise RuntimeError("manufactured benchmark failure")

    monkeypatch.setattr(cli_module, "simulate", fail_solver)
    out = tmp_path / "benchmark_failure"
    exit_code = cli_module.command_benchmark(
        Namespace(
            case=ROOT / "examples" / "tiny_synthetic.json",
            out=out,
            seed=3,
            overwrite=False,
        )
    )
    assert exit_code == 3
    status = json.loads((out / "status.json").read_text())
    assert status["stage"] == "benchmark_L0"
    assert status["exception"] == {"category": "runtime_error"}
    assert "Traceback" not in capsys.readouterr().err


def test_solver_failure_preserves_nonempty_requested_output_and_writes_sibling_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    def fail_solver(*args, **kwargs):
        raise RuntimeError("manufactured safe-output failure")

    monkeypatch.setattr(cli_module, "simulate", fail_solver)
    out = tmp_path / "occupied"
    out.mkdir()
    sentinel = out / "sentinel.txt"
    sentinel.write_text("preserve me")
    exit_code = cli_module.command_forward(
        Namespace(
            case=ROOT / "examples" / "tiny_synthetic.json",
            fidelity="L0",
            out=out,
            uq_power=None,
            seed=4,
            overwrite=False,
        )
    )
    assert exit_code == 3
    assert sentinel.read_text() == "preserve me"
    failures = list(tmp_path.glob(".occupied.failure-*"))
    assert len(failures) == 1
    provenance = json.loads((failures[0] / "provenance.json").read_text())
    assert provenance["requested_output_preserved"] is True


@pytest.mark.parametrize("interruption", [KeyboardInterrupt(), SystemExit(17)])
def test_solver_wrapper_does_not_swallow_process_control_exceptions(tmp_path: Path, monkeypatch, interruption) -> None:
    def interrupt(*args, **kwargs):
        raise interruption

    monkeypatch.setattr(cli_module, "simulate", interrupt)
    out = tmp_path / "must_not_exist"
    with pytest.raises(type(interruption)):
        cli_module.command_forward(
            Namespace(
                case=ROOT / "examples" / "tiny_synthetic.json",
                fidelity="L0",
                out=out,
                uq_power=None,
                seed=5,
                overwrite=False,
            )
        )
    assert not out.exists()


@pytest.mark.parametrize(
    "mutator, expected_path",
    [
        (lambda raw: [], "$"),
        (lambda raw: {**raw, "kiln": []}, "$.kiln"),
        (lambda raw: {**raw, "kiln": {**raw["kiln"], "profile": None}}, "$.kiln.profile"),
        (lambda raw: {**raw, "kiln": {**raw["kiln"], "profile": [1, 2]}}, "$.kiln.profile[0]"),
        (lambda raw: {**raw, "inverse_design": []}, "$.inverse_design"),
        (lambda raw: {**raw, "inverse_design": None}, "$.inverse_design"),
    ],
)
def test_malformed_container_matrix_returns_validation_exit_2_without_traceback(
    tmp_path: Path, capsys, mutator, expected_path: str
) -> None:
    payload = mutator(copy.deepcopy(BASE.raw))
    path = tmp_path / "malformed.json"
    path.write_text(json.dumps(payload))
    exit_code = cli_module.main(["validate", str(path), "--json"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert expected_path in captured.out
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "mutator",
    [
        lambda raw: raw["forming"].update(moisture_wet_basis=1.0),
        lambda raw: raw["geometry"].update(brick_half_thickness_m=0.0),
        lambda raw: raw["kiln"].update(reference_speed_m_s=0.0),
        lambda raw: raw["kiln"]["profile"][0].update(ambient_pressure_Pa=-1.0),
    ],
)
def test_invalid_schema_cli_validate_returns_exit_2_without_solver_traceback(tmp_path: Path, mutator) -> None:
    raw = copy.deepcopy(BASE.raw)
    mutator(raw)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(raw))
    assert cli_module.main(["validate", str(path), "--json"]) == 2


def test_forward_accepts_and_records_tightened_solver_tolerances() -> None:
    result = simulate(
        BASE,
        "L0",
        {"grid_check": False, "solver_rtol": 1e-8, "solver_atol": 1e-11},
    )
    assert result.status.success, result.status.message
    assert result.solver_statistics["rtol"] == 1e-8
    assert result.solver_statistics["atol"] == 1e-11
    assert result.conservation["mass_relative_residual"] < 1e-8
    assert result.conservation["max_element_relative_residual"] < 1e-8


def test_l0_matches_manufactured_newton_cooling_limit() -> None:
    def constant_boundary(raw) -> None:
        for point in raw["kiln"]["profile"]:
            point.update(
                gas_temperature_K=600.0,
                wall_temperature_K=600.0,
                h_W_m2_K=12.0,
                mass_transfer_m_s=0.0,
                oxygen_mole_fraction=0.0,
            )

    case = mutated_case(constant_boundary)
    parameters = {
        "grid_check": False,
        "reactions_enabled": False,
        "emissivity_scale": 0.0,
        "sintering_scale": 0.0,
    }
    context = build_context(case, parameters)
    result = simulate(case, "L0", parameters)
    assert result.status.success, result.status.message

    external_h = 12.0
    effective_h = 1.0 / (
        1.0 / external_h + context.half_thickness_m / (3.0 * context.conductivity)
    )
    rho_heat = context.rho_dry * (1.0 + context.water_ratio)
    decay = effective_h / (context.half_thickness_m * rho_heat * context.cp)
    initial = float(case.raw["forming"]["initial_temperature_K"])
    expected = 600.0 + (initial - 600.0) * math.exp(-decay * context.residence_time_s)
    actual = float(result.fields["temperature"]["values"][-1])
    assert actual == pytest.approx(expected, rel=2e-5, abs=2e-5)
