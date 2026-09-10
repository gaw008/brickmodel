"""Reconstruct published symbols, never use the fitted line as observations.

Run from repository root. The original PDF/SVG remain in the ignored cache.
See DIGITIZATION_PLAN.md for the conservative graphic envelope and limitations.
"""
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


D = Decimal
ROOT = Path(__file__).resolve().parents[4]
SVG = ROOT / '.tools/source-cache/amadou2006/sorption-page6.svg'
EXPECTED = '2d918e1a89f049023475987a9f040d7dd4cead81c1b6ea6a061b02314ed73544'
SOURCE_SHA256 = '8070dddbca2b70863650d936bc11ad0e244c03b674aed677326c573368507c9a'
NUMBER = r'-?\d+(?:\.\d+)?'
# Rectangle paths on PDF page6, in the markers' shared source coordinates.
AXES = {
    50: tuple(map(D, ('191.579329', '441.781272', '575.658649', '674.898378'))),
    30: tuple(map(D, ('193.738671', '436.019116', '404.781206', '492.500536'))),
}
TRANSFORM = 'matrix(0.998568, 0, 0, -0.998568, -77.703499, 746.365778)'


def interval_coordinate(low: Decimal, high: Decimal, origin: Decimal, end: Decimal) -> tuple[Decimal, Decimal]:
    """Independent +/-0.5 graphic registration on marker and each axis end."""
    half = D('.5')
    candidates = [
        (point - start) / (stop - start)
        for point in (low - half, high + half)
        for start in (origin - half, origin + half)
        for stop in (end - half, end + half)
    ]
    return min(candidates), max(candidates)


def main() -> None:
    source_raw = Path(__file__).with_name('source.json').read_bytes()
    if hashlib.sha256(source_raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('source metadata differs from inspected record')
    source = json.loads(source_raw)
    for asset in source['assets']:
        asset_path = (ROOT / asset['path']).resolve()
        if not asset_path.is_relative_to(ROOT) or hashlib.sha256(asset_path.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('original source asset unavailable or changed')
    parameters = {row['temperature_degC']: (D(row['k']), D(row['n'])) for row in source['relation']['rows']}
    raw = SVG.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError('SVG differs from inspected source export')
    paths = list(ET.fromstring(raw).iter('{http://www.w3.org/2000/svg}path'))
    selected = {30: [], 50: []}
    for index, path in enumerate(paths):
        if path.get('fill') != 'rgb(0%, 0%, 100%)':
            continue
        if path.get('transform') != TRANSFORM:
            raise ValueError('unexpected marker transform')
        coords = list(map(D, re.findall(NUMBER, path.attrib['d'])))
        xs, ys = coords[::2], coords[1::2]
        xlo, xhi, ylo, yhi = min(xs), max(xs), min(ys), max(ys)
        center_y = (ylo + yhi) / 2
        # Separate legend markers at y~662 and y~487 from data, visually checked.
        temperature = 50 if D(580) < center_y < D(660) else 30 if D(410) < center_y < D(480) else None
        if temperature is None:
            continue
        selected[temperature].append((xlo, index, path, (xlo, xhi, ylo, yhi)))
    output = []
    for temperature in (30, 50):
        markers = sorted(selected[temperature], key=lambda item: item[0])
        if len(markers) != 8:
            raise ValueError('expected eight experimental markers per figure')
        ax0, ax1, ay0, ay1 = AXES[temperature]
        for ordinal, (_, index, path, box) in enumerate(markers, 1):
            xlo, xhi, ylo, yhi = box
            half_stroke = D(path.attrib['stroke-width']) / 2
            alo, ahi = interval_coordinate(xlo-half_stroke, xhi+half_stroke, ax0, ax1)
            lo, hi = interval_coordinate(ylo-half_stroke, yhi+half_stroke, ay0, ay1)
            lo, hi = lo / 4, hi / 4
            activity = D(ordinal) / 10
            if not alo <= activity <= ahi:
                raise ValueError('inferred nominal activity outside graphic envelope')
            observed = ((ylo+yhi)/2-ay0)/(ay1-ay0)/4
            k, n = parameters[temperature]
            printed_fit = k * (activity / (1-activity)) ** n
            output.append({
                'temperature_degC': temperature,
                'parameter_node_id': f'AMADOU2006_OSWIN_DESORPTION_{temperature}_PARAMETERS',
                'equation_node_id': f'AMADOU2006_OSWIN_DESORPTION_{temperature}_FORWARD',
                'figure': 3 if temperature == 50 else 4,
                'svg_path_index_zero_based': index,
                'original_path': path.attrib['d'],
                'transform': TRANSFORM,
                'axis_rectangle': list(map(str, AXES[temperature])),
                'marker_box': list(map(str, box)),
                'half_stroke': str(half_stroke),
                'inferred_nominal_activity': str(activity),
                'digitized_activity': str(((xlo+xhi)/2-ax0)/(ax1-ax0)),
                'activity_graphic_interval': list(map(str, (alo, ahi))),
                'digitized_X_kg_water_per_kg_dry': str(observed),
                'X_graphic_interval': list(map(str, (lo, hi))),
                'reported_coefficient_fit_X': str(printed_fit),
                'fit_minus_digitized_X': str(printed_fit-observed),
                'printed_fit_in_graphic_interval': lo <= printed_fit <= hi,
                'role': 'published_fit_reconstruction_not_independent_validation',
            })
    payload = {
        'source_id': 'SRC_AMADOU_2006_DESORPTION',
        'source_metadata_sha256': SOURCE_SHA256,
        'source_assets': source['assets'],
        'pdf_page': 6, 'svg_sha256': EXPECTED,
        'method': 'full experimental marker envelope plus stroke and0.5-source-unit registration; Decimal50',
        'experimental_scatter': None,
        'records': output,
    }
    Path(__file__).with_name('observations.json').write_text(json.dumps(payload, indent=2)+'\n')
    print(json.dumps({'points': len(output), 'fit_in_graphic_interval': sum(row['printed_fit_in_graphic_interval'] for row in output),
                      'max_abs_residual': str(max(abs(D(row['fit_minus_digitized_X'])) for row in output))}))


if __name__ == '__main__':
    with localcontext() as context:
        context.prec = 50
        main()
