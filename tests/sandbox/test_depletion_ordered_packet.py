"""Actual manufactured packet integration; no water backend or physical claim."""
from dataclasses import replace
import numpy as np
import pytest
from sludge_sandbox import depletion_integration as m
from sludge_sandbox.integration import ConservedState,Rates
from test_depletion_integration import policies


def setup(gap=1e-9,mixed_factor=2.,acceleration=0.):
    p,e=policies()
    p=replace(p,stretch_absolute_tolerance=1e-9,stretch_scale=1.)
    e=replace(e,terminal_method='affine_midpoint',ordered_event_policy='ordered_affine_packet_v1',
              nested_approach=m.NestedApproachPolicy(maximum_step_s=.001,reuse_ordinary_spine=False))
    calls=[]
    def callback(state,t,modes):
        calls.append((t,modes))
        sinks=[1. if modes[0]=='existing_liquid' else 0.,
               (1.+acceleration*t)*(mixed_factor if modes[0]!='existing_liquid' else 1.) if modes[1]=='existing_liquid' else 0.]
        power=[1. if modes[0]=='existing_liquid' else 3.,2. if modes[1]=='existing_liquid' else 4.]
        rates=Rates(np.zeros((3,2)),np.zeros(3),np.array([[-r,r] for r in sinks]),np.array(power),
                    {'body':power},mechanical_rates_per_s=np.array([.1,.2,.3]))
        return m.DepletionEvaluation(rates,tuple(sinks),tuple(state.internal_energy_j), (0.,0.),(1e5,1e5),(0.,0.))
    op=m.ManufacturedDepletionAdapter(evaluate_callback=callback,liquid_index=0,water_vapor_index=1,interfaces=('existing_liquid',)*2,program_knots_s=(),source_ids=('ordered-manufactured',))
    initial=ConservedState([[.01,0.],[.01+gap,0.]],[300.,301.],mechanical_stretches=[1.,1.,1.])
    return p,e,op,initial,calls


def run(gap=1e-9,**kwargs):
    p,e,op,state,calls=setup(gap,**kwargs)
    result=m.integrate_depletion(state,op,start_s=0.,end_s=.03,integration_policy=p,event_policy=e)
    return result,p,e,state,calls


def test_close_events_use_actual_mixed_rhs_and_one_atomic_packet():
    result,p,e,initial,calls=run()
    assert result.status=='completed',result.reason
    assert type(result) is m.OrderedPacketResult
    assert len(result.events)==2 and len(result.packets)==1
    t0,t1=[ev.time_s for ev in result.events]
    assert abs(t0-.01)<1e-12 and abs(t1-(.01+1e-9/2))<1e-12
    assert 0<t1-t0<e.time_absolute_s
    assert any(modes==('depleted_no_nucleation','existing_liquid') for _,modes in calls)
    np.testing.assert_allclose(result.states[-1].internal_energy_j,[300.+.01+3*.02,301.+2*t1+4*(.03-t1)],rtol=0,atol=1e-8)
    np.testing.assert_allclose(result.states[-1].mechanical_stretches,[1.003,1.006,1.009],rtol=0,atol=1e-9)
    assert len({id(ev.terminal_panel) for ev in result.events})==2
    assert any(ref.status=='independent_approach_pass' for ref in result.refinements)
    assert sum(ref.status=='comparison_pass' for ref in result.refinements)>=2


def test_default_still_rejects_initial_tangent_tie():
    p,e,op,state,_=setup()
    e=replace(e,ordered_event_policy=None)
    result=m.integrate_depletion(state,op,start_s=0.,end_s=.03,integration_policy=p,event_policy=e)
    assert result.status=='unsupported' and result.reason=='simultaneous_events_not_separated'
    assert type(result) is m.DepletionResult


def test_exact_coincident_surrogate_roots_remain_unsupported():
    result,*_=run(gap=0.,mixed_factor=1.)
    assert result.status=='unsupported' and result.reason=='ordered_packet_roots_not_strictly_separated'
    assert result.events==() and result.packets==()
    assert result.times_s[-1]<.01


def test_equal_initial_tangents_split_by_acceleration_without_inventory_perturbation():
    from decimal import Decimal,localcontext
    result,p,e,initial,calls=run(gap=0.,mixed_factor=1.,acceleration=100.)
    assert result.status=='completed',result.reason
    assert [ev.cell_index for ev in result.events]==[1,0]
    with localcontext() as ctx:
        ctx.prec=60
        first=float((Decimal(3).sqrt()-1)/100)
    assert abs(result.events[0].time_s-first)<e.time_absolute_s
    assert abs(result.events[1].time_s-.01)<e.time_absolute_s
    for frame in result.packets[0]:
        roots=[row['root_interval_s'] for row in frame.root_order['roots'] if row['root_interval_s'] is not None]
        roots.sort()
        assert all(roots[0][1]<r[0] for r in roots[1:])


def test_failure_during_mixed_rhs_keeps_only_original_accepted_prefix():
    from sludge_sandbox.integration import IntegrationError
    p,e,op,initial,calls=setup()
    callback=op.evaluate_callback
    def fail(state,t,modes):
        if modes[0]=='depleted_no_nucleation':raise IntegrationError('deliberate_mixed_failure')
        return callback(state,t,modes)
    op=replace(op,evaluate_callback=fail)
    result=m.integrate_depletion(initial,op,start_s=0.,end_s=.03,integration_policy=p,event_policy=e)
    assert result.status!='completed' and 'deliberate_mixed_failure' in result.reason
    assert result.events==result.packets==() and result.times_s[-1]<.01
    assert all(s.amounts_mol[0,0]>0 for s in result.states)
    assert result.attempted_steps>len(result.steps)


def test_cancellation_in_speculative_packet_does_not_commit_first_event():
    p,e,op,initial,calls=setup()
    result=m.integrate_depletion(initial,op,start_s=0.,end_s=.03,integration_policy=p,event_policy=e,
        cancel=lambda:any(modes[0]=='depleted_no_nucleation' for _,modes in calls))
    assert result.status=='cancelled'
    assert result.events==result.packets==() and result.times_s[-1]<.01
    assert result.operator.interfaces==('existing_liquid','existing_liquid')


def test_packet_continuation_explicitly_rejected_before_callback():
    p,e,op,initial,calls=setup()
    with pytest.raises(m.DepletionIntegrationError,match='packet_continuation_not_admitted'):
        m.integrate_depletion(initial,op,start_s=0.,end_s=.03,integration_policy=p,event_policy=e,continuation=object())
    assert calls==[]


def test_packet_policy_requires_real_independent_approach_and_affine():
    p,e,op,initial,calls=setup()
    for changes in ({'terminal_method':'euler'},{'nested_approach':None},{'ordered_event_policy':True}):
        with pytest.raises(m.DepletionIntegrationError):replace(e,**changes)


def test_source_change_in_terminal_callback_rolls_back_packet():
    p,e,op,initial,calls=setup();callback=op.evaluate_callback
    def mutate(state,t,modes):
        value=callback(state,t,modes)
        if modes[0]=='depleted_no_nucleation':
            object.__setattr__(op,'source_ids',('changed-source',))
        return value
    op=replace(op,evaluate_callback=mutate)
    result=m.integrate_depletion(initial,op,start_s=0.,end_s=.03,integration_policy=p,event_policy=e)
    assert result.status!='completed' and 'binding_changed' in result.reason
    assert result.events==result.packets==()


def test_refinement_disagreement_does_not_accept_a_partial_packet():
    p,e,op,initial,calls=setup();callback=op.evaluate_callback
    counter={'branch':0,'wet':True}
    def changing(state,t,modes):
        wet=modes[0]=='existing_liquid'
        if counter['wet'] and not wet:counter['branch']+=1
        counter['wet']=wet
        value=callback(state,t,modes)
        if not wet:
            powers=np.array([float(counter['branch']),float(counter['branch'])])
            value=replace(value,rates=replace(value.rates,cell_power_w=powers,cell_power_components_w={'body':powers}))
        return value
    op=replace(op,evaluate_callback=changing)
    result=m.integrate_depletion(initial,op,start_s=0.,end_s=.03,integration_policy=p,event_policy=e)
    assert result.status!='completed'
    assert result.events==result.packets==()
    assert any(ref.status=='comparison_fail' for ref in result.refinements)


def test_unrepresentable_close_event_spacing_is_not_an_epsilon_step():
    gap=float(np.nextafter(.01,np.inf)-.01)
    result,*_=run(gap=gap,mixed_factor=1.)
    assert result.status!='completed'
    assert result.events==result.packets==()


def test_every_frame_has_real_common_time_and_comparison_budget_metadata():
    result,*_=run()
    assert result.status=='completed',result.reason
    frames=result.packets[0]
    assert frames[0].event.common_time_s==frames[1].event.common_time_s
    assert frames[1].event.common_time_s>frames[1].event.time_s
    for frame in frames:
        assert frame.event.previous_time_s>0 and frame.event.coarse_time_s>0
        assert frame.event.common_energy_difference_j==frames[0].event.common_energy_difference_j


def test_stage_replan_control_flow_discards_preview_and_keeps_real_prefix(monkeypatch):
    """Inject one positive-stage preview only; actual subsequent integration is real.

    This exercises transaction control, not an assertion that the injected stage
    is a physical RK solution of the manufactured constant-sink model.
    """
    base_integrate=m.integrate;injected=[]
    def intercept(state,operator,**kwargs):
        if not injected and state.amounts_mol[0,0]==0 and state.amounts_mol[1,0]>0:
            injected.append(True)
            def preview(stage,t):
                amounts=np.array(stage.amounts_mol);amounts[1,0]=1e-30
                altered=ConservedState(amounts,stage.internal_energy_j,stage.energy_model_identity,
                                       mechanical_stretches=stage.mechanical_stretches)
                return operator(altered,t)
            return base_integrate(state,preview,**kwargs)
        return base_integrate(state,operator,**kwargs)
    monkeypatch.setattr(m,'integrate',intercept)
    result,*_=run(gap=.003)
    assert injected and result.status=='completed',result.reason
    assert len(result.events)==2
    assert all(s.amounts_mol[1,0]!=1e-30 for s in result.states)
    assert abs(result.events[1].time_s-.0115)<1e-10
    assert result.attempted_steps>len(result.steps)


def test_stage_replan_without_localizable_root_stops_without_identical_retries(monkeypatch):
    """A control-flow sentinel cannot turn an out-of-window tangent into a root."""
    base_integrate=m.integrate;interceptions=[]
    def intercept(state,operator,**kwargs):
        if state.amounts_mol[0,0]==0 and state.amounts_mol[1,0]>0:
            interceptions.append(True)
            def preview(stage,t):
                amounts=np.array(stage.amounts_mol);amounts[1,0]=1e-30
                altered=ConservedState(amounts,stage.internal_energy_j,stage.energy_model_identity,
                                       mechanical_stretches=stage.mechanical_stretches)
                return operator(altered,t)
            return base_integrate(state,preview,**kwargs)
        return base_integrate(state,operator,**kwargs)
    monkeypatch.setattr(m,'integrate',intercept)
    p,e,op,state,calls=setup(gap=.1)
    result=m.integrate_depletion(state,op,start_s=0.,end_s=.03,integration_policy=p,event_policy=e,
                                cancel=lambda:len(interceptions)>3)
    assert result.status=='unsupported',result.reason
    assert result.reason=='ordered_packet_stage_replan_without_localizable_root'
    assert len(interceptions)==1
    assert result.events==result.packets==()
    assert result.times_s[-1]<.01
