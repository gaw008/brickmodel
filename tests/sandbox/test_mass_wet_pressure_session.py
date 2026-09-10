"""Pure arithmetic/untrusted seeds and failed orchestration; no fabricated proof PASS."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal as D
import pytest
from test_mass_wet_pressure_interval import control_flow_only,proposals
from sludge_sandbox import mass_wet_pressure_provider_v2 as provider
from sludge_sandbox import mass_wet_pressure_seed as seedmod
from sludge_sandbox import mass_wet_pressure_session as sessions


@pytest.fixture
def seam(control_flow_only,monkeypatch):
    base,policy,request,stamp,clock=control_flow_only
    source=Path(__file__).parent/'fixtures/water-interval-primitives-v1/heos-water.json'
    policy=replace(policy,coefficient_json=str(source))
    rate=SimpleNamespace(inverse=SimpleNamespace(point=SimpleNamespace(fluid=SimpleNamespace(mechanical=SimpleNamespace(temperature_k=305.)))))
    request=replace(request,rate=rate)
    monkeypatch.setattr(provider,'parameters',base.parameters)
    monkeypatch.setattr(seedmod,'parameters',base.parameters)
    for module in (provider,seedmod,sessions):monkeypatch.setattr(module,'time',base.time)
    return base,policy,request,stamp,clock


def test_failure_category_depends_on_type_not_reason(seam):
    base,policy,request,stamp,clock=seam
    kwargs=dict(branch_policy=policy,boxes=proposals(),budget=base.ProofBudget(4,8,5.))
    def caller():raise ValueError('cancelled session_wall_budget resource_limit')
    result=provider.StructuredLiquidPressureProvider().evaluate(request,**kwargs,caller_guard=caller)
    assert result.failure_kind=='unresolved' and result.attempted_proof_operations==0
    def timeout():raise TimeoutError('arbitrary_without_budget_words')
    result=provider.StructuredLiquidPressureProvider().evaluate(request,**kwargs,caller_guard=timeout)
    assert result.failure_kind=='resource_limit'
    result=provider.StructuredLiquidPressureProvider().evaluate(request,**kwargs,cancel=lambda:True)
    assert result.failure_kind=='cancelled' and result.schema=='conditional_pressure_evidence_v2'


def test_real_coefficient_seed_is_only_untrusted_proposal(seam):
    _,policy,request,_,_=seam
    result=seedmod.propose_liquid_boxes(request,policy,policy=seedmod.LiquidSeedPolicy(),
        maximum_evaluations=12,maximum_wall_seconds=5.)
    assert result.status=='completed_untrusted_proposals' and result.boxes is not None
    assert 0<result.attempted==result.completed<=12
    assert len(result.iterations)==result.attempted and result.ancillary_json
    assert all(row.value_json and row.status=='completed' for row in result.iterations)
    assert result.qualification=='untrusted_numerical_proposals_not_certificates'


def test_seed_mid_evaluation_failure_retains_actual_prefix(seam,monkeypatch):
    _,policy,request,_,_=seam
    original=seedmod.evaluate_box;count=[0]
    def fail(*args,**kwargs):
        count[0]+=1
        if count[0]==2:raise ArithmeticError('actual_second_entered_seed_failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(seedmod,'evaluate_box',fail)
    result=seedmod.propose_liquid_boxes(request,policy,policy=seedmod.LiquidSeedPolicy(),maximum_evaluations=12,maximum_wall_seconds=5.)
    assert result.status=='unresolved' and result.boxes is None
    assert result.attempted==2 and result.completed==1
    assert result.iterations[0].value_json and result.iterations[1].status=='failed'


def test_seed_completed_value_survives_post_guard_failure(seam,monkeypatch):
    _,policy,request,stamp,_=seam;original=seedmod.evaluate_box
    def changed(*args,**kwargs):
        value=original(*args,**kwargs);stamp[0]='changed';return value
    monkeypatch.setattr(seedmod,'evaluate_box',changed)
    result=seedmod.propose_liquid_boxes(request,policy,policy=seedmod.LiquidSeedPolicy(),maximum_evaluations=12,maximum_wall_seconds=5.)
    assert result.failure_kind=='binding_failure' and result.boxes is None
    assert result.attempted==result.completed==1 and result.iterations[0].value_json


@pytest.fixture
def session_seam(seam,monkeypatch):
    base,policy,request,stamp,clock=seam
    pair=SimpleNamespace(interfaces=('existing_liquid','existing_liquid'),physics=b'original')
    monkeypatch.setattr(sessions,'_physics',lambda p:p.physics)
    monkeypatch.setattr(sessions.BoundLiquidPressureRequest,'capture',lambda *args:request)
    session=sessions.PressureSession(pair,branch_policy=policy,seed_policy=seedmod.LiquidSeedPolicy(),
        budget=sessions.PressureSessionBudget(12,4,5.,8))
    return session,pair,request,stamp,clock


def test_same_session_failed_queries_never_reset_work(session_seam):
    session,pair,request,_,_=session_seam
    first=session.query(pair,(),request.rate,0,context=b'first')
    assert first.status=='unresolved' and first.proof and first.seed.boxes
    assert first.cumulative_proof_attempted==1 and first.cumulative_proof_completed==0
    second=session.query(pair,(),request.rate,0,context=b'second')
    assert second.cumulative_seed_attempted==first.cumulative_seed_attempted+second.seed.attempted
    assert second.cumulative_proof_attempted==2
    saved=session.snapshot()
    assert len(saved.attempts)==2 and saved.cost_complete
    assert saved.native_calls==0 and saved.bottom_level_residual_evaluation_count is None


def test_session_deadline_includes_host_gap_and_retains_original_history(session_seam):
    session,pair,request,_,clock=session_seam
    first=session.query(pair,(),request.rate,0,context=b'first')
    clock[0]=6.
    second=session.query(pair,(),request.rate,0,context=b'after-host-gap')
    assert second.failure_kind=='resource_limit' and second.seed is None
    assert second.cumulative_seed_attempted==first.cumulative_seed_attempted
    assert session.snapshot().attempts[0] is first


def test_per_trial_guard_more_restrictive_and_cancellation_no_charge(session_seam):
    session,pair,request,_,_=session_seam
    out=session.query(pair,(),request.rate,0,context=b'cancel',cancel=lambda:True)
    assert out.failure_kind=='cancelled' and out.seed is None
    out=session.query(pair,(),request.rate,0,context=b'caller-wall',remaining_caller_wall=lambda:0.)
    assert out.failure_kind=='resource_limit' and out.seed is None
    assert session.snapshot().seed_attempted==0


def test_source_change_and_unrecorded_child_failure_close_cost_scope(session_seam,monkeypatch):
    session,pair,request,_,_=session_seam
    pair.physics=b'changed'
    out=session.query(pair,(),request.rate,0,context=b'changed')
    assert out.failure_kind=='binding_failure' and out.seed is None
    pair.physics=b'original'
    def escaped(*args,**kwargs):raise RuntimeError('unreturned_child')
    monkeypatch.setattr(sessions,'propose_liquid_boxes',escaped)
    out=session.query(pair,(),request.rate,0,context=b'unknown-cost')
    assert not out.cost_complete and out.failure_kind=='callback_failure'
    again=session.query(pair,(),request.rate,0,context=b'closed')
    assert not again.cost_complete and again.seed is None


@pytest.mark.parametrize('changes',[{'maximum_seed_evaluations':True},{'maximum_wall_seconds':float('inf')}, {'maximum_boxes_per_primitive':3}])
def test_strict_session_budget(changes):
    values=dict(maximum_seed_evaluations=12,maximum_proof_operations=4,maximum_wall_seconds=5.,maximum_boxes_per_primitive=8)
    with pytest.raises(ValueError):sessions.PressureSessionBudget(**(values|changes))


@pytest.mark.parametrize('seed_limit,proof_limit',[ (1,4),(12,1) ])
def test_original_cumulative_budget_exhaustion_stops_next_query(session_seam,seed_limit,proof_limit):
    old,pair,request,_,_=session_seam
    session=sessions.PressureSession(pair,branch_policy=old._branch,seed_policy=old._seed,
        budget=sessions.PressureSessionBudget(seed_limit,proof_limit,5.,8))
    first=session.query(pair,(),request.rate,0,context=b'charged-first')
    second=session.query(pair,(),request.rate,0,context=b'exhausted-second')
    assert first.seed and second.failure_kind=='resource_limit' and second.seed is None
    assert second.cumulative_seed_attempted==first.cumulative_seed_attempted
    assert second.cumulative_proof_attempted==first.cumulative_proof_attempted
    assert session.snapshot().attempts[0] is first
