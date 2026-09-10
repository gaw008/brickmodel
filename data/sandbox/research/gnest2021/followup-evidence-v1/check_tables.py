"""Check printed-table arithmetic, not physical closure or source authenticity."""
import json
from fractions import Fraction as F
from pathlib import Path

record = json.loads(Path(__file__).with_name('quantitative-record.json').read_text())
assert record['source_doi'] == '10.19211/KUP9783862199815'
assert record['table5_1']['columns'] == ['ar', 'ad', 'd', 'daf']
assert record['table5_1']['units'] == 'mass percent'
assert record['table5_2']['columns'] == ['char', 'tar']
assert record['table5_2']['basis'] == 'daf; tar ash-free and excludes generated water'
rows = record['table5_1']['rows']
assert set(rows) == {'char', 'gas', 'tar', 'generated_water', 'ash', 'initial_moisture'}
assert all(len(row) == 4 for row in rows.values())
sums = [sum(F(row[i]) for row in rows.values()) for i in range(4)]
assert sums == [F(100), F('99.99'), F(100), F(100)]
elements = record['table5_2']['element_mass_percent']
assert set(elements) == set('CHNOS')
assert all(len(row) == 2 for row in elements.values())
assert [sum(F(row[i]) for row in elements.values()) for i in range(2)] == [F(100), F(100)]
gases = record['table5_3']['gas_mass_percent']
assert set(gases) == {'CO2', 'CO', 'H2', 'CH4'}
assert sum(map(F, gases.values())) == 100
# Printed feed hydrogen 3.60 percent dry; original Eq3-1, not a new fitted coefficient.
feed = record['table3_4_selected']
hhv = F(feed['measured_feed_HHV_d_MJ_kg'])
printed_lhv = F(feed['derived_feed_LHV_d_MJ_kg'])
lhv = hhv - F('0.09') * F('3.60') * F('2.44')
# Check agreement with the independently printed two-decimal LHV, not an
# assertion that this rounding interval represents experimental uncertainty.
assert abs(lhv - printed_lhv) < F('0.005'), 'printed feed LHV rounding mismatch'
print(json.dumps({'table5_1_column_sums': list(map(str, sums)), 'table5_2_CHNOS_sums': ['100', '100'], 'table5_3_gas_sum': '100', 'feed_LHV_from_printed_formula_MJ_kg': str(lhv), 'physical_closure_proven': False}, indent=2))
