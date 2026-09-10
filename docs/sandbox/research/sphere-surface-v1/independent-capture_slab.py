from pathlib import Path
import importlib.util,sys,json,hashlib
from dataclasses import fields,replace
from test_programmed_solid_fluid_heat import wrapped,program
from test_solid_fluid_heat import ingredients
HERE=Path('/private/tmp/brick-sphere-surface-review')
spec=importlib.util.spec_from_file_location('sludge_sandbox._review_surface_prior',HERE/'prior_programmed_solid_fluid_heat.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
ing=ingredients.__wrapped__()
def serial(out):
 return {'surface_temperature_k':out.surface_temperature_k.hex(),'conductive_into_cell_w':out.conductive_into_cell_w.hex(),'convective_in_w':out.heat.convective_in_w.hex(),'radiative_in_w':out.heat.radiative_in_w.hex(),'surface_balance_residual_w':out.surface_balance_residual_w.hex(),'surface_balance_limit_w':out.surface_balance_limit_w.hex(),'iterations':out.surface_iterations,'status':out.surface_status,'face_species':[[float(v).hex() for v in row] for row in out.rates.face_species_mol_s],'face_energy':[float(v).hex() for v in out.rates.face_energy_w]}
def cases():
 for label,h,em,k,perm in [('film',20.,0.,1.,0.),('radiation',20.,.8,1.,0.),('insulated',0.,0.,0.,0.),('zero_k_gas',20.,0.,0.,1e-15)]:
  op=wrapped(ing,convection_w_m2_k=h,emissivity=em,program=program(radiation_temperature_k=(400.,)*4 if em else (300.,)*4))
  op=replace(op,base_model=replace(op.base_model,transport=replace(op.transport,conductivities_w_m_k=(k,),permeability_m2=(perm,))))
  prior=m.ProgrammedSolidFluidHeat(**{f.name:getattr(op,f.name) for f in fields(m.ProgrammedSolidFluidHeat) if f.init})
  state=prior.base_model.state_from_temperatures([[2.,0.,0.,.01]],[300.])
  yield label,prior,op,state
if __name__=='__main__':
 records=[]
 for label,prior,op,state in cases():
  for t in [0.,.025,.05,.075,.1,.125,.15]:records.append({'case':label,'time_s':t,'expected':serial(prior.evaluate(state,t))})
 result={'baseline_commit':(HERE/'BASELINE_COMMIT.txt').read_text().strip(),'old_file_sha256':hashlib.sha256((HERE/'prior_programmed_solid_fluid_heat.py').read_bytes()).hexdigest(),'records':records,'scope':'4dry liquid-zero slab boundary modes,7program times each; no native liquid EOS'}
 (HERE/'SLAB_GOLDEN.json').write_text(json.dumps(result,indent=2)+'\n');print('28 golden records captured')
