"""Exact unit conversion only, no extrapolation or reaction-heat inference."""
import json
from pathlib import Path
from fractions import Fraction as F
r=json.loads(Path(__file__).with_name('facts.json').read_text())
assert r['qualification']['material_qualified'] is False
assert r['qualification']['reaction_heat_identified'] is False
assert r['qualification']['same_batch_GNEST2021'] is None
cp=r['thesis_table8_1'];hhv=r['ion_figure7']
assert cp['source_id']=='mendoza2016-thesis' and hhv['source_id']=='ion2026'
assert cp['quantity']=='Cp' and cp['unit']=='kJ/kg/K'
assert hhv['quantity']=='HHV' and hhv['unit']=='kJ/kg' and hhv['basis']=='dry'
assert set(cp['values'])=={'feed','HRN1','HRN2','HRN3','HRN4','HRN5'}
assert set(hhv['values'])=={'feed','char_250C','char_550C','char_700C'}
assert cp['temperature_range_C']==['-10','50']
assert all(type(v) is str and F(v)>0 for g in (cp,hhv) for v in g['values'].values())
assert cp['moisture_mass_basis_explicit_for_DSC'] is None
assert cp['reported_uncertainty'] is None and hhv['errorbar_values'] is None
print(json.dumps({'Cp_J_kg_K':{k:str(F(v)*1000) for k,v in cp['values'].items()},'HHV_MJ_kg':{k:str(F(v)/1000) for k,v in hhv['values'].items()},'reaction_heat_identified':False},indent=2))
