"""Read saved JSON/files only; no sandbox imports, EOS, codec or solver replay."""
from collections import Counter
from pathlib import Path
from hashlib import sha256
import json,time,xml.etree.ElementTree as ET

REPO=Path('/Users/wanggaoying/Desktop/brickmodel-github')
BASE=Path('/private/tmp/brick-source-wet-shared-pressure-v1')
RUN=BASE/'root/native01'
OUT=BASE/'code-review'
start=time.monotonic(); checks=[]
def check(ok,label):
    if not ok: raise AssertionError(label)
    checks.append(label)
def exact(a,b):
    return json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False)
def read(path):
    raw=path.read_bytes();return json.loads(raw),{'path':str(path),'sha256':sha256(raw).hexdigest(),'bytes':len(raw)}
final,final_file=read(RUN/'native-result.json')
parent,parent_file=read(RUN/'parent-native-result.json')
obs,obs_file=read(RUN/'pressure-observations.json')
freeze,freeze_file=read(BASE/'root/EXECUTION_FREEZE.json')
installed,installed_file=read(BASE/'root/installed-file-check.json')
check(final_file['sha256']=='6c55383e8d2063ed6c81f2126b40542ba44ee173fc1671b227573b908bfbfc53' and final_file['bytes']==46566617,'complete final file identity')
check(set(final)-set(parent)=={'inherited_parent_initial_strategy_label','new_pressure_study'} and not set(parent)-set(final),'final adds only preregistered metadata fields')
changes=[]
for key in parent:
    if not exact(final[key],parent[key]):changes.append(key)
check(changes==['pressure_strategy'],'only existing top-level value changed is strategy label')
check(exact(final['new_pressure_study'],obs),'embedded wrapper record equals separately saved observations')
check(final['inherited_parent_initial_strategy_label']==parent['pressure_strategy']==obs['inherited_parent_initial_strategy_label']=='explicit_shared_source_dry_volume','original inherited label preserved')
check(final['pressure_strategy']==obs['actual_pressure_strategy']==final['transition']['fields']['pressure_strategy']=='explicit_shared_source_wet_and_dry_volume','actual strategy comes from actual nested transition')
check(obs['parent_output_sha256']==parent_file['sha256'],'parent raw output digest binding')
check(final['status']==parent['status']==obs['status']=='completed' and obs['parent_exit_code']==0,'completed statuses and recorded parent exit 0')
parent_stdout=json.loads((RUN/'parent-stdout.log').read_text())
launch_stdout=json.loads((BASE/'root/native01-launch.log').read_text())
check(parent_stdout['status']==launch_stdout['status']=='completed','raw stdout status correspondence')
check(parent_stdout['callbacks']==len(parent['captures'])==32,'parent stdout captures correspondence')
check(obs['extra_request_cap']==16 and len(obs['extra_requests'])==8 and len(obs['wet_pairs'])==4,'8 extra requests in 4 pairs under 16 cap')
check(obs['pure_comparison_eos_attempts']==0,'comparison state_tp guard recorded zero attempts')
check(all(type(a['ordinal']) is int for a in obs['extra_requests']) and [a['ordinal'] for a in obs['extra_requests']]==list(range(1,9)),'extra request ordinals complete')
transition=final['transition']['fields']
expected_slots=((0,0),(0,2),(1,0),(1,2))
all_states=0
for index,(phase,cell) in enumerate(expected_slots):
    pair=obs['wet_pairs'][index]
    nested=transition['wet_pressure_pairs'][phase][cell]
    check(pair['pair_index']==index and pair['status']=='returned' and exact(pair['pair'],nested),f'pair {index}: nested actual row correspondence')
    body=nested['fields']; evidence=body['evidence']['fields']; attempts=evidence['attempts']
    check(body['status']=='conditional_shared_wet_pressure_enclosure' and body['reason'] is None,f'pair {index}: actual conditional result')
    check(exact(pair['endpoints'],body['endpoints']),f'pair {index}: retained input endpoints')
    for side in range(2):
        check(exact(body['endpoints'][side],transition['candidates'][side]['fields']['cell_pressure_endpoints'][phase][cell]),f'pair {index}: original candidate endpoint {side}')
    shared=body['shared_volume']['fields']
    live=final['live_cell_parameter_identities'][cell]
    check(pair['storage_object_id']==live['storage_object_id'] and pair['volume_object_id']==live['volume_object_id'] and shared['object_identity']==[live['storage_object_id'],live['volume_object_id']],f'pair {index}: retained live spatial id metadata')
    queries=[a for a in obs['extra_requests'] if a['pair_index']==index]
    check(len(queries)==len(attempts)==len(evidence['support']['fields']['requests'])==2,f'pair {index}: exact duplicate query count')
    for local,(query,attempt) in enumerate(zip(queries,attempts)):
        a=attempt['fields']; request=evidence['support']['fields']['requests'][local]
        check(query['status']=='returned' and a['failure_type'] is None and a['failure_message'] is None,f'pair {index} query {local}: successful actual return')
        check(query['provider_object_id']==a['water_object_identity'] and a['ordinal']==local,f'pair {index} query {local}: attempt/provider identity')
        check(exact([query['temperature_k'],query['pressure_pa'],query['phase']],request) and exact([a['temperature_k'],a['pressure_pa'],a['phase']],request),f'pair {index} query {local}: exact requested inputs')
        check(exact(query['water_state'],a['state']),f'pair {index} query {local}: every full WaterState field retained')
        state=a['state']; check(state['type']=='sludge_sandbox.water_properties.WaterState' and exact([state['fields']['temperature_k'],state['fields']['pressure_pa'],state['fields']['phase']],request),f'pair {index} query {local}: returned actual T/P/phase')
        all_states+=1
    check(len(body['error_parts'])==2 and body['source_certified'] is body['material_qualified'] is body['event_admitted'] is False,f'pair {index}: complete error parts and no qualification upgrade')
keys={(a['provider_object_id'],float(a['temperature_k']).hex(),float(a['pressure_pa']).hex(),a['phase']) for a in obs['extra_requests']}
check(len(keys)==obs['distinct_extra_request_keys']==4,'4 exact distinct query keys; repeats remain actual requests')
check(final['outer_seconds']==510. and final['per_trial_callback_cap']==16 and final['per_dry_path_callback_cap']==24 and final['total_callback_cap']==97,'original resource caps unchanged')
check(final['backend_constructors_started']==final['backend_constructors_completed']==final['constructor_reference_anchor_checks']==4,'four actual constructor/anchor records')
check(final['initial_energy_evaluations_attempted']==final['initial_energy_evaluations_completed']==len(final['initial_energy_attempts'])==3,'three initial energy records')
captures=final['captures']
check([c['ordinal'] for c in captures]==list(range(1,33)) and all('evaluation' in c and 'exception_type' not in c for c in captures),'32 complete successful source captures')
check(all(c['same_original_cell_storage_objects']==c['same_original_cell_volume_objects']==[True,True,True] for c in captures),'all source callbacks preserve spatial storage/volume ids')
phase_counts=dict(Counter(c['phase'] for c in captures))
check(phase_counts=={'initial_rate_probe':1,'seed':2,'approach':11,'shifted_seed':2,'coarse_dry_candidate':8,'shifted_dry_candidate':8},'source callback stage accounting')
check(exact(final['returned_candidates'],transition['candidates']),'all returned candidate records preserved')
check(final['numerical_comparison_completed'] is True and final['numerical_event_accepted'] is transition['numerical_event_accepted'] is obs['numerical_event_accepted'] is True and final['material_qualified'] is transition['material_qualified'] is False,'numeric completion/event accepted versus material false')
check(transition['cell_conditional_pressure_gates']==[[False,False,False],[False,False,False]] and transition['cell_selected_pressure_gates']==[[True,True,True],[True,True,True]],'original pressure failures retained beside new selected gates')
check(final['wall_seconds']<510. and not final.get('outer_timeout_requested',False),'saved parent runtime under original cap')
for f in freeze['files']:
    p=(REPO if f['path'].startswith(('src/','tests/')) else BASE)/f['path']
    data=p.read_bytes()
    check(sha256(data).hexdigest()==f['sha256'] and len(data)==f['bytes'],'execution frozen file '+f['path'])
check(freeze['source_tests']==freeze['installed_tests']==44 and freeze['package_files']==140,'execution freeze final test/package counts')
xml=[]
for label in ('source-fixed02','installed-fixed02'):
    p=BASE/'root'/f'{label}.xml'
    suites=[dict(s.attrib) for s in ET.parse(p).getroot().iter('testsuite')]
    check(sum(int(s['tests']) for s in suites)==44 and all(int(s['errors'])==int(s['failures'])==int(s.get('skipped','0'))==0 for s in suites),label+' actual XML 44 passed')
    xml.append({'path':str(p),'sha256':sha256(p.read_bytes()).hexdigest(),'suites':suites})
check(installed['status']=='matched' and installed['module_count']==133 and installed['package_file_count']==len(installed['files'])==140,'installed manifest 133 modules / 140 files')
check(sum(f['path'].endswith('.py') for f in installed['files'])==133,'manifest actual module count')
for f in installed['files']:
    for root_key in ('source','installed'):
        p=Path(installed[root_key])/f['path']
        check(sha256(p.read_bytes()).hexdigest()==f['sha256'],root_key+' frozen package file '+f['path'])
result={'status':'approved','scope':'Saved JSON/file structure and association audit only; no physics arithmetic, EOS, native execution, codec or solver replay', 'files':[final_file,parent_file,obs_file,freeze_file,installed_file], 'checks':len(checks),'check_labels':checks,'final_parent_changed_existing_keys':changes,'extra_requests':8,'fully_matched_water_states':all_states,'wet_pairs':4,'distinct_exact_keys':4,'comparison_guard_attempts':0,'source_captures':32,'source_stage_counts':phase_counts,'parent_wall_seconds':final['wall_seconds'],'wrapper_seconds':obs['wrapper_seconds'],'numerical_event_accepted':True,'material_qualified':False,'source_modules':133,'package_files':140,'xml':xml,'elapsed_seconds':time.monotonic()-start,'findings':[]}
(OUT/'RUN_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('check_labels','files','xml')},indent=2))
