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
BASE=Path(sys.argv[1]); OUT=Path(__file__).parent; began=time.monotonic(); checks=0
def ck(v):
 global checks
 checks+=1
 assert v,checks
groups={}; hashes={}
for name in ('parent','continuous','paused'):
 events=[]
 for p in sorted((BASE/name/'events').glob('*.json')):
  raw=p.read_bytes(); hashes[str(p.relative_to(BASE))]=hashlib.sha256(raw).hexdigest();j=json.loads(raw)
  events.append((j['event'],decode(j['payload'])))
 groups[name]=events
results={k:[v for e,v in events if e=='ordinary_segment_returned'] for k,events in groups.items()}
continuous=results['continuous'][-1]; prefix,paused=results['paused']; cr=continuous['execution']['result']; pr=paused['execution']['result']
ck({k:v for k,v in cr.items() if k!='elapsed_seconds'}=={k:v for k,v in pr.items() if k!='elapsed_seconds'})
ck(continuous['execution']['observations']==paused['execution']['observations']);ck(continuous['balances']==paused['balances'])
ck(prefix['execution']['result']['steps']==pr['steps'][:1]);ck(prefix['execution']['result']['states']==pr['states'][:2]);ck(pr['evaluations']==22 and len(pr['steps'])==3)
ck(any(pr['states'][0]['internal_energy_j'][i]!=pr['states'][-1]['internal_energy_j'][i] for i in range(3)))
ck(all(s['amounts_mol']==pr['states'][0]['amounts_mol'] for s in pr['states']))
for name,events in groups.items():
 for i,(e,v) in enumerate(events):
  if e=='rhs_started':
   ne,nv=events[i+1];ck(ne=='rhs_returned');ck(v['state']==nv['state']);ck(v['time']==nv['time'])
last=[v for e,v in groups['paused'] if e=='rhs_returned'][-1]
ck(last['state']==pr['states'][-1]);ck(last['time']==pr['times_s'][-1]);obs=paused['execution']['observations'][-1]
ck(obs['role']=='accepted' and obs['state']==last['state'] and obs['time']==last['time'])
max_n=F();max_u=F();global_u=[]
for old,new,step in zip(pr['states'],pr['states'][1:],pr['steps']):
 ck(step['face_energy_j'][0]==step['face_energy_j'][-1]==0)
 for i in range(3):
  for j in range(4):
   residual=new['amounts_mol'][i][j]-old['amounts_mol'][i][j]-(step['face_species_mol'][i][j]-step['face_species_mol'][i+1][j]+step['reaction_species_mol'][i][j]);ck(abs(residual)<=F(1e-7));max_n=max(max_n,abs(residual))
  residual=new['internal_energy_j'][i]-old['internal_energy_j'][i]-(step['face_energy_j'][i]-step['face_energy_j'][i+1]+step['cell_work_j'][i]);ck(abs(residual)<=F(.001));max_u=max(max_u,abs(residual))
 du=sum(new['internal_energy_j'])-sum(old['internal_energy_j']);ck(abs(du)<=F(.001));global_u.append(du)
for row in paused['balances']:
 cells=row['cell_balances']
 for key in ('inventory_residual_mol','full_inventory_residual_mol'):
  for j in range(4):ck(sum(c[key][j] for c in cells)==row[key][j]);ck(abs(row[key][j])<=F(1e-7))
 for key in ('energy_residual_j','full_energy_residual_j'):
  ck(sum(c[key] for c in cells)==row[key]);ck(abs(row[key])<=F(.001))
 for c in cells:
  for key in ('inventory_residual_mol','full_inventory_residual_mol'):ck(max(map(abs,c[key]))<=F(1e-7))
  for key in ('energy_residual_j','full_energy_residual_j'):ck(abs(c[key])<=F(.001))
for result in (continuous,paused):
 for key in ('material_qualified','full_firing_cycle','archived_resume_authorized'):ck(result[key] is False)
# Additional native-only acceptance and serialized checkpoint checks are added after readiness.
res={'scope':'manufactured preparation' if not (BASE/'ACCEPTANCE.json').exists() else 'native saved audit','checks':checks,'elapsed_seconds':time.monotonic()-began,'stationary':False,'max_step_inventory_residual_mol':str(max_n),'max_step_energy_residual_j':str(max_u),'global_step_energy_changes_j':list(map(str,global_u)),'journal_sha256':hashes}
(OUT/('PREP_RESULT.json' if res['scope']=='manufactured preparation' else 'RESULT.json')).write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='journal_sha256'},indent=2))
