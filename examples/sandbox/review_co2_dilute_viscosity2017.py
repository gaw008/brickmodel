"""Independent source-formula reconstruction and literature comparisons."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.co2_dilute_viscosity import CarbonDioxideDiluteViscosity
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root, q = args.parameters.resolve().parent, p['review']
    mp.mp.dps = q['decimal_precision']
    model = CarbonDioxideDiluteViscosity(p)
    a = list(map(mp.mpf, p['coefficients']))

    def source(temperature):
        t = temperature / mp.mpf(p['kelvin_scale'])
        # Original fraction form; production combines powers and exponentials.
        denominator = (a[0] + a[1]*mp.root(t, 6) + a[2]*mp.exp(a[3]*mp.root(t, 3))
            + (a[4]+a[5]*mp.root(t, 3))/mp.exp(mp.root(t, 3)) + a[6]*mp.sqrt(t))
        return mp.mpf(p['millipascal_to_pascal'])*mp.mpf(p['experimental_scaling_factor'])*mp.sqrt(t)/denominator

    arithmetic = []
    for temperature in q['temperatures_k']:
        value, derivative = source(mp.mpf(temperature)), mp.diff(source, mp.mpf(temperature))
        actual, slope = model.value_and_temperature_derivative(temperature)
        error = float(abs(mp.mpf(actual)/value-1))
        slope_error = float(abs(mp.mpf(slope)/derivative-1))
        arithmetic.append({'temperature_k': temperature, 'viscosity_pa_s': actual,
            'derivative_pa_s_k': slope, 'source_viscosity_decimal': str(value),
            'source_derivative_decimal': str(derivative), 'relative_error': error,
            'derivative_relative_error': slope_error, 'within_budgets':
                error <= q['value_relative_budget'] and slope_error <= q['derivative_relative_budget']})
    anchors = []
    for row in p['paper_calculated_values']:
        value = source(mp.mpf(row['temperature_k']))/mp.mpf(p['millipascal_to_pascal'])
        error = abs(value-mp.mpf(row['viscosity_mpa_s']))
        anchors.append(dict(row, source_value_mpa_s_decimal=str(value),
            absolute_difference_mpa_s=float(error),
            within_printed_rounding=error <= mp.mpf(row['rounding_half_unit_mpa_s'])))
    old_table = json.loads((root/q['historical_nist_file']).read_text())
    historical = []
    for row in old_table['tables']['CO2']['tables'][1][3:]:
        temperature, tabulated = float(row[0]), float(row[-1])
        actual = model.viscosity_pa_s(temperature)*float(p['pascal_to_micropascal'])
        budget = tabulated*q['historical_nist_relative_screen']+q['historical_nist_rounding_half_unit_micro_pa_s']
        historical.append({'temperature_k': temperature, 'tabulated_micro_pa_s': tabulated,
            'correlation_micro_pa_s': actual, 'signed_relative_difference': actual/tabulated-1,
            'screen_budget_micro_pa_s': budget, 'within_screen': abs(actual-tabulated) <= budget})
    lj = NonpolarGasTransport(json.loads((root/q['legacy_lj_parameters']).read_text()))
    legacy = []
    for temperature in q['legacy_comparison_temperatures_k']:
        value = model.viscosity_pa_s(temperature)
        old = lj.viscosity_pa_s(temperature, 'CO2')
        legacy.append({'temperature_k': temperature, 'source_viscosity_pa_s': value,
            'legacy_lj_viscosity_pa_s': old, 'legacy_relative_difference': old/value-1})
    result = {'settings': p, 'arithmetic_reviews': arithmetic, 'calculated_paper_anchors': anchors,
        'historical_nist_comparisons': historical, 'legacy_lj_comparisons': legacy,
        'all_arithmetic_budgets_met': all(row['within_budgets'] for row in arithmetic),
        'all_printed_anchor_budgets_met': all(row['within_printed_rounding'] for row in anchors),
        'all_historical_screen_budgets_met': all(row['within_screen'] for row in historical),
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key.startswith('all_')}))


if __name__ == '__main__':
    main()
