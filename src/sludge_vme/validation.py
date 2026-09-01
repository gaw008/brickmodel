from __future__ import annotations

import math
from typing import Any

from .types import CaseConfig, ValidationIssue, ValidationReport

TOLERANCE = 1e-8
REQUIRED_FEEDS = ("shale", "coal_gangue", "sludge")
REQUIRED_BASIS = {
    "feed_fraction": "kg_dry_solids",
    "moisture": "kg_water_per_kg_wet_feed",
    "internal_temperature": "K",
    "internal_pressure": "Pa",
    "internal_time": "s",
}


def _issue(report: ValidationReport, path: str, code: str, message: str, warning: bool = False) -> None:
    target = report.warnings if warning else report.errors
    target.append(ValidationIssue(path, code, message))


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _positive(report: ValidationReport, value: Any, path: str) -> bool:
    if not _finite(value) or float(value) <= 0.0:
        _issue(report, path, "invalid_positive_value", "value must be finite and strictly positive")
        return False
    return True


def _ordered_bounds(report: ValidationReport, value: Any, path: str) -> tuple[float, float] | None:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(_finite(item) for item in value)
        or float(value[0]) >= float(value[1])
    ):
        _issue(report, path, "invalid_bounds", "bounds must be two finite values with lower < upper")
        return None
    return float(value[0]), float(value[1])


def _positive_count(report: ValidationReport, value: Any, path: str, *, power_of_two: bool = False) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        _issue(report, path, "invalid_positive_count", "count must be a positive integer")
        return None
    if power_of_two and value & (value - 1):
        _issue(report, path, "invalid_power_of_two_count", "Sobol/UQ count must be a positive power of two")
        return None
    return value


def _simplex(report: ValidationReport, values: list[Any], path: str, key: str) -> None:
    numeric = [float(value) for value in values if _finite(value)]
    for index, value in enumerate(values):
        if not _finite(value) or float(value) < 0.0:
            _issue(report, f"{path}[{index}].fraction", "invalid_fraction", "fraction must be finite and nonnegative")
    residual = sum(numeric) - 1.0
    report.normalized_simplex_residuals[key] = residual
    if len(numeric) != len(values) or abs(residual) > TOLERANCE:
        _issue(report, path, "simplex_not_closed", f"fractions must sum to one within {TOLERANCE:g}; residual={residual:.6g}")


def validate_case(case: CaseConfig) -> ValidationReport:
    raw = case.raw
    report = ValidationReport()
    basis = raw.get("basis")
    if not isinstance(basis, dict):
        _issue(report, "$.basis", "missing_basis", "canonical basis object is required")
    else:
        for key, expected in REQUIRED_BASIS.items():
            if basis.get(key) != expected:
                _issue(report, f"$.basis.{key}", "invalid_basis", f"expected {expected!r}")

    feeds = raw.get("feedstocks")
    if not isinstance(feeds, dict):
        _issue(report, "$.feedstocks", "missing_feedstocks", "feedstocks object is required")
        return report
    for name in REQUIRED_FEEDS:
        if name not in feeds:
            _issue(report, f"$.feedstocks.{name}", "missing_feedstock", "required feedstock is missing")
    feed_values = [feeds[name].get("dry_mass_fraction") for name in feeds]
    numeric_feed = [float(v) for v in feed_values if _finite(v)]
    feed_residual = sum(numeric_feed) - 1.0
    report.normalized_simplex_residuals["dry_feed_fractions"] = feed_residual
    if len(numeric_feed) != len(feed_values) or any(value < 0 for value in numeric_feed) or abs(feed_residual) > TOLERANCE:
        _issue(report, "$.feedstocks", "dry_feed_simplex_not_closed", "dry_mass_fraction values must be nonnegative and sum to one")

    sourced = 0
    for name, feed in feeds.items():
        prefix = f"$.feedstocks.{name}"
        components = feed.get("components")
        if not isinstance(components, list) or not components:
            _issue(report, f"{prefix}.components", "missing_components", "nonempty canonical component partition is required")
        else:
            _simplex(report, [item.get("fraction") for item in components], f"{prefix}.components", f"{name}.components")
            identifiers = [item.get("id") for item in components]
            if len(identifiers) != len(set(identifiers)):
                _issue(report, f"{prefix}.components", "duplicate_component_id", "component ids must be unique within a feedstock")
            for index, component in enumerate(components):
                if component.get("kind") == "amorphous_oxide_pool":
                    oxides = component.get("oxide_fractions", {})
                    if not isinstance(oxides, dict) or not oxides:
                        _issue(report, f"{prefix}.components[{index}].oxide_fractions", "missing_oxide_partition", "oxide fractions are required")
                    else:
                        residual = sum(float(v) for v in oxides.values()) - 1.0
                        report.normalized_simplex_residuals[f"{name}.components[{index}].oxide_fractions"] = residual
                        if any(not _finite(v) or float(v) < 0 for v in oxides.values()) or abs(residual) > TOLERANCE:
                            _issue(report, f"{prefix}.components[{index}].oxide_fractions", "oxide_simplex_not_closed", "oxide fractions must be nonnegative and sum to one")
                elif not isinstance(component.get("formula"), dict) or not component.get("formula"):
                    _issue(report, f"{prefix}.components[{index}].formula", "missing_formula", "formula is required for non-oxide components")
        declared = feed.get("declared_double_counts", [])
        if declared:
            _issue(report, f"{prefix}.declared_double_counts", "element_double_count", "declared overlapping inventories are forbidden")
            report.element_double_count_checks[name] = "failed"
        else:
            report.element_double_count_checks[name] = "passed"
        psd = feed.get("particle_size_distribution", {})
        try:
            d10, d50, d90 = (float(psd[key]) for key in ("d10_m", "d50_m", "d90_m"))
            if not (0.0 < d10 < d50 < d90):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            _issue(report, f"{prefix}.particle_size_distribution", "invalid_psd_order", "require 0 < d10_m < d50_m < d90_m")
        morphology = feed.get("morphology", {})
        sphericity = morphology.get("sphericity")
        aspect = morphology.get("aspect_ratio")
        if not _finite(sphericity) or not 0.0 < float(sphericity) <= 1.0:
            _issue(report, f"{prefix}.morphology.sphericity", "invalid_sphericity", "sphericity must be in (0, 1]")
        if not _finite(aspect) or float(aspect) < 1.0:
            _issue(report, f"{prefix}.morphology.aspect_ratio", "invalid_aspect_ratio", "aspect_ratio must be >= 1")
        material_properties = feed.get("material_properties", {})
        if not isinstance(material_properties, dict):
            _issue(report, f"{prefix}.material_properties", "missing_material_properties", "bounded material properties are required")
        else:
            for key in (
                "true_density_kg_m3",
                "specific_heat_J_kg_K",
                "thermal_conductivity_W_m_K",
                "effective_gas_diffusivity_m2_s",
            ):
                _positive(report, material_properties.get(key), f"{prefix}.material_properties.{key}")
        moisture = feed.get("free_moisture_wet_basis")
        if not _finite(moisture) or not 0.0 <= float(moisture) < 1.0:
            _issue(report, f"{prefix}.free_moisture_wet_basis", "invalid_moisture", "wet-basis moisture must be in [0, 1)")
        if isinstance(feed.get("source"), dict) and feed["source"].get("kind"):
            sourced += 1

    report.source_coverage = sourced / max(len(feeds), 1)
    forming = raw.get("forming", {})
    if not isinstance(forming, dict):
        _issue(report, "$.forming", "missing_forming", "forming object is required")
        forming = {}
    forming_moisture = forming.get("moisture_wet_basis")
    if not _finite(forming_moisture) or not 0.0 <= float(forming_moisture) < 1.0:
        _issue(report, "$.forming.moisture_wet_basis", "invalid_forming_moisture", "forming wet-basis moisture must be in [0, 1)")
    compaction = forming.get("compaction_factor")
    if not _finite(compaction) or not 0.0 < float(compaction) <= 1.0:
        _issue(report, "$.forming.compaction_factor", "invalid_compaction_factor", "compaction factor must be in (0, 1]")
    _positive(report, forming.get("initial_temperature_K"), "$.forming.initial_temperature_K")

    geometry = raw.get("geometry", {})
    if not isinstance(geometry, dict):
        _issue(report, "$.geometry", "missing_geometry", "geometry object is required")
        geometry = {}
    _positive(report, geometry.get("brick_half_thickness_m"), "$.geometry.brick_half_thickness_m")
    _positive(report, geometry.get("initial_bulk_volume_m3"), "$.geometry.initial_bulk_volume_m3")
    green_porosity = geometry.get("green_porosity")
    if not _finite(green_porosity) or not 0.0 < float(green_porosity) < 1.0:
        _issue(report, "$.geometry.green_porosity", "invalid_porosity", "green porosity must be in (0, 1)")

    kiln = raw.get("kiln", {})
    if not isinstance(kiln, dict):
        _issue(report, "$.kiln", "missing_kiln", "kiln object is required")
        kiln = {}
    length_ok = _positive(report, kiln.get("length_m"), "$.kiln.length_m")
    _positive(report, kiln.get("reference_speed_m_s"), "$.kiln.reference_speed_m_s")
    speed_bounds = _ordered_bounds(report, kiln.get("speed_ratio_bounds"), "$.kiln.speed_ratio_bounds")
    speed = kiln.get("speed_ratio")
    if not _finite(speed):
        _issue(report, "$.kiln.speed_ratio", "invalid_speed_ratio", "speed ratio must be finite")
    elif speed_bounds is not None and not speed_bounds[0] <= float(speed) <= speed_bounds[1]:
        _issue(report, "$.kiln.speed_ratio", "speed_ratio_out_of_bounds", "speed ratio must lie inside declared bounds")

    profile = kiln.get("profile", [])
    positions = [knot.get("s_m") for knot in profile]
    if len(profile) < 2 or any(not _finite(value) for value in positions) or any(float(a) >= float(b) for a, b in zip(positions, positions[1:])):
        _issue(report, "$.kiln.profile", "invalid_kiln_map", "kiln map requires at least two strictly increasing s_m knots")
    for index, knot in enumerate(profile):
        for key in ("gas_temperature_K", "wall_temperature_K", "oxygen_mole_fraction", "h_W_m2_K", "km_m_s", "ambient_pressure_Pa"):
            if not _finite(knot.get(key)):
                _issue(report, f"$.kiln.profile[{index}].{key}", "missing_boundary_value", "finite boundary value is required")
        oxygen = knot.get("oxygen_mole_fraction")
        if _finite(oxygen) and not 0.0 <= float(oxygen) <= 1.0:
            _issue(report, f"$.kiln.profile[{index}].oxygen_mole_fraction", "invalid_mole_fraction", "oxygen mole fraction must be in [0, 1]")
        for key in ("gas_temperature_K", "wall_temperature_K", "h_W_m2_K", "km_m_s", "ambient_pressure_Pa"):
            value = knot.get(key)
            if _finite(value) and float(value) <= 0.0:
                _issue(report, f"$.kiln.profile[{index}].{key}", "invalid_positive_value", "boundary value must be strictly positive")
    if (
        length_ok
        and len(positions) >= 2
        and all(_finite(value) for value in positions)
        and (abs(float(positions[0])) > TOLERANCE or abs(float(positions[-1]) - float(kiln["length_m"])) > TOLERANCE)
    ):
        _issue(report, "$.kiln.profile", "kiln_profile_endpoint_mismatch", "profile must start at 0 and end at kiln.length_m")

    quality = raw.get("quality_targets", {})
    if not isinstance(quality, dict):
        _issue(report, "$.quality_targets", "missing_quality_targets", "quality target object is required")
        quality = {}
    for name in ("bulk_density_kg_m3", "open_porosity", "linear_shrinkage"):
        target = quality.get(name, {})
        _ordered_bounds(report, [target.get("min"), target.get("max")] if isinstance(target, dict) else None, f"$.quality_targets.{name}")
    for name, key in (
        ("water_absorption_proxy_percent", "max"),
        ("strength_proxy_Pa", "min"),
        ("cracking_risk", "max"),
        ("bloating_risk", "max"),
        ("thermo_coverage_score", "min"),
    ):
        target = quality.get(name, {})
        _positive(report, target.get(key) if isinstance(target, dict) else None, f"$.quality_targets.{name}.{key}")

    inverse = raw.get("inverse_design", {})
    if not isinstance(inverse, dict):
        _issue(report, "$.inverse_design", "missing_inverse_design", "inverse design object is required")
        inverse = {}
    for name in (
        "sludge_dry_mass_fraction_bounds",
        "sludge_free_moisture_bounds",
        "speed_ratio_bounds",
        "sludge_true_density_kg_m3_bounds",
        "sludge_specific_heat_J_kg_K_bounds",
        "sludge_thermal_conductivity_W_m_K_bounds",
        "sludge_effective_gas_diffusivity_m2_s_bounds",
    ):
        _ordered_bounds(report, inverse.get(name), f"$.inverse_design.{name}")
    for name in ("sludge_dry_mass_fraction_bounds", "sludge_free_moisture_bounds"):
        value = inverse.get(name)
        if isinstance(value, list) and len(value) == 2 and all(_finite(item) for item in value):
            if float(value[0]) < 0.0 or float(value[1]) > 1.0:
                _issue(report, f"$.inverse_design.{name}", "bounds_out_of_range", "fraction bounds must lie in [0, 1]")
    inverse_speed = inverse.get("speed_ratio_bounds")
    if (
        speed_bounds is not None
        and isinstance(inverse_speed, list)
        and len(inverse_speed) == 2
        and all(_finite(item) for item in inverse_speed)
        and (float(inverse_speed[0]) < speed_bounds[0] or float(inverse_speed[1]) > speed_bounds[1])
    ):
        _issue(report, "$.inverse_design.speed_ratio_bounds", "inverse_bounds_exceed_kiln_bounds", "inverse speed bounds must be inside kiln speed bounds")
    failure_policy = inverse.get("robust_failure_policy")
    if failure_policy is not None:
        if not isinstance(failure_policy, dict):
            _issue(report, "$.inverse_design.robust_failure_policy", "invalid_failure_policy", "failure policy must be an object")
        else:
            maximum = failure_policy.get("maximum_failure_rate")
            if not _finite(maximum) or not 0.0 <= float(maximum) < 1.0:
                _issue(report, "$.inverse_design.robust_failure_policy.maximum_failure_rate", "invalid_failure_rate", "maximum failure rate must be finite and in [0, 1)")
            basis_text = failure_policy.get("scientific_basis")
            if not isinstance(basis_text, str) or not basis_text.strip():
                _issue(report, "$.inverse_design.robust_failure_policy.scientific_basis", "missing_scientific_basis", "a nonempty scientific basis is required for a nondefault failure policy")
    for budget_name in ("tiny", "default"):
        budget = inverse.get(budget_name, {})
        if not isinstance(budget, dict):
            _issue(report, f"$.inverse_design.{budget_name}", "missing_inverse_budget", "inverse budget object is required")
            continue
        sobol_count = _positive_count(report, budget.get("sobol_designs"), f"$.inverse_design.{budget_name}.sobol_designs", power_of_two=True)
        _positive_count(report, budget.get("l0_uncertainty_samples"), f"$.inverse_design.{budget_name}.l0_uncertainty_samples", power_of_two=True)
        shortlist = _positive_count(report, budget.get("l1_shortlist"), f"$.inverse_design.{budget_name}.l1_shortlist")
        _positive_count(report, budget.get("l1_uncertainty_samples"), f"$.inverse_design.{budget_name}.l1_uncertainty_samples", power_of_two=True)
        if sobol_count is not None and shortlist is not None and shortlist > sobol_count:
            _issue(report, f"$.inverse_design.{budget_name}.l1_shortlist", "invalid_count_relation", "L1 shortlist cannot exceed Sobol design count")
    if raw.get("environmental_thresholds") is None:
        _issue(report, "$.environmental_thresholds", "environmental_threshold_missing", "environmental status will be not_evaluated", warning=True)
    return report
