"""Reproduce conservative readable Figure8 temperature markers; never fit/interpolate.

Requires pypdf, Pillow, numpy. The original licensed PDF stays in ignored cache.
Coordinates refer to the native 1303x1050 embedded raster, with top-left origin.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import platform
from collections import deque
from importlib.metadata import version
from pathlib import Path
from typing import TypedDict

import numpy as np
from numpy.typing import NDArray
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


class Component(TypedDict):
    area: int
    bbox_px: list[int]
    center_px: list[float]


def components(mask: NDArray[np.bool_]) -> list[Component]:
    """Eight-connected components of a fresh boolean mask; no interpolation."""
    pending = mask.copy()
    result = []
    for y, x in zip(*np.nonzero(pending)):
        if not pending[y, x]:
            continue
        pending[y, x] = False
        queue = deque([(int(y), int(x))])
        points = []
        while queue:
            cy, cx = queue.popleft()
            points.append((cx, cy))
            for dy, dx in itertools.product((-1, 0, 1), repeat=2):
                ny, nx = cy + dy, cx + dx
                if (dy or dx) and 0 <= ny < pending.shape[0] and 0 <= nx < pending.shape[1] and pending[ny, nx]:
                    pending[ny, nx] = False
                    queue.append((ny, nx))
        if len(points) >= 5:
            coordinates = np.array(points)
            low, high = coordinates.min(axis=0), coordinates.max(axis=0)
            result.append({"area": len(points), "bbox_px": [int(low[0]), int(low[1]), int(high[0]), int(high[1])],
                           "center_px": [float(v) for v in (low + high) / 2]})
    return sorted(result, key=lambda item: item["center_px"][0])


def calibrated_interval(
    pixel: float, readout: float, p0: float, p1: float,
    v0: float, v1: float, axis_readout: float,
) -> tuple[float, float, float]:
    value = v0 + (pixel - p0) * (v1 - v0) / (p1 - p0)
    possibilities = [v0 + (p - a) * (v1 - v0) / (b - a)
                     for p, a, b in itertools.product((pixel-readout, pixel+readout),
                                                      (p0-axis_readout, p0+axis_readout),
                                                      (p1-axis_readout, p1+axis_readout))]
    return value, min(possibilities), max(possibilities)


def main() -> None:
    metadata_bytes = (HERE.parent / "source.json").read_bytes()
    metadata = json.loads(metadata_bytes)
    selection = json.loads((HERE / "selection.json").read_text())
    calibration = selection["calibration"]
    expected_calibration = {
        "time_px": [133, 1125], "temperature_px": [843, 49],
        "time_values_min": [0, 160], "temperature_values_degC": [0, 140],
        "axis_readout_halfwidth_px": 1,
        "time_check_ticks_px": [257, 381, 505, 629, 753, 877, 1001],
        "temperature_check_ticks_px": [729, 616, 503, 389, 276, 163],
    }
    if calibration != expected_calibration:
        raise ValueError("Axis calibration differs from the reviewed Figure8 settings")
    pdf_path = ROOT / metadata["asset"]["path"]
    pdf_bytes = pdf_path.read_bytes()
    if hashlib.sha256(pdf_bytes).hexdigest() != metadata["asset"]["sha256"]:
        raise ValueError("Source PDF hash differs from the registered asset")
    reader = PdfReader(pdf_path)
    images = [image for image in reader.pages[9].images if image.name == "I16.jpg"]
    if len(images) != 1 or images[0].image.size != (1303, 1050):
        raise ValueError("Original Figure8 embedded raster identity changed")
    native = images[0]
    if hashlib.sha256(native.data).hexdigest() != selection["native_image_sha256"]:
        raise ValueError("Embedded raster bytes differ from reviewed selection")
    rgb = np.array(native.image.convert("RGB"), dtype=float)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    masks = {
        "red": (red > 150) & (green < 125) & (blue < 125),
        "blue": (blue > 130) & (red < 110) & (green < 150),
        "green": (green > 100) & (green > red + 25) & (green > blue + 10) & (red < 120),
        "gray": (rgb.max(axis=2) - rgb.min(axis=2) < 15) & (red < 140),
    }
    audit, observations = {}, []
    conditions = {item["run"]: item for item in metadata["conditions"]}
    for color, mask in masks.items():
        # Erode by a5x5 square to remove hollow-marker outlines and narrow bars.
        core = mask.copy()
        for dy, dx in itertools.product(range(-2, 3), repeat=2):
            core &= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
        core[:25] = core[840:] = False
        core[:, :137] = core[:, 1120:] = False
        found = components(core)
        chosen = selection["series"][color]
        used = set()
        centers = []
        for anchor in chosen["reviewed_core_anchors_px"]:
            matches = [(index, item) for index, item in enumerate(found)
                       if max(abs(item["center_px"][i] - anchor[i]) for i in (0, 1)) <= 2]
            if len(matches) != 1 or matches[0][0] in used:
                raise ValueError(f"Reviewed anchor is not a unique core: {color}, {anchor}")
            index, item = matches[0]
            used.add(index)
            centers.append((item["center_px"], "reviewed_isolated_eroded_core"))
        centers += [(entry["center_px"], "manual_review_overlap") for entry in chosen["manual_centers"]]
        centers.sort(key=lambda item: item[0][0])
        audit[color] = {"components": found, "selected_component_indices": sorted(used),
                        "manual_centers": chosen["manual_centers"]}
        condition = conditions[chosen["run"]]
        expected = {"gray": (1, "MSJ", 2), "red": (6, "MSJ", 4),
                    "blue": (7, "CB", 2), "green": (10, "CB", 4)}[color]
        if ((chosen["run"], condition["material_id"], condition["diameter_cm"]) != expected
                or condition["gas_temperature_degC"] != 138
                or condition["gas_velocity_m_s"] != 2.4):
            raise ValueError(f"Source condition differs from the Figure8 legend: {color}")
        for index, (center, method) in enumerate(centers, 1):
            x, y = center
            halfwidth = chosen["center_readout_halfwidth_px"]
            t, tlo, thi = calibrated_interval(x, halfwidth, *calibration["time_px"], 0, 160, 1)
            temp, lower, upper = calibrated_interval(y, halfwidth, *calibration["temperature_px"], 0, 140, 1)
            observations.append({"selection_id": f"figure8-{color}-{index:03d}",
                "source_id": metadata["id"], "figure": 8, "article_page": 2052,
                "run": chosen["run"], "material_id": condition["material_id"],
                "diameter_cm": condition["diameter_cm"], "gas_temperature_degC": 138,
                "gas_velocity_m_s": 2.4, "quantity": "internal_temperature_degC",
                "role": "development", "x_px": x, "y_px": y,
                "x_readout_halfwidth_px": halfwidth, "y_readout_halfwidth_px": halfwidth,
                "axis_readout_halfwidth_px": 1, "time_min": t, "time_s": 60*t,
                "time_readout_lower_s": 60*tlo, "time_readout_upper_s": 60*thi,
                "time_readout_bound_s": 60*max(t-tlo, thi-t), "value_degC": temp,
                "temperature_readout_lower_degC": lower, "temperature_readout_upper_degC": upper,
                "temperature_readout_bound_degC": max(temp-lower, upper-temp),
                "plotted_sd_degC": None, "selection_method": method})
    # Stable readable decimals; pixel and temperature uncertainties remain explicit.
    with (HERE / "observations.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(observations[0]))
        writer.writeheader()
        for row in observations:
            writer.writerow({key: round(value, 9) if isinstance(value, float) else value for key, value in row.items()})
    (HERE / "extraction_audit.json").write_text(json.dumps({"pdf_sha256": metadata["asset"]["sha256"],
        "source_metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "native_image_sha256": selection["native_image_sha256"], "native_image_size": [1303, 1050],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "runtime": {"python": platform.python_version(), "numpy": version("numpy"),
                    "pypdf": version("pypdf"), "Pillow": version("Pillow")},
        "selection_sha256": hashlib.sha256((HERE / "selection.json").read_bytes()).hexdigest(),
        "point_count": len(observations), "readout_is_not_experimental_uncertainty": True,
        "coverage": "partial_readable_markers_only", "component_audit": audit}, indent=2) + "\n")
    print(json.dumps({"point_count": len(observations), "counts": {color: len(selection["series"][color]["reviewed_core_anchors_px"]) + len(selection["series"][color]["manual_centers"]) for color in masks}}))


if __name__ == "__main__":
    main()
