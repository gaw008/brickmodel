"""Actual exact numerical chain, instrumented native-only callback seam; no EOS."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace as NS
import numpy as np
from test_exact_terminal_executor import fixture
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.depletion_integration import NestedApproachPolicy
from sludge_sandbox.exact_depletion_integration import integrate_exact_depletion
from sludge_sandbox.exact_event_clock import ExactEventTime as T


def setup(monkeypatch,gap=1e-9):
    state,view,kw,calls,providers,native,mode=fixture(monkeypatch,gap=gap)
    def observed(self,s):
        out=native(self,s)
        closed=tuple(NS(mechanical=NS(temperature_k=300.,pressure_pa=100000.),pressure_error_bound_pa=0.) for _ in s.amounts_mol)
        base=NS(storage_states=closed,storage_inverses=tuple(NS(temperature_error_bound_k=0.) for _ in closed))
        return replace(out,base_evaluation=base)
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',observed)
    e=replace(kw['event_policy'],ordered_event_policy='ordered_affine_packet_v1',nested_approach=NestedApproachPolicy(maximum_step_s=.001,reuse_ordinary_spine=False))
    return state,view,kw['integration_policy'],e,calls


def run(monkeypatch,**changes):
    state,view,p,e,calls=setup(monkeypatch)
    args=dict(start=T(F(1,2)),end=T(F(53,100)),integration_policy=p,event_policy=e)
    args.update(changes)
    return integrate_exact_depletion(state,view,**args),calls


def test_complete_two_near_events_original_gates(monkeypatch):
    r,calls=run(monkeypatch)
    assert r.status=='completed',r.reason
    assert sum(len(p) for p in r.packets)==2
    assert r.operator.operator.interfaces==('depleted_no_nucleation',)*2
    assert any(x.role=='independent' and x.status=='comparison_pass' for x in r.refinements)
    assert len(r.times_s)==len(r.steps)+1
    duration=float(r.times_s[-1].elapsed_since(r.times_s[0]))
    np.testing.assert_allclose(r.states[-1].internal_energy_j,[10+2*duration,20+3*duration],rtol=0,atol=1e-10)
    assert r.costs['evaluations_attempted']==len(calls)
    for packet in r.packets:
        for frame in packet:assert frame.common_time is not None and len(frame.packet_maximum_differences)==6


def test_cancel_uncommitted_packet_retains_prefix(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch)
    def cancel():return any(modes[0]=='depleted_no_nucleation' for _,modes in calls)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e,cancel=cancel)
    assert r.status=='cancelled',r.reason
    assert r.packets==() and r.operator.operator.interfaces==('existing_liquid',)*2
    assert len(r.steps)>0 and r.terminal_attempts


def test_independent_grid_and_controls_are_both_finer(monkeypatch):
    r,_=run(monkeypatch)
    assert r.status=='completed'
    independent=[x for x in r.refinements if x.role=='independent']
    assert independent
    for fine in independent:
        prior=next(x for x in reversed(r.refinements[:r.refinements.index(fine)]) if x.role=='terminal')
        assert fine.approach_cap_s*2==prior.approach_cap_s
        assert fine.safe_fraction*2==prior.safe_fraction
        assert fine.path.approach_grid!=prior.path.approach_grid
        for path in (fine.path,prior.path):
            first_terminal_start=path.frames[0].terminal.observations[0].time
            assert all(at<=first_terminal_start for at in path.approach_grid)
            assert path.times[-1]>first_terminal_start  # Later continuation is excluded.
        assert fine.costs['evaluations_attempted']>0


def test_source_mutation_after_speculative_event_never_commits(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch)
    callback=WaterPhaseTransfer.evaluate_autonomous
    def corrupt(self,state):
        out=callback(self,state)
        if self.interfaces[0]=='depleted_no_nucleation':
            object.__setattr__(v.operator,'coefficient_version','mutated')
        return out
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',corrupt)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.status!='completed' and r.packets==()
    assert r.terminal_attempts and len(r.steps)>0


def test_global_panel_limit_retains_last_accepted_ordinary_step(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch)
    p=replace(p,maximum_steps=1)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.status=='resource_limit' and len(r.steps)==1 and r.packets==()
    assert r.costs['ordinary_trials']==1


def test_original_temperature_error_floor_does_not_get_dropped(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch)
    e=replace(e,maximum_refinements=3)
    callback=WaterPhaseTransfer.evaluate_autonomous
    def uncertain(self,state):
        out=callback(self,state)
        for inv in out.base_evaluation.storage_inverses:inv.temperature_error_bound_k=1e-3
        return out
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',uncertain)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.status!='completed' and r.packets==()
    assert any(x.status=='comparison_fail' for x in r.refinements)


def test_cancel_during_ordinary_preserves_complete_local_prefix(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e,cancel=lambda:len(calls)>=10)
    assert r.status=='cancelled' and r.packets==() and len(r.steps)==1
    assert len(r.states)==2 and r.operator is v


def test_equal_roots_fail_without_partial_mode_commit(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch,gap=0.)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.status!='completed' and r.packets==()
    assert 'coincident' in r.reason
    assert r.operator.operator.interfaces==('existing_liquid',)*2


def test_paired_pressure_dispatch_preserves_original_bound_and_endpoint_costs(monkeypatch):
    # This tests driver wiring; the actual paired certificate has its own pure tests.
    import sludge_sandbox.exact_depletion_integration as m
    from test_pressure_comparison import policy as pressure_policy
    from sludge_sandbox.pressure_comparison import PressureComparisonPolicy
    s,v,p,e,calls=setup(monkeypatch)
    box=pressure_policy().cell_boxes[0]
    pp=PressureComparisonPolicy((box,replace(box,point_identity_sha256='b'*64)))
    e=replace(e,pressure_comparison=pp)
    monkeypatch.setattr(m,'pressure_comparison_binding',lambda op:{'boxes':pp.to_record()['cell_boxes']})
    native=WaterPhaseTransfer.evaluate_autonomous
    def higherrors(self,state):
        out=native(self,state)
        for closed in out.base_evaluation.storage_states:closed.pressure_error_bound_pa=.1
        out.base_evaluation.total_inverses=tuple(out.base_evaluation.storage_inverses)
        return out
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',higherrors)
    paired=[]
    def compare(oa,sa,ia,ob,sb,ib,*,policy,before_endpoint,after_endpoint):
        assert type(oa) is type(ob) is WaterPhaseTransfer and policy is pp
        assert len(ia)==len(ib)==2
        before_endpoint();after_endpoint('actual-test-sample')
        paired.append((sa,sb))
        return NS(to_record=lambda:{'bound_pa':0.,'endpoint_samples':['actual-test-sample']})
    monkeypatch.setattr(m,'compare_pressure_pair',compare)
    r=m.integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.status=='completed',r.reason
    assert len(paired)==r.costs['endpoint_attempts']==r.costs['endpoint_completed']>0
    rows=[row for ref in r.refinements if ref.comparison for row in ref.comparison]
    assert all(row['independent_pressure_bound_pa']>=.2 and row['differences'][4]==0 for row in rows)


def test_actual_mixed_rhs_acceleration_keeps_order_and_full_ledger(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch,gap=.008)
    native=WaterPhaseTransfer.evaluate_autonomous
    def accelerated(self,state):
        out=native(self,state)
        if self.interfaces[0]=='depleted_no_nucleation' and self.interfaces[1]=='existing_liquid':
            rate=1.+2000.*max(0.,float(state.internal_energy_j[1])-20.03)
            source=np.array(out.rates.reaction_species_mol_s);source[1]=[-rate,rate]
            transfers=list(out.cell_transfers);transfers[1]=replace(transfers[1],rate_mol_s=rate)
            out=replace(out,rates=replace(out.rates,reaction_species_mol_s=source),cell_transfers=tuple(transfers))
        return out
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',accelerated)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.status=='completed',r.reason
    frames=[f for packet in r.packets for f in packet]
    assert [f.terminal.root_order.selected_cell for f in frames]==[0,1]
    assert float(frames[1].terminal.observations[-1].time.seconds)<.018
    assert r.costs['ordinary_rejected']+r.costs['stage_replans']>0
    np.testing.assert_allclose(r.states[-1].internal_energy_j,[10.06,20.09],rtol=0,atol=1e-9)


def test_midstage_preview_replan_is_charged_and_never_installs_stage_mode(monkeypatch):
    # State-local narrow rate peak is an adversarial control-flow fixture, not a physical oracle.
    import math
    s,v,p,e,calls=setup(monkeypatch,gap=.008)
    e=replace(e,maximum_refinements=3)
    native=WaterPhaseTransfer.evaluate_autonomous
    def pulse(self,state):
        out=native(self,state)
        if self.interfaces[0]=='depleted_no_nucleation' and self.interfaces[1]=='existing_liquid':
            elapsed=(float(state.internal_energy_j[1])-20.)/3.
            rate=1.+1000.*math.exp(-((elapsed-.0105)/.00004)**2)
            source=np.array(out.rates.reaction_species_mol_s);source[1]=[-rate,rate]
            transfers=list(out.cell_transfers);transfers[1]=replace(transfers[1],rate_mol_s=rate)
            out=replace(out,rates=replace(out.rates,reaction_species_mol_s=source),cell_transfers=tuple(transfers))
        return out
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',pulse)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.costs['stage_replans']>0
    assert r.costs['ordinary_trials']>=r.costs['ordinary_panels']+r.costs['stage_replans']
    for state,modes in calls:
        for i,mode in enumerate(modes):
            if mode=='depleted_no_nucleation':assert state.amounts_mol[i,0]==0


def test_postcallback_cancel_preserves_outer_classification(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e,cancel=lambda:len(calls)>=2)
    assert r.status=='cancelled' and r.reason=='cancel_requested'
    assert r.steps==() and r.costs['evaluations_completed']==len(calls)==2


def test_postcallback_wall_expiry_preserves_outer_classification(monkeypatch):
    import sludge_sandbox.exact_depletion_integration as m
    s,v,p,e,calls=setup(monkeypatch);clock=[0.]
    monkeypatch.setattr(m,'time',NS(monotonic=lambda:clock[0]))
    native=WaterPhaseTransfer.evaluate_autonomous
    def expire(self,state):
        out=native(self,state)
        if len(calls)==2:clock[0]=p.maximum_wall_seconds+1
        return out
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',expire)
    r=m.integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.status=='resource_limit' and r.reason=='wall_time_limit'
    assert r.steps==() and r.costs['evaluations_completed']==2


def test_wrong_water_mass_refused_even_without_terminal(monkeypatch):
    import pytest
    from sludge_sandbox.integration import IntegrationError
    s,v,p,e,calls=setup(monkeypatch)
    e=replace(e,roundoff_policy=replace(e.roundoff_policy,molar_mass_kg_mol=.02))
    with pytest.raises(IntegrationError,match='molar_mass'):
        integrate_exact_depletion(s,v,start=T(F()),end=T(F(1,100000)),integration_policy=p,event_policy=e)
    assert calls==[]


def test_initial_native_domain_exit_is_distinct(monkeypatch):
    from sludge_sandbox.integration import DomainExit
    s,v,p,e,calls=setup(monkeypatch)
    def domain(self,state):raise DomainExit('actual_domain')
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',domain)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert r.status=='domain_exit' and r.reason=='actual_domain' and r.steps==()
    assert r.costs['evaluations_attempted']==1 and r.costs['evaluations_completed']==0


def test_rejections_do_not_consume_original_accepted_panel_budget(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch)
    original=WaterPhaseTransfer.evaluate_autonomous
    def nonlinear(self,state):
        out=original(self,state)
        return replace(out,rates=replace(out.rates,
            mechanical_rates_per_s=1000.*state.mechanical_stretches))
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',nonlinear)
    p=replace(p,maximum_steps=1,initial_step_s=.0001,maximum_step_s=.0001)
    r=integrate_exact_depletion(s,v,start=T(F()),end=T(F(1,10000)),integration_policy=p,event_policy=e)
    assert r.status=='resource_limit',r.reason
    assert len(r.steps)==1
    assert r.costs['ordinary_panels']==1
    assert r.costs['ordinary_rejected']>0
    assert r.costs['ordinary_trials']==1+r.costs['ordinary_rejected']
    assert r.packets==() and r.terminal_attempts==()
