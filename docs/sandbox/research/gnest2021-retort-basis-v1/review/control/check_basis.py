"""Exact conversions of printed retort values; no recovered raw measurements."""
import json
from fractions import Fraction as F
from pathlib import Path

p = Path(__file__).with_name('facts.json')
r = json.loads(p.read_text())
assert r['source_doi'] == '10.19211/KUP9783862199815'
assert r['columns'] == ['ar', 'ad', 'd', 'daf']
rows = r['printed_mass_percent']
assert set(rows) == {'char', 'gas', 'tar', 'generated_water', 'ash', 'initial_moisture'}
assert all(len(v) == 4 for v in rows.values())
factors = r['basis_factors_printed']
assert set(factors) == {'M_ar_percent', 'M_ad_percent', 'ash_d_percent'}
assert F(factors['M_ar_percent']) == F(rows['initial_moisture'][0])
assert F(factors['M_ad_percent']) == F(rows['initial_moisture'][1])
assert F(factors['ash_d_percent']) == F(rows['ash'][2])
assert rows['initial_moisture'][2:] == ['0', '0'] and rows['ash'][3] == '0'
q = F(r['rounding_assumption']['half_last_printed_decimal_percent'])
assert q == F('0.005')

def projected_interval(value, removed_percent):
    """Positive product box with independently rounded input and basis factor."""
    value, removed_percent = F(value), F(removed_percent)
    assert value > q and q < removed_percent < 100 - q
    return ((value-q)*(100-removed_percent-q)/100,
            (value+q)*(100-removed_percent+q)/100)

conversions = []
for product in ('char', 'gas', 'tar', 'generated_water'):
    values = list(map(F, rows[product]))
    for src, dst, removed in ((3,2,factors['ash_d_percent']),
                              (2,1,factors['M_ad_percent']),
                              (2,0,factors['M_ar_percent'])):
        nominal = values[src]*(100-F(removed))/100
        lo, hi = projected_interval(values[src], removed)
        observed = (values[dst]-q, values[dst]+q)
        overlap = max(lo,observed[0]) <= min(hi,observed[1])
        assert overlap, (product,src,dst)
        conversions.append(dict(product=product, source_basis=r['columns'][src],
            target_basis=r['columns'][dst], nominal_exact=str(nominal),
            printed_target=rows[product][dst], signed_nominal_minus_printed=str(nominal-values[dst]),
            conditional_rounding_interval=list(map(str,(lo,hi))), marginal_overlap=overlap))
assert len(conversions) == 12
adjustment = r['tar_adjustment']
assert adjustment['allocated_product'] == 'tar'
assert adjustment['unadjusted_recovery'] is None
assert adjustment['sign_explicitly_established'] is False
mag = F(adjustment['reported_discrepancy_magnitude_percent_daf'])
mag_d = mag*(100-F(factors['ash_d_percent']))/100
conditional_raw_daf = F(rows['tar'][3])-mag
actual = r['actual_run']; run_dry_mass = F(actual['feed_mass_g'])*(100-F(actual['initial_moisture_percent']))/100
result = dict(conversions=conversions, column_sums=[str(sum(F(v[i]) for v in rows.values())) for i in range(4)],
    adjustment_magnitude_percent_d_exact=str(mag_d),
    conditional_raw_tar_percent_daf_if_positive_correction=str(conditional_raw_daf),
    actual_run_dry_mass_g_from_printed_inputs=str(run_dry_mass),
    actual_run_initial_water_g_from_printed_inputs=str(F(actual['feed_mass_g'])-run_dry_mass),
    raw_recovery_identified=False, marginal_rounding_overlap_not_joint_covariance=True,
    material_qualified=False)
assert result['column_sums'] == ['100', '9999/100', '100', '100']
print(json.dumps(result,indent=2))
