"""Combine completed individual source audits with saved-observation timing.

The whole-trajectory scientific audits are read, never rerun here. This command
adds the existing same-mesh time comparison; space qualification is separate.
"""
import argparse
import json
from pathlib import Path

from audit_carbon_calcium_column import compare, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    parent = json.loads((root/settings['parent_review_parameters']).read_text())
    reviews = {name: json.loads((root/path).read_text())['trajectory_review']
               for name, path in settings['individual_reviews'].items()}
    samples, headers = {}, {}
    for name, path in parent['trajectories'].items():
        stream = records(root/path); headers[name] = next(stream); samples[name] = {}
        for row in stream:
            if row['kind'] == 'sample':
                samples[name][row['time_s']] = [{key: state[key] for key in
                    ['temperature_k', 'pressure_pa', 'amounts_mol']} for state in row['states']]
    left, right = parent['time_comparison_pair']
    time_review = compare(samples[left], samples[right], headers[left]['settings']['verification'])
    result = {'settings': settings, 'parent_settings': parent, 'trajectory_reviews': reviews,
              'comparisons': {'time': time_review},
              'all_requested_numerical_budgets_met': all(review['all_requested_numerical_budgets_met'] for review in reviews.values()) and time_review['all_requested_budgets_met'],
              'scope': 'Previously completed individual whole-trajectory audits plus existing saved-observation time comparison. No repeated whole audit or spatial qualification.',
              'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met'], 'comparisons': result['comparisons']}), flush=True)


if __name__ == '__main__':
    main()
