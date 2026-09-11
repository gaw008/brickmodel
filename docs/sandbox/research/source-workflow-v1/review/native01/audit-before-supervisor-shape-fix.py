"""Independent standard-library audit of the one durable native attempt.

Raw DAGs remain data. No application import, reconstruction, callable replay or
EOS. Full numerical result/observation comparison omits only result elapsed.
"""
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import time

ROOT = Path('/private/tmp/brick-source-workflow-v1')
RUN = ROOT/'native01'
OUT = Path(__file__).parent
started = time.monotonic()
checks = []
def require(ok, label):
    assert ok, label
    checks.append(label)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def exact(value):
    return F(value)


class Node:
    def __init__(self, kind, values):
        self._kind, self._fields = kind, values
    def __getattr__(self, name):
        return self._fields[name]


def decode_graph(graph):
    require(graph['schema'] == 'source_run_raw_projection_v1', 'raw graph schema')
    cache, visiting = {}, set()
    def visit(value):
        if not isinstance(value, dict):
            return value
        if set(value) == {'binary64'}:
            result = float.fromhex(value['binary64'])
            require(math.isfinite(result), 'finite saved float')
            return result
        if set(value) == {'fraction'}:
            n,d = value['fraction']
            require(type(n) is int and type(d) is int and d > 0 and math.gcd(n,d)==1, 'canonical saved fraction')
            return F(n,d)
        require(set(value) == {'ref'}, 'closed raw reference')
        key = value['ref']
        if key in cache:
            return cache[key]
        require(key not in visiting, 'acyclic requested raw data')
        visiting.add(key)
        item = graph['nodes'][key]
        kind = item['type']
        if kind in ('builtins.tuple', 'builtins.list'):
            result = tuple(visit(x) for x in item['values'])
        elif kind in ('builtins.dict', 'builtins.mappingproxy'):
            result = {k:visit(v) for k,v in item['fields'].items()}
        else:
            values = {k:visit(v) for k,v in item.get('fields',{}).items()}
            if 'values' in item:
                values.update(values=tuple(visit(v) for v in item['values']))
            for k,v in item.items():
                if k not in ('type','fields','values'):
                    # Only array shape/dtype, empty-field metadata and passive
                    # live-reference identity/modes are present in requested nodes.
                    values[k] = visit(v) if isinstance(v,dict) else v
            result = Node(kind, values)
        visiting.remove(key)
        cache[key] = result
        return result
    return visit(graph['root'])


def signature(value, *, skip_elapsed=False):
    """Type-sensitive full field projection; no wildcard numeric/identity skip."""
    if isinstance(value, Node):
        fields = value._fields
        if skip_elapsed and value._kind == 'sludge_sandbox.exact_integration.ExactIntegrationResult':
            fields = {k:v for k,v in fields.items() if k != 'elapsed_seconds'}
        return ('node', value._kind, tuple((k,signature(v,skip_elapsed=skip_elapsed)) for k,v in sorted(fields.items())))
    if isinstance(value, dict):
        return ('dict', tuple((k,signature(v,skip_elapsed=skip_elapsed)) for k,v in sorted(value.items())))
    if isinstance(value, (list,tuple)):
        return (type(value).__name__, tuple(signature(v,skip_elapsed=skip_elapsed) for v in value))
    if type(value) is float:
        return ('float',value.hex())
    if type(value) is F:
        return ('fraction',value.numerator,value.denominator)
    return (type(value).__name__,value)


events, counts, leases, outputs, rhs = {}, {}, {}, {}, {}
for branch, expected in [('parent',113),('continuous',60),('paused',63)]:
    paths = sorted((RUN/branch/'events').glob('*.json'))
    require(len(paths)==expected, branch+' complete event count')
    loaded = [json.loads(p.read_bytes()) for p in paths]
    require([x['ordinal'] for x in loaded] == list(range(1,expected+1)), branch+' monotonic event ordinals')
    events[branch] = loaded
    counts[branch] = Counter(x['event'] for x in loaded)
    require(not any('failed' in x['event'] or x['event']=='request_blocked' for x in loaded),branch+' no failed event')
    leases[branch] = [decode_graph(x['payload']) for x in loaded if x['event']=='managed_lease_closed']
    outputs[branch] = [decode_graph(x['payload']) for x in loaded if x['event']=='ordinary_segment_returned']
    rhs[branch] = [decode_graph(x['payload']) for x in loaded if x['event']=='rhs_returned']
    for key,n in [('rhs',32 if branch=='parent' else 22),('heos',4),
                  ('initial_energy',3 if branch=='parent' else 0),('wet',8 if branch=='parent' else 0)]:
        require(counts[branch][key+'_started']==counts[branch][key+'_returned']==n,branch+' paired '+key)
    require(counts[branch]['heos_kernel_returned']==4,branch+' kernel returns')
    require(counts[branch]['managed_lease_started']==counts[branch]['managed_lease_closed']==(2 if branch=='paused' else 1),branch+' paired leases')
    current=None; rhs_in_lease=[]
    for event in loaded:
        if event['event']=='managed_lease_started':
            require(current is None,branch+' lease not nested')
            current=0
        elif event['event']=='rhs_returned':
            require(current is not None,branch+' RHS inside lease')
            current+=1
        elif event['event']=='managed_lease_closed':
            rhs_in_lease.append(current); current=None
        elif event['event']=='ordinary_segment_returned':
            require(current is None,branch+' result after lease closed')
    require(current is None,branch+' final lease closed')
    require(rhs_in_lease==({'parent':[32],'continuous':[22],'paused':[8,14]}[branch]),branch+' lease actual RHS counts')
    for audit,n in zip(leases[branch],rhs_in_lease):
        require(audit['status']=='closed' and audit['primary_error'] is None and audit['secondary_errors']==(),branch+' clean close')
        a=audit['audit']
        require(a['closed'] is True and a['material_qualified'] is False and len(a['rhs'])==n,branch+' closed audit count')
        for entry in a['rhs']:
            require(entry['status']=='verified' and entry['primary_error'] is None and entry['exit_errors']==(),branch+' RHS verification')
            require([c['stage'] for c in entry['checks']]==['entry']*4+['exit']*4,branch+' all 4 providers entry/exit')
            require(all(c['status']=='verified' for c in entry['checks']),branch+' all provider checks verified')

continuous=outputs['continuous'][0]
prefix,finished=outputs['paused']
require(continuous.status==finished.status=='completed' and prefix.status=='paused','actual result states')
require(signature(continuous.execution.result,skip_elapsed=True)==signature(finished.execution.result,skip_elapsed=True),'full integration result equality except elapsed')
require(signature(continuous.execution.observations)==signature(finished.execution.observations),'complete 22 numerical observations equal')
require(signature(continuous.balances)==signature(finished.balances),'all seven saved cumulative balance rows equal')
require(signature(prefix.execution.result.steps)==signature(finished.execution.result.steps[:1]),'pause exact first accepted step')
require(signature(prefix.execution.observations)==signature(finished.execution.observations[:8]),'pause exact first eight observations')
require(len(prefix.execution.result.steps)==1 and len(finished.execution.result.steps)==3,'actual 1 and 3 steps')
require(prefix.execution.result.evaluations==8 and finished.execution.result.evaluations==22 and finished.execution.result.rejected_trials==0,'actual callback and rejection counters')
require(signature(tuple(x['evaluation'] for x in rhs['continuous']))==signature(tuple(x['evaluation'] for x in rhs['paused'])),'complete raw source RHS numerical observations equal')
for branch,result in [('continuous',continuous),('paused',finished)]:
    require(len(result.execution.observations)==len(rhs[branch])==22,branch+' no repeated pause physical callback')
    for observed,physical in zip(result.execution.observations,rhs[branch]):
        require(signature(observed.state)==signature(physical['state']),branch+' every numerical observation binds raw input')
        require(signature(observed.time)==signature(physical['time']),branch+' every observation time binds raw input')
        require(signature(observed.rates)==signature(physical['evaluation'].rates),branch+' every observation binds actual returned rates')
    require(result.material_qualified is result.full_firing_cycle is result.archived_resume_authorized is False,branch+' qualifications remain false')
    require(result.execution.result.elapsed_seconds<180 and result.cumulative_outer_seconds<510,branch+' original wall limits')

numerical=finished.execution.result
start,end=numerical.times_s[0].seconds,numerical.times_s[-1].seconds
require(end-start==F(3,64),'exact new interval 3/64 s')
require(all(b.seconds-a.seconds==F(1,64) for a,b in zip(numerical.times_s,numerical.times_s[1:])),'original 1/64 step sizes')
config=json.loads((RUN/'case.json').read_bytes())
policy=config['integration_policy']
u_tol=F(policy['energy_absolute_tolerance_j']); n_tol=F(policy['amount_absolute_tolerance_mol'])
global_changes=[]; local_residuals=[]
for old,new,ledger in zip(numerical.states,numerical.states[1:],numerical.steps):
    require(signature(old.amounts_mol)==signature(new.amounts_mol),'all inventories unchanged')
    face=list(map(F,ledger.face_energy_j.values)); work=list(map(F,ledger.cell_work_j.values))
    require(face[0]==face[-1]==0 and all(v==0 for v in work),'closed boundary and zero external work')
    require(any(v!=0 for v in face[1:-1]),'actual nonzero interior integrated heat')
    residual=[F(b)-F(a)-(face[i]-face[i+1]+work[i]) for i,(a,b) in enumerate(zip(old.internal_energy_j.values,new.internal_energy_j.values))]
    require(all(abs(v)<=u_tol for v in residual),'independent per-cell step energy residual')
    delta=sum(map(F,new.internal_energy_j.values))-sum(map(F,old.internal_energy_j.values))
    require(abs(delta)<=u_tol,'independent global step energy residual')
    global_changes.append(delta); local_residuals.append(residual)
require(len(finished.balances)==7,'seven saved whole-chain balance rows')
for balance in finished.balances:
    require(abs(balance.full_energy_residual_j)<=u_tol and all(abs(v)<=n_tol for v in balance.full_inventory_residual_mol),'saved whole-chain N/U residual gate')
    for cell in balance.cell_balances:
        require(abs(cell.full_energy_residual_j)<=u_tol and all(abs(v)<=n_tol for v in cell.full_inventory_residual_mol),'saved whole-chain cell N/U gate')
first=rhs['paused'][0]['evaluation'].source_evaluation
last=rhs['paused'][-1]['evaluation'].source_evaluation
dt=[]; et=[]
for a,b in zip(first.cells,last.cells):
    dt.append(F(b.inverse.point.fluid.mechanical.temperature_k)-F(a.inverse.point.fluid.mechanical.temperature_k))
    et.append(F(a.inverse.temperature_error_bound_k)+F(b.inverse.temperature_error_bound_k))
require(any(abs(d)>e for d,e in zip(dt,et)),'actual temperature change exceeds paired original inverse bounds')
require(any(f.shared_evaluation.conduction_w!=0 for f in first.faces[1:-1]),'actual initial internal conduction')

acceptance_raw=(RUN/'ACCEPTANCE.json').read_bytes(); acceptance=json.loads(acceptance_raw)
require(acceptance['global_energy_changes_j']==list(map(float,global_changes)),'published global balances equal independent values')
require(acceptance['temperature_change_k']==list(map(float,dt)) and acceptance['paired_inverse_temperature_bounds_k']==list(map(float,et)),'published temperature values equal independent values')
actual={key:sum(counts[b][key] for b in counts) for key in ('rhs_started','rhs_returned','heos_started','heos_kernel_returned','heos_returned','initial_energy_started','initial_energy_returned','wet_started','wet_returned')}
require(actual==acceptance['total_actual_counts'],'aggregate counts from event names equal publication')
require(actual['rhs_started']==76<=97 and actual['wet_started']==8<=16,'original cumulative caps')
require(acceptance['elapsed_seconds']<510,'original full-workflow time')
parent=json.loads((RUN/'parent/result.json').read_bytes())
transition=decode_graph(next(x['payload'] for x in events['parent'] if x['event']=='transition_returned'))['result']
require(transition.numerical_event_accepted is True and transition.material_qualified is False,'actual parent transition acceptance and scope')
require(parent['status']=='completed' and parent['numerical_event_accepted'] is True,'parent sealed result acceptance')
require(start==transition.candidates[1].end.seconds,'ordinary start bound to actual parent candidate 1')
raw_sha=sha((RUN/'case.json').read_bytes()); config_sha=sha((RUN/'parent/config.json').read_bytes())
require((RUN/'parent/case.json').read_bytes()==(RUN/'case.json').read_bytes(),'parent raw case copy')
require(parent['case_sha256']==raw_sha and parent['config_sha256']==config_sha,'parent raw and canonical hashes correctly bound')
require(json.loads((RUN/'parent/config.json').read_bytes())==config,'same raw and canonical config content')
require(acceptance['case_sha256']==config_sha and config_sha!=raw_sha,'document actual legacy mislabeled case hash')
supervision=json.loads((ROOT/'supervised-native01/status.json').read_bytes())
metadata=json.loads((ROOT/'supervised-native01/metadata.json').read_bytes())
require(supervision['status']=='complete' and supervision['returncode']==0 and supervision['cleanup']['leader_reaped'] is True,'supervisor actual successful reaped process')
require(metadata['inputs_before']==supervision['inputs_after'] and supervision['inputs_unchanged'] is True,'all supervised before/after inputs equal')
require(metadata['timeout_s']==570 and metadata['cleanup_grace_s']==1 and supervision['elapsed_s']<570,'original supervision budget')
for path,digest in supervision['inputs_after'].items():
    require(sha(Path(path).read_bytes())==digest,'current supervised input byte match')
require(metadata['inputs_before'][str(Path(json.loads((RUN/'request.json').read_bytes())['case_path']))]==raw_sha,'raw case bound to supervision')
require(sha((RUN/'parent/source-study-record.json').read_bytes())==parent['source_record']['sha256']==acceptance['parent_study_sha256'],'parent record content hash binding')
require(sha((RUN/'ordinary-checkpoint.json').read_bytes())==acceptance['checkpoint_sha256'],'actual numeric checkpoint content hash binding')
result=dict(status='passed_with_documented_metadata_label_defect',check_count=len(checks),
    check_categories=dict(Counter(checks)),seconds=time.monotonic()-started,eos_calls=0,application_imports=0,
    events={b:len(x) for b,x in events.items()},counts=actual,lease_rhs_counts=[32,22,8,14],
    accepted_steps=3,evaluations_per_branch=22,pause_evaluations=8,continuation_new_evaluations=14,
    exact_interval=[(end-start).numerator,(end-start).denominator],physical_start=float(start),physical_end=float(end),
    temperature_change_k=list(map(float,dt)),paired_inverse_error_k=list(map(float,et)),
    energy_change_j=[float(F(b)-F(a)) for a,b in zip(numerical.states[0].internal_energy_j.values,numerical.states[-1].internal_energy_j.values)],
    global_step_energy_residual_j=list(map(float,global_changes)),local_step_energy_residual_j=[[float(v) for v in row] for row in local_residuals],
    energy_gate_j=float(u_tol),inventory_gate_mol=float(n_tol),full_balance_rows=7,
    raw_case_sha256=raw_sha,canonical_config_sha256=config_sha,
    original_acceptance_sha256=sha(acceptance_raw),original_mislabeled_case_sha256=acceptance['case_sha256'],
    scope='independent saved observations and step arithmetic; seven saved full-history residual rows checked, not recomputation of all historical quadrature or EOS',
    parent_record_sha256=parent['source_record']['sha256'],supervised_elapsed_seconds=supervision['elapsed_s'],
    workflow_elapsed_seconds=acceptance['elapsed_seconds'],parent_elapsed_seconds=parent['elapsed_wall_seconds'],
    material_qualified=False,full_firing_cycle=False,training_eligible=False,archived_source_resume_authorized=False)
(OUT/'NATIVE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','check_count','seconds','counts','temperature_change_k','paired_inverse_error_k')}))
