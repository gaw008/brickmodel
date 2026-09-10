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
BASE=Path('/private/tmp/brick-source-dynamic-continuation-v1/native01'); OUT=Path(__file__).parent; started=time.monotonic();checks=0
def ck(v):
 global checks
 checks+=1
 assert v,checks
summary=json.loads((BASE/'parent/result.json').read_text());failure=json.loads((BASE/'FAILURE.json').read_text());status=json.loads((BASE.parent/'supervised-native01/status.json').read_text())
ck(status['status']=='failed' and status['returncode']==1);ck(status['cleanup']['leader_reaped']);ck(status['inputs_unchanged'])
ck(summary['status']=='completed');ck(summary['numerical_event_accepted'] is False);ck(failure['status']=='failed' and failure['exception_type']=='AssertionError')
for name in ('continuous','paused','ordinary-checkpoint.json','ACCEPTANCE.json'):ck(not (BASE/name).exists())
ck(hashlib.sha256((BASE/'parent/source-study-record.json').read_bytes()).hexdigest()=='bd137a827789ae701eaeb5accb5986da61ad26dc51551c4ad49f961e49cda7ca')
case=json.loads((BASE/'parent/case.json').read_text()); original=json.loads(Path('data/sandbox/cases/source-nonstationary-heos-v1.json').read_text());ck(case==original)
events=[];hashes={}
for path in sorted((BASE/'parent/events').glob('*.json')):
 raw=path.read_bytes();j=json.loads(raw); hashes[path.name]=hashlib.sha256(raw).hexdigest();ck(j['ordinal']==len(events)+1);events.append((j['event'],decode(j['payload'])))
counts=Counter(e for e,v in events)
for key,value in summary['counts'].items():ck(counts[key]==value)
for prefix,count in [('heos',4),('rhs',32),('wet',8),('initial_energy',3)]:ck(counts[prefix+'_started']==counts[prefix+'_returned']==count)
for i,(e,v) in enumerate(events):
 if e=='rhs_started':
  ne,nv=events[i+1];ck(ne=='rhs_returned');ck(v['state']==nv['state']);ck(v['time']==nv['time'])
 if e=='wet_started':
  ne,nv=events[i+1];ck(ne=='wet_returned');ck(v['request']==nv['request'])
ck(counts['ordinary_segment_returned']==0);ck(counts['source_trajectory_reconstructed']==0)
ck(summary['runtime_before']==summary['runtime_after'])
for key in ('material_qualified','training_eligible','resume_authorized','full_firing_cycle'):ck(summary[key] is False)
res={'status':'audit_passed_of_failed_native_attempt','checks':checks,'audit_seconds':time.monotonic()-started,'supervisor_elapsed_s':status['elapsed_s'],'parent_elapsed_s':summary['elapsed_wall_seconds'],'parent_completed':True,'numerical_event_accepted':False,'new_segments_executed':0,'checkpoint_exists':False,'counts':dict(counts),'case_sha256':hashlib.sha256((BASE/'parent/case.json').read_bytes()).hexdigest(),'parent_record_sha256':'bd137a827789ae701eaeb5accb5986da61ad26dc51551c4ad49f961e49cda7ca','journal_sha256':hashes,'scope':'No EOS or source-study decode; raw parent event projection pairing and failure scope only; gate diagnosis delegated separately.'}
(OUT/'NATIVE_FAILURE_RESULT.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='journal_sha256'},indent=2))
