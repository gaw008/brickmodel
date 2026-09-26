"""Reconstruct printed Cp expressions and distinguish version/material evidence."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_sensible_heat_polynomial import RecordedSensibleHeatPolynomial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    source = json.loads((args.parameters.resolve().parent / p['source_file']).read_text())
    mp.mp.dps = p['decimal_digits']
    t0 = mp.mpf(str(p['reference_temperature_k']))
    offset = mp.mpf(str(p['kelvin_offset']))
    models = {'thesis_raw': source['michot2008']['raw_kaolin_equation4_1'],
              'thesis_calcined': source['michot2008']['calcined_equation4_2'],
              'journal_abstract_calcined': source['michot2011']['abstract_formula']}
    reviews = {}
    for name, record in models.items():
        a, b, c = [mp.mpf(str(record[key])) for key in ['A', 'B', 'C']]
        model = RecordedSensibleHeatPolynomial(float(a), float(b), float(c), float(t0))
        cp = lambda t: a + b*t + c/t**2
        temperatures = p['raw_kaolin_review_temperatures_c'] if name == 'thesis_raw' else p['calcined_review_temperatures_c']
        rows = []
        for temperature in temperatures:
            t = mp.mpf(str(temperature)) + offset
            values = [model.cp_j_kg_k(float(t)), model.relative_enthalpy_j_kg(float(t)), model.relative_entropy_j_kg_k(float(t))]
            references = [cp(t), mp.quad(cp, [t0, t]), mp.quad(lambda u: cp(u)/u, [t0, t])]
            errors = [float(abs(mp.mpf(value)-reference)) for value, reference in zip(values, references, strict=True)]
            rows.append({'temperature_c': temperature, 'cp_j_kg_k': values[0], 'relative_enthalpy_j_kg': values[1],
                'relative_entropy_j_kg_k': values[2], 'independent_errors': errors})
        maxima = [max(row['independent_errors'][i] for row in rows) for i in range(3)]
        budgets = p['numerical_budgets']
        flags = {key: maxima[i] <= budgets[key] for i, key in enumerate(['cp_absolute_j_kg_k', 'enthalpy_absolute_j_kg', 'entropy_absolute_j_kg_k'])}
        tmax = mp.mpf(str(temperatures[-1]))+offset
        reviews[name] = {'rows': rows, 'maximum_cp_h_s_errors': maxima, 'within_numerical_budgets': flags,
            'positive_cp_certificate': {'basis': 'B>0 and C<0 imply Cp increases for positive T; minimum Cp at lower endpoint',
                'minimum_cp_j_kg_k': float(cp(t0)), 'minimum_cp_slope_j_kg_k2': float(b-2*c/tmax**3)}}
    comparisons = []
    for first, second in zip(reviews['thesis_calcined']['rows'], reviews['journal_abstract_calcined']['rows'], strict=True):
        comparisons.append({'temperature_c': first['temperature_c'],
            'thesis_minus_journal_cp_j_kg_k': first['cp_j_kg_k']-second['cp_j_kg_k'],
            'thesis_cp_relative_to_journal_minus_one': first['cp_j_kg_k']/second['cp_j_kg_k']-1,
            'thesis_minus_journal_sensible_enthalpy_j_kg': first['relative_enthalpy_j_kg']-second['relative_enthalpy_j_kg']})
    measured = []
    for row, calculation in zip(source['michot2008']['table4_1_raw_KGa1B'], reviews['thesis_raw']['rows'], strict=True):
        measured.append({**row, 'equation_cp_j_kg_k': calculation['cp_j_kg_k'],
            'relative_difference_from_measurement': calculation['cp_j_kg_k']/row['measured_cp_j_kg_k']-1})
    appendix = source['michot2008']['appendix1_rows']
    sums = {key: mp.fsum(mp.mpf(str(row['wt_percent']))*mp.mpf(str(row[key]))/100 for row in appendix)
            for key in ['a_prime', 'b_prime', 'c_prime']}
    result = {'settings': p, 'source': source, 'models': reviews, 'version_comparison': comparisons,
        'raw_measurement_comparison': measured,
        'appendix_arithmetic': {'unnormalized_weight_sum_percent': float(mp.fsum(mp.mpf(str(row['wt_percent'])) for row in appendix)),
            'unnormalized_weighted_coefficients': {key: float(value) for key, value in sums.items()},
            'printed_total_coefficients': source['michot2008']['appendix1_printed_totals'],
            'weights_renormalized': False},
        'all_numerical_budgets_met': all(all(review['within_numerical_budgets'].values()) for review in reviews.values()),
        'formation_enthalpy_supplied': False, 'absolute_entropy_supplied': False,
        'changing_phase_reaction_heat_supplied': False, 'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_numerical_budgets_met': result['all_numerical_budgets_met'],
        'appendix_arithmetic': result['appendix_arithmetic'], 'at_last_temperature': comparisons[-1]}))


if __name__ == '__main__':
    main()
