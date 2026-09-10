"""Offline saved stage/rate/ledger audit. No scientific library/model imports."""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib,math
BASE=Path('/private/tmp/brick-source-liquid-column-v1/native');OUT=Path('/private/tmp/brick-source-liquid-physics-v1/native-review')
def q(v):return F(v['numerator'],v['denominator']) if isinstance(v,dict) else F(v)
checks={}
def check(k,v):checks[k]=bool(v);assert v,k
def upward(v):
 f=float(v);return math.nextafter(f,math.inf) if F(f)<v else f
raw=(BASE/'installed-step.json').read_bytes();d=json.loads(raw);check('terminal',d['status']=='completed')
r=d['run'];stages=d['completed_stage_observations'];prov=d['provenance']['base'];mobraw=(BASE/'mobility.json').read_bytes();mob=json.loads(mobraw);mh=hashlib.sha256(mobraw).hexdigest()
check('mobility_sha',d['mobility_sha256']==mh);check('run_complete',r['status']=='completed' and r['reason'] is None)
check('stage_count',len(stages)==r['evaluations_completed']==r['evaluations_attempted']==3)
check('prefix',len(r['states'])==len(r['times_s'])==2 and len(r['ledgers'])==len(r['observations'])==1)
check('material',d['material_qualified'] is False and r['material_qualified'] is False and d['provenance']['material_qualified'] is False)
l=r['ledgers'][0];dt=q(l['duration_s']);old,new=r['states']
check('stage_state_binding',[s['states'] for s in stages]==[old,l['midpoint_states'],new])
check('stage_time',[q(s['when']['seconds']) for s in stages]==[F(),dt/2,dt])
liquid_values=[]
for j,s in enumerate(stages):
 o=s['observation'];ls=o['liquid_states'];area=q(prov['face_area_m2']);width=prov['cell_widths_m']
 check(f'{j}_qualification',o['liquid_pressure_interval_scope']=='fixed_decoded_temperature' and o['full_inverse_liquid_direction_certified'] is False)
 for i,state in enumerate(ls):
  point=o['cells'][i]['inverse']['point'];mech=point['fluid']['mechanical']
  check(f'{j}_{i}_decoded',state['pressure_pa']==mech['liquid_pressure_pa']==mech['pressure_pa'] and state['temperature_k']==mech['temperature_k'] and state['inventory_mol']==s['states'][i]['liquid_water_mol'])
  check(f'{j}_{i}_pressure_error',state['pressure_error_pa']==point['pressure_error_pa'])
  check(f'{j}_{i}_saturation',state['saturation']==mech['liquid_volume_m3']/point['available_pore_volume_m3'])
 for i,face in enumerate(o['faces'][1:-1]):
  ex=face['liquid_exchange'];left,right=ls[i:i+2];relations=prov['liquid_transport']['relations'][i:i+2]
  M=[]
  for side,(state,rel) in enumerate(zip((left,right),relations)):
   check(f'{j}_{i}_{side}_mobility_source',dict(rel['source_asset_sha256'])['mobility.json']==mh and all(rel[k]==mob[k] for k in ('saturation_knots','permeability_m2','relative_permeability','viscosity_pa_s','classification','relation_kind')))
   check(f'{j}_{i}_{side}_mobility_domain',rel['temperature_range_k'][0]<=state['temperature_k']<=rel['temperature_range_k'][1] and rel['pressure_range_pa'][0]<=state['pressure_pa']<=rel['pressure_range_pa'][1] and 0<=state['saturation']<=1)
   M.append(q(mob['permeability_m2'][0])*q(mob['relative_permeability'][0])/q(mob['viscosity_pa_s'][0]))
  dp=q(left['pressure_pa'])-q(right['pressure_pa']);Q=area*dp/(q(width[i])/2/M[0]+q(width[i+1])/2/M[1]);donor=left if Q>0 else right;N=Q/q(donor['molar_volume_m3_mol']);H=N*q(donor['enthalpy_j_mol'])
  check(f'{j}_{i}_darcy',ex['volume_flow_m3_s']==float(Q) and face['liquid_mol_s']==ex['molar_flow_mol_s']==float(N) and face['liquid_enthalpy_w']==ex['enthalpy_flow_w']==float(H))
  check(f'{j}_{i}_donor',ex['donor']==('left' if Q>0 else 'right'))
  eps=q(left['pressure_error_pa'])+q(right['pressure_error_pa'])
  check(f'{j}_{i}_direction',ex['pressure_difference_error_pa']==upward(eps) and ex['direction_qualification']==('conditional_direction_resolved' if abs(dp)>eps else 'nominal_direction_not_certified') and ex['full_inverse_direction_certified'] is False)
  check(f'{j}_{i}_projection',q(face['liquid_enthalpy_projection_w'])==F(float(H))-F(float(N))*q(donor['enthalpy_j_mol']))
  check(f'{j}_{i}_energy',face['energy_w']==math.fsum([face['conduction_w'],*face['diffusive_enthalpy_w'],*face['advective_enthalpy_w'],face['liquid_enthalpy_w']]))
  liquid_values.append({'stage':j,'face':i+1,'mol_s':float(N),'enthalpy_w':float(H),'donor':ex['donor']})
 check(f'{j}_liquid_boundaries',all(f.get('liquid_mol_s',0)==0 for f in (o['faces'][0],o['faces'][-1])))
for i,(face,rate) in enumerate(zip(l['faces'],stages[1]['observation']['faces'])):
 for integ,field in [('energy_j','energy_w'),('conduction_j','conduction_w'),('liquid_mol','liquid_mol_s'),('liquid_enthalpy_j','liquid_enthalpy_w'),('liquid_enthalpy_projection_j','liquid_enthalpy_projection_w')]:
  check(f'face{i}_{integ}_dt',q(face.get(integ,0))==dt*q(rate.get(field,0)))
 for integral,field in [('gas_mol','gas_mol_s'),('diffusive_enthalpy_j','diffusive_enthalpy_w'),('advective_enthalpy_j','advective_enthalpy_w')]:check(f'face{i}_{integral}_dt',list(map(q,face[integral]))==[dt*q(x) for x in rate[field]])
 check(f'face{i}_decomposition',q(face['energy_j'])==q(face['conduction_j'])+sum(map(q,face['diffusive_enthalpy_j']))+sum(map(q,face['advective_enthalpy_j']))+q(face.get('liquid_enthalpy_j',0))+q(face['energy_decomposition_roundoff_j']))
f=l['faces'];rounding=l['roundoff'];liq=lambda face:q(face.get('liquid_mol',0))
for i,(a,b) in enumerate(zip(old,new)):
 phase=q(l['phase_water_mol'][i]);check(f'phase{i}_dt',phase==dt*q(stages[1]['observation']['cells'][i]['phase']['phase_water_mol_s']))
 check(f'cell{i}_fixed',a['solid_mass_kg']==b['solid_mass_kg'] and a['energy_model_identity']==b['energy_model_identity'])
 check(f'cell{i}_liquid',q(b['liquid_water_mol'])-q(a['liquid_water_mol'])==liq(f[i])-liq(f[i+1])-phase+q(rounding['liquid_mol'][i]))
 check(f'cell{i}_energy',q(b['internal_energy_j'])-q(a['internal_energy_j'])==q(f[i]['energy_j'])-q(f[i+1]['energy_j'])+q(rounding['energy_j'][i]))
 for k in range(3):check(f'cell{i}_gas{k}',q(b['gas_amounts_mol'][k])-q(a['gas_amounts_mol'][k])==q(f[i]['gas_mol'][k])-q(f[i+1]['gas_mol'][k])+(phase if k==2 else 0)+q(rounding['gas_mol'][i][k]))
 check(f'cell{i}_water',q(b['liquid_water_mol'])+q(b['gas_amounts_mol'][2])-q(a['liquid_water_mol'])-q(a['gas_amounts_mol'][2])==liq(f[i])-liq(f[i+1])+q(f[i]['gas_mol'][2])-q(f[i+1]['gas_mol'][2])+q(rounding['liquid_mol'][i])+q(rounding['gas_mol'][i][2]))
balances={}
for name,measure,external,err in [('U',lambda s:q(s['internal_energy_j']),-q(f[-1]['energy_j']),sum(map(q,rounding['energy_j']))),('liquid',lambda s:q(s['liquid_water_mol']),-sum(map(q,l['phase_water_mol'])),sum(map(q,rounding['liquid_mol']))),*[(name,lambda s,k=k:q(s['gas_amounts_mol'][k]),-q(f[-1]['gas_mol'][k]),sum(q(row[k]) for row in rounding['gas_mol'])) for k,name in enumerate(('O2','N2'))],('water',lambda s:q(s['liquid_water_mol'])+q(s['gas_amounts_mol'][2]),-q(f[-1]['gas_mol'][2]),sum(map(q,rounding['liquid_mol']))+sum(q(row[2]) for row in rounding['gas_mol']))]:
 change=sum(map(measure,new))-sum(map(measure,old));check('global_'+name,change==external+err);balances[name]={'change':str(change),'float_change':float(change),'contribution':str(external),'roundoff':str(err),'residual':'0'}
b=l['boundary_integral'];check('surface_single',q(b['conductive_into_cell_j'])==-q(f[-1]['conduction_j']));check('surface_defect',q(b['exact_surface_balance_defect_j'])==q(b['conductive_into_cell_j'])-q(b['convective_in_j'])-q(b['radiative_in_j']));check('surface_limit',abs(q(b['reported_surface_residual_j']))<=q(b['surface_balance_limit_j']))
probe_raw=(BASE/'source-probe.json').read_bytes();probe=json.loads(probe_raw)
check('source_probe_complete',probe['status']=='completed')
check('source_probe_initial_matches',probe['initial']==old)
check('source_probe_observation_matches_first_stage',probe['observation']==stages[0]['observation'])
result={'probe_sha256':hashlib.sha256(probe_raw).hexdigest(),'checks_passed':len(checks),'checks':checks,'input_sha256':hashlib.sha256(raw).hexdigest(),'mobility_sha256':mh,'input_path':str(BASE/'installed-step.json'),'stage_liquid_flows':liquid_values,'balances':balances,'elapsed_reported':r['elapsed_seconds'],'scope':'Saved arithmetic only, no EOS/model imports; donor liquid v/h are saved inputs, not independently re-evaluated EOS values.','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(OUT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
