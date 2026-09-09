"""Exact service control/evidence tests with explicitly instrumented physics."""
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
import json
import pytest
from test_exact_depletion_integration import setup
from test_dynamic_solid_storage import forbid_water_eos
import sludge_sandbox.verification_case as vc
import sludge_sandbox.run_service as service
import sludge_sandbox.exact_run_service as exact
import sludge_sandbox.exact_terminal_proof_audit as proof
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.exact_record import read_exact_run,pack
ROOT=Path(__file__).resolve().parents[2]
ACTUAL_EXACT_SNAPSHOT=exact.snapshot_exact


def payload():
    p=json.loads((ROOT/'data/sandbox/cases/reacting-wet-free-paired-events-endpoint-root-v1.json').read_bytes())
    p['schema']=exact.CASE_SCHEMA;p['case_id']='explicit-exact-service-test'
    p['numerics']['depletion']['schema']='sandbox_exact_depletion_policy_v1'
    p['numerics']['depletion']['ordered_event_policy']='ordered_affine_packet_v1'
    p['numerics']['depletion']['nested_approach']['reuse_ordinary_spine']=False
    return p

@pytest.fixture
def app(monkeypatch,tmp_path):
    initial,view,p,e,calls=setup(monkeypatch)
    monkeypatch.setattr(WaterPhaseTransfer,'__post_init__',lambda self:None)
    monkeypatch.setattr(proof,'observation_binding',lambda v,o,s:proof.numeric(o.rates))
    monkeypatch.setattr(proof,'geometry_binding',lambda v,s,o:())
    data=payload();data['refinement']=0
    data['numerics'].update(start_s=0.,end_s=.03,integration=vc.encode(p))
    ep=vc.encode(e);ep.update(schema='sandbox_exact_depletion_policy_v1',pressure_comparison=None)
    data['numerics']['depletion']=ep
    case=tmp_path/'source.json';case.write_text(json.dumps(data))
    water=tmp_path/'water';water.mkdir();(water/'manufactured-source.json').write_text('{}')
    def build(case,water):return vc.BuiltCase(case,view.operator,initial,0.,.03,p,{},e)
    monkeypatch.setattr(vc,'build_case',build)
    def snap(built,state,t):return dict(state=vc.encode(state),temperature_k=[300.,300.],pressure_pa=[100000.,100000.],interfaces=list(built.operator.interfaces))
    monkeypatch.setattr(vc,'snapshot',snap)
    seen=[]
    def final_snapshot(built,current,state,t):
        seen.append((current.operator.interfaces,t))
        return snap(replace(built,operator=current.operator),state,t)
    monkeypatch.setattr(exact,'snapshot_exact',final_snapshot)
    return case,water,calls,seen


def test_strict_schema_explicit_optin_and_old_unchanged(tmp_path):
    data=payload();path=tmp_path/'case.json';path.write_text(json.dumps(data))
    assert vc.read_case(path).payload['schema']==exact.CASE_SCHEMA
    data['schema']='sludge_sandbox_free_event_case_v1';path.write_text(json.dumps(data))
    with pytest.raises(vc.CaseError):vc.read_case(path)
    original=ROOT/'data/sandbox/cases/reacting-wet-free-paired-events-endpoint-root-v1.json'
    assert vc.read_case(original).payload['schema']=='sludge_sandbox_free_event_case_v1'


def test_full_canonical_run_replay_and_trace(app,tmp_path):
    case,water,calls,seen=app
    first=service.run_case(case,water,tmp_path/'first')
    assert first['status']=='completed',first.get('reason')
    assert len(first['exact_audits'])==4
    checked,manifest=service.read_run(tmp_path/'first')
    record=read_exact_run((tmp_path/'first'/exact.RECORD).read_bytes())
    assert checked['integration']==exact.presentation(record)
    assert seen[-1][0]==('depleted_no_nucleation',)*2
    trace=service.trace_run(tmp_path/'first','mechanical_stretches')
    assert trace['canonical_exact_record']['sha256']==record.sha256
    assert any(x['symbol']=='integrate_exact_depletion' for x in trace['equations'])
    assert trace['dependency_graph']['case_sha256']==checked['case_sha256']
    replay=service.replay_run(tmp_path/'first',tmp_path/'replay')
    assert replay['status']=='completed',replay.get('reason')
    assert replay['integration']['states']==first['integration']['states']
    assert (tmp_path/'replay/replay_parent'/exact.RECORD).read_bytes()==record.canonical_bytes


def test_resume_full_history_and_parent_record_binding(app,tmp_path):
    case,water,calls,seen=app;flag=[False]
    first=service.run_case(case,water,tmp_path/'first',cancel=lambda:flag[0],_exact_on_commit=lambda info:flag.__setitem__(0,True))
    assert first['status']=='cancelled',first.get('reason')
    assert first['integration']['steps']
    assert service.trace_run(tmp_path/'first','temperature_k')['value'] is None
    second=service.resume_run(tmp_path/'first',tmp_path/'second')
    assert second['status']=='completed',second.get('reason')
    n=len(first['integration']['states'])
    assert second['integration']['states'][:n]==first['integration']['states']
    assert second['resume_of']['exact_record_sha256']==first['exact_record']['sha256']
    assert second['continuation_boundary']['states']==n
    assert second['initial_snapshot']==first['initial_snapshot']
    assert (tmp_path/'second/parent'/exact.RECORD).is_file()
    service.read_run(tmp_path/'second')


def test_resealed_display_tamper_is_not_authoritative(app,tmp_path):
    case,water,_,_=app;r=service.run_case(case,water,tmp_path/'first');assert r['status']=='completed',r.get('reason')
    r['integration']['states'][-1]['internal_energy_j'][0]+=1.
    service._json(tmp_path/'first/result.json',r);service._seal(tmp_path/'first')
    with pytest.raises(service.RunError,match='presentation_binding'):service.read_run(tmp_path/'first')


def test_post_audit_failure_retains_raw_canonical_record(app,tmp_path,monkeypatch):
    import sludge_sandbox.exact_record_comparison_audit as comparison
    case,water,_,_=app
    monkeypatch.setattr(comparison,'audit_exact_comparisons',lambda *a,**k:(_ for _ in ()).throw(ValueError('forced_audit_failure')))
    r=service.run_case(case,water,tmp_path/'failed')
    assert r['status']=='failed' and r['core_status']=='completed',r
    assert (tmp_path/'failed'/exact.RECORD).is_file() and (tmp_path/'failed/exact-core-projection.json').is_file()
    assert set(r['exact_audits'])=={'prefix','terminal_proofs'}
    service.read_run(tmp_path/'failed')


def test_repeated_resume_has_single_original_history(app,tmp_path):
    case,water,_,_=app;flag=[False]
    observer=lambda info:flag.__setitem__(0,True)
    a=service.run_case(case,water,tmp_path/'a',cancel=lambda:flag[0],_exact_on_commit=observer)
    flag[0]=False
    b=service.resume_run(tmp_path/'a',tmp_path/'b',cancel=lambda:flag[0],_exact_on_commit=observer)
    assert b['status']=='cancelled',b.get('reason')
    c=service.resume_run(tmp_path/'b',tmp_path/'c')
    assert c['status']=='completed',c.get('reason')
    for old,new in ((a,b),(b,c)):
        assert new['integration']['states'][:len(old['integration']['states'])]==old['integration']['states']
        assert new['integration']['elapsed_seconds']>=old['integration']['elapsed_seconds']
    service.read_run(tmp_path/'c')


def test_exact_kind_cannot_be_removed_to_bypass_record(app,tmp_path):
    case,water,_,_=app;r=service.run_case(case,water,tmp_path/'first');assert r['status']=='completed'
    r.pop('integration_kind');service._json(tmp_path/'first/result.json',r);service._seal(tmp_path/'first')
    with pytest.raises(service.RunError,match='kind_case_mismatch'):service.read_run(tmp_path/'first')


def test_live_initial_mismatch_replay_and_resume_before_callbacks(app,tmp_path,monkeypatch):
    case,water,calls,_=app;flag=[False]
    first=service.run_case(case,water,tmp_path/'first',cancel=lambda:flag[0],_exact_on_commit=lambda info:flag.__setitem__(0,True))
    assert first['status']=='cancelled';build=vc.build_case
    def altered(*args):
        b=build(*args);return replace(b,initial=replace(b.initial,internal_energy_j=b.initial.internal_energy_j+1.))
    monkeypatch.setattr(vc,'build_case',altered);count=len(calls)
    for name,action in (('resume',service.resume_run),('replay',service.replay_run)):
        result=action(tmp_path/'first',tmp_path/name)
        assert result['status']=='failed' and result['reason']=='exact_parent_original_state_interval',result
        assert len(calls)==count


def test_snapshot_failure_preserves_audited_canonical_output(app,tmp_path,monkeypatch):
    case,water,_,_=app
    monkeypatch.setattr(exact,'snapshot_exact',lambda *a:(_ for _ in ()).throw(ValueError('snapshot_failed')))
    result=service.run_case(case,water,tmp_path/'failed')
    assert result['status']=='failed' and result['core_status']=='completed'
    assert len(result['exact_audits'])==4 and result.get('final_snapshot') is None
    service.read_run(tmp_path/'failed')


def test_pressure_null_is_explicit_not_a_missing_fallback(tmp_path):
    data=payload();data['numerics']['depletion']['pressure_comparison']=None
    path=tmp_path/'case.json';path.write_text(json.dumps(data));vc.read_case(path)
    del data['numerics']['depletion']['pressure_comparison'];path.write_text(json.dumps(data))
    with pytest.raises(vc.CaseError):vc.read_case(path)

@pytest.mark.parametrize('field',['kind','policy_bool','audit_missing','initial_state','canonical_removed'])
def test_resealed_typed_association_attacks(app,tmp_path,field):
    case,water,_,_=app;r=service.run_case(case,water,tmp_path/'run');assert r['status']=='completed'
    if field=='kind':r['exact_record']['schema']='invented'
    elif field=='policy_bool':r['policy']['amount_scale_mol']=True
    elif field=='audit_missing':r['exact_audits'].pop('resources')
    elif field=='initial_state':r['initial_snapshot']['state']['mechanical_stretches'][0]=True
    else:(tmp_path/'run'/exact.RECORD).unlink();r.pop('exact_record')
    service._json(tmp_path/'run/result.json',r);service._seal(tmp_path/'run')
    with pytest.raises((ValueError,OSError)):service.read_run(tmp_path/'run')


def test_verified_export_preserves_canonical_json_text_and_local_route(app,tmp_path,monkeypatch):
    import uuid
    from sludge_sandbox.local_app import JobManager
    case,water,_,_=app
    manager=JobManager(case_path=case,water_directory=water,evidence_directory=None,storage_directory=tmp_path/'storage',maximum_jobs=2)
    identity=str(uuid.uuid4());directory=manager.jobs_directory/identity;directory.mkdir()
    r=service.run_case(case,water,directory/'run');assert r['status']=='completed',r.get('reason')
    raw=(directory/'run'/exact.RECORD).read_bytes()
    import sludge_sandbox.local_app as local
    monkeypatch.setattr(local,'_MAX_BYTES',1)
    with pytest.raises(local.LocalAppError,match='artifact_too_large'):manager.artifact(identity,exact.RECORD)
    exported=manager.export(identity)
    assert exported==service.export_run(directory/'run')
    assert exported['canonical_exact_record']['text'].encode('utf-8')==raw
    assert exported['canonical_exact_record']['sha256']==r['exact_record']['sha256']
    # A JSON client receives the canonical content as an opaque string. Rational
    # integers are not parsed as JS Number or rounded for visualization.
    transported=json.loads(json.dumps(exported))
    assert transported['canonical_exact_record']['text'].encode()==raw
    assert service._hash(raw)==exported['manifest']['files'][exact.RECORD]
    assert 'not a standalone' in exported['export_scope']


def test_exact_snapshot_uses_actual_exact_query_without_float_projection(app,monkeypatch):
    from sludge_sandbox.exact_event_clock import ExactEventTime as T
    case,water,calls,_=app;built=vc.build_case(vc.read_case(case),water)
    view=exact.ExactFreeWaterTransfer(built.operator);query=T(F(1,3));seen=[]
    def selected(b,s,t,out,op):
        seen.append((t,out,op));return {'state':vc.encode(s)}
    monkeypatch.setattr(vc,'_snapshot_evaluation',selected)
    result=ACTUAL_EXACT_SNAPSHOT(built,view,built.initial,query)
    assert len(calls)==1 and seen[0][0] is query and seen[0][2] is built.operator
    assert result['exact_time']=={'numerator':'1','denominator':'3'}


@pytest.mark.parametrize('early_exit', ('cancel', 'build_failure'))
def test_exact_resume_early_exit_has_only_historical_parent(app,tmp_path,monkeypatch,early_exit):
    case,water,_,_=app;flag=[False]
    parent_dir=tmp_path/'parent'
    parent=service.run_case(case,water,parent_dir,cancel=lambda:flag[0],
        _exact_on_commit=lambda info:flag.__setitem__(0,True))
    assert parent['status']=='cancelled' and parent['integration']['steps']
    parent_raw=(parent_dir/'exact-run-record.json').read_bytes()
    if early_exit=='build_failure':
        def fail_build(*args,**kwargs):raise RuntimeError('explicit_build_failure')
        monkeypatch.setattr(vc,'build_case',fail_build)
    child_dir=tmp_path/'child'
    result=service.resume_run(parent_dir,child_dir,cancel=lambda:early_exit=='cancel')
    assert result['status']==('cancelled' if early_exit=='cancel' else 'failed')
    assert result['reason']==('cancelled_before_build' if early_exit=='cancel' else 'explicit_build_failure')
    assert result['integration'] is None
    assert not (child_dir/'exact-run-record.json').exists()
    assert (child_dir/'parent/exact-run-record.json').read_bytes()==parent_raw
    assert (child_dir/'parent/result.json').read_bytes()==(parent_dir/'result.json').read_bytes()
    checked,_=service.read_run(child_dir)
    assert checked==result
