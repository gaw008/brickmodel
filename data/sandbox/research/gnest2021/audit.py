"""Recalculate printed-table consistency; never repairs or admits material data."""
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path


def audit(source):
    table = source['table3']
    reactions = []
    for i, name in enumerate(table['reactions']):
        products = [D(row[i]) for row in table['products'].values()]
        weight = D(table['yi'][i])
        total = sum(products, D(0))
        # Conditional bound: nearest rounding at each printed decimal place.
        bound = D('0.005') + len(products)*D('0.0005')
        residual = total-weight
        reactions.append({'reaction': name, 'sum_printed_products': str(total),
            'printed_yi': str(weight), 'sum_products_minus_yi': str(residual),
            'conditional_nearest_rounding_bound': str(bound),
            'outside_rounding_bound': abs(residual) > bound})
    mass = []
    for row in source['table4_tg3']:
        total = sum(map(D, row['products'].values()), D(0))
        mass.append({'temperature_c': row['temperature_c'], 'sum_printed_products': str(total),
            'printed_total': row['printed_total'], 'unaccounted_relative_to_unit_feed': str(D(1)-total),
            'difference_from_printed_total': str(total-D(row['printed_total']))})
    elements = []
    for temperature, totals in source['table5_printed_totals'].items():
        for element, total in totals.items():
            feed = D(source['table5_feed'][element])
            residual = D(total)-feed
            elements.append({'temperature_c': int(temperature), 'element': element,
                'printed_output_minus_input_kg_per_kg_dry_feed': str(residual),
                'interpretation': 'printed analytical bookkeeping; not a complete mineral-element balance'})
    return {'schema': 'gnest_printed_closure_audit_v1', 'reaction_checks': reactions,
            'mass_checks': mass, 'element_checks': elements,
            'runtime_admission': False, 'qualification': 'table consistency audit only',
            'decision': 'Printed R5/R6 products cannot directly instantiate Eq11 without unresolved correction or additional species. No normalization performed.'}


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    path = root/'source_facts.json'
    raw = path.read_bytes()
    result = audit(json.loads(raw))
    result['inputs_sha256'] = hashlib.sha256(raw).hexdigest()
    result['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (root/'audit_result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
