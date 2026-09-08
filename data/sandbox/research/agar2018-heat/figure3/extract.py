"""Extract this publication's fixed vector markers, not instrument samples."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

NS = '{http://www.w3.org/2000/svg}'
SERIES = {
    '15': ('rgb(47.842407%, 47.842407%, 47.842407%)', 2, 'diamond'),
    '16': ('rgb(76.863098%, 77.255249%, 77.255249%)', 2, 'square'),
    '17': ('rgb(63.137817%, 63.137817%, 63.137817%)', 2, 'triangle'),
    '18': ('rgb(26.66626%, 26.66626%, 26.274109%)', 1, 'cross'),
    '19': ('rgb(89.019775%, 89.411926%, 89.411926%)', 1, 'star'),
    '20': ('rgb(74.118042%, 74.510193%, 74.510193%)', 2, 'circle'),
}
X0 = tuple(map(F, ('207.058594', '207.695312')))
X30 = tuple(map(F, ('539.296875', '539.933594')))
Y100 = tuple(map(F, ('689.742188', '690.378906')))
Y900 = tuple(map(F, ('493.871094', '494.5625')))


def box(paths: list[ET.Element]) -> tuple[F, F, F, F]:
    """Conservative hull of absolute path endpoints and Bezier controls."""
    coordinates = []
    for path in paths:
        data = path.attrib['d']
        if set(re.findall('[A-Za-z]', data)) - set('MLCZ'):
            raise ValueError('unsupported_path_command')
        numbers = [F(v) for v in re.findall(r'-?\d+(?:\.\d+)?', data)]
        if not numbers or len(numbers) % 2:
            raise ValueError('malformed_coordinate_pairs')
        coordinates.extend(zip(numbers[::2], numbers[1::2]))
    xs, ys = zip(*coordinates)
    return min(xs), max(xs), min(ys), max(ys)


def interval(values: list[F]) -> dict[str, object]:
    """Retain exact bounds and outward-rounded six-place decimal strings."""
    low, high = min(values), max(values)
    scale = 1_000_000
    lower = (low.numerator*scale)//low.denominator
    upper = -((-high.numerator*scale)//high.denominator)
    def decimal(integer: int) -> str:
        sign = '-' if integer < 0 else ''
        return f'{sign}{abs(integer)//scale}.{abs(integer)%scale:06d}'
    return {'rational_bounds': [str(low), str(high)],
            'decimal_bounds': [decimal(lower), decimal(upper)],
            'representative_midpoint': float((low+high)/2)}


def extract(directory: Path) -> dict[str, object]:
    """Fail closed if the registered figure structure no longer matches."""
    raw = (directory/'page5.svg').read_bytes()
    root = ET.fromstring(raw)
    parents = {child: parent for parent in root.iter() for child in parent}
    paths = list(root.iter(NS+'path'))
    rows, legends = [], {}
    for run, (color, parts, shape) in SERIES.items():
        chosen = [(i, p) for i, p in enumerate(paths) if p.get('fill') == color]
        if len(chosen) != 31*parts:
            raise ValueError('unexpected_series_path_count:'+run)
        for _, p in chosen:
            ancestor = p
            while ancestor is not None:
                if ancestor.get('transform'):
                    raise ValueError('unexpected_transform')
                ancestor = parents.get(ancestor)
        for marker in range(31):
            group = chosen[marker*parts:(marker+1)*parts]
            xmin, xmax, ymin, ymax = box([p for _, p in group])
            if marker == 30:
                if not (400 < xmin < xmax < 540 and 490 < ymin < ymax < 547):
                    raise ValueError('legend_region_mismatch')
                legends[run] = {'path_indices': [i for i, _ in group], 'shape': shape,
                                'bbox_page_points': list(map(str, (xmin, xmax, ymin, ymax)))}
                continue
            if not (F(3) < xmax-xmin < F(8) and F(3) < ymax-ymin < F(8)):
                raise ValueError('unexpected_marker_extent')
            times = [30*(x-a)/(b-a) for x, a, b in product((xmin, xmax), X0, X30)]
            temps = [100+800*(y-a)/(b-a) for y, a, b in product((ymin, ymax), Y100, Y900)]
            nominal = marker+1
            if not min(times) <= nominal <= max(times):
                raise ValueError('nominal_minute_not_enclosed')
            rows.append({'run_id': run, 'role': 'wall' if run in ('18', '19') else 'feedstock',
                         'marker_index': marker, 'nominal_minute_enclosed': nominal,
                         'path_indices': [i for i, _ in group], 'color': color, 'shape': shape,
                         'bbox_page_points': list(map(str, (xmin, xmax, ymin, ymax))),
                         'time_min': interval(times), 'temperature_c': interval(temps),
                         'time_envelope_extends_beyond_plot': min(times) < 0 or max(times) > 30})
    if len(rows) != 180:
        raise ValueError('incomplete_figure')
    return {'schema': 'agar2018_figure3_vector_v1', 'source_pdf_sha256': hashlib.sha256((directory.parent/'source.pdf').read_bytes()).hexdigest(),
            'svg_sha256': hashlib.sha256(raw).hexdigest(), 'extractor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'svg_provider': 'pdftocairo 26.07.0, -f 5 -l 5 -svg',
            'classification': 'derived_from_public_plot_geometry_not_raw_instrument_data',
            'interval_meaning': 'Conditional marker/control hull and axis-line calibration envelope; not experimental uncertainty.',
            'runtime_admission': False, 'training_eligible': False, 'external_validation_performed': False,
            'legends_excluded': legends, 'observations': rows}


if __name__ == '__main__':
    folder = Path(__file__).resolve().parent
    output = extract(folder)
    (folder/'observations.json').write_text(json.dumps(output, indent=2)+'\n')
    print('Extracted', len(output['observations']), 'published marker envelopes')
