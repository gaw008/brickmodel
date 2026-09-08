"""Audit printed decimal relationships, without fitting or admitting a material."""
from decimal import Decimal, localcontext
from pathlib import Path
import hashlib
import json
from typing import Any


def audit(facts: dict[str, Any]) -> dict[str, Any]:
    """Recompute the versioned facts file; retain unresolved printed bases."""
    d = Decimal
    with localcontext() as context:
        context.prec = 40
        t1, t6 = facts['table1'], facts['table6']
        total = d(t6['input_kj'])
        products = sum(map(d, t6['product_energy_kj'].values()))
        sensible = sum(map(d, t6['sensible_energy_kj'].values()))
        elements = {k: d(v) for k, v in t1['elements_wt_percent'].items()}
        recovery = 100*products/total
        sensible_percent = 100*sensible/total
        checks = {
            'proximate_sum_percent': sum(map(d, t1['proximate_wt_percent'].values())),
            'listed_element_sum_on_printed_daf_basis_percent': sum(elements.values()),
            'listed_elements_plus_ash_percent_basis_not_reinterpreted': sum(elements.values())+d(t1['proximate_wt_percent']['ash']),
            'dulong_from_printed_values_mj_kg': d('.3383')*elements['C']+d('1.443')*(elements['H']-elements['O']/8)+d('.0927')*elements['S'],
            'input_components_sum_kj': d(t6['feed_energy_kj'])+d(t6['net_process_input_kj']),
            'product_sum_kj': products,
            'recovery_percent': recovery,
            'usable_percent': 100*(d(t6['product_energy_kj']['gas'])+d(t6['product_energy_kj']['liquid']))/total,
            'sensible_sum_kj': sensible,
            'sensible_percent': sensible_percent,
            'balance_error_from_component_energies_percent': 100-recovery-sensible_percent,
            'reported_percentage_triplet_sum': d(t6['reported_recovery_percent'])+d(t6['reported_sensible_percent'])+d(t6['reported_balance_error_percent']),
            'sensible_percent_minus_reported_percentage_points': sensible_percent-d(t6['reported_sensible_percent']),
            'feed_energy_divided_by_mass_mj_kg': d(t6['feed_energy_kj'])/d(t6['feed_mass_g']),
            'product_yield_sum_percent': sum(map(d, t6['product_yield_percent'].values())),
        }
        # Conditional rounding feasibility, not experimental uncertainty:
        # each printed energy rounded to nearest 0.01 kJ, percentage to 0.01%.
        lower = 100*(sensible-d('.015'))/(total+d('.005'))
        upper = 100*(sensible+d('.015'))/(total-d('.005'))
        reported = d(t6['reported_sensible_percent'])
        return {
            'schema': 'liu2023_decimal_audit_result_v1',
            'values': {key: str(value) for key, value in checks.items()},
            'conditional_rounding': {
                'assumption': 'nearest 0.01 kJ for each of three terms and total; nearest 0.01 percent for reported percentage',
                'computed_sensible_percent_bounds': [str(lower), str(upper)],
                'reported_sensible_percent_bounds': [str(reported-d('.005')), str(reported+d('.005'))],
                'intervals_disjoint': upper < reported-d('.005') or lower > reported+d('.005'),
            },
            'interpretation': 'Printed arithmetic mismatch requires clarification; no correction, normalized composition, missing species or heat capacity inferred.',
            'runtime_admission': False,
        }


if __name__ == '__main__':
    directory = Path(__file__).resolve().parent
    raw = (directory/'source_facts.json').read_bytes()
    result = audit(json.loads(raw))
    result['facts_sha256'] = hashlib.sha256(raw).hexdigest()
    result['audit_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (directory/'audit_result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
