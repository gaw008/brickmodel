from dataclasses import replace
import pytest
from test_depletion_integration import policies,oracle
from sludge_sandbox.integration import ConservedState

import sludge_sandbox.depletion_integration as m
import sludge_sandbox.event_record as records

def fixture(mod):
    import numpy as np
    p,e=policies();e=mod.DepletionPolicy(**vars(e))
    def callback(state,t,modes):
        sink=.001 if modes[0]=='existing_liquid' else 0.
        rates=mod.Rates(np.zeros((2,2)),np.zeros(2),[[-sink,sink]],[0.],mechanical_rates_per_s=[.2,-.1])
        return mod.DepletionEvaluation(rates,(sink,),(300.,),(0.,),(0.,),(0.,))
    op=mod.ManufacturedDepletionAdapter(evaluate_callback=callback,liquid_index=0,water_vapor_index=1,interfaces=('existing_liquid',),program_knots_s=(),source_ids=('manufactured:continuation',))
    p=replace(p,stretch_absolute_tolerance=1e-11,stretch_scale=1.,maximum_wall_seconds=10.)
    return p,e,op,ConservedState([[1e-4,0.]],[600.],mechanical_stretches=[1.,1.])

def test_explicit_none_preserves_default():
    p,e,op,initial=fixture(m)
    result=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e,continuation=None)
    assert result.status=='completed'
    assert len(result.events)==1


# This test uses the independently authored real strict record audit, not a
# stand-in certificate. Its source remains owned by the record-audit worker.

@pytest.mark.parametrize("method",["euler","affine_midpoint"])
def test_cancel_before_after_event_resume_twice_and_reaudit_tampering(method):
    import json
    from sludge_sandbox.verification_case import encode
    p,e,op,initial=fixture(m);e=replace(e,terminal_method=method)
    observed=[];original_callback=op.evaluate_callback
    def callback(state,t,modes):
        observed.append(t);return original_callback(state,t,modes)
    op=replace(op,evaluate_callback=callback)
    first=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e,cancel=lambda:bool(observed) and observed[-1]>=.03)
    assert first.status=='cancelled' and first.steps and not first.events
    def audited(run):
        record=records.encode_depletion_result(run,original_interfaces=op.interfaces)
        return records.audit_depletion_record(record,initial,p,e,op.interfaces,operator=run.operator,start_s=0.,end_s=.2)
    prefix=audited(first)
    observed.clear()
    second=m.integrate_depletion(first.states[-1],first.operator,start_s=first.times_s[-1],end_s=.2,integration_policy=p,event_policy=e,continuation=prefix,cancel=lambda:bool(observed) and observed[-1]>=.15)
    assert second.status=='cancelled' and len(second.events)==1
    assert second.times_s[:len(first.times_s)]==first.times_s
    assert second.attempted_steps>first.attempted_steps>=len(first.steps)
    assert second.evaluations>first.evaluations
    assert second.elapsed_seconds>=first.elapsed_seconds
    observed.clear()
    third=m.integrate_depletion(second.states[-1],second.operator,start_s=second.times_s[-1],end_s=.2,integration_policy=p,event_policy=e,continuation=audited(second))
    assert third.status=='completed',third.reason
    assert len(third.events)==1 and third.operator.interfaces==('depleted_no_nucleation',)
    assert third.attempted_steps>len(third.steps)  # discarded event trials stay charged
    assert third.roundoff_totals==second.roundoff_totals
    assert third.corrections==second.corrections
    assert third.times_s[:len(second.times_s)]==second.times_s
    assert third.states[-1].mechanical_stretches==pytest.approx([1.04,.98],abs=1e-10)
    assert third.states[-1].internal_energy_j[0]==600.
    assert third.evaluations>second.evaluations and third.attempted_steps>second.attempted_steps
    assert third.elapsed_seconds>=second.elapsed_seconds
    audited(third)  # full original-prefix conservation and corrections audited
    tampered=json.loads(prefix.record_json);tampered['attempted_steps']=-1
    with pytest.raises(ValueError):
        fake=records.AuditedDepletionRecord(json.dumps(tampered).encode(),prefix.original_policy_json)
        m.integrate_depletion(first.states[-1],first.operator,start_s=first.times_s[-1],end_s=.2,integration_policy=p,event_policy=e,continuation=fake)

def test_remaining_trial_budget_is_not_refunded_on_resume():
    p,e,op,initial=fixture(m);p=replace(p,maximum_steps=2)
    observed=[];original=op.evaluate_callback
    def callback(state,t,modes):
        observed.append(t);return original(state,t,modes)
    op=replace(op,evaluate_callback=callback)
    first=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e,cancel=lambda:bool(observed) and observed[-1]>=.02)
    assert first.status=='cancelled' and first.steps and first.attempted_steps==1
    record=records.encode_depletion_result(first,original_interfaces=op.interfaces)
    prefix=records.audit_depletion_record(record,initial,p,e,op.interfaces,operator=first.operator,start_s=0.,end_s=.2)
    count=len(observed)
    result=m.integrate_depletion(first.states[-1],first.operator,start_s=first.times_s[-1],end_s=.2,integration_policy=p,event_policy=e,continuation=prefix)
    assert result.status=='resource_limit' and result.reason=='global_accepted_trial_panel_limit'
    assert len(observed)>count
    assert result.attempted_steps==2
    assert result.times_s[:len(first.times_s)]==first.times_s
    assert len(result.steps)==2
    assert result.evaluations>first.evaluations

def test_cumulative_wall_exhaustion_preserves_prefix_without_evaluation(monkeypatch):
    from types import SimpleNamespace
    p,e,op,initial=fixture(m)
    observed=[];original=op.evaluate_callback
    def callback(state,t,modes):observed.append(t);return original(state,t,modes)
    op=replace(op,evaluate_callback=callback)
    first=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e,cancel=lambda:bool(observed) and observed[-1]>=.02)
    assert first.status=='cancelled' and first.steps
    prefix=records.audit_depletion_record(records.encode_depletion_result(first,original_interfaces=op.interfaces),initial,p,e,op.interfaces,operator=first.operator,start_s=0.,end_s=.2)
    count=len(observed);ticks=iter([0.,p.maximum_wall_seconds])
    monkeypatch.setattr(m,'time',SimpleNamespace(monotonic=lambda:next(ticks,p.maximum_wall_seconds)))
    result=m.integrate_depletion(first.states[-1],first.operator,start_s=first.times_s[-1],end_s=.2,integration_policy=p,event_policy=e,continuation=prefix)
    assert result.status=='resource_limit' and result.reason=='wall_time_limit'
    assert result.times_s==first.times_s and len(observed)==count
    assert result.evaluations==first.evaluations
    from fractions import Fraction
    assert Fraction(result.elapsed_seconds)>=Fraction(first.elapsed_seconds)+Fraction(p.maximum_wall_seconds)
