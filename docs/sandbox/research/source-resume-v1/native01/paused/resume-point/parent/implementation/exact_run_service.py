"""Explicit exact service adapter. Canonical records, never display clocks, resume."""
from dataclasses import dataclass, replace
import json
from pathlib import Path
from .checkpoint import ResumePrefix
from .exact_event_clock import ExactEventTime as T
from .exact_record import encode_exact_run,read_exact_run,pack
from .exact_free_host import ExactFreeWaterTransfer
from .exact_depletion_integration import integrate_exact_depletion
from .exact_continuation_admission import ExactContinuationRequest

CASE_SCHEMA='sludge_sandbox_free_exact_event_case_v1'
KIND='exact_ordered_depletion_v1'
RECORD='exact-run-record.json'

@dataclass(frozen=True)
class ExactParent(ResumePrefix):
    parent_exact_raw:bytes
    parent_exact_sha256:str


def require(ok,message):
    from .run_service import RunError
    if not ok:raise RunError(message)


def clock(t):
    value=t.elapsed_since(T.from_float(0.))
    return {'numerator':str(value.numerator),'denominator':str(value.denominator)}


def presentation(record):
    """Derived plot/export data. Float elapsed clocks cannot be solver inputs."""
    from .verification_case import encode
    r=record.result
    return dict(schema='exact_core_presentation_v1',status=r.status,reason=r.reason,
        times_s=[float(t.elapsed_since(record.start)) for t in record.times],
        exact_times=[clock(t) for t in record.times],
        time_semantics='display_elapsed_from_original_start_only; exact_times are authoritative rational strings; no sorting or deduplication',
        states=[encode(s) for s in record.states],
        steps=[{'start':clock(x.start_s),'end':clock(x.end_s)} for x in record.ledgers],
        accepted_steps=len(record.ledgers),committed_packets=len(r.packets),
        committed_events=sum(len(p) for p in r.packets),costs=dict(r.costs),elapsed_seconds=r.elapsed_seconds)


def verify_exact_artifacts(directory,result,manifest):
    """Strict canonical-to-summary association, not live numerical authorization."""
    from .run_service import _hash
    case=json.loads((Path(directory)/'case.json').read_bytes())
    declared=type(case) is dict and case.get('schema')==CASE_SCHEMA
    if not declared:
        require(result.get('integration_kind')!=KIND,'exact_kind_case_mismatch')
        return
    if RECORD not in manifest['files'] and result.get('status') in ('failed','cancelled') and result.get('integration') is None:return
    require(result.get('integration_kind')==KIND,'exact_kind_case_mismatch')
    descriptor=result.get('exact_record')
    # Preparation/build/encode failures may have no canonical record. They must
    # not acquire a misleading accepted presentation from the parent or fallback.
    if descriptor is None:
        require(result.get('status') in ('failed','cancelled') and result.get('integration') is None,'missing_exact_canonical_record')
        return
    require(type(descriptor) is dict and set(descriptor)=={'artifact','sha256','schema'} and descriptor.get('artifact')==RECORD,'exact_record_descriptor')
    raw=(Path(directory)/RECORD).read_bytes();record=read_exact_run(raw)
    require(descriptor['schema']==json.loads(raw)['schema'],'exact_record_schema_binding')
    require(descriptor.get('sha256')==_hash(raw)==manifest['files'].get(RECORD),'exact_record_hash_binding')
    require(record.binding['case_sha256']==result['case_sha256'],'exact_record_case_binding')
    require(pack(record.binding['runtime_identity'])==pack(result['runtime_before']),'exact_record_runtime_binding')
    require(pack(result.get('integration'))==pack(presentation(record)),'exact_presentation_binding')
    require(pack(json.loads((Path(directory)/'exact-core-projection.json').read_bytes()))==pack(pack(record.result)),'exact_core_projection_binding')
    from .verification_case import encode
    require(pack(result.get('initial_snapshot',{}).get('state'))==pack(encode(record.states[0])),'exact_initial_snapshot_binding')
    if result.get('final_snapshot') is not None:
        require(pack(result['final_snapshot'].get('state'))==pack(encode(record.states[-1])),'exact_final_snapshot_state_binding')
    require(result.get('core_status')==record.result.status and result.get('core_reason')==record.result.reason,'exact_core_status_binding')
    require(pack(result.get('policy'))==pack(_encode(record.result.initial_policy)) and pack(result.get('depletion_policy'))==pack(_encode(record.result.event_policy)),'exact_policy_binding')
    names={'prefix','terminal_proofs','comparisons','resources'}
    reports=result.get('exact_audits',{})
    require(type(reports) is dict and set(reports)<=names,'exact_audit_names')
    for name,value in reports.items():
        require(type(value) is dict and value.get('record_sha256')==record.sha256,'exact_audit_record_binding')
        require(pack(json.loads((Path(directory)/('exact-audit-'+name+'.json')).read_bytes()))==pack(value),'exact_audit_artifact_binding')
    if result.get('status')=='completed':
        require(record.result.status=='completed','exact_completed_status_binding')
        require(set(reports)==names,'completed_exact_audits_missing')


def _encode(value):
    from .verification_case import encode
    # The record has EvidenceNode policy containers, not arbitrary restored types.
    from .exact_record import EvidenceNode,REGISTRY
    from dataclasses import fields
    allowed={'IntegrationPolicy','DepletionPolicy','NestedApproachPolicy','DepletionRoundoffPolicy','PressureComparisonPolicy','SharedConstantParameterBox'}
    def restore(v):
        if type(v) is EvidenceNode:
            require(v.kind in allowed,'explicit_exact_policy_node')
            cls=REGISTRY[v.kind]
            return cls(**{f.name:restore(v.values[f.name]) for f in fields(cls) if f.init})
        if type(v) is tuple:return tuple(restore(x) for x in v)
        return v
    return encode(restore(value))


def parent_from(directory,result,manifest):
    from .run_service import _hash
    directory=Path(directory)
    raw=(directory/RECORD).read_bytes();rr=(directory/'result.json').read_bytes();mr=(directory/'manifest.json').read_bytes()
    require(_hash(raw)==manifest['files'].get(RECORD),'exact_parent_changed_after_validation')
    require(_hash(rr)==manifest['files']['result.json'] and json.loads(mr)==manifest,'exact_parent_changed_after_validation')
    return ExactParent(rr,mr,_hash(rr),_hash(mr),raw,_hash(raw))


def checked_parent(parent,result,built,view,start,end):
    from .run_service import _hash
    from .exact_record import validate_binding
    require(type(parent) is ExactParent,'typed_exact_parent_required')
    require(type(parent.parent_exact_raw) is bytes and _hash(parent.parent_exact_raw)==parent.parent_exact_sha256,'exact_parent_bytes_binding')
    files=json.loads(parent.parent_manifest_raw)['files']
    require(files.get(RECORD)==parent.parent_exact_sha256,'exact_parent_manifest_binding')
    r=validate_binding(read_exact_run(parent.parent_exact_raw),view,case_sha256=result['case_sha256'],runtime_identity=result['runtime_before'])
    require(r.start==start and r.end==end and pack(r.states[0])==pack(built.initial),'exact_parent_original_state_interval')
    require(pack(r.result.initial_policy)==pack(built.policy) and pack(r.result.event_policy)==pack(built.depletion_policy),'exact_parent_original_policies')
    return r


def snapshot_exact(built,view,state,t):
    from .verification_case import _snapshot_evaluation,read_case
    require(read_case(built.case.path).sha256==built.case.sha256,'case_source_changed_before_exact_snapshot')
    out=view.evaluate(state,t)
    result=_snapshot_evaluation(built,state,t,out,view.operator)
    result['exact_time']=clock(t)
    result['time_semantics']='exact accepted absolute time; no float query projection'
    return result


def run_exact_event(built,result,parent,output,cancel,*,replay_parent=None,on_commit=None):
    from .run_service import _json,_hash
    from .verification_case import encode,snapshot
    from .exact_record_audit import audit_exact_run
    from .exact_terminal_proof_audit import audit_committed_terminal_proofs
    from .exact_record_comparison_audit import audit_exact_comparisons
    from .exact_resource_audit import audit_exact_resources
    result['integration_kind']=KIND
    result['integration']=None
    result['depletion_policy']=encode(built.depletion_policy)
    require(built.depletion_policy is not None and built.depletion_policy.ordered_event_policy=='ordered_affine_packet_v1','explicit_exact_policy_required')
    view=ExactFreeWaterTransfer(built.operator);start=T.from_float(built.start_s);end=T.from_float(built.end_s)
    continuation=None
    if replay_parent is not None:checked_parent(replay_parent,result,built,view,start,end)
    if parent is not None:
        prior=checked_parent(parent,result,built,view,start,end)
        require(prior.result.status=='cancelled' and prior.result.reason=='cancel_requested' and prior.ledgers and prior.times[-1]<end,'resume_requires_cancelled_exact_prefix')
        continuation=ExactContinuationRequest(parent.parent_exact_raw,parent.parent_exact_sha256,result['case_sha256'],result['runtime_before'])
        result['continuation_boundary']={'schema':'exact_continuation_boundary_v1','accepted_steps':len(prior.ledgers),'states':len(prior.states),'packets':len(prior.result.packets),'checkpoint_time':clock(prior.times[-1]),'prior_costs':dict(prior.result.costs),'prior_elapsed_seconds':prior.result.elapsed_seconds,'semantics':'Returned core history is complete cumulative history; do not merge again.'}
        result['resume_of'].update(exact_record_sha256=parent.parent_exact_sha256,wall_scope='Original cumulative core budget: prior active time plus new entry/admission/restore/integration. Diagnostics and copying are separate service overhead.')
    else:
        result['initial_snapshot']=encode(snapshot(built,built.initial,built.start_s))
    _json(output/'result.json',result)
    run=integrate_exact_depletion(built.initial,view,start=start,end=end,integration_policy=built.policy,event_policy=built.depletion_policy,cancel=cancel,continuation=continuation,on_commit=on_commit)
    result.update(core_status=run.status,core_reason=run.reason)
    # Persist full raw core evidence first. Failure never becomes a float-codec fallback.
    _json(output/'exact-core-projection.json',pack(run))
    raw=encode_exact_run(run,original_operator=view,start=start,end=end,case_sha256=result['case_sha256'],runtime_identity=result['runtime_before'])
    (output/RECORD).write_bytes(raw)
    record=read_exact_run(raw)
    result.update(status=run.status,reason=run.reason,exact_record={'artifact':RECORD,'sha256':_hash(raw),'schema':json.loads(raw)['schema']},integration=presentation(record))
    _json(output/'result.json',result)
    common=dict(original_initial=built.initial,start=start,end=end,integration_policy=built.policy,event_policy=built.depletion_policy,case_sha256=result['case_sha256'],runtime_identity=result['runtime_before'])
    audits=(('prefix',lambda:audit_exact_run(record,view,**common)),('terminal_proofs',lambda:audit_committed_terminal_proofs(raw,original_operator=view,**common)),('comparisons',lambda:audit_exact_comparisons(record,view,**common)),('resources',lambda:audit_exact_resources(record,original_policy=built.policy)))
    result['exact_audits']={}
    for name,call in audits:
        report=call();require(report.record_sha256==record.sha256,'exact_audit_record_binding')
        value=encode(report);_json(output/('exact-audit-'+name+'.json'),value)
        result['exact_audits'][name]=value
        _json(output/'result.json',result)
    if run.status=='completed':result['final_snapshot']=snapshot_exact(built,run.operator,run.states[-1],run.times_s[-1])
