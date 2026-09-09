"""Closed manufactured analytic-liquid actual kg/mol framework, no native EOS."""
from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_mass_wet_exact_stage import setup as stage_setup, fixture, policy
from sludge_sandbox.mass_wet_exact_controller import integrate_mixed_exact, MixedControllerPolicy, audit_prefix
from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy
from sludge_sandbox.exact_event_clock import ExactEventTime as T


def setup(monkeypatch):
    pair,initial=stage_setup(monkeypatch)
    # Two finite wet inventories, distinct actual evaporation event times.
    states=[]
    for i,n in enumerate((1e-10,1.3e-10)):
        s=pair.storages[i].state((.01,.002),n,(.2,.2,1e-8),0.)
        states.append(replace(s,internal_energy_j=pair.storages[i].evaluate(s,305.).total_internal_energy_j))
    mw=pair.storages[0].water.reference.molar_mass_kg_mol
    rp=DepletionRoundoffPolicy(correction_absolute_mol=1e-15,correction_fraction_evaporated=1e-8,storage_absolute_mol=1e-15,cumulative_storage_absolute_mol=1e-14,element_absolute_mol=2e-15,cumulative_element_absolute_mol=2e-14,mass_absolute_kg=1e-16,cumulative_mass_absolute_kg=1e-15,cumulative_correction_absolute_mol=1e-14,molar_mass_kg_mol=mw)
    cp=MixedControllerPolicy(F(1,10000),F(1,2),F(1,10000),6,4000,2000,120.)
    return pair,tuple(states),rp,cp


def execute(pair,initial,rp,cp,**kw):
    return integrate_mixed_exact(pair,initial,start=T(F()),end=T(F(1,2000)),stage_policy=policy(),roundoff_policy=rp,original_liquid_fraction_limit=F('1e-8'),controller_policy=cp,constant_liquid_fixture=fixture(pair),**kw)


def test_actual_wet_wet_dry_wet_dry_dry_atomic_packet(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch);r=execute(pair,initial,rp,cp)
    assert r.status=='completed',r.reason
    assert r.times[-1]==T(F(1,2000)) and len(r.packets)==1 and len(r.packets[0])==2
    assert tuple(f.terminal.root_order.selected_cell for f in r.packets[0])==(0,1)
    assert r.packets[0][0].modes_after==('depleted_no_nucleation','existing_liquid')
    assert r.operator.interfaces==('depleted_no_nucleation',)*2
    assert all(s.liquid_water_mol==0 for s in r.states[-1])
    assert pair.interfaces==('existing_liquid',)*2 and r.states[0] is initial
    assert [x.status for x in r.refinements[-3:]]==['comparison_pass']*3
    assert r.refinements[-1].role=='independent'
    assert r.refinements[-1].path.approach_grid!=r.refinements[-2].path.approach_grid
    assert r.refinements[-1].approach_cap_s==r.refinements[-2].approach_cap_s/2
    assert r.refinements[-1].safe_fraction==r.refinements[-2].safe_fraction/2
    assert r.roundoff_totals.context.original_states==initial
    from test_mass_wet_transport import totals
    original_elements,original_mass,original_water,original_energy=totals(pair,initial)
    for prefix in r.states:
        elements,mass,water,energy=totals(pair,prefix)
        assert max(abs(x-y) for x,y in zip(elements,original_elements))<F(2e-15)
        assert abs(mass-original_mass)<F(2e-15)
        assert abs(water-original_water)<F(1e-15)
        assert abs(energy-original_energy)<F(2e-10)

    for ref in r.refinements:
        audit_prefix(ref.path,initial,r.stage_policy)
        assert len(ref.comparison)==0 if ref.status=='coarse_reference' else len(ref.comparison)==3
    assert all(s.solid_mass_kg[0]<initial[i].solid_mass_kg[0] for i,s in enumerate(r.states[-1]))
    from independent_mixed_ode import reference
    import numpy as np
    end_state,frames,segments,decode=reference(pair,initial,.0005)
    assert tuple(f[0] for f in frames)==(0,1)
    for event,(_,at,_) in zip(r.packets[0],frames):
        assert abs(float(event.time.seconds)-at)<=r.stage_policy.time_absolute_s
    maximum=[0.]*5
    for at,states in zip(r.times,r.states):
        time=float(at.seconds)
        segment=next(part for part in segments if part[0]-1e-15<=time<=part[1]+1e-15)
        expected,temperatures,pressures,_=decode(segment[2](time))
        for i,state in enumerate(states):
            maximum[0]=max(maximum[0],max(abs(np.array(state.solid_mass_kg)-expected[i,:2])))
            maximum[1]=max(maximum[1],max(abs(np.array((state.liquid_water_mol,*state.gas_amounts_mol))-expected[i,2:6])))
            maximum[2]=max(maximum[2],abs(state.internal_energy_j-expected[i,6]))
    last=r.refinements[-2].path.final_observation
    expected,temperatures,pressures,_=decode(end_state)
    for i,cell in enumerate(last.rates.cells):
        maximum[3]=max(maximum[3],abs(cell.inverse.point.temperature_k-temperatures[i]))
        maximum[4]=max(maximum[4],abs(cell.inverse.point.pressure_pa-pressures[i]))
    assert all(value<=bound for value,bound in zip(maximum,(1e-8,4e-7,1e-3,1e-3,1.))),maximum
    from sludge_sandbox.mass_wet_writeback import MixedWritebackTotals
    accepted=r.refinements[-2].path
    with pytest.raises(ValueError,match='once_only_original_correction_totals'):
        audit_prefix(replace(accepted,totals=MixedWritebackTotals.empty(accepted.totals.context)),initial,r.stage_policy)
    first=accepted.steps[0]
    terms=tuple((key,value+1. if key==('face_energy',) else value) for key,value in first.represented_integrals)
    with pytest.raises(ValueError,match='energy_component_prefix_budget'):
        audit_prefix(replace(accepted,steps=(replace(first,represented_integrals=terms),*accepted.steps[1:])),initial,r.stage_policy)
    print({'costs':dict(r.costs),'accepted_panels':len(r.steps),'refinements':len(r.refinements),'events':[(f.terminal.root_order.selected_cell,float(f.time.seconds)) for f in r.packets[0]],'independent_ode_maxima_kg_mol_U_T_P':maximum})



def test_cancelled_candidate_keeps_no_commit_and_spent_work(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch);count=[0]
    from sludge_sandbox.mass_wet_transport import WetPair
    old=WetPair.evaluate
    def observed(self,states):
        result=old(self,states);count[0]+=1;return result
    monkeypatch.setattr(WetPair,'evaluate',observed)
    r=execute(pair,initial,rp,cp,cancel=lambda:count[0]>=5)
    assert r.status=='cancelled' and r.states==(initial,) and not r.steps and not r.packets
    assert dict(r.costs)['evaluations_completed']==5
    assert r.refinements and r.refinements[0].path.attempts
    assert r.roundoff_totals.aggregate.events==0


def test_cumulative_evaluation_and_panel_budgets_no_reset(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch)
    r=execute(pair,initial,rp,replace(cp,maximum_evaluations=12))
    assert r.status=='resource_limit' and dict(r.costs)['evaluations_attempted']==12
    assert not r.steps and r.refinements[0].path.steps
    r=execute(pair,initial,rp,replace(cp,maximum_panel_attempts=2))
    assert r.status=='resource_limit' and dict(r.costs)['panel_attempts']==0 and not r.steps


def test_generic_wet_has_no_implicit_pressure_certificate(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch)
    r=integrate_mixed_exact(pair,initial,start=T(F()),end=T(F(1,2000)),stage_policy=policy(),roundoff_policy=rp,original_liquid_fraction_limit=F('1e-8'),controller_policy=cp)
    assert r.status=='failed' and r.reason=='pressure_temperature_envelope_unavailable'
    assert not r.steps and r.refinements[0].path.attempts


def test_failed_mixed_endpoint_retains_transition_without_global_commit(monkeypatch):
    from sludge_sandbox.mass_wet_transport import WetPair
    from sludge_sandbox.integration import DomainExit
    pair,initial,rp,cp=setup(monkeypatch);old=WetPair.evaluate
    def fail(self,states):
        if self.interfaces==('depleted_no_nucleation','existing_liquid'):
            raise DomainExit('manufactured_mixed_endpoint_exit')
        return old(self,states)
    monkeypatch.setattr(WetPair,'evaluate',fail)
    r=execute(pair,initial,rp,replace(cp,terminal_window_s=F(1)))
    assert r.status=='domain_exit' and r.reason=='manufactured_mixed_endpoint_exit'
    assert not r.steps and r.roundoff_totals.aggregate.events==0
    candidate=r.refinements[0].path
    assert len(candidate.frames)==1 and candidate.frames[0].observation is None
    assert candidate.frames[0].old_binding!=candidate.frames[0].new_binding
    assert candidate.frames[0].terminal.projection is not None
    assert r.observation_journal[-1].status=='domain_exit'
    assert r.observation_journal[-1].states==candidate.states[-1]
    assert dict(r.costs)['evaluations_attempted']==dict(r.costs)['evaluations_completed']+1


def test_changed_controls_without_real_pre_first_grid_are_not_independent(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch)
    r=execute(pair,initial,rp,replace(cp,approach_cap_s=F(1,1000),terminal_window_s=F(1)))
    assert r.status=='failed' and r.reason=='independent_pre_first_approach_grid_uninformative'
    assert not r.steps and len(r.refinements)==4
    assert r.refinements[-1].role=='independent' and r.refinements[-1].status=='comparison_fail'
    assert not r.refinements[-1].path.approach_grid


def test_strict_original_clock_gate_failure_is_not_committed(monkeypatch):
    pair,initial,rp,cp=setup(monkeypatch)
    r=integrate_mixed_exact(pair,initial,start=T(F()),end=T(F(1,2000)),stage_policy=replace(policy(),time_absolute_s=1e-20),roundoff_policy=rp,original_liquid_fraction_limit=F('1e-8'),controller_policy=replace(cp,maximum_refinements=2),constant_liquid_fixture=fixture(pair))
    assert r.status=='failed' and r.reason=='original_refinement_budget_exhausted'
    assert not r.steps and r.states==(initial,) and r.roundoff_totals.aggregate.events==0
    assert any(ref.status=='comparison_fail' for ref in r.refinements)
    assert all(ref.path.status=='completed' for ref in r.refinements)
