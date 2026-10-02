"""Convert explicit RH and dry-gas inputs into a wet inlet candidate.

Inputs and provenance live in the full-cycle root parameter document. This
module only performs the declared ideal-gas conversion; it does not evaluate
saturation properties, initialize a host, change root bounds or run a solver.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping


def _parameter(root: Mapping[str, Any], key: str, units: tuple[str, ...]) -> tuple[float, Mapping[str, Any]]:
    """Read a scalar from an existing read_parameters configuration."""
    item = root["parameters"][key]
    if item["unit"] not in units:
        raise ValueError(f"dimension mismatch for {key}: expected {units}, found {item['unit']!r}")
    return float(item["value"]), item


def build_humid_gas_boundary(root: Mapping[str, Any]) -> dict[str, Any]:
    """Build a candidate fragment from root['humid_gas_boundary'].

    The API accepts a root configuration already read by read_parameters.
    That contract names RH, total pressure, temperature, saturation pressure,
    every dry-species mole-fraction parameter, and an explicit output
    source/status. RH unit is '1' or '%'; pressure is 'Pa'; temperature is
    'K'; dry mole fractions use '1'. The saturation-pressure entry must name
    its temperature_parameter and reference_phase ('liquid_water' or 'ice').

    p_H2O = RH_fraction * p_sat(T, phase), x_H2O = p_H2O / P, and
    x_i_wet = (1 - x_H2O) * x_i_dry. The declared dry composition is used
    directly, with no normalization. Supersaturation is retained when the
    caller's declared ranges permit it; negative RH is outside this domain.

    The existing FullCycle inlet requires strictly positive fractions and
    closure within eps * gas-species-count. Zero components therefore raise
    ValueError here rather than being replaced by a positive seed. Existing
    target parameter ranges are copied unchanged; any range conflicts and
    input/host pressure or temperature differences accompany the candidate.
    """
    schema = root["schema"]
    contract = root["humid_gas_boundary"]
    rh_key = contract["relative_humidity_parameter"]
    pressure_key = contract["total_pressure_parameter"]
    temperature_key = contract["temperature_parameter"]
    saturation_key = contract["saturation_pressure_parameter"]
    dry_keys = contract["dry_mole_fraction_parameters"]
    output_source = contract["output_source"]
    output_status = contract["output_status"]
    sources = root["sources"]
    if output_status not in ("literature", "assumed", "measured"):
        raise ValueError("unknown parameter identity: humid_gas_boundary.output_status")

    gas_species = [
        item["id"] for item in root["species"]
        if item["phase"] == "gas"
    ]
    if "H2O" not in gas_species:
        raise ValueError("existing gas inlet must declare the H2O gas species")
    dry_species = [name for name in gas_species if name != "H2O"]
    if set(dry_keys) != set(dry_species):
        raise ValueError(
            "dry mole-fraction parameters must exactly cover the root gas "
            f"species excluding H2O: expected {dry_species}, found {list(dry_keys)}"
        )

    rh_value, rh_item = _parameter(root, rh_key, ("1", "%"))
    pressure_pa, pressure_item = _parameter(root, pressure_key, ("Pa",))
    temperature_k, temperature_item = _parameter(root, temperature_key, ("K",))
    saturation_pa, saturation_item = _parameter(root, saturation_key, ("Pa",))
    phase = saturation_item["reference_phase"]
    if phase not in ("liquid_water", "ice"):
        raise ValueError("saturation reference_phase must be 'liquid_water' or 'ice'")
    saturation_temperature_key = saturation_item["temperature_parameter"]
    if saturation_temperature_key != temperature_key:
        raise ValueError("saturation pressure and RH must reference the same temperature parameter")
    rh_fraction = rh_value / 100.0 if rh_item["unit"] == "%" else rh_value
    if rh_fraction < 0:
        raise ValueError("relative humidity must be nonnegative")
    if pressure_pa <= 0 or saturation_pa <= 0 or temperature_k <= 0:
        raise ValueError("positive total pressure, saturation pressure and absolute temperature are required")
    water_pressure_pa = rh_fraction * saturation_pa
    if not 0 <= water_pressure_pa <= pressure_pa:
        raise ValueError("RH * saturation pressure must be between zero and total pressure")

    inputs = {
        rh_key: deepcopy(rh_item),
        pressure_key: deepcopy(pressure_item),
        temperature_key: deepcopy(temperature_item),
        saturation_key: deepcopy(saturation_item),
    }
    dry = {}
    for name in dry_species:
        key = dry_keys[name]
        value, item = _parameter(root, key, ("1",))
        if value < 0:
            raise ValueError(f"dry mole fraction must be nonnegative: {name}")
        dry[name] = value
        inputs[key] = deepcopy(item)
    dry_residual = math.fsum(dry.values()) - 1.0
    # This is the host's floating-point closure convention, not an input
    # uncertainty or an adjustable scientific acceptance tolerance.
    if abs(dry_residual) > math.ulp(1.0) * len(dry_species):
        raise ValueError("dry gas mole fractions must sum to one; no normalization is applied")
    water_fraction = water_pressure_pa / pressure_pa
    wet = {
        name: water_fraction if name == "H2O" else (1.0 - water_fraction) * dry[name]
        for name in gas_species
    }
    wet_residual = math.fsum(wet.values()) - 1.0
    if any(value <= 0 for value in wet.values()):
        raise ValueError(
            "existing FullCycle inlet requires every wet mole fraction to be "
            "strictly positive; zero RH, pure vapor or zero dry components "
            "cannot be seeded or clipped by this converter"
        )
    if abs(wet_residual) > math.ulp(1.0) * len(gas_species):
        raise ValueError("positive gas inlet fractions must sum to one")

    host_pressure_pa, host_pressure_item = _parameter(root, "gas.pressure", ("Pa",))
    host_temperature_k, host_temperature_item = _parameter(root, "initial.temperature", ("K",))
    original_entries = {}
    entries = {}
    conflicts = {}
    for name, value in wet.items():
        key = "gas.inlet." + name
        _, original = _parameter(root, key, ("1",))
        original_entries[key] = deepcopy(original)
        candidate = deepcopy(original)
        candidate.update({
            "value": value,
            "source": output_source,
            "status": output_status,
            "note": "Wet mole fraction derived from explicit RH, saturation pressure, "
                    "total pressure and dry mole fractions; see humid_gas_boundary_provenance.",
        })
        entries[key] = candidate
        lower, upper = candidate["range"]
        if value < lower or value > upper:
            conflicts[key] = {"candidate_value": value, "unchanged_declared_range": deepcopy(candidate["range"])}
    source_ids = {item["source"] for item in inputs.values()}
    source_ids.update(item["source"] for item in original_entries.values())
    source_ids.update((output_source, host_pressure_item["source"], host_temperature_item["source"]))
    provenance = {
        "contract": deepcopy(contract),
        "input_parameters": inputs,
        "input_and_original_target_sources": {
            key: deepcopy(sources[key]) for key in sorted(source_ids)
        },
        "original_inlet_parameters": original_entries,
        "reference_phase": phase,
        "temperature_K": temperature_k,
        "relative_humidity_fraction": rh_fraction,
        "total_pressure_Pa": pressure_pa,
        "saturation_pressure_Pa": saturation_pa,
        "water_partial_pressure_Pa": water_pressure_pa,
        "dry_mole_fractions": dry,
        "wet_mole_fractions": wet,
        "dry_simplex_signed_residual": dry_residual,
        "wet_simplex_signed_residual": wet_residual,
        "supersaturated_with_respect_to_reference_phase": rh_fraction > 1.0,
        "relations": [
            "RH_fraction = RH_percent / 100 when unit is %",
            "p_H2O = RH_fraction * p_sat(T, declared reference phase)",
            "x_H2O_wet = p_H2O / total_pressure",
            "x_i_wet = (1 - x_H2O_wet) * x_i_dry",
        ],
        "physical_model": "Declared ideal-gas partial-pressure conversion; caller supplies saturation pressure. "
                          "No saturation correlation, enhancement factor, fugacity correction or measured input is inferred.",
        "measurement_claim": "Source and status are caller declarations; this conversion adds no measurements or kinetic evidence.",
    }
    return {
        "input_root_schema": schema,
        "candidate_root_fragment": {
            "parameters": entries,
            "sources": {output_source: deepcopy(sources[output_source])},
            "humid_gas_boundary_provenance": provenance,
        },
        "integration_context": {
            "declared_range_conflicts": conflicts,
            "host_pressure_parameter": deepcopy(host_pressure_item),
            "host_initial_temperature_parameter": deepcopy(host_temperature_item),
            "input_pressure_matches_host": pressure_pa == host_pressure_pa,
            "input_temperature_matches_host_initial": temperature_k == host_temperature_k,
            "gas_program_scale_parameter": deepcopy(root["parameters"]["gas.program_scale"]),
            "stages": deepcopy(root["stages"]),
            "stage_composition_parameter_names": [
                key for key in root["parameters"] if key.startswith("gas.stage.")
            ],
            "scope": "Candidate changes only gas.inlet.*. The finite-gas host uses gas.pressure and "
                     "initial.temperature for initial inventory, and separate stage compositions/program scale "
                     "for later boundary knots. Root ranges, temperature, pressure and stage program require "
                     "an explicit integration decision; no host initialization or scientific qualification was performed.",
        },
    }
