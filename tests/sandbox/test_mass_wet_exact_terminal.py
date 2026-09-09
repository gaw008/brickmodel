"""Actual analytic-liquid host connection, no native EOS or event commit."""
from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_mass_wet_transport import setup as host_setup
from sludge_sandbox.mass_wet_exact_terminal import prepare_mixed_terminal,source_labels
from sludge_sandbox.mass_wet_writeback import MixedWritebackContext,MixedWritebackTotals
from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.mass_wet_transport import WetPair


def setup(monkeypatch):
    pair,states=host_setup(monkeypatch)
    s=replace(states[0],liquid_water_mol=1e-10)
    s=replace(s,internal_energy_j=pair.storages[0].evaluate(s,305.).total_internal_energy_j)
    initial=(s,states[1]);mw=pair.storages[0].water.reference.molar_mass_kg_mol
    p=DepletionRoundoffPolicy(correction_absolute_mol=1e-15,correction_fraction_evaporated=1e-8,storage_absolute_mol=1e-15,cumulative_storage_absolute_mol=1e-14,element_absolute_mol=2e-15,cumulative_element_absolute_mol=2e-14,mass_absolute_kg=1e-16,cumulative_mass_absolute_kg=1e-15,cumulative_correction_absolute_mol=1e-14,molar_mass_kg_mol=mw)
    ctx=MixedWritebackContext(initial,T(F()),pair.binding(),source_labels(pair),mw,p,F('1e-8'))
    return pair,initial,ctx,MixedWritebackTotals.empty(ctx)


def run(pair,initial,ctx,totals,**kw):
    return prepare_mixed_terminal(pair,initial,start=T(F()),upper=T(F(1,1000)),context=ctx,totals=totals,time_absolute_s=1e-8,**kw)


def test_actual_samples_to_full_terminal_projection(monkeypatch):
    pair,initial,c,t=setup(monkeypatch);r=run(pair,initial,c,t)
    assert r.status=='prepared',r.reason
    assert r.evaluations_attempted==r.evaluations_completed==2
    assert len(r.samples)==2 and r.samples[1].state==r.predictor_state
    assert r.root_order.selected_cell==0 and len(r.root_order.exclusions)==1
    assert r.evidence.clock.samples.start_inventory_mol==initial[0].liquid_water_mol
    assert r.evidence.panel_terms[0].liquid_mol==r.evidence.clock.signed_terms_mol
    assert r.projection.states[0].liquid_water_mol==0
    assert r.projection.states[0].solid_mass_kg==r.evidence.raw_states[0].solid_mass_kg
    assert r.projection.states[0].internal_energy_j==r.evidence.raw_states[0].internal_energy_j
    assert r.projection.states[1] is r.evidence.raw_states[1]
    assert pair.interfaces==('existing_liquid',)*2 and t.aggregate.events==0
    assert r.raw_states==r.evidence.raw_states and r.panel_terms==r.evidence.panel_terms
    d=dict(r.ledger.represented_integrals)
    for i,(before,after) in enumerate(zip(initial,r.evidence.raw_states)):
        assert abs(F(after.internal_energy_j)-F(before.internal_energy_j)-(-1,1)[i]*F(d['face_energy',]))<F(1e-10)
        for j in range(2):assert abs(F(after.solid_mass_kg[j])-F(before.solid_mass_kg[j])-F(d['solid',i,j]))<F(1e-17)
        for j in range(3):
            increment=F(d['chemical_gas',i,j])+(-1,1)[i]*F(d['face_species',j])+(F(d['phase_water',i]) if j==2 else 0)
            assert abs(F(after.gas_amounts_mol[j])-F(before.gas_amounts_mol[j])-increment)<F(1e-16)
        assert abs(F(after.liquid_water_mol)-F(before.liquid_water_mol)+F(d['phase_water',i]))<F(1e-16)

    for key,r0,slope in r.component_coefficients:
        h=r.ledger.end.elapsed_since(r.ledger.start)
        assert dict(r.ledger.exact_integrals)[key]==r0*h+slope*h*h/2


def test_callback_budget_retains_actual_predictor(monkeypatch):
    pair,initial,c,t=setup(monkeypatch);r=run(pair,initial,c,t,maximum_evaluations=1)
    assert r.status=='resource_limit' and r.evaluations_attempted==1
    assert r.predictor_state is not None and len(r.samples)==1 and r.projection is None


def test_source_context_and_water_policy_before_callbacks(monkeypatch):
    pair,initial,c,t=setup(monkeypatch)
    wrong=replace(c,operator_identity='f'*64)
    r=run(pair,initial,wrong,MixedWritebackTotals.empty(wrong))
    assert r.status=='failed' and r.evaluations_attempted==0
    p=replace(c.policy,molar_mass_kg_mol=.02)
    wrong=replace(c,water_molar_mass_kg_mol=.02,policy=p)
    r=run(pair,initial,wrong,MixedWritebackTotals.empty(wrong))
    assert r.reason=='roundoff_water_molar_mass_mismatch' and r.evaluations_attempted==0


def test_callback_domain_failure_preserves_cost_and_prefix(monkeypatch):
    from sludge_sandbox.integration import DomainExit
    pair,initial,c,t=setup(monkeypatch);old=WetPair.evaluate;calls=[0]
    def fail(self,states):
        calls[0]+=1
        if calls[0]==2:raise DomainExit('manufactured_midpoint_domain')
        return old(self,states)
    monkeypatch.setattr(WetPair,'evaluate',fail)
    r=run(pair,initial,c,t)
    assert r.status=='domain_exit' and r.evaluations_attempted==2 and r.evaluations_completed==1
    assert r.predictor_state is not None and r.projection is None and t.aggregate.events==0


def test_actual_coincident_shared_host_rejected_without_index_choice(monkeypatch):
    pair,initial,c,t=setup(monkeypatch);initial=(initial[0],initial[0])
    c=replace(c,original_states=initial);t=MixedWritebackTotals.empty(c)
    r=run(pair,initial,c,t)
    assert r.status=='failed' and r.reason=='unsupported_exact_coincident_first_roots'
    assert r.root_order is None and r.projection is None and len(r.samples)==2
    assert r.root_search_evidence


def test_actual_close_roots_are_strictly_ordered_not_timegate_separated(monkeypatch):
    pair,initial,c,t=setup(monkeypatch)
    b=replace(initial[0],liquid_water_mol=initial[0].liquid_water_mol*1.000001)
    b=replace(b,internal_energy_j=pair.storages[1].evaluate(b,305.).total_internal_energy_j)
    initial=(initial[0],b);c=replace(c,original_states=initial);t=MixedWritebackTotals.empty(c)
    r=run(pair,initial,c,t)
    assert r.status=='prepared',r.reason
    assert len(r.root_order.candidates)==2 and not r.root_order.exclusions
    a,b=(entry.evidence for entry in r.root_order.candidates)
    assert a.upper<b.lower and b.upper.elapsed_since(a.lower)<F(1e-8)
    assert r.projection.states[1].liquid_water_mol>0


def test_refinement_budget_and_original_local_budget_are_not_reset(monkeypatch):
    pair,initial,c,t=setup(monkeypatch)
    r=run(pair,initial,c,t,maximum_refinements=1)
    assert r.status=='failed' and r.reason=='unsupported_root_order_refinement_budget'
    assert r.root_search_evidence and r.projection is None
    c=replace(c,original_liquid_fraction_limit=F(1,10**50));t=MixedWritebackTotals.empty(c)
    r=run(pair,initial,c,t)
    assert r.status=='failed' and r.reason=='original_cell_liquid_fraction_budget'
    assert r.evidence is not None and r.ledger is not None and r.projection is None
    assert t.aggregate.events==0


def test_large_exact_origin_and_source_drift_after_midpoint(monkeypatch):
    pair,initial,c,t=setup(monkeypatch);a=run(pair,initial,c,t)
    shift=F(10**12);c=replace(c,original_time=T(shift));t=MixedWritebackTotals.empty(c)
    b=prepare_mixed_terminal(pair,initial,start=T(shift),upper=T(shift+F(1,1000)),context=c,totals=t,time_absolute_s=1e-8)
    assert b.status=='prepared' and b.projection.states==a.projection.states
    assert b.ledger.exact_integrals==a.ledger.exact_integrals
    assert b.evidence.clock.lower.seconds-a.evidence.clock.lower.seconds==shift
    old=WetPair.evaluate;calls=[0]
    def changed(self,states):
        result=old(self,states);calls[0]+=1
        if calls[0]==2:object.__setattr__(self,'rate_constants_per_s',(1.,1.))
        return result
    monkeypatch.setattr(WetPair,'evaluate',changed)
    r=prepare_mixed_terminal(pair,initial,start=T(shift),upper=T(shift+F(1,1000)),context=c,totals=t,time_absolute_s=1e-8)
    assert r.status=='failed' and 'source' in r.reason and r.evaluations_completed==2 and r.projection is None


def test_policy_drift_after_callback_does_not_relax_original_gate(monkeypatch):
    pair,initial,c,t=setup(monkeypatch);old=WetPair.evaluate
    def changed(self,states):
        result=old(self,states)
        object.__setattr__(c,'original_liquid_fraction_limit',F('1e-9'))
        return result
    monkeypatch.setattr(WetPair,'evaluate',changed)
    r=run(pair,initial,c,t)
    assert r.status=='failed' and r.reason=='original_terminal_context_or_totals_changed'
    assert r.evaluations_attempted==r.evaluations_completed==1 and r.projection is None


def test_cancel_and_wall_preserve_prepared_not_committed_states(monkeypatch):
    import sludge_sandbox.mass_wet_exact_terminal as module
    pair,initial,c,t=setup(monkeypatch);calls=[0];old=WetPair.evaluate
    def observed(self,states):
        result=old(self,states);calls[0]+=1;return result
    monkeypatch.setattr(WetPair,'evaluate',observed)
    r=run(pair,initial,c,t,cancel=lambda:calls[0]>=2)
    assert r.status=='cancelled' and r.evaluations_completed==2 and r.projection is None
    assert len(r.samples)==2 and r.predictor_state is not None and t.aggregate.events==0
    ticks=[0]
    def clock():ticks[0]+=1;return ticks[0]*.1
    monkeypatch.setattr(module.time,'monotonic',clock)
    r=run(pair,initial,c,t,maximum_wall_seconds=.15)
    assert r.status=='resource_limit' and r.projection is None
    assert r.evaluations_completed==1 and len(r.samples)==1


def test_negative_kg_predictor_retains_attempted_component_ledger(monkeypatch):
    pair,initial,c,t=setup(monkeypatch);old=WetPair.evaluate
    def extreme(self,states):
        actual=old(self,states)
        # Deliberately manufactured adversarial RHS: retain real observation,
        # replace only a solid derivative to exercise the inventory guard.
        return replace(actual,cells=(replace(actual.cells[0],solid_kg_s=(-1e9,2e9)),actual.cells[1]))
    monkeypatch.setattr(WetPair,'evaluate',extreme)
    r=run(pair,initial,c,t)
    assert r.status=='failed' and r.reason=='negative_trial_inventory'
    assert r.predictor_state is None and r.predictor_ledger is not None
    assert r.evaluations_attempted==r.evaluations_completed==1 and r.projection is None
    assert r.initial_state is initial and t.aggregate.events==0
