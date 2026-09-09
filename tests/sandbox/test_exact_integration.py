from dataclasses import replace
from fractions import Fraction as F
import math
import numpy as np
import pytest
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_boundary_program import ExactProgramView
from sludge_sandbox.boundary_program import ScalarProgram,ProgramIdentity
from sludge_sandbox.integration import ConservedState,Rates,IntegrationPolicy,IntegrationError,DomainExit,StepLedger,IntegrationResult
from sludge_sandbox.exact_integration import integrate_exact,ExactStepLedger,ExactIntegrationResult


def policy():
    return IntegrationPolicy(initial_step_s=2**-30,maximum_step_s=2**-30,minimum_step_s=1e-14,
        relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-8,
        amount_scale_mol=1e-4,energy_scale_j=1.,maximum_steps=5000,maximum_rejections=100,maximum_wall_seconds=30.,
        stretch_absolute_tolerance=1e-9,stretch_scale=1.)


def rates(state,power=2.):
    return Rates(np.array([[.2,0.],[.1,0.],[0.,0.]]),np.array([3.,1.,0.]),
                 np.array([[-.5,.5],[-.25,.25]]),np.array([power,power]),
                 {'body':np.array([power+1,power+1]),'mechanical_constraint':np.array([-1.,-1.])},
                 mechanical_rates_per_s=np.array([.1,.2,.3]))


def initial():return ConservedState([[1.,0.],[2.,0.]],[10.,20.],mechanical_stretches=[1.,1.,1.])


def audit(result,p):
    first=result.states[0];n=[F() for _ in first.amounts_mol.flat];u=[F(),F()];stretch=[F(),F(),F()];comp=[F(),F()]
    for k,(ledger,state) in enumerate(zip(result.steps,result.states[1:])):
        assert type(ledger) is ExactStepLedger and not isinstance(ledger,StepLedger)
        assert ledger.start_s==result.times_s[k] and ledger.end_s==result.times_s[k+1]
        assert F(p.minimum_step_s)<=ledger.end_s.elapsed_since(ledger.start_s)<=F(p.maximum_step_s)
        for flat,(i,j) in enumerate(np.ndindex(first.amounts_mol.shape)):
            n[flat]+=F(float(ledger.face_species_mol[i,j]))-F(float(ledger.face_species_mol[i+1,j]))+F(float(ledger.reaction_species_mol[i,j]))
            assert abs(F(float(state.amounts_mol[i,j]))-F(float(first.amounts_mol[i,j]))-n[flat])<=F(p.amount_absolute_tolerance_mol)
        for i in range(2):
            u[i]+=F(float(ledger.face_energy_j[i]))-F(float(ledger.face_energy_j[i+1]))+F(float(ledger.cell_work_j[i]))
            assert abs(F(float(state.internal_energy_j[i]))-F(float(first.internal_energy_j[i]))-u[i])<=F(p.energy_absolute_tolerance_j)
            comp[i]+=abs(ledger.component_sum_residual_j[i])
            assert comp[i]<=F(p.energy_absolute_tolerance_j)
        for i in range(3):
            stretch[i]+=F(float(ledger.stretch_increment[i]))-ledger.stretch_quadrature_roundoff[i]
            assert abs(F(float(state.mechanical_stretches[i]))-F(float(first.mechanical_stretches[i]))-stretch[i])<=F(p.stretch_absolute_tolerance)


def test_autonomous_origin_translation_coincident_displays_and_all_ledgers():
    p=policy();duration=F(1,2**28);outputs=[]
    for origin in (F(),F(10**12)):
        calls=[]
        def op(state,t):
            assert type(t) is T
            calls.append(t);return rates(state)
        result=integrate_exact(initial(),op,start_s=T(origin),end_s=T(origin+duration),policy=p)
        assert result.status=='completed',result.reason
        assert type(result) is ExactIntegrationResult and not isinstance(result,IntegrationResult)
        assert len(result.steps)==4 and result.evaluations==29
        assert all(t.seconds>=origin for t in calls)
        audit(result,p);outputs.append(result)
    for a,b in zip(outputs[0].states,outputs[1].states):
        np.testing.assert_array_equal(a.amounts_mol,b.amounts_mol)
        np.testing.assert_array_equal(a.internal_energy_j,b.internal_energy_j)
    assert len({t.display().seconds_binary64 for t in outputs[1].times_s})==1
    np.testing.assert_allclose(outputs[1].states[-1].internal_energy_j,[10+4*float(duration),20+3*float(duration)],rtol=0,atol=1e-12)


def test_translated_piecewise_forcing_exact_clips_and_analytic_heat():
    p=replace(policy(),initial_step_s=2**-28,maximum_step_s=2**-28)
    h=2**-30;origin=F(10**12)
    program=ScalarProgram(identity=ProgramIdentity(program_id='analytic',version='1',classification='virtual_design_choice',source_ids=('analytic',)),
        knot_times_s=(0.,h,3*h),values=(1e6,3e6,1e6),unit='W')
    view=ExactProgramView(program,origin);start,end=view.knots[0],view.knots[-1]
    result=integrate_exact(initial(),lambda s,t:rates(s,view.at(t)),start_s=start,end_s=end,policy=p,breakpoints_s=view.breakpoints(start,end))
    assert result.status=='completed',result.reason
    assert view.knots[1] in result.times_s
    assert all(not step.start_s<view.knots[1]<step.end_s for step in result.steps)
    duration=F(3)*F(h);heat=F(2_000_000)*duration
    np.testing.assert_allclose(result.states[-1].internal_energy_j,[float(F(10)+heat+2*duration),float(F(20)+heat+duration)],rtol=0,atol=1e-12)
    audit(result,p)


def test_no_silent_minimum_step_relaxation():
    p=policy();calls=[]
    result=integrate_exact(initial(),lambda s,t:(calls.append(t) or rates(s)),start_s=T(F(10**12)),end_s=T(F(10**12)+F(1,10**15)),policy=p)
    assert result.reason=='minimum_time_step' and len(calls)==1 and result.steps==()


def test_cancel_preserves_accepted_prefix():
    p=policy();calls=[]
    result=integrate_exact(initial(),lambda s,t:(calls.append(t) or rates(s)),start_s=T(F()),end_s=T(F(1,2**28)),policy=p,cancel=lambda:len(calls)>=9)
    assert result.status=='cancelled' and len(result.steps)==1
    assert result.attempted_trials==2
    audit(result,p)


def test_real_nonlinearity_rejects_trials_and_uses_original_error_scale():
    p=replace(policy(),initial_step_s=.1,maximum_step_s=.1)
    def op(state,t):
        out=rates(state)
        return replace(out,reaction_species_mol_s=np.array([[state.amounts_mol[0,0],0.],[0.,0.]]))
    result=integrate_exact(initial(),op,start_s=T(F()),end_s=T(F.from_float(.1)),policy=p)
    assert result.status=='completed',result.reason
    assert result.rejected_trials>0 and result.attempted_trials==len(result.steps)+result.rejected_trials
    assert abs(result.states[-1].amounts_mol[0,0]-(1.1*math.exp(.1)-.1))<2e-6
    audit(result,p)


def test_domain_initial_and_trial_failures_preserve_prefix():
    p=policy()
    def initial_fail(state,t):raise DomainExit('initial_domain')
    result=integrate_exact(initial(),initial_fail,start_s=T(F()),end_s=T(F(1,2**28)),policy=p)
    assert result.status=='domain_exit' and result.evaluations==1 and result.steps==()
    limit=T(F(1,2**30))
    def later(state,t):
        if t>limit:raise DomainExit('later_domain')
        return rates(state)
    result=integrate_exact(initial(),later,start_s=T(F()),end_s=T(F(1,2**28)),policy=p)
    assert result.status=='domain_exit' and result.times_s[-1]==limit
    assert result.rejected_trials>0
    audit(result,p)


def test_resource_step_limit_and_schema_change():
    p=replace(policy(),maximum_steps=1)
    result=integrate_exact(initial(),lambda s,t:rates(s),start_s=T(F()),end_s=T(F(1,2**28)),policy=p)
    assert result.reason=='accepted_step_limit' and len(result.steps)==1
    calls=[]
    def changing(state,t):
        calls.append(t);out=rates(state)
        return replace(out,cell_power_components_w=None) if len(calls)>2 else out
    result=integrate_exact(initial(),changing,start_s=T(F()),end_s=T(F(1,2**28)),policy=policy())
    assert result.reason=='component_work_schema_changed' and result.steps==()


def test_implicit_times_or_bad_breakpoints_rejected():
    for changes in ({'start_s':0.},{'end_s':True},{'breakpoints_s':(.5,)},{'breakpoints_s':(T(F(1,2)),T(F(1,2)))}):
        args=dict(start_s=T(F()),end_s=T(F(1)),policy=policy());args.update(changes)
        with pytest.raises(IntegrationError):integrate_exact(initial(),lambda s,t:rates(s),**args)


def test_all_actual_rk_stage_times_are_exact_quarters():
    p=policy();origin=F(10**12);h=F(p.initial_step_s);calls=[]
    result=integrate_exact(initial(),lambda s,t:(calls.append(t.seconds-origin) or rates(s)),start_s=T(origin),end_s=T(origin+h),policy=p)
    assert result.status=='completed'
    assert calls==[F(),F(),h,F(),h/2,h/2,h,h]
    assert result.steps[0].end_s.elapsed_since(result.steps[0].start_s)==h


def test_no_mechanical_state_and_zero_inventory_extraction_guard():
    state=ConservedState([[1.,0.],[2.,0.]],[10.,20.]);p=policy()
    def op(s,t):return replace(rates(s),mechanical_rates_per_s=None,cell_power_components_w=None)
    r=integrate_exact(state,op,start_s=T(F()),end_s=T(F(p.initial_step_s)),policy=p)
    assert r.status=='completed' and r.steps[0].stretch_increment is None
    assert r.cumulative_absolute_component_residual_j is None
    zero=ConservedState([[0.,0.],[2.,0.]],[10.,20.])
    r=integrate_exact(zero,op,start_s=T(F()),end_s=T(F(p.initial_step_s)),policy=p)
    assert r.reason=='outflow_from_zero_inventory' and r.steps==()


def test_rejection_resource_budget_is_not_reset():
    p=replace(policy(),maximum_rejections=1)
    def op(s,t):
        if t.seconds>0:raise DomainExit('strict_domain')
        return rates(s)
    r=integrate_exact(initial(),op,start_s=T(F()),end_s=T(F(p.initial_step_s)),policy=p)
    assert r.reason=='rejected_trial_limit' and r.rejected_trials==r.attempted_trials==1
    assert r.steps==()


def test_wall_budget_uses_monotonic_clock_without_extra_operator_call(monkeypatch):
    import sludge_sandbox.exact_integration as m
    from types import SimpleNamespace
    ticks=iter((0.,31.,32.));calls=[]
    monkeypatch.setattr(m,'time',SimpleNamespace(monotonic=lambda:next(ticks)))
    r=m.integrate_exact(initial(),lambda s,t:(calls.append(t) or rates(s)),start_s=T(F()),end_s=T(F(1)),policy=policy())
    assert r.reason=='wall_time_limit' and r.status=='resource_limit' and calls==[]


def test_invalid_accepted_state_is_not_committed():
    calls=[];p=policy()
    def op(s,t):
        calls.append(t)
        if len(calls)==8:raise DomainExit('accepted_domain_rejection')
        return rates(s)
    r=integrate_exact(initial(),op,start_s=T(F()),end_s=T(F(p.initial_step_s)),policy=p)
    assert r.status=='completed',r.reason
    assert r.rejected_trials==1 and len(r.steps)==2
    audit(r,p)


def test_mechanical_only_error_forces_refinement_and_closes_exact_quadrature():
    p=replace(policy(),initial_step_s=.1,maximum_step_s=.1)
    def op(s,t):
        return Rates(np.zeros((3,2)),np.zeros(3),np.zeros((2,2)),np.zeros(2),{'body':np.zeros(2)},mechanical_rates_per_s=s.mechanical_stretches)
    r=integrate_exact(initial(),op,start_s=T(F()),end_s=T(F(.1)),policy=p)
    assert r.status=='completed' and r.rejected_trials>0
    assert max(abs(r.states[-1].mechanical_stretches-math.exp(.1)))<2e-6
    audit(r,p)
    with pytest.raises(ValueError):r.steps[0].stretch_increment[0]=99.


def test_positivity_rejects_large_trial_without_clipping_inventory():
    p=replace(policy(),initial_step_s=.1,maximum_step_s=.1)
    def op(s,t):
        return Rates(np.zeros((3,2)),np.zeros(3),np.array([[-20*s.amounts_mol[0,0],0.],[0.,0.]]),np.zeros(2),{'body':np.zeros(2)},mechanical_rates_per_s=np.zeros(3))
    r=integrate_exact(initial(),op,start_s=T(F()),end_s=T(F(.1)),policy=p)
    assert r.status=='completed',r.reason
    assert r.rejected_trials>0
    assert all(s.amounts_mol[0,0]>0 for s in r.states)
    assert abs(r.states[-1].amounts_mol[0,0]-math.exp(-2))<2e-6
    audit(r,p)


def test_nonmultiple_endpoint_plans_two_legal_intervals_without_dropping_tail():
    p=replace(policy(),initial_step_s=.3,maximum_step_s=.3)
    r=integrate_exact(initial(),lambda s,t:replace(rates(s),reaction_species_mol_s=np.zeros((2,2))),start_s=T(F()),end_s=T(F(3)),policy=p)
    assert r.status=='completed',r.reason
    assert r.times_s[-1]==T(F(3))
    assert len(r.steps)==11
    assert sum((s.end_s.elapsed_since(s.start_s) for s in r.steps),F())==3
    audit(r,p)
