"""Independent numerical/source review of the 2025 N2 zero-density term."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.lemmon2004_dilute_transport import dilute_transport
from sludge_sandbox.nitrogen2025_dilute_conductivity import dilute_conductivity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    review = p['review']
    mp.mp.dps = review['decimal_precision']

    def reference(t):
        reduced = t/mp.mpf(p['critical_temperature_k'])
        top = mp.fsum(mp.mpf(c)*reduced**i for i, c in enumerate(p['numerator_ascending']))
        bottom = mp.fsum(mp.mpf(c)*reduced**i for i, c in enumerate(p['denominator_ascending']))
        return mp.mpf(p['milli_w_to_w'])*top/bottom

    rows, anchors, historical, changes = [], [], [], []
    for t in review['temperatures_k']:
        actual = dilute_conductivity(t, p)
        exact = {'conductivity_w_m_k': reference(mp.mpf(t)),
                 'conductivity_temperature_derivative_w_m_k2': mp.diff(reference, mp.mpf(t))}
        errors = {k: float(abs(mp.mpf(actual[k])/value-1)) for k, value in exact.items()}
        flags = {k: error <= review['relative_derivative_budget' if 'derivative' in k else 'relative_value_budget']
                 for k, error in errors.items()}
        rows.append({'temperature_k': t, 'actual': actual,
            'reference_decimal': {k: str(value) for k, value in exact.items()},
            'relative_errors': errors, 'within_budgets': flags})
    for anchor in p['calculated_paper_anchors']:
        actual = dilute_conductivity(float(anchor['temperature_k']), p)['conductivity_w_m_k']/float(p['milli_w_to_w'])
        error = abs(actual-float(anchor['conductivity_mw_m_k']))
        anchors.append({'source': anchor, 'actual_mw_m_k': actual, 'absolute_error_mw_m_k': error,
                        'within_printed_rounding': error <= float(anchor['rounding_half_unit_mw_m_k'])})
    table = json.loads((root/review['nist_table_file']).read_text())['tables']['N2']
    for row in table['tables'][1][3:]:
        t, observed = float(row[0]), float(row[-2])
        actual = dilute_conductivity(t, p)['conductivity_w_m_k']/float(p['milli_w_to_w'])
        budget = review['nist_historical_uncertainty_fraction']*observed + review['nist_historical_rounding_half_unit_mw_m_k']
        historical.append({'temperature_k': t, 'historical_mw_m_k': observed, 'new_zero_density_mw_m_k': actual,
            'signed_relative_difference': (actual-observed)/observed,
            'historical_uncertainty_plus_rounding_mw_m_k': budget,
            'within_historical_table_range': abs(actual-observed) <= budget,
            'pressure_condition_matches': False, 'source_url': table['url']})
    previous = json.loads((root/review['previous_parameters']).read_text())
    for t in review['previous_comparison_temperatures_k']:
        before = dilute_transport(t, 'N2', previous)['conductivity_w_m_k']
        after = dilute_conductivity(t, p)['conductivity_w_m_k']
        changes.append({'temperature_k': t, 'lemmon2004_w_m_k': before, 'sotiriadou2025_w_m_k': after,
                        'signed_relative_change': (after-before)/before})
    result = {'settings': p, 'independent_arithmetic': rows, 'paper_calculated_anchors': anchors,
        'historical_nist_table_comparison': historical, 'zero_density_source_changes': changes,
        'all_source_arithmetic_and_printed_anchor_budgets_met': all(all(row['within_budgets'].values()) for row in rows)
            and all(row['within_printed_rounding'] for row in anchors),
        'all_historical_table_ranges_met': all(row['within_historical_table_range'] for row in historical),
        'pressure_matched_experimental_validation': False, 'material_qualified': False, 'training_eligible': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k.startswith('all_')}), flush=True)


if __name__ == '__main__':
    main()
