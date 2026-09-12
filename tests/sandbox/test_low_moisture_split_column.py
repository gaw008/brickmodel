"""Same-source split updates: stiff positivity, shared ledgers and accepted prefixes."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from test_low_moisture_column import setup
from test_controlled_vapor_column import boundary
from sludge_sandbox.low_moisture_fast_inverse import NUMERICAL_POLICY_ID
from sludge_sandbox.source_wet_column import integrate_source_column
from sludge_sandbox.low_moisture_split_column import (
    integrate_low_moisture_split, freeze_local_coefficients,
)


def case(monkeypatch):
    base, initial = setup(monkeypatch)
    base=replace(base, inverse_strategy=NUMERICAL_POLICY_ID,
        faces=tuple(replace(f,diffusivities_m2_s=(0.,)*3,permeability_m2=0.) for f in base.faces))
    return boundary(base, coefficient=1e-3), initial


def test_stiff_vapor_contact_is_positive_and_preserves_each_shared_update(monkeypatch):
    column, initial = case(monkeypatch)
    explicit = integrate_source_column(column, initial, duration_s=1., steps=1)
    assert explicit.status == 'domain_exit' and explicit.states == (initial,)
    run = integrate_low_moisture_split(column, initial, duration_s=1., steps=2)
    assert run.status == 'completed', run.reason
    assert run.times_s == (F(), F(1,2), F(1))
    assert run.evaluations_completed == 5
    for old, new, ledger in zip(run.states,run.states[1:],run.ledgers):
        assert ledger.local_states[0].liquid_water_mol > 0
        for before, after, faces, phase, error in (
            (old,ledger.local_states,ledger.local_faces,ledger.phase_water_mol,ledger.local_roundoff),
            (ledger.local_states,new,ledger.slow_faces,(F(),)*2,ledger.slow_roundoff)):
            for i,(s,t) in enumerate(zip(before,after)):
                assert F(t.internal_energy_j)-F(s.internal_energy_j) == faces[i].energy_j-faces[i+1].energy_j+error.energy_j[i]
                assert F(t.liquid_water_mol)-F(s.liquid_water_mol) == getattr(faces[i],'moisture_mol',F())-getattr(faces[i+1],'moisture_mol',F())-phase[i]+error.liquid_mol[i]
                for k in range(3):
                    assert F(t.gas_amounts_mol[k])-F(s.gas_amounts_mol[k]) == faces[i].gas_mol[k]-faces[i+1].gas_mol[k]+(phase[i] if k==2 else F())+error.gas_mol[i][k]
        assert all(f.gas_mol==(F(),)*3 for f in ledger.slow_faces)
        assert ledger.slow_faces[-1].energy_j == ledger.slow_faces[-1].conduction_j
        assert ledger.local_faces[-1].energy_j == ledger.local_steps[-1].outlet_enthalpy_j
        assert all(step.additional_latent_energy_j == 0 for step in ledger.local_steps)
        assert all(s.liquid_water_mol>=0 and all(n>=0 for n in s.gas_amounts_mol) for s in new)
    assert not run.material_qualified
    assert run.failed_trial is None


def test_freeze_keeps_actual_context_and_refuses_cross_state_or_high_W(monkeypatch):
    column, initial = case(monkeypatch)
    rates = column.evaluate(initial)
    frozen = freeze_local_coefficients(column,initial,rates)
    assert frozen[0].coefficients.c_s_inv == frozen[0].coefficients.forcing_mol_s == 0
    assert frozen[-1].coefficients.c_s_inv > 0
    assert frozen[0].peq_per_condensed_mol_pa > 0  # Exact dry limit uses the source join.
    for state,cell,w in zip(initial,rates.cells,frozen):
        assert w.state is state and w.inverse is cell.inverse and w.phase is cell.phase
        c=w.coefficients
        assert c.input_classification=='manufactured_test_fixture'
        assert dict(w.origin_classifications)['local_phase_coefficient']=='manufactured_test_fixture'
        assert w.phase_rate_readout_residual_mol_s == c.a_s_inv*F(state.liquid_water_mol)-c.b_s_inv*F(state.gas_amounts_mol[2])-F(cell.phase.phase_water_mol_s)
    changed=(replace(initial[0],internal_energy_j=initial[0].internal_energy_j+1.),initial[1])
    with pytest.raises(ValueError,match='state_mismatch'):
        freeze_local_coefficients(column,changed,rates)
    high=column.storages[0].state(.2,initial[0].gas_amounts_mol,0.)
    high=replace(high,internal_energy_j=column.storages[0].evaluate(high,330.).total_internal_energy_j)
    high_states=(high,initial[1])
    with pytest.raises(ValueError,match='low_moisture_split_domain'):
        freeze_local_coefficients(column,high_states,column.evaluate(high_states))


def test_failure_after_local_step_preserves_only_accepted_prefix(monkeypatch):
    column, initial = case(monkeypatch)
    from sludge_sandbox.controlled_vapor_column import ControlledVaporColumn
    original=ControlledVaporColumn.evaluate
    calls=[]
    def fail_after_local(self,states):
        calls.append(states)
        if len(calls)==3:
            raise ValueError('manufactured_end_check_failure')
        return original(self,states)
    monkeypatch.setattr(ControlledVaporColumn,'evaluate',fail_after_local)
    run=integrate_low_moisture_split(column,initial,duration_s=1.,steps=2)
    assert run.status=='failed' and run.reason=='manufactured_end_check_failure'
    assert run.states==(initial,) and run.times_s==(F(),) and not run.ledgers
    assert run.failed_trial.local_states is not None
    assert run.failed_trial.proposed_states is not None
    assert run.failed_trial.stage=='final_decode'
    assert run.evaluations_attempted==3 and run.evaluations_completed==2


def test_cancel_and_budget_exit_do_not_commit_a_partial_step(monkeypatch):
    column,initial=case(monkeypatch)
    cancelled=integrate_low_moisture_split(column,initial,duration_s=1.,steps=1,cancel=lambda:True)
    assert cancelled.status=='cancelled' and cancelled.states==(initial,)
    assert cancelled.evaluations_attempted==0
    refused=integrate_low_moisture_split(column,initial,duration_s=1.,steps=1,energy_roundoff_budget_j=1e-30)
    assert refused.status=='failed' and 'budget' in refused.reason
    assert refused.states==(initial,) and not refused.ledgers


def test_actual_sourced_internal_water_and_heat_bath_are_each_applied_once(monkeypatch):
    from test_low_moisture_transport_column import setup as sourced_setup
    from sludge_sandbox.controlled_vapor_column import ControlledVaporColumn, VaporBoundaryControl
    base,initial=sourced_setup(monkeypatch)
    column=ControlledVaporColumn(replace(base,inverse_strategy=NUMERICAL_POLICY_ID),
        VaporBoundaryControl(0.,1e-8,350.,.001,('virtual:split-contact',)))
    run=integrate_low_moisture_split(column,initial,duration_s=1/128,steps=1)
    assert run.status=='completed',run.reason
    ledger=run.ledgers[0]
    face=ledger.slow_faces[1]
    assert face.moisture_mol!=0 and face.moisture_enthalpy_j!=0
    assert face.moisture_witness.source_state_binding_verified
    for i,inv in enumerate(face.moisture_witness.inverses):
        assert inv.target_energy_j==ledger.local_states[i].internal_energy_j
    water=lambda row:sum((F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in row),F())
    errors=(ledger.local_roundoff,ledger.slow_roundoff)
    expected=-ledger.local_steps[-1].outlet_transfer_mol+sum((sum(e.liquid_mol)+sum(r[2] for r in e.gas_mol) for e in errors),F())
    assert water(run.states[-1])-water(initial)==expected
    delta_U=sum((F(n.internal_energy_j)-F(o.internal_energy_j) for o,n in zip(initial,run.states[-1])),F())
    assert delta_U==-ledger.local_steps[-1].outlet_enthalpy_j-ledger.slow_faces[-1].energy_j+sum((sum(e.energy_j) for e in errors),F())
    assert run.energy_roundoff_used_j==ledger.step_energy_roundoff_j
    assert run.inventory_roundoff_used_mol==ledger.step_inventory_roundoff_mol
