"""Read twelve raster anchors; no curve fit, integration, or material model."""

from __future__ import annotations

import argparse
from fractions import Fraction as F
from hashlib import sha256
from itertools import combinations
from io import BytesIO
import json
from math import ceil, floor
from pathlib import Path

from PIL import Image, __version__ as pillow_version


BASE = Path(__file__).resolve().parent.parent
LABEL_RADIUS = F(2)
CURVE_RADIUS = F(3, 2)
PANELS = {
    "TG": {
        "file": "figure3-000.png",
        "sha256": "112af34fd17a14abaa6c1069d8cd88af1581d276164670f92bfc86791c27a613",
        "size": (760, 470),
        "roi": (100, 610, 80, 375),
        "x_labels": [(25, "101"), (225, "217"), (425, "332.5"), (625, "450.5"), (825, "566.5")],
        "y_labels": [(100, "85.5"), (80, "143.5"), (60, "201.5"), (40, "259"), (20, "316.5"), (0, "375")],
        "targets": [100, 225, 319, 421, 590, 825],
        "unit": "wt_percent_of_initial_TG_sample",
    },
    "DSC": {
        "file": "figure3-001.jpg",
        "sha256": "6da1e51045b44daf30e44bd9ccadad3a46a414b6580f399e2cd583d9b4982231",
        "size": (977, 638),
        "roi": (190, 929, 65, 512),
        "x_labels": [(0, "134.5"), (100, "267"), (200, "399"), (300, "529.5"), (400, "661.5"), (500, "793.5"), (600, "926")],
        "y_labels": [("0.1", "39"), (0, "106"), ("-0.1", "172"), ("-0.2", "239"), ("-0.3", "305"), ("-0.4", "372"), ("-0.5", "438"), ("-0.6", "505")],
        "targets": [100, 200, 300, 400, 500, 575],
        "unit": "W_per_g_initial_DSC_sample_plot_endo_down",
    },
}


def calibration(labels: list[tuple[object, str]]) -> list[tuple[F, F]]:
    """Vertices of pixel=a*physical+b satisfying every label-center box."""
    constraints = [(F(v), F(p) - LABEL_RADIUS, F(p) + LABEL_RADIUS) for v, p in labels]
    lines = [(v, bound) for v, low, high in constraints for bound in (low, high)]
    vertices = set()
    for (v1, p1), (v2, p2) in combinations(lines, 2):
        if v1 == v2:
            continue
        a = (p1 - p2) / (v1 - v2)
        b = p1 - a * v1
        if all(low <= a * v + b <= high for v, low, high in constraints):
            vertices.add((a, b))
    if not vertices:
        raise ValueError("No affine calibration satisfies all label boxes")
    result = sorted(vertices)
    if any(a == 0 for a, _ in result):
        raise ValueError("Degenerate calibration")
    return result


def nominal(vertices: list[tuple[F, F]]) -> tuple[F, F]:
    """Barycenter is a declared nominal convention, not an axis best fit."""
    return tuple(sum(v[i] for v in vertices) / len(vertices) for i in (0, 1))


def selected(panel: str, rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    if panel == "TG":
        return g - r >= 25 and g - b >= 25 and g <= 235
    # Orange JPEG fringes around black labels have markedly unequal G/B.
    return r - g >= 45 and r - b >= 45 and abs(g - b) <= 40


def read_anchor(panel: str, cfg: dict, image: Image.Image, xcal: list, ycal: list, target: int) -> dict:
    target_f = F(target)
    xposs = [a * target_f + b for a, b in xcal]
    xlow, xhigh = min(xposs), max(xposs)
    # A pixel whose closed half-pixel footprint intersects a feasible x location.
    columns = list(range(ceil(xlow - F(1, 2)), floor(xhigh + F(1, 2)) + 1))
    left, right, top, bottom = cfg["roi"]
    pixels = []
    by_column = {}
    for x in columns:
        ys = []
        if left <= x <= right:
            for y in range(top, bottom + 1):
                rgb = image.getpixel((x, y))
                if selected(panel, rgb):
                    ys.append(y)
                    pixels.append([x, y, list(rgb)])
        by_column[x] = ys
    row = {
        "panel": panel,
        "target_temperature_C": target,
        "value_unit": cfg["unit"],
        "joint_TG_DSC_temperature_overlap": 50 <= target <= 600,
        "feasible_x_pixel_center_range": [str(xlow), str(xhigh)],
        "inspected_columns": columns,
        "actual_selected_RGB_pixels": pixels,
        "experimental_uncertainty": None,
    }
    if any(not ys for ys in by_column.values()):
        return {**row, "status": "unknown", "reason": "At least one feasible column has no selected curve pixel"}
    if any(any(b - a > 2 for a, b in zip(ys, ys[1:])) for ys in by_column.values()):
        return {**row, "status": "unknown", "reason": "Multiple separated color branches in a feasible column"}
    raw_y_min = min(p[1] for p in pixels)
    raw_y_max = max(p[1] for p in pixels)
    y_bounds = [F(raw_y_min) - CURVE_RADIUS, F(raw_y_max) + CURVE_RADIUS]
    physical = [(y - b) / a for y in y_bounds for a, b in ycal]
    lo, hi = min(physical), max(physical)
    ax, bx = nominal(xcal)
    ay, by = nominal(ycal)
    xnom = floor(ax * target_f + bx + F(1, 2))
    ynom = (F(min(by_column[xnom])) + F(max(by_column[xnom]))) / 2
    value = (ynom - by) / ay
    if not lo <= value <= hi:
        raise ValueError("Nominal anchor lies outside its analyst envelope")
    return {
        **row,
        "status": "readable",
        "raw_selected_y_extent_px": [raw_y_min, raw_y_max],
        "curve_y_envelope_px": [str(y) for y in y_bounds],
        "nominal_pixel": [xnom, str(ynom)],
        "nominal_value_fraction": str(value),
        "nominal_value": float(value),
        "analyst_read_envelope_fraction": [str(lo), str(hi)],
        "analyst_read_envelope": [float(lo), float(hi)],
    }


def main(destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Output already exists: " + str(destination))
    results = []
    axes = {}
    for panel, cfg in PANELS.items():
        path = BASE / "source" / cfg["file"]
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != cfg["sha256"]:
            raise ValueError(f"Source image changed: {path.name}")
        with Image.open(BytesIO(raw)) as original:
            image = original.convert("RGB")
        if image.size != cfg["size"]:
            raise ValueError("Unexpected native image size")
        xcal = calibration(cfg["x_labels"])
        ycal = calibration(cfg["y_labels"])
        if not all(a > 0 for a, _ in xcal) or not all(a < 0 for a, _ in ycal):
            raise ValueError("Unexpected axis orientation")
        axes[panel] = {
            "x_labels": cfg["x_labels"], "y_labels": cfg["y_labels"],
            "x_affine_vertices": [[str(a), str(b)] for a, b in xcal],
            "y_affine_vertices": [[str(a), str(b)] for a, b in ycal],
            "nominal_x": [str(v) for v in nominal(xcal)],
            "nominal_y": [str(v) for v in nominal(ycal)],
            "native_image": cfg["file"], "native_image_sha256": cfg["sha256"],
        }
        results.extend(read_anchor(panel, cfg, image, xcal, ycal, target) for target in cfg["targets"])
    payload = {
        "kind": "twelve_conditional_raster_anchor_readings_not_experimental_error",
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": sha256((BASE / "PROTOCOL.md").read_bytes()).hexdigest(),
        "Pillow_version": pillow_version,
        "pixel_coordinates": "zero-based centers in native embedded image; x right, y down",
        "analyst_label_center_half_width_px": str(LABEL_RADIUS),
        "analyst_curve_extent_padding_px": str(CURVE_RADIUS),
        "axes": axes,
        "readings": results,
    }
    raw_output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with destination.open("x") as output:
        output.write(raw_output)
    for row in results:
        if row["status"] == "readable":
            lo, hi = row["analyst_read_envelope"]
            print(f'{row["panel"]:3} {row["target_temperature_C"]:3} C {row["nominal_value"]:.6f} [{lo:.6f}, {hi:.6f}]')
        else:
            print(row["panel"], row["target_temperature_C"], row["status"], row["reason"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output path; existing files are refused")
    main(parser.parse_args().output)
