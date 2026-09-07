"""Dry ordinary continuation must retain adaptive history until the next node."""
from dataclasses import replace
from fractions import Fraction
import math
import numpy as np
import pytest
from sludge_sandbox.depletion_integration import ManufacturedDepletionAdapter,DepletionEvaluation,integrate_depletion
from sludge_sandbox.integration import ConservedState,Rates
from test_depletion_integration import policies


def relaxation_operator(target=1000.,knots=()):
    def evaluate(state,t,modes):
        power=.01*(target-float(state.internal_energy_j[0]))
        return DepletionEvaluation(Rates(np.zeros((2,2)),np.zeros(2),np.zeros((1,2)),np.array([power])),
            (0.,),(float(state.internal_energy_j[0])/2,),(0.,),(1e5,),(0.,))
    return ManufacturedDepletionAdapter(evaluate_callback=evaluate,liquid_index=0,water_vapor_index=1,
        interfaces=('depleted_no_nucleation',),program_knots_s=knots,source_ids=('manufactured:dry-relaxation-ode-v1',))


def dry_policy():
    p,e=policies()
    # Keep the existing ordinary error policy; only time/resource scales change.
    p=replace(p,initial_step_s=2.,maximum_step_s=2.,maximum_rejections=100,maximum_steps=5000,
        maximum_wall_seconds=30.)
    return p,e


@pytest.mark.parametrize('target',[1000.,200.])
def test_all_dry_relaxation_keeps_adaptive_history_and_exact_prefix(target):
    p,e=dry_policy();initial=ConservedState([[0.,.01]],[600.])
    out=integrate_depletion(initial,relaxation_operator(target,knots=(300.,)),start_s=0,end_s=600.,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert 300. in out.times_s and out.times_s[-1]==600.
    assert out.rejected_trials<100 and not out.events
    total=Fraction()
    for step,state in zip(out.steps,out.states[1:]):
        assert not step.start_s<300.<step.end_s
        total+=Fraction(float(step.cell_work_j[0]))
        assert abs(Fraction(float(state.internal_energy_j[0]))-Fraction(600.)-total)<=Fraction(1e-8)
        assert np.array_equal(state.amounts_mol,initial.amounts_mol)
    exact=target+(600.-target)*math.exp(-.01*600.)
    assert abs(float(out.states[-1].internal_energy_j[0])-exact)<=1e-4
    assert out.cumulative_energy_j==(total,)


def test_dry_coast_still_enforces_global_panel_limit():
    p,e=dry_policy();p=replace(p,maximum_steps=3)
    out=integrate_depletion(ConservedState([[0.,.01]],[600.]),relaxation_operator(),start_s=0,end_s=600.,integration_policy=p,event_policy=e)
    assert out.status=='resource_limit'
    assert len(out.steps)<=3 and out.times_s[-1]<600.
    assert not out.events


def test_dry_continuation_stops_at_node_and_uses_changed_forcing():
    def evaluate(state,t,modes):
        target=1000.-2*max(t-300.,0.)
        power=.01*(target-float(state.internal_energy_j[0]))
        return DepletionEvaluation(Rates(np.zeros((2,2)),np.zeros(2),np.zeros((1,2)),np.array([power])),
            (0.,),(float(state.internal_energy_j[0])/2,),(0.,),(1e5,),(0.,))
    op=replace(relaxation_operator(),evaluate_callback=evaluate,program_knots_s=(300.,))
    p,e=dry_policy()
    out=integrate_depletion(ConservedState([[0.,.01]],[600.]),op,start_s=0,end_s=600.,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert 300. in out.times_s
    u300=1000.-400.*math.exp(-3.)
    # Exact solution for a continuous linear target after the program node.
    exact=1000.-2*300+200+(u300-1000.-200)*math.exp(-3.)
    assert abs(out.states[-1].internal_energy_j[0]-exact)<=1e-4
    assert all(not s.start_s<300.<s.end_s for s in out.steps)
    assert any(s.cell_work_j[0]<0 for s in out.steps if s.start_s>300.)


def test_wet_zero_rate_is_not_treated_as_all_dry():
    # The initial rate is zero. Later forcing activates evaporation; only
    # explicit interface mode may select the long dry-continuation path.
    def evaluate(state,t,modes):
        r=.001*max(t-.125,0) if modes[0]=='existing_liquid' else 0.
        return DepletionEvaluation(Rates(np.zeros((2,2)),np.zeros(2),np.array([[-r,r]]),np.zeros(1)),
            (r,),(300.,),(0.,),(1e5,),(0.,))
    op=replace(relaxation_operator(),evaluate_callback=evaluate,interfaces=('existing_liquid',),program_knots_s=(.125,))
    p,e=policies();p=replace(p,initial_step_s=1/64,maximum_step_s=1/64)
    out=integrate_depletion(ConservedState([[.5*.001*.125**2,.01]],[600.]),op,start_s=0,end_s=.375,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert len(out.events)==1 and abs(out.events[0].time_s-.25)<=1e-7
