"""Reproduce a published first-order law under two explicit time-unit readings."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import expi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    readings = json.loads((root/settings['readings']).read_text())
    policy = settings['integration']
    start, stop = settings['temperature_interval_k']
    b = settings['activation_energy_j_mol']/settings['gas_constant_j_mol_k']

    def primitive(t):
        return t*math.exp(-b/t)+b*expi(-b/t)

    def integral(t):
        return primitive(t)-primitive(start)

    def quadrature(t):
        return quad(lambda u: math.exp(-b/u), start, t,
                    epsabs=policy['quadrature_absolute'], epsrel=policy['quadrature_relative'],
                    limit=policy['quadrature_limit'])[0]

    records = []
    temperatures = np.linspace(start, stop, policy['curve_samples'])
    for name, divisor in settings['preexponential_interpretations'].items():
        a = math.exp(settings['ln_preexponential'])/divisor
        curves, comparisons = [], []
        for heating in settings['heating_rates_k_min']:
            beta = heating/settings['seconds_per_minute']

            def conversion(t):
                initial = settings['initial_conversion']
                return initial-(1-initial)*math.expm1(-a/beta*integral(t))

            def event(alpha):
                return brentq(lambda t: conversion(t)-alpha, start, stop,
                              xtol=policy['root_absolute_temperature_k'], rtol=policy['root_relative'],
                              maxiter=policy['root_iterations'])

            curves.append({'heating_rate_k_min': heating, 'temperature_k': temperatures.tolist(),
                           'conversion': [conversion(t) for t in temperatures]})
            for sample in readings['samples']:
                if sample['heating_rate_k_min']!=heating: continue
                predicted = event(sample['conversion_nominal'])
                span = [event(alpha) for alpha in sample['conversion_reading_interval']]
                observed = sample['temperature_reading_interval_k']
                value, independent = integral(predicted), quadrature(predicted)
                error = abs(value-independent)/abs(independent)
                comparisons.append({'reading': sample, 'predicted_temperature_k': predicted,
                    'predicted_conversion_band_temperature_k': span,
                    'distance_to_reading_interval_k': max(observed[0]-predicted, predicted-observed[1], 0.),
                    'conversion_band_intersects_reading_temperature': bool(span[0]<=observed[1] and observed[0]<=span[1]),
                    'analytic_integral_k': value, 'independent_quadrature_integral_k': independent,
                    'integral_relative_difference': error,
                    'integral_comparison_budget_met': bool(error<=policy['analytic_quadrature_relative_budget'])})
        records.append({'interpretation': name, 'preexponential_per_s': a,
                        'comparisons': comparisons, 'curves': curves})
    result = {'settings': settings, 'readings': readings, 'records': records,
              'scope': 'Closed-form F1 nonisothermal conversion with fixed source coefficients; independent Arrhenius quadrature. Curve consistency does not resolve the printed unit or demonstrate material validity.',
              'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    for record in records:
        print(json.dumps({'interpretation': record['interpretation'],
                          'reading_intersections': sum(row['conversion_band_intersects_reading_temperature'] for row in record['comparisons']),
                          'observations': len(record['comparisons']),
                          'maximum_interval_distance_k': max(row['distance_to_reading_interval_k'] for row in record['comparisons']),
                          'all_integral_comparisons_met': all(row['integral_comparison_budget_met'] for row in record['comparisons'])}))


if __name__ == '__main__':
    main()
