import json,hashlib,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
START=time.monotonic(); BASE=Path('/private/tmp/brick-source-continuation-v1/native01'); OUT=Path(__file__).parent
checks=0
def ck(v):
 global checks
 checks+=1
 assert v, checks
def decode(p):
 n=p['nodes']; cache={}
 def d(x):
  if isinstance(x,list):return [d(z) for z in x]
  if not isinstance(x,dict):return x
  if 'fraction' in x:return F(*x['fraction'])
  if 'binary64' in x:return F(float.fromhex(x['binary64']))
  if 'ref' in x:
   key=x['ref']
   if key not in cache:
    z=n[key]
    if 'fields' in z:cache[key]={k:d(v) for k,v in z['fields'].items()}
    elif 'values' in z:
     vals=d(z['values']);shape=z.get('shape',[])
     cache[key]=[vals[i:i+shape[1]] for i in range(0,len(vals),shape[1])] if len(shape)==2 else vals
    else:cache[key]=z
   return cache[key]
  return {k:d(v) for k,v in x.items()}
 return d(p['root'])
a=json.loads((BASE/'ACCEPTANCE.json').read_text()); groups={}; hashes={}
for name in ('parent','continuation'):
 ev=[]
 for p in sorted((BASE/name/'events').glob('*.json')):
  raw=p.read_bytes();hashes[str(p.relative_to(BASE))]=hashlib.sha256(raw).hexdigest(); j=json.loads(raw);ev.append((j['event'],decode(j['payload'])))
 groups[name]=ev
c=groups['continuation']; p=groups['parent']; results=[v for k,v in c if k=='ordinary_segment_returned']; ck(len(results)==2)
pause,final=results; r=final['execution']['result']; pr=pause['execution']['result']
ck(pause['status']=='paused' and final['status']=='completed');ck(r['steps'][:len(pr['steps'])]==pr['steps']);ck(r['states'][:len(pr['states'])]==pr['states']);ck(final['execution']['observations'][:len(pause['execution']['observations'])]==pause['execution']['observations'])
ck(len(pr['steps'])==1 and len(r['steps'])==4);ck(r['evaluations']==29);ck(a['runtime_before']==a['runtime_after'])
for k in ('material_qualified','full_firing_cycle','archived_resume_authorized'):ck(a[k] is False and final[k] is False)
for name,events in groups.items():
 counts=Counter(k for k,v in events)
 for event in ('heos','rhs','wet','initial_energy'):
  ck(counts[event+'_started']==counts[event+'_returned'])
 for i,(k,v) in enumerate(events):
  if k=='rhs_started':
   nk,nv=events[i+1];ck(nk=='rhs_returned');ck(v['state']==nv['state']);ck(v['time']==nv['time'])
 pc=Counter(k for k,v in p);cc=Counter(k for k,v in c)
for key,value in a['parent_counts'].items():ck(pc[key]==value)
for key,value in a['final_counts'].items():ck(pc[key]+cc[key]==value)
stationary=all(s==r['states'][0] for s in r['states']); ck(stationary)
for i,step in enumerate(r['steps']):
 s,t=r['states'][i:i+2]
 for cell in range(3):
  for j in range(4):
   change=step['face_species_mol'][cell][j]-step['face_species_mol'][cell+1][j]+step['reaction_species_mol'][cell][j]
   ck(t['amounts_mol'][cell][j]-s['amounts_mol'][cell][j]-change==0)
  change=step['face_energy_j'][cell]-step['face_energy_j'][cell+1]+step['cell_work_j'][cell]
  ck(t['internal_energy_j'][cell]-s['internal_energy_j'][cell]-change==0)
rows=final['balances'];ck(len(rows)==8)
for row in rows:
 cells=row['cell_balances'];ck(len(cells)==3)
 for key in ('inventory_residual_mol','full_inventory_residual_mol'):
  for j in range(4):ck(sum(z[key][j] for z in cells)==row[key][j])
 for key in ('energy_residual_j','full_energy_residual_j','water_balance_residual_mol','event_water_storage_roundoff_mol','fluid_mass_residual_kg'):
  ck(sum(z[key] for z in cells)==row[key])
 for cell in cells:
  for key in ('inventory_residual_mol','full_inventory_residual_mol'):ck(max(map(abs,cell[key]))<=F(float(a['original_policy']['amount_absolute_tolerance_mol'])))
  for key in ('energy_residual_j','full_energy_residual_j'):ck(abs(cell[key])<=F(float(a['original_policy']['energy_absolute_tolerance_j'])))
  ck(cell['water_balance_residual_mol']==cell['inventory_residual_mol'][0]+cell['inventory_residual_mol'][3])
# New stationary zero-ledger prefixes retain the original complete-chain residuals.
for row in rows[-4:]:
 for key in rows[-5]:
  if key not in ('time','phase'):ck(row[key]==rows[-5][key])
res={'checks':checks,'elapsed_seconds':time.monotonic()-START,'stationary_new_segment':stationary,'accepted_steps':len(r['steps']),'new_rhs':r['evaluations'],'total_rhs':a['final_counts']['rhs_returned'],'event_counts':{k:dict(Counter(e for e,v in g)) for k,g in groups.items()},'acceptance_sha256':hashlib.sha256((BASE/'ACCEPTANCE.json').read_bytes()).hexdigest(),'journal_sha256':hashes,'qualification':'saved numerical/software evidence only; no new material dynamics; no EOS or source-study decoding','balance_scope':'new segment state-minus-ledger independently exact; old whole-chain saved cell residual sums and gates, not old source study reconstruction'}
(OUT/'RESULT.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='journal_sha256'},indent=2))
