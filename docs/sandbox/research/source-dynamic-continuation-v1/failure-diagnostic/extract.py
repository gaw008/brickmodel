"""Standard-library projection of one actual final event; no solver import."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,time
began=time.monotonic()
root=Path('/private/tmp/brick-source-dynamic-continuation-v1/native01/parent')
path=root/'events/000111.json';raw=path.read_bytes();event=json.loads(raw);g=event['payload'];nodes=g['nodes']
def node(x):return nodes[x['ref']]
def field(x,k):return node(x)['fields'][k]
def items(x):return node(x)['values']
def scalar(x):
 if type(x) is dict and 'binary64' in x:return float.fromhex(x['binary64'])
 if type(x) is dict and 'fraction' in x:return F(*x['fraction'])
 return x
def simple(x):
 if type(x) is dict and 'ref' in x:
  n=node(x)
  if 'values' in n:return [simple(v) for v in n['values']]
  return {'type':n['type'],**{k:simple(v) for k,v in n.get('fields',{}).items()}}
 s=scalar(x)
 return {'fraction':str(s),'approx':float(s)} if type(s) is F else s
transition=field(g['root'],'result')
names=['status','numerical_event_accepted','clock_distance_upper_s','clock_gate','endpoint_differences','endpoint_gates','conditional_pressure_bounds_pa','conditional_pressure_gates','pressure_strategy','cell_endpoint_differences','cell_endpoint_gates','cell_conditional_pressure_bounds_pa','cell_conditional_pressure_gates','cell_selected_pressure_bounds_pa','cell_selected_pressure_gates']
out={k:simple(field(transition,k)) for k in names}
candidates=items(field(transition,'candidates'))
out['event_policy']=simple(field(candidates[0],'event_policy'))
out['wet_pairs']=[]
for phase_index,row in enumerate(items(field(transition,'wet_pressure_pairs'))):
 for cell,pair in enumerate(items(row)):
  if pair is None:continue
  result={'phase_index':phase_index,'cell':cell}
  for k in ['status','reason','residual_interval_m3','compliance_lower_m3_pa','root_difference_bound_pa','joint_bound_pa','independent_bound_pa','bound_pa','error_parts']:
   result[k]=simple(field(pair,k))
  evidence=field(pair,'evidence');result['support']=simple(field(evidence,'support'))
  result['endpoints']=[]
  for endpoint in items(field(pair,'endpoints')):
   inverse=field(endpoint,'inverse');point=field(inverse,'point');fluid=field(point,'fluid');mechanical=field(fluid,'mechanical')
   detail={'state':simple(field(endpoint,'state')),'inverse':{k:simple(v) for k,v in node(inverse)['fields'].items() if k!='point'},'point':{k:simple(v) for k,v in node(point)['fields'].items() if k not in ['fluid','model_identity','source_ids']},'mechanical':{k:simple(v) for k,v in node(mechanical)['fields'].items() if k not in ['source_asset_sha256','source_ids','model_identity']},'fluid_pressure_error_bound_pa':simple(field(fluid,'pressure_error_bound_pa'))}
   result['endpoints'].append(detail)
  out['wet_pairs'].append(result)
out['dry_pairs']=[{k:simple(field(pair,k)) for k in ['bound_pa','status']} for pair in items(field(transition,'shared_pressure_pairs'))]
out['input']={'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'study_sha256':hashlib.sha256((root/'source-study-record.json').read_bytes()).hexdigest()}
out['elapsed_seconds']=time.monotonic()-began;out['eos_calls']=0;out['full_study_decodes']=0
Path(__file__).with_name('EXTRACT.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['wet_pairs','event_policy','endpoint_differences','cell_endpoint_differences','cell_conditional_pressure_bounds_pa']},indent=2))
for p in out['wet_pairs']:
 print('PAIR',p['phase_index'],p['cell'],'status',p['status'],'reason',p['reason'],'joint',p['joint_bound_pa'])
 for side,part in enumerate(p['error_parts']):print('PART',side,{k:part[k] for k in ['actual_fluid_error_pa','saved_volume_residual_m3','report_to_root_bound_pa','retained_report_error_pa','original_temperature_error_pa','added_temperature_error_pa','machine_residual_bound_m3']})
