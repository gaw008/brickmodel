"""Actual manufactured controller with explicitly instrumented pressure proofs.

No native calls, no claimed HEOS certificate. Stage/root/writeback/mode and
all original comparison/commit code execute; the session's numerical proof
implementation has its own separate tests.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from types import SimpleNamespace
import json
import pytest
from test_mass_wet_exact_controller import setup
from test_mass_wet_exact_stage import fixture,policy
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.mass_wet_exact_stage import pressure_radius,Sample
from sludge_sandbox import mass_wet_exact_controller as controller
from sludge_sandbox.mass_wet_pressure_session import PressureSession
from sludge_sandbox.mass_wet_pressure_interval import encoded
from sludge_sandbox.mass_wet_controller_pressure import ControllerPressureQueryContext,controller_pressure_radius


@dataclass(frozen=True)
class Snapshot:
    attempts: tuple
    original_configuration_json: bytes=b'pure_orchestration_proof_instrumentation'
    original_physics_json: bytes=b'actual_analytic_manufactured_fixture'
    source_before: tuple=('instrumented-session-source',)


@dataclass(frozen=True)
class Attempt:
    index: int
    context: bytes
    modes: tuple
    status: str
    failure_kind: str | None
    reason: str | None
    pressure_radius_pa: F | None


def make_session(monkeypatch,*,failure=None,after=None):
    s=object.__new__(PressureSession);calls=[];native_calls=[]
    def snapshot(self):return Snapshot(tuple(calls))
    def query(self,pair,states,rate,cell,*,context,caller_guard=None,remaining_caller_wall=None,**kw):
        assert self is s and states[cell].liquid_water_mol>0
        caller_guard();assert remaining_caller_wall()>0
        payload=json.loads(context);kind=payload[0]['fields'].get('comparison_kind')
        radius=pressure_radius(pair,states[cell],rate.inverse,cell,fixture(pair))
        fail=failure(len(calls),payload,pair) if failure else None
        a=Attempt(len(calls),context,pair.interfaces,'unresolved' if fail else 'proved_conditional_query',fail,'synthetic proof failure' if fail else None,None if fail else radius)
        calls.append(a);native_calls.append((pair,states,rate,cell))
        if after:after(len(calls),payload)
        return a
    monkeypatch.setattr(PressureSession,'snapshot',snapshot);monkeypatch.setattr(PressureSession,'query',query)
    return s,calls,native_calls


def execute(pair,initial,rp,cp,s,**kw):
    return controller.integrate_mixed_exact(pair,initial,start=T(F()),end=T(F(1,2000)),stage_policy=policy(),roundoff_policy=rp,original_liquid_fraction_limit=F('1e-8'),controller_policy=cp,pressure_session=s,**kw)


def test_complete_native_optin_has_all_original_packet_gates_and_shared_history(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch);s,calls,actual=make_session(monkeypatch)
    r=execute(pair,initial,rp,cp,s)
    assert type(r) is controller.NativePressureMixedControllerResult and r.status=='completed',r.reason
    assert r.original_initial is initial and r.states[0] is initial
    assert len(r.packets)==1 and len(r.packets[0])==2 and tuple(f.terminal.root_order.selected_cell for f in r.packets[0])==(0,1)
    assert r.operator.interfaces==('depleted_no_nucleation',)*2 and pair.interfaces==('existing_liquid',)*2
    assert [x.status for x in r.refinements[-3:]]==['comparison_pass']*3
    assert r.refinements[-1].role=='independent' and r.refinements[-1].path.approach_grid!=r.refinements[-2].path.approach_grid
    assert r.refinements[-1].approach_cap_s==r.refinements[-2].approach_cap_s/2 and r.refinements[-1].safe_fraction==r.refinements[-2].safe_fraction/2
    assert len(r.pressure_session_before.attempts)==0 and tuple(calls)==r.pressure_session_after.attempts
    previous=0;ordinary=0
    for ref in r.refinements:
        controller.audit_prefix(ref.path,initial,r.stage_policy)
        for name,trial in ref.path.attempts:
            if name!='ordinary':continue
            ordinary+=1
            assert len(trial.pressure_session_before.attempts)>=previous
            previous=len(trial.pressure_session_after.attempts)
            assert trial.evaluations_completed==9
        if ref.status!='coarse_reference':assert len(ref.comparison)==3 and all(len(row[2])==6 for row in ref.comparison)
    assert ordinary==dict(r.costs)['ordinary_trials']
    event_attempts=[(a,q) for a,q in zip(calls,actual) if json.loads(a.context)[0]['fields'].get('comparison_kind')=='event']
    assert len(event_attempts)==6 # first event: one remaining wet cell x two sides x three comparisons
    for a,(op,states,rate,cell) in event_attempts:
        ctx=json.loads(a.context)[0]['fields']
        assert ctx['selected_cell']==0 and cell==1 and a.modes==('depleted_no_nucleation','existing_liquid')
        assert ctx['source_binding']==op.binding() and states[0].liquid_water_mol==0
    assert {c.comparison_kind for c in r.pressure_comparison_contexts}=={'event','common'}
    assert not any(json.loads(a.context)[0]['fields'].get('comparison_kind')=='common' for a in calls) # both dry
    from sludge_sandbox.mass_wet_exact_record import pack,MixedRecordError
    with pytest.raises(MixedRecordError,match='unsupported_record_type:NativePressureMixedControllerResult'):pack(r)
    print({'queries':len(calls),'event_queries':len(event_attempts),'host_costs':dict(r.costs)})


@pytest.mark.parametrize('kind',['cancelled','resource_limit','domain_exit'])
def test_ordinary_pressure_failure_has_no_global_commit(monkeypatch,kind):
    pair,initial,rp,cp=setup(monkeypatch);s,calls,_=make_session(monkeypatch,failure=lambda n,c,p:kind if n==1 else None)
    r=execute(pair,initial,rp,cp,s)
    assert r.status==kind and r.reason=='synthetic proof failure'
    assert not r.steps and not r.packets and r.states==(initial,) and r.roundoff_totals.aggregate.events==0
    assert len(calls)==2 and len(r.pressure_session_after.attempts)==2 and r.refinements[0].path.attempts
    assert dict(r.costs)['evaluations_completed']>=9


def test_original_controller_inputs_mutation_keeps_original_bytes(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch)
    s,calls,_=make_session(monkeypatch,after=lambda n,c:object.__setattr__(cp,'maximum_evaluations',cp.maximum_evaluations+1))
    r=execute(pair,initial,rp,cp,s)
    assert r.status=='failed' and not r.steps and len(calls)==1
    assert 'native_original_controller_inputs_changed' in r.reason
    assert json.loads(r.original_controller_inputs_json)[6]['fields']['maximum_evaluations']==4000


def test_context_requires_actual_event_time_state_source_and_modes(monkeypatch):
    pair,states,rp,cp=setup(monkeypatch);rates=pair.evaluate(states);s,calls,_=make_session(monkeypatch)
    at=T(F(1,10000));sample=Sample('event_endpoint',at,states,rates,pair.binding(),pair.interfaces)
    ctx=ControllerPressureQueryContext('event','reference',1,'terminal',0,0,1,at,pair.binding(),pair.interfaces,b'original_inputs')
    for bad in [replace(ctx,time=at.shifted(F(1))),replace(ctx,source_binding='wrong'),replace(ctx,interfaces=('depleted_no_nucleation',)*2),replace(ctx,cell=0)]:
        with pytest.raises(ValueError):controller_pressure_radius(pair,states,sample,1,pressure_session=s,context=bad)
    with pytest.raises(ValueError):controller_pressure_radius(pair,tuple(list(states)),sample,1,pressure_session=s,context=ctx)
    assert not calls


def test_fixture_and_native_are_exclusive_before_controller_work(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch);s,calls,_=make_session(monkeypatch)
    with pytest.raises(ValueError,match='exclusive'):execute(pair,initial,rp,cp,s,constant_liquid_fixture=fixture(pair))
    assert not calls


def test_independent_last_event_proof_failure_rolls_back_whole_packet(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch)
    def fail(n,payload,op):
        c=payload[0]['fields']
        if c.get('comparison_kind')=='event' and c['refinement_role']=='independent' and c['side']=='candidate':return 'resource_limit'
    s,calls,_=make_session(monkeypatch,failure=fail)
    r=execute(pair,initial,rp,cp,s)
    assert r.status=='resource_limit' and r.reason=='synthetic proof failure'
    assert r.states==(initial,) and not r.steps and not r.packets and r.roundoff_totals.aggregate.events==0
    assert [ref.status for ref in r.refinements[-3:-1]]==['comparison_pass']*2
    assert r.refinements[-1].role=='independent' and r.refinements[-1].path.status=='completed'
    assert r.refinements[-1].path.frames and r.refinements[-1].status=='comparison_fail'
    assert r.pressure_session_after.attempts[-1].failure_kind=='resource_limit'
    assert len(r.pressure_session_after.attempts)==len(calls)>2


def test_completed_comparison_row_survives_later_cancel(monkeypatch):
    from sludge_sandbox import mass_wet_controller_pressure as helper
    pair,initial,rp,cp=setup(monkeypatch);s,calls,_=make_session(monkeypatch);cancelled=[False]
    actual=helper.controller_pressure_radius
    def wrapped(*a,**kw):
        ctx=kw['context']
        if ctx.refinement_role=='terminal' and ctx.refinement_level==1 and ctx.event_index==1:cancelled[0]=True
        return actual(*a,**kw)
    monkeypatch.setattr(helper,'controller_pressure_radius',wrapped)
    r=execute(pair,initial,rp,cp,s,cancel=lambda:cancelled[0])
    assert r.status=='cancelled' and not r.steps and not r.packets
    assert r.refinements[-1].path.status=='completed' and r.refinements[-1].path.steps
    assert len(r.refinements[-1].comparison)==1
    assert r.refinements[-1].comparison[0][0:2]==('event',0)
    assert len(r.refinements[-1].comparison[0][2])==6


@pytest.mark.parametrize('side,kind',[('reference','resource_limit'),('candidate','cancelled')])
def test_terminal_first_or_second_query_failure_keeps_current_path(monkeypatch,side,kind):
    pair,initial,rp,cp=setup(monkeypatch)
    def fail(n,payload,op):
        c=payload[0]['fields']
        if c.get('comparison_kind')=='event' and c['refinement_role']=='terminal' and c['side']==side:return kind
    s,calls,_=make_session(monkeypatch,failure=fail)
    r=execute(pair,initial,rp,cp,s)
    assert r.status==kind and not r.steps and not r.packets and r.states==(initial,)
    assert len(r.refinements)==2 and r.refinements[-1].path.status=='completed'
    assert r.refinements[-1].path.steps and r.refinements[-1].path.attempts
    assert r.refinements[-1].comparison==() # incomplete first row must not be manufactured
    assert r.pressure_session_after.attempts[-1].failure_kind==kind


def test_zero_liquid_existing_mode_cannot_skip_proof(monkeypatch):
    pair,states,rp,cp=setup(monkeypatch);rates=pair.evaluate(states);s,calls,_=make_session(monkeypatch)
    states=(replace(states[0],liquid_water_mol=0.),states[1]);at=T(F(1,10000))
    sample=Sample('event_endpoint',at,states,rates,pair.binding(),pair.interfaces)
    ctx=ControllerPressureQueryContext('event','reference',1,'terminal',0,0,0,at,pair.binding(),pair.interfaces,b'original_inputs')
    with pytest.raises(ValueError,match='zero_liquid_requires_depleted_mode'):
        controller_pressure_radius(pair,states,sample,0,pressure_session=s,context=ctx)
    assert not calls


def test_new_capture_entry_rejects_even_before_binding_parse(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch);s,calls,_=make_session(monkeypatch)
    r=execute(pair,initial,rp,cp,s,cancel=lambda:True)
    from sludge_sandbox.mass_wet_exact_record import encode_mixed_run,MixedRecordError
    with pytest.raises(MixedRecordError,match='explicit_mixed_capture'):
        encode_mixed_run(r,original_binding=b'not_a_legacy_binding')
    assert r.status=='cancelled' and not calls


def test_injected_rejection_retry_and_refinements_keep_entry_history(monkeypatch):
    """Orchestration injection, not a claim that the first scientific gate failed."""
    pair,initial,rp,cp=setup(monkeypatch);s,calls,_=make_session(monkeypatch)
    sentinel=Attempt(-1,b'prior_session_history',pair.interfaces,'proved_conditional_query',None,None,F())
    calls.append(sentinel)
    actual=controller.try_step_doubling;trials=[]
    def once_rejected(*a,**kw):
        assert kw['pressure_session'] is s
        trial=actual(*a,**kw)
        trials.append(trial)
        if len(trials)==1:
            assert trial.status=='accepted'
            return replace(trial,status='rejected',reason='test_only_injected_rejection')
        return trial
    monkeypatch.setattr(controller,'try_step_doubling',once_rejected)
    r=execute(pair,initial,rp,cp,s)
    assert r.status=='completed',r.reason
    assert dict(r.costs)['ordinary_rejected']>=1 and len(trials)>2
    assert r.pressure_session_before.attempts==(sentinel,)
    first=trials[0].pressure_session_after.attempts
    assert len(first)>1 and trials[1].pressure_session_before.attempts==first
    assert trials[1].end.seconds-trials[1].start.seconds < trials[0].end.seconds-trials[0].start.seconds
    assert r.pressure_session_after.attempts==tuple(calls)
    assert r.pressure_session_after.attempts[:len(first)]==first
    assert [ref.status for ref in r.refinements[-3:]]==['comparison_pass']*3
    for ref in r.refinements:
        for name,trial in ref.path.attempts:
            if name=='ordinary':assert trial.pressure_session_before.attempts[0]==sentinel
