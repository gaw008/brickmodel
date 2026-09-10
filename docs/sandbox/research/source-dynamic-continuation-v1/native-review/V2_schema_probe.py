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
BASE=Path('/private/tmp/brick-source-dynamic-continuation-v1/native02');OUT=Path(__file__).parent
es=[]
for p in sorted((BASE/'continuous/events').glob('*.json')):
 j=json.loads(p.read_text());es.append((j['event'],decode(j['payload'])))
z=es[-1][1];r=z['execution']['result']
print('RESULT', {k:v for k,v in r.items() if k not in ['states','steps']})
print('EXEC',z['execution'].keys());print('LASTOBS',z['execution']['observations'][-1].keys());print('CALL', [v for e,v in es if e=='rhs_returned'][-1].keys())
v=[v for e,v in es if e=='rhs_returned'][-1];print('EVAL',v['evaluation'].keys()); print('CELL',v['evaluation']['source_evaluation']['cells'][0].keys())
print('ROLES',[(o['ordinal'],o['role'],float(o['time']['seconds'])) for o in z['execution']['observations']]);print('INV',v['evaluation']['source_evaluation']['cells'][0]['inverse'].keys());print('FACE',v['evaluation']['source_evaluation']['faces'][1].keys());print('CP',z['execution']['committed_checkpoint'].keys());print('POLICY',z['execution']['committed_checkpoint']['policy'])
