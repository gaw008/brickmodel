"""Actual N3 liquid/enthalpy transfer and one mixed wet/dry continuation."""
from dataclasses import replace
from fractions import Fraction as F

import numpy as np
import pytest

from test_source_multicell_terminal import prepare_multicell
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.source_dry_pressure import SourceDryPressure
from sludge_sandbox.source_inverse_pressure import SourceInversePressure
from sludge_sandbox.source_dry_shared_pressure import declare_source_shared_dry_volume
from sludge_sandbox.source_dry_transition import (
    SourceDryTransitionError, _audit_path, compare_source_dry_candidates,
    evaluate_source_dry_transition,
)


@pytest.fixture(scope='module')
def completed_multicell():
    with pytest.MonkeyPatch.context() as patch:
        refinement,end=prepare_multicell(patch)
        storage=refinement.approach.proposal.original_trial.adapter.column.storages[1]
        yield evaluate_source_dry_transition(refinement,end=end,maximum_callbacks_per_path=24,
            shared_volume=declare_source_shared_dry_volume(storage))


def test_actual_middle_cell_event_preserves_liquid_recipient_and_dry_face_law(completed_multicell):
    out=completed_multicell
    assert out.selected_cell_index==1
    initial=out.refinement.approach.proposal.original_trial.initial
    for index,path in enumerate(out.candidates):
        assert path.status=='executed_dry_candidate' and path.terminal.selected_cell_index==1
        assert path.terminal.dry_adapter.interfaces==('existing_liquid','depleted_no_nucleation','existing_liquid')
        assert path.reference.status=='completed' and path.reference.steps
        assert path.reference.states[-1].amounts_mol[1,0]==0
        assert np.all(path.reference.states[-1].amounts_mol[[0,2],0]>0)
        assert path.reference.states[-1].amounts_mol[2,0]>initial.amounts_mol[2,0]
        # Incoming liquid carries the signed enthalpy of the actual reference
        # convention; adding matter need not increase reference-relative U.
        ledgers=(*out.refinement.approach.trial.reference.steps,) if index else ()
        ledgers=(*ledgers,path.terminal.prefix.ledger,*path.reference.steps)
        incoming=sum((F(float(l.face_energy_j[2]))-F(float(l.face_energy_j[3]))
                      +F(float(l.cell_work_j[2])) for l in ledgers),F())
        change=F(float(path.reference.states[-1].internal_energy_j[2]))-F(float(initial.internal_energy_j[2]))
        assert incoming!=0 and change*incoming>0
        assert abs(change-incoming)<=F(path.seed.policy.energy_absolute_tolerance_j)
        wet_face=path.seed.captures[0].evaluation.source_evaluation.faces[2]
        dry_face=path.captures[0].evaluation.source_evaluation.faces[2]
        assert wet_face.liquid_mol_s>0 and wet_face.liquid_enthalpy_w!=0
        assert dry_face.liquid_exchange.status=='zero_mobility' and dry_face.liquid_mol_s==0
        assert dry_face.liquid_exchange.connection==wet_face.liquid_exchange.connection
        assert path.captures[-1].time==path.end
    assert out.candidates[0].end==out.candidates[1].end
    assert not out.material_qualified


def test_all_wet_cell_pressure_gates_still_control_event_acceptance(completed_multicell):
    out=completed_multicell
    assert len(out.shared_pressure_pairs)==2
    for k in range(2):
        assert len(out.cell_endpoint_differences[k])==3
        assert out.cell_selected_pressure_gates[k][1] is True
        assert out.cell_selected_pressure_gates[k][0] is False
        assert out.cell_selected_pressure_gates[k][2] is False
        assert out.selected_pressure_gates[k] is False
        assert out.endpoint_differences[k][3]==tuple(
            max(row[j] for row in out.cell_endpoint_differences[k]) for j in range(4))
        for candidate in out.candidates:
            row=candidate.cell_pressure_endpoints[k]
            assert tuple(type(x) for x in row)==(SourceInversePressure,SourceDryPressure,SourceInversePressure)
            assert candidate.pressure_endpoints[k] is row[1]
    assert not out.numerical_event_accepted


def test_local_and_global_full_path_accounts_remain_separate(completed_multicell):
    out=completed_multicell
    for path in out.balance_paths:
        for row in path:
            assert tuple(c.cell_index for c in row.cell_balances)==(0,1,2)
            for key in ('energy_residual_j','full_energy_residual_j','water_balance_residual_mol',
                        'event_water_storage_roundoff_mol','fluid_mass_residual_kg'):
                assert getattr(row,key)==sum((getattr(c,key) for c in row.cell_balances),F())
            for key in ('inventory_residual_mol','full_inventory_residual_mol'):
                assert getattr(row,key)==tuple(sum((getattr(c,key)[j] for c in row.cell_balances),F())
                                               for j in range(4))
            assert row.cell_balances[0].event_water_storage_roundoff_mol==0
            assert row.cell_balances[2].event_water_storage_roundoff_mol==0


def test_saved_all_cell_binding_and_gates_are_passive_and_not_droppable(completed_multicell,monkeypatch):
    out=completed_multicell
    monkeypatch.setattr(ExactSourceColumn,'evaluate',lambda *a,**k:pytest.fail('passive review called physics'))
    out.check()
    original=compare_source_dry_candidates(out.refinement,out.candidates)
    assert not original.numerical_event_accepted and original.shared_volume is None
    assert original.endpoint_gates==out.endpoint_gates
    candidate=out.candidates[0]
    for rows in ((),tuple((row[1],) for row in candidate.cell_pressure_endpoints)):
        with pytest.raises(ValueError):replace(candidate,cell_pressure_endpoints=rows).check()
    foreign=replace(candidate.pressure_endpoints[0],storage=replace(candidate.pressure_endpoints[0].storage))
    with pytest.raises(ValueError,match='selected_pressure_storage_changed'):
        replace(candidate,pressure_endpoints=(foreign,candidate.pressure_endpoints[1])).check()
    for changes in ({'selected_cell_index':0},{'numerical_event_accepted':True},
                    {'cell_selected_pressure_gates':((True,True,True),)*2},
                    {'cell_endpoint_differences':out.cell_endpoint_differences[:1]}):
        with pytest.raises(ValueError):replace(out,**changes).check()


@pytest.mark.parametrize('energy',[False,True])
def test_opposite_cell_errors_cannot_hide_in_global_balance(completed_multicell,energy):
    candidate=completed_multicell.candidates[0]
    last=candidate.reference.states[-1]
    amounts=last.amounts_mol.copy();heat=last.internal_energy_j.copy()
    if energy:
        heat[0]+=.5;heat[2]-=.5
        assert abs(sum(map(F,heat),F())-sum(map(F,last.internal_energy_j),F()))<=F(candidate.seed.policy.energy_absolute_tolerance_j)
    else:
        amounts[0,1]+=2**-10;amounts[2,1]-=2**-10
        assert sum(map(F,amounts[:,1]),F())==sum(map(F,last.amounts_mol[:,1]),F())
    changed=replace(last,amounts_mol=amounts,internal_energy_j=heat)
    candidate=replace(candidate,reference=replace(candidate.reference,
        states=(*candidate.reference.states[:-1],changed)))
    with pytest.raises(ValueError,match='cumulative_original_balance_budget'):
        _audit_path(candidate)


def test_equal_storage_in_wrong_spatial_cell_cannot_authorize_shared_event(completed_multicell,monkeypatch):
    out=completed_multicell
    column=out.refinement.approach.proposal.original_trial.adapter.column
    assert column.storages[0] is not column.storages[1]
    assert column.storages[0].model_identity==column.storages[1].model_identity
    foreign=declare_source_shared_dry_volume(column.storages[0])
    monkeypatch.setattr(ExactSourceColumn,'evaluate',lambda *a,**k:pytest.fail('wrong-cell declaration called physics'))
    with pytest.raises(ValueError,match='belong_to_original_path'):
        evaluate_source_dry_transition(out.refinement,end=out.candidates[0].end,
            maximum_callbacks_per_path=24,shared_volume=foreign)


def test_later_wet_cell_assessment_failure_retains_completed_dry_run_and_partial_row(completed_multicell,monkeypatch):
    out=completed_multicell
    import sludge_sandbox.source_dry_transition as module
    actual=module.enclose_source_inverse_pressure
    right=out.candidates[0].terminal.dry_adapter.column.storages[2]
    def fail(storage,*args,**kwargs):
        if storage is right:raise RuntimeError('last-wet-cell-assessment')
        return actual(storage,*args,**kwargs)
    monkeypatch.setattr(module,'enclose_source_inverse_pressure',fail)
    with pytest.raises(SourceDryTransitionError) as caught:
        evaluate_source_dry_transition(out.refinement,end=out.candidates[0].end,
            maximum_callbacks_per_path=24,shared_volume=out.shared_volume)
    assert len(caught.value.candidates)==1
    retained=caught.value.candidates[0]
    assert retained.status=='failed' and 'last-wet-cell-assessment' in retained.reason
    assert retained.reference.status=='completed' and retained.captures[-1].time==retained.end
    assert len(retained.cell_pressure_endpoints)==1 and len(retained.cell_pressure_endpoints[0])==2
    assert len(retained.pressure_endpoints)==1


def test_positive_dry_mobility_keeps_real_domain_failure_without_disabling_face(completed_multicell):
    base=completed_multicell.refinement.approach.proposal.original_trial.adapter.column
    with pytest.MonkeyPatch.context() as patch:
        refinement,end=prepare_multicell(patch,base=base,zero_dry_mobility=False)
        with pytest.raises(SourceDryTransitionError) as caught:
            evaluate_source_dry_transition(refinement,end=end,maximum_callbacks_per_path=24)
        retained=caught.value.candidates[0]
        assert retained.status!='executed_dry_candidate'
        assert retained.terminal is not None and retained.terminal.selected_cell_index==1
        assert retained.captures and retained.captures[0].evaluation is None
        assert 'active_face_requires_existing_liquid_both_sides' in retained.captures[0].failure
        assert retained.terminal.dry_adapter.column.liquid_transport.connections[1].status=='connected'
        assert retained.terminal.dry_adapter.column.liquid_transport.relations[1].relative_permeability[0]==.5
        assert not retained.event_admitted and not retained.material_qualified
