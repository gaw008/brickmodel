"""Offline numerical comparison of saved water-column phase trajectories.

No physical host is imported. Inventory/energy residuals use exact saved binary
values; event convergence is reported separately from the root bracket width.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_equilibrium_water_column import analyze_implicit, compare


def analyze_events(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    header, initial = rows[:2]
    species = header['parameters']['boundary_program']['values']['species_order']
    original = [sum(Fraction(p['inventories_mol'][k]) for p in initial['states']) for k in species]
    original.append(sum(Fraction(p['internal_energy_j']) for p in initial['states']))
    residuals = [0.] * len(original)
    events = []
    for row in rows:
        if row['kind'] != 'phase_event':
            continue
        current = [sum(Fraction(p['inventories_mol'][k]) for p in row['states']) for k in species]
        current.append(sum(Fraction(p['internal_energy_j']) for p in row['states']))
        for i, (after, before, exported) in enumerate(zip(current, original, row['exterior_integrals'], strict=True)):
            residuals[i] = max(residuals[i], abs(float(after-before+Fraction(exported))))
        events.append({k: row[k] for k in ('scope', 'cell_index', 'transition', 'time_s',
            'time_bracket_s', 'criterion_bracket_pa', 'bisection_iterations')})
    policy = header['parameters']['numerics']['phase_events']
    widths = [r['time_bracket_s'][1]-r['time_bracket_s'][0] for r in events]
    return {'events': events, 'column_events': [r for r in events if r['scope'] == 'column'],
        'maximum_bracket_width_s': max(widths) if widths else None,
        'all_brackets_within_configured_width': all(w <= policy['absolute_time_tolerance_s'] for w in widths),
        'all_brackets_change_phase': all((r['criterion_bracket_pa'][0]>0)!=(r['criterion_bracket_pa'][1]>0) for r in events),
        'event_global_inventory_residual_mol': max(residuals[:-1]),
        'event_global_energy_residual_j': residuals[-1],
        'scope': 'Crossings resolved by configured scan nodes; no exclusion of unobserved touching or paired roots.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    runs = {}
    for name, path in config['trajectories'].items():
        runs[name] = {'trajectory': analyze_implicit(root/path), 'phase': analyze_events(root/path)}
    comparisons = []
    for item in config['comparisons']:
        coarse, fine = runs[item['coarse']], runs[item['fine']]
        pair = compare(coarse['trajectory'], fine['trajectory'], item['kind'])
        a, b = coarse['phase']['column_events'], fine['phase']['column_events']
        identities_match = [e['transition'] for e in a] == [e['transition'] for e in b]
        differences = [abs(x['time_s']-y['time_s']) for x, y in zip(a, b, strict=True)] if identities_match else []
        budget = config['event_comparison_budgets_s'][item['kind']]
        pair.update(event_identities_match=identities_match, column_event_time_differences_s=differences,
            phase_event_comparison_budget_s=budget,
            phase_events_within_comparison_budget=identities_match and bool(differences) and all(d<=budget for d in differences))
        comparisons.append(pair)
    result = {'settings': config, 'runs': runs, 'comparisons': comparisons,
              'material_qualified': False, 'qualification': 'numerical evidence for the specified conditional channel only'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'comparisons': comparisons, 'event_counts': {k: len(v['phase']['events']) for k,v in runs.items()}}, indent=2))


if __name__ == '__main__':
    main()
