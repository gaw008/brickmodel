"""Service/ledger control tests with analytic manufactured callbacks, no EOS."""
import json
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
from test_depletion_integration import policies
from sludge_sandbox.integration import ConservedState,Rates,IntegrationPolicy
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

@pytest.fixture
def app(monkeypatch,tmp_path):
    import sludge_sandbox.depletion_integration as m
    import sludge_sandbox.event_record as record
    import sludge_sandbox.verification_case as vc
    import sludge_sandbox.run_service as service
    p,e=policies();p=replace(p,stretch_absolute_tolerance=1e-11,stretch_scale=1.,maximum_wall_seconds=10.)
    e=m.DepletionPolicy(**{**vars(e),'terminal_method':'affine_midpoint'})
    payload=json.loads((ROOT/'data/sandbox/cases/reacting-wet-free-slab-v1.json').read_bytes())
    payload['schema']='sludge_sandbox_free_event_case_v1';payload['refinement']=0
    payload['numerics'].update(start_s=0.,end_s=.2,integration=vc.encode(p),depletion={'schema':'sandbox_depletion_policy_v1',**vc.encode(e)})
    casepath=tmp_path/'source-case.json';casepath.write_text(json.dumps(payload))
    water=tmp_path/'water';water.mkdir();(water/'source.json').write_text('{}')
    observed=[]
    def callback(state,t,modes):
        observed.append(t);sink=.001 if modes[0]=='existing_liquid' else 0.
        return m.DepletionEvaluation(Rates(np.zeros((2,2)),np.zeros(2),[[-sink,sink]],[0.],mechanical_rates_per_s=[.2,-.1]),(sink,),(300.,),(0.,),(0.,),(0.,))
    op=m.ManufacturedDepletionAdapter(evaluate_callback=callback,liquid_index=0,water_vapor_index=1,interfaces=('existing_liquid',),program_knots_s=(),source_ids=('manufactured:service-test',))
    initial=ConservedState([[1e-4,0.]],[600.],mechanical_stretches=[1.,1.])
    def build(case,*args):return vc.BuiltCase(case,op,initial,0.,.2,p,{},e)
    monkeypatch.setattr(vc,'build_case',build)
    def snapshot(built,state,t):return {'state':vc.encode(state),'interfaces':list(built.operator.interfaces),'time_s':t,'temperature_k':[300.],'pressure_pa':[0.]}
    monkeypatch.setattr(vc,'snapshot',snapshot)
    return service,vc,casepath,water,observed,record

def test_actual_event_run_replay_and_final_modes(app,tmp_path):
    service,vc,case,water,observed,_=app
    run=service.run_case(case,water,tmp_path/'first')
    assert run['status']=='completed',run.get('reason')
    assert len(run['integration']['events'])==1
    assert run['integration']['final_interfaces']==['depleted_no_nucleation']
    assert run['final_snapshot']['interfaces']==['depleted_no_nucleation']
    assert run['initial_snapshot']['interfaces']==['existing_liquid']
    assert run['integration']['states'][-1]['mechanical_stretches']==pytest.approx([1.04,.98],abs=1e-10)
    service.read_run(tmp_path/'first')
    replay=service.replay_run(tmp_path/'first',tmp_path/'replay')
    assert replay['status']=='completed',replay.get('reason')
    assert replay['integration']['states']==run['integration']['states']
    assert replay['replay_of']['result_sha256']

def test_twice_resume_uses_full_history_once(app,tmp_path):
    service,vc,case,water,observed,_=app
    first=service.run_case(case,water,tmp_path/'first',cancel=lambda:bool(observed) and observed[-1]>=.03)
    assert first['status']=='cancelled' and first['integration']['steps']
    observed.clear()
    second=service.resume_run(tmp_path/'first',tmp_path/'second',cancel=lambda:bool(observed) and observed[-1]>=.15)
    assert second['status']=='cancelled',second.get('reason')
    assert len(second['integration']['events'])==1
    observed.clear()
    third=service.resume_run(tmp_path/'second',tmp_path/'third')
    assert third['status']=='completed',third.get('reason')
    assert third['initial_snapshot']==first['initial_snapshot']
    assert third['checkpoint_snapshot']['interfaces']==['depleted_no_nucleation']
    for prior,next_run in [(first,second),(second,third)]:
        n=len(prior['integration']['states'])
        assert next_run['integration']['states'][:n]==prior['integration']['states']
        assert next_run['continuation_boundary']['states']==n
        assert next_run['integration']['attempted_steps']>prior['integration']['attempted_steps']
    assert len(third['integration']['events'])==1
    assert not (tmp_path/'third/resume_suffix.json').exists()
    assert (tmp_path/'third/depletion_result.json').exists()
    service.read_run(tmp_path/'third')

def test_diagnostic_failure_retains_full_audited_event_result(app,tmp_path,monkeypatch):
    service,vc,case,water,_,_=app;original=vc.snapshot
    def snapshot(built,state,t):
        if t==.2:raise ValueError('diagnostic_probe_failure')
        return original(built,state,t)
    monkeypatch.setattr(vc,'snapshot',snapshot)
    result=service.run_case(case,water,tmp_path/'failed')
    assert result['status']=='failed' and result['integration']['status']=='completed'
    assert len(result['integration']['events'])==1
    assert (tmp_path/'failed/depletion_result.json').exists()
    service.read_run(tmp_path/'failed')

def test_rebuilt_original_initial_mismatch_refuses_before_suffix(app,tmp_path,monkeypatch):
    service,vc,case,water,observed,_=app
    first=service.run_case(case,water,tmp_path/'first',cancel=lambda:bool(observed) and observed[-1]>=.03)
    assert first['status']=='cancelled';original=vc.build_case
    def build(*args):
        built=original(*args);return replace(built,initial=ConservedState([[1e-4,0.]],[601.],mechanical_stretches=[1.,1.]))
    monkeypatch.setattr(vc,'build_case',build);count=len(observed)
    result=service.resume_run(tmp_path/'first',tmp_path/'bad')
    assert result['status']=='failed' and result['reason']=='resume_live_initial_mismatch'
    assert len(observed)==count
    assert result['integration']==first['integration']

def test_replay_checks_runtime_after_before_native(app,tmp_path):
    service,vc,case,water,observed,_=app
    first=service.run_case(case,water,tmp_path/'first');assert first['status']=='completed'
    first['runtime_after']={'changed':True};service._json(tmp_path/'first/result.json',first);service._seal(tmp_path/'first')
    count=len(observed)
    with pytest.raises(service.RunError,match='replay_runtime_mismatch'):
        service.replay_run(tmp_path/'first',tmp_path/'bad')
    assert len(observed)==count

def test_failed_event_audit_saves_raw_result_and_trusted_parent(app,tmp_path,monkeypatch):
    service,vc,case,water,observed,records=app
    first=service.run_case(case,water,tmp_path/'first',cancel=lambda:bool(observed) and observed[-1]>=.03)
    assert first['status']=='cancelled';observed.clear();original=records.audit_depletion_record
    def audit(record,*args,**kwargs):
        if record['status']=='completed':raise ValueError('independent_prefix_audit_rejected')
        return original(record,*args,**kwargs)
    monkeypatch.setattr(records,'audit_depletion_record',audit)
    result=service.resume_run(tmp_path/'first',tmp_path/'rejected')
    assert result['status']=='failed' and result['integration']==first['integration']
    raw=json.loads((tmp_path/'rejected/depletion_result.json').read_bytes())
    assert raw['status']=='completed' and len(raw['events'])==1
    service.read_run(tmp_path/'rejected')
