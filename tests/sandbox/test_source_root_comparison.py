"""Partitioned actual source paths retain their distinct numerical evidence."""
from dataclasses import replace
from fractions import Fraction as F

import numpy as np
import pytest

from test_source_approach import actual, choice
from test_source_net_roots import poly
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.source_approach import propose_source_approach, evaluate_source_approach
from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
from sludge_sandbox.source_root_comparison import (
    SourceRootStudyError, compare_source_root_clocks, evaluate_source_root_refinement,
    compare_source_root_trials, positive_source_common_end,
    evaluate_source_common_endpoint, compare_source_common_trials,
)


@pytest.mark.parametrize('origin',[F(),F(10**400),-F(10**400)])
def test_absolute_surrogate_clocks_cancel_origin_exactly(origin):
    a,b=choice((poly(1,-1),)),choice((poly(F(3,4),-1),))
    out=compare_source_root_clocks((a,b),(T(origin),T(origin+F(1,4))),time_absolute_s=F(1,100))
    assert out.distance_lower_s==out.distance_upper_s==0
    assert out.gate and out.additional_rounds==(0,0)
    assert all(x.lower==x.upper==T(origin+1) for x in out.intervals)
    out.check()


def test_comparison_narrowing_never_resets_order_or_approach_budget():
    c=choice((poly(1,-3,1),),budget=3)
    out=compare_source_root_clocks((c,c),(T(F()),T(F())),time_absolute_s=F(1,10**20))
    for root,extra in zip(out.refined_roots,out.additional_rounds):
        assert c.order.refinement_level+c.additional_refinement_rounds+extra==3
        assert root.refinements==3 and root.upper>root.lower
    assert out.distance_lower_s==0 and out.distance_upper_s>out.time_absolute_s
    assert not out.gate  # Overlap of coarse root intervals is not accuracy evidence.
    out.check()


def test_disjoint_root_interval_distance_and_original_tolerance():
    a,b=choice((poly(1,-1),)),choice((poly(F(3,4),-1),))
    out=compare_source_root_clocks((a,b),(T(F()),T(F())),time_absolute_s=F(1,8))
    assert out.distance_lower_s==out.distance_upper_s==F(1,4) and not out.gate
    with pytest.raises(ValueError):replace(out,distance_upper_s=F()).check()
    with pytest.raises(ValueError):replace(out,gate=True).check()


def test_invalid_times_or_changed_first_inventory_refused():
    a=choice((poly(1,-1),))
    with pytest.raises(ValueError):
        compare_source_root_clocks((a,a),(T(F()),T(F())),time_absolute_s=.1)
    with pytest.raises(ValueError):
        compare_source_root_clocks((a,a),(0.,T(F())),time_absolute_s=F(1,10))
    b=choice((poly(1,-1,cell=1),))
    with pytest.raises(ValueError):
        compare_source_root_clocks((a,b),(T(F()),T(F())),time_absolute_s=F(1,10))


@pytest.mark.parametrize('seconds',[1,True,1.])
def test_clock_wrapper_must_still_contain_exact_fraction(seconds):
    a=choice((poly(1,-1),))
    altered=T(F(1))
    object.__setattr__(altered,'seconds',seconds)
    with pytest.raises(ValueError):
        compare_source_root_clocks((a,a),(altered,T(F())),time_absolute_s=F(1,10))


@pytest.fixture(scope='module')
def approach(actual):
    seed,policy=actual
    value=evaluate_source_approach(propose_source_approach(seed,event_policy=policy),maximum_callbacks=16)
    assert value.status=='validated_positive_numerical_approach'
    return value


@pytest.fixture(scope='module')
def refinement(approach):
    value=evaluate_source_root_refinement(approach,maximum_callbacks=16)
    assert value.status=='partitioned_surrogate_roots_compared',value.reason
    return value


def test_actual_shifted_trial_connects_reference_and_keeps_failed_full_prefix(refinement,monkeypatch):
    out=refinement
    assert out.shifted_trial.reason=='source_prefix_negative_inventory_minimum'
    assert out.shifted_trial.prefix is None and len(out.shifted_trial.captures)==out.new_evaluations==2
    assert np.array_equal(out.shifted_trial.initial.amounts_mol,out.approach.trial.reference.states[-1].amounts_mol)
    assert out.shifted_trial.start==out.approach.trial.end
    assert out.shifted_trial.end==out.approach.proposal.original_trial.end
    assert out.shifted_trial.captures[0].evaluation is not out.approach.trial.captures[-1].evaluation
    assert out.shifted_trial.captures[1].time!=out.approach.proposal.original_trial.captures[1].time
    assert out.clock.distance_upper_s>=out.clock.distance_lower_s
    def forbidden(*a,**k):pytest.fail('retained comparison attempted fresh physics')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    out.check()
    for changed in (replace(out,new_evaluations=0),replace(out,event_admitted=True),
                    replace(out,reason='ignored'),replace(out,material_qualified=True)):
        with pytest.raises(ValueError):changed.check()


def test_original_coarse_trial_cannot_impersonate_shifted_trial(refinement):
    with pytest.raises(ValueError):
        compare_source_root_trials(refinement.approach,refinement.approach.proposal.original_trial)


@pytest.mark.parametrize('cap,cancel',[(1,None),(16,lambda:True)])
def test_shifted_attempt_resource_and_cancel_kept(approach,cap,cancel):
    out=evaluate_source_root_refinement(approach,maximum_callbacks=cap,cancel=cancel)
    assert out.status=='root_comparison_not_available' and out.clock is None
    assert out.shifted_trial.status==('cancelled' if cancel else 'resource_limit')
    assert out.new_evaluations==(0 if cancel else 1)
    out.check()


def test_actual_common_endpoints_and_joined_cumulative_ledgers(refinement,monkeypatch):
    end=positive_source_common_end(refinement)
    assert refinement.shifted_trial.start<end<min(x.lower for x in refinement.clock.intervals)
    calls=[];original=ExactSourceColumn.evaluate
    def counted(self,state,at):
        calls.append((state,at));return original(self,state,at)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',counted)
    out=evaluate_source_common_endpoint(refinement,end=end,maximum_callbacks_per_trial=16)
    assert out.new_evaluations==len(calls)==22
    assert out.coarse_trial.end==out.shifted_trial.end==out.common_end==end
    assert out.differences.comparison_time_offset_s==0
    assert out.coarse_trial.reference.status==out.shifted_trial.reference.status=='completed'
    assert len(out.cumulative_residuals[0])==len(out.coarse_trial.reference.steps)
    assert len(out.cumulative_residuals[1])==len(refinement.approach.trial.reference.steps)+len(out.shifted_trial.reference.steps)
    # Independently recompute total water drift from the original common start.
    water=lambda s:F(float(s.amounts_mol[0,0]))+F(float(s.amounts_mol[0,3]))
    delta=water(out.shifted_trial.reference.states[-1])-water(refinement.approach.trial.initial)
    nr=out.cumulative_residuals[1][-1][1]
    assert delta==nr[0]+nr[3]
    assert all(all(abs(v)<=F(out.coarse_trial.policy.amount_absolute_tolerance_mol) for v in row[1])
               for rows in out.cumulative_residuals for row in rows)
    assert out.gates==(True,True,True,False) and out.conditional_pressure_gate is False
    assert not out.event_admitted and not out.material_qualified
    def forbidden(*a,**k):pytest.fail('saved common endpoint check called new physics')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    out.check()
    with pytest.raises(ValueError):replace(out,new_evaluations=True).check()
    with pytest.raises(ValueError):replace(out,cumulative_residuals=((),())).check()
    with pytest.raises(ValueError):replace(out,event_admitted=True).check()
    with pytest.raises(ValueError):compare_source_common_trials(refinement,out.shifted_trial,out.coarse_trial)


def test_common_interval_cannot_cross_root_or_skip_connection(refinement,monkeypatch):
    def forbidden(*a,**k):pytest.fail('invalid common interval called physics')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    for end in (refinement.shifted_trial.start,refinement.shifted_trial.end,
                min(x.lower for x in refinement.clock.intervals)):
        with pytest.raises(ValueError):
            evaluate_source_common_endpoint(refinement,end=end,maximum_callbacks_per_trial=16)
    altered=positive_source_common_end(refinement)
    object.__setattr__(altered,'seconds',float(altered.seconds))
    with pytest.raises(ValueError):
        evaluate_source_common_endpoint(refinement,end=altered,maximum_callbacks_per_trial=16)


def test_failed_common_trial_retains_actual_attempt_and_stops_second_path(refinement):
    end=positive_source_common_end(refinement)
    with pytest.raises(SourceRootStudyError) as caught:
        evaluate_source_common_endpoint(refinement,end=end,maximum_callbacks_per_trial=1)
    error=caught.value
    assert error.stage=='coarse_common_trial' and len(error.records)==2
    assert error.records[1].status=='resource_limit'
    assert len(error.records[1].captures)==1
    error.records[1].check()


def test_common_postprocessing_failure_retains_both_completed_trials(refinement,monkeypatch):
    import sludge_sandbox.source_root_comparison as module
    end=positive_source_common_end(refinement)
    def fail(*a,**k):raise RuntimeError('comparison unavailable')
    monkeypatch.setattr(module,'compare_source_common_trials',fail)
    with pytest.raises(SourceRootStudyError) as caught:
        evaluate_source_common_endpoint(refinement,end=end,maximum_callbacks_per_trial=16)
    error=caught.value
    assert error.stage=='common_endpoint_assessment'
    assert len(error.records)==3 and isinstance(error.__cause__,RuntimeError)
    for trial in error.records[1:]:
        assert trial.status=='validated_positive_numerical_trial' and len(trial.captures)==11
        trial.check()


def test_common_trial_can_span_multiple_original_reference_steps(actual):
    original,event=actual
    cap=original.policy.maximum_step_s/16
    policy=replace(original.policy,initial_step_s=cap,maximum_step_s=cap)
    seed=evaluate_source_prefix_trial(original.adapter,original.initial,start=original.start,end=original.end,
        integration_policy=policy,maximum_callbacks=32)
    approach=evaluate_source_approach(propose_source_approach(seed,event_policy=event),maximum_callbacks=32)
    refinement=evaluate_source_root_refinement(approach,maximum_callbacks=32)
    end=positive_source_common_end(refinement)
    assert end.elapsed_since(original.start)>F(cap)
    out=evaluate_source_common_endpoint(refinement,end=end,maximum_callbacks_per_trial=32)
    assert len(out.coarse_trial.reference.steps)>=2
    for trial in (out.coarse_trial,out.shifted_trial):
        assert trial.discrepancy<=1
        assert all(step.end_s.elapsed_since(step.start_s)<=F(cap) for step in trial.reference.steps)
    out.check()
