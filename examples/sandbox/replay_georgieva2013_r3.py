"""Reproduce printed R3 kinetic pairs and compare a published DTG peak."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq, minimize_scalar
from scipy.special import expi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); facts = json.loads((root/settings['source_facts']).read_text())
    beta = settings['comparison_heating_rate_k_min']/settings['seconds_per_minute']
    root_options = {'xtol': settings['root_absolute_tolerance_k'], 'rtol': settings['root_relative_tolerance'],
                    'maxiter': settings['root_maximum_iterations']}
    records = []
    for source in facts['parameter_sets']:
        e = source['activation_energy_j_mol']; a = source['preexponential_per_minute']/settings['seconds_per_minute']
        b = e/settings['gas_constant_j_mol_k']
        primitive = lambda t: t*math.exp(-b/t)+b*expi(-b/t)
        observation = next(p for p in facts['peak_observations'] if p['material']==source['material'])
        for t0 in settings['cold_anchor_temperatures_k']:
            initial_radius = (1-settings['cold_anchor_initial_conversion'])**(1/3)
            def integral(t): return float(primitive(t)-primitive(t0))
            def z(t): return a/beta*integral(t)
            def rate(t): return 3*a*math.exp(-b/t)*(initial_radius-z(t))**2
            complete = brentq(lambda t: z(t)-initial_radius, t0, settings['maximum_temperature_k'], **root_options)
            peak = brentq(lambda t: b/t**2*(initial_radius-z(t))-2*a/beta*math.exp(-b/t), t0, complete, **root_options)
            numerical_peak = minimize_scalar(lambda t: -rate(t), bounds=(t0,complete), method='bounded',
                options={'xatol': settings['scalar_search_absolute_tolerance_k']})
            if not numerical_peak.success: raise RuntimeError(numerical_peak.message)
            integral_direct, integration_error = quad(lambda t: math.exp(-b/t), t0, peak,
                epsabs=settings['quadrature_absolute_tolerance_k'], epsrel=settings['quadrature_relative_tolerance'])
            relative_difference = abs(integral_direct-integral(peak))/abs(integral_direct)
            observed = observation['peak_temperature_c']+settings['kelvin_offset']
            readings = []
            for t in np.linspace(t0,complete,settings['plot_samples'])[:-1]:
                radius = initial_radius-z(t)
                readings.append({'temperature_k': float(t), 'conversion': 1-radius**3, 'rate_per_s': rate(t)})
            readings.append({'temperature_k': complete, 'conversion': 1., 'rate_per_s': 0.})
            row = {'parameter_set': source, 'cold_anchor_temperature_k': t0, 'source_observation': observation,
                'preexponential_per_second': a, 'peak_temperature_k': peak, 'peak_temperature_c': peak-settings['kelvin_offset'],
                'conversion_at_peak': 1-(initial_radius-z(peak))**3, 'completion_temperature_k': complete,
                'observed_peak_temperature_k': observed, 'signed_peak_difference_k': peak-observed,
                'within_printing_interval_only': abs(peak-observed)<=observation['source_printing_half_step_k'],
                'independent_peak_temperature_k': float(numerical_peak.x), 'independent_peak_difference_k': abs(peak-float(numerical_peak.x)),
                'integral_relative_difference': relative_difference, 'quadrature_error_estimate_k': integration_error,
                'arithmetic_budgets_met': relative_difference<=settings['integral_relative_comparison_budget'] and abs(peak-float(numerical_peak.x))<=settings['peak_independent_tolerance_k'],
                'curve': readings}
            records.append(row)
            print(json.dumps({k: row[k] for k in ('cold_anchor_temperature_k','peak_temperature_c','signed_peak_difference_k','arithmetic_budgets_met')} | {'name': source['name']}), flush=True)
    result = {'settings': settings, 'source_facts': facts, 'records': records,
        'all_arithmetic_budgets_met': all(r['arithmetic_budgets_met'] for r in records),
        'model_note': 'R3 radius deficit is the Arrhenius time integral until exact reactant exhaustion. The derivative peak condition and independent scalar maximization use the same fixed source pair. No parameter fitting.',
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')


if __name__ == '__main__': main()
