"""Read one published vector curve; no kinetic constants or model predictions.

Requires Poppler pdftocairo 26.07.0 and the separately retained original PDF.
The selected SVG path and plot identity were checked against the rendered page.
Only standard-library geometry is used after the PDF-to-SVG conversion.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from xml.etree import ElementTree as ET


PDF_REL = "data/sandbox/research/raw/nowicki-2011-char-kinetics.pdf"
PDF_SHA = "b1970f72bb595e31c67276860886545d337130587991a88d8c321c6d25aebb23"
NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
SVG_NS = "{http://www.w3.org/2000/svg}"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_segments(path):
    tokens = re.findall(r"[MLC]|" + NUMBER, path["d"])
    residue = re.sub(r"[MLC]|" + NUMBER + r"|\s+|,", "", path["d"])
    if residue:
        raise ValueError(f"unsupported SVG path syntax: {residue}")
    matrix = [float(x) for x in re.findall(NUMBER, path["transform"])]
    if len(matrix) != 6:
        raise ValueError("one explicit SVG affine matrix is required")
    a, b, c, d, e, f = matrix
    def transform(point):
        x, y = point
        return (a * x + c * y + e, b * x + d * y + f)
    segments, current, cursor = [], None, 0
    while cursor < len(tokens):
        command = tokens[cursor]
        count = {"M": 2, "L": 2, "C": 6}[command]
        values = [float(x) for x in tokens[cursor + 1:cursor + 1 + count]]
        if len(values) != count:
            raise ValueError("incomplete path command")
        points = [transform(values[i:i + 2]) for i in range(0, count, 2)]
        if command != "M":
            if current is None:
                raise ValueError("path must begin with M")
            segments.append({"kind": command, "points": [current] + points})
        current = points[-1]
        cursor += 1 + count
    return segments


def point_at(segment, u):
    points = segment["points"]
    if segment["kind"] == "L":
        return tuple((1. - u) * points[0][j] + u * points[1][j] for j in (0, 1))
    weights = ((1. - u)**3, 3. * (1. - u)**2 * u,
               3. * (1. - u) * u**2, u**3)
    return tuple(sum(w * p[j] for w, p in zip(weights, points)) for j in (0, 1))


def turning_parameters(segment, coordinate):
    if segment["kind"] == "L":
        return []
    p0, p1, p2, p3 = [p[coordinate] for p in segment["points"]]
    a, b, c = 3. * (-p0 + 3. * p1 - 3. * p2 + p3), 6. * (p0 - 2. * p1 + p2), 3. * (p1 - p0)
    if abs(a) < 1e-12:
        roots = [] if abs(b) < 1e-12 else [-c / b]
    else:
        discriminant = b * b - 4. * a * c
        roots = [] if discriminant < 0. else [
            (-b - math.sqrt(discriminant)) / (2. * a),
            (-b + math.sqrt(discriminant)) / (2. * a),
        ]
    return sorted(set(u for u in roots if 0. < u < 1.))


def crossings(segments, level):
    hits = []
    for index, segment in enumerate(segments):
        partitions = [0.] + turning_parameters(segment, 1) + [1.]
        for lo, hi in zip(partitions[:-1], partitions[1:]):
            ylo, yhi = point_at(segment, lo)[1], point_at(segment, hi)[1]
            for u, y in ((lo, ylo), (hi, yhi)):
                if abs(y - level) <= 1e-10:
                    hits.append({"segment_index": index, "kind": segment["kind"],
                                 "u": u, "point_pt": point_at(segment, u)})
            if (ylo - level) * (yhi - level) < 0.:
                left, right = lo, hi
                for _ in range(60):
                    middle = (left + right) / 2.
                    if (point_at(segment, left)[1] - level) * (point_at(segment, middle)[1] - level) <= 0.:
                        right = middle
                    else:
                        left = middle
                u = (left + right) / 2.
                hits.append({"segment_index": index, "kind": segment["kind"],
                             "u": u, "point_pt": point_at(segment, u)})
    unique = []
    for hit in sorted(hits, key=lambda value: value["point_pt"][0]):
        if not unique or abs(hit["point_pt"][0] - unique[-1]["point_pt"][0]) > 1e-8:
            unique.append(hit)
    return unique


def horizontal_band_extent(segments, lower_y, upper_y):
    # extrema in a horizontal band can occur at a band crossing, endpoint, or
    # interior x extremum. Include all three, without assuming monotonic data.
    points = [hit["point_pt"] for level in (lower_y, upper_y)
              for hit in crossings(segments, level)]
    for segment in segments:
        for u in [0., 1.] + turning_parameters(segment, 0):
            point = point_at(segment, u)
            if lower_y <= point[1] <= upper_y:
                points.append(point)
    if not points:
        raise ValueError("no curve geometry in requested horizontal band")
    return min(p[0] for p in points), max(p[0] for p in points)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    pdf = args.repo / PDF_REL
    if sha(pdf) != PDF_SHA:
        raise ValueError("original PDF identity mismatch")
    args.scratch.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    svg = args.scratch / "page4.svg"
    command = ["pdftocairo", "-f", "4", "-l", "4", "-svg", str(pdf), str(svg)]
    conversion = subprocess.run(command, capture_output=True, text=True, check=True)
    version = subprocess.run(["pdftocairo", "-v"], capture_output=True, text=True, check=True)
    version_line = (version.stdout + version.stderr).splitlines()[0]
    if version_line != "pdftocairo version 26.07.0":
        raise ValueError("path indices were verified with Poppler 26.07.0; re-audit another version")
    root = ET.parse(svg).getroot()
    stroked = [p for p in root.iter(SVG_NS + "path") if "stroke-width" in p.attrib]
    selected = dict(stroked[553].attrib)
    if len(stroked) != 1608 or len(selected["d"]) != 8838 or selected["stroke-width"] != "0.597":
        raise ValueError("verified solid curve path identity mismatch")
    if selected["transform"] != "matrix(0.998785, 0, 0, -0.998785, 254.310697, 149.875657)":
        raise ValueError("verified solid curve transform mismatch")
    segments = parse_segments(selected)
    # Printed tick centers, not text-label bounding boxes, define calibration.
    x_indices = [8, 13, 18, 23, 28, 33]
    y_indices = list(range(35, 46))
    x_ticks = [{"time_s": i * 3600, "stroked_path_index": index,
                "x_pt": parse_segments(stroked[index].attrib)[0]["points"][0][0]}
               for i, index in enumerate(x_indices)]
    y_ticks = [{"alpha_plot": i / 10., "stroked_path_index": index,
                "y_pt": parse_segments(stroked[index].attrib)[0]["points"][0][1]}
               for i, index in enumerate(y_indices)]
    x0, x1 = x_ticks[0]["x_pt"], x_ticks[-1]["x_pt"]
    y0, y1 = y_ticks[0]["y_pt"], y_ticks[-1]["y_pt"]
    for tick in x_ticks:
        tick["residual_from_endpoint_map_pt"] = tick["x_pt"] - (x0 + tick["time_s"] / 18000. * (x1 - x0))
    for tick in y_ticks:
        tick["residual_from_endpoint_map_pt"] = tick["y_pt"] - (y0 + tick["alpha_plot"] * (y1 - y0))
    residual_x = max(abs(t["residual_from_endpoint_map_pt"]) for t in x_ticks)
    residual_y = max(abs(t["residual_from_endpoint_map_pt"]) for t in y_ticks)
    transform_scale = .998785
    curve_width = float(selected["stroke-width"]) * transform_scale
    axis_width = .34 * transform_scale
    dpi, half_pixel_pt = 600., 72. / 600. / 2.
    curve_halfbox = curve_width / 2. + half_pixel_pt
    axis_half_x = axis_width / 2. + half_pixel_pt + residual_x
    axis_half_y = axis_width / 2. + half_pixel_pt + residual_y
    y_halfband = curve_halfbox + axis_half_y
    crop_x, crop_y = 1900, 450
    observations = []
    for tenth in range(1, 9):
        alpha = tenth / 10.
        target_y = y0 + alpha * (y1 - y0)
        hits = crossings(segments, target_y)
        if len(hits) != 1:
            raise ValueError(f"alpha_plot={alpha} lacks a unique centerline intersection; preserve as unknown")
        hit = hits[0]
        x, y = hit["point_pt"]
        time = 18000. * (x - x0) / (x1 - x0)
        band_lo, band_hi = horizontal_band_extent(segments, target_y - y_halfband, target_y + y_halfband)
        xlo, xhi = band_lo - curve_halfbox, band_hi + curve_halfbox
        time_corners = [18000. * (xx - aa) / (bb - aa)
                        for xx, aa, bb in itertools.product(
                            (xlo, xhi), (x0 - axis_half_x, x0 + axis_half_x),
                            (x1 - axis_half_x, x1 + axis_half_x))]
        observations.append({
            "alpha_plot": alpha, "time_s": round(time),
            "time_bounds_s": [math.floor(min(time_corners)), math.ceil(max(time_corners))],
            "time_from_vector_centerline_s": time,
            "time_bounds_unrounded_s": [min(time_corners), max(time_corners)],
            "pdf_page_top_left_pt": [x, y],
            "pdf_user_space_bottom_left_pt": [x, 790.866 - y],
            "crop_600dpi_px": [x * dpi / 72. - crop_x, y * dpi / 72. - crop_y],
            "centerline_horizontal_band_extent_x_pt": [band_lo, band_hi],
            "reading_box_top_left_pt": {"x": [xlo, xhi], "y": [target_y - y_halfband, target_y + y_halfband]},
            "centerline_intersection": hit,
            "intersection_vertical_residual_pt": y - target_y,
            "source_locator": "PDF page 4 / journal 696 / Figure 2(a) / 500 C solid experimental curve",
        })
    vectors = {
        "schema_version": 1, "source_pdf_sha256": PDF_SHA,
        "source_svg_sha256": sha(svg), "stroked_path_index_base": 0,
        "selection_rule": "document-order path elements with an explicit stroke-width attribute",
        "solid_500C_main_path_index": 553, "solid_500C_main_path_attributes": selected,
        "solid_500C_main_path_clip": "M 254.3125 64.769531 L 309 64.769531 L 309 150.019531 L 254.3125 150.019531 Z",
        "axis_path_attributes": {str(index): dict(stroked[index].attrib) for index in x_indices + y_indices},
        "qualifier": "Selected published vector geometry, not original experimental samples.",
    }
    vector_file = args.output / "figure2a_selected_vectors.json"
    vector_file.write_text(json.dumps(vectors, indent=2) + "\n")
    facts = {
        "schema_version": 1,
        "source": {"id": "SRC_NOWICKI_2011_CHAR", "title": "The kinetics of gasification of char derived from sewage sludge",
                   "authors": ["Lech Nowicki", "Anna Antecka", "Tomasz Bedyk", "Pawel Stolarek", "Stanislaw Ledakowicz"],
                   "year": 2011, "doi": "10.1007/s10973-010-1032-1",
                   "url": "https://link.springer.com/article/10.1007/s10973-010-1032-1",
                   "download_url": "https://link.springer.com/content/pdf/10.1007/s10973-010-1032-1.pdf",
                   "pdf_path": PDF_REL, "pdf_sha256": PDF_SHA, "pdf_bytes": pdf.stat().st_size,
                   "license": "Creative Commons Attribution Noncommercial; version not specified in PDF",
                   "license_locator": "PDF page 7 / journal 699 / Open Access paragraph",
                   "registry_path": "data/sandbox/research/source_candidates.json",
                   "registry_sha256": sha(args.repo / "data/sandbox/research/source_candidates.json")},
        "plot": {"pdf_page_1_based": 4, "journal_page": 696, "figure": "2(a)",
                 "temperature_c": 500, "gas_label": "Oxygen 10 vol.% in Ar", "line_style": "solid",
                 "x_quantity": "Time", "x_unit": "s", "y_quantity": "increasing plotted Conversion alpha_plot",
                 "full_page_size_pt": [595.276, 790.866], "coordinate_convention": "page top-left x right, y down; point=1/72 inch",
                 "curve_stroke_width_local_pt": .597, "curve_stroke_width_page_pt": curve_width,
                 "axis_stroke_width_page_pt": axis_width,
                 "render_check": {"dpi": dpi, "crop_page_pixels_xywh": [1900, 450, 1400, 980],
                                  "image_scratch_only": "fig2a-600dpi.png"}},
        "calibration": {"method": "affine endpoint map; all other tick deviations retained as a reading allowance",
                        "x_ticks": x_ticks, "y_ticks": y_ticks,
                        "time_s_per_page_pt": 18000. / (x1 - x0),
                        "alpha_plot_per_page_pt": 1. / (y0 - y1),
                        "max_tick_residual_x_pt": residual_x, "max_tick_residual_y_pt": residual_y,
                        "half_render_pixel_pt": half_pixel_pt,
                        "curve_halfbox_pt": curve_halfbox,
                        "axis_endpoint_halfbound_x_pt": axis_half_x,
                        "axis_endpoint_halfbound_y_pt": axis_half_y,
                        "total_y_search_halfband_pt": y_halfband,
                        "bounds_method": "Find all centerline geometry inside target_y +/- (curve_halfbox + axis_endpoint_halfbound_y); expand its x extrema by curve_halfbox; map all corners of x and uncertain x-axis endpoints to time; round interval outwards to seconds.",
                        "bounds_semantics": "conservative declared reading allowance from printed stroke, tick inconsistency and 600 dpi inspection; neither experimental scatter nor a statistical confidence interval"},
        "observations": observations,
        "method": {"script": str(Path(__file__).resolve().relative_to(args.repo.resolve())),
                   "script_sha256": sha(Path(__file__)), "python_version": sys.version,
                   "converter_version": version_line, "conversion_command": command,
                   "conversion_stderr": conversion.stderr.strip(), "svg_sha256": sha(svg),
                   "selected_vectors_file": vector_file.name, "selected_vectors_sha256": sha(vector_file),
                   "solid_path_d_sha256": hashlib.sha256(selected["d"].encode()).hexdigest(),
                   "intersection_method": "M/L/C vector geometry; cubic derivative partitions and 60-step bisection; no reaction equation, curve fit or Table2 value",
                   "max_vertical_intersection_residual_pt": max(abs(row["intersection_vertical_residual_pt"]) for row in observations)},
        "qualification": {"data_kind": "eight level crossings of one published experimental curve, not original sampled observations or independent replicates",
                          "observation_definition": "alpha_plot only; printed Eq1 sign inconsistency with the increasing figure and Eq6 remains unresolved",
                          "not_inferred": ["carbon-element conversion", "mass inventories", "m0 or mk", "oxygen consumption", "product yields", "reaction heat", "500 C rate constant or predicted curve"],
                          "source_values_loaded": "original PDF page4 vector geometry and source registry only; no Table2 CSV or kinetic model imported",
                          "admission": "limited source-condition plotted-response comparison; not raw sludge, brick-body or full-cycle validation"},
    }
    (args.output / "facts.json").write_text(json.dumps(facts, indent=2) + "\n")
    print(json.dumps({"facts": str(args.output / "facts.json"),
                      "observations": [{k: row[k] for k in ("alpha_plot", "time_s", "time_bounds_s")}
                                       for row in observations]}, indent=2))


if __name__ == "__main__":
    main()
