"""Extract the publisher's colored curves without fitting or image resampling."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def affine(value, pixels, coordinates):
    return coordinates[0] + (value - pixels[0]) * (coordinates[1] - coordinates[0]) / (pixels[1] - pixels[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    image = np.array(Image.open(root / p['curve_figure']).convert('RGB'))
    curves = []
    for specimen, axes in p['curve_axes'].items():
        x0, x1 = axes['x_pixels']
        for color in p['curve_colors']:
            points = []
            for alpha in p['conversion_levels']:
                y = round(affine(alpha, axes['conversion'], axes['y_pixels']))
                h = p['curve_scan_half_height_pixels']
                matches = np.all(image[y-h:y+h+1, x0+1:x1] == color['rgb'], axis=2)
                xs = np.nonzero(matches)[1] + x0 + 1
                point = {'conversion': alpha, 'scan_center_y_pixel': y, 'matching_pixel_count': len(xs)}
                if not len(xs):
                    point['reading_status'] = 'color_not_visible_at_requested_conversion'
                    points.append(point)
                    continue
                lo, hi = int(xs.min()), int(xs.max())
                allowance = p['curve_axis_and_antialias_allowance_pixels']
                point.update({'reading_status': 'extracted', 'visible_x_pixel_interval': [lo, hi],
                    'temperature_c': affine((lo + hi) / 2, axes['x_pixels'], axes['temperature_c']),
                    'temperature_reading_interval_c': [affine(lo-allowance, axes['x_pixels'], axes['temperature_c']),
                                                       affine(hi+allowance, axes['x_pixels'], axes['temperature_c'])]})
                points.append(point)
            curves.append({'specimen': specimen, 'heating_rate_c_min': color['heating_rate_c_min'], 'points': points})
    parameters = {}
    for specimen, centers in p['parameter_centers_at_3_c_min'].items():
        row = {'heating_rate_c_min': p['selected_parameter_heating_rate_c_min']}
        for quantity, key in [('activation_energy_kcal_mol', 'activation_energy_y_pixel'), ('log10_A_per_min', 'log10_A_y_pixel')]:
            axes = p['parameter_axes'][quantity]
            center = centers[key]
            value = {'center_y_pixel': center, 'nominal': affine(center, axes['y_pixels'], axes['values'])}
            for label, width in [('reading_interval', p['parameter_center_reading_half_width_pixels']),
                                 ('hidden_errorbar_enclosing_interval', p['hidden_errorbar_plus_reading_half_width_pixels'])]:
                value[label] = sorted(affine(center + sign * width, axes['y_pixels'], axes['values']) for sign in [-1, 1])
            row[quantity] = value
        parameters[specimen] = row
    result = {'settings': p, 'curves': curves, 'parameters_from_figure6': parameters,
        'reading_intervals_are_experimental_confidence_intervals': False,
        'hidden_errorbar_envelope_note': 'Encloses a dot radius plus axis/center reading allowance. Not a confidence interval; Ea/A covariance and raw fit uncertainty are unavailable.',
        'raw_instrument_data': False, 'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'curves': len(curves), 'readings': sum(point['reading_status'] == 'extracted' for curve in curves for point in curve['points']),
                      'requested': sum(len(curve['points']) for curve in curves), 'source_parameters': parameters}))


if __name__ == '__main__':
    main()
