import json, time, hashlib
from dataclasses import replace
from pytest import MonkeyPatch
from test_mass_wet_storage import setup
from sludge_sandbox.deforming_solid_storage import _canonical,_digest
start=time.monotonic(); rows={}
for name in ('wet','dry','error'):
 with MonkeyPatch.context() as mp:
  st,state,calls=setup(mp)
  if name=='dry':state=replace(state,liquid_water_mol=0.)
  if name=='error':
   st=replace(st,bulk_volume_error_m3=1e-12,fluid_template=replace(st.fluid_template,envelope=replace(st.fluid_template.envelope,liquid_abs_du_dp_bound_j_mol_pa=1e-6)))
   state=st.state(state.solid_mass_kg,state.liquid_water_mol,state.gas_amounts_mol,0.)
  out=st.evaluate(state,305.)
  rows[name]={'identity':st._identity,'point_digest':_digest(out),'point':_canonical(out),'liquid_calls':len(calls)}
print(json.dumps({'elapsed_s':time.monotonic()-start,'rows':rows},indent=2))
