"""Source-row selection plus independent full binary-viscosity/DGM balances."""
import argparse
import json
from pathlib import Path

from audit_co2_n2_reference_dusty_gas import property_review
from audit_dusty_gas_four_species_column import audit
from audit_dusty_gas_open_pure_column import time_comparison
from co2_n2_kinetic_column_reference import KineticColumnReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    reviews, trajectories, properties, selections = {}, {}, {}, {}
    for name, path in p['trajectories'].items():
        reviews[name], trajectories[name] = audit(root/path, KineticColumnReference)
        header = trajectories[name][0]
        properties[name] = property_review(header)
        selected = header['settings']['mixture_viscosity']['cross_section_row']
        original = next(row for row in header['mixture_source_settings']['cross_section_rows']
                        if row['temperature_k'] == selected['temperature_k'])
        selections[name] = {
            'exact_source_row': selected == original,
            'source_temperature_used_without_interpolation': header['settings']['temperature_k'] == float(original['temperature_k']),
            'source_species_order': header['settings']['species_order'] == ['CO2', 'N2'],
        }
        print(json.dumps({'trajectory': name, 'all_requested_budgets_met': reviews[name]['all_requested_budgets_met']}), flush=True)
    time = time_comparison(trajectories['base'], trajectories['refined'])
    result = {'settings': p, 'property_reviews': properties, 'source_row_selection': selections,
        'trajectory_reviews': reviews, 'time_comparison': time,
        'all_requested_budgets_met': all(r['all_requested_budgets_met'] for r in reviews.values())
            and all(r['within_budget'] for r in properties.values())
            and all(all(r.values()) for r in selections.values()) and time['within_budget'],
        'scope': 'Original nonsymmetric DGM equations and binary-viscosity H solve; full local/global species and entropy budgets, native BDF-node time comparison. Discrete source temperature, dilute properties and virtual pore geometry. Spatial qualification separate.',
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_requested_budgets_met': result['all_requested_budgets_met'], 'time_comparison': time}))


if __name__ == '__main__':
    main()
