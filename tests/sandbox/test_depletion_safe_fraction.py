"""Explicit ordinary inventory guard; terminal/root tolerances remain unchanged."""
from dataclasses import replace
import numpy as np
import pytest
from sludge_sandbox.depletion_integration import DepletionIntegrationError,integrate_depletion
from sludge_sandbox.integration import ConservedState
from test_depletion_integration import policies,oracle
from test_depletion_multicell import two_cell_oracle,initial_state


@pytest.mark.parametrize('value',[True,False,0.,-1.,.5,1.,float('nan'),float('inf'),-float('inf'),'0.4'])
def test_fraction_requires_finite_strictly_between_zero_and_half(value):
    _,event=policies()
    with pytest.raises(DepletionIntegrationError):replace(event,safe_inventory_fraction=value)


def test_default_matches_explicit_quarter_full_trajectory_and_cost():
    policy,event=policies()
    assert event.safe_inventory_fraction==.25
    runs=[integrate_depletion(initial_state(),two_cell_oracle(),start_s=0,end_s=.012,
        integration_policy=policy,event_policy=e) for e in (event,replace(event,safe_inventory_fraction=.25))]
    a,b=runs
    assert a.status==b.status=='completed'
    assert a.times_s==b.times_s and a.evaluations==b.evaluations and a.rejected_trials==b.rejected_trials
    assert a.safe_inventory_fraction==b.safe_inventory_fraction==.25
    for x,y in zip(a.states,b.states):
        assert np.array_equal(x.amounts_mol,y.amounts_mol) and np.array_equal(x.internal_energy_j,y.internal_energy_j)
    for x,y in zip(a.steps,b.steps):
        for name in ('face_species_mol','face_energy_j','reaction_species_mol','cell_work_j'):
            assert np.array_equal(getattr(x,name),getattr(y,name))


def test_point_four_two_cell_shared_faces_and_continuing_reaction():
    p,e=policies();e=replace(e,safe_inventory_fraction=.4)
    out=integrate_depletion(initial_state(),two_cell_oracle(),start_s=0,end_s=.012,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert out.safe_inventory_fraction==.4
    assert [v.time_s for v in out.events]==pytest.approx([.004,.008],rel=0,abs=1e-8)
    for t,state in zip(out.times_s,out.states):
        a=min(t,.004);b=min(t,.008)
        expected=[[0.,max(4.8e-6-.0012*t,0),.01,.01+.001*a-.00005*t],
                  [.0003*t,max(7.2e-6-.001*t+.0002*a,0),.01-.0003*t,.01+.001*b+.00005*t]]
        assert np.max(np.abs(state.amounts_mol-expected))<=1e-10
        assert state.internal_energy_j==pytest.approx([600.-5*t+2*max(t-.004,0),700.+8*t],rel=0,abs=1e-7)
        assert state.amounts_mol[:,[1,3]].sum()==pytest.approx(.020012,rel=0,abs=1e-12)


def test_point_four_preserves_accelerating_oracle_gates(monkeypatch):
    import test_depletion_multicell as prior
    original=prior.policies
    def policies_point_four():
        p,e=original();return p,replace(e,safe_inventory_fraction=.4)
    monkeypatch.setattr(prior,'policies',policies_point_four)
    prior.test_accelerating_second_event_replans_common_time_after_first_switch()


def test_strong_sink_keeps_stage_positivity_and_resource_limit():
    p,e=policies();e=replace(e,safe_inventory_fraction=.4,terminal_window_s=1e-6)
    initial=ConservedState([[1e-4,0.]],[600.])
    out=integrate_depletion(initial,oracle(a=1.),start_s=0,end_s=.001,integration_policy=p,event_policy=e)
    assert out.status=='completed',out.reason
    assert abs(out.events[0].time_s-1e-4)<=1e-8
    assert all(np.all(state.amounts_mol>=0) for state in out.states)
    limited=integrate_depletion(initial,oracle(a=1.),start_s=0,end_s=.001,
        integration_policy=replace(p,maximum_steps=2),event_policy=e)
    assert limited.status=='resource_limit'
    assert limited.accepted_trial_panels<=2 and not limited.events
    assert limited.operator.interfaces==('existing_liquid',)
