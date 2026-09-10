"""Actual source host, manufactured water/transport; no HEOS or event claim."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from test_source_liquid_column import setup
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.integration import IntegrationPolicy, DomainExit, IntegrationError
from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial

POLICY=IntegrationPolicy(1/16384,1/16384,1/16384,1e-8,1e-7,1e-3,1.,1e5,4,4,15.)


def fixture(monkeypatch,count=1):
    column,states=setup(monkeypatch,count=count)
    adapter=ExactSourceColumn(column)
    return adapter,adapter.pack(states)


def run(adapter,state,**kwargs):
    return evaluate_source_prefix_trial(adapter,state,start=T(F()),end=T(F(1,16384)),
        integration_policy=POLICY,maximum_callbacks=16,**kwargs)


def test_actual_first_midpoint_terminal_reference_and_original_scales(monkeypatch):
    adapter,state=fixture(monkeypatch)
    out=run(adapter,state)
    assert out.status=='validated_positive_numerical_trial',out.reason
    assert len(out.captures)==11 and all(c.evaluation is not None for c in out.captures)
    assert [c.role for c in out.captures[:3]]==['initial','euler_midpoint','prefix_terminal']
    assert out.discrepancy<=1
    assert out.reference.status=='completed'
    assert out.reference_policy.maximum_wall_seconds<=POLICY.maximum_wall_seconds
    assert out.terminal_bounds[0][3]==out.captures[2].evaluation.source_evaluation.cells[0].inverse.point.pressure_error_pa
    assert out.prefix.qualification=='numerical_prefix_only_no_stage_event_or_wet_state_permission'
    out.check()


@pytest.mark.parametrize('exception,status',[(DomainExit('endpoint-only'), 'domain_exit'),
    (IntegrationError('endpoint-only'),'numerical_failure'),(ValueError('endpoint-only'),'numerical_failure')])
def test_real_endpoint_callback_failure_retains_actual_attempt(monkeypatch,exception,status):
    adapter,state=fixture(monkeypatch)
    original=ExactSourceColumn.evaluate; calls=[]
    def fail(self,current,when):
        calls.append((current,when))
        if len(calls)==3:raise exception
        return original(self,current,when)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',fail)
    out=run(adapter,state)
    assert out.status==status and 'endpoint-only' in out.reason
    assert len(out.captures)==3 and out.reference is None
    assert out.captures[-1].evaluation is None and out.captures[-1].failure=='endpoint-only'
    assert out.captures[-1].ordinal==3 and out.captures[-1].time==out.end
    np.testing.assert_array_equal(out.captures[-1].state.amounts_mol,out.prefix.raw_state.amounts_mol)
    out.check()


def test_callback_cap_includes_reference_and_retains_partial_reference(monkeypatch):
    adapter,state=fixture(monkeypatch)
    out=evaluate_source_prefix_trial(adapter,state,start=T(F()),end=T(F(1,16384)),
        integration_policy=POLICY,maximum_callbacks=4)
    assert out.status=='resource_limit' and out.reason=='trial_callback_limit'
    assert len(out.captures)==4 and out.reference.status!='completed'
    assert out.discrepancy is None
    out.check()


def test_reference_endpoint_failure_cannot_supply_comparison(monkeypatch):
    adapter,state=fixture(monkeypatch)
    original=ExactSourceColumn.evaluate; count=0
    def fail(self,current,when):
        nonlocal count
        count+=1
        if count==11:raise DomainExit('reference-only-endpoint')
        return original(self,current,when)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',fail)
    out=run(adapter,state)
    assert out.status!='validated_positive_numerical_trial'
    assert out.reference.status!='completed' and out.discrepancy is None
    assert out.captures[-1].evaluation is None and out.captures[-1].ordinal==11


def test_original_policy_is_independent_of_callback_mutating_caller(monkeypatch):
    adapter,state=fixture(monkeypatch)
    policy=replace(POLICY)
    original=ExactSourceColumn.evaluate
    def changed(self,current,when):
        object.__setattr__(policy,'amount_absolute_tolerance_mol',123.)
        return original(self,current,when)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',changed)
    out=evaluate_source_prefix_trial(adapter,state,start=T(F()),end=T(F(1,16384)),
        integration_policy=policy,maximum_callbacks=16)
    assert out.status=='validated_positive_numerical_trial',out.reason
    assert out.policy.amount_absolute_tolerance_mol==POLICY.amount_absolute_tolerance_mol
    assert out.reference_policy.amount_absolute_tolerance_mol==POLICY.amount_absolute_tolerance_mol
    out.check()
    object.__setattr__(out.policy,'amount_absolute_tolerance_mol',123.)
    with pytest.raises(ValueError,match='policy_binding'):out.check()


def test_discrepancy_has_no_one_third_factor():
    from sludge_sandbox.source_prefix_trial import normalized_prefix_discrepancy
    from sludge_sandbox.integration import ConservedState
    a=ConservedState(np.ones((1,4)),np.array([100.]),('test',))
    b=ConservedState(np.ones((1,4)),np.array([102.]),('test',))
    policy=replace(POLICY,relative_tolerance=.5,energy_absolute_tolerance_j=.5,energy_scale_j=1.)
    assert normalized_prefix_discrepancy(a,b,policy)==2.


def test_cancel_after_actual_call_preserves_observation(monkeypatch):
    adapter,state=fixture(monkeypatch)
    original=ExactSourceColumn.evaluate; cancelled=False
    def observed(self,current,when):
        nonlocal cancelled
        result=original(self,current,when);cancelled=True
        return result
    monkeypatch.setattr(ExactSourceColumn,'evaluate',observed)
    out=run(adapter,state,cancel=lambda:cancelled)
    assert out.status=='cancelled' and len(out.captures)==1
    assert out.captures[0].evaluation is not None and out.captures[0].failure=='cancel_requested'
    out.check()


def test_N3_actual_source_trial_preserves_all_inverses_and_no_extra_EOS_check(monkeypatch):
    adapter,state=fixture(monkeypatch,3)
    out=run(adapter,state)
    assert out.status=='validated_positive_numerical_trial',out.reason
    assert len(out.terminal_bounds)==3 and out.prefix.raw_state.amounts_mol.shape==(3,4)
    def forbidden(*args,**kwargs):pytest.fail('record check executed new source physics')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    out.check()
    assert sum(out.prefix.full_residual_mol,F())==sum(
        F(float(x))-F(float(y)) for x,y in zip(out.prefix.raw_state.amounts_mol.flat,state.amounts_mol.flat))


def test_forged_success_capture_and_reference_ledger_are_rejected(monkeypatch):
    adapter,state=fixture(monkeypatch)
    out=run(adapter,state)
    assert out.status=='validated_positive_numerical_trial',out.reason
    changed=replace(out.captures[-1],binding=None)
    with pytest.raises(ValueError):replace(out,captures=(*out.captures[:-1],changed)).check()
    changed=replace(out.captures[0],time=T(F(1,32768)))
    with pytest.raises(ValueError):replace(out,captures=(changed,*out.captures[1:])).check()
    bad_step=replace(out.reference.steps[0],face_energy_j=out.reference.steps[0].face_energy_j+1)
    bad_ref=replace(out.reference,steps=(bad_step,*out.reference.steps[1:]))
    with pytest.raises(ValueError,match='replay_changed'):replace(out,reference=bad_ref).check()


def test_every_zero_initial_is_unsupported_without_callback(monkeypatch):
    from sludge_sandbox.integration import ConservedState
    adapter,state=fixture(monkeypatch)
    amounts=state.amounts_mol.copy();amounts[0,1]=0.
    state=ConservedState(amounts,state.internal_energy_j,state.energy_model_identity)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',lambda *a:pytest.fail('zero initial evaluated'))
    out=run(adapter,state)
    assert out.status=='unsupported' and not out.captures
    out.check()


def test_exact_origin_translation(monkeypatch):
    adapter,state=fixture(monkeypatch)
    origin=F(2**80)+F(1,3)
    out=evaluate_source_prefix_trial(adapter,state,start=T(origin),end=T(origin+F(1,16384)),
        integration_policy=POLICY,maximum_callbacks=16)
    assert out.status=='validated_positive_numerical_trial',out.reason
    assert out.captures[1].time==T(origin+F(1,32768))


@pytest.mark.parametrize('bad',[True,0,-1,1.5])
def test_callback_budget_exact_type(monkeypatch,bad):
    adapter,state=fixture(monkeypatch)
    with pytest.raises(ValueError,match='resource_controls'):
        evaluate_source_prefix_trial(adapter,state,start=T(F()),end=T(F(1,16384)),
            integration_policy=POLICY,maximum_callbacks=bad)


def test_original_outcome_reference_policy_and_callback_cap_are_bound(monkeypatch):
    adapter,state=fixture(monkeypatch)
    out=run(adapter,state)
    assert out.status=='validated_positive_numerical_trial',out.reason
    for forged in (replace(out,status='unsupported',reason='made-up-domain'),
                   replace(out,maximum_callbacks=1000),
                   replace(out,reference_policy=replace(out.reference_policy,maximum_wall_seconds=1.))):
        with pytest.raises(ValueError,match='binding'):forged.check()


def test_wall_guard_after_callback_includes_observation_cost(monkeypatch):
    import sludge_sandbox.source_prefix_trial as module
    adapter,state=fixture(monkeypatch)
    original=ExactSourceColumn.evaluate;clock=[0.]
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    def delayed(self,current,when):
        result=original(self,current,when)
        clock[0]=POLICY.maximum_wall_seconds+1
        return result
    monkeypatch.setattr(ExactSourceColumn,'evaluate',delayed)
    out=run(adapter,state)
    assert out.status=='resource_limit' and len(out.captures)==1
    assert out.captures[0].evaluation is not None
    assert out.elapsed_seconds==POLICY.maximum_wall_seconds+1
    out.check()


def test_predictor_zero_rejected_before_second_source_call(monkeypatch):
    import sludge_sandbox.source_prefix_trial as module
    from sludge_sandbox.integration import ConservedState
    adapter,state=fixture(monkeypatch)
    original=module.advance_exact_euler
    def zero(*args):
        predictor=original(*args);amounts=predictor.amounts_mol.copy();amounts[0,0]=0.
        return ConservedState(amounts,predictor.internal_energy_j,predictor.energy_model_identity)
    monkeypatch.setattr(module,'advance_exact_euler',zero)
    out=run(adapter,state)
    assert out.status=='unsupported' and len(out.captures)==1
    assert out.reason=='source_trial_nonpositive_predictor_inventory'


def test_interior_knot_rejected_before_source_callback(monkeypatch):
    adapter,state=fixture(monkeypatch)
    monkeypatch.setattr(ExactSourceColumn,'breakpoints',lambda *a:(T(F(1,32768)),))
    monkeypatch.setattr(ExactSourceColumn,'evaluate',lambda *a:pytest.fail('cross-knot evaluation'))
    out=run(adapter,state)
    assert out.status=='unsupported' and out.reason=='source_trial_interior_program_knot'
    assert not out.captures


@pytest.mark.parametrize('side',[0,1])
def test_nonfinite_comparison_energy_cannot_hide_in_max(side):
    from sludge_sandbox.source_prefix_trial import normalized_prefix_discrepancy
    from sludge_sandbox.integration import ConservedState
    states=[ConservedState(np.ones((1,4)),np.array([100.]),('test',)) for _ in range(2)]
    object.__setattr__(states[side],'internal_energy_j',np.array([float('nan')]))
    with pytest.raises(ValueError,match='finite_binary64'):
        normalized_prefix_discrepancy(*states,POLICY)


def test_completed_reference_at_wrong_exact_endpoint_is_not_usable(monkeypatch):
    import sludge_sandbox.source_prefix_trial as module
    adapter,state=fixture(monkeypatch)
    original=module.integrate_exact
    def wrong(*args,**kwargs):
        result=original(*args,**kwargs)
        return replace(result,times_s=(*result.times_s[:-1],T(F(1,8192))))
    monkeypatch.setattr(module,'integrate_exact',wrong)
    out=run(adapter,state)
    assert out.reference.status=='completed'
    assert out.status=='numerical_failure' and out.reason=='trial_reference_incomplete_interval'
    assert out.discrepancy is None


def test_wrapper_rejects_direct_discrepancy_two_without_division(monkeypatch):
    import sludge_sandbox.source_prefix_trial as module
    adapter,state=fixture(monkeypatch)
    monkeypatch.setattr(module,'normalized_prefix_discrepancy',lambda *a:2.)
    out=run(adapter,state)
    assert out.status=='numerical_failure' and out.discrepancy==2.
    assert out.reason=='source_trial_reference_discrepancy'


def test_programmed_actual_source_positive_trial(monkeypatch):
    from test_programmed_source_wet_column import setup as furnace_setup
    from test_source_liquid_column import config
    column,states=furnace_setup(monkeypatch,count=1)
    column=replace(column,base=replace(column.base,liquid_transport=config(1)))
    adapter=ExactSourceColumn(column)
    out=run(adapter,adapter.pack(states))
    assert out.status=='validated_positive_numerical_trial',out.reason
    assert all(c.evaluation.source_evaluation.boundary.time==c.time for c in out.captures)
    out.check()


def test_failed_terminal_attempt_input_and_failure_text_cannot_be_changed(monkeypatch):
    from sludge_sandbox.integration import ConservedState
    adapter,state=fixture(monkeypatch)
    original=ExactSourceColumn.evaluate;count=0
    def fail(self,current,when):
        nonlocal count
        count+=1
        if count==3:raise DomainExit('actual-terminal-failure')
        return original(self,current,when)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',fail)
    out=run(adapter,state)
    old=out.captures[-1]
    changed=ConservedState(old.state.amounts_mol+1,old.state.internal_energy_j,old.state.energy_model_identity)
    for capture in (replace(old,state=changed),replace(old,failure='invented-failure')):
        with pytest.raises(ValueError,match='binding'):
            replace(out,captures=(*out.captures[:-1],capture)).check()


def test_reference_can_recover_from_actual_domain_exit_attempt(monkeypatch):
    adapter,state=fixture(monkeypatch)
    original=ExactSourceColumn.evaluate;count=0
    def once(self,current,when):
        nonlocal count
        count+=1
        if count==6:raise DomainExit('recoverable-trial-domain')
        return original(self,current,when)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',once)
    policy=replace(POLICY,initial_step_s=1/1024,maximum_step_s=1/1024,maximum_wall_seconds=20.)
    out=evaluate_source_prefix_trial(adapter,state,start=T(F()),end=T(F(1,1024)),
        integration_policy=policy,maximum_callbacks=32)
    assert out.reference.status=='completed'
    assert out.status=='validated_positive_numerical_trial',out.reason
    assert out.reference.rejected_trials>=1 and out.captures[5].failure=='recoverable-trial-domain'
    assert out.discrepancy<=1
    out.check()


@pytest.mark.parametrize('error',[DomainExit(),IntegrationError(),ValueError()])
def test_empty_exception_message_still_has_recorded_failure(monkeypatch,error):
    adapter,state=fixture(monkeypatch)
    def fail(*args):raise error
    monkeypatch.setattr(ExactSourceColumn,'evaluate',fail)
    out=run(adapter,state)
    assert len(out.captures)==1 and out.captures[0].failure==''
    assert out.captures[0].failure_kind in ('DomainExit','IntegrationError')
    out.check()
