"""Independent raster/axis reconstruction; does not import the extraction code."""

from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
HALF = Fraction(1, 2)
F = Fraction


def decode(item: dict) -> Fraction:
    return F(int(item["numerator"]), int(item["denominator"]))


def clip(vertices: list, a: Fraction, b: Fraction, c: Fraction) -> list:
    """Sutherland-Hodgman clipping, independent of pair-intersection enumeration."""
    out = []
    for start, end in zip(vertices, vertices[1:] + vertices[:1]):
        ds = a * start[0] + b * start[1] - c
        de = a * end[0] + b * end[1] - c
        if ds <= 0:
            out.append(start)
        if (ds < 0 < de) or (de < 0 < ds):
            ratio = ds / (ds - de)
            out.append(tuple(s + ratio * (e - s) for s, e in zip(start, end)))
    return list(dict.fromkeys(out))


def tick_groups(image: Image.Image, axis: str, strip: range, span: range) -> list:
    """Recover stroke positions directly; label order was read visually."""
    present = []
    for coord in span:
        values = [image.getpixel((coord, s) if axis == "x" else (s, coord)) for s in strip]
        if any(rgb != (255, 255, 255) for rgb in values):
            assert all(rgb != (255, 255, 255) for rgb in values)
            present.append(coord)
    groups = []
    for coord in present:
        if not groups or coord != groups[-1][-1] + 1:
            groups.append([coord])
        else:
            groups[-1].append(coord)
    return groups if axis == "x" else groups[::-1]


def reconstruct_axis(groups: list, labels: list) -> list:
    vertices = [(F(-1000), F(-1000)), (F(1000), F(-1000)),
                (F(1000), F(1000)), (F(-1000), F(1000))]
    for group, label in zip(groups, labels):
        r = (label - labels[0]) / (labels[-1] - labels[0])
        vertices = clip(vertices, 1 - r, r, max(group) + HALF)
        vertices = clip(vertices, r - 1, -r, HALF - min(group))
    assert vertices
    return sorted(vertices)


def component_count(points: set) -> int:
    remaining = set(points)
    count = 0
    while remaining:
        frontier = {remaining.pop()}
        while frontier:
            adjacent = {p for p in remaining if any(
                max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= 1 for q in frontier)}
            remaining -= adjacent
            frontier = adjacent
        count += 1
    return count


def main() -> None:
    facts = json.loads((ROOT / "extraction/facts.json").read_text())
    images = {}
    for n in (1, 2):
        with Image.open(ROOT / f"arlabosse-figure{n}.gif") as source:
            images[n] = source.convert("RGB")
    # All labels below are independent manual readings from the displayed originals.
    specifications = {
        (1, "x"): (range(245, 248), range(65, 482), [F(i, 5) for i in range(6)]),
        (1, "y"): (range(62, 65), range(7, 245), [F(i, 10) for i in range(11)]),
        (2, "x"): (range(244, 247), range(83, 489), [F(i, 2) for i in range(7)]),
        (2, "y"): (range(80, 83), range(6, 244), [F(2000000 + i * 200000) for i in range(10)]),
    }
    axes = {}
    tick_count = 0
    for (n, axis), (strip, span, labels) in specifications.items():
        groups = tick_groups(images[n], axis, strip, span)
        assert len(groups) == len(labels)
        vertices = reconstruct_axis(groups, labels)
        recorded = facts["calibration"][str(n)][axis]
        assert groups == [v["pixel_centers"] for v in recorded["ticks"]]
        assert labels == [decode(v["numeric_value"]) for v in recorded["ticks"]]
        assert vertices == sorted(tuple(map(decode, p)) for p in recorded["feasible_pixel_endpoint_vertices"])
        nominal = tuple(sum(p[k] for p in vertices) / len(vertices) for k in (0, 1))
        assert nominal == tuple(map(decode, recorded["nominal_pixel_endpoints"]))
        axes[n, axis] = labels[0], labels[-1], vertices, nominal
        tick_count += len(labels)
    # Stronger full-width test than the author's >=401/405 threshold; identical mask.
    grid = [y for y in range(6, 244) if all(
        images[2].getpixel((x, y)) != (255, 255, 255) for x in range(84, 489))]
    assert grid == facts["figure2_horizontal_grid_rows_masked_for_localization"]
    checks = []
    pixel_count = 0
    for recorded in facts["observations"]:
        n = recorded["figure"]
        level = F(recorded["requested_moisture_kg_water_per_kg_dry_matter"])
        target_axis, value_axis = ("y", "x") if n == 1 else ("x", "y")
        v0, v1, vertices, _ = axes[n, target_axis]
        ratio = (level - v0) / (v1 - v0)
        positions = [(1 - ratio) * p[0] + ratio * p[1] for p in vertices]
        band = min(positions), max(positions)
        assert band == tuple(map(decode, recorded["target_pixel_band_px"]))
        indices = [i for i in range(500) if i + HALF >= band[0] and i - HALF <= band[1]]
        assert indices == recorded["sampled_pixel_rows_or_columns"]
        domain = ((x, y) for y in indices for x in range(67, 481)) if n == 1 else (
            (x, y) for x in indices for y in range(7, 242) if y not in grid)
        points = {p for p in domain if images[n].getpixel(p) != (255, 255, 255)}
        supplied = {(p["x"], p["y"]): tuple(p["rgb"]) for p in recorded["raw_visible_pixels"]}
        assert points == set(supplied)
        assert all(images[n].getpixel(p) == rgb for p, rgb in supplied.items())
        pixel_count += len(points)
        components = component_count(points)
        assert components == recorded["visible_component_count"]
        flags = []
        if not points:
            flags.append("no_curve_pixels_visible_off_grid")
        if components > 1:
            flags.append("multiple_disconnected_visible_components")
        if n == 2 and any(abs(y - row) <= 1 for x, y in points for row in grid):
            flags.append("curve_pixel_footprint_touches_horizontal_grid_footprint")
        assert flags == recorded["unknown_reasons"]
        assert recorded["status"] == ("unknown" if flags else "candidate_reading")
        if not flags:
            values = [p[0 if n == 1 else 1] for p in points]
            span = min(values) - HALF, max(values) + HALF
            v0, v1, vertices, nominal = axes[n, value_axis]
            mapped = [v0 + (p - a) * (v1 - v0) / (b - a) for p in span for a, b in vertices]
            bound = min(mapped), max(mapped)
            assert bound == tuple(map(decode, recorded["digitization_bounds"]))
            mid = F(min(values) + max(values), 2)
            assert v0 + (mid - nominal[0]) * (v1 - v0) / (nominal[1] - nominal[0]) == decode(recorded["value"])
        else:
            assert recorded["value"] is None and recorded["digitization_bounds"] is None
        checks.append({"figure": n, "W": str(level), "status": recorded["status"], "pixel_count": len(points)})
    replay = ROOT / "review/facts.reviewer_replay.json"
    assert replay.read_bytes() == (ROOT / "extraction/facts.json").read_bytes()
    compile((ROOT / "extraction/extract_pixels.py").read_text(), "extract_pixels.py", "exec")
    report = {"status": "pass_for_discrete_candidate_raster_values_only",
              "independence": "own code, no extraction-module import; exact polygon clipping instead of vertex enumeration; same declared raster-footprint convention",
              "axes": 4, "tick_groups": tick_count, "observations": checks,
              "raw_rgb_pixels_verified": pixel_count, "replay_byte_identical": True,
              "facts_sha256": sha256((ROOT / "extraction/facts.json").read_bytes()).hexdigest(),
              "continuous_domain_admitted": None, "material_qualified": False}
    with (ROOT / "review/INDEPENDENT_CHECK.json").open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
