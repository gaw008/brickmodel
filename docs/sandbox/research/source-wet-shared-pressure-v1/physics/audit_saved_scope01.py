import json,hashlib,time
from pathlib import Path
from fractions import Fraction as F
from audit_saved_wet import dec
start=time.monotonic();n=0

def ck(v,s):
 global n
 n+=1
 if not v:raise AssertionError(s)
p=Path('/private/tmp/brick-source-wet-shared-pressure-v1/root/native01/native-result.json');o=Path('/private/tmp/brick-source-multicell-transition-v1/root/native-result.json');raw=p.read_bytes();oldraw=o.read_bytes();ck(hashlib.sha256(raw).hexdigest()=='6c55383e8d2063ed6c81f2126b40542ba44ee173fc1671b227573b908bfbfc53','newSHA');ck(hashlib.sha256(oldraw).hexdigest()=='2660d33ec0e832e006d5adcccd8ddcf38cc314ac5e65a17830cdf2f73cbdc51d','oldSHA');r=dec(json.loads(raw));old=dec(json.loads(oldraw));t=r['transition'];ot=old['transition'];s=r['new_pressure_study']
for key in ('initial','initial_temperature_k','initial_liquid_mol','initial_gas_mol','horizon','event_policy','integration_policy','liquid_transport_configuration','initial_energy_attempts','adapter_provenance'):
 ck(r[key]==old[key],key)
ck(len(r['captures'])==len(old['captures'])==32,'32 actual callbacks')
for a,b in zip(r['captures'],old['captures']):
 for k in ('packed_input','time','evaluation','interface_modes'):
  ck(a[k]==b[k],'unchanged physical callback '+k)
 ck(a['same_original_cell_storage_objects'] and a['same_original_cell_volume_objects'],'actual callback original parameters')
for key in ('cell_endpoint_differences','cell_endpoint_gates','cell_conditional_pressure_bounds_pa','cell_conditional_pressure_gates','endpoint_differences','endpoint_gates','conditional_pressure_gates','clock_gate'):
 ck(t[key]==ot[key],'old gates and differences '+key)
for a,b in zip(t['candidates'],ot['candidates']):
 for key in ('terminal','projection','dry_result'):
  if key in a:ck(a[key]==b[key],'unchanged full candidate '+key)
ck(len(s['extra_requests'])==8 and len(s['wet_pairs'])==4 and s['pure_comparison_eos_attempts']==0,'actual additional calls')
ck(len(set((q['provider_object_id'],q['temperature_k'],q['pressure_pa'],q['phase']) for q in s['extra_requests']))==4,'4 provider query keys')
for pi,item in enumerate(s['wet_pairs']):
 pair=item['pair'];decl=pair['shared_volume'];ck(item['status']=='returned' and item['storage_object_id']==decl['object_identity'][0] and item['volume_object_id']==decl['object_identity'][1],'saved same live declaration')
 calls=[q for q in s['extra_requests'] if q['pair_index']==pi]
 ck(len(calls)==len(pair['evidence']['attempts'])==2,'two actual requests for equal reported T')
 for q,obs in zip(calls,pair['evidence']['attempts']):
  ck(q['water_state']==obs['state'] and q['provider_object_id']==obs['water_object_identity'],'actual water observation identity')
for phase,row in enumerate(t['wet_pressure_pairs']):
 ck(row[1] is None,'dry middle not wet bridge')
 selected=[]
 for i in range(3):
  v=t['shared_pressure_pairs'][phase]['bound_pa'] if i==1 else row[i]['bound_pa'];selected.append(v)
  if i!=1:ck(row[i]['endpoints']==[c['cell_pressure_endpoints'][0 if phase==0 else -1][i] for c in t['candidates']],'same actual endpoint views')
 ck(selected==t['cell_selected_pressure_bounds_pa'][phase],'all cell selected exact')
 ck([x<=F(r['event_policy']['pressure_absolute_pa']) for x in selected]==t['cell_selected_pressure_gates'][phase]==[True]*3,'original threshold all cells')
 ck(max(selected)==t['selected_pressure_bounds_pa'][phase],'max all cells')
ck(t['endpoint_gates']==[[True,True,True,False]]*2 and t['conditional_pressure_gates']==[False,False],'original pressure failures retained')
ck(t['numerical_event_accepted'] and not t['material_qualified'] and not old['transition']['numerical_event_accepted'],'new numerical-only acceptance old false unchanged')
result=dict(checks=n,elapsed_s=time.monotonic()-start,status='passed',new_sha256=hashlib.sha256(raw).hexdigest(),old_sha256=hashlib.sha256(oldraw).hexdigest(),scope='saved actual full callback equality and exact selected gates; live identity is audited recorded producer evidence, not reconstructed Python objects')
Path(__file__).with_name('SAVED_SCOPE_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
