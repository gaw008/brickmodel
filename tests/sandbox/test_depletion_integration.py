"""Explicit manufactured oracle adapter; no fake constant-water EOS."""
import math
import numpy as np
import pytest
from sludge_sandbox.depletion_integration import (DepletionPolicy,ManufacturedDepletionAdapter,
    DepletionEvaluation,integrate_depletion)
from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy
from sludge_sandbox.integration import ConservedState,Rates,IntegrationPolicy


def policies():
    base=IntegrationPolicy(initial_step_s=.01,maximum_step_s=.01,minimum_step_s=1e-14,
        relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-8,
        amount_scale_mol=1e-4,energy_scale_j=1.,maximum_steps=5000,maximum_rejections=100,maximum_wall_seconds=30.)
    rounding=DepletionRoundoffPolicy(correction_absolute_mol=1e-15,correction_fraction_evaporated=1e-8,
        storage_absolute_mol=1e-15,cumulative_storage_absolute_mol=1e-14,
        element_absolute_mol=2e-15,cumulative_element_absolute_mol=2e-14,
        mass_absolute_kg=1e-16,cumulative_mass_absolute_kg=1e-15,cumulative_correction_absolute_mol=1e-14,
        molar_mass_kg_mol=.018015268)
    event=DepletionPolicy(time_absolute_s=1e-8,amount_absolute_mol=1e-11,energy_absolute_j=1e-7,
        temperature_absolute_k=1e-5,pressure_absolute_pa=1e-4,terminal_window_s=.001,
        maximum_refinements=14,roundoff_policy=rounding)
    return base,event


def oracle(a=.001,b=0.,knots=()):
    def evaluate(state,t,modes):
        rate=(a+b*t) if modes[0]=='existing_liquid' else 0.
        sources=np.array([[-rate,rate]])
        rates=Rates(np.zeros((2,2)),np.zeros(2),sources,np.array([2. if modes[0]!='existing_liquid' else 0.]))
        # Independent caloric U=2*T. Mode-dependent external heating makes
        # comparing only states at unequal event times insufficient.
        return DepletionEvaluation(rates,(rate,),(float(state.internal_energy_j[0])/2,),(.0,),(.0,),(.0,))
    return ManufacturedDepletionAdapter(evaluate_callback=evaluate,liquid_index=0,water_vapor_index=1,
        interfaces=('existing_liquid',),program_knots_s=knots,source_ids=('manufactured:analytic-depletion',))


def test_constant_sink_reaches_event_and_continues_at_common_time():
    policy,event=policies();initial=ConservedState([[1e-4,0.]],[600.])
    out=integrate_depletion(initial,oracle(),start_s=0,end_s=.2,integration_policy=policy,event_policy=event)
    assert out.status=='completed',out.reason
    assert len(out.events)==1
    assert abs(out.events[0].time_s-.1)<=1e-9
    assert out.times_s[-1]==.2
    assert out.states[-1].amounts_mol[0,0]==0
    assert out.states[-1].amounts_mol.sum()==pytest.approx(1e-4,rel=0,abs=1e-12)
    assert out.states[-1].internal_energy_j[0]==pytest.approx(600.2,rel=0,abs=1e-8)


def test_time_varying_sink_with_program_node():
    policy,event=policies();initial=ConservedState([[1e-4,0.]],[600.])
    out=integrate_depletion(initial,oracle(b=.002,knots=(.05,)),start_s=0,end_s=.2,integration_policy=policy,event_policy=event)
    exact=(-.001+math.sqrt(.001**2+2*.002*1e-4))/.002
    assert out.status=='completed',out.reason
    assert .05 in out.times_s
    assert abs(out.events[0].time_s-exact)<=1e-7
    assert out.states[-1].internal_energy_j[0]==pytest.approx(600+2*(.2-exact),rel=0,abs=1e-7)


def test_cancel_preserves_initial_state_and_empty_prefix():
    p,e=policies();initial=ConservedState([[1e-4,0.]],[600.])
    out=integrate_depletion(initial,oracle(),start_s=0,end_s=.2,integration_policy=p,event_policy=e,cancel=lambda:True)
    assert out.status=='cancelled'
    assert out.states==(initial,) and not out.steps and not out.events
    assert all(v==0 for v in out.cumulative_amounts_mol+out.cumulative_energy_j)


def test_attempted_step_limit_preserves_last_committed_state():
    from dataclasses import replace
    p,e=policies();p=replace(p,maximum_steps=2)
    out=integrate_depletion(ConservedState([[1e-4,0.]],[600.]),oracle(),start_s=0,end_s=.2,integration_policy=p,event_policy=e)
    assert out.status=='resource_limit'
    assert len(out.steps)<=2 and out.states[-1].amounts_mol[0,0]>0
    assert out.operator.interfaces==('existing_liquid',)
    assert not out.events and not out.corrections


def test_net_liquid_loss_without_evaporation_is_not_relabelled():
    from dataclasses import replace
    op=oracle();original=op.evaluate_callback
    def non_evaporative(state,t,modes):
        return replace(original(state,t,modes),evaporation_mol_s=(0.,))
    op=replace(op,evaluate_callback=non_evaporative)
    p,e=policies()
    out=integrate_depletion(ConservedState([[1e-4,0.]],[600.]),op,start_s=0,end_s=.2,integration_policy=p,event_policy=e)
    assert out.status=='unsupported' and out.reason=='unsupported_non_evaporative_liquid_depletion'
    assert not out.steps and not out.events


def test_simultaneous_cells_are_explicitly_unsupported():
    def evaluate(state,t,modes):
        sources=np.array([[-.001,.001],[-.001,.001]])
        return DepletionEvaluation(Rates(np.zeros((3,2)),np.zeros(3),sources,np.zeros(2)),
            (.001,.001),(300.,300.),(0.,0.),(1e5,1e5),(0.,0.))
    op=ManufacturedDepletionAdapter(evaluate_callback=evaluate,liquid_index=0,water_vapor_index=1,
        interfaces=('existing_liquid','existing_liquid'),program_knots_s=(),source_ids=('manufactured:simultaneous',))
    p,e=policies()
    out=integrate_depletion(ConservedState([[1e-4,0.],[1e-4,0.]],[600.,600.]),op,start_s=0,end_s=.2,integration_policy=p,event_policy=e)
    assert out.status=='unsupported' and out.reason=='simultaneous_events_not_separated'
    assert not out.steps and not out.events


def test_already_dry_oracle_keeps_full_heat_rates():
    from dataclasses import replace
    p,e=policies();op=replace(oracle(),interfaces=('depleted_no_nucleation',))
    out=integrate_depletion(ConservedState([[0.,1e-4]],[600.]),op,start_s=0,end_s=.2,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert not out.events
    assert out.states[-1].internal_energy_j[0]==pytest.approx(600.4,rel=0,abs=1e-8)
    assert all(s.amounts_mol[0,0]==0 for s in out.states)


def test_failed_preview_keeps_wet_mode_and_prior_physical_prefix():
    from dataclasses import replace
    from fractions import Fraction
    p,e=policies();p=replace(p,maximum_steps=25)
    initial=ConservedState([[1e-4,0.]],[600.])
    out=integrate_depletion(initial,oracle(),start_s=0,end_s=.2,integration_policy=p,event_policy=e)
    assert out.status=='resource_limit',out.reason
    assert out.accepted_trial_panels>len(out.steps) # discarded speculative panels were charged
    assert out.operator.interfaces==('existing_liquid',) and out.states[-1].amounts_mol[0,0]>0
    assert not out.events and not out.corrections and out.roundoff_totals.events==0
    physical=sum((Fraction(float(step.reaction_species_mol[0,0])) for step in out.steps),Fraction())
    assert out.cumulative_amounts_mol[0]==physical
    assert all(v==0 for v in out.cumulative_energy_j)


def test_event_exactly_at_node_cannot_be_declared_separated():
    # Binary-exact times/rates make this an actual coincidence, not an atol snap.
    from dataclasses import replace
    p,e=policies();p=replace(p,initial_step_s=1/64,maximum_step_s=1/64)
    e=replace(e,terminal_window_s=1/1024)
    initial=ConservedState([[.125,0.]],[600.])
    out=integrate_depletion(initial,oracle(a=1.,knots=(.125,)),start_s=0,end_s=.25,integration_policy=p,event_policy=e)
    assert out.status=='unsupported',out.reason
    assert out.reason in ('no_common_post_event_time','event_node_order_not_separated')
    assert not out.events and out.operator.interfaces==('existing_liquid',)


def test_event_storage_roundoff_keeps_paired_and_actual_prefix_separate():
    from fractions import Fraction
    p,e=policies();initial=ConservedState([[1e-4,.1]],[600.])
    out=integrate_depletion(initial,oracle(),start_s=0,end_s=.2,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert len(out.corrections)==1
    c=out.corrections[0]
    assert c.ideal_liquid_increment_mol==-c.ideal_vapor_increment_mol
    assert c.vapor_storage_roundoff_mol!=0
    assert out.roundoff_totals.signed_storage_roundoff_mol==c.vapor_storage_roundoff_mol
    physical=sum((Fraction(float(step.reaction_species_mol[0,1])) for step in out.steps),Fraction())
    expected=physical+c.ideal_vapor_increment_mol+c.vapor_storage_roundoff_mol
    assert out.cumulative_amounts_mol[1]==expected
    assert abs(Fraction(float(out.states[-1].amounts_mol[0,1]))-Fraction(.1)-expected)<=Fraction(p.amount_absolute_tolerance_mol)
    assert out.refinements[-1].status=='comparison_pass'
    assert out.refinements[-1].common_time_s>out.events[0].time_s


def test_tiny_initial_inventory_requires_actual_terminal_refinement():
    # All former fixed-window caps exceeded tau: identical Euler panels gave
    # false zero comparison error although the independent root error was 98 ns.
    p,e=policies();initial=ConservedState([[1e-8,0.]],[600.])
    a=.001;b=2.
    exact=2*1e-8/(a+math.sqrt(a*a+2*b*1e-8))
    out=integrate_depletion(initial,oracle(a=a,b=b),start_s=0,end_s=.001,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert abs(out.events[0].time_s-exact)<=1e-8
    panel=out.events[0].terminal_panel
    assert panel.end_s-panel.start_s<=(1e-8/a)/4
