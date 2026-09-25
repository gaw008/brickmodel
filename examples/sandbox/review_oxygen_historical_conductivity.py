"""Trace a historical O2 expression; do not qualify it as current transport."""
import argparse
import json
import math
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.lemmon2004_dilute_transport import dilute_transport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    mp.mp.dps = p['review']['decimal_precision']
    coefficients = p['coefficients_ascending_third_power']
    power_first, denominator = p['first_power_numerator'], p['power_denominator']

    def reference(t):
        return mp.mpf(p['milli_w_to_w'])*mp.fsum(mp.mpf(a)*mp.mpf(t)**(
            mp.mpf(i+power_first)/denominator) for i, a in enumerate(coefficients))

    arithmetic, comparisons = [], []
    for t in p['review']['temperatures_k']:
        actual = float(p['milli_w_to_w'])*math.fsum(float(a)*t**((i+power_first)/denominator)
            for i, a in enumerate(coefficients))
        exact = reference(t)
        error = float(abs(mp.mpf(actual)/exact-1))
        arithmetic.append({'temperature_k': t, 'historical_formula_w_m_k': actual,
            'reference_decimal': str(exact), 'relative_arithmetic_error': error,
            'within_arithmetic_budget': error <= p['review']['relative_arithmetic_budget'],
            'within_roder_measurement_temperature_range': p['source']['measurement_temperature_range_k'][0] <= t <= p['source']['measurement_temperature_range_k'][1]})
    nist = json.loads((root/p['review']['nist_table_file']).read_text())['tables']['O2']
    prior = json.loads((root/p['review']['lemmon2004_parameters']).read_text())
    for row in nist['tables'][1][3:]:
        t, observed = float(row[0]), float(row[-2])
        historic = float(reference(t)/mp.mpf(p['milli_w_to_w']))
        later = dilute_transport(t, 'O2', prior)['conductivity_w_m_k']/float(p['milli_w_to_w'])
        budget = p['review']['nist_conductivity_uncertainty_fraction']*observed + p['review']['nist_rounding_half_unit_mw_m_k']
        comparisons.append({'temperature_k': t, 'nist_table_mw_m_k': observed,
            'historical_formula_mw_m_k': historic, 'lemmon2004_mw_m_k': later,
            'historical_relative_difference': (historic-observed)/observed,
            'lemmon2004_relative_difference': (later-observed)/observed,
            'historical_within_nist_range': abs(historic-observed) <= budget,
            'lemmon2004_within_nist_range': abs(later-observed) <= budget,
            'pressure_condition_matches': False, 'exact_refprop7_model_identity_proven': False})
    theory = []
    for t, value in p['hanley1973_table']['points']:
        tabulated = mp.mpf(value)*mp.mpf(p['hanley1973_table']['table_value_to_w_m_k'])
        historic = reference(t)
        theory.append({'temperature_k': t, 'hanley1973_w_m_k': float(tabulated),
            'roder1982_formula_w_m_k': float(historic),
            'signed_relative_difference': float(historic/tabulated-1),
            'is_independent_experiment': False})
    result = {'settings': p, 'arithmetic': arithmetic, 'nist_table_comparison': comparisons,
        'hanley1973_theoretical_table_comparison': theory,
        'all_arithmetic_budgets_met': all(row['within_arithmetic_budget'] for row in arithmetic),
        'all_historical_nist_ranges_met': all(row['historical_within_nist_range'] for row in comparisons),
        'same_pressure_experimental_validation': False, 'exact_refprop7_model_identity_proven': False,
        'production_property_admitted': False, 'material_qualified': False, 'training_eligible': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k.startswith('all_')}), flush=True)


if __name__ == '__main__':
    main()
