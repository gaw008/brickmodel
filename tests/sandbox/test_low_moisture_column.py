"""Actual column dispatch and conserved dry/rewetting inventories with a fluid fixture."""
from dataclasses import fields, replace
from fractions import Fraction as F

import pytest

from test_arlabosse_sorption_column import setup as old_setup
from sludge_sandbox.arlabosse_low_moisture import ArlabosseLowMoisture
from sludge_sandbox.arlabosse_low_moisture_storage import LowMoistureSorptionStorage
from sludge_sandbox.source_wet_column import (
    SourceWetColumn, LowMoistureSorptionColumn, integrate_source_column,
)


def setup(monkeypatch, liquids=(0., .04)):
    old, old_states = old_setup(monkeypatch)
    original = old.storages[0]
    storage = LowMoistureSorptionStorage(original.base, original.wet,
        original.pressure_domain_pa, excess=ArlabosseLowMoisture(original.wet))
    values = {f.name:getattr(old,f.name) for f in fields(SourceWetColumn) if f.init}
    values.update(storages=(storage,storage), interface_modes=('reversible_sorption',)*2)
    column = LowMoistureSorptionColumn(**values)
    states = []
    for nc, previous in zip(liquids,old_states):
        state = storage.state(nc,previous.gas_amounts_mol,0.)
        states.append(replace(state,internal_energy_j=storage.evaluate(state,330.).total_internal_energy_j))
    return column, tuple(states)


def test_zero_inventory_rewets_in_actual_column_with_conservation(monkeypatch):
    column, initial = setup(monkeypatch)
    run = integrate_source_column(column,initial,duration_s=1/128,steps=2)
    assert run.status == 'completed',run.reason
    assert len(run.ledgers)==2
    assert run.states[-1][0].liquid_water_mol>0
    for old,new,ledger in zip(run.states,run.states[1:],run.ledgers):
        for i in range(2):
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j)==(
                ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i])
        water=lambda row:sum((F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in row),F())
        assert water(new)-water(old)==sum(ledger.roundoff.liquid_mol)+sum(r[2] for r in ledger.roundoff.gas_mol)
    assert not run.material_qualified


def test_oversized_depletion_step_refuses_and_preserves_initial_water(monkeypatch):
    column,initial=setup(monkeypatch,(.04,.04))
    column=replace(column,transfer_coefficients_mol_s_pa=(1.,1.))
    run=integrate_source_column(column,initial,duration_s=1.,steps=1)
    assert run.status=='domain_exit' and 'inventory' in run.reason
    assert run.states==(initial,) and not run.ledgers


def test_low_sorption_is_explicit_and_old_event_semantics_stay_closed(monkeypatch):
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    column,states=setup(monkeypatch)
    with pytest.raises(ValueError):
        ExactSourceColumn(column)
    with pytest.raises(ValueError):
        replace(column,interface_modes=('existing_liquid',)*2)
    values={f.name:getattr(column,f.name) for f in fields(SourceWetColumn) if f.init}
    with pytest.raises(ValueError):
        SourceWetColumn(**values)
    with pytest.raises(ValueError):
        column.with_depleted_cells(states,(0,))
