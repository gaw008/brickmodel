"""Compare volume-matched partial-concentration observations across uniform meshes."""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    observations = {}
    for name, path in p['records'].items():
        with (root/path).open() as stream:
            rows = (json.loads(line) for line in stream)
            observations[name] = [row for row in rows if row['kind'] in ('initial', 'sample')]
    comparisons = []
    for coarse_name, fine_name in p['pairs']:
        coarse, fine = observations[coarse_name], observations[fine_name]
        maximum, when, location = 0.0, None, None
        same_times = [row['time_s'] for row in coarse] == [row['time_s'] for row in fine]
        mean_difference = 0.0
        for a, b in zip(coarse, fine, strict=True):
            x, y = np.asarray(a['partial_concentrations_mol_m3']), np.asarray(b['partial_concentrations_mol_m3'])
            parent = y.reshape(len(x), len(y)//len(x), x.shape[1]).mean(axis=1)
            difference = np.abs(parent-x)
            error = float(np.max(difference))
            mean_difference = max(mean_difference, float(np.max(np.abs(y.mean(axis=0)-x.mean(axis=0)))))
            if error > maximum:
                maximum, when = error, a['time_s']
                location = list(map(int, np.unravel_index(np.argmax(difference), difference.shape)))
        comparisons.append({'coarse': coarse_name, 'fine': fine_name, 'observations': len(coarse),
            'same_times': same_times, 'maximum_parent_concentration_difference_mol_m3': maximum,
            'maximum_at_time_s': when, 'maximum_at_coarse_cell_and_species_zero_based': location,
            'maximum_mean_concentration_difference_mol_m3': mean_difference,
            'budget': p['maximum_parent_concentration_difference_mol_m3_budget'],
            'within_budget': same_times and maximum <= p['maximum_parent_concentration_difference_mol_m3_budget']})
    result = {'settings': p, 'comparisons': comparisons,
        'all_requested_budgets_met': all(row['within_budget'] for row in comparisons),
        'scope': 'Same-volume averages on prescribed uniform grids, not an experimental validation.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
