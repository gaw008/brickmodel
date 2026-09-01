from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..chemistry.formula import formula_element_moles, formula_molar_mass
from ..chemistry.stoichiometry import GAS_FORMULAS, ReactionPotential, initial_element_inventory, reaction_potentials
from ..physics.kinetics import arrhenius_rate_constant
from ..physics.sintering import reduced_sintering_rate
from ..types import CaseConfig, ForwardResult, RunStatus

REACTIONS = ("free_water_removal", "organic_oxidation", "kaolinite_dehydroxylation", "carbonate_decomposition")
GASES = ("H2O", "CO2", "N2", "SO2")
SIGMA_SB = 5.670374419e-8
R_GAS = 8.31446261815324


@dataclass
class ModelContext:
    case: CaseConfig
    parameters: dict[str, Any]
    potentials: list[ReactionPotential]
    gas_mass_matrix: np.ndarray
    rho_dry: float
    water_ratio: float
    cp: float
    conductivity: float
    diffusivity: float
    emissivity: float
    true_density: float
    connectivity: float
    dense_strength: float
    strength_coefficient: float
    bloating_pressure_scale_Pa: float
    d32_m: float
    kinetic_A: np.ndarray
    kinetic_E: np.ndarray
    speed_ratio: float
    residence_time_s: float
    half_thickness_m: float
    profile: dict[str, np.ndarray]
    parameter_pack_hash: str


def _load_pack() -> tuple[dict[str, Any], str]:
    path = Path(__file__).resolve().parents[3] / "data" / "parameter_pack_synthetic_v1.json"
    payload = path.read_bytes()
    return json.loads(payload), hashlib.sha256(payload).hexdigest()


def build_context(case: CaseConfig, parameters: dict[str, Any] | None = None) -> ModelContext:
    p = dict(parameters or {})
    pack, pack_hash = _load_pack()
    props = pack["parameters"]
    potentials = reaction_potentials(case)
    gas_matrix = np.zeros((len(REACTIONS), len(GASES)))
    for r, potential in enumerate(potentials):
        for g, species in enumerate(GASES):
            gas_matrix[r, g] = potential.gas_moles_per_kg_dry.get(species, 0.0) * formula_molar_mass(GAS_FORMULAS[species])
    phi0 = float(case.raw["geometry"]["green_porosity"])
    true_density = float(props["solid_true_density_kg_m3"]["default"]) * float(p.get("density_scale", 1.0))
    rho_dry = (1.0 - phi0) * true_density
    forming_w = float(case.raw["forming"]["moisture_wet_basis"])
    water_ratio = forming_w / (1.0 - forming_w)
    reaction_pack = pack["reactions"]
    kinetic_A = np.array([reaction_pack[name]["A_1_s"] for name in REACTIONS], dtype=float) * float(p.get("kinetics_scale", 1.0))
    kinetic_E = np.array([reaction_pack[name]["E_J_mol"] for name in REACTIONS], dtype=float)
    speed = float(p.get("speed_ratio", case.raw["kiln"]["speed_ratio"]))
    speed_bounds = case.raw["kiln"]["speed_ratio_bounds"]
    if not float(speed_bounds[0]) <= speed <= float(speed_bounds[1]):
        raise ValueError("speed_ratio is outside declared human-approved synthetic bounds")
    residence = float(case.raw["kiln"]["length_m"]) / (float(case.raw["kiln"]["reference_speed_m_s"]) * speed)
    knots = case.raw["kiln"]["profile"]
    profile = {
        key: np.array([float(item[key]) for item in knots], dtype=float)
        for key in ("s_m", "gas_temperature_K", "wall_temperature_K", "oxygen_mole_fraction", "h_W_m2_K", "km_m_s", "ambient_pressure_Pa")
    }
    d32 = sum(
        float(feed["dry_mass_fraction"]) * float(feed["particle_size_distribution"]["d50_m"])
        for feed in case.raw["feedstocks"].values()
    )
    return ModelContext(
        case=case,
        parameters=p,
        potentials=potentials,
        gas_mass_matrix=gas_matrix,
        rho_dry=rho_dry,
        water_ratio=water_ratio,
        cp=float(props["solid_specific_heat_J_kg_K"]["default"]) * float(p.get("cp_scale", 1.0)),
        conductivity=float(props["solid_thermal_conductivity_W_m_K"]["default"]) * float(p.get("conductivity_scale", 1.0)),
        diffusivity=float(props["effective_diffusivity_m2_s"]["default"]) * float(p.get("diffusivity_scale", 1.0)),
        emissivity=float(props["emissivity"]["default"]) * float(p.get("emissivity_scale", 1.0)),
        true_density=true_density,
        connectivity=min(1.0, max(0.0, float(props["open_pore_connectivity"]["default"]) * float(p.get("connectivity_scale", 1.0)))),
        dense_strength=float(props["dense_strength_proxy_Pa"]["default"]) * float(p.get("strength_scale", 1.0)),
        strength_coefficient=float(props["strength_porosity_coefficient"]["default"]),
        bloating_pressure_scale_Pa=float(props["bloating_pressure_scale_Pa"]["default"]) * float(p.get("bloating_pressure_scale", 1.0)),
        d32_m=d32,
        kinetic_A=kinetic_A,
        kinetic_E=kinetic_E,
        speed_ratio=speed,
        residence_time_s=residence,
        half_thickness_m=float(case.raw["geometry"]["brick_half_thickness_m"]),
        profile=profile,
        parameter_pack_hash=pack_hash,
    )


def boundary(ctx: ModelContext, time_s: float) -> dict[str, float]:
    position = min(ctx.profile["s_m"][-1], float(ctx.case.raw["kiln"]["reference_speed_m_s"]) * ctx.speed_ratio * time_s)
    return {key: float(np.interp(position, ctx.profile["s_m"], values)) for key, values in ctx.profile.items() if key != "s_m"}


def liquid_fraction(temperature_K: np.ndarray | float) -> np.ndarray:
    values = np.asarray(temperature_K, dtype=float)
    exponent = np.clip(-(values - 1150.0) / 45.0, -50.0, 50.0)
    return 0.34 / (1.0 + np.exp(exponent))


def reaction_rates(ctx: ModelContext, temperature_K: np.ndarray, extents: np.ndarray, oxygen_fraction: float) -> np.ndarray:
    if not bool(ctx.parameters.get("reactions_enabled", True)):
        return np.zeros_like(extents)
    rates = np.empty_like(extents)
    for index in range(len(REACTIONS)):
        multiplier = max(0.02, oxygen_fraction / 0.21) if index == 1 else 1.0
        hazard = np.vectorize(arrhenius_rate_constant)(ctx.kinetic_A[index], ctx.kinetic_E[index], temperature_K, multiplier)
        rates[index] = hazard * (1.0 - extents[index])
    return rates


def sintering_rate(ctx: ModelContext, temperature_K: np.ndarray) -> np.ndarray:
    scale = float(ctx.parameters.get("sintering_scale", 1.0))
    return scale * np.vectorize(reduced_sintering_rate)(temperature_K, liquid_fraction(temperature_K), ctx.d32_m)


def _field(values: Any, unit: str, *, basis: str = "", proxy: bool = False, status: str = "resolved") -> dict[str, Any]:
    return {"values": values, "unit": unit, "basis": basis, "proxy": proxy, "status": status}


def _summary(value: Any, unit: str, *, proxy: bool = False, status: str = "resolved", validity: str = "synthetic screening domain") -> dict[str, Any]:
    return {"value": value, "unit": unit, "proxy": proxy, "status": status, "validity": validity}


def finalize_result(
    ctx: ModelContext,
    fidelity: str,
    time: np.ndarray,
    x: np.ndarray,
    temperature: np.ndarray,
    extents: np.ndarray,
    gas: np.ndarray,
    ln_volume: np.ndarray,
    released: np.ndarray,
    q_boundary: np.ndarray,
    q_reaction: np.ndarray,
    solver_success: bool,
    solver_message: str,
    solver_statistics: dict[str, Any],
) -> ForwardResult:
    raw_extents = extents
    projected_extents = np.clip(raw_extents, 0.0, 1.0)
    extent_projection_max = float(np.max(np.abs(projected_extents - raw_extents)))
    extents = projected_extents
    volume_ratio = np.exp(ln_volume)
    mean_extents = raw_extents[-1].mean(axis=1)
    bounded_mean_extents = extents[-1].mean(axis=1)
    actual_gas_density = gas[-1].mean(axis=1) + released[-1]
    generated_gas_density = ctx.rho_dry * (mean_extents @ ctx.gas_mass_matrix)
    gas_residual = generated_gas_density - actual_gas_density
    dry_loss = np.array([
        0.0,
        ctx.potentials[1].reactant_mass_kg_per_kg_dry,
        ctx.potentials[2].gas_mass_kg_per_kg_dry,
        ctx.potentials[3].gas_mass_kg_per_kg_dry,
    ])
    feed_loss_density = ctx.rho_dry * float(mean_extents @ dry_loss)
    water_remaining = ctx.rho_dry * ctx.water_ratio * (1.0 - mean_extents[0])
    oxygen_in_density = ctx.rho_dry * mean_extents[1] * ctx.potentials[1].oxygen_in_mol_O2_per_kg_dry * formula_molar_mass("O2")
    initial_mass_density = ctx.rho_dry * (1.0 + ctx.water_ratio)
    final_condensed_density = ctx.rho_dry - feed_loss_density + water_remaining
    mass_residual = initial_mass_density + oxygen_in_density - final_condensed_density - float(actual_gas_density.sum())
    mass_relative = abs(mass_residual) / max(initial_mass_density + oxygen_in_density, 1.0)
    gas_relative = float(np.max(np.abs(gas_residual))) / max(float(generated_gas_density.sum()), 1.0)

    initial_elements = {key: value * ctx.rho_dry for key, value in initial_element_inventory(ctx.case).items()}
    initial_water_moles = ctx.rho_dry * ctx.water_ratio / formula_molar_mass("H2O")
    for element, value in formula_element_moles("H2O", initial_water_moles).items():
        initial_elements[element] = initial_elements.get(element, 0.0) + value
    left = dict(initial_elements)
    left["O"] = left.get("O", 0.0) + 2.0 * ctx.rho_dry * mean_extents[1] * ctx.potentials[1].oxygen_in_mol_O2_per_kg_dry
    condensed = dict(initial_elements)
    for index, potential in enumerate(ctx.potentials):
        for element, value in potential.feed_elements_released_mol_per_kg_dry.items():
            condensed[element] = condensed.get(element, 0.0) - ctx.rho_dry * mean_extents[index] * value
    gas_elements: dict[str, float] = {}
    for species, mass in zip(GASES, actual_gas_density):
        amount = mass / formula_molar_mass(GAS_FORMULAS[species])
        for element, value in formula_element_moles(GAS_FORMULAS[species], amount).items():
            gas_elements[element] = gas_elements.get(element, 0.0) + value
    element_residual: dict[str, float] = {}
    for element in set(left) | set(condensed) | set(gas_elements):
        element_residual[element] = left.get(element, 0.0) - condensed.get(element, 0.0) - gas_elements.get(element, 0.0)
    element_relative = {
        element: abs(value) / max(abs(left.get(element, 0.0)), 1e-12) for element, value in element_residual.items()
    }
    max_element = max(element_relative.values(), default=0.0)

    rho_heat = ctx.rho_dry * (1.0 + ctx.water_ratio)
    stored_energy = rho_heat * ctx.cp * (float(temperature[-1].mean()) - float(temperature[0].mean()))
    supplied_energy = float(q_boundary[-1] + q_reaction[-1])
    energy_residual = stored_energy - supplied_energy
    energy_relative = abs(energy_residual) / max(abs(q_boundary[-1]) + abs(q_reaction[-1]), 1.0)

    local_feed_loss = ctx.rho_dry * np.tensordot(extents, dry_loss, axes=(1, 0))
    solid_mass_density = ctx.rho_dry - local_feed_loss
    porosity_raw = 1.0 - solid_mass_density / (ctx.true_density * volume_ratio)
    porosity = np.clip(porosity_raw, 0.0, 1.0)
    open_porosity = porosity * ctx.connectivity
    liquid = liquid_fraction(temperature)
    final_volume = float(volume_ratio[-1].mean())
    final_dry_mass = ctx.rho_dry - feed_loss_density
    bulk_density = final_dry_mass / final_volume
    final_open = float(open_porosity[-1].mean())
    shrinkage = 1.0 - final_volume ** (1.0 / 3.0)
    absorption = 100.0 * 1000.0 * final_open / max(bulk_density, 1.0)

    gas_moles = np.zeros_like(gas)
    for index, species in enumerate(GASES):
        gas_moles[:, index, :] = gas[:, index, :] / formula_molar_mass(GAS_FORMULAS[species])
    generated_partial_pressure = R_GAS * temperature * gas_moles.sum(axis=1) / np.maximum(open_porosity * volume_ratio, 1e-6)
    overpressure = float(np.max(generated_partial_pressure))
    if temperature.shape[1] == 1:
        boundary_differences = np.array([abs(boundary(ctx, t)["gas_temperature_K"] - temp[0]) for t, temp in zip(time, temperature)])
        gradient = 0.12 * boundary_differences
    else:
        gradient = np.abs(temperature[:, 0] - temperature[:, -1])
    max_gradient = float(np.max(gradient))
    crack_risk = max_gradient / 600.0
    bloating_risk = overpressure / ctx.bloating_pressure_scale_Pa
    underfire_risk = float(np.max(1.0 - bounded_mean_extents[1:]))
    overfire_risk = float(np.max(liquid)) / 0.45
    strength = ctx.dense_strength * math.exp(-ctx.strength_coefficient * final_open) * max(0.2, 1.0 - 0.2 * min(crack_risk, 1.0))
    stress_proxy = max_gradient * 1e6 * 1e-5 / 0.75
    reaction_completion = {name: float(value) for name, value in zip(REACTIONS, bounded_mean_extents)}
    released_per_dry = {name: float(value / ctx.rho_dry) for name, value in zip(GASES, released[-1])}
    phase_amounts = {"solid_pseudo": float(1.0 - liquid[-1].mean()), "oxide_liquid_ideal_pseudo": float(liquid[-1].mean())}

    flags = ["synthetic_demo", "research_only", "thermo_database_gap", "performance_proxy_unresolved_for_certification", "environmental_threshold_missing"]
    warnings = [
        "Synthetic boundary, feedstocks and parameter intervals are not plant facts.",
        "Ideal pseudo-liquid and pure-phase coverage do not represent a complete multicomponent oxide-liquid database.",
        "Strength, water absorption, stress and defect metrics are closure-dependent proxies, not certification results.",
        "No PLC, kiln, robot or production-control interface is implemented.",
    ]
    if fidelity == "L1":
        warnings.append("One-dimensional half-slab omits holes, corners, stacking contact and kiln-flow feedback.")
    if extent_projection_max > 0.0:
        warnings.append(f"Reaction extents received an explicit [0,1] numerical projection; max correction={extent_projection_max:.3e}.")
    bounds_ok = bool(np.all(np.isfinite(temperature)) and extent_projection_max <= 1e-5 and np.all((porosity_raw >= -1e-6) & (porosity_raw <= 1.0 + 1e-6)))
    conservation_ok = mass_relative < 1e-8 and max_element < 1e-8 and energy_relative < 1e-4 and gas_relative < 1e-8
    success = solver_success and bounds_ok and conservation_ok
    status = RunStatus("success" if success else ("conservation_failure" if solver_success else "solver_failure"), solver_message, success)
    fields = {
        "temperature": _field(temperature[:, 0].tolist() if temperature.shape[1] == 1 else temperature.tolist(), "K", basis="cell"),
        "reaction_extents": {name: _field(extents[:, index, 0].tolist() if temperature.shape[1] == 1 else extents[:, index, :].tolist(), "1", basis="cell") for index, name in enumerate(REACTIONS)},
        "gas_concentrations": {name: _field(gas[:, index, 0].tolist() if temperature.shape[1] == 1 else gas[:, index, :].tolist(), "kg/m3_reference_bulk", basis="deforming-cell extensive inventory divided by initial volume") for index, name in enumerate(GASES)},
        "gas_overpressure": _field(generated_partial_pressure[:, 0].tolist() if temperature.shape[1] == 1 else generated_partial_pressure.tolist(), "Pa", proxy=True),
        "liquid_fraction": _field(liquid[:, 0].tolist() if temperature.shape[1] == 1 else liquid.tolist(), "1", proxy=True, status="ideal_pseudo_coverage_limited"),
        "total_porosity": _field(porosity[:, 0].tolist() if temperature.shape[1] == 1 else porosity.tolist(), "1"),
        "open_porosity": _field(open_porosity[:, 0].tolist() if temperature.shape[1] == 1 else open_porosity.tolist(), "1", proxy=True),
        "volume_ratio": _field(volume_ratio[:, 0].tolist() if temperature.shape[1] == 1 else volume_ratio.tolist(), "1"),
        "sintering_strain": _field((np.log(volume_ratio) / 3.0)[:, 0].tolist() if temperature.shape[1] == 1 else (np.log(volume_ratio) / 3.0).tolist(), "1", proxy=True),
        "stress_proxy": _field((gradient * 1e6 * 1e-5 / 0.75).tolist(), "Pa", proxy=True),
    }
    summary = {
        "residence_time_s": _summary(ctx.residence_time_s, "s"),
        "bulk_density_kg_m3": _summary(bulk_density, "kg/m3"),
        "open_porosity": _summary(final_open, "1", proxy=True),
        "linear_shrinkage": _summary(shrinkage, "1", proxy=True),
        "water_absorption_proxy_percent": _summary(absorption, "%", proxy=True),
        "strength_proxy_Pa": _summary(strength, "Pa", proxy=True, status="unresolved_for_certification"),
        "liquid_fraction": _summary(float(liquid[-1].mean()), "1", proxy=True, status="ideal_pseudo_coverage_limited"),
        "phase_amounts": _summary(phase_amounts, "mass_fraction_proxy", proxy=True, status="coverage_limited"),
        "released_gas_kg_per_kg_dry": _summary(released_per_dry, "kg/kg_dry"),
        "max_overpressure_Pa": _summary(overpressure, "Pa", proxy=True),
        "max_center_surface_temperature_difference_K": _summary(max_gradient, "K", proxy=fidelity == "L0"),
        "stress_proxy_Pa": _summary(stress_proxy, "Pa", proxy=True),
        "reaction_completion": _summary(reaction_completion, "1"),
        "cracking_risk": _summary(crack_risk, "1", proxy=True),
        "bloating_risk": _summary(bloating_risk, "1", proxy=True),
        "underfiring_risk": _summary(underfire_risk, "1", proxy=True),
        "overfiring_risk": _summary(overfire_risk, "1", proxy=True),
        "warpage_risk": _summary(max_gradient / 800.0, "1", proxy=True),
        "efflorescence_risk": _summary(None, "1", proxy=True, status="unresolved"),
        "thermo_coverage_score": _summary(0.78, "1", status="coverage_limited"),
        "environmental_status": _summary(None, "", status="not_evaluated", validity="thresholds absent"),
    }
    conservation = {
        "mass_relative_residual": mass_relative,
        "gas_species_relative_residual": gas_relative,
        "element_relative_residual_by_element": element_relative,
        "max_element_relative_residual": max_element,
        "energy_relative_residual": energy_relative,
        "energy_residual_J_m3": energy_residual,
        "extent_projection_max": extent_projection_max,
        "extent_projection_tolerance": 1e-5,
        "tolerances": {"mass": 1e-8, "element": 1e-8, "energy": 1e-4},
        "storage_basis": "deforming-cell extensive inventories on reference volume",
    }
    provenance = {
        "spec_version": ctx.case.raw.get("spec_version"),
        "case_hash": ctx.case.content_hash,
        "parameter_pack_hash": ctx.parameter_pack_hash,
        "parameter_overrides": ctx.parameters,
        "thermo_backend": "minimal_ideal_pseudo_coverage_limited",
    }
    return ForwardResult(fidelity, status, {"time_s": time.tolist(), "x_m": x.tolist()}, fields, summary, conservation, flags, warnings, provenance, solver_statistics)
