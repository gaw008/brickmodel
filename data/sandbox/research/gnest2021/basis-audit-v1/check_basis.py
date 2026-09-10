"""Independent rational consistency checks on the saved basis diagnostics."""
import json
from fractions import Fraction as F
from pathlib import Path

p=Path(__file__).parent
result=json.loads((p/'BASIS_ARITHMETIC.json').read_text())
original=json.loads((p.parent/'table4-table5-audit-v1/quantitative-record.json').read_text())
assert result['source_sha256']==original['source_sha256']
# Complete atom inventories are not obtained by calling an ash complement O.
assert F(result['feed_CHONS_sum'])+F(result['implied_unassigned_ash_fraction'])==1
assert F(result['implied_unassigned_ash_fraction'])>0
# Require complete, unique source row coverage before making a ten-row claim.
expected_rows={(temperature,element) for temperature in (570,960) for element in 'CHONS'}
rows=result['rows']
assert len(rows)==len(expected_rows), 'basis row count'
assert {(row['T_C'],row['element']) for row in rows}==expected_rows, 'basis row identities'
assert all(len(row['independent_multiplication_of_printed_y_and_composition'])==6 for row in rows), 'six product terms required'
# Products in each row are exact finite-decimal quantities, independent of Decimal arithmetic.
for row in result['rows']:
    terms=list(map(F,row['independent_multiplication_of_printed_y_and_composition']))
    assert sum(terms,F())==F(row['sum'])
    feed=F(original['table5_960C_aggregate_element_audit'][row['element']]['feed_kg_per_kg_dry_feed'])
    assert sum(terms,F())-feed==F(row['sum_minus_printed_feed'])
# Even a missing species with zero H/O cannot decrease their existing positive excess.
for element in ('H','O'):
    fixed=original['table5_960C_aggregate_element_audit'][element]
    excess=F(fixed['printed_total_products_960C'])-F(fixed['feed_kg_per_kg_dry_feed'])
    assert excess>0
    for nonnegative_addition in (F(),F(1,1000),F(1,10)):
        assert excess+nonnegative_addition>0
# The illustrative balance is not silently renamed or corrected to the reported heat.
e=result['illustrative_LHV_25C_balance_MJ_kg_feed']
net=F(e['solid'])+F(e['gas'])+F(e['organic_liquid'])-F('11.3')
assert net==F(e['sum_minus_printed_feed_LHV11_3'])
assert net!=F(e['printed_inferred_requirement'])
assert e['not_reproduction_or_correction'] is True
print('PASS: source linkage, 10 exact row balances, fixed-product nonnegative-addition counterexample, and explicitly unreproduced LHV illustration; no source-wide uncertainty or atom-inventory certification')
