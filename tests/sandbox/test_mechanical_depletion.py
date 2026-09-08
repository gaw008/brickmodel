import math
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState,Rates
from test_depletion_integration import policies

import sludge_sandbox.depletion_integration as m


def fixture(method='euler',missing=False):
    p,e=policies()
    p=replace(p,relative_tolerance=1e-12,energy_absolute_tolerance_j=1e-11,stretch_absolute_tolerance=1e-11,stretch_scale=1.,maximum_wall_seconds=10.)
    e=m.DepletionPolicy(**{k:v for k,v in vars(e).items() if k!='terminal_method'},terminal_method=method)
    def callback(state,t,modes):
        n=state.mechanical_stretches[0]
        sink=.001 if modes[0]=='existing_liquid' else 0.
        rates=Rates(np.zeros((2,2)),np.zeros(2),[[-sink,sink]],[n],
                    mechanical_rates_per_s=None if missing else [n,.2])
        return m.DepletionEvaluation(rates,(sink,),(300.,),(0.,),(0.,),(0.,))
    op=m.ManufacturedDepletionAdapter(evaluate_callback=callback,liquid_index=0,water_vapor_index=1,
        interfaces=('existing_liquid',),program_knots_s=(),source_ids=('manufactured:mechanical-depletion',))
    initial=ConservedState([[1e-4,0.]],[600.],mechanical_stretches=[1.,1.])
    return p,e,op,initial


@pytest.mark.parametrize('method',['euler','affine_midpoint'])
def test_real_mechanical_event_and_original_prefix(method):
    p,e,op,initial=fixture(method)
    run=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
    assert run.status=='completed',run.reason
    assert len(run.events)==1 and run.states[-1].amounts_mol[0,0]==0.
    assert abs(run.events[0].time_s-.1)<1e-8
    total=[F(),F()];exact=[F(),F()];rounding=[F(),F()]
    for step,t,state in zip(run.steps,run.times_s[1:],run.states[1:]):
        assert abs(state.mechanical_stretches[0]-math.exp(t))<1e-8
        assert abs(state.mechanical_stretches[1]-(1+.2*t))<1e-10
        assert abs(state.internal_energy_j[0]-(599.+math.exp(t)))<1e-8
        for i in range(2):
            inc=F(float(step.stretch_increment[i]));q=step.stretch_quadrature_roundoff[i]
            total[i]+=inc;exact[i]+=inc-q;rounding[i]+=abs(q)
            change=F(float(state.mechanical_stretches[i]))-F(1.)
            assert abs(change-total[i])<=F(p.stretch_absolute_tolerance)
            assert abs(change-exact[i])<=F(p.stretch_absolute_tolerance)
            assert rounding[i]<=F(p.stretch_absolute_tolerance)
    assert run.events[0].terminal_panel.stretch_increment is not None


def test_missing_rates_fails_without_commit():
    p,e,op,initial=fixture(missing=True)
    run=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
    assert run.status!='completed' and run.states==(initial,) and not run.steps


def test_cancel_keeps_actual_mechanical_initial():
    p,e,op,initial=fixture()
    run=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e,cancel=lambda:True)
    assert run.status=='cancelled' and run.states==(initial,) and not run.events


def test_affine_panel_rejects_negative_interior_with_positive_endpoints():
    # n(h)=1-8h+8h²: both endpoints 1, midpoint -1.
    _,_,_,state=fixture()
    def rates(v):return Rates(np.zeros((2,2)),np.zeros(2),np.zeros((1,2)),[0.],mechanical_rates_per_s=v)
    with pytest.raises(m._Failure,match='mechanical_panel_nonpositive_path'):
        m._mechanical_panel(state,rates([-8.,0.]),F(1),rates([0.,0.]),F(1,2))


def test_affine_panel_exact_integral_and_signed_roundoff():
    _,_,_,state=fixture()
    def rates(v):return Rates(np.zeros((2,2)),np.zeros(2),np.zeros((1,2)),[0.],mechanical_rates_per_s=v)
    h=F(.13);hm=F(.07)
    after,inc,qs=m._mechanical_panel(state,rates([.2,-.1]),h,rates([.3,.1]),hm)
    for i,(a,b) in enumerate(zip((.2,-.1),(.3,.1))):
        exact=h*F(a)+h*h*(F(b)-F(a))/(2*hm)
        assert F(float(inc[i]))-qs[i]==exact
        assert after[i]==float(F(1)+F(float(inc[i])))


def test_explicit_stretch_policy_required():
    p,e,op,initial=fixture()
    with pytest.raises(ValueError):
        m.integrate_depletion(initial,op,start_s=0.,end_s=.2,
            integration_policy=replace(p,stretch_absolute_tolerance=None,stretch_scale=None),event_policy=e)


def test_terminal_cancellation_rolls_back_event_branch():
    p,e,op,initial=fixture('affine_midpoint');called=[]
    original=op.evaluate_callback
    def callback(state,t,modes):
        called.append(modes[0])
        return original(state,t,modes)
    op=replace(op,evaluate_callback=callback)
    run=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e,
        cancel=lambda:'depleted_no_nucleation' in called)
    assert run.status=='cancelled' and not run.events
    assert len(run.steps)>0 and run.times_s[-1]<.1
    assert all(state.mechanical_stretches is not None for state in run.states)
    assert all(state.amounts_mol[0,0]>0 for state in run.states)


def test_cumulative_signed_quadrature_cannot_reset(monkeypatch):
    p,e,op,initial=fixture();original=m.integrate
    def corrupt(*args,**kwargs):
        run=original(*args,**kwargs)
        if run.steps:
            step=run.steps[0]
            # Each injected error fits a local budget; accumulation must fail.
            q=F(p.stretch_absolute_tolerance)*F(3,5)
            step=replace(step,stretch_quadrature_roundoff=(q,q))
            return replace(run,steps=(step,)+run.steps[1:])
        return run
    monkeypatch.setattr(m,'integrate',corrupt)
    run=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
    assert run.status=='failed' and run.reason=='cross_segment_stretch_prefix_roundoff'
    assert not run.events and len(run.steps)>0


def test_depletion_writeback_keeps_stretches_exact():
    # Main event tests already exercise correction when needed; use actual
    # recorded event before/after arrays to check all step states are immutable.
    p,e,op,initial=fixture('affine_midpoint')
    run=m.integrate_depletion(initial,op,start_s=0.,end_s=.12,integration_policy=p,event_policy=e)
    assert run.status=='completed',run.reason
    for state in run.states:
        with pytest.raises(ValueError):state.mechanical_stretches.flags.writeable=True
    assert run.events[0].stretch_difference is not None
    assert run.events[0].stretch_difference<=p.stretch_absolute_tolerance
    assert any('event_stretches' in r.comparison_details for r in run.refinements)


def test_mechanical_common_difference_blocks_otherwise_equal_event(monkeypatch):
    p,e,op,initial=fixture();e=replace(e,maximum_refinements=4)
    switches=[]
    def callback(state,t,modes):
        sink=.001 if modes[0]=='existing_liquid' else 0.
        rates=Rates(np.zeros((2,2)),np.zeros(2),[[-sink,sink]],[0.],mechanical_rates_per_s=[0.,0.])
        return m.DepletionEvaluation(rates,(sink,),(300.,),(0.,),(0.,),(0.,))
    op=replace(op,evaluate_callback=callback)
    switch=m.ManufacturedDepletionAdapter.with_depleted_cells
    def altered(self,state,cells):
        dry=switch(self,state,cells);switches.append(1);bias=len(switches)*.01
        base=dry.evaluate_callback
        def biased(state,t,modes):
            out=base(state,t,modes)
            return replace(out,rates=replace(out.rates,mechanical_rates_per_s=[bias,0.]))
        return replace(dry,evaluate_callback=biased)
    monkeypatch.setattr(m.ManufacturedDepletionAdapter,'with_depleted_cells',altered)
    run=m.integrate_depletion(initial,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
    assert run.status!='completed' and not run.events
    comparisons=[r for r in run.refinements if r.status=='comparison_fail']
    assert comparisons
    assert all(all(value<=limit for value,limit in zip(r.differences[:5],
        (e.time_absolute_s,e.amount_absolute_mol,e.energy_absolute_j,e.temperature_absolute_k,e.pressure_absolute_pa)))
        for r in comparisons)
    assert all(r.comparison_details['common_stretches']['maximum']>p.stretch_absolute_tolerance for r in comparisons)


@pytest.mark.parametrize('method',['euler','affine_midpoint'])
def test_nested_independent_approach_preserves_mechanical_fields(method):
    p,e,op,initial=fixture(method)
    e=replace(e,nested_approach=m.NestedApproachPolicy(maximum_step_s=.005,reuse_ordinary_spine=True))
    op=replace(op,deterministic_contract=('manufactured:pure-coupled-rates-v1',))
    run=m.integrate_depletion(initial,op,start_s=0.,end_s=.12,integration_policy=p,event_policy=e)
    assert run.status=='completed',run.reason
    independent=[r for r in run.refinements if r.status=='independent_approach_pass']
    assert independent and run.events[0].stretch_difference<=p.stretch_absolute_tolerance
    assert all(r.comparison_details['approach_grid_a_s']!=r.comparison_details['approach_grid_b_s'] for r in independent)
