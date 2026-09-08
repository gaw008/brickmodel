"""Independently verify fixed printed arithmetic using exact rational numbers."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import runpy


def verify() -> dict[str, object]:
    """Check replay, provenance hashes, all values, and rounding disjointness."""
    directory = Path('/Users/wanggaoying/Desktop/brickmodel-github/data/sandbox/research/liu2023-energy')
    facts_bytes = (directory / 'source_facts.json').read_bytes()
    facts = json.loads(facts_bytes)
    result = json.loads((directory / 'audit_result.json').read_bytes())
    script_bytes = (directory / 'audit.py').read_bytes()
    assert result['facts_sha256'] == hashlib.sha256(facts_bytes).hexdigest()
    assert result['audit_sha256'] == hashlib.sha256(script_bytes).hexdigest()
    source_bytes = Path(facts['local_source']).read_bytes()
    assert len(source_bytes) == facts['source_bytes']
    assert hashlib.sha256(source_bytes).hexdigest() == facts['source_sha256']
    replay = runpy.run_path(str(directory / 'audit.py'))['audit'](facts)
    assert all(result[key] == value for key, value in replay.items())
    t = facts['table6']
    a = facts['table1']
    e = {key: F(value) for key, value in a['elements_wt_percent'].items()}
    sensible = sum(map(F, t['sensible_energy_kj'].values()))
    total = F(t['input_kj'])
    products = sum(map(F, t['product_energy_kj'].values()))
    expected = {
        'proximate_sum_percent': sum(map(F, a['proximate_wt_percent'].values())),
        'listed_element_sum_on_printed_daf_basis_percent': sum(e.values()),
        'listed_elements_plus_ash_percent_basis_not_reinterpreted': sum(e.values()) + F(a['proximate_wt_percent']['ash']),
        'dulong_from_printed_values_mj_kg': F('.3383')*e['C'] + F('1.443')*(e['H']-e['O']/8) + F('.0927')*e['S'],
        'input_components_sum_kj': F(t['feed_energy_kj']) + F(t['net_process_input_kj']),
        'product_sum_kj': products,
        'recovery_percent': 100*products/total,
        'usable_percent': 100*(F(t['product_energy_kj']['gas']) + F(t['product_energy_kj']['liquid']))/total,
        'sensible_sum_kj': sensible,
        'sensible_percent': 100*sensible/total,
        'balance_error_from_component_energies_percent': 100-100*(products+sensible)/total,
        'reported_percentage_triplet_sum': F(t['reported_recovery_percent']) + F(t['reported_sensible_percent']) + F(t['reported_balance_error_percent']),
        'sensible_percent_minus_reported_percentage_points': 100*sensible/total-F(t['reported_sensible_percent']),
        'feed_energy_divided_by_mass_mj_kg': F(t['feed_energy_kj'])/F(t['feed_mass_g']),
        'product_yield_sum_percent': sum(map(F, t['product_yield_percent'].values())),
    }
    assert expected.keys() == result['values'].keys()
    for key, value in expected.items():
        assert abs(F(result['values'][key])-value) < F('1e-35'), key
    lower = 100*(sensible-F('.015'))/(total+F('.005'))
    upper = 100*(sensible+F('.015'))/(total-F('.005'))
    reported = F(t['reported_sensible_percent'])
    disjoint = upper < reported-F('.005') or lower > reported+F('.005')
    assert disjoint == result['conditional_rounding']['intervals_disjoint']
    for actual, bound in zip(result['conditional_rounding']['computed_sensible_percent_bounds'], [lower, upper], strict=True):
        assert abs(F(actual)-bound) < F('1e-35')
    assert list(map(F, result['conditional_rounding']['reported_sensible_percent_bounds'])) == [reported-F('.005'), reported+F('.005')]
    return {'status': 'passed', 'checked_values': len(expected), 'maximum_allowed_representation_difference': '1e-35', 'scope': 'Printed arithmetic and replay only; no EOS or material validation', 'facts_sha256': result['facts_sha256'], 'audit_sha256': result['audit_sha256'], 'source_sha256': facts['source_sha256'], 'source_bytes': len(source_bytes), 'rounding_intervals_disjoint': disjoint, 'lower_to_reported_upper_gap_exact_fraction': str(lower-(reported+F('.005'))), 'verification_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
