"""Reproduce finite TG picks and conditional coordinate intervals, never kinetics.

Requires Pillow and the hash-matched source images/PDF in ignored local cache.
Run --check to compare saved derived JSON/CSV without writing any file.
The preregistered intervals describe coordinate picking, not experiment error
or an enclosure of the whole curve across the horizontal uncertainty interval.
"""

import argparse
import csv
from decimal import ROUND_CEILING, ROUND_FLOOR
from fractions import Fraction as F
import hashlib
import io
from itertools import product
import json
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CALIBRATION = ROOT / "docs/sandbox/research/areias2019-tg-preregistration/tick-calibration-proposal.json"
METHOD = "areias2019-tg-sparse-native-picks-v1"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coordinate(pixel, first, last):
    x0, v0 = first
    x1, v1 = last
    require(x0 != x1, "coincident_calibration_ticks")
    return v0 + (pixel - x0) * (v1 - v0) / (x1 - x0)


def axis_interval(pixel, axis):
    ticks = [(F(t["pixel_center"]), F(t["value"])) for t in axis["ticks"]]
    first, last = ticks[0], ticks[-1]
    residual = max(abs(coordinate(x, first, last) - y) for x, y in ticks)
    require(residual == F(axis["max_abs_tick_residual_exact"]), "tick_residual_mismatch")
    require(all(F(t["conditional_pixel_halfwidth"]) == 1 for t in axis["ticks"]),
            "preregistered_tick_halfwidth_changed")
    corners = [coordinate(pixel + dp, (first[0] + da, first[1]),
                          (last[0] + db, last[1]))
               for dp, da, db in product((F(-2), F(2)), (F(-1), F(1)), (F(-1), F(1)))]
    return coordinate(pixel, first, last), min(corners) - residual, max(corners) + residual


def decimal(value, rounding=None):
    scaled = value * 100
    if rounding == ROUND_FLOOR:
        cents = scaled.numerator // scaled.denominator
    elif rounding == ROUND_CEILING:
        cents = -((-scaled.numerator) // scaled.denominator)
    else:
        require(rounding is None, "unsupported_rounding")
        cents = round(scaled)
    sign = "-" if cents < 0 else ""
    magnitude = abs(cents)
    return f"{sign}{magnitude // 100}.{magnitude % 100:02d}"


def interval_fields(prefix, values):
    nominal, lower, upper = values
    return {prefix: decimal(nominal), prefix + "_lower": decimal(lower, ROUND_FLOOR),
            prefix + "_upper": decimal(upper, ROUND_CEILING)}


def generate():
    calibration = json.loads(CALIBRATION.read_text())
    picks_path = HERE / "picks.json"
    picks = json.loads(picks_path.read_text())
    require(picks["calibration_sha256"] == digest(CALIBRATION), "pick_calibration_hash_mismatch")
    require(picks["point_halfwidth_xy"] == [2, 2] and picks["tick_halfwidth"] == 1,
            "preregistered_pixel_envelope_changed")
    source_path = HERE.parent / "source.json"
    source = json.loads(source_path.read_text())
    links_path = HERE.parent / "batch-links.json"
    links = json.loads(links_path.read_text())
    pdf = next(a for a in source["assets"] if a["path"].endswith("/thesis.pdf"))
    require(digest(ROOT / pdf["path"]) == pdf["sha256"], "source_pdf_hash_mismatch")
    require([p["figure"] for p in picks["plots"]] == [38, 39, 40], "figure_set_or_order")
    require([p["figure"] for p in calibration["plots"]] == [38, 39, 40], "calibration_figure_set")
    rows = []
    images = []
    for plot, cal in zip(picks["plots"], calibration["plots"]):
        figure = plot["figure"]
        image_path = ROOT / "runs/sandbox/source-cache/areias2019-20260907" / f"tg-native-{figure - 38:03}.png"
        require(digest(image_path) == cal["source_sha256"], "source_image_hash_mismatch")
        require(plot["source_sha256"] == cal["source_sha256"], "pick_image_hash_mismatch")
        with Image.open(image_path) as image:
            width, height = image.size
            pixels = image.convert("RGB")
        images.append({"path": str(image_path.relative_to(ROOT)), "sha256": digest(image_path),
                       "width": width, "height": height, "figure": figure})
        require([p["target_temperature_c"] for p in plot["points"]] ==
                calibration["proposed_sparse_target_temperatures_c"], "target_grid_changed")
        sample = next(s for s in links["samples"] if s["tg_dsc"]["figure"] == figure)
        x_axis, y_axis = cal["x_axis"], cal["green_y_axis"]
        slope = F(x_axis["nominal_endpoint_map"]["slope_exact"])
        intercept = F(x_axis["nominal_endpoint_map"]["intercept_exact"])
        first, last = x_axis["ticks"][0], x_axis["ticks"][-1]
        require(slope == (F(last["value"]) - F(first["value"])) /
                (F(last["pixel_center"]) - F(first["pixel_center"])) and
                intercept == F(first["value"]) - slope * F(first["pixel_center"]),
                "redundant_x_calibration_mismatch")
        for index, point in enumerate(plot["points"], 1):
            x = F(str(point["pixel_x"]))
            require(x == round((F(point["target_temperature_c"]) - intercept) / slope),
                    "target_nearest_column_changed")
            require(0 <= x < width, "pixel_x_outside_image")
            require(point["status"] in ("picked", "unknown"), "unsupported_pick_status")
            row = {"point_id": f"fig{figure}-{index:02}", "figure": figure,
                   "sample_id": sample["sample_id"], "target_temperature_c": point["target_temperature_c"],
                   "pixel_x": point["pixel_x"], "pixel_y": point["pixel_y"], "status": point["status"],
                   "reason": point["reason"]}
            row.update(interval_fields("temperature_c", axis_interval(x, x_axis)))
            if point["status"] == "unknown":
                require(point["pixel_y"] is None, "unknown_has_fabricated_ordinate")
                row.update({"plotted_weight_percent": None, "plotted_weight_percent_lower": None,
                            "plotted_weight_percent_upper": None})
            else:
                require(point["pixel_y"] is not None, "picked_without_ordinate")
                y = F(str(point["pixel_y"]))
                require(0 <= y < height, "pixel_y_outside_image")
                footprint = point["footprint"]
                observed = footprint["green_pixels"]
                require(bool(observed) and footprint["complete_green_identity_verified"],
                        "picked_without_verified_trace")
                require(all(abs(F(p["y"]) - y) <= 2 for p in observed), "pick_footprint_outside_box")
                require(all(tuple(p["rgb"]) == pixels.getpixel((int(x), p["y"])) for p in observed),
                        "pick_pixel_rgb_mismatch")
                row.update(interval_fields("plotted_weight_percent", axis_interval(y, y_axis)))
            rows.append(row)
    upstream = [Path(__file__), picks_path, CALIBRATION, source_path, links_path,
                HERE.parent / "thermal/facts.json"]
    data = {"schema_version": 1, "method_id": METHOD, "classification": "derived_from_evidence",
            "source_id": source["source_id"], "source_url": source["official_pdf_url"],
            "source_pdf": pdf, "source_images": images,
            "locations": [{"figure": 38, "pdf_page_one_based": 103, "printed_page": 100},
                          {"figure": 39, "pdf_page_one_based": 103, "printed_page": 100},
                          {"figure": 40, "pdf_page_one_based": 104, "printed_page": 101}],
            "upstream": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in upstream],
            "quantity": "green Peso (%) plotted relative weight, not cumulative loss or reaction conversion",
            "interval_scope": "conditional coordinate boxes; tick +/-1 and pick +/-2 native pixels, endpoint corners plus intermediate-tick residual, outward to 0.01; not experimental confidence or curve enclosure",
            "experimental_uncertainty": None, "normalization_mass_basis": None,
            "kinetics_fitted": False, "runtime_material_qualified": False, "training_eligible": False,
            "validation_status": "digitized observation candidate only; no model-versus-experiment comparison",
            "points": rows}
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return {"points.json": json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            "points.csv": stream.getvalue()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = generate()
    for name, content in outputs.items():
        path = HERE / name
        if args.check:
            require(path.read_text() == content, "derived_content_mismatch: " + name)
        else:
            path.write_text(content)
    data = json.loads(outputs["points.json"])
    print(json.dumps({"targets": len(data["points"]),
                      "picked": sum(p["status"] == "picked" for p in data["points"]),
                      "check": args.check}))


if __name__ == "__main__":
    main()
