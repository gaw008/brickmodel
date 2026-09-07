"""Re-render review images from frozen manual picks; never select or modify points.

Pillow required. Reproduces the original overlay/contact drawing operations.
The RGB scan and manual selection steps are deliberately absent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

PICKS_SHA256 = "47abe70a2f8815c361a0ca8eb77682906248113e69320347c9aa54756e43d737"


def render(picks_path: Path, output_dir: Path, source_directory: Path | None = None) -> None:
    raw = picks_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PICKS_SHA256:
        raise ValueError("frozen manual picks hash mismatch")
    data = json.loads(raw)
    output_dir.mkdir(parents=True, exist_ok=True)
    for plot in data["plots"]:
        source = Path(plot["source_path"])
        if source_directory is not None:
            source = source_directory / source.name
        source_bytes = source.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != plot["source_sha256"]:
            raise ValueError(f"source hash mismatch: {source}")
        with Image.open(source) as loaded:
            native = loaded.convert("RGB")
        overlay = native.resize(
            (native.width * 3, native.height * 3), Image.Resampling.NEAREST
        )
        overlay_draw = ImageDraw.Draw(overlay)
        sheet = Image.new("RGB", (520, 13 * 100), "white")
        sheet_draw = ImageDraw.Draw(sheet)
        for index, point in enumerate(plot["points"]):
            x = point["pixel_x"]
            # Unknown centers are diagnostic markers, never observations.
            center_y = point["footprint"]["possible_center_for_inspection_only"]
            color = "red" if point["status"] == "unknown" else "black"
            overlay_draw.ellipse(
                (x * 3 - 10, center_y * 3 - 10,
                 x * 3 + 10, center_y * 3 + 10),
                outline=color, width=2,
            )
            overlay_draw.text(
                (x * 3 + 11, center_y * 3 - 9), str(index + 1), fill=color
            )
            crop = native.crop(
                (x - 8, int(center_y) - 7, x + 9, int(center_y) + 8)
            ).resize((102, 90), Image.Resampling.NEAREST)
            sheet.paste(crop, (0, index * 100))
            sheet_draw.text(
                (115, index * 100 + 8),
                f'{index + 1}: {point["target_temperature_c"]} C  '
                f'x={x}, y={point["pixel_y"]}  {point["status"]}',
                fill="black",
            )
            sheet_draw.text(
                (115, index * 100 + 28),
                f'green rows {point["footprint"]["min_y"]}..'
                f'{point["footprint"]["max_y"]}; native fixed column x',
                fill="black",
            )
            sheet_draw.line(
                (51, index * 100 + 90, 51, index * 100 + 96),
                fill="red", width=1,
            )
        overlay.save(output_dir / f'figure-{plot["figure"]}-overlay.png')
        sheet.save(output_dir / f'figure-{plot["figure"]}-contact.png')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--picks", type=Path,
                        default=Path(__file__).with_name("picks.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-directory", type=Path,
                        help="Relocated cache containing the same hash-verified native images")
    args = parser.parse_args()
    render(args.picks, args.output_dir, args.source_directory)
