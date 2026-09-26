"""Keep numerical accuracy separate from source-curve and cross-rate agreement."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_third_order_dehydroxylation import RecordedThirdOrderDehydroxylation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--readings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    data = json.loads(args.readings.read_text())
    mp.mp.dps = p['decimal_digits']
    calorie = mp.mpf(str(p['joules_per_thermochemical_kilocalorie']))
    gas_constant = mp.mpf(str(p['gas_constant_j_mol_k']))
    minute = mp.mpf(str(p['seconds_per_minute']))
    offset = mp.mpf(str(p['kelvin_offset']))
    alpha0 = mp.mpf(str(p['initial_conversion']))

    def independent(alpha_initial, t0_c, t1_c, beta_c_min, energy_kcal, log_a_min):
        energy = mp.mpf(str(energy_kcal)) * calorie
        a = mp.power(10, mp.mpf(str(log_a_min))) / minute
        beta = mp.mpf(str(beta_c_min)) / minute
        exposure = mp.quad(lambda t: a * mp.exp(-energy / (gas_constant * t)) / beta,
                           [mp.mpf(str(t0_c)) + offset, mp.mpf(str(t1_c)) + offset])
        return 1 - 1 / mp.sqrt((1-alpha_initial) ** -2 + 2 * exposure)

    reviews = []
    for curve in data['curves']:
        source_parameters = data['parameters_from_figure6'][curve['specimen']]
        e = source_parameters['activation_energy_kcal_mol']
        log_a = source_parameters['log10_A_per_min']
        model = RecordedThirdOrderDehydroxylation(float(mp.power(10, log_a['nominal']) / minute),
            float(mp.mpf(str(e['nominal'])) * calorie), float(gas_constant))
        initial = next(point for point in curve['points'] if point['conversion'] == p['initial_conversion'])
        t0 = initial['temperature_c'] + float(offset)
        points = [point for point in curve['points'] if point['reading_status'] == 'extracted'
                  and point['conversion'] > p['initial_conversion']]
        temperatures = np.array([point['temperature_c'] + float(offset) for point in points])
        beta = curve['heating_rate_c_min'] / p['seconds_per_minute']
        solutions = {}
        for name in ['base', 'refined']:
            solver = p['solver']
            sol = solve_ivp(lambda t, a: [model.conversion_rate_per_s(t, a[0]) / beta],
                [t0, temperatures[-1]], [float(alpha0)], method=solver['method'],
                rtol=solver[name]['relative_tolerance'], atol=solver[name]['absolute_tolerance'],
                max_step=solver['maximum_temperature_step_k'], t_eval=temperatures)
            if not sol.success:
                raise RuntimeError(sol.message)
            solutions[name] = sol.y[0]
        observations = []
        for index, point in enumerate(points):
            nominal = independent(alpha0, initial['temperature_c'], point['temperature_c'],
                curve['heating_rate_c_min'], e['nominal'], log_a['nominal'])
            row = {'observed_conversion': point['conversion'], 'source_temperature_c': point['temperature_c'],
                'source_temperature_reading_interval_c': point['temperature_reading_interval_c'],
                'predicted_conversion': float(solutions['refined'][index]),
                'prediction_minus_observed_conversion': float(solutions['refined'][index] - point['conversion']),
                'independent_reference_conversion': float(nominal),
                'reference_error': float(abs(mp.mpf(float(solutions['refined'][index])) - nominal)),
                'time_precision_difference': float(abs(solutions['refined'][index] - solutions['base'][index]))}
            for label in ['reading_interval', 'hidden_errorbar_enclosing_interval']:
                lower = independent(alpha0, initial['temperature_reading_interval_c'][1],
                    point['temperature_reading_interval_c'][0], curve['heating_rate_c_min'], e[label][1], log_a[label][0])
                upper = independent(alpha0, initial['temperature_reading_interval_c'][0],
                    point['temperature_reading_interval_c'][1], curve['heating_rate_c_min'], e[label][0], log_a[label][1])
                row[label] = {'predicted_conversion_interval': [float(lower), float(upper)],
                    'observed_conversion_inside': bool(lower <= point['conversion'] <= upper)}
            observations.append(row)
        reference_error = max(row['reference_error'] for row in observations)
        time_difference = max(row['time_precision_difference'] for row in observations)
        numerical = {'reference_conversion': reference_error <= p['numerical_budgets']['reference_conversion_absolute'],
                     'time_conversion': time_difference <= p['numerical_budgets']['time_conversion_absolute']}
        review = {'specimen': curve['specimen'], 'heating_rate_c_min': curve['heating_rate_c_min'],
            'role': 'same_curve_parameter_reconstruction' if curve['heating_rate_c_min'] == source_parameters['heating_rate_c_min'] else 'conditional_cross_rate_transfer',
            'initial_condition_from_this_curve': initial, 'parameters_from_3_c_min': source_parameters,
            'observations': observations, 'excluded_readings': [point for point in curve['points'] if point['reading_status'] != 'extracted'],
            'maximum_reference_error': reference_error, 'maximum_time_precision_difference': time_difference,
            'numerical_budgets_met': numerical,
            'nominal_mean_absolute_conversion_error': float(np.mean([abs(row['prediction_minus_observed_conversion']) for row in observations])),
            'nominal_maximum_absolute_conversion_error': max(abs(row['prediction_minus_observed_conversion']) for row in observations),
            'observations_inside_intervals': {label: sum(row[label]['observed_conversion_inside'] for row in observations)
                for label in ['reading_interval', 'hidden_errorbar_enclosing_interval']}}
        reviews.append(review)
        print(json.dumps({key: review[key] for key in ['specimen', 'heating_rate_c_min', 'role', 'numerical_budgets_met',
              'nominal_mean_absolute_conversion_error', 'observations_inside_intervals']}), flush=True)
    result = {'settings': p, 'readings_file': str(args.readings), 'reviews': reviews,
        'all_numerical_budgets_met': all(all(row['numerical_budgets_met'].values()) for row in reviews),
        'experimental_pass_threshold_defined': False,
        'intervals_are_experimental_confidence_intervals': False,
        'initial_conditions_from_each_target_curve': True,
        'within_study_transfer_is_independent_material_qualification': False,
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
