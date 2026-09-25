"""Closed-form whole-interval spatial error of a finite-volume cosine mode.

This concerns the exact semidiscrete ODE solution versus exact PDE cell
averages. It does not assert a whole-interval bound on the BDF numerical error.
"""
import argparse
import json
from pathlib import Path

import mpmath as mp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    mp.mp.dps = settings['decimal_precision']
    records = []
    for case in settings['cases']:
        with (root/case['trajectory']).open() as stream:
            header = json.loads(next(stream))
        p = header['settings']
        count = header['cell_count']
        length, duration = mp.mpf(p['geometry']['length_m']), mp.mpf(p['duration_s'])
        width = length/count
        wave = p['initial']['cosine_mode']*mp.pi/length
        if case['model'] == 'binary_fick':
            diffusivity = mp.mpf(header['binary_diffusivity_m2_s'][0][1])
            amplitude = mp.mpf(p['initial']['cosine_amplitudes'][0])
            budget = p['verification']['continuum_exact_cell_average_fraction_budget']
            unit = 'mole_fraction'
        elif case['model'] == 'pure_knudsen':
            diffusivity = mp.mpf(header['effective_knudsen_diffusivities_m2_s'][0])/mp.mpf(p['pore']['porosity'])
            amplitude = mp.mpf(p['initial']['cosine_partial_pressure_amplitudes_pa'][0])/(mp.mpf(header['gas_constant_j_mol_k'])*mp.mpf(p['temperature_k']))
            budget = p['verification']['continuum_exact_cell_average_concentration_budget_mol_m3']
            unit = 'mol_m3'
        discrete = 4*diffusivity*mp.sin(wave*width/2)**2/width**2
        continuum = diffusivity*wave**2
        critical = mp.log(continuum/discrete)/(continuum-discrete)
        peak_time = min(duration, critical)
        amplitudes = [amplitude*mp.cos(wave*(i+mp.mpf('0.5'))*width)
            *mp.sin(wave*width/2)/(wave*width/2) for i in range(count)]
        time_factor = mp.exp(-discrete*peak_time)-mp.exp(-continuum*peak_time)
        cell_errors = [abs(value*time_factor) for value in amplitudes]
        maximum = max(cell_errors)
        derivative = -discrete*mp.exp(-discrete*peak_time)+continuum*mp.exp(-continuum*peak_time)
        records.append({'name': case['name'], 'trajectory': case['trajectory'], 'model': case['model'],
            'cell_count': count, 'error_unit': unit, 'diffusivity_m2_s_decimal': str(diffusivity),
            'discrete_decay_per_s_decimal': str(discrete), 'continuum_decay_per_s_decimal': str(continuum),
            'unconstrained_critical_time_s_decimal': str(critical), 'interval_peak_time_s_decimal': str(peak_time),
            'maximum_error_over_all_cells_and_time_decimal': str(maximum),
            'time_factor_derivative_at_peak_per_s_decimal': str(derivative),
            'budget': budget, 'within_budget': bool(maximum <= mp.mpf(budget))})
    result = {'settings': settings, 'records': records,
        'all_requested_budgets_met': all(row['within_budget'] for row in records),
        'scope': 'Exact real-arithmetic cosine modal solutions with frozen binary64 physical inputs, evaluated at declared MP precision. Whole-time spatial-operator comparison; no interval arithmetic and no rigorous whole-time BDF error bound. Existing trajectory audits remain separate.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
