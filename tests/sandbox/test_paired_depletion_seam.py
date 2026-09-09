"""Integration transaction tests with an explicit control-flow stand-in.

The paired calculator and native host admission are replaced here; these tests
prove snapshot/cost/cancellation plumbing, not liquid physics or certificates.
Actual helper/host and native probes are validated separately.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
from types import SimpleNamespace as NS
import numpy as np
import pytest
from sludge_sandbox import depletion_integration as m
from sludge_sandbox import pressure_comparison as pc
from sludge_sandbox.paired_pressure_host import SharedConstantParameterBox
from sludge_sandbox.integration import ConservedState, Rates
from test_depletion_integration import policies

@dataclass(frozen=True)
class ControlFlowHost:
    interfaces: tuple = ('existing_liquid',)
    liquid_index: int = 0
    water_vapor_index: int = 1
    source_ids: tuple = ('manufactured:transaction-test',)
    @property
    def chemical(self):
        return NS(reference=NS(molar_mass_kg_mol=.018015268),
                  water=NS(implementation=None),source_asset_sha256={})
    @property
    def base_model(self):return NS(energy_model_identity=None,operator_identity=None)
    def breakpoints_s(self,start,end):return ()
    def with_depleted_cells(self,state,cells):
        assert all(state.amounts_mol[c,0]==0 for c in cells)
        modes=list(self.interfaces)
        for c in cells:modes[c]='depleted_no_nucleation'
        return replace(self,interfaces=tuple(modes))
    def evaluate(self,state,t):
        sink=(.001+.002*t) if self.interfaces[0]=='existing_liquid' else 0.
        rates=Rates(np.zeros((2,2)),np.zeros(2),[[-sink,sink]],[0.])
        inverse=NS(token_state=state,token_time=t)
        base=NS(storage_states=(NS(mechanical=NS(temperature_k=300.,pressure_pa=100000.),pressure_error_bound_pa=.01),),
                storage_inverses=(NS(temperature_error_bound_k=0.),),total_inverses=(inverse,))
        return NS(rates=rates,cell_transfers=(NS(rate_mol_s=sink),),base_evaluation=base)
    def __call__(self,state,t):return self.evaluate(state,t).rates


def setup(monkeypatch, mode='success'):
    import sludge_sandbox.water_phase_transfer as water
    monkeypatch.setattr(water,'WaterPhaseTransfer',ControlFlowHost)
    box=SharedConstantParameterBox('a'*64,('A',),(F(1),),(F(0),),F(2),F(0))
    p,e=policies();e=replace(e,pressure_comparison=pc.PressureComparisonPolicy((box,)))
    monkeypatch.setattr(pc,'pressure_comparison_binding',lambda op:{'boxes':e.pressure_comparison.to_record()['cell_boxes']})
    trace={'attempts':0,'completed':0,'pairs':[],'cancel':False}
    def compare(opa,a,ia,opb,b,ib,*,policy,before_endpoint,after_endpoint):
        assert ia[0].token_state is a and ib[0].token_state is b
        trace['pairs'].append((ia[0].token_time,ib[0].token_time,opa.interfaces,opb.interfaces))
        for i in range(4):
            before_endpoint();trace['attempts']+=1
            if mode=='fail_second' and trace['attempts']==2:raise ValueError('endpoint_test_failure')
            trace['completed']+=1
            if mode=='cancel_second' and trace['completed']==2:trace['cancel']=True
            after_endpoint(None)
        return NS(to_record=lambda:{'bound_pa':0.})
    monkeypatch.setattr(pc,'compare_pressure_pair',compare)
    initial=ConservedState([[1e-4,0.]],[600.])
    return p,e,initial,trace


def test_opt_in_uses_saved_event_and_common_snapshots_and_charges_calls(monkeypatch):
    p,e,initial,trace=setup(monkeypatch)
    out=m.integrate_depletion(initial,ControlFlowHost(),start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert len(out.events)==1 and trace['pairs']
    assert any(a!=b for a,b,_,_ in trace['pairs'])  # event pair at different times
    assert any(a==b for a,b,_,_ in trace['pairs'])  # common horizon pair
    costs=out.phase_costs['comparison']
    assert costs['endpoint_attempts']==costs['endpoint_completed']==trace['attempts']==4*len(trace['pairs'])
    refs=[r for r in out.refinements if r.differences is not None]
    for ref in refs:
        d=ref.comparison_details['pressure_comparison']
        assert d['original_independent_pressure_difference_pa']==.02
        assert d['selected_pressure_difference_pa']==ref.differences[4]==0.
        assert set(d['pairs'])=={'event','common'}


@pytest.mark.parametrize('mode,status,complete',[('fail_second','failed',1),('cancel_second','cancelled',2)])
def test_failed_or_cancelled_pair_preserves_accepted_prefix_and_attempts(monkeypatch,mode,status,complete):
    p,e,initial,trace=setup(monkeypatch,mode)
    out=m.integrate_depletion(initial,ControlFlowHost(),start_s=0.,end_s=.2,integration_policy=p,event_policy=e,
                              cancel=lambda:trace['cancel'])
    assert out.status==status,out.reason
    assert out.steps and not out.events and out.states[-1].amounts_mol[0,0]>0
    assert out.phase_costs['comparison']['endpoint_attempts']==2
    assert out.phase_costs['comparison']['endpoint_completed']==complete
    assert out.operator.interfaces==('existing_liquid',)


def test_default_does_not_use_pair_calculator_or_new_cost_fields(monkeypatch):
    p,e,initial,trace=setup(monkeypatch)
    e=replace(e,pressure_comparison=None)
    out=m.integrate_depletion(initial,ControlFlowHost(),start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
    assert not trace['pairs']
    assert 'endpoint_attempts' not in out.phase_costs['comparison']
    assert not out.events
    assert any(r.differences and r.differences[4]==.02 for r in out.refinements)


def test_wrong_declared_box_rejected_before_any_trajectory(monkeypatch):
    p,e,initial,trace=setup(monkeypatch)
    box=replace(e.pressure_comparison.cell_boxes[0],reference_volume_m3=F(3))
    changed=replace(e,pressure_comparison=pc.PressureComparisonPolicy((box,)))
    with pytest.raises(m.DepletionIntegrationError,match='original_box_binding'):
        m.integrate_depletion(initial,ControlFlowHost(),start_s=0.,end_s=.2,integration_policy=p,event_policy=changed)
    assert not trace['pairs']
