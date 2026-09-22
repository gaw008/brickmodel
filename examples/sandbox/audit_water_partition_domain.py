"""Check the dilute-branch pressure-root premise for saved inventories.

The liquid molar-volume bound covers the full recorded Gibbs rectangle via
Chebyshev coefficient bounds; inventories are only the saved accepted states.
This is scientific accounting, not a runtime guard or an interval proof.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.chebyshev import chebder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    results = []
    for name, path in settings['trajectories'].items():
        with (root/path).open() as stream:
            header = json.loads(next(stream))
            table = header['water_source']['liquid_representation']
            pressure = table['pressure_domain_pa']
            coefficients = chebder(np.array(table['gibbs_coefficients_j_mol']),
                                  scl=2/(pressure[1]-pressure[0]), axis=1)
            center = float(coefficients[0, 0])
            radius = math.fsum(abs(float(v)) for v in coefficients.flat)-abs(center)
            volume_bound = [center-radius, center+radius]
            count = header['cell_count']
            order = header['parameters']['boundary_program']['values']['species_order']
            width = len(order)+1
            maximum = None
            minimum_carrier = math.inf
            evaluated = 0
            for line in stream:
                row = json.loads(line)
                if row['kind'] != 'accepted':
                    continue
                for i in range(count):
                    amounts = row['conserved_state'][i*width:i*width+len(order)]
                    ratio = math.fsum(amounts)*volume_bound[1]/header['cell_fluid_volume_m3']
                    carrier = math.fsum(n for k, n in zip(order, amounts, strict=True) if k != 'H2O')
                    minimum_carrier = min(minimum_carrier, carrier)
                    if maximum is None or ratio > maximum['ratio']:
                        maximum = {'ratio': ratio, 'time_s': row['time_s'], 'cell': i,
                                   'inventories_mol': dict(zip(order, amounts, strict=True))}
                    evaluated += 1
            results.append({'name': name, 'trajectory': path, 'accepted_cell_states': evaluated,
                'temperature_domain_k': table['temperature_domain_k'],
                'pressure_domain_pa': pressure, 'molar_volume_bound_m3_mol': volume_bound,
                'maximum_total_inventory_volume_ratio': maximum,
                'minimum_carrier_mol': minimum_carrier,
                'dilute_premise_over_recorded_rectangle': maximum['ratio'] < 1 and minimum_carrier > 0,
                'minimum_available_gas_fraction_bound': 1-maximum['ratio']})
    result = {'settings': settings, 'results': results,
        'qualification': 'Floating-point algebraic bound on the saved polynomial rectangle for each accepted inventory. No bound on unsaved nonlinear trials, time-continuous inventories, or EOS approximation error.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
