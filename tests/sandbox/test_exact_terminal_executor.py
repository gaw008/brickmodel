"""Real pure numerical chain with instrumented exact typed native-host dispatch."""
from copy import copy
from dataclasses import dataclass,replace
from fractions import Fraction as F
import numpy as np
import pytest
from test_exact_free_host import binding_fixture
from test_depletion_integration import policies
from sludge_sandbox.integration import ConservedState,Rates,IntegrationError,DomainExit
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer,WaterTransferEvaluation,CellWaterTransfer
from sludge_sandbox.depletion_roundoff import DepletionRoundoffTotals
from sludge_sandbox.exact_terminal_executor import execute_exact_terminal


def fixture(monkeypatch,*,gap=.001):
    op,providers,_=binding_fixture()
    @dataclass(frozen=True)
    class Layout:liquid_index:int=0
    @dataclass(frozen=True)
    class Thermal:
        storages:tuple
        species_order:tuple=('liquid','H2O')
        inventory_layout:Layout=Layout()
    object.__setattr__(op.base_model,'base_model',Thermal(op.base_model.storages*2))
    identity=('manufactured-terminal','total','same-model')
    object.__setattr__(op.base_model,'_binding',identity)
    calls=[]
    def native(self,state):
        calls.append((state,self.interfaces))
        sinks=[1. if m=='existing_liquid' else 0. for m in self.interfaces]
        r=Rates(np.zeros((3,2)),np.zeros(3),np.array([[-s,s] for s in sinks]),np.array([2.,3.]),{'body':np.array([2.,3.])},mechanical_rates_per_s=np.array([.1,.2,.3]))
        transfers=tuple(CellWaterTransfer(s,1.,None,None,None,None,None,'instrumented') for s in sinks)
        return WaterTransferEvaluation(r,None,transfers,'test','1','virtual_design_choice',('instrumented',),interface_modes=self.interfaces)
    def mode(self,state,cells):
        changed=copy(self);modes=list(self.interfaces)
        for i in cells:
            assert state.amounts_mol[i,0]==0
            modes[i]='depleted_no_nucleation'
        object.__setattr__(changed,'interface_modes',tuple(modes));return changed
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',native)
    monkeypatch.setattr(WaterPhaseTransfer,'with_depleted_cells',mode)
    p,e=policies();p=replace(p,stretch_absolute_tolerance=1e-9,stretch_scale=1.);e=replace(e,terminal_method='affine_midpoint')
    @dataclass(frozen=True)
    class Reference:molar_mass_kg_mol:float=e.roundoff_policy.molar_mass_kg_mol
    reference=Reference()
    for provider in providers:object.__setattr__(provider,'reference',reference)
    object.__setattr__(op.chemical.vapor,'reference',reference)
    view=ExactFreeWaterTransfer(op)
    state=ConservedState([[.01,0.],[.01+gap,0.]],[10.,20.],identity,mechanical_stretches=[1.,1.,1.])
    args=dict(start=T(F(10**12)),common_endpoint=T(F(10**12)+F(3,100)),integration_policy=p,event_policy=e,totals=DepletionRoundoffTotals(e.roundoff_policy))
    return state,view,args,calls,providers,native,mode


def test_actual_numerical_chain_records_three_observations_and_uncommitted_state(monkeypatch):
    state,view,kw,calls,_,_,_=fixture(monkeypatch)
    result=execute_exact_terminal(state,view,**kw)
    assert result.status=='speculative_completed',result.reason
    assert len(calls)==3 and [x.role for x in result.observations]==['initial','midpoint','endpoint']
    assert result.costs.evaluation_attempts==result.costs.evaluation_completed==3
    assert result.costs.predictor_panels==result.costs.terminal_panels==result.costs.mode_transition_attempts==1
    assert result.root_order.selected_cell==0
    assert result.corrected_state.amounts_mol[0,0]==0
    assert view.operator.interfaces==('existing_liquid',)*2 and state.amounts_mol[0,0]==.01
    assert result.candidate_operator.operator.interfaces==('depleted_no_nucleation','existing_liquid')
    assert kw['totals'].events==0
    h=result.terminal_panel.ledger.end_s.elapsed_since(kw['start'])
    assert abs(float(h)-.01)<1e-12
    np.testing.assert_allclose(result.corrected_state.internal_energy_j,[10+2*float(h),20+3*float(h)],rtol=0,atol=1e-12)
    np.testing.assert_allclose(result.corrected_state.mechanical_stretches,[1+.1*float(h),1+.2*float(h),1+.3*float(h)],rtol=0,atol=1e-12)
    assert result.terminal_panel.ledger.end_s.display().seconds_binary64==float(10**12+.01)
    with pytest.raises(ValueError):result.corrected_state.amounts_mol[0,0]=1.


def test_endpoint_failure_retains_speculative_accounting_without_original_mutation(monkeypatch):
    state,view,kw,calls,_,native,_=fixture(monkeypatch)
    def fail(self,current):
        if self.interfaces[0]=='depleted_no_nucleation':raise DomainExit('endpoint_failure')
        return native(self,current)
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',fail)
    r=execute_exact_terminal(state,view,**kw)
    assert r.status=='domain_exit' and r.reason=='endpoint_failure'
    assert r.costs.evaluation_attempts==3 and r.costs.evaluation_completed==2
    assert r.terminal_panel is not None and r.corrected_state is not None
    assert view.operator.interfaces==('existing_liquid',)*2 and kw['totals'].events==0


def test_cancel_after_midpoint_retains_only_predictor_and_completed_observations(monkeypatch):
    state,view,kw,calls,_,_,_=fixture(monkeypatch)
    r=execute_exact_terminal(state,view,**kw,cancel=lambda:len(calls)>=2)
    assert r.status=='cancelled' and r.costs.evaluation_attempts==r.costs.evaluation_completed==2
    assert len(r.observations)==2 and r.predictor_panel is not None
    assert r.terminal_panel is None and r.candidate_operator is None


def test_mode_change_cannot_smuggle_coefficient_content_change(monkeypatch):
    state,view,kw,calls,_,_,mode=fixture(monkeypatch)
    def changed(self,current,cells):
        value=mode(self,current,cells);object.__setattr__(value,'coefficient_version','changed');return value
    monkeypatch.setattr(WaterPhaseTransfer,'with_depleted_cells',changed)
    r=execute_exact_terminal(state,view,**kw)
    assert r.reason=='terminal_mode_transition_content_mismatch' and len(calls)==2
    assert view.operator.coefficient_version is None


def test_actual_provider_mutation_is_detected_by_pre_post_identity(monkeypatch):
    state,view,kw,calls,providers,native,_=fixture(monkeypatch)
    def changed(self,current):
        result=native(self,current)
        if len(calls)==2:object.__setattr__(providers[2],'implementation',replace(providers[2].implementation,provider_version='changed'))
        return result
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',changed)
    r=execute_exact_terminal(state,view,**kw)
    assert r.reason=='exact_autonomous_source_binding_changed'
    assert r.costs.evaluation_attempts==2 and r.costs.evaluation_completed==1
    assert r.candidate_operator is None and kw['totals'].events==0


def test_equal_roots_explicitly_fail_without_mode_attempt(monkeypatch):
    state,view,kw,calls,_,_,_=fixture(monkeypatch,gap=0.)
    r=execute_exact_terminal(state,view,**kw)
    assert r.status=='failed' and 'coincident' in r.reason
    assert r.failure_diagnostic is not None and r.costs.mode_transition_attempts==0
    assert r.terminal_panel is None


def test_initial_identity_and_time_contract_rejected_before_host_call(monkeypatch):
    state,view,kw,calls,_,_,_=fixture(monkeypatch)
    bad=ConservedState(state.amounts_mol,state.internal_energy_j,('wrong','scope','source'),mechanical_stretches=state.mechanical_stretches)
    r=execute_exact_terminal(bad,view,**kw)
    assert r.reason=='terminal_energy_model_identity_mismatch' and not calls
    with pytest.raises(IntegrationError):execute_exact_terminal(state,view,**dict(kw,start=.5))


def test_original_water_mass_gate_before_any_observation(monkeypatch):
    state,view,kw,calls,_,_,_=fixture(monkeypatch)
    wrong=replace(kw['event_policy'].roundoff_policy,molar_mass_kg_mol=.02)
    kw.update(event_policy=replace(kw['event_policy'],roundoff_policy=wrong),totals=DepletionRoundoffTotals(wrong))
    r=execute_exact_terminal(state,view,**kw)
    assert r.reason=='roundoff_water_molar_mass_mismatch' and calls==[]
    assert r.costs.evaluation_attempts==0


def test_failed_predictor_records_attempt_without_completed_panel(monkeypatch):
    state,view,kw,calls,_,native,_=fixture(monkeypatch)
    def bad(self,current):
        result=native(self,current)
        rates=replace(result.rates,mechanical_rates_per_s=np.array([-1000.,0.,0.]))
        return replace(result,rates=rates)
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',bad)
    r=execute_exact_terminal(state,view,**kw)
    assert r.status=='failed' and r.costs.predictor_panel_attempts==1 and r.costs.predictor_panels==0
    assert r.costs.evaluation_attempts==r.costs.evaluation_completed==1
    assert r.costs.mode_transition_attempts==0


def test_actual_state_dependent_midpoint_selects_root_not_tangent_hint(monkeypatch):
    state,view,kw,calls,_,native,_=fixture(monkeypatch,gap=0.)
    def accelerated(self,current):
        result=native(self,current)
        sink=1.+50.*(current.internal_energy_j[0]-10.) if self.interfaces[1]=='existing_liquid' else 0.
        source=np.array(result.rates.reaction_species_mol_s);source[1]=[-sink,sink]
        transfers=(result.cell_transfers[0],replace(result.cell_transfers[1],rate_mol_s=sink))
        return replace(result,rates=replace(result.rates,reaction_species_mol_s=source),cell_transfers=transfers)
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',accelerated)
    r=execute_exact_terminal(state,view,**kw)
    assert r.status=='speculative_completed',r.reason
    assert r.root_order.selected_cell==1
    assert r.candidate_operator.operator.interfaces==('existing_liquid','depleted_no_nucleation')
    assert r.corrected_state.amounts_mol[0,0]>0
    assert abs(float(r.terminal_panel.ledger.end_s.elapsed_since(kw['start']))-(3**.5-1)/100)<1e-10


def test_wall_limit_before_call_preserves_zero_attempt_cost(monkeypatch):
    import sludge_sandbox.exact_terminal_executor as module
    from types import SimpleNamespace
    state,view,kw,calls,_,_,_=fixture(monkeypatch)
    ticks=iter((0.,31.,32.));monkeypatch.setattr(module,'time',SimpleNamespace(monotonic=lambda:next(ticks)))
    r=execute_exact_terminal(state,view,**kw)
    assert r.status=='resource_limit' and r.reason=='wall_time_limit' and calls==[]
    assert r.costs.evaluation_attempts==r.costs.mode_transition_attempts==0


def test_wall_limit_after_midpoint_preserves_observations_and_predictor(monkeypatch):
    import sludge_sandbox.exact_terminal_executor as module
    from types import SimpleNamespace
    state,view,kw,calls,_,_,_=fixture(monkeypatch)
    monkeypatch.setattr(module,'time',SimpleNamespace(monotonic=lambda:31. if len(calls)>=2 else 0.))
    r=execute_exact_terminal(state,view,**kw)
    assert r.status=='resource_limit' and r.reason=='wall_time_limit'
    assert r.costs.evaluation_attempts==r.costs.evaluation_completed==2
    assert [o.role for o in r.observations]==['initial','midpoint']
    assert r.predictor_panel is not None and r.terminal_panel is None
    assert r.costs.terminal_panel_attempts==r.costs.mode_transition_attempts==0
    assert r.candidate_operator is None and kw['totals'].events==0


def test_same_reason_integration_error_is_not_domain_exit(monkeypatch):
    state,view,kw,calls,_,native,_=fixture(monkeypatch)
    def fail(self,current):
        if self.interfaces[0]=='depleted_no_nucleation':raise IntegrationError('endpoint_failure')
        return native(self,current)
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',fail)
    r=execute_exact_terminal(state,view,**kw)
    assert r.status=='failed' and r.reason=='endpoint_failure'
    assert r.costs.evaluation_attempts==3 and r.costs.evaluation_completed==2
    assert r.corrected_state is not None and r.terminal_panel is not None
    assert view.operator.interfaces==('existing_liquid',)*2 and kw['totals'].events==0
