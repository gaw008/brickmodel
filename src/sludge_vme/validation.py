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
        moisture = feed.get("free_moisture_wet_basis")
        if not _finite(moisture) or not 0.0 <= float(moisture) < 1.0:
            _issue(report, f"{prefix}.free_moisture_wet_basis", "invalid_moisture", "wet-basis moisture must be in [0, 1)")
        if isinstance(feed.get("source"), dict) and feed["source"].get("kind"):
            sourced += 1

    report.source_coverage = sourced / max(len(feeds), 1)
    profile = raw.get("kiln", {}).get("profile", [])
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
    if raw.get("environmental_thresholds") is None:
        _issue(report, "$.environmental_thresholds", "environmental_threshold_missing", "environmental status will be not_evaluated", warning=True)
    return report
