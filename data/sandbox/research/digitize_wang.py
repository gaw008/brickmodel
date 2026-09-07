"""Digitize published experimental symbols, never evaluate a fitted drying model.

Source: Wang et al. (2021), DOI 10.3390/en14227722, PDF page 5,
Figure 3 panels a-d. Original embedded bitmaps were extracted with pdfimages;
the calibration and point counts were inspected against the source figure and
Table 3. Output uncertainty is only a pixel readout bound, not a confidence
interval or an estimate of experimental scatter.
"""

import csv
import hashlib
import json
import statistics
from pathlib import Path

from PIL import Image


BASE = Path(__file__).resolve().parent
SOURCE_ID = "SRC_WANG_2021_SLUDGE_DRYING"
# Image, panel, RH, x(t=0), x(t=280 min), y(MR=0), y(MR=1).
PANELS = (
    ("wang2021-figure3-ab.png", "a", 30, 96, 569, 361, 37),
    ("wang2021-figure3-ab.png", "b", 40, 714, 1187, 361, 37),
    ("wang2021-figure3-cd.png", "c", 50, 96, 569, 356, 31),
    ("wang2021-figure3-cd.png", "d", 60, 714, 1187, 356, 31),
)
POINT_COUNTS = {
    (40, 30): 15, (40, 40): 17, (40, 50): 22, (40, 60): 29,
    (50, 30): 11, (50, 40): 13, (50, 50): 17, (50, 60): 20,
    (60, 30): 9, (60, 40): 10, (60, 50): 11, (60, 60): 12,
}


def matches(pixel, temperature):
    """Select saturated plot colors with a margin against anti-aliasing."""
    red, green, blue = pixel
    if temperature == 60:
        return red > 180 and green < 140 and blue < 140
    if temperature == 50:
        return green > 180 and red < 140 and blue < 140
    return blue > 180 and red < 140 and green < 140


def bottom_cluster(ys):
    """Remove a possible legend cluster, retaining the plotted symbol band.

    All late-time curves are below their legends in these specific figures.
    This is an inspected source-specific choice, not a general graph parser.
    """
    unique = sorted(set(ys))
    if not unique:
        raise ValueError("No curve pixels at a required published sample")
    start = len(unique) - 1
    # A steep connecting line can be separated from its marker by a few
    # anti-aliased pixels. Keep that local band together; legend separation
    # in these images is much larger (over 100 pixels for affected samples).
    while start > 0 and unique[start] - unique[start - 1] <= 20:
        start -= 1
    return sorted(y for y in ys if y >= unique[start])


def digitize():
    rows = []
    images = {}
    for filename, panel, rh, x0, x280, y0, y1 in PANELS:
        path = BASE / "figures" / filename
        images[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        with Image.open(path) as original:
            bitmap = original.convert("RGB")
        if bitmap.size not in {(1242, 466), (1242, 465)}:
            raise ValueError(f"Unexpected image dimensions for {filename}")
        for temperature in (40, 50, 60):
            last_mr = 1.0
            for index in range(POINT_COUNTS[temperature, rh]):
                time_min = index * 10
                x = round(x0 + (x280 - x0) * time_min / 280)
                if index == 0:
                    center = float(y1)
                    uncertainty = 0.0
                    method = "initial_normalization_defined_by_source_eq2"
                else:
                    pixels = [
                        y
                        for xx in range(x - 2, x + 3)
                        for y in range(y1 - 3, y0 + 1)
                        if matches(bitmap.getpixel((xx, y)), temperature)
                    ]
                    cluster = bottom_cluster(pixels)
                    center = statistics.median(cluster)
                    uncertainty = max(3, (cluster[-1] - cluster[0]) / 2 + 1) / (y0 - y1)
                    method = "color_symbol_pixel_readout"
                mr = (y0 - center) / (y0 - y1)
                if not 0 <= mr <= 1.015 or mr > last_mr + 0.015:
                    raise ValueError(f"Unexpected digitized point {panel=} {temperature=} {time_min=}")
                last_mr = mr
                rows.append({
                    "source_id": SOURCE_ID,
                    "material_id": "mianyang_qixingba_sludge",
                    "temperature_C": temperature,
                    "relative_humidity_percent": rh,
                    "time_min": time_min,
                    "moisture_ratio": round(mr, 6),
                    "readout_bound_MR": round(uncertainty, 6),
                    "experimental_uncertainty_MR": "",
                    "source_kind": "derived_from_evidence",
                    "upstream_observation_kind": "reported_experimental_curve",
                    "locator": f"PDF p5 Figure3{panel}",
                    "image": str(path.relative_to(BASE)),
                    "pixel_x": x,
                    "pixel_y": center,
                    "method": method,
                    "calibration_role": "unassigned",
                    "independent_material": False,
                })
    return rows, images


def main():
    rows, images = digitize()
    output = BASE / "wang_drying_digitized.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    audit = {
        "source_id": SOURCE_ID,
        "source_pdf": "raw/energies-14-07722.pdf",
        "extraction": "pdfimages -f 5 -l 5 -png raw/energies-14-07722.pdf /tmp/wang-fig; retain images000 and001 unchanged",
        "bitmap_sha256": images,
        "panel_calibration": PANELS,
        "point_count": len(rows),
        "condition_count": len(POINT_COUNTS),
        "sampling_interval_min": 10,
        "reported_replicates_per_condition": 3,
        "replicate_handling": "Source figure curves only; underlying triplicate series/scatter unavailable.",
        "error_meaning": "Readout bound covers half selected band plus1pixel or3pixels minimum; does not cover source measurement or calibration uncertainty.",
        "admission": "Experimental-data digitization for source-specific benchmark, not fitted-curve resampling and not whole-brick validation.",
        "limitations": [
            "MR uses source approximation Me=0; bound-water and equilibrium-moisture implications require model matching.",
            "High-RH low-temperature threshold times disagree between paper Sections3.1 and3.2; digitized curve is the selected upstream evidence.",
            "Underlying numerical measurements are unavailable; independent re-digitization is required before tight scientific tolerance claims.",
        ],
    }
    (BASE / "wang_digitization_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"Digitized {len(rows)} observations across {len(POINT_COUNTS)} conditions: {output}")


if __name__ == "__main__":
    main()
