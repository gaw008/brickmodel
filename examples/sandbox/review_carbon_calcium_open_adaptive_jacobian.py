"""Compare local adaptive body coloring with separate-coordinate differences."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.integrate._ivp.common import num_jac

from carbon_calcium_column_derivative_setup import recorded_column
from sludge_sandbox.carbon_calcium_open_colored_jacobian import OpenColumnAdaptiveBodyJacobian


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    prior = json.loads((root/p['reference_rhs']).read_text())
    rows = []
    for snapshot in prior['snapshots']:
        kind = snapshot['column_kind']
        header = prior['headers'][kind]
        column = recorded_column(root, header, kind)
        body = 4*column.count
        values, at = np.array(snapshot['values']), snapshot['time_s']
        threshold = np.array(header['absolute_tolerances'][:body])
        numerics = {k: v for k, v in p['numerics'].items() if k != 'refinement_factor'}
        adaptive = OpenColumnAdaptiveBodyJacobian(column, threshold, numerics)
        actual = adaptive(at, values).toarray()
        rates = column.rates(at, values)

        def vectorized(time, columns):
            return np.column_stack([column.rates(time, np.concatenate((v, values[body:])))[:body] for v in columns.T])

        reference, factors = num_jac(vectorized, at, values[:body], rates[:body], threshold,
            None, (column.numerical_jacobian_sparsity()[:body, :body], np.arange(body)))
        scales = np.array(p['review']['rate_scales_C_O_N_T']*column.count)
        error = float(np.max(np.abs(actual[:body, :body]-reference.toarray())
                       * np.abs(values[:body])[None, :]/scales[:, None]))
        flags = {'body_matrix': error <= p['review']['scaled_matrix_absolute_budget'],
                 'body_adaptive_factors_equal': bool(np.array_equal(adaptive.factor, factors)),
                 'zero_ledger_columns': bool(np.all(actual[:, body:] == 0)),
                 'rhs_unchanged': bool(np.array_equal(rates, snapshot['rates']))}
        rows.append({'kind': kind, 'time_s': at, 'maximum_scaled_body_difference': error,
                     'within_budgets': flags})
    result = {'settings': p, 'rows': rows,
        'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in rows),
        'ledger_derivative_basis': 'static-smallstep-compensated-review.json; separate per-face MP comparison',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met'],
                      'maximum_scaled_body_difference': max(r['maximum_scaled_body_difference'] for r in rows)}), flush=True)


if __name__ == '__main__':
    main()
