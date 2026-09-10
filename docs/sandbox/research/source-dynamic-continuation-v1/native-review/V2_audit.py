import json,hashlib,time,sys
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
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
BASE=Path('/private/tmp/brick-source-dynamic-continuation-v1/native02');OUT=Path(__file__).parent;began=time.monotonic();checks=0
def ck(v):
 global checks
 checks+=1
 assert v,checks
failure=json.loads((BASE/'FAILURE.json').read_text());status=json.loads((BASE.parent/'supervised-native02/status.json').read_text());parent=json.loads((BASE/'parent/result.json').read_text())
ck(status['returncode']==1 and status['inputs_unchanged'] and status['cleanup']['leader_reaped']);ck(parent['numerical_event_accepted'] is True)
for name in ('paused','ordinary-checkpoint.json','ACCEPTANCE.json'):ck(not (BASE/name).exists())
groups={};hashes={}
for branch in ('parent','continuous'):
 ev=[]
 for path in sorted((BASE/branch/'events').glob('*.json')):
  raw=path.read_bytes();j=json.loads(raw);hashes[str(path.relative_to(BASE))]=hashlib.sha256(raw).hexdigest();ck(j['ordinal']==len(ev)+1);ev.append((j['event'],decode(j['payload'])))
 groups[branch]=ev
 for i,(e,v) in enumerate(ev):
  if e=='rhs_started':
   ne,nv=ev[i+1];ck(ne=='rhs_returned');ck(v['state']==nv['state']);ck(v['time']==nv['time'])
counts=Counter(e for g in groups.values() for e,v in g)
for key,value in failure['total_known_actual_counts'].items():ck(counts[key]==value)
ck(counts['rhs_started']==counts['rhs_returned']==53);ck(counts['heos_returned']==8)
ret=[v for e,v in groups['continuous'] if e=='ordinary_segment_returned'];ck(len(ret)==1);z=ret[0];r=z['execution']['result'];obs=z['execution']['observations'];calls=[v for e,v in groups['continuous'] if e=='rhs_returned']
ck(z['status']=='resource_limit' and z['reason']=='wall_time_limit');ck(len(r['steps'])==2 and len(r['states'])==3 and r['evaluations']==21 and r['attempted_trials']==3);ck(z['execution']['checkpoint'] is None)
ck(r['elapsed_seconds']>180);ck(z['execution']['committed_checkpoint']['problem']['policy']['maximum_wall_seconds']==180)
accepted=[(i,o) for i,o in enumerate(obs) if o['role']=='accepted'];ck(len(accepted)==2);ix,o=accepted[-1];ck(o['state']==r['states'][-1] and o['time']==r['times_s'][-1]);ck(calls[ix]['state']==o['state'] and calls[ix]['time']==o['time'])
ck(len(obs)-ix-1==6);ck(obs[-1]['role']=='right_second');ck(obs[-1]['time']!=r['times_s'][-1])
first=calls[0]['evaluation']['source_evaluation'];last=calls[ix]['evaluation']['source_evaluation']
dt=[];et=[]
for a,b in zip(first['cells'],last['cells']):
 ia,ib=a['inverse'],b['inverse'];dt.append(ib['point']['fluid']['mechanical']['temperature_k']-ia['point']['fluid']['mechanical']['temperature_k']);et.append(ia['temperature_error_bound_k']+ib['temperature_error_bound_k'])
ck(any(abs(t)>e for t,e in zip(dt,et)));ck(any(f['shared_evaluation']['conduction_w']!=0 for f in first['faces'][1:-1]))
maxu=F();globaldu=[]
for a,b,step in zip(r['states'],r['states'][1:],r['steps']):
 ck(a['amounts_mol']==b['amounts_mol']);ck(step['face_energy_j'][0]==step['face_energy_j'][-1]==0)
 for i in range(3):
  for j in range(4):ck(b['amounts_mol'][i][j]-a['amounts_mol'][i][j]==step['face_species_mol'][i][j]-step['face_species_mol'][i+1][j]+step['reaction_species_mol'][i][j])
  residual=b['internal_energy_j'][i]-a['internal_energy_j'][i]-step['face_energy_j'][i]+step['face_energy_j'][i+1]-step['cell_work_j'][i];ck(abs(residual)<=F(.001));maxu=max(maxu,abs(residual))
 du=sum(b['internal_energy_j'])-sum(a['internal_energy_j']);ck(abs(du)<=F(.001));globaldu.append(du)
for row in z['balances']:
 for key in ('inventory_residual_mol','full_inventory_residual_mol'):
  for j in range(4):ck(sum(c[key][j] for c in row['cell_balances'])==row[key][j]);ck(abs(row[key][j])<=F(1e-7))
 for key in ('energy_residual_j','full_energy_residual_j'):ck(sum(c[key] for c in row['cell_balances'])==row[key]);ck(abs(row[key])<=F(.001))
for key in ('material_qualified','full_firing_cycle','archived_resume_authorized'):ck(z[key] is False)
res={'checks':checks,'audit_seconds':time.monotonic()-began,'status':'partial_native_prefix_verified_not_complete','counts':dict(counts),'accepted_steps':2,'attempted_trials':3,'accepted_end_seconds':str(r['times_s'][-1]['seconds']),'accepted_end_float':float(r['times_s'][-1]['seconds']),'segment_elapsed_seconds':float(r['elapsed_seconds']),'temperature_changes_k':list(map(float,dt)),'temperature_bound_sums_k':list(map(float,et)),'energy_changes_j':[float(b-a) for a,b in zip(r['states'][0]['internal_energy_j'],r['states'][-1]['internal_energy_j'])],'max_step_U_residual_j':str(maxu),'global_step_U_changes_j':list(map(str,globaldu)),'unaccepted_tail_callbacks':6,'balance_rows':len(z['balances']),'journal_sha256':hashes}
(OUT/'V2_RESULT.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='journal_sha256'},indent=2))
