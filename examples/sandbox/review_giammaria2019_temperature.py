"""Reconcile source temperature relations without claiming independent validation."""
import argparse
import json
import math
from pathlib import Path
import sys

import mpmath as mp
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_calcite_steam_plateau import RecordedCalciteSteamPlateau
from sludge_sandbox.recorded_calcite_steam_temperature import RecordedCalciteSteamTemperature


def fit_rows(rows, settings, energies, gas_constant):
    """A two-coefficient log-linear fit with a reported minimax margin factor."""
    A = []
    bounds = []
    for row in rows:
        log_value = math.log(row['value'])
        lower = log_value - math.log(row['value'] - row['margin'])
        upper = math.log(row['value'] + row['margin']) - log_value
        x = row['coordinate']
        A.extend([[1, x, -upper], [-1, -x, -lower]])
        bounds.extend([log_value, -log_value])
    policy = settings['fit']
    scale = settings['inverse_temperature_coordinate_scale_k']
    energy_bounds = [(energies[0] - energies[1]) / (gas_constant * scale),
                     (energies[0] + energies[1]) / (gas_constant * scale)]
    solution = linprog([0, 0, 1], A_ub=A, b_ub=bounds,
        bounds=[(None, None), tuple(energy_bounds), (0, None)], method=policy['method'],
        options={'primal_feasibility_tolerance': policy['primal_feasibility_tolerance'],
                 'dual_feasibility_tolerance': policy['dual_feasibility_tolerance']})
    a, b, z = map(float, solution.x)
    return {'log_reference_value': a, 'coordinate_slope': b,
            'reference_value': math.exp(a), 'energy_j_mol': b * gas_constant * scale,
            'maximum_log_margin_factor': z, 'solver_success': bool(solution.success),
            'solver_message': solution.message,
            'all_fitted_rows_inside_source_margins': z <= 1 + policy['margin_comparison_roundoff']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    parent = json.loads((root / settings['plateau_parameters']).read_text())
    plateau_source = json.loads((root / parent['source_file']).read_text())
    source = json.loads((root / settings['source_file']).read_text())
    table = plateau_source['table_rows']
    gas_constant = settings['gas_constant_j_mol_k']
    tref = settings['reference_temperature_c'] + parent['kelvin_offset']
    scale = settings['inverse_temperature_coordinate_scale_k']
    rate_factor = parent['site_density_mol_m2'] * parent['rate_table_multiplier_m2_s']
    pressure_factor = parent['pascal_per_bar']
    specifications = [('dry', 'k2_printed', 'k2_margin', rate_factor),
                      ('wet', 'k3_printed', 'k3_margin', rate_factor),
                      ('adsorption', 'K1_per_bar', 'K1_margin', 1 / pressure_factor)]
    reviews = {}
    for name, value_key, margin_key, conversion in specifications:
        printed = source['printed_temperature_relations'][name]
        energy = printed['enthalpy_j_mol'] if name == 'adsorption' else printed['activation_energy_j_mol']
        energy_margin = printed['enthalpy_margin_j_mol'] if name == 'adsorption' else printed['energy_margin_j_mol']
        if name == 'adsorption':
            log_prefactor = printed['entropy_j_mol_k'] / gas_constant - math.log(pressure_factor)
        else:
            log_prefactor = printed['log_prefactor']
            if name == 'wet':
                log_prefactor += math.log(parent['site_density_mol_m2'])
        rows = []
        for entry in table:
            t = entry['temperature_c'] + parent['kelvin_offset']
            value = entry[value_key] * conversion
            margin = entry[margin_key] * conversion
            predicted = math.exp(log_prefactor - energy / (gas_constant * t))
            rows.append({'temperature_c': entry['temperature_c'], 'temperature_k': t,
                'coordinate': scale * (1 / tref - 1 / t), 'value': value, 'margin': margin,
                'printed_central_prediction': predicted,
                'printed_prediction_inside_table_margin': abs(predicted - value) <= margin,
                'printed_relative_difference': (predicted - value) / value})
        fitted = fit_rows(rows, settings, (energy, energy_margin), gas_constant)
        for row in rows:
            predicted = math.exp(fitted['log_reference_value'] + fitted['coordinate_slope'] * row['coordinate'])
            row['reconciled_prediction'] = predicted
            row['reconciled_relative_difference'] = (predicted - row['value']) / row['value']
            row['reconciled_inside_source_margin'] = abs(predicted - row['value']) <= row['margin']
        withheld = []
        for i, row in enumerate(rows):
            other = fit_rows(rows[:i] + rows[i+1:], settings, (energy, energy_margin), gas_constant)
            predicted = math.exp(other['log_reference_value'] + other['coordinate_slope'] * row['coordinate'])
            withheld.append({'temperature_c': row['temperature_c'], 'fit': other,
                'predicted': predicted, 'source_value': row['value'], 'source_margin': row['margin'],
                'relative_difference': (predicted - row['value']) / row['value'],
                'inside_withheld_source_margin': abs(predicted - row['value']) <= row['margin']})
        reviews[name] = {'rows': rows, 'fit': fitted, 'withheld_table_rows': withheld,
            'internal_fitted_table_comparison_only': True}
    model = RecordedCalciteSteamTemperature(tref,
        RecordedCalciteSteamPlateau(reviews['dry']['fit']['reference_value'],
            reviews['wet']['fit']['reference_value'], reviews['adsorption']['fit']['reference_value']),
        reviews['dry']['fit']['energy_j_mol'], reviews['wet']['fit']['energy_j_mol'],
        reviews['adsorption']['fit']['energy_j_mol'], gas_constant)
    numerical = []
    mp.mp.dps = settings['numerical_review']['decimal_digits']
    M = lambda x: mp.mpf(str(x))
    def independent(t, p):
        coordinate = (1 / M(tref) - 1 / t) / M(gas_constant)
        a = M(model.reference_plateau.dry_rate_mol_s) * mp.exp(M(model.dry_activation_energy_j_mol) * coordinate)
        b = M(model.reference_plateau.steam_saturated_rate_mol_s) * mp.exp(M(model.wet_activation_energy_j_mol) * coordinate)
        k = M(model.reference_plateau.water_adsorption_coefficient_per_pa) * mp.exp(M(model.water_adsorption_enthalpy_j_mol) * coordinate)
        return (a + b * k * p) / (1 + k * p)
    for tc in settings['review_temperatures_c']:
        t = tc + parent['kelvin_offset']
        for pbar in settings['review_water_pressures_bar']:
            p = pbar * pressure_factor
            calculated = model.rate_and_derivatives(t, p)
            reference = {'rate_mol_s': float(independent(M(t), M(p))),
                'temperature_derivative_mol_s_k': float(mp.diff(lambda tt: independent(tt, M(p)), M(t))),
                'pressure_derivative_mol_s_pa': float(mp.diff(lambda pp: independent(M(t), pp), M(p)))}
            numerical.append({'temperature_c': tc, 'water_pressure_bar': pbar, 'calculated': calculated,
                'independent': reference, 'absolute_differences': {k: abs(calculated[k] - reference[k]) for k in reference}})
    mapping = {'rate_mol_s': 'rate_budget_mol_s',
               'temperature_derivative_mol_s_k': 'temperature_derivative_budget_mol_s_k',
               'pressure_derivative_mol_s_pa': 'pressure_derivative_budget_mol_s_pa'}
    maxima = {k: max(row['absolute_differences'][k] for row in numerical) for k in mapping}
    summary = {'printed_central_relations_inside_table_margins': {
        name: sum(row['printed_prediction_inside_table_margin'] for row in review['rows']) for name, review in reviews.items()},
        'total_table_rows_per_relation': len(table),
        'reconciled_relations_inside_fitted_source_margins': {name: review['fit']['all_fitted_rows_inside_source_margins'] for name, review in reviews.items()},
        'reconciled_predictions_inside_source_margins_direct': {name: all(row['reconciled_inside_source_margin'] for row in review['rows']) for name, review in reviews.items()},
        'withheld_table_rows_inside_margins': {name: sum(row['inside_withheld_source_margin'] for row in review['withheld_table_rows']) for name, review in reviews.items()},
        'maximum_numerical_differences': maxima,
        'numerical_budgets_met': {k: value <= settings['numerical_review'][mapping[k]] for k, value in maxima.items()}}
    result = {'settings': settings, 'source': source, 'relations': reviews, 'numerical': numerical,
        'summary': summary, 'scope': 'Conditional temperature parameterization of source plateau tables. Calibration consistency and derivative arithmetic, not experimental transient qualification.',
        'material_qualified': False, 'training_eligible': False}
    out = root / settings['output_directory']
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'review.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
