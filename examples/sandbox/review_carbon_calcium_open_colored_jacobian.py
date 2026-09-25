"""Review simultaneous local derivatives against independent dense differences."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import mpmath as mp

from carbon_calcium_column_derivative_setup import recorded_column
from sludge_sandbox.carbon_calcium_open_colored_jacobian import OpenColumnColoredJacobian


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    mp.mp.dps = p['review']['entropy_difference_decimal_precision']
    prior = json.loads((root/p['reference_rhs']).read_text())
    columns = {kind: recorded_column(root, header, kind) for kind, header in prior['headers'].items()}
    rows = []
    for snapshot in prior['snapshots']:
        column = columns[snapshot['column_kind']]
        values, at = np.array(snapshot['values']), snapshot['time_s']
        body = 4*column.count
        rhs_error = float(np.max(np.abs(column.rates(at, values)-snapshot['rates'])))
        rate_scale = np.array(p['review']['rate_scales_C_O_N_T']*column.count
                              + p['review']['ledger_rate_scales_E_S_Pi_Erad_Srad'])
        state_scale = np.concatenate((np.abs(values[:body]), np.ones(5)))
        for factor in [1., p['numerics']['refinement_factor']]:
            numerics = {key: value*factor for key, value in p['numerics'].items() if key != 'refinement_factor'}
            start = time.monotonic()
            matrix = OpenColumnColoredJacobian(column, numerics)(at, values).toarray()
            colored_seconds = time.monotonic()-start
            start = time.monotonic()
            dense = np.zeros_like(matrix)
            rounded_total_pi = np.zeros(body+5)
            for j in range(body+5):
                if j >= body:
                    step = p['review']['ledger_probe_increment'][j-body]
                elif j%4 == 3:
                    step = numerics['temperature_step_k']
                else:
                    step = abs(values[j])*numerics['inventory_relative_step']
                plus, minus = values.copy(), values.copy()
                plus[j] += step
                minus[j] -= step
                rates_plus, pieces_plus = column.rate_components(at, plus)
                rates_minus, pieces_minus = column.rate_components(at, minus)
                dense[:, j] = (rates_plus-rates_minus)/(plus[j]-minus[j])
                rounded_total_pi[j] = dense[body+2, j]
                # Sum all faces in MP before differencing, independently of
                # the sparse matrix's affected-face selection. Subtracting
                # two already-rounded total productions loses small slopes.
                dense[body+2, j] = float(mp.fsum(
                    [mp.mpf(float(v)) for v in pieces_plus]
                    + [-mp.mpf(float(v)) for v in pieces_minus])
                    / mp.mpf(float(plus[j]-minus[j])))
            dense_seconds = time.monotonic()-start
            scaled = np.abs(matrix-dense)*state_scale[None, :]/rate_scale[:, None]
            error = float(np.max(scaled))
            flags = {'scaled_matrix': error <= p['review']['scaled_matrix_absolute_budget'],
                     'rhs_unchanged': rhs_error <= p['review']['rhs_absolute_budget'],
                     'zero_ledger_feedback': float(np.max(np.abs(dense[:, body:]))) <= p['review']['ledger_feedback_absolute_budget']}
            rows.append({'column_kind': snapshot['column_kind'], 'time_s': at, 'factor': factor,
                'prior_phase_patterns': snapshot['phase_patterns'], 'rhs_absolute_error': rhs_error,
                'maximum_scaled_matrix_difference': error,
                'rounded_total_production_subtraction_scaled_error': float(np.max(
                    np.abs(rounded_total_pi-dense[body+2])*state_scale/rate_scale[body+2])),
                'largest_difference_row_column': [int(v) for v in np.unravel_index(np.argmax(scaled), scaled.shape)],
                'colored_seconds': colored_seconds, 'dense_seconds': dense_seconds,
                'within_budgets': flags})
    result = {'settings': p, 'rows': rows,
        'all_requested_numerical_budgets_met': all(all(row['within_budgets'].values()) for row in rows),
        'mathematical_differentiability_at_phase_boundaries_claimed': False,
        'material_qualified': False, 'training_eligible': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met'],
                      'matrices': len(rows), 'maximum_scaled_difference': max(r['maximum_scaled_matrix_difference'] for r in rows)}), flush=True)


if __name__ == '__main__':
    main()
