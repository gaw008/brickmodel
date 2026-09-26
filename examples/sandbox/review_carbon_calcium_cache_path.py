"""Compare complete recorded trajectories after exact thermal memoization."""
import argparse
from collections import Counter
from itertools import zip_longest
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    examples, mismatched_rows = [], 0
    counts = [Counter(), Counter()]
    summaries, missing_rows = [None, None], 0

    def differences(a, b, path, ignored):
        if path in ignored:
            return []
        if isinstance(a, dict) and isinstance(b, dict):
            result = []
            for key in sorted(a.keys() | b.keys()):
                child = f'{path}.{key}' if path else key
                if child in ignored:
                    continue
                if key not in a or key not in b:
                    result.append(child)
                else:
                    result.extend(differences(a[key], b[key], child, ignored))
            return result
        return [] if a == b else [path]

    paths = [root / settings[key] for key in ['original_trajectory', 'candidate_trajectory']]
    with paths[0].open() as old, paths[1].open() as new:
        for index, pair in enumerate(zip_longest(old, new)):
            rows = [json.loads(line) if line is not None else None for line in pair]
            for i, row in enumerate(rows):
                if row is not None:
                    counts[i][row['kind']] += 1
                    if row['kind'] == 'summary':
                        summaries[i] = row
            if None in rows:
                missing_rows += 1
                mismatched_rows += 1
                continue
            kind = rows[0]['kind']
            ignored = settings['ignored_input_paths'] if kind == 'input' else (
                settings['ignored_summary_paths'] if kind == 'summary' else [])
            delta = differences(*rows, '', ignored)
            if delta:
                mismatched_rows += 1
                if len(examples) < settings['maximum_difference_examples']:
                    examples.append({'row_index': index, 'kind': kind, 'fields': delta})
    result = {'settings': settings, 'record_counts': [dict(c) for c in counts],
        'rows_missing_in_one_trajectory': missing_rows, 'mismatched_rows': mismatched_rows,
        'difference_examples': examples, 'all_compared_fields_exactly_equal': mismatched_rows == 0,
        'both_trajectories_completed': all(s is not None and s['status'] == 'completed' for s in summaries),
        'elapsed_seconds': [s['elapsed_s'] if s is not None else None for s in summaries],
        'material_qualified': False, 'training_eligible': False}
    with (root / settings['output']).open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
