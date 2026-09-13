"""Offline conditional isobaric heat differences from two saved TP value records."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from fractions import Fraction as F
import math
from pathlib import Path

from .cedrone_oxygen import derive_cedrone_oxygen_pool, check_cedrone_oxygen_result
from .tp_equilibrium import (
    ELEMENTS, SPECIES, MODEL_SHA256, TPPool, TPPolicy, TPResult,
    _frozen, _load_pack, _property_check, _diagnostics, _inventory,
)

# Existing nist-codata-2022 registration: exact defining SI values, then binary64.
_SI_R_EXACT = F("6.02214076e23") * F("1.380649e-23")
_SI_R = float(_SI_R_EXACT)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _restore(value: object, depth: int = 0) -> object:
    """Restore only JSON values and the existing two-integer Fraction record."""
    _require(depth <= 32, "saved_value_nesting_limit")
    if isinstance(value, Mapping):
        _require(all(isinstance(k, str) for k in value), "saved_keys_must_be_strings")
        _require("invalid_computed_float" not in value, "nonfinite_saved_value")
        if set(value) == {"numerator", "denominator"}:
            numerator, denominator = value["numerator"], value["denominator"]
            _require(type(numerator) is int and type(denominator) is int and denominator > 0,
                     "invalid_saved_fraction")
            return F(numerator, denominator)
        return {k: _restore(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return tuple(_restore(v, depth + 1) for v in value)
    if isinstance(value, float):
        _require(math.isfinite(value), "nonfinite_saved_value")
        return value
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise ValueError("unsupported_saved_value")


def _result(saved: Mapping) -> TPResult:
    _require(isinstance(saved, Mapping) and set(saved) == {f.name for f in fields(TPResult)},
             "expected_saved_TPResult_object")
    data = _restore(saved)
    _require(isinstance(data["request"], Mapping), "missing_saved_pool")
    data["request"] = TPPool(**data["request"])
    result = TPResult(**data)
    _require(result.status == "completed" and result.failure is None, "saved_result_not_completed")
    _require(type(result.elapsed_seconds) in (int, float) and 0 <= result.elapsed_seconds <= 10.,
             "invalid_completed_elapsed")
    _require(type(result.provider_calls_attempted) is int and type(result.provider_calls_completed) is int
             and 0 <= result.provider_calls_completed <= result.provider_calls_attempted,
             "invalid_saved_call_counts")
    _require(result.material_qualified is False and result.training_eligible is False,
             "unsupported_saved_qualification")
    return result


def _physical_point(pack: dict, point: Mapping) -> None:
    _require(point["temperature_k"] == 800. and point["pressure_pa"] == 100000.,
             "heat_comparison_requires_exact_800K_1bar")
    _require(type(point["gas_constant_j_mol_k"]) is float and point["gas_constant_j_mol_k"] == _SI_R,
             "saved_gas_constant_differs_from_SI")
    loaded = point["loaded_definition"]
    _require(len(loaded["species"]) == 19, "loaded_species_count_mismatch")
    for actual, source in zip(loaded["species"], pack["derived"]["species"], strict=True):
        thermo = source["thermo"]
        expected = {"name": source["name"], "composition": source["composition"],
                    "reference_pressure_pa": 100000.,
                    "temperature_range_k": (thermo["temperature-ranges"][0], thermo["temperature-ranges"][2]),
                    "coefficients_high_then_low": (thermo["temperature-ranges"][1], *thermo["data"][1], *thermo["data"][0])}
        _require(actual == _frozen(expected), "saved_phase_source_mismatch")
    _require(math.isclose(loaded["carbon_density_kg_m3"], 2160., rel_tol=1e-14, abs_tol=1e-10),
             "saved_graphite_density_mismatch")
    _property_check(pack, point)


def _admit(saved: Mapping, lam: F, source_root: str | Path, pack: dict) -> tuple:
    result = _result(saved)
    _require(result.initial is not None and result.final is not None, "missing_saved_snapshots")
    weights = result.initial["loaded_definition"]["gas_atomic_weights_kg_kmol"]
    inputs = derive_cedrone_oxygen_pool(source_root, lam, weights)
    observations = check_cedrone_oxygen_result(result, inputs)
    expected_provenance = _frozen({"model": pack["model"], "source": pack["source"], "model_sha256": MODEL_SHA256})
    _require(result.provenance == expected_provenance, "saved_provenance_source_mismatch")
    for point in (result.initial, result.final):
        _physical_point(pack, point)
        _require(all(v is True for v in _inventory(pack, result.request, point)["checks"].values()),
                 "saved_inventory_postcheck_failed")
        _require(result.provider_identity["gas_constant_j_mol_k"] == point["gas_constant_j_mol_k"]
                 and result.provider_identity["reference_branch"] == pack["model"]["reference_branch"],
                 "saved_provider_physical_identity_mismatch")
    recalculated = _diagnostics(pack, result.request, result.initial, result.final, TPPolicy())
    _require(all(v is True for v in recalculated["checks"].values()), "recomputed_TP_postcheck_failed")
    n = tuple(row["amount_mol"] for row in observations["species"])
    h = tuple(F(v) for v in result.final["standard_h_j_mol"])
    total_h = sum((amount * value for amount, value in zip(n, h, strict=True)), F())
    _require(total_h == result.diagnostics["mixture_enthalpy_j"] == recalculated["mixture_enthalpy_j"],
             "saved_enthalpy_sum_mismatch")
    return result, inputs, observations, n, h, total_h


def compare_cedrone_heat(baseline_result: Mapping, candidate_result: Mapping, *,
                         source_root: str | Path, candidate_lambda: F,
                         baseline_lambda: F = F()) -> Mapping:
    """Return exact represented-data heat arithmetic under explicit shared-feed conditions.

    No Cantera import, phase construction or equilibrium call. The existing pure
    source/property and posterior checks are reused; linalg floats need only pass
    their original gates, while inventories and enthalpy sums are exact Fractions.
    """
    _require(not isinstance(baseline_lambda, bool) and isinstance(baseline_lambda, (F, int))
             and baseline_lambda == 0, "baseline_lambda_must_be_zero")
    _require(not isinstance(candidate_lambda, bool) and isinstance(candidate_lambda, (F, int))
             and candidate_lambda in (F(), F(1, 4), F(1)), "unsupported_candidate_lambda")
    try:
        pack = _load_pack(source_root)
        base = _admit(baseline_result, F(), source_root, pack)
        case = _admit(candidate_result, F(candidate_lambda), source_root, pack)
        br, bi, bo, bn, bh, base_h = base
        cr, ci, co, cn, ch, case_h = case
        _require(br.initial["loaded_definition"] == cr.initial["loaded_definition"], "different_physical_phase_identity")
        h = tuple(F(v) for v in br.initial["standard_h_j_mol"])
        _require(h == bh == ch == tuple(F(v) for v in cr.initial["standard_h_j_mol"]),
                 "different_common_enthalpy_vectors")
        _require(br.initial["gas_constant_j_mol_k"] == cr.initial["gas_constant_j_mol_k"],
                 "different_gas_constant")
        definition = ci.definition()
        oxygen, nitrogen = definition["added_O2_mol"], definition["added_N2_mol"]
        incoming_o, incoming_n = oxygen * h[5], nitrogen * h[6]
        delta_h = case_h - base_h
        delta_q = delta_h - incoming_o - incoming_n
        added = tuple(oxygen if i == 5 else nitrogen if i == 6 else F() for i in range(19))
        nu = tuple(c - b - a for c, b, a in zip(cn, bn, added, strict=True))
        _require(delta_q == sum((v * hi for v, hi in zip(nu, h, strict=True)), F()), "formal_heat_equation_mismatch")
        target_zero = tuple(c - b - d for c, b, d in
                            zip(ci.pool.element_mol, bi.pool.element_mol, definition["element_increment_mol"], strict=True))
        _require(target_zero == (F(),) * 5, "strict_target_element_equation_not_zero")
        atoms = pack["atoms"]
        residual_difference = tuple(co["element_residual_mol"][e] - bo["element_residual_mol"][e] for e in ELEMENTS)
        reference_coefficients = tuple(sum((nu[i] * atoms[i][j] for i in range(19)), F()) for j in range(5))
        _require(reference_coefficients == residual_difference, "actual_reference_shift_identity_mismatch")
        return _frozen({
            "model_id": "CEDRONE_SAME_FEED_ISOBARIC_RELATIVE_HEAT_V1", "status": "completed",
            "baseline_lambda": F(), "candidate_lambda": F(candidate_lambda),
            "temperature_k": 800., "pressure_pa": 100000., "inlet_temperature_k": 800.,
            "original_reported_sample_basis_kg": F(1),
            "baseline_equilibrium_enthalpy_j": base_h, "candidate_equilibrium_enthalpy_j": case_h,
            "equilibrium_enthalpy_difference_j": delta_h,
            "added_o2_mol": oxygen, "added_n2_mol": nitrogen,
            "incoming_o2_h_j_mol": h[5], "incoming_n2_h_j_mol": h[6],
            "incoming_o2_enthalpy_j": incoming_o, "incoming_n2_enthalpy_j": incoming_n,
            "conditional_delta_q_j": delta_q, "conditional_delta_q_mj_per_kg_reported_sample": delta_q / 10**6,
            "species": tuple({"name": name, "composition": dict(zip(ELEMENTS, atoms[i])),
                              "baseline_amount_mol": bn[i], "candidate_amount_mol": cn[i],
                              "standard_h_j_mol": h[i], "baseline_nh_j": bn[i] * h[i], "candidate_nh_j": cn[i] * h[i],
                              "formal_difference_mol": nu[i], "formal_heat_contribution_j": nu[i] * h[i]}
                             for i, name in enumerate(SPECIES)),
            "strict_target_element_zero_mol": dict(zip(ELEMENTS, target_zero)),
            "baseline_element_residual_mol": bo["element_residual_mol"],
            "candidate_element_residual_mol": co["element_residual_mol"],
            "reference_shift_coefficients_mol": dict(zip(ELEMENTS, reference_coefficients)),
            "source": {"cedrone_sha256": bi.definition()["source_sha256"], "thermochemistry": br.provenance,
                       "basis": bi.definition()["source_document"]["basis"],
                       "excluded_and_unidentified": bi.definition()["source_document"]["excluded_and_unidentified"]},
            "gas_constant": {"exact_j_mol_k": _SI_R_EXACT, "represented_j_mol_k": _SI_R,
                             "source_id": "nist-codata-2022", "classification": "physical_law_or_constant",
                             "registry": "data/sandbox/thermochemistry/sources.json",
                             "url": "https://physics.nist.gov/cuu/Constants/Table/allascii.txt",
                             "locator": "Avogadro and Boltzmann constant rows; exact R=N_A*k_B",
                             "exact_N_A_per_mol": "6.02214076e23", "exact_k_B_j_per_k": "1.380649e-23"},
            "h_locators": {"o2_inlet": "baseline-result#/initial/standard_h_j_mol/5",
                           "n2_inlet": "baseline-result#/initial/standard_h_j_mol/6",
                           "products": "each-result#/final/standard_h_j_mol; order is species"},
            "conditions": ("same unknown initial feed state and amount", "isobaric with only pV work; no KE/PE difference",
                           "identical outside-subsystem initial/final state changes",
                           "ideal O2/N2 enters at 800 K; upstream preheating outside boundary"),
            "sign": "Q positive into the system; negative delta Q means less net heat than baseline, not self-heating",
            "unknowns": {"H_feed_j": None, "absolute_baseline_heat_j": None, "absolute_candidate_heat_j": None,
                         "material_and_thermochemical_fit_error": None, "upstream_preheat_energy_j": None},
            "common_unknowns_were_set_to_zero": False, "material_qualified": False, "training_eligible": False,
            "equilibrium_calls": 0, "EOS_calls": 0,
            "qualification": "conditional net heat difference; not furnace fuel saving, emissions, char yield or absolute heat duty",
        })
    except (KeyError, TypeError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError("invalid_saved_TP_result:" + str(exc)) from exc
