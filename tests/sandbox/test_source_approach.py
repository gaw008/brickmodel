"""Root guidance is checked against fresh actual source trials, not event claims."""
from dataclasses import replace
from fractions import Fraction as F

import numpy as np
import pytest

from test_depletion_integration import policies
from test_source_net_roots import poly
from test_source_liquid_column import setup
from test_source_prefix_trial import POLICY
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.source_approach import (
    choose_positive_approach, propose_source_approach, evaluate_source_approach,
    SourceApproachAssessmentError,
)
from sludge_sandbox.source_net_roots import order_inventory_roots
from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial


def choice(polynomials, *, budget=32, duration=F(2), **controls):
    order=order_inventory_roots(polynomials,duration,maximum_refinements=budget)
    values=dict(safe_fraction=F(1,4),minimum_step_s=F(1,2**30),maximum_step_s=duration,horizon_s=duration)
    values.update(controls)
    return choose_positive_approach(order,**values)


def test_ordering_and_positive_lower_bound_share_one_refinement_budget():
    liquid=poly(F(1,10000),-1,1)
    gas=poly(F(3,16),-1,1,family='gas',index=1)
    out=choice((liquid,gas),budget=3,duration=F(1))
    assert out.order.refinement_level==2
    assert out.additional_refinement_rounds==1
    assert out.selected_root.lower==0 and out.duration_s is None
    assert out.status=='positive_root_lower_bound_unresolved'
    assert out.order.roots[0].refinements==2
    out.check()


def test_exact_first_root_lower_bound_and_original_caps():
    for controls in ({},{'maximum_step_s':F(1,100)}, {'horizon_s':F(1,1000)}):
        out=choice((poly(1,-3,1),),**controls)
        assert out.status=='positive_numerical_proposal'
        assert 0 < out.duration_s <= out.desired_duration_s <= out.safe_fraction*out.selected_root.lower
        assert out.duration_s <= min(out.maximum_step_s,out.horizon_s)
        assert all(row[3]>0 for row in out.minima)
        assert out.order.roots[0].lower==0 and out.selected_root.lower>0
        out.check()


@pytest.mark.parametrize('polynomials,status',[
    ((poly(1,1),),'no_roots_use_ordinary_integrator'),
    ((poly(1,-1),poly(1,-2,family='gas',index=1)),'gas_first'),
    ((poly(1,-1),poly(2,-2,cell=1)),'competing_first_roots'),
    ((poly(1,-2,1),),'tangent_not_depletion'),
    ((poly(0,1),),'unsupported_zero_initial'),
])
def test_no_event_shortcuts_for_other_first_inventory_cases(polynomials,status):
    out=choice(polynomials)
    assert out.status==status and out.duration_s is None
    out.check()


def test_minimum_step_is_not_relaxed_and_failed_duration_retained():
    out=choice((poly(1,-1),),minimum_step_s=F(1,2))
    assert out.status=='approach_below_original_minimum_step'
    assert out.duration_s==F(1,4)
    out.check()


@pytest.mark.parametrize('controls',[
    {'safe_fraction':F(1,2)}, {'safe_fraction':F()}, {'safe_fraction':.25},
    {'minimum_step_s':F()}, {'maximum_step_s':F()}, {'horizon_s':F(3)},
])
def test_invalid_exact_controls_refused(controls):
    with pytest.raises(ValueError):
        choice((poly(1,-1),),**controls)


@pytest.fixture(scope='module')
def actual():
    with pytest.MonkeyPatch.context() as patch:
        column,_=setup(patch,count=1)
        storage=column.storages[0]
        state=storage.state(1e-6,(.125,.25,1e-12),0.)
        state=replace(state,internal_energy_j=storage.evaluate(state,325.).total_internal_energy_j)
        adapter=ExactSourceColumn(column)
        initial=adapter.pack((state,))
        observation=adapter.evaluate(initial,T(F()))
        phase=observation.source_evaluation.cells[0].phase.phase_water_mol_s
        assert phase>0
        horizon=F(3,2)*F(state.liquid_water_mol)/F(phase)
        policy=replace(POLICY,initial_step_s=float(horizon),maximum_step_s=float(horizon),minimum_step_s=2**-30)
        seed=evaluate_source_prefix_trial(adapter,initial,start=T(F()),end=T(horizon),
            integration_policy=policy,maximum_callbacks=16)
        assert seed.reason=='source_prefix_negative_inventory_minimum' and seed.prefix is None
        assert len(seed.captures)==2 and seed.captures[1].state.amounts_mol[0,0]>0
        seed.check()
        event_policy=replace(policies()[1],maximum_refinements=32)
        yield seed,event_policy


def test_actual_failed_full_prefix_proposes_without_new_physics(actual,monkeypatch):
    seed,policy=actual
    def forbidden(*args,**kwargs):pytest.fail('pure proposal evaluated source physics')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    proposal=propose_source_approach(seed,event_policy=policy)
    assert proposal.status=='positive_numerical_proposal'
    assert proposal.end<seed.captures[1].time<seed.end
    assert proposal.roots.order.earliest_labels==( ('liquid',0,0), )
    assert len(proposal.choice.minima)==4
    assert proposal.choice.additional_refinement_rounds==1
    assert seed.prefix is None and seed.status=='numerical_failure'
    assert proposal.event_policy is not policy and proposal.event_policy==policy
    proposal.check()


def test_fresh_actual_approach_reference_and_saved_checks(actual,monkeypatch):
    seed,policy=actual
    proposal=propose_source_approach(seed,event_policy=policy)
    original=ExactSourceColumn.evaluate; calls=[]
    def counted(self,state,when):
        calls.append((state,when))
        return original(self,state,when)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',counted)
    out=evaluate_source_approach(proposal,maximum_callbacks=16)
    assert out.status=='validated_positive_numerical_approach',out.reason
    assert out.new_evaluations==len(calls)==11
    assert out.trial.reference.status=='completed'
    assert out.trial.end==proposal.end and out.trial.discrepancy<=1
    assert out.trial.captures[1].time!=seed.captures[1].time
    assert np.all(out.trial.prefix.raw_state.amounts_mol>0)
    assert out.trial.prefix.raw_state.amounts_mol[0,0]<seed.initial.amounts_mol[0,0]
    assert out.trial.policy==seed.policy and out.trial.captures[0].evaluation is not seed.captures[0].evaluation
    assert out.pressure.comparison is out.comparison
    assert not out.event_admitted and not out.material_qualified
    def forbidden(*args,**kwargs):pytest.fail('saved check evaluated new source physics')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    out.check()
    for altered in (replace(out,event_admitted=True),replace(out,new_evaluations=0),
                    replace(out,maximum_callbacks=32),replace(out,reason='hidden_failure')):
        with pytest.raises(ValueError):altered.check()


def test_missing_policy_cap_and_changed_choice_refused(actual):
    seed,policy=actual
    missing=propose_source_approach(seed,event_policy=None)
    out=evaluate_source_approach(missing,maximum_callbacks=16)
    assert out.status=='not_evaluated' and out.new_evaluations==0
    out.check()
    proposal=propose_source_approach(seed,event_policy=replace(policy,maximum_refinements=1000))
    assert proposal.effective_root_refinement_limit==256
    assert proposal.event_policy.maximum_refinements==1000
    proposal.check()
    for altered in (replace(proposal,end=seed.end),replace(proposal,effective_root_refinement_limit=1),
                    replace(proposal,choice=replace(proposal.choice,additional_refinement_rounds=0)),
                    replace(proposal,event_policy=replace(policy,safe_inventory_fraction=.125))):
        with pytest.raises(ValueError):altered.check()


@pytest.mark.parametrize('budget,cancel',[(1,None),(16,lambda:True)])
def test_actual_new_trial_stops_retain_failure_evidence(actual,budget,cancel):
    seed,policy=actual
    out=evaluate_source_approach(propose_source_approach(seed,event_policy=policy),
                                 maximum_callbacks=budget,cancel=cancel)
    assert out.status==('cancelled' if cancel else 'resource_limit')
    assert out.new_evaluations==(0 if cancel else 1)
    assert out.trial is not None and out.comparison is None and out.pressure is None
    out.check()


def test_no_root_and_stopped_seeds_do_not_trigger_new_trials(actual,monkeypatch):
    seed,policy=actual
    small=evaluate_source_prefix_trial(seed.adapter,seed.initial,start=seed.start,end=seed.start.shifted(F(1,16384)),
        integration_policy=replace(seed.policy,initial_step_s=1/16384,maximum_step_s=1/16384),maximum_callbacks=16)
    stopped=evaluate_source_prefix_trial(seed.adapter,seed.initial,start=seed.start,end=seed.end,
        integration_policy=seed.policy,maximum_callbacks=16,cancel=lambda:True)
    def forbidden(*args,**kwargs):pytest.fail('not-applicable proposal made a new source call')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    for original,status in ((small,'no_roots_use_ordinary_integrator'),(stopped,'stopped_seed_requires_explicit_restart')):
        proposal=propose_source_approach(original,event_policy=policy)
        assert proposal.status==status
        out=evaluate_source_approach(proposal,maximum_callbacks=16)
        assert out.new_evaluations==0 and out.status=='not_evaluated'
        out.check()


@pytest.mark.parametrize('function,stage', [
    ('compare_source_trial_endpoints','endpoint_comparison'),
    ('propagate_source_trial_pressure','inverse_pressure'),
])
def test_postprocessing_failure_retains_actual_trial_without_repeating_it(actual,monkeypatch,function,stage):
    import sludge_sandbox.source_approach as module
    seed,policy=actual
    proposal=propose_source_approach(seed,event_policy=policy)
    cause=RuntimeError('')
    def fail(*args,**kwargs):raise cause
    monkeypatch.setattr(module,function,fail)
    with pytest.raises(SourceApproachAssessmentError) as caught:
        evaluate_source_approach(proposal,maximum_callbacks=16)
    error=caught.value
    assert error.stage==stage and error.__cause__ is cause
    assert error.exception_type=='RuntimeError' and error.exception_message==''
    assert error.trial.status=='validated_positive_numerical_trial'
    assert len(error.trial.captures)==11 and error.trial.reference.status=='completed'
    assert (error.comparison is None)==(stage=='endpoint_comparison')
    assert error.pressure is None
    error.trial.check()


def test_callback_cannot_replace_frozen_approach_event_policy(actual,monkeypatch):
    seed,policy=actual
    proposal=propose_source_approach(seed,event_policy=policy)
    binding=proposal.policy_binding
    original=ExactSourceColumn.evaluate
    calls=[]
    def mutate(self,state,when):
        if not calls:
            object.__setattr__(proposal.event_policy,'safe_inventory_fraction',.125)
            object.__setattr__(proposal.event_policy.roundoff_policy,'storage_absolute_mol',1e-12)
        calls.append(when)
        return original(self,state,when)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',mutate)
    out=evaluate_source_approach(proposal,maximum_callbacks=16)
    assert len(calls)==out.new_evaluations==11
    assert out.proposal.policy_binding==out.comparison.policy_binding==binding
    assert out.proposal.event_policy.safe_inventory_fraction==.25
    assert out.proposal.event_policy.roundoff_policy.storage_absolute_mol==1e-15
    assert out.proposal is not proposal
    out.check()
    with pytest.raises(ValueError):proposal.check()
