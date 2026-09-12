"""Restricted, closed CHONS TP equilibrium; nominal checks, no sludge qualification.

Public inventories are mol of atoms. Cantera inventories are explicitly kmol.
Only the pinned NASA7 / graphite package is admitted. This module has no kinetics,
thermal-history inference, source discovery, solver fallback, or phase cache.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import time
from types import MappingProxyType

import numpy as np

ELEMENTS = ("C", "H", "O", "N", "S")
SPECIES = ("H2", "H2O", "CO", "CO2", "CH4", "O2", "N2", "NH3", "HCN",
           "NO", "NO2", "N2O", "H2S", "SO2", "SO3", "COS", "CS2", "S2", "C(gr)")
MODEL_SHA256 = "2a0b23f987a0ce4a930ffc9a6a9c682e982676eaa79cfa1af9a4cf40cdad8cfd"
PACK_FILES = frozenset(("derived.json", "source.json", "LICENSE.txt",
                        "original/nasa_gas.yaml", "original/graphite.yaml"))
MODEL_ID = "RESTRICTED_CHONS_TP_NASA1993_1BAR_V1"


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, F)):
        raise ValueError("finite_real_number_required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("finite_real_number_required")
    return result


def _frozen(value: object) -> object:
    """Copy only the small value records returned here, never live providers."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _frozen(v) for k, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_frozen(v) for v in value)
    if value is None or isinstance(value, (str, bool, int, float, F)):
        return value
    raise TypeError(f"unsupported_result_value:{type(value).__name__}")


@dataclass(frozen=True)
class TPPool:
    """An explicit element pool; its scale is not a mass of real sludge."""
    temperature_k: float
    pressure_pa: float
    element_mol: tuple[F, ...]
    basis_id: str
    classification: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        temperature, pressure = _number(self.temperature_k), _number(self.pressure_pa)
        if not 800 <= temperature <= 1200 or pressure != 100000:
            raise ValueError("outside_declared_TP_domain")
        if len(self.element_mol) != 5:
            raise ValueError("exactly_CHONS_required")
        for value in self.element_mol:
            if _number(value) < 0 or value < 0:
                raise ValueError("negative_element_inventory")
        amounts = tuple(F(v) for v in self.element_mol)
        if not any(amounts):
            raise ValueError("empty_element_pool")
        if not isinstance(self.basis_id, str) or not self.basis_id.strip():
            raise ValueError("explicit_basis_required")
        if self.classification not in {"virtual_design_choice", "derived_from_evidence",
                                       "manufactured_test_fixture"}:
            raise ValueError("unsupported_pool_classification")
        if (isinstance(self.source_ids, str) or not self.source_ids
                or any(not isinstance(s, str) or not s.strip() for s in self.source_ids)):
            raise ValueError("explicit_source_ids_required")
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "pressure_pa", pressure)
        object.__setattr__(self, "element_mol", amounts)
        object.__setattr__(self, "source_ids", tuple(self.source_ids))


@dataclass(frozen=True)
class TPPolicy:
    """Declared numerical policy; these tolerances are not physical error bars."""
    solver: str = "vcs"
    rtol: float = 1e-10
    max_steps: int = 1000
    maximum_elapsed_s: float = 10.0

    def __post_init__(self) -> None:
        if self.solver not in {"vcs", "gibbs"} or not 0 < _number(self.rtol) <= 1e-10:
            raise ValueError("unsupported_solver_policy")
        if type(self.max_steps) is not int or not 0 < self.max_steps <= 1000:
            raise ValueError("invalid_solver_step_limit")
        if _number(self.maximum_elapsed_s) <= 0:
            raise ValueError("invalid_wall_limit")

    def definition(self) -> Mapping:
        if self.solver == "vcs":
            effective = {
                "requested_rtol_consumed": False,
                "tolmaj": 1e-8, "tolmin": 1e-6, "tolmaj2": 1e-10, "tolmin2": 1e-8,
                "meaning": "Cantera 3.2.0 TP bridge does not consume err; these are internal defaults, not external acceptance",
                "source_locations": (
                    "Cantera/v3.2.0/src/equil/vcs_MultiPhaseEquil.cpp:406-481",
                    "Cantera/v3.2.0/include/cantera/equil/vcs_solve.h:1284-1293"),
                "source_sha256": (
                    "470730b185a54977bdf4bddafa0719375ffe0bd40d2ddebbec26d7bbd09faa20",
                    "5f25b7a9653fa93871ff9c8baf65739fb01d3c66f4ce2b58df8d4d5caa629be3")}
            initialization = "estimate_equil=0 is forwarded; native VCS uses the supplied estimate"
        else:
            effective = {
                "requested_rtol_consumed": True, "reaction_deltaG_over_RT": self.rtol,
                "meaning": "Gibbs stopping error checks reaction chemical potentials, not element residuals",
                "source_locations": ("Cantera/v3.2.0/src/equil/MultiPhaseEquil.cpp:155-171,626-650",)}
            initialization = "TP Gibbs dispatch does not forward estimate_equil; constructor defaults to linear initial estimate"
        return _frozen({f.name: getattr(self, f.name) for f in fields(self)} | {
            "policy_id": "CHONS_TP_NOMINAL_ACCEPTANCE_V2",
            "requested_native_rtol": self.rtol, "effective_native_tolerances": effective,
            "requested_estimate_equil": 0, "effective_initialization": initialization,
            "element_abs_mol": 1e-10, "element_relative": 1e-10,
            "temperature_abs_k": 1e-8, "pressure_abs_pa": 1e-6,
            "scaled_gap_range": (-1e-10, 1e-7), "active_mu_over_RT": 1e-7,
            "active_fit_amount_over_atoms": 1e-12, "G_descent_over_RTB": 1e-7,
            "wall_limit": "checked at call boundaries; external supervision required for in-flight calls",
            "thermochemical_and_log_interval_error": "unknown"})


@dataclass(frozen=True)
class TPResult:
    """Read-only snapshots, including returned values from unsuccessful calls."""
    status: str
    reason: str | None
    request: TPPool
    policy: Mapping
    seed: Mapping | None
    initial: Mapping | None
    final: Mapping | None
    diagnostics: Mapping | None
    failure: Mapping | None
    provenance: Mapping | None
    provider_identity: Mapping | None
    provider_calls_attempted: int
    provider_calls_completed: int
    elapsed_seconds: float
    actual_source_properties_checked: bool
    material_qualified: bool = False
    training_eligible: bool = False
    qualification: str = "nominal restricted TP composition only; physical/model error unknown"

    def __post_init__(self) -> None:
        for field in fields(self):
            if field.name not in {"request"}:
                object.__setattr__(self, field.name, _frozen(getattr(self, field.name)))


def _load_pack(root: str | Path) -> dict:
    folder = Path(root) / "data/sandbox/research/tp-equilibrium-v1"
    raw = (folder / "model.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MODEL_SHA256:
        raise ValueError("model_source_hash_changed")
    model = json.loads(raw)
    if set(model["files"]) != PACK_FILES or model["model_id"] != MODEL_ID:
        raise ValueError("unexpected_source_package")
    contents = {}
    for name, expected in model["files"].items():
        contents[name] = (folder / name).read_bytes()
        if hashlib.sha256(contents[name]).hexdigest() != expected:
            raise ValueError(f"source_hash_changed:{name}")
    derived = json.loads(contents["derived.json"])
    # The pinned bytes contain only local records: never accept caller YAML/imports.
    if (set(derived) != {"description", "phases", "species"}
            or tuple(s["name"] for s in derived["species"]) != SPECIES
            or [p["name"] for p in derived["phases"]] != ["gas", "graphite"]):
        raise ValueError("unexpected_species_or_phase_set")
    atoms = tuple(tuple(s["composition"].get(e, 0) for e in ELEMENTS)
                  for s in derived["species"])
    return {"model": model, "source": json.loads(contents["source.json"]),
            "derived": derived, "atoms": atoms, "model_sha256": MODEL_SHA256}


def _seed(pool: TPPool, variant: str) -> dict:
    amounts = [F()] * 19
    for species_index, element_index in ((0, 1), (5, 2), (6, 3), (17, 4)):
        amounts[species_index] = pool.element_mol[element_index] / 2
    amounts[18] = pool.element_mol[0]
    if variant == "methane_shift":
        if amounts[18] < F(1, 10) or amounts[0] < F(1, 5):
            raise ValueError("infeasible_methane_shift_seed")
        amounts[18] -= F(1, 10)
        amounts[0] -= F(1, 5)
        amounts[4] += F(1, 10)
    elif variant != "element_basis":
        raise ValueError("unknown_seed_variant")
    if not any(amounts[:18]):
        raise ValueError("unsupported_degenerate_phase_pool")
    kmol = tuple(float(n / 1000) for n in amounts)
    if any(not math.isfinite(v) or (n > 0 and v <= 0) for n, v in zip(amounts, kmol)):
        raise ValueError("unrepresentable_seed_inventory")
    return {"variant": variant, "classification": "numerical_policy", "species": SPECIES,
            "exact_amounts_mol": tuple(amounts), "supplied_amounts_kmol": kmol,
            "meaning": "feasible numerical guess, not actual feed molecular composition"}


def _inventory(pack: dict, pool: TPPool, point: Mapping) -> dict:
    raw = tuple(point["amounts_kmol"])
    if len(raw) != 19 or any(_number(n) < 0 for n in raw):
        raise ValueError("invalid_returned_inventory")
    n = tuple(F(v) * 1000 for v in raw)
    b = tuple(sum((n[i] * pack["atoms"][i][e] for i in range(19)), F()) for e in range(5))
    residual = tuple(out - requested for out, requested in zip(b, pool.element_mol))
    allowed = tuple(all(not a or pool.element_mol[e] > 0 for e, a in enumerate(row))
                    for row in pack["atoms"])
    checks = {
        "nonnegative_finite_inventory": True,
        "elements": all(abs(r) <= F(1, 10**10) * (1 + abs(b0))
                        for r, b0 in zip(residual, pool.element_mol)),
        "structural_zero_elements": all(ok or n[i] == 0 for i, ok in enumerate(allowed)),
        "temperature": abs(_number(point["temperature_k"]) - pool.temperature_k) <= 1e-8,
        "pressure": abs(_number(point["pressure_pa"]) - pool.pressure_pa) <= 1e-6,
        "declared_domain": 800 <= _number(point["temperature_k"]) <= 1200
                           and _number(point["pressure_pa"]) > 0,
    }
    return {"amounts_mol": n, "elements_mol": b, "element_residual_mol": residual,
            "structurally_admitted": allowed, "checks": checks}


def _gibbs(point: Mapping, n: tuple[F, ...]) -> tuple[F, tuple[float | None, ...]]:
    rt = _number(point["gas_constant_j_mol_k"]) * _number(point["temperature_k"])
    standard = tuple(_number(g) for g in point["standard_g_j_mol"])
    if rt <= 0 or len(standard) != 19:
        raise ValueError("invalid_standard_thermochemistry")
    gas_total = sum(n[:18], F())
    if gas_total <= 0:
        raise ValueError("unsupported_degenerate_phase_pool")
    log_total = math.log(gas_total)
    mu = tuple(standard[i] + rt * (math.log(n[i]) - log_total) if n[i] else None
               for i in range(18)) + (standard[18],)
    value = sum((amount * F(potential) for amount, potential in zip(n, mu) if amount), F())
    return value, mu


def _diagnostics(pack: dict, pool: TPPool, initial: Mapping, final: Mapping,
                 policy: TPPolicy) -> dict:
    """Independent ideal-mixture arithmetic; no composition optimizer is added."""
    out = _inventory(pack, pool, final)
    n, b, residual = out["amounts_mol"], out["elements_mol"], out["element_residual_mol"]
    gibbs, mu = _gibbs(final, n)
    seed_g, _ = _gibbs(initial, _inventory(pack, pool, initial)["amounts_mol"])
    rt = _number(final["gas_constant_j_mol_k"]) * _number(final["temperature_k"])
    positive_elements = tuple(i for i, v in enumerate(pool.element_mol) if v > 0)
    atom_total = sum(b, F())
    active = tuple(i for i in range(19) if n[i] > atom_total * F(1, 10**12))
    if not active:
        raise ValueError("unresolved_element_potential_diagnostic")
    matrix = np.array([[pack["atoms"][i][e] for e in positive_elements] for i in active], dtype=float)
    rhs = np.array([mu[i] / rt for i in active], dtype=float)
    fit, _, rank, singular = np.linalg.lstsq(matrix, rhs, rcond=None)
    if rank != len(positive_elements) or not np.all(np.isfinite(fit)):
        raise ValueError("unresolved_element_potential_diagnostic")
    potentials = [0.0] * 5
    for e, value in zip(positive_elements, fit):
        potentials[e] = float(value) * rt
    implied = tuple(math.fsum(a * v for a, v in zip(row, potentials)) for row in pack["atoms"])
    standard = final["standard_g_j_mol"]
    logs = tuple((implied[i] - standard[i]) / rt for i in range(18)
                 if out["structurally_admitted"][i])
    if not logs or not all(math.isfinite(v) for v in logs):
        raise ValueError("unsupported_partition_diagnostic")
    maximum = max(logs)
    log_z = maximum + math.log(math.fsum(math.exp(v - maximum) for v in logs))
    d_carbon = (standard[18] - potentials[0]) / rt if pool.element_mol[0] else None
    delta = max(0.0, log_z, -d_carbon if d_carbon is not None else 0.0)
    penalty = F(rt) * F(delta)
    lower_out = sum((F(v) * a for v, a in zip(potentials, b)), F()) - penalty * atom_total
    lower_requested = (sum((F(v) * a for v, a in zip(potentials, pool.element_mol)), F())
                       - penalty * sum(pool.element_mol, F()))
    gap_out, gap_requested = gibbs - lower_out, gibbs - lower_requested
    correction = (sum((F(v) * r for v, r in zip(potentials, residual)), F())
                  - penalty * sum(residual, F()))
    active_residuals = tuple((mu[i] - implied[i]) / rt for i in active)
    scale = F(rt) * atom_total
    carbon_resolved = n[18] > atom_total * F(1, 10**12)
    carbon_check = (d_carbon is None or (abs(d_carbon) <= 1e-7 if carbon_resolved
                                       else d_carbon >= -1e-7))
    checks = out["checks"] | {
        "nominal_gibbs_gap": -F(1, 10**10) <= gap_out / scale <= F(1, 10**7),
        "resolved_active_chemical_potentials": max(map(abs, active_residuals)) <= 1e-7,
        "graphite_condition": carbon_check,
        "gibbs_descent": gibbs <= seed_g + scale * F(1, 10**7),
    }
    enthalpy = sum((amount * F(_number(h)) for amount, h in zip(n, final["standard_h_j_mol"])), F())
    return out | {"checks": checks, "gibbs_j": gibbs, "seed_gibbs_j": seed_g,
                  "mixture_enthalpy_j": enthalpy,
                  "mixture_entropy_j_k": (enthalpy - gibbs) / F(final["temperature_k"]),
                  "chemical_potentials_j_mol": mu, "element_potentials_j_mol_atoms": tuple(potentials),
                  "resolved_active_species": tuple(SPECIES[i] for i in active),
                  "active_residuals_over_RT": active_residuals, "fit_singular_values": tuple(map(float, singular)),
                  "log_partition_sum": log_z, "graphite_reduced_potential_over_RT": d_carbon,
                  "graphite_fit_status": "resolved" if 18 in active else "trace_or_absent",
                  "partition_penalty": delta, "lower_bound_out_j": lower_out,
                  "lower_bound_requested_j": lower_requested, "gap_out_j": gap_out,
                  "gap_requested_j": gap_requested, "requested_pool_gap_correction_j": correction,
                  "scaled_gap_out": gap_out / scale,
                  "zero_gas_mu": "None denotes the analytic zero-inventory limit; not finite mu",
                  "qualification": "nominal represented-data bounds; full thermochemistry/log error unknown"}


def _nasa_properties(record: Mapping, temperature: float, gas_constant: float) -> tuple[float, ...]:
    thermo = record["thermo"]
    a = thermo["data"][0 if temperature <= thermo["temperature-ranges"][1] else 1]
    t = temperature
    cp = gas_constant * (a[0] + a[1]*t + a[2]*t*t + a[3]*t**3 + a[4]*t**4)
    h = gas_constant*t*(a[0] + a[1]*t/2 + a[2]*t*t/3 + a[3]*t**3/4 + a[4]*t**4/5 + a[5]/t)
    s = gas_constant*(a[0]*math.log(t) + a[1]*t + a[2]*t*t/2 + a[3]*t**3/3 + a[4]*t**4/4 + a[6])
    return h, s, cp, h-t*s


def _property_check(pack: dict, point: Mapping) -> dict:
    actual = tuple(tuple(point[k]) for k in ("standard_h_j_mol", "standard_s_j_mol_k",
                                            "standard_cp_j_mol_k", "standard_g_j_mol"))
    if any(len(row) != 19 for row in actual):
        raise ValueError("incorrect_property_vector_shape")
    residuals = []
    for i, record in enumerate(pack["derived"]["species"]):
        expected = _nasa_properties(record, point["temperature_k"], point["gas_constant_j_mol_k"])
        row = tuple(_number(actual[j][i]) - expected[j] for j in range(4))
        residuals.append(row)
        if any(abs(r) > (1e-5 if j in (0, 3) else 1e-8) + 5e-12*abs(expected[j])
               for j, r in enumerate(row)):
            raise ValueError(f"loaded_NASA7_property_mismatch:{SPECIES[i]}")
    return {"NASA7_residuals_h_s_cp_g": tuple(residuals),
            "join_policy": "T <= midpoint uses low coefficients", "reference_pressure_pa": 100000.0}


class _CanteraBackend:
    """Fresh mutable native objects contained inside one call; never returned."""
    def __init__(self, pack: dict) -> None:
        import cantera as ct
        if ct.__version__ != "3.2.0":
            raise ValueError("cantera_version_mismatch")
        self.ct, self.pack = ct, pack
        self.identity = {"kind": "actual_cantera", "version": ct.__version__,
                         "gas_constant_j_mol_k": float(ct.gas_constant / 1000),
                         "reference_branch": pack["model"]["reference_branch"]}
        self.partial = {}

    def _loaded(self) -> dict:
        loaded = []
        for phase, names in ((self.gas, SPECIES[:18]), (self.carbon, SPECIES[18:])):
            if tuple(phase.species_names) != names:
                raise ValueError("loaded_species_mismatch")
            for species in phase.species():
                record = self.pack["derived"]["species"][SPECIES.index(species.name)]
                thermo = species.thermo
                expected = record["thermo"]
                coefficients = (expected["temperature-ranges"][1], *expected["data"][1], *expected["data"][0])
                if (species.composition != record["composition"] or species.charge != 0
                        or thermo.reference_pressure != 100000.0
                        or thermo.min_temp != expected["temperature-ranges"][0]
                        or thermo.max_temp != expected["temperature-ranges"][2]
                        or tuple(thermo.coeffs) != coefficients):
                    raise ValueError(f"loaded_species_thermo_mismatch:{species.name}")
                loaded.append({"name": species.name, "composition": dict(species.composition),
                               "reference_pressure_pa": float(thermo.reference_pressure),
                               "temperature_range_k": (float(thermo.min_temp), float(thermo.max_temp)),
                               "coefficients_high_then_low": tuple(map(float, thermo.coeffs))})
        if self.gas.thermo_model != "ideal-gas" or self.carbon.thermo_model != "fixed-stoichiometry":
            raise ValueError("loaded_phase_model_mismatch")
        if not math.isclose(self.carbon.density, 2160., rel_tol=1e-14, abs_tol=1e-10):
            raise ValueError("loaded_graphite_density_mismatch")
        return {"species": loaded, "gas_atomic_weights_kg_kmol": dict(zip(self.gas.element_names,
                     map(float, self.gas.atomic_weights))), "carbon_density_kg_m3": float(self.carbon.density)}

    def prepare(self, pool: TPPool, seed: Mapping) -> dict:
        text = json.dumps(self.pack["derived"], allow_nan=False)
        self.gas = self.ct.Solution(yaml=text, name="gas")
        self.partial["gas_constructed"] = {"species": tuple(self.gas.species_names)}
        self.carbon = self.ct.Solution(yaml=text, name="graphite")
        self.partial["graphite_constructed"] = {"species": tuple(self.carbon.species_names)}
        self.loaded = self._loaded()
        self.partial["loaded_definition"] = self.loaded
        self.mix = self.ct.Mixture([(self.gas, 1.0), (self.carbon, 0.0)])
        self.mix.T, self.mix.P = pool.temperature_k, pool.pressure_pa
        self.mix.species_moles = seed["supplied_amounts_kmol"]
        return self.snapshot()

    def snapshot(self) -> dict:
        raw = {"temperature_k": float(self.mix.T), "pressure_pa": float(self.mix.P),
               "amounts_kmol": tuple(map(float, self.mix.species_moles))}
        self.partial["last_inventory_readback"] = raw.copy()
        temperature, pressure = _number(raw["temperature_k"]), _number(raw["pressure_pa"])
        amounts = raw["amounts_kmol"]
        if len(amounts) != 19 or any(_number(n) < 0 for n in amounts):
            raise ValueError("invalid_returned_inventory")
        if not any(amounts[:18]):
            raise ValueError("unsupported_degenerate_phase_pool")
        if not 800 <= temperature <= 1200 or abs(pressure - 100000.) > 1e-6:
            raise ValueError("snapshot_outside_declared_TP_domain")
        # Python Mixture.phase(n) only returns an object. Set the phase state
        # explicitly from the saved inventory; never normalize/write back n.
        self.gas.TPX = temperature, pressure, amounts[:18]
        self.carbon.TP = temperature, pressure
        raw["phase_snapshot_state_policy"] = "explicit_readback_TP_and_gas_amount_ratios; absolute_kmol_unmodified"
        r = float(self.ct.gas_constant / 1000)
        raw.update({"gas_constant_j_mol_k": r, "loaded_definition": self.loaded})
        self.partial["partial_snapshot"] = raw.copy()
        for key, attribute, factor in (("standard_h_j_mol", "standard_enthalpies_RT", r*temperature),
                                      ("standard_s_j_mol_k", "standard_entropies_R", r),
                                      ("standard_cp_j_mol_k", "standard_cp_R", r),
                                      ("standard_g_j_mol", "standard_gibbs_RT", r*temperature),
                                      ("chemical_potentials_j_mol", "chemical_potentials", .001)):
            raw[key] = tuple(float(v)*factor for phase in (self.gas, self.carbon)
                             for v in getattr(phase, attribute))
            self.partial["partial_snapshot"] = raw.copy()
        return raw

    def equilibrate(self, policy: TPPolicy) -> dict:
        try:
            self.mix.equilibrate("TP", solver=policy.solver, rtol=policy.rtol,
                                 max_steps=policy.max_steps, max_iter=100,
                                 estimate_equil=0, log_level=0)
        except Exception:
            try:
                self.partial["state_after_failure"] = self.snapshot()
            except Exception as exc:
                self.partial["failure_readback_error"] = {"error_type": type(exc).__name__, "message": str(exc)}
            raise
        self.partial["native_equilibrium_returned"] = True
        # A post-return readback failure retains its prefix and is not retried.
        return self.snapshot()


class _WallLimit(RuntimeError):
    pass


def solve_tp(pool: TPPool, source_root: str | Path, *, policy: TPPolicy = TPPolicy(),
             seed_variant: str = "element_basis",
             _backend_factory: Callable | None = None) -> TPResult:
    """One fixed-solver attempt. A private fake seam never qualifies source physics."""
    if type(pool) is not TPPool or type(policy) is not TPPolicy:
        raise TypeError("exact_TPPool_and_TPPolicy_required")
    started = time.monotonic()
    backend = None
    seed = initial = final = diagnostics = provenance = identity = failure = None
    attempted = completed = 0
    source_checked = False
    status, reason, stage = "completed", None, "construction"

    def guard() -> None:
        if time.monotonic() - started > policy.maximum_elapsed_s:
            raise _WallLimit("maximum_elapsed_seconds")

    try:
        pack = _load_pack(source_root)
        provenance = {"model": pack["model"], "source": pack["source"], "model_sha256": MODEL_SHA256}
        seed = _seed(pool, seed_variant)
        guard()
        attempted += 1
        backend = (_CanteraBackend if _backend_factory is None else _backend_factory)(pack)
        completed += 1
        identity = _frozen(dict(backend.identity) | {
            "requested_native_solver": policy.solver, "requested_native_rtol": policy.rtol,
            "effective_native_tolerances": policy.definition()["effective_native_tolerances"]})
        guard()
        attempted += 1
        initial = _frozen(backend.prepare(pool, seed))
        completed += 1
        guard()
        initial_inventory = _inventory(pack, pool, initial)
        if not all(initial_inventory["checks"].values()):
            raise ValueError("initial_inventory_projection_or_TP_rejected")
        initial_property = None
        if _backend_factory is None:
            initial_property = _property_check(pack, initial)
        stage = "solve"
        guard()
        attempted += 1
        final = _frozen(backend.equilibrate(policy))
        completed += 1
        guard()
        stage = "postcheck"
        diagnostics = _diagnostics(pack, pool, initial, final, policy)
        if _backend_factory is None:
            diagnostics["source_properties"] = {"initial": initial_property, "final": _property_check(pack, final)}
            source_checked = True
        diagnostics["checks"]["initial_inventory_projection"] = all(initial_inventory["checks"].values())
        _load_pack(source_root)
        diagnostics["checks"]["source_files_unchanged"] = True
        diagnostics["actual_source_properties_checked"] = source_checked
        if not all(diagnostics["checks"].values()):
            raise ValueError("nominal_posterior_checks_rejected")
        guard()
    except Exception as exc:
        status = "resource_limit" if isinstance(exc, _WallLimit) else f"{stage}_failed"
        reason = str(exc)
        failure = {"stage": stage, "error_type": type(exc).__name__, "reason": str(exc),
                   "partial": _frozen(backend.partial) if backend is not None else None}
    finished = time.monotonic()
    elapsed = finished - started
    if elapsed > policy.maximum_elapsed_s and status == "completed":
        status, reason = "resource_limit", "maximum_elapsed_seconds_at_return"
        failure = {"stage": "return", "reason": reason, "partial": _frozen(backend.partial)}
    return TPResult(status, reason, pool, policy.definition(), seed, initial, final, diagnostics,
                    failure, provenance, identity, attempted, completed, elapsed, source_checked)
