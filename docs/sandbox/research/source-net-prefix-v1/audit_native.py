"""Stdlib-only passive native singleton prefix audit; no production imports."""
from fractions import Fraction as F
from pathlib import Path
import json,hashlib,time
BASE=Path('/Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research')
OUT=Path(__file__).parent
NEW=Path('/private/tmp/brick-source-net-prefix-v1/root/native-prefix-result.json')
NATIVE=BASE/'exact-source-column-v1/native-result.json';AUDIT=BASE/'exact-source-column-v1/native-audit.json';PANEL=BASE/'source-net-panel-v1/native-replay-result.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dec(x):
 if isinstance(x,list):return [dec(v) for v in x]
 if isinstance(x,dict):
  if set(x)=={'numerator','denominator'}:return F(x['numerator'],x['denominator'])
  if set(x)=={'type','fields'}:return dec(x['fields'])
  if 'dtype' in x and 'values' in x:return dec(x['values'])
  return {k:dec(v) for k,v in x.items()}
 return x
def flat(a):return [v for r in a for v in r] if a and isinstance(a[0],list) else a
count=0
def ck(ok,label):
 global count
 count+=1
 if not ok:raise AssertionError(label)
start=time.monotonic()
for p,h in [(NEW,'8ca3d79c533801f70002b3ad6bace09e84446c87e62d9bd4233d8fce57fc95e0'),(NATIVE,'033dccd09ed268eeb2ce9570a37d52f66d4eb5da18b68f2f44a89bd01054c4f2'),(AUDIT,'c705d9410458690d0a8379da59e5a7c86a01fd4f59e2897699a5616e55c1914d'),(PANEL,'b1652b5b9c0e6887592bee70a0927637df78ea4213eb1411c4ffc87bd274a643')]:ck(sha(p)==h,'input hash')
r=dec(json.loads(NEW.read_text()));n=dec(json.loads(NATIVE.read_text()));old=dec(json.loads(PANEL.read_text()))
ck(r['status']=='completed' and len(r['trials'])==7,'terminalseven')
ck(r['original_policy']==n['policy'],'original policy unchanged')
maxn=maxu=F();stats=[]
for k,(t,prior) in enumerate(zip(r['trials'],old['trials'])):
 for key in ('capture_indices','original_trial','sample_bindings'):ck(t[key]==prior[key],f'{k} {key}')
 c,m=[n['captures'][i] for i in t['capture_indices']];s=c['packed_input'];e=m['evaluation'];rates=e['rates'];first=c['evaluation']['rates'];p=t['prefix'];a=t['singleton_audit'];L=p['ledger'];h=F(t['original_trial']['h']);origin=F(t['original_trial']['start'])
 ck(c['time']['seconds']==origin and m['time']['seconds']==origin+h/2 and p['end']['seconds']==origin+h,'exactclock')
 ck(L['start_s']==c['time'] and L['end_s']==p['end'],'ledgerclock')
 ck(t['operator_identity']==c['evaluation']['operator_identity']==e['operator_identity'],'operator')
 ck(t['energy_identity']==s['energy_model_identity']==p['raw_state']['energy_model_identity'],'energy identity')
 ck(all(x['solid_mass_kg']==t['fixed_dry_mass_kg'][i:i+1] for i,x in enumerate(e['source_states'])),'fixed kg')
 ck(p['policy']==r['original_policy'] and dict(p['policy_binding'])==p['policy'],'policy frozen')
 exact={};represented={}
 mapping={'face_species_mol_s':'face_species_mol','face_energy_w':'face_energy_j','reaction_species_mol_s':'reaction_species_mol','cell_power_w':'cell_work_j'}
 for name,values,errors in p['integrals']:
  expected=[h*F(v) for v in flat(rates[name])];rep=[F(float(v)) for v in expected]
  ck(values==expected,'exact midpoint integral');ck(errors==[v-x for v,x in zip(rep,expected)],'integral signed projection');ck(flat(L[mapping[name]])==[float(v) for v in expected],'represented integral')
  tol=F(p['policy']['energy_absolute_tolerance_j'] if name in ('face_energy_w','cell_power_w') else p['policy']['amount_absolute_tolerance_mol'])
  ck(all(abs(v)<=tol for v in errors),'integral budget');exact[name]=expected;represented[name]=rep
 ck(len(exact)==4 and sum(map(len,exact.values()))==35,'all35 components')
 for i in range(3):ck(exact['reaction_species_mol_s'][4*i]==-exact['reaction_species_mol_s'][4*i+3] and represented['reaction_species_mol_s'][4*i]==-represented['reaction_species_mol_s'][4*i+3],'phasepair')
 for energy in (False,True):
  before=s['internal_energy_j'] if energy else flat(s['amounts_mol']);after=p['raw_state']['internal_energy_j'] if energy else flat(p['raw_state']['amounts_mol']);face='face_energy_w' if energy else 'face_species_mol_s';local='cell_power_w' if energy else 'reaction_species_mol_s';width=1 if energy else 4
  de=[exact[face][i]-exact[face][i+width]+exact[local][i] for i in range(len(before))];dr=[represented[face][i]-represented[face][i+width]+represented[local][i] for i in range(len(before))]
  es=[];full=[]
  for v,w,d,f in zip(before,after,dr,de):
   ck(w==float(F(v)+d),'single state projection');es.append(F(w)-F(v)-d);full.append(F(w)-F(v)-f)
  suffix='j' if energy else 'mol';kind='energy' if energy else 'inventory'
  ck(p['state_roundoff_'+suffix]==es and p['full_residual_'+suffix]==full,'state/full residual')
  ck(a['cumulative_'+kind+'_exchange_'+suffix]==dr and a['cumulative_exact_'+kind+'_exchange_'+suffix]==de,'singleton exact/represented cumulative')
  ck(a[kind+'_residual_'+suffix]==es and a['full_'+kind+'_residual_'+suffix]==full,'singleton residual')
  tol=F(p['policy']['energy_absolute_tolerance_j'] if energy else p['policy']['amount_absolute_tolerance_mol']);ck(all(abs(x)<=tol for x in es+full),'state full budgets')
  if energy:maxu=max(maxu,*map(abs,full));ck(sum(F(v) for v in after)-sum(F(v) for v in before)==exact[face][0]-exact[face][-1]+sum(full),'global U')
  else:
   maxn=max(maxn,*map(abs,full))
   for js in ((1,),(2,),(0,3)):
    ck(sum((F(after[4*i+j])-F(before[4*i+j]) for i in range(3) for j in js),F())==sum((exact[face][j]-exact[face][12+j] for j in js),F())+sum((full[4*i+j] for i in range(3) for j in js),F()),'global gas/water')
 for q,row in zip(prior['inventory_polynomials'],p['minima']):
  nn,rr,qq=q['initial'],q['linear'],q['quadratic'];pts=[F(),h]
  if qq>0 and 0 < -rr/(2*qq) < h:pts.append(-rr/(2*qq))
  value,at=min((nn+rr*x+qq*x*x,x) for x in pts)
  ck(row==[q['family'],q['cell'],q['index'],value,at] and value>0,'exact positive minimum')
 faces=e['source_evaluation']['faces'];firstfaces=c['evaluation']['source_evaluation']['faces'];rev=[]
 for i,(f,d) in enumerate(zip(faces,p['face_diagnostics'])):
  ck(d['face_id']==i,'face id')
  ck(('liquid_mol_s' in f)==('liquid_mol' in d),'liquid diagnostic schema')
  if 'liquid_mol_s' not in f:ck(i in (0,3) and rates['face_species_mol_s'][i][0]==0.,'gas-only boundary zero liquid')
  for src,dst in [('gas_mol_s','gas_mol'),('diffusive_enthalpy_w','diffusive_enthalpy_j'),('advective_enthalpy_w','advective_enthalpy_j')]:ck(d[dst]==[h*F(x) for x in f[src]],'face vector diagnostic')
  for src,dst in [('energy_w','energy_j'),('conduction_w','conduction_j'),('liquid_mol_s','liquid_mol'),('liquid_enthalpy_w','liquid_enthalpy_j'),('liquid_enthalpy_projection_w','liquid_enthalpy_projection_j')]:ck(d.get(dst,F())==h*F(f.get(src,F())),'face scalar exact diagnostic')
  ck(d['energy_decomposition_roundoff_j']==h*(F(f['energy_w'])-F(f['conduction_w'])-sum(map(F,f['diffusive_enthalpy_w']))-sum(map(F,f['advective_enthalpy_w']))-F(f.get('liquid_enthalpy_w',F()))),'decomposition')
  initial=F(firstfaces[i].get('liquid_mol_s',F()));final=2*F(f.get('liquid_mol_s',F()))-initial
  if initial*final<0:rev.append(i)
 ck(rev==p['liquid_direction_reversal_faces'],'affine reversal indicators')
 ck(p['status']=='strictly_positive_numerical_prefix' and t['material_qualified'] is False and t['physical_trajectory_or_event_admitted'] is False,'qualification')
 stats.append({'trial_status':t['original_trial']['status'],'h':str(h)})
result={'status':'passed','checks':count,'trials':7,'shared_integral_values':245,'state_values':105,'inventory_minima':84,'face_diagnostics':28,'max_full_inventory_residual_mol':str(maxn),'max_full_inventory_residual_float':float(maxn),'max_full_energy_residual_j':str(maxu),'max_full_energy_residual_float':float(maxu),'elapsed_s':time.monotonic()-start,'trials_summary':stats,'sha256':{str(x):sha(x) for x in (NEW,NATIVE,AUDIT,PANEL)},'scope':'Seven independent saved affine singleton prefixes; no concatenated trajectory, EOS, event or ODE step acceptance.'}
(OUT/'NATIVE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
