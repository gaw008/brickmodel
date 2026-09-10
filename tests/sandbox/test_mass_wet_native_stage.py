"""Pure stage orchestration; analytic host and instrumented concrete session.

These tests do not claim a native pressure certificate: session internals are
covered separately. Actual stage/transport/inverse/ledger paths remain active.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from types import SimpleNamespace
import json
import pytest
from test_mass_wet_exact_stage import setup,fixture,policy
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox import mass_wet_exact_stage as stage
from sludge_sandbox.mass_wet_pressure_session import PressureSession
from sludge_sandbox.mass_wet_pressure_interval import data
from sludge_sandbox.mass_wet_transport import WetPair


@dataclass(frozen=True)
class Snapshot:
    attempts: tuple
    policy_identity: bytes=b'instrumented_orchestration_not_native_certificate'


def session(monkeypatch,pair,*,fail_at=None,kind='unresolved',radius=None,after=None):
    obj=object.__new__(PressureSession);calls=[]
    def snapshot(self):return Snapshot(tuple(calls))
    def query(self,actual_pair,states,rate,cell,*,context,caller_guard=None,remaining_caller_wall=None,**kw):
        assert self is obj and actual_pair is pair
        caller_guard();assert remaining_caller_wall()>0
        r=stage.pressure_radius(pair,states[cell],rate.inverse,cell,fixture(pair)) if radius is None else radius
        failure=kind if len(calls)+1==fail_at else None
        calls.append((states,rate,cell,context,r,failure))
        if after:after(len(calls))
        return SimpleNamespace(status='proved_conditional_query' if failure is None else 'unresolved',
                               failure_kind=failure,reason='synthetic pressure query',pressure_radius_pa=r if failure is None else None)
    monkeypatch.setattr(PressureSession,'snapshot',snapshot);monkeypatch.setattr(PressureSession,'query',query)
    return obj,calls


def run(pair,initial,s,**kwargs):
    return stage.try_step_doubling(pair,initial,start=T(F()),end=T(F(1,1000)),policy=policy(),pressure_session=s,**kwargs)


def test_four_actual_comparison_contexts_nine_callbacks_and_legacy_refusal(monkeypatch):
    pair,initial=setup(monkeypatch);s,calls=session(monkeypatch,pair)
    r=run(pair,initial,s)
    assert type(r) is stage.NativePressureMixedTrialResult and r.status=='accepted',r.reason
    assert r.evaluations_attempted==r.evaluations_completed==9 and len(calls)==4
    assert r.pressure_session_before.attempts==() and len(r.pressure_session_after.attempts)==4
    for k,(states,rate,cell,encoded,radius,failure) in enumerate(calls):
        expected=r.steps[0 if k%2==0 else 2]
        assert cell==k//2 and states is expected.endpoint_state and rate is expected.endpoint_sample.rates.cells[cell]
        ctx=r.pressure_query_contexts[k]
        assert ctx.role==('full' if k%2==0 else 'fine') and ctx.time==r.end
        assert json.loads(encoded)==data((ctx,states,rate,cell))
    assert len(r.comparisons)==6 and r.candidate_state is r.steps[-1].endpoint_state
    from sludge_sandbox.mass_wet_exact_record import pack,MixedRecordError
    with pytest.raises(MixedRecordError,match='unsupported_record_type:NativePressureMixedTrialResult'):pack(r)


@pytest.mark.parametrize('number,kind,expected',[(2,'unresolved','failed'),(3,'resource_limit','resource_limit'),(4,'cancelled','cancelled'),(2,'domain_exit','domain_exit')])
def test_late_failure_retains_whole_stage_and_prior_queries(monkeypatch,number,kind,expected):
    pair,initial=setup(monkeypatch);s,calls=session(monkeypatch,pair,fail_at=number,kind=kind)
    r=run(pair,initial,s)
    assert r.status==expected and r.candidate_state is None
    assert len(r.samples)==r.evaluations_completed==9 and len(r.steps)==3
    assert len(r.pressure_session_after.attempts)==len(calls)==number
    assert r.initial_state is initial and r.reason=='synthetic pressure query'


def test_fixture_native_ambiguity_before_callback(monkeypatch):
    pair,initial=setup(monkeypatch);s,calls=session(monkeypatch,pair)
    def forbidden(*a):raise AssertionError('unexpected host call')
    monkeypatch.setattr(WetPair,'evaluate',forbidden)
    with pytest.raises(ValueError,match='exclusive'):run(pair,initial,s,constant_liquid_fixture=fixture(pair))
    assert not calls


def test_cancel_after_proof_keeps_cost_and_no_candidate(monkeypatch):
    pair,initial=setup(monkeypatch);s,calls=session(monkeypatch,pair)
    r=run(pair,initial,s,cancel=lambda:len(calls)>=2)
    assert r.status=='cancelled' and r.candidate_state is None and len(r.pressure_session_after.attempts)==2
    assert r.evaluations_completed==9


def test_pressure_radius_cannot_bypass_original_pressure_gate(monkeypatch):
    pair,initial=setup(monkeypatch);s,calls=session(monkeypatch,pair,radius=F(2))
    r=run(pair,initial,s)
    assert r.status=='rejected' and r.reason=='full_vs_half_original_gates' and r.candidate_state is None
    assert dict(r.comparisons)['pressure_pa']>=4 and len(calls)==4


def test_generic_wet_default_still_refuses_and_base_result_preserved(monkeypatch):
    pair,initial=setup(monkeypatch)
    r=run(pair,initial,None)
    assert type(r) is stage.MixedTrialResult and r.reason=='pressure_temperature_envelope_unavailable'
    assert r.evaluations_completed==9


def test_dry_no_pressure_queries(monkeypatch):
    pair,initial=setup(monkeypatch);zeros=[]
    for i,state in enumerate(initial):
        z=pair.storages[i].state(state.solid_mass_kg,0.,(.2,.2,1e-8),0.)
        zeros.append(replace(z,internal_energy_j=pair.storages[i].evaluate(z,305.+5*i).total_internal_energy_j))
    initial=tuple(zeros);pair=pair.with_depleted_cells(initial,(0,1));s,calls=session(monkeypatch,pair)
    r=run(pair,initial,s)
    assert r.status=='accepted',r.reason
    assert not calls and r.pressure_session_before==r.pressure_session_after and r.evaluations_completed==9


def test_wrong_current_inverse_or_source_or_time_rejected(monkeypatch):
    pair,initial=setup(monkeypatch);rate=pair.evaluate(initial).cells[0];s,calls=session(monkeypatch,pair)
    ctx=stage.NativePressureQueryContext('full',T(F(1)),pair.binding(),pair.interfaces,initial,T(F()),T(F(1)),policy())
    options=dict(states=initial,cell_rate=rate,pressure_session=s,query_context=ctx)
    with pytest.raises(ValueError,match='actual_state_inverse'):
        stage.pressure_radius(pair,initial[0],replace(rate.inverse),0,None,**options)
    for wrong in [replace(ctx,source_binding='wrong'),replace(ctx,time=T(F(2))),replace(ctx,interfaces=('depleted_no_nucleation',)*2)]:
        with pytest.raises(ValueError,match='native_pressure_comparison'):
            stage.pressure_radius(pair,initial[0],rate.inverse,0,None,**dict(options,query_context=wrong))
    assert not calls


def test_session_history_is_not_reset_between_stage_calls(monkeypatch):
    pair,initial=setup(monkeypatch);s,calls=session(monkeypatch,pair,fail_at=5,kind='resource_limit')
    first=run(pair,initial,s);second=run(pair,initial,s)
    assert first.status=='accepted' and second.status=='resource_limit'
    assert len(second.pressure_session_before.attempts)==4 and len(second.pressure_session_after.attempts)==5
    assert second.candidate_state is None


@pytest.mark.parametrize('failure',['source','wall'])
def test_postproof_source_or_wall_failure_retains_attempt(monkeypatch,failure):
    pair,initial=setup(monkeypatch)
    def after(n):
        if failure=='source':object.__setattr__(pair,'rate_constants_per_s',(1.,1.))
        else:monkeypatch.setattr(stage.time,'monotonic',lambda:1e12)
    s,calls=session(monkeypatch,pair,after=after)
    r=run(pair,initial,s)
    assert r.status==('failed' if failure=='source' else 'resource_limit')
    assert r.candidate_state is None and r.evaluations_completed==9 and len(r.pressure_session_after.attempts)==1


def test_original_stage_policy_cannot_be_loosened_during_proof(monkeypatch):
    pair,initial=setup(monkeypatch);original=policy()
    s,calls=session(monkeypatch,pair,radius=F(2),after=lambda n:object.__setattr__(original,'pressure_absolute_pa',100.))
    result=stage.try_step_doubling(pair,initial,start=T(F()),end=T(F(1,1000)),policy=original,pressure_session=s)
    assert result.status=='failed' and result.candidate_state is None
    assert result.reason=='native_original_stage_policy_changed'
    assert len(result.pressure_session_after.attempts)==1
    assert json.loads(result.original_stage_policy_json)['fields']['pressure_absolute_pa']=={'float_hex':(1.).hex()}


def test_original_initial_cannot_be_rewritten_during_proof(monkeypatch):
    pair,initial=setup(monkeypatch);original_energy=initial[0].internal_energy_j
    s,calls=session(monkeypatch,pair,after=lambda n:object.__setattr__(initial[0],'internal_energy_j',initial[0].internal_energy_j+1.))
    result=run(pair,initial,s)
    assert result.status=='failed' and result.candidate_state is None
    assert result.reason=='native_original_stage_inputs_changed'
    assert len(result.pressure_session_after.attempts)==1
    assert json.loads(result.original_stage_inputs_json)[0][0]['fields']['internal_energy_j']=={'float_hex':original_energy.hex()}
