"""Independent two-cell numerical oracle; no manufactured water EOS."""
from fractions import Fraction
import numpy as np
import pytest
from sludge_sandbox.depletion_integration import ManufacturedDepletionAdapter,DepletionEvaluation,integrate_depletion
from sludge_sandbox.integration import ConservedState,Rates
from test_depletion_integration import policies


def two_cell_oracle():
    def evaluate(state,t,modes):
        wet=[m=='existing_liquid' for m in modes]
        evaporation=[.001 if w else 0. for w in wet]
        face=np.zeros((3,4));face[1,1]=.0002 if all(wet) else 0.;face[1,3]=.00005
        source=np.zeros((2,4))
        for i,r in enumerate(evaporation):source[i,1]=-r;source[i,3]=r
        source[1,2]=-.0003;source[1,0]=.0003
        rates=Rates(face,np.array([0.,5.,0.]),source,np.array([0. if wet[0] else 2.,3.]))
        return DepletionEvaluation(rates,tuple(evaporation),tuple(state.internal_energy_j/2),(0.,0.),
            tuple(1e5+1000*state.amounts_mol[:,3]),(0.,0.))
    return ManufacturedDepletionAdapter(evaluate_callback=evaluate,liquid_index=1,water_vapor_index=3,
        interfaces=('existing_liquid','existing_liquid'),program_knots_s=(),source_ids=('manufactured:two-cell-depletion-oracle-v1',))


def initial_state():return ConservedState([[0.,4.8e-6,.01,.01],[0.,7.2e-6,.01,.01]],[600.,700.])


def run_case():
    p,e=policies()
    return integrate_depletion(initial_state(),two_cell_oracle(),start_s=0,end_s=.012,integration_policy=p,event_policy=e)


def test_two_separated_events_inside_original_preview_horizon():
    out=run_case()
    assert out.status=='completed',out.reason
    assert [event.cell_index for event in out.events]==[0,1]
    assert [event.time_s for event in out.events]==pytest.approx([.004,.008],rel=0,abs=1e-8)
    assert out.times_s[-1]==.012
    assert out.operator.interfaces==('depleted_no_nucleation','depleted_no_nucleation')
    assert out.events[0].time_s<out.events[0].common_time_s<out.events[1].time_s
    assert out.events[1].time_s<out.events[1].common_time_s<=.012
    for t,state in zip(out.times_s,out.states):
        a=min(t,.004);b=min(t,.008)
        expected=np.array([[0.,max(4.8e-6-.0012*t,0),.01,.01+.001*a-.00005*t],
            [.0003*t,max(7.2e-6-.001*t+.0002*a,0),.01-.0003*t,.01+.001*b+.00005*t]])
        assert np.max(np.abs(state.amounts_mol-expected))<=1e-10
        energy=[600.-5*t+2*max(t-.004,0),700.+8*t]
        assert state.internal_energy_j==pytest.approx(energy,rel=0,abs=1e-7)
        assert np.all(state.amounts_mol>=0)
        assert state.amounts_mol[:,[1,3]].sum()==pytest.approx(.020012,rel=0,abs=1e-12)
        assert state.amounts_mol[:,[0,2]].sum()==pytest.approx(.02,rel=0,abs=1e-12)
    for event in out.events:
        assert event.terminal_panel.reaction_species_mol[1,2]<0
        assert event.terminal_panel.reaction_species_mol[1,0]>0


def test_two_event_full_physical_and_correction_prefix():
    out=run_case();assert out.status=='completed',out.reason
    initial=initial_state();n=np.zeros((2,4),dtype=object);u=np.zeros(2,dtype=object)
    n[:]=Fraction();u[:]=Fraction()
    for step,state in zip(out.steps,out.states[1:]):
        for i,j in np.ndindex(n.shape):
            n[i,j]+=Fraction(float(step.face_species_mol[i,j]))-Fraction(float(step.face_species_mol[i+1,j]))+Fraction(float(step.reaction_species_mol[i,j]))
        for i in range(2):u[i]+=Fraction(float(step.face_energy_j[i]))-Fraction(float(step.face_energy_j[i+1]))+Fraction(float(step.cell_work_j[i]))
        for event in out.events:
            if event.terminal_panel is step and event.correction:
                c=event.correction;n[c.cell_index,c.liquid_index]+=c.ideal_liquid_increment_mol
                n[c.cell_index,c.vapor_index]+=c.ideal_vapor_increment_mol+c.vapor_storage_roundoff_mol
        for i,j in np.ndindex(n.shape):
            assert abs(Fraction(float(state.amounts_mol[i,j]))-Fraction(float(initial.amounts_mol[i,j]))-n[i,j])<=Fraction(1e-12)
        for i in range(2):assert abs(Fraction(float(state.internal_energy_j[i]))-Fraction(float(initial.internal_energy_j[i]))-u[i])<=Fraction(1e-8)
    assert tuple(n.flat)==out.cumulative_amounts_mol and tuple(u)==out.cumulative_energy_j


def test_accelerating_second_event_replans_common_time_after_first_switch():
    from dataclasses import replace
    from sludge_sandbox.integration import DomainExit
    original=two_cell_oracle();base=original.evaluate_callback
    def accelerated(state,t,modes):
        if any(m=='existing_liquid' and state.amounts_mol[i,1]<=0 for i,m in enumerate(modes)):
            raise DomainExit('manufactured_wet_branch_requires_positive_inventory')
        evaluated=base(state,t,modes)
        rates=evaluated.rates;source=np.array(rates.reaction_species_mol_s)
        r=.0001+100*max(t-.004,0)**2 if modes[1]=='existing_liquid' else 0.
        source[1,1]=-r;source[1,3]=r
        return replace(evaluated,rates=Rates(rates.face_species_mol_s,rates.face_energy_w,source,rates.cell_power_w),
            evaporation_mol_s=(evaluated.evaporation_mol_s[0],r))
    op=replace(original,evaluate_callback=accelerated)
    initial=ConservedState([[0.,4.8e-6,.01,.01],[0.,8e-7,.01,.01]],[600.,700.])
    p,e=policies()
    # Tight ordinary policy controls this cubic integrated sink independently
    # of the event refinement indicator. The preregistered event gates stay.
    p=replace(p,relative_tolerance=1e-9,amount_absolute_tolerance_mol=1e-14)
    out=integrate_depletion(initial,op,start_s=0,end_s=.012,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert [v.cell_index for v in out.events]==[0,1]
    assert [v.time_s for v in out.events]==pytest.approx([.004,.007],rel=0,abs=1e-8)
    assert any(v.status=='common_time_horizon_reduced' for v in out.refinements)
    assert out.events[0].common_time_s<out.events[1].time_s


def test_horizon_restart_discards_all_old_comparisons_and_charges_cost():
    out=run_case();assert out.status=='completed',out.reason
    reductions=[v for v in out.refinements if v.status=='common_time_horizon_reduced']
    assert reductions
    for change in reductions:
        assert change.event_time_s<change.next_common_time_s<change.common_time_s
        assert change.next_common_time_s<.008
        i=out.refinements.index(change)
        assert out.refinements[i+1].level==0
        assert out.refinements[i+1].common_time_s==change.next_common_time_s
        assert out.refinements[i+1].status=='coarse_reference'
    assert out.accepted_trial_panels>len(out.steps)
    assert len(out.events)==2
    assert out.roundoff_totals.events==sum(v.correction is not None for v in out.events)


def test_resource_failure_after_horizon_restart_does_not_commit_trial_modes():
    from dataclasses import replace
    p,e=policies();p=replace(p,maximum_steps=16)
    out=integrate_depletion(initial_state(),two_cell_oracle(),start_s=0,end_s=.012,integration_policy=p,event_policy=e)
    assert out.status=='resource_limit',out.reason
    assert any(v.status=='common_time_horizon_reduced' for v in out.refinements)
    assert not out.events and not out.corrections and out.roundoff_totals.events==0
    assert out.operator.interfaces==('existing_liquid','existing_liquid')
    assert np.all(out.states[-1].amounts_mol[:,1]>0)
