"""Manufactured accounting tests, no water EOS and no altered material gates."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from test_depletion_integration import policies, oracle
from sludge_sandbox.integration import ConservedState, Rates
from sludge_sandbox.depletion_integration import integrate_depletion


def component_oracle(change_after=False, change_at=None):
    op=oracle(knots=(.05,.15))
    original=op.evaluate_callback
    def evaluate(s,t,m):
        obs=original(s,t,m)
        parts={'elastic':[.1], 'pore':[-.1], 'body':obs.rates.cell_power_w}
        if (change_after and m[0]!='existing_liquid') or (change_at is not None and t>=change_at):
            parts={'body':obs.rates.cell_power_w}
        return replace(obs,rates=replace(obs.rates,cell_power_components_w=parts))
    return replace(op,evaluate_callback=evaluate)


def run(op,**kw):
    p,e=policies()
    return integrate_depletion(ConservedState([[1e-4,0.]],[600.]),op,
        start_s=0,end_s=.2,integration_policy=p,event_policy=e,**kw)


def test_terminal_and_all_normal_components_preserved():
    out=run(component_oracle())
    assert out.status=='completed',out.reason
    assert len(out.events)==1
    prefix=F()
    for step in out.steps:
        assert set(step.cell_work_components_j)=={'elastic','pore','body'}
        represented=sum((F(float(v[0])) for v in step.cell_work_components_j.values()),F())
        assert represented+step.component_sum_residual_j[0]==F(float(step.cell_work_j[0]))
        prefix+=abs(step.component_sum_residual_j[0])
    assert out.cumulative_absolute_component_residual_j==(prefix,)
    terminal=out.events[0].terminal_panel
    exact=(F(terminal.end_s)-F(terminal.start_s))*F(.1)
    assert terminal.cell_work_components_j['elastic'][0]==float(exact)
    assert terminal.component_quadrature_roundoff_j['elastic']==(F(float(exact))-exact,)


@pytest.mark.parametrize('options',[{'change_after':True},{'change_at':.05}])
def test_schema_is_locked_across_trial_modes_and_segments(options):
    out=run(component_oracle(**options))
    assert out.status!='completed'
    assert 'component_work_schema_changed' in out.reason
    assert not out.events
    assert out.operator.interfaces==('existing_liquid',)


def test_default_none_propagates():
    out=run(oracle())
    assert out.status=='completed'
    assert out.cumulative_absolute_component_residual_j is None
    assert all(s.cell_work_components_j is None for s in out.steps)


def test_cancel_has_no_speculative_component_budget():
    out=run(component_oracle(),cancel=lambda:True)
    assert out.status=='cancelled'
    assert out.cumulative_absolute_component_residual_j is None
    assert not out.steps


def test_total_energy_binding_survives_terminal_and_normal_restart():
    p,e=policies();binding=('manufactured_total',('version','1'))
    out=integrate_depletion(ConservedState([[1e-4,0.]],[600.],energy_model_identity=binding),
        component_oracle(),start_s=0,end_s=.2,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert len(out.events)==1
    assert all(s.energy_model_identity==binding for s in out.states)


@pytest.mark.parametrize('budget,expect_refinement',[(3e-18,False),(4.4e-18,True)])
def test_cross_segment_absolute_budget_rejects_entire_path(budget,expect_refinement):
    p,e=policies();op=oracle(a=1/1024);old=op.evaluate_callback
    def evaluate(s,t,m):
        x=old(s,t,m)
        return replace(x,rates=replace(x.rates,cell_power_w=[.5],
            cell_power_components_w={'elastic':[.1],'body':[.4]}))
    op=replace(op,evaluate_callback=evaluate)
    out=integrate_depletion(ConservedState([[1/8192,0]],[0]),op,start_s=0,end_s=.25,
        integration_policy=replace(p,initial_step_s=1/32,maximum_step_s=1/32,
                                   energy_absolute_tolerance_j=budget),event_policy=e)
    assert out.status=='failed' and out.reason=='cross_segment_component_sum_roundoff'
    assert not out.events and not out.corrections
    assert out.operator.interfaces==('existing_liquid',)
    assert all(s.amounts_mol[0,0]>0 for s in out.states)
    exact=sum((abs(F(float(s.cell_work_j[0]))-sum((F(float(v[0]))
                 for v in s.cell_work_components_j.values()),F())) for s in out.steps),F())
    assert out.cumulative_absolute_component_residual_j==(exact,)
    assert exact<=F(budget)
    if expect_refinement:assert out.refinements


def test_terminal_subnormal_component_exact_error_is_retained():
    op=oracle();old=op.evaluate_callback;tiny=float.fromhex('0x0.0000000000001p-1022')
    def evaluate(s,t,m):
        x=old(s,t,m)
        return replace(x,rates=replace(x.rates,cell_power_components_w={
            'elastic':[tiny],'pore':[-tiny],'body':x.rates.cell_power_w}))
    out=run(replace(op,evaluate_callback=evaluate))
    assert out.status=='completed'
    step=out.events[0].terminal_panel
    exact=(F(step.end_s)-F(step.start_s))*F(tiny)
    assert exact>0 and step.cell_work_components_j['elastic'][0]==0
    assert step.component_quadrature_roundoff_j['elastic']==(-exact,)
    assert step.component_quadrature_roundoff_j['pore']==(exact,)


def test_cancel_after_committed_prefix_keeps_exact_components():
    op=component_oracle();old=op.evaluate_callback;stop=[False]
    def evaluate(s,t,m):
        x=old(s,t,m)
        if t>=.04:stop[0]=True
        return x
    out=run(replace(op,evaluate_callback=evaluate),cancel=lambda:stop[0])
    assert out.status=='cancelled'
    assert out.steps and not out.events
    assert all(s.cell_work_components_j is not None for s in out.steps)
    assert out.cumulative_absolute_component_residual_j==tuple(
        sum((abs(s.component_sum_residual_j[i]) for s in out.steps),F()) for i in range(1))
