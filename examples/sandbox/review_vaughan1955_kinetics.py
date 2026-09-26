"""Review the printed Arrhenius table and integrate an explicit source example."""
import argparse
import json
import math
from pathlib import Path
import sys

import mpmath as mp
import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_first_order_dehydroxylation import RecordedFirstOrderDehydroxylation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    source = json.loads((root / p['source_file']).read_text())
    mp.mp.dps = p['decimal_digits']
    cal = mp.mpf(str(p['joules_per_thermochemical_calorie']))
    minute = mp.mpf(str(p['seconds_per_minute']))
    half = p['printed_rounding_half_widths']
    conventions = {}
    for name, convention in p['conventions'].items():
        r_cal = (mp.mpf(str(convention['gas_constant_j_mol_k'])) / cal
                 if 'gas_constant_j_mol_k' in convention else mp.mpf(str(convention['gas_constant_cal_mol_k'])))
        t = mp.mpf(p['half_time_temperature_c']) + mp.mpf(str(convention['kelvin_offset']))
        rows = []
        for row in source['rows']:
            energy = mp.mpf(row['activation_energy_cal_mol'])
            log_a = mp.mpf(row['log10_frequency_factor'])
            def half_time(e, a):
                return mp.mpf(source['half_time_numerator_printed']) * mp.exp(e / (r_cal * t)) / mp.power(10, a)
            value = half_time(energy, log_a)
            energy_half = mp.mpf(str(half['activation_energy_cal_mol']))
            a_half = mp.mpf(str(half['log10_frequency_factor']))
            lower = half_time(energy - energy_half, log_a + a_half)
            upper = half_time(energy + energy_half, log_a - a_half)
            printed = mp.mpf(row['half_time_550c_min'])
            printed_half = mp.mpf(str(half['half_time_min']))
            rows.append({'id': row['id'], 'printed_half_time_min': float(printed),
                'calculated_half_time_min': float(value), 'nominal_minus_printed_min': float(value - printed),
                'parameter_printing_half_time_interval_min': [float(lower), float(upper)],
                'within_half_time_printing_only': bool(abs(value - printed) <= printed_half),
                'parameter_and_table_printing_intervals_overlap': bool(lower <= printed + printed_half
                                                                       and upper >= printed - printed_half),
                'if_A_were_per_second_half_time_min': float(value / minute)})
        conventions[name] = {'declared_constants': convention, 'rows': rows,
            'all_printing_intervals_overlap': all(row['parameter_and_table_printing_intervals_overlap'] for row in rows)}

    row = next(row for row in source['rows'] if row['id'] == p['selected_row_id'])
    convention = p['conventions']['declared_si']
    r = mp.mpf(str(convention['gas_constant_j_mol_k']))
    offset = mp.mpf(str(convention['kelvin_offset']))
    a = mp.power(10, mp.mpf(row['log10_frequency_factor'])) / minute
    energy = mp.mpf(row['activation_energy_cal_mol']) * cal
    model = RecordedFirstOrderDehydroxylation(float(a), float(energy), float(r))
    rate_reference = lambda t: a * mp.exp(-energy / (r * t))
    isothermal = []
    for temperature_c in p['isothermal_temperatures_c']:
        t = mp.mpf(temperature_c) + offset
        rate = model.rate_constant_per_s(float(t))
        reference = rate_reference(t)
        exposure = reference * p['isothermal_duration_s']
        isothermal.append({'temperature_c': temperature_c, 'rate_per_s': rate,
            'independent_relative_rate_error': float(abs(mp.mpf(rate) / reference - 1)),
            'half_time_s': float(mp.log(2) / reference),
            'conversion_after_declared_duration': model.conversion_from_exposure(float(exposure))})

    times = p['temperature_program']['time_s']
    temperatures = p['temperature_program']['temperature_c']
    observations = np.array(p['observation_times_s'], dtype=float)
    trajectories = {}
    reference_at_observations = []
    prior_reference_exposure = mp.mpf(0)
    for i in range(len(times) - 1):
        start, end = times[i:i + 2]
        lo, hi = map(mp.mpf, temperatures[i:i + 2])
        source_temperature = lambda time: lo + (hi - lo) * (time - start) / (end - start) + offset
        selected = observations[(observations >= start) & (observations <= end)]
        for time in selected:
            if reference_at_observations and time == reference_at_observations[-1]['time_s']:
                continue
            exposure = prior_reference_exposure + mp.quad(lambda x: rate_reference(source_temperature(x)), [start, float(time)])
            conversion = -mp.expm1(-exposure)
            reference_at_observations.append({'time_s': float(time), 'temperature_k': float(source_temperature(time)),
                'exposure': float(exposure), 'conversion': float(conversion)})
        prior_reference_exposure += mp.quad(lambda x: rate_reference(source_temperature(x)), [start, end])
    ref = np.array([[row['exposure'], row['conversion']] for row in reference_at_observations])
    for name in ['base', 'refined']:
        solver = p['solver']
        state = np.array([0., 0.])
        values = []
        segments = []
        for i in range(len(times) - 1):
            start, end = times[i:i + 2]
            lo, hi = temperatures[i:i + 2]
            def rhs(time, y):
                t = lo + (hi - lo) * (time - start) / (end - start) + float(offset)
                return [model.rate_constant_per_s(t), model.conversion_rate_per_s(t, y[1])]
            sol = solve_ivp(rhs, [start, end], state, method=solver['method'],
                rtol=solver[name]['relative_tolerance'], atol=solver[name]['absolute_tolerance'],
                max_step=solver['maximum_step_s'], dense_output=True)
            if not sol.success:
                raise RuntimeError(sol.message)
            selected = observations[(observations >= start) & (observations <= end)]
            for time, value in zip(selected, sol.sol(selected).T, strict=True):
                if values and time == values[-1]['time_s']:
                    continue
                values.append({'time_s': float(time), 'exposure': float(value[0]), 'conversion': float(value[1]),
                    'exponential_conversion': model.conversion_from_exposure(float(value[0]))})
            state = sol.y[:, -1]
            segments.append({'start_s': start, 'end_s': end, 'accepted_steps': len(sol.t) - 1,
                             'rhs_evaluations': sol.nfev, 'solver_message': sol.message})
        array = np.array([[value['exposure'], value['conversion']] for value in values])
        maxima = np.max(np.abs(array - ref), axis=0)
        trajectories[name] = {'segments': segments, 'observations': values,
            'maximum_reference_errors': {'exposure_absolute': float(maxima[0]), 'conversion_absolute': float(maxima[1])},
            'within_numerical_budgets': {'exposure_absolute': bool(maxima[0] <= p['numerical_budgets']['exposure_absolute']),
                                        'conversion_absolute': bool(maxima[1] <= p['numerical_budgets']['conversion_absolute'])}}
    time_difference = max(abs(a['conversion'] - b['conversion']) for a, b in zip(
        trajectories['base']['observations'], trajectories['refined']['observations'], strict=True))
    flags = {'isothermal_rate': max(row['independent_relative_rate_error'] for row in isothermal) <= p['numerical_budgets']['rate_relative'],
             'time_conversion': time_difference <= p['numerical_budgets']['time_conversion_absolute']}
    result = {'settings': p, 'source': source, 'table_arithmetic': conventions,
        'selected_specimen': row, 'isothermal': isothermal, 'independent_reference': reference_at_observations,
        'trajectories': trajectories, 'maximum_time_conversion_difference': time_difference,
        'within_numerical_budgets': flags,
        'all_numerical_budgets_met': all(flags.values()) and all(all(value['within_numerical_budgets'].values()) for value in trajectories.values()),
        'table_is_independent_reality_validation': False, 'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_numerical_budgets_met': result['all_numerical_budgets_met'],
        'table_printing_overlap_counts': {key: sum(row['parameter_and_table_printing_intervals_overlap'] for row in value['rows'])
                                        for key, value in conventions.items()},
        'maximum_time_conversion_difference': time_difference}))


if __name__ == '__main__':
    main()
