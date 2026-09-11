"""Standard-library audit of saved execution boundaries; no model/codec import."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import pstats

root=Path('/private/tmp/brick-source-performance-v1')
out=root/'review'
result=json.loads((root/'rhs02/RESULT.json').read_bytes())
supervisor=json.loads((root/'supervised-rhs02/status.json').read_bytes())
request=json.loads((root/'root/managed-request.json').read_bytes())
manifest=json.loads((Path(request['assets_root'])/'data/sandbox/water/heos-8.0.0-rhs-v2-manifest.json').read_bytes())
checks=[]

def require(condition,name):
    assert condition,name
    checks.append(name)

events=[(p,json.loads(p.read_bytes())) for p in sorted((root/'rhs02/events').glob('*.json'))]
require([d['ordinal'] for p,d in events]==list(range(1,16)),'fifteen consecutive durable event ordinals')
expected=['heos_started','heos_kernel_returned','heos_returned']*4+['source_rhs_query_admitted','rhs_started','rhs_returned']
require([d['event'] for p,d in events]==expected,'four complete constructor chains, admission and one RHS chain')
counts=Counter(d['event'] for p,d in events)
for key,value in result['counts'].items():
    require(type(value) is int and value==counts[key],'result count matches events: '+key)
require(result['status']=='completed' and result['accepted_steps']==0 and type(result['accepted_steps']) is int
        and result['material_qualified'] is False and result['source_resume_authorized'] is False,'completed diagnostic only')
require(not (root/'rhs02/FAILURE.json').exists(),'no conflicting failure terminal')
require(supervisor['status']=='complete' and supervisor['returncode']==0 and supervisor['inputs_unchanged'] is True,'successful supervisor and frozen input state')
require(supervisor['cleanup']['leader_reaped'] is True and supervisor['cleanup']['signal_errors']==[],'supervised process reaped without cleanup errors')
require(result['request_sha256']==hashlib.sha256((root/'root/managed-request.json').read_bytes()).hexdigest(),'executed request hash')
audit=result['managed_audit']
require(audit['closed'] is True and audit['material_qualified'] is False and len(audit['rhs'])==1,'closed admission with one audited RHS')
rhs=audit['rhs'][0]
require(rhs['status']=='verified' and rhs['primary_error'] is None and rhs['exit_errors']==[],'verified scope with no primary or exit errors')
require([c['stage'] for c in rhs['checks']]==['entry']*4+['exit']*4,'all four registered kernels checked at both boundaries')
config_hash=hashlib.sha256(json.dumps(manifest['config'],sort_keys=True).encode()).hexdigest()
for check in rhs['checks']:
    require(check['status']=='verified' and check['fluid_sha256']==manifest['fluid_sha256']
            and check['config_sha256']==config_hash,'recorded complete config/fluid boundary verification')
metadata=json.loads((root/'supervised-rhs02/metadata.json').read_bytes())
require(metadata['command'][1:4]==['-I','-m','sludge_sandbox.source_managed_worker'],'isolated installed module command')
require(metadata['timeout_s']==120. and metadata['cleanup_grace_s']==1.,'original preregistered supervision budget')
require(all((root/'rhs02'/name).is_file() for name in ('request.json','case.json','profile.pstats','PROFILE.txt','RESULT.json')),'required output artifacts present')

statistics={}
for folder in ('rhs01','rhs02'):
    stats=pstats.Stats(str(root/folder/'profile.pstats'))
    functions={}
    getter_edges=[]
    for callee,entry in stats.stats.items():
        if callee[0].endswith('/_heos_kernel.py') and callee[2] in ('state_tp','_transaction'):
            functions[callee[2]]=dict(calls=entry[1],self_seconds=entry[2],cumulative_seconds=entry[3])
        if callee[0].endswith('/_heos_rhs_scope.py') and callee[2] in ('_verify','_active_for_kernel'):
            functions[callee[2]]=dict(calls=entry[1],self_seconds=entry[2],cumulative_seconds=entry[3])
        for caller,edge in entry[4].items():
            if ((caller[0].endswith('/_heos_kernel.py') and caller[2]=='_transaction') or
                (caller[0].endswith('/_heos_rhs_scope.py') and caller[2]=='_verify')) and (
                 callee[2]=='loads' or 'openssl_sha256' in callee[2]):
                getter_edges.append(dict(caller=caller,callee=callee,calls=edge[1]))
    statistics[folder]=dict(total_calls=stats.total_calls,self_total_seconds=stats.total_tt,
        functions=functions,successful_getter_verification_edges=getter_edges)
    require(functions['state_tp']['calls']==2045 and functions['_transaction']['calls']==4090,folder+': same 2045 native calls, 4090 generator resumptions')
require(rhs['native_operations']==2045==statistics['rhs02']['functions']['_active_for_kernel']['calls'],'live operation audit matches native profile')
require(statistics['rhs02']['functions']['_verify']['calls']==2,'one full entry and one full exit verification pass')
old_edges=statistics['rhs01']['successful_getter_verification_edges'];new_edges=statistics['rhs02']['successful_getter_verification_edges']
require(sorted(row['calls'] for row in old_edges)==[4090,4090],'old successful per-call config decode and fluid SHA counts')
require(sorted(row['calls'] for row in new_edges)==[8,16],'new eight config decodes and eight fluid plus eight recorded-config SHA counts')

evidence=[root/'rhs02/RESULT.json',root/'rhs02/profile.pstats',root/'supervised-rhs02/status.json',root/'supervised-rhs02/metadata.json']
report=dict(status='approved_saved_run_boundaries',checks=checks,check_count=len(checks),event_count=len(events),event_counts=dict(counts),
    actual_work=dict(provider_constructor_chains=4,new_rhs=1,native_state_calls=2045,initial_U=0,wet_collector_requests=0,accepted_steps=0),
    scope_checks=dict(entry=4,exit=4,closed=True),
    timings=dict(worker_total_seconds=result['elapsed_seconds'],reconstruction_seconds=result['reconstruction_seconds'],rhs_profiled_seconds=result['rhs_profiled_seconds'],scope_seconds=rhs['elapsed_seconds'],supervisor_seconds=supervisor['elapsed_s']),
    profile=statistics,getter_count_interpretation='Cython getter functions are not standalone pstats rows; successful verification call edges and frozen code establish 4090 config plus 4090 fluid checks before, eight config plus eight fluid checks in the managed RHS. Excludes reconstruction outside the profiled region.',
    numerical_equality_review='delegated to the other independent reviewer; not recomputed here',
    identity_limit='four registered live objects are enforced by reviewed runtime code; repeated saved kernel identity hashes describe equal implementations, not distinct persisted object IDs',
    scope='one successful diagnostic; not a completed ordinary trajectory or scientific/material certification',reviewer_eos_calls=0,
    evidence_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence})
(out/'MANAGED_RUN_BOUNDARY_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('status','check_count','event_count','actual_work','scope_checks','timings')},indent=2))
