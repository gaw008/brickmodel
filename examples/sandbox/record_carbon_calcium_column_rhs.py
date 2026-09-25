"""Preserve pre-change RHS values at named physical trajectory snapshots."""
import argparse
import json
from pathlib import Path

import numpy as np

from carbon_calcium_column_derivative_setup import recorded_column


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    snapshots, headers = [], {}
    for kind, filename in p['trajectories'].items():
        with (root/filename).open() as stream:
            header = json.loads(next(stream))
            headers[kind] = header
            column = recorded_column(root, header, kind)
            for line in stream:
                row = json.loads(line)
                if row['kind'] in ('initial', 'sample') and row['time_s'] in p['snapshot_times_s']:
                    values = np.array(row['values'])
                    snapshots.append({'column_kind': kind, 'time_s': row['time_s'],
                        'values': row['values'], 'rates': column.rates(row['time_s'], values).tolist(),
                        'phase_patterns': [[s['calcium_phase'], s['carbon_phase']] for s in row['states']]})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump({'settings': p, 'headers': headers, 'snapshots': snapshots}, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'recorded_snapshots': len(snapshots)}), flush=True)


if __name__ == '__main__':
    main()
