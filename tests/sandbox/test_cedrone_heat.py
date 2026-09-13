"""Offline saved-simulation arithmetic and negative controls; no native provider."""
import builtins
import copy
from fractions import Fraction as F
import importlib.util
import json
from pathlib import Path

import pytest

from sludge_sandbox import cedrone_heat as heat

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/sandbox/research/cedrone-relative-heat-v1"
SPEC = importlib.util.spec_from_file_location("cedrone_heat_cli", ROOT / "examples/sandbox/compare_cedrone_heat.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


@pytest.fixture
def records():
    return tuple(json.loads((DATA / name).read_text()) for name in
                 ("lambda0-result.json", "lambda-quarter-result.json", "lambda1-result.json"))


def compare(base, candidate, lam=F(1, 4)):
    return heat.compare_cedrone_heat(base, candidate, source_root=ROOT, candidate_lambda=lam)


def test_saved_heat_sums_include_all_phases_and_both_inlet_gases(records, monkeypatch):
    original_import = builtins.__import__
    def no_cantera(name, *args, **kwargs):
        if name == "cantera" or name.startswith("cantera."):
            pytest.fail("offline comparison must not import Cantera")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_cantera)
    baseline, quarter, one = records
    zero = compare(baseline, baseline, F())
    assert zero["conditional_delta_q_j"] == 0
    assert all(v == 0 for v in zero["reference_shift_coefficients_mol"].values())
    for candidate, lam, expected in ((quarter, F(1, 4), -3.38404021365e6), (one, F(1), -14.9776042983e6)):
        result = compare(baseline, candidate, lam)
        assert len(result["species"]) == 19 and result["species"][-1]["name"] == "C(gr)"
        assert float(result["conditional_delta_q_j"]) == pytest.approx(expected, abs=.001)
        assert result["conditional_delta_q_j"] == (result["equilibrium_enthalpy_difference_j"]
                                                   - result["incoming_o2_enthalpy_j"] - result["incoming_n2_enthalpy_j"])
        wrong_without_nitrogen = result["equilibrium_enthalpy_difference_j"] - result["incoming_o2_enthalpy_j"]
        assert wrong_without_nitrogen - result["conditional_delta_q_j"] == result["incoming_n2_enthalpy_j"] > 0
        assert sum(row["candidate_nh_j"] for row in result["species"]) == result["candidate_equilibrium_enthalpy_j"]
        assert result["unknowns"]["H_feed_j"] is None
        assert result["unknowns"]["absolute_candidate_heat_j"] is None


def test_formal_equation_preserves_real_residuals_under_element_reference_shift(records):
    result = compare(records[0], records[1])
    shifts = dict(zip(heat.ELEMENTS, (F(500), F(-70), F(9), F(11), F(40))))
    shifted = sum(row["formal_difference_mol"] * (row["standard_h_j_mol"] +
                  sum(F(row["composition"].get(e, 0)) * value for e, value in shifts.items()))
                  for row in result["species"])
    expected = sum(shifts[e] * result["reference_shift_coefficients_mol"][e] for e in heat.ELEMENTS)
    assert shifted - result["conditional_delta_q_j"] == expected
    assert all(value == 0 for value in result["strict_target_element_zero_mol"].values())
    assert any(value != 0 for value in result["reference_shift_coefficients_mol"].values())
    for e in heat.ELEMENTS:
        assert result["reference_shift_coefficients_mol"][e] == (result["candidate_element_residual_mol"][e]
                                                               - result["baseline_element_residual_mol"][e])


def test_legal_serializer_and_timing_metadata_do_not_change_physics(records):
    candidate = copy.deepcopy(records[1])
    candidate["provider_identity"]["input_serialization"] = "another_recorded_layout"
    candidate["initial"]["construction_timings_s"] = {"manufactured_metadata_only": .002}
    candidate["elapsed_seconds"] = .2
    expected = compare(records[0], records[1])
    actual = compare(records[0], candidate)
    assert actual["conditional_delta_q_j"] == expected["conditional_delta_q_j"]


@pytest.mark.parametrize("case", ("baseline_lambda", "candidate_lambda", "basis"))
def test_wrong_source_pool_or_declared_lambda_rejected(records, case):
    baseline, candidate = copy.deepcopy(records[:2])
    with pytest.raises(ValueError):
        if case == "baseline_lambda":
            heat.compare_cedrone_heat(baseline, candidate, source_root=ROOT, candidate_lambda=F(1, 4), baseline_lambda=F(1))
        elif case == "candidate_lambda":
            compare(baseline, candidate, F(1))
        else:
            candidate["request"]["basis_id"] = "another_sample"
            compare(baseline, candidate)


@pytest.mark.parametrize("case", ("nan", "infinite_metadata", "zero_denominator", "fraction_float"))
def test_invalid_saved_numeric_values_rejected(records, case):
    candidate = copy.deepcopy(records[1])
    if case == "nan":
        candidate["final"]["standard_h_j_mol"][0] = float("nan")
    elif case == "infinite_metadata":
        candidate["elapsed_seconds"] = float("inf")
    elif case == "zero_denominator":
        candidate["request"]["element_mol"][0]["denominator"] = 0
    else:
        candidate["request"]["element_mol"][0]["numerator"] = 1.5
    with pytest.raises(ValueError):
        compare(records[0], candidate)


@pytest.mark.parametrize("case", ("temperature", "pressure", "failed", "source", "phase", "h_vector", "H_sum",
                                "initial_inventory", "R_scaled"))
def test_physical_correspondence_and_original_failures_rejected(records, case):
    baseline = copy.deepcopy(records[0])
    candidate = copy.deepcopy(records[1])
    if case == "temperature":
        candidate["initial"]["temperature_k"] = 800.01
    elif case == "pressure":
        candidate["final"]["pressure_pa"] = 100001.
    elif case == "failed":
        candidate["status"] = "postcheck_failed"
    elif case == "source":
        candidate["provenance"]["model_sha256"] = "0" * 64
    elif case == "phase":
        for point in (candidate["initial"], candidate["final"]):
            point["loaded_definition"]["species"][0]["coefficients_high_then_low"][1] += 1.
    elif case == "h_vector":
        candidate["final"]["standard_h_j_mol"][0] += 1.
    elif case == "H_sum":
        candidate["diagnostics"]["mixture_enthalpy_j"]["numerator"] += 1
    elif case == "initial_inventory":
        candidate["initial"]["amounts_kmol"][0] += 1e-6
    else:
        for record in (baseline, candidate):
            record["provider_identity"]["gas_constant_j_mol_k"] *= 2
            for point in (record["initial"], record["final"]):
                point["gas_constant_j_mol_k"] *= 2
                for field in ("standard_h_j_mol", "standard_s_j_mol_k", "standard_cp_j_mol_k",
                              "standard_g_j_mol", "chemical_potentials_j_mol"):
                    point[field] = [value * 2 for value in point[field]]
            record["diagnostics"]["mixture_enthalpy_j"]["numerator"] *= 2
    with pytest.raises(ValueError):
        compare(baseline, candidate)


def test_cli_saves_offline_identities_and_rejects_existing_output(tmp_path):
    args = ["--source-root", str(ROOT), "--baseline-result", str(DATA / "lambda0-result.json"),
            "--candidate-result", str(DATA / "lambda-quarter-result.json"), "--lambda", "1/4",
            "--output-dir", str(tmp_path / "comparison")]
    assert cli.main(args) == 0
    output = tmp_path / "comparison"
    before = (output / "RESULT.json").read_bytes()
    assert cli.main(args) == 2
    assert (output / "RESULT.json").read_bytes() == before
    inputs = json.loads((output / "INPUT.json").read_text())
    assert inputs["inputs"]["baseline"]["sha256"] != inputs["inputs"]["candidate"]["sha256"]
    assert json.loads((output / "STATUS.json").read_text())["equilibrium_calls"] == 0


def test_cli_second_input_failure_keeps_first_identity_and_original_request(tmp_path):
    output = tmp_path / "failed"
    assert cli.main(["--source-root", str(ROOT), "--baseline-result", str(DATA / "lambda0-result.json"),
                     "--candidate-result", str(tmp_path / "absent.json"), "--lambda", "1/4",
                     "--output-dir", str(output)]) == 1
    record = json.loads((output / "INPUT.json").read_text())
    assert record["inputs"]["baseline"]["bytes"] > 0
    assert "candidate" not in record["inputs"]
    assert json.loads((output / "STATUS.json").read_text())["status"] == "failed"
    assert not (output / "RESULT.json").exists()
