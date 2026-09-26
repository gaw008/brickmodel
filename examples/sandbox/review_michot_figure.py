"""Record a broad envelope of visible source curves at one printed temperature."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def affine(value, pixels, coordinates):
    return coordinates[0] + (value-pixels[0])*(coordinates[1]-coordinates[0])/(pixels[1]-pixels[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    source = json.loads((root / p['source_file']).read_text())
    q = p['figure_review']
    image = np.array(Image.open(root / q['local_render']).convert('RGB'))
    x = round(affine(q['temperature_c'], q['x_axis_temperature_c'], q['x_axis_pixels']))
    width = q['scan_half_width_pixels']
    ymin, ymax = q['scan_y_interval_pixels']
    region = image[ymin:ymax+1, x-width:x+width+1]
    mask = (region.max(axis=2) < q['maximum_rgb_channel']) & (np.ptp(region, axis=2) < q['maximum_rgb_spread'])
    ys = np.nonzero(mask)[0] + ymin
    endpoints = [int(ys.min())-q['reading_allowance_pixels'], int(ys.max())+q['reading_allowance_pixels']]
    interval = sorted(affine(y, q['y_axis_pixels'], q['y_axis_cp_j_kg_k']) for y in endpoints)
    values = {}
    t = q['temperature_c']+p['kelvin_offset']
    for name, formula in [('thesis_equation4_2', source['michot2008']['calcined_equation4_2']),
                          ('journal_abstract', source['michot2011']['abstract_formula'])]:
        cp = formula['A']+formula['B']*t+formula['C']/t**2
        values[name] = {'cp_j_kg_k': cp, 'inside_visible_curve_envelope': interval[0] <= cp <= interval[1]}
    result = {'settings': q, 'scan_center_x_pixel': x, 'visible_y_pixels': sorted(set(map(int, ys))),
        'visible_curve_and_grid_cp_envelope_j_kg_k': interval, 'candidate_values': values,
        'scope': 'Broad source-chart consistency envelope containing the visible gray/dashed curves and any grid pixels passing the stated filter. It is not raw calorimetry, a confidence interval or a model fit.',
        'figure_compared_is_independent_measurement_of_journal_fit': False,
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
