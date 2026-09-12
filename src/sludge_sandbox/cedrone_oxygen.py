"""Cedrone Table 4 with finite virtual O2/N2: bookkeeping, not new thermochemistry.

These helpers read one pinned public record and perform algebra only. The caller
uses solve_tp once; its 10 s boundary checks require external native supervision.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path

from .tp_equilibrium import ELEMENTS, MODEL_SHA256, SPECIES, TPPool, TPPolicy, TPResult, _frozen

SOURCE_RELATIVE = Path("data/sandbox/research/cedrone2024-element-pool-v1/printed-pool.json")
SOURCE_SHA256 = "92feba43d25479d99a2607466fb902841d0afcffc5b1108ca2ff74a42145f7fd"
MODEL_ID = "CEDRONE_REPORTED_CHONS_FINITE_OXYGEN_V1"
QUALIFICATION = _frozen({
    "material_qualified": False, "training_eligible": False,
    "scope": "conditional restricted TP composition per original 1 kg reported sample",
    "unknown": "strict dry basis, mineral allocation, O uncertainty/covariance, omitted phases and material error",
    "not_inferred": "char yield, emissions, kinetics, firing heat duty or complete-brick qualification",
})


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _fraction(record: Mapping) -> F:
    return F(int(record["numerator"]), int(record["denominator"]))


@dataclass(frozen=True)
class CedroneOxygenInput:
    """A frozen value record made by derive_cedrone_oxygen_pool, before phase binding."""
    pool: TPPool
    atomic_weights_kg_kmol: tuple[float, ...]
    _definition: Mapping

    def __post_init__(self) -> None:
        object.__setattr__(self, "atomic_weights_kg_kmol", tuple(self.atomic_weights_kg_kmol))
        object.__setattr__(self, "_definition", _frozen(self._definition))

    def definition(self) -> Mapping:
        """Return existing read-only values; no file access, hashing or recomputation."""
        return self._definition


def derive_cedrone_oxygen_pool(source_root: str | Path, lambda_value: F,
                               atomic_weights: Mapping[str, float]) -> CedroneOxygenInput:
    """Derive a pool once from pinned printed masses and pending actual Element reads."""
    _require(not isinstance(lambda_value, bool) and isinstance(lambda_value, (int, F))
             and lambda_value in (F(), F(1, 4), F(1)), "unsupported_lambda")
    lam = F(lambda_value)
    _require(isinstance(atomic_weights, Mapping) and set(atomic_weights) == set(ELEMENTS),
             "exactly_CHONS_atomic_weights_required")
    weights = tuple(atomic_weights[e] for e in ELEMENTS)
    _require(all(isinstance(v, float) and math.isfinite(v) and v > 0 for v in weights),
             "positive_finite_binary64_atomic_weights_required")
    source_path = Path(source_root) / SOURCE_RELATIVE
    raw = source_path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == SOURCE_SHA256, "cedrone_source_hash_changed")
    source = json.loads(raw)
    masses = tuple(_fraction(source["nominal_CHONS_kg"][e]) for e in ELEMENTS)
    weights_exact = tuple(F.from_float(v) for v in weights)
    b = tuple(1000 * mass / weight for mass, weight in zip(masses, weights_exact))
    demand = b[0] + b[1] / 4 + b[4] - b[2] / 2
    _require(demand > 0 and sum(masses, F()) == F(".704"), "invalid_nominal_source_pool")
    oxygen, nitrogen = lam * demand, F(79, 21) * lam * demand
    delta = (F(), F(), 2 * oxygen, 2 * nitrogen, F())
    total = tuple(value + change for value, change in zip(b, delta))
    added_mass = sum((weight * change / 1000 for weight, change in zip(weights_exact, delta)), F())
    sources = (
        "cedrone2024:doi10.3390/environments11100210:Table4:reported_sample_CHONS",
        "conditional_assumption:reported_CHONS_available_to_gas_graphite:mineral_allocation_unknown",
        "virtual_design:closed_pool_800K_100000Pa",
    ) + ((f"virtual_design:finite_O2_N2_21_79_lambda_{lam}",) if lam else ())
    pool = TPPool(800., 100000., total, "CEDRONE_TABLE4_REPORTED_SAMPLE_1KG_CONDITIONAL_CHONS",
                  "derived_from_evidence", sources)
    definition = {
        "model_id": MODEL_ID, "lambda": lam, "source_file": str(source_path),
        "source_sha256": SOURCE_SHA256, "source_document": source,
        "element_order": ELEMENTS, "atomic_weights_kg_kmol": dict(zip(ELEMENTS, weights)),
        "exact_represented_atomic_weights": dict(zip(ELEMENTS, weights_exact)),
        "atomic_weights_binding_checked": False, "nominal_CHONS_kg": dict(zip(ELEMENTS, masses)),
        "base_element_mol": b, "reference_O2_demand_mol": demand,
        "added_O2_mol": oxygen, "added_N2_mol": nitrogen, "element_increment_mol": delta,
        "added_O2_mass_kg": 2 * oxygen * weights_exact[2] / 1000,
        "added_N2_mass_kg": 2 * nitrogen * weights_exact[3] / 1000,
        "added_gas_mass_kg": added_mass, "total_element_mol": total,
        "model_input_mass_kg": F(".704") + added_mass,
        "original_reported_sample_basis_kg": F(1), "pool": pool.__dict__,
        "classifications": {"printed_CHNS": "measured_public_data", "printed_O_by_difference": "derived_from_evidence",
                            "mass_to_mol_and_addition": "derived_from_evidence", "finite_21_79_TP_boundary": "virtual_design_choice",
                            "binary64_and_acceptance": "numerical_policy", "material_uncertainty": "unknown"},
        "approximations": "all reported CHONS available to the restricted phases; 21/79 is virtual; D is a formal product reference",
        "qualification": QUALIFICATION,
    }
    return CedroneOxygenInput(pool, weights, definition)


def check_cedrone_oxygen_result(result: TPResult, inputs: CedroneOxygenInput) -> Mapping:
    """Check the same returned phase weights and exact added-mass accounting; no EOS."""
    _require(isinstance(result, TPResult) and isinstance(inputs, CedroneOxygenInput), "expected_TP_value_records")
    _require(result.status == "completed" and result.actual_source_properties_checked is True
             and result.diagnostics is not None and result.diagnostics["checks"]
             and all(v is True for v in result.diagnostics["checks"].values()), "module_result_not_accepted")
    _require(result.request == inputs.pool, "request_input_mismatch")
    _require(result.policy == TPPolicy(solver="vcs").definition(), "numerical_policy_changed")
    _require(result.provider_identity is not None and result.provider_identity.get("kind") == "actual_cantera"
             and result.provider_identity.get("version") == "3.2.0"
             and result.provenance is not None and result.provenance.get("model_sha256") == MODEL_SHA256,
             "thermochemical_provider_or_model_changed")
    _require(result.initial is not None and result.final is not None, "missing_actual_snapshots")
    for point in (result.initial, result.final):
        actual_weights = point["loaded_definition"]["gas_atomic_weights_kg_kmol"]
        _require(set(actual_weights) == set(ELEMENTS)
                 and tuple(actual_weights[e] for e in ELEMENTS) == inputs.atomic_weights_kg_kmol,
                 "atomic_weights_binding_mismatch")
    loaded = result.final["loaded_definition"]
    _require(loaded == result.initial["loaded_definition"], "loaded_thermochemistry_changed")
    rows = loaded["species"]
    _require(tuple(row["name"] for row in rows) == SPECIES, "species_order_changed")
    n = tuple(F(value) * 1000 for value in result.final["amounts_kmol"])
    _require(len(n) == 19 and all(value >= 0 for value in n)
             and n == result.diagnostics["amounts_mol"], "actual_inventory_mismatch")
    atoms = tuple(tuple(F(row["composition"].get(e, 0)) for e in ELEMENTS) for row in rows)
    weights = tuple(F.from_float(value) for value in inputs.atomic_weights_kg_kmol)
    masses = tuple(amount * sum((a * w for a, w in zip(row, weights)), F()) / 1000
                   for amount, row in zip(n, atoms))
    out = tuple(sum((amount * row[j] for amount, row in zip(n, atoms)), F()) for j in range(5))
    residual = tuple(value - original for value, original in zip(out, inputs.pool.element_mol))
    limits = tuple(F(1, 10**10) * (1 + abs(value)) for value in inputs.pool.element_mol)
    _require(residual == result.diagnostics["element_residual_mol"]
             and all(abs(r) <= bound for r, bound in zip(residual, limits)), "original_element_gate_failed")
    definition = inputs.definition()
    mass_difference = sum(masses, F()) - definition["model_input_mass_kg"]
    weighted = sum((weight * r / 1000 for weight, r in zip(weights, residual)), F())
    triangle = sum((weight * abs(r) / 1000 for weight, r in zip(weights, residual)), F())
    propagated = sum((weight * limit / 1000 for weight, limit in zip(weights, limits)), F())
    _require(mass_difference == weighted and abs(weighted) <= triangle <= propagated, "mass_identity_or_bound_failed")
    gas_total = sum(n[:18], F())
    _require(gas_total > 0, "empty_gas_phase")
    return _frozen({
        "atomic_weights_binding_checked": True,
        "species": tuple({"name": name, "amount_mol": n[i], "model_mass_kg": masses[i],
                          "gas_mole_fraction": n[i] / gas_total if i < 18 else None} for i, name in enumerate(SPECIES)),
        "gas_total_mol": gas_total, "graphite_carbon_mol": n[18], "graphite_carbon_mass_kg": masses[18],
        "graphite_carbon_fraction": n[18] / definition["base_element_mol"][0],
        "model_input_mass_kg": definition["model_input_mass_kg"], "model_output_mass_kg": sum(masses, F()),
        "element_residual_mol": dict(zip(ELEMENTS, residual)),
        "mass_audit": {"residual_kg": mass_difference, "weighted_element_residual_kg": weighted,
                       "actual_residual_triangle_bound_kg": triangle, "original_element_tolerance_bound_kg": propagated},
        "basis": "absolute amounts per original 1 kg reported sample, not per kg mixture with added gas",
        "qualification": QUALIFICATION,
    })
