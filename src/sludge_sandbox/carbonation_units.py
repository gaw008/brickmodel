#!/usr/bin/env python3
"""Offline source-preserving carbonation units CLI and importable API.

F evidence conversion uses the standard library and the supplied JSON/CSV.
P38 mapping delegates to the existing source_tg API before adding unit views.
No fixture, external snapshot, network, host evaluation or mobility estimate.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import json
import math
from pathlib import Path
import sys
from typing import Mapping

__all__ = ["convert_record", "normalize_f_evidence", "load_f_evidence", "map_p38_record"]


class MissingNormalization(ValueError):
    """A required normalization quantity was not supplied explicitly."""


def _number(value: float | None, name: str) -> float:
    if value is None:
        raise MissingNormalization(f"Missing explicit {name}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


# Mathematical unit definitions, not material/process parameters. Each entry is
# (scale, offset, target unit); mass-basis changes are not hidden in this table.
_UNIT_RULES = {
    "time": {"s": (1, 0, "s"), "min": (60, 0, "s"), "h": (3600, 0, "s"), "d": (86400, 0, "s")},
    "temperature": {"degC": (1, 273.15, "K"), "K": (1, 0, "K")},
    "fraction": {"1": (1, 0, "1"), "percent": (0.01, 0, "1"), "vol_percent": (0.01, 0, "1"), "ppmv": (1e-6, 0, "1")},
    "specific_area": {"m2/g": (1000, 0, "m2/kg"), "m2/kg": (1, 0, "m2/kg")},
    "density": {"g/cm3": (1000, 0, "kg/m3"), "kg/m3": (1, 0, "kg/m3")},
    "specific_pore_volume": {"cm3/g": (1e-3, 0, "m3/kg"), "m3/kg": (1, 0, "m3/kg")},
    "length": {"um": (1e-6, 0, "m"), "mm": (1e-3, 0, "m"), "m": (1, 0, "m")},
    "pressure": {"Pa": (1, 0, "Pa"), "kPa": (1000, 0, "Pa")},
    "mass": {"mg": (1e-6, 0, "kg"), "g": (1e-3, 0, "kg"), "kg": (1, 0, "kg")},
    "molar_mass": {"g/mol": (1e-3, 0, "kg/mol"), "kg/mol": (1, 0, "kg/mol")},
    "mass_ratio": {"g/g": (1, 0, "kg/kg"), "kg/kg": (1, 0, "kg/kg")},
    "CH_per_dry_reference": {"g_CH/100g_dry_reference": (0.01, 0, "kg_CH/kg_dry_reference")},
}


def _unit_rule(unit: str, quantity: str) -> tuple[float, float, str]:
    if quantity not in _UNIT_RULES or unit not in _UNIT_RULES[quantity]:
        raise ValueError(f"Unsupported {quantity} unit: {unit}")
    return _UNIT_RULES[quantity][unit]


def _convert(value: float, unit: str, quantity: str) -> float:
    """Convert explicit units; retain signs and do not infer a new mass basis."""
    value = _number(value, quantity)
    scale, offset, _ = _unit_rule(unit, quantity)
    result = value * scale
    return _number(result + offset if offset else result, f"converted {quantity}")


def _partial_pressure_pa(*, gas_fraction: float, total_pressure_pa: float | None) -> float:
    """Boundary pressure only; a chamber value is not an internal pore pressure."""
    pressure = _number(total_pressure_pa, "total_pressure_pa")
    fraction = _number(gas_fraction, "gas_fraction")
    if pressure <= 0 or not 0 <= fraction <= 1:
        raise ValueError("Pressure must be positive and gas fraction in [0,1]")
    return fraction * pressure


def _known(value: object, label: str) -> str:
    if not isinstance(value, str) or value.strip().lower() in {"", "unknown", "pending", "template"}:
        raise ValueError(f"{label}: explicit known declaration required")
    return value


def _unit_view(value, unit, quantity, *, source_id, locator, basis, domain) -> dict:
    """One unit operation and its declarations; missing source values stay null."""
    scale, offset, target = _unit_rule(unit, quantity)
    return {
        "value": None if value is None else _convert(value, unit, quantity),
        "unit": target,
        "conversion": {
            "input_value": value, "input_unit": unit, "quantity": quantity,
            "scale": scale, "offset": offset, "formula": "value * scale + offset",
            "source_id": source_id, "source_locator": locator,
            "basis": deepcopy(basis), "domain": deepcopy(domain),
            "value_status": "not_supplied" if value is None else "unit_converted",
        },
    }


def convert_record(record: Mapping[str, object]) -> dict:
    """Map one sourced numeric unit record, preserving original basis/domain.

    Required fields: value, unit, quantity, source_id, source_locator, basis,
    domain. domain.source_id must match; domain.identity must be declared.
    This is unit arithmetic, not physical/material or mobility admission.
    """
    source = _known(record["source_id"], "source_id")
    locator = _known(record["source_locator"], "source_locator")
    basis = _known(record["basis"], "basis")
    domain = record["domain"]
    _known(domain["identity"], "domain.identity")
    if domain["source_id"] != source:
        raise ValueError("domain.source_id differs from unit record source_id")
    # Single-value input is numeric; absence is allowed only in source datasets.
    value = _number(record["value"], "value")
    return {
        "schema": "carbonation_sourced_unit_record_v1", "original_input": deepcopy(record),
        "converted": _unit_view(value, record["unit"], record["quantity"],
                                source_id=source, locator=locator, basis=basis, domain=domain),
        "admission": {"purpose": "unit_mapping", "material_validation": False,
                      "canonical_fit_observation": False, "mobility_admitted": False},
    }


def _condition_view(condition: Mapping[str, object]) -> dict:
    source = _known(condition["source_id"], "condition.source_id")
    identity = _known(condition["id"], "condition.id")
    locator = _known(condition["source_locator"], "condition.source_locator")
    area = condition["specific_area"]
    basis = _known(area["basis_id"], "specific_area.basis_id")
    _known(area["basis"], "specific_area.basis")
    domain = {"source_id": source, "identity": identity, "material_basis_id": basis}

    def view(value, unit, quantity, mass_basis):
        return _unit_view(value, unit, quantity, source_id=source, locator=locator,
                          basis=mass_basis, domain=domain)

    temperature = view(condition["temperature"]["value"], condition["temperature"]["unit"],
                       "temperature", "source experimental temperature")
    gas = condition["co2_boundary"]
    co2 = view(gas["value"], gas["unit"], "fraction", "CO2 volume fraction at declared external boundary")
    area_si = view(area["value"], area["unit"], "specific_area", basis)
    if temperature["value"] is not None and temperature["value"] <= 0:
        raise ValueError(f"{identity}: source temperature must be positive in K")
    if co2["value"] is not None and not 0 <= co2["value"] <= 1:
        raise ValueError(f"{identity}: source CO2 fraction outside [0,1]")
    if area_si["value"] is not None and area_si["value"] < 0:
        raise ValueError(f"{identity}: source specific area must be nonnegative")
    pressure = None
    if gas["total_pressure_pa"] is not None and co2["value"] is not None:
        pressure = _partial_pressure_pa(gas_fraction=co2["value"], total_pressure_pa=gas["total_pressure_pa"])
    pressure_view = {
        "value": pressure, "unit": "Pa",
        "conversion": {"formula": "CO2 fraction * explicit total boundary pressure",
                       "input_fraction": co2["value"], "total_pressure_pa": gas["total_pressure_pa"],
                       "source_id": source, "source_locator": locator, "domain": deepcopy(domain),
                       "basis": "declared external gas boundary",
                       "scope": deepcopy(gas["scope"]),
                       "value_status": "not_supplied" if pressure is None else "unit_derived"},
    }
    humidity = condition["RH"]
    humidity_view = {"original": deepcopy(humidity), "components": {}}
    if "history" in humidity:
        humidity_view["history"] = []
        for step in humidity["history"]:
            rh = view(step["percent"], "percent", "fraction", "source relative humidity")
            if not 0 <= rh["value"] <= 1:
                raise ValueError(f"{identity}: source RH outside [0,1]")
            humidity_view["history"].append({
                "original": deepcopy(step), "RH": rh,
                "duration": view(step["duration_days"], "d", "time", "elapsed source exposure duration"),
            })
    else:
        for key in ("value", "lower", "upper"):
            if key in humidity:
                rh = view(humidity[key], humidity["unit"], "fraction", "source relative humidity")
                if rh["value"] is not None and not 0 <= rh["value"] <= 1:
                    raise ValueError(f"{identity}: source RH outside [0,1]")
                humidity_view["components"][key] = rh
    return {"id": identity, "source_id": source, "original": deepcopy(condition),
            "domain": domain, "temperature": temperature, "CO2_fraction": co2,
            "CO2_boundary_pressure": pressure_view, "specific_area": area_si,
            "RH": humidity_view, "mobility_admitted": False}


def normalize_f_evidence(evidence: Mapping, observations: list[Mapping]) -> dict:
    """Convert current F fields without changing relations or admitting rates.

    Uses only the supplied evidence object and CSV rows; downloads, snapshots
    and historical fixture/verification files are never accessed.
    """
    if evidence["schema"] != "direct_carbonation_workpackage_f_v1":
        raise ValueError("Unsupported evidence schema")
    source_limit = evidence["source_count_limit"]
    if isinstance(source_limit, bool) or not isinstance(source_limit, int) or source_limit <= 0:
        raise ValueError("source_count_limit must declare a positive integer")
    sources = {s["id"]: s for s in evidence["sources"]}
    if len(sources) != len(evidence["sources"]) or len(sources) > source_limit:
        raise ValueError("Duplicate source ids or exceeded declared source cap")
    for source in sources.values():
        _known(source["id"], "source.id")
    conditions = {c["id"]: c for c in evidence["conditions"]}
    if len(conditions) != len(evidence["conditions"]):
        raise ValueError("Duplicate condition ids")
    converted_conditions = []
    for condition in conditions.values():
        if condition["source_id"] not in sources or condition["mobility_admitted"] is not False:
            raise ValueError("Invalid source or unauthorized mobility admission")
        converted_conditions.append(_condition_view(condition))
    ids = set()
    converted_observations = []
    for row in observations:
        _known(row["id"], "observation.id")
        if row["id"] in ids or row["condition_id"] not in conditions:
            raise ValueError("Duplicate observation or unknown condition")
        ids.add(row["id"])
        condition = conditions[row["condition_id"]]
        if row["source_id"] != condition["source_id"]:
            raise ValueError("Source/condition mismatch")
        if row["mobility_admitted"] != "false":
            raise ValueError("Observation must not admit mobility")
        if row["extraction_method"] == "manual_primary_plot":
            if not row["reading_error"] or not row["time_value"] or row["value_unit"] != "1":
                raise ValueError("Plot reading must declare reading error, time and conversion unit")
        if row["time_relation"] not in {"selected_plot_time", "reported_time", "before", "window", "not_paired"}:
            raise ValueError("Unknown time relation")
        if row["observed_relation"] not in {"approx", "range", "greater_than", "less_equal", "qualitative", "reported_uncertainty"}:
            raise ValueError("Unknown observation relation")
        source = _known(row["source_id"], "observation.source_id")
        locator = _known(row["locator"], "observation.locator")
        basis = _known(row["observable"], "observation.observable")
        domain = {"source_id": source, "identity": row["condition_id"],
                  "condition_material_basis_id": condition["specific_area"]["basis_id"],
                  "observation_basis": basis, "history_or_basis": row["history_or_basis"]}

        def field(key, unit, quantity, field_basis):
            value = None if row[key] == "" else _number(float(row[key]), key)
            return _unit_view(value, unit, quantity, source_id=source, locator=locator,
                              basis=field_basis, domain=domain)

        time_fields = {key: field(key, row["time_unit"], "time", "source-reported exposure time; history retained in original row")
                       for key in ("time_value", "time_lower", "time_upper")}
        value_fields = {}
        if row["value_unit"] in {"1", "g_CH/100g_dry_reference"}:
            quantity = "fraction" if row["value_unit"] == "1" else "CH_per_dry_reference"
            value_fields = {key: field(key, row["value_unit"], quantity, basis)
                            for key in ("observed_value", "observed_lower", "observed_upper", "reading_error")}
        elif row["value_unit"] != "qualitative":
            raise ValueError(f"Unsupported source observation unit: {row['value_unit']}")
        else:
            # Numeric content on a declared qualitative row is checked but
            # never turned into a fractional endpoint.
            for key in ("observed_value", "observed_lower", "observed_upper", "reading_error"):
                if row[key]:
                    _number(float(row[key]), key)
        converted_observations.append({
            "id": row["id"], "source_id": source, "condition_id": row["condition_id"],
            "original": deepcopy(row), "basis": basis, "domain": domain,
            "time_relation": row["time_relation"], "observed_relation": row["observed_relation"],
            "time_fields": time_fields, "value_fields": value_fields,
            "extraction_method": row["extraction_method"],
            "reading_error_meaning": "Preserved source/analyst meaning; scaled units only, no uncertainty propagation",
            "exact_rate_endpoint_admitted": False, "mobility_admitted": False,
        })
    return {
        "schema": "direct_carbonation_f_unit_view_v1", "operation": "source_unit_mapping",
        "original_evidence": deepcopy(evidence), "conditions": converted_conditions,
        "observations": converted_observations,
        "source_count": len(sources), "condition_count": len(conditions),
        "observation_count": len(observations),
        "admission": {"purpose": "source_reference_units", "material_validation": False,
                      "canonical_fit_observation": False, "mobility_admitted": False},
    }


def load_f_evidence(evidence_path: Path | str) -> dict:
    """Read only the supplied manifest and its adjacent declared CSV."""
    path = Path(evidence_path)
    evidence = json.loads(path.read_text(encoding="utf-8"))
    csv_path = path.parent / evidence["observations_file"]
    with csv_path.open(newline="", encoding="utf-8") as stream:
        observations = list(csv.DictReader(stream))
    result = normalize_f_evidence(evidence, observations)
    result["input_files"] = {"evidence": str(path), "observations": str(csv_path)}
    return result


def map_p38_record(*, config: dict, record: dict) -> dict:
    """Delegate unchanged input to P38, then attach unit-only provenance views.

    No pre-conversion, added admission option, new TG separation or guessed
    denominator. Legacy errors propagate; legacy result/admission is retained.
    Only this entry imports source_tg; F/convert CLI needs no project imports.
    """
    from sludge_vme.inverse.source_tg import map_saeki2026_tg

    mapped = map_saeki2026_tg(config=config, record=record)
    original = mapped["original_input"]
    source = original["source_id"]
    denominator = original["denominator"]
    domain = {"source_id": source, "identity": original["sample"]["id"],
              "sample_basis": original["sample"]["basis"], "time_id": original["time"]["id"],
              "denominator_id": denominator["id"],
              "applicability": deepcopy(mapped["admission"]["applicability"])}
    phases = {}
    for name in mapped["formula_contract"]["phase_order"]:
        item = original["phase_masses"][name]
        phases[name] = _unit_view(item["value"], item["unit"], "mass_ratio",
                                 source_id=source, locator=item["source_locator"],
                                 basis=denominator["basis"], domain=domain)
    molar_masses = {}
    formula_source = mapped["formula_contract"]["formula_source_id"]
    constant_domain = {"source_id": formula_source, "identity": formula_source,
                       "applies_to_record_source_id": source,
                       "sample_id": original["sample"]["id"]}
    for name, item in mapped["source_molar_masses"].items():
        molar_masses[name] = {
            "original_parameter": deepcopy(item),
            "SI": _unit_view(item["value"], item["unit"], "molar_mass",
                             source_id=formula_source, locator=mapped["source_formula"]["locator"],
                             basis=f"molar mass of {name}", domain=constant_domain),
        }
    time = original["time"]
    return {
        "schema": "direct_carbonation_p38_unit_view_v1", "operation": "P38_source_mapping_with_unit_view",
        "P38_mapping": mapped, "original_input": deepcopy(original), "domain": domain,
        "phase_mass_ratios_SI": phases, "source_molar_masses_SI": molar_masses,
        "elapsed_time_SI": {"value": mapped["time"]["elapsed_s"], "unit": "s",
                            "original": deepcopy(time), "source_id": source,
                            "source_locator": time["source_locator"],
                            "basis": {"origin": time["origin"], "meaning": mapped["time"]["meaning"]},
                            "domain": deepcopy(domain),
                            "conversion": "Existing P38 source-time convert to s; source origin is retained"},
        "admission": deepcopy(mapped["admission"]), "mobility_admitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    evidence_command = commands.add_parser("f-data", help="Export the current F JSON/CSV with sourced SI views")
    evidence_command.add_argument("--evidence", type=Path, required=True)
    evidence_command.add_argument("--output", type=Path)
    unit_command = commands.add_parser("convert-record", help="Convert one numeric JSON record with explicit source/basis/domain")
    unit_command.add_argument("--input", type=Path, required=True)
    unit_command.add_argument("--output", type=Path)
    p38_command = commands.add_parser("p38", help="Map one record through existing P38 before adding SI views")
    p38_command.add_argument("--project-root", type=Path, required=True)
    p38_command.add_argument("--config", type=Path, required=True)
    p38_command.add_argument("--record", type=Path, required=True)
    p38_command.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "f-data":
        result = load_f_evidence(args.evidence)
    elif args.command == "convert-record":
        result = convert_record(json.loads(args.input.read_text(encoding="utf-8")))
    else:
        source_file = (args.project_root / "src/sludge_vme/inverse/source_tg.py").resolve(strict=True)
        sys.path.insert(0, str(source_file.parents[2]))
        config = json.loads(args.config.read_text(encoding="utf-8"))
        record = json.loads(args.record.read_text(encoding="utf-8"))
        result = map_p38_record(config=config, record=record)
    output = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output is None:
        sys.stdout.write(output)
    else:
        args.output.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
