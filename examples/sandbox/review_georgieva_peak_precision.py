"""Independently locate R3 rate maxima using high-precision direct quadrature."""
import argparse
import json
from pathlib import Path

from mpmath import mp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); replay = json.loads((root/settings['replay']).read_text())
    policy = replay['settings']; mp.dps = settings['decimal_digits']; records = []
    beta = mp.mpf(policy['comparison_heating_rate_k_min'])/mp.mpf(policy['seconds_per_minute'])
    r = mp.mpf(policy['gas_constant_j_mol_k'])
    for case in replay['records']:
        source = case['parameter_set']; t0 = mp.mpf(case['cold_anchor_temperature_k'])
        a = mp.mpf(source['preexponential_per_minute'])/mp.mpf(policy['seconds_per_minute'])
        b = mp.mpf(source['activation_energy_j_mol'])/r
        radius0 = mp.root(1-mp.mpf(policy['cold_anchor_initial_conversion']),3)
        def rate(t):
            accumulated = a/beta*mp.quad(lambda v: mp.exp(-b/v), [t0,t])
            return 3*a*mp.exp(-b/t)*(radius0-accumulated)**2
        nominal = mp.mpf(case['peak_temperature_k']); delta = mp.mpf(settings['peak_bracket_half_width_k'])
        peak = mp.findroot(lambda t: mp.diff(rate,t), (nominal-delta,nominal+delta),
                           tol=mp.mpf(settings['root_tolerance']), maxsteps=settings['maximum_root_steps'])
        curvature = mp.diff(rate,peak,2)
        error = float(abs(peak-nominal))
        row = {'name': source['name'], 'cold_anchor_temperature_k': float(t0), 'independent_peak_temperature_k': str(peak),
            'absolute_difference_k': error, 'second_derivative_per_s_k2': str(curvature),
            'within_budget': bool(error<=settings['absolute_peak_budget_k'] and curvature<0)}
        records.append(row); print(json.dumps(row),flush=True)
    result = {'settings': settings, 'records': records, 'all_arithmetic_budgets_met': all(r['within_budget'] for r in records),
        'scope': 'Independent numerical differentiation of direct quadrature, no source parameter adjustment and no material validation.',
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream: json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__ == '__main__': main()
