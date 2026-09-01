from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

from ..config import sha256_json
from ..types import CaseConfig


def design_from_unit(base: CaseConfig, point: np.ndarray, design_id: int) -> tuple[CaseConfig, dict[str, float]]:
    if len(point) < 8 or np.any((point < 0.0) | (point > 1.0)):
        raise ValueError("design point must contain at least eight unit-cube coordinates")
    raw = copy.deepcopy(base.raw)
    bounds = raw["inverse_design"]
    sludge_low, sludge_high = bounds["sludge_dry_mass_fraction_bounds"]
    sludge_fraction = sludge_low + float(point[0]) * (sludge_high - sludge_low)
    matrix_total = 1.0 - sludge_fraction
    matrix_reference = float(base.raw["feedstocks"]["shale"]["dry_mass_fraction"]) + float(base.raw["feedstocks"]["coal_gangue"]["dry_mass_fraction"])
    raw["feedstocks"]["shale"]["dry_mass_fraction"] = matrix_total * float(base.raw["feedstocks"]["shale"]["dry_mass_fraction"]) / matrix_reference
    raw["feedstocks"]["coal_gangue"]["dry_mass_fraction"] = matrix_total * float(base.raw["feedstocks"]["coal_gangue"]["dry_mass_fraction"]) / matrix_reference
    raw["feedstocks"]["sludge"]["dry_mass_fraction"] = sludge_fraction

    organic = 0.12 + 0.23 * float(point[1])
    calcite = 0.04 + 0.14 * float(point[2])
    amorphous = 0.12 + 0.23 * float(point[3])
    remaining = 1.0 - organic - calcite - amorphous
    components = {item["id"]: item for item in raw["feedstocks"]["sludge"]["components"]}
    components["organic_pseudo_A"]["fraction"] = organic
    components["calcite"]["fraction"] = calcite
    components["amorphous_oxide_pool"]["fraction"] = amorphous
    for name, share in {"quartz": 0.30, "kaolinite": 0.30, "illite_pseudo": 0.25, "hematite": 0.15}.items():
        components[name]["fraction"] = remaining * share

    d50 = math.exp(math.log(10e-6) + float(point[4]) * (math.log(120e-6) - math.log(10e-6)))
    raw["feedstocks"]["sludge"]["particle_size_distribution"] = {"d10_m": 0.2 * d50, "d50_m": d50, "d90_m": 5.0 * d50}
    sphericity = 0.40 + 0.55 * float(point[5])
    raw["feedstocks"]["sludge"]["morphology"] = {"sphericity": sphericity, "aspect_ratio": 1.0 + 4.0 * (1.0 - sphericity)}
    moisture_low, moisture_high = bounds["sludge_free_moisture_bounds"]
    moisture = moisture_low + float(point[6]) * (moisture_high - moisture_low)
    raw["feedstocks"]["sludge"]["free_moisture_wet_basis"] = moisture
    speed_low, speed_high = bounds["speed_ratio_bounds"]
    speed = speed_low + float(point[7]) * (speed_high - speed_low)
    raw["kiln"]["speed_ratio"] = speed
    raw["case_id"] = f"inverse_design_{design_id:04d}"
    decision = {
        "sludge_dry_mass_fraction": sludge_fraction,
        "sludge_organic_fraction": organic,
        "sludge_calcite_fraction": calcite,
        "sludge_amorphous_fraction": amorphous,
        "sludge_d50_m": d50,
        "sludge_sphericity": sphericity,
        "sludge_free_moisture_wet_basis": moisture,
        "speed_ratio": speed,
    }
    return CaseConfig(raw, base.source_path, sha256_json(raw)), decision
