"""Review pure zero-density correlations against MP math and printed anchors."""
import argparse
import json
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
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    review = p['review']
    mp.mp.dps = review['decimal_precision']
    rows, anchors, comparisons = [], [], []
    nist = json.loads((root/review['nist_table_file']).read_text())['tables']
    previous = json.loads((root/review['previous_lj_review']).read_text())
    for name, item in p['species'].items():
        def eta(t):
            x = mp.log(t/mp.mpf(item['well_depth_over_kb_k']))
            omega = mp.exp(mp.polyval(list(reversed([mp.mpf(v) for v in p['collision_log_coefficients']])), x))
            return (mp.mpf(p['viscosity_prefactor'])*mp.sqrt(mp.mpf(item['molar_mass_g_mol'])*t)
                    / (mp.mpf(item['diameter_nm'])**2*omega))

        def conductivity(t):
            tau = mp.mpf(item['critical_temperature_k'])/t
            return (mp.mpf(item['conductivity_viscosity_coefficient'])*eta(t)
                    + mp.fsum(mp.mpf(a)*tau**mp.mpf(power) for a, power in item['conductivity_terms']))

        for t in review['temperatures_k']:
            actual = dilute_transport(t, name, p)
            eta_scale = mp.mpf(p['unit_conversion']['micro_pa_s_to_pa_s'])
            lambda_scale = mp.mpf(p['unit_conversion']['milli_w_m_k_to_w_m_k'])
            reference = {'viscosity_pa_s': eta(t)*eta_scale,
                'viscosity_temperature_derivative_pa_s_k': mp.diff(eta, t)*eta_scale,
                'conductivity_w_m_k': conductivity(t)*lambda_scale,
                'conductivity_temperature_derivative_w_m_k2': mp.diff(conductivity, t)*lambda_scale}
            errors = {k: float(abs(mp.mpf(actual[k])/value-1)) for k, value in reference.items()}
            flags = {k: value <= review['relative_temperature_derivative_budget' if 'derivative' in k else 'relative_value_budget'] for k, value in errors.items()}
            rows.append({'species': name, 'temperature_k': t, 'actual': actual,
                         'reference_decimal': {k: str(v) for k, v in reference.items()},
                         'relative_errors': errors, 'within_budgets': flags})
        for row in nist[name]['tables'][1][3:]:
            t = float(row[0])
            actual = dilute_transport(t, name, p)
            values = {'viscosity': actual['viscosity_pa_s']/float(p['unit_conversion']['micro_pa_s_to_pa_s']),
                      'conductivity': actual['conductivity_w_m_k']/float(p['unit_conversion']['milli_w_m_k_to_w_m_k'])}
            for prop, column in [('viscosity', -1), ('conductivity', -2)]:
                table_value = float(row[column])
                budget = table_value*review['nist_estimated_uncertainty_fraction'][name][prop] + review['nist_rounding_half_unit'][name][prop]
                comparisons.append({'species': name, 'temperature_k': t, 'property': prop,
                    'table_value': table_value, 'model_value': values[prop],
                    'signed_relative_difference': (values[prop]-table_value)/table_value,
                    'table_uncertainty_plus_rounding': budget,
                    'within_table_range': abs(values[prop]-table_value) <= budget,
                    'pressure_condition_matches': False, 'source_url': nist[name]['url']})
    for item in p['calculated_paper_references']:
        actual = dilute_transport(item['temperature_k'], item['species'], p)
        eta = actual['viscosity_pa_s']/float(p['unit_conversion']['micro_pa_s_to_pa_s'])
        thermal = actual['conductivity_w_m_k']/float(p['unit_conversion']['milli_w_m_k_to_w_m_k'])
        errors = {'viscosity': abs(eta-float(item['viscosity_micro_pa_s'])),
                  'conductivity': abs(thermal-float(item['conductivity_mw_m_k']))}
        anchors.append({'source': item, 'actual_viscosity_micro_pa_s': eta,
            'actual_conductivity_mw_m_k': thermal, 'absolute_errors': errors,
            'within_printed_rounding': {k: v <= float(item[k+'_rounding_half_unit']) for k, v in errors.items()}})
    differences = []
    for row in previous['viscosity']:
        if row['species'] in p['species']:
            new = dilute_transport(row['temperature_k'], row['species'], p)['viscosity_pa_s']
            differences.append({'species': row['species'], 'temperature_k': row['temperature_k'],
                'previous_lj_pa_s': row['viscosity_pa_s'], 'paper_correlation_pa_s': new,
                'signed_relative_change': (new-row['viscosity_pa_s'])/row['viscosity_pa_s']})
    output = {'settings': p, 'independent_arithmetic': rows, 'paper_calculated_anchors': anchors,
        'nist_historical_table_comparisons': comparisons, 'difference_from_previous_lj_model': differences,
        'all_source_arithmetic_and_printed_anchor_budgets_met': all(all(r['within_budgets'].values()) for r in rows)
            and all(all(r['within_printed_rounding'].values()) for r in anchors),
        'all_nist_table_ranges_met': all(r['within_table_range'] for r in comparisons),
        'pressure_matched_experimental_validation': False, 'material_qualified': False, 'training_eligible': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({k: v for k, v in output.items() if k.startswith('all_')}), flush=True)


if __name__ == '__main__':
    main()
