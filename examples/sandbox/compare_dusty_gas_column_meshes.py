"""Compare volume-matched concentrations on both trajectories' native BDF nodes."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_maxwell_stefan_binary_column import polynomial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    records = {}
    for name, path in p['records'].items():
        with (root/path).open() as stream:
            records[name] = [json.loads(line) for line in stream]
    comparisons = []
    for coarse_name, fine_name in p['pairs']:
        coarse, fine = records[coarse_name], records[fine_name]
        accepted, ends = [], []
        times = {0.0}
        for rows in [coarse, fine]:
            steps = [row for row in rows if row['kind'] == 'accepted']
            accepted.append(steps)
            ends.append([row['time_s'] for row in steps])
            times.update(row['time_s'] for row in rows if row['kind'] in ('accepted', 'sample'))
            for order in rows[0]['settings']['verification']['entropy_quadrature_orders']:
                nodes, _ = leggauss(order)
                for row in steps:
                    left, right = row['dense_output']['start_time_s'], row['dense_output']['end_time_s']
                    times.update(float((left+right)/2+(right-left)*node/2) for node in nodes)
        maximum, when, location = 0.0, None, None
        mean_difference = 0.0
        for at in sorted(times):
            x, y = [(np.asarray(rows[1]['values']) if at == 0 else polynomial(steps[bisect_left(end, at)], at))
                .reshape(rows[0]['cell_count'], -1)
                for rows, steps, end in zip([coarse, fine], accepted, ends, strict=True)]
            parent = y.reshape(len(x), len(y)//len(x), x.shape[1]).mean(axis=1)
            difference = np.abs(parent-x)
            error = float(np.max(difference))
            mean_difference = max(mean_difference, float(np.max(np.abs(y.mean(axis=0)-x.mean(axis=0)))))
            if error > maximum:
                maximum, when = error, at
                location = list(map(int, np.unravel_index(np.argmax(difference), difference.shape)))
        comparisons.append({'coarse': coarse_name, 'fine': fine_name, 'union_times_compared': len(times),
            'maximum_parent_concentration_difference_mol_m3': maximum,
            'maximum_at_time_s': when, 'maximum_at_coarse_cell_and_species_zero_based': location,
            'maximum_mean_concentration_difference_mol_m3': mean_difference,
            'budget': p['maximum_parent_concentration_difference_mol_m3_budget'],
            'within_budget': maximum <= p['maximum_parent_concentration_difference_mol_m3_budget']})
    result = {'settings': p, 'comparisons': comparisons,
        'all_requested_budgets_met': all(row['within_budget'] for row in comparisons),
        'scope': 'Same-volume parent averages at the union of both accepted endpoints, 2/4-point dense quadrature nodes and observations, using native BDF polynomials. Not a continuous-time supremum or an experimental validation.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
