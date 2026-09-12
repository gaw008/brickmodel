"""Conditional sorption/column integration with an explicit manufactured fluid seam."""
from dataclasses import fields, replace
from fractions import Fraction as F

import pytest

from test_source_wet_column import setup as old_column_setup
from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.arlabosse_wet_thermo import ArlabosseWetThermodynamics
from sludge_sandbox.arlabosse_rigid_sorption import ArlabosseSorptionStorage
from sludge_sandbox.arlabosse_sorption_phase import evaluate_sorption_phase
from sludge_sandbox.source_wet_column import ArlabosseSorptionColumn, SourceWetColumn, integrate_source_column
from sludge_sandbox.mass_wet_transport import evaluate_wet_phase


def setup(monkeypatch):
    old, _ = old_column_setup(monkeypatch, 2)
    wet = ArlabosseWetThermodynamics(REPOSITORY, REPOSITORY/'data/sandbox/water')
    base = replace(old.storages[0], dry_mass_kg=.01)
    storage = ArlabosseSorptionStorage(base, wet, (90000., 110000.))
    values = {f.name: getattr(old, f.name) for f in fields(old) if f.init}
    values['storages'] = (storage, storage)
    column = ArlabosseSorptionColumn(**values)
    states = []
    for i, (liquid, vapor, temperature) in enumerate(((.2, 1e-6, 330.), (.225, 3e-6, 333.))):
        state = storage.state(liquid, (.008, .027-vapor, vapor), 0.)
        states.append(replace(state, internal_energy_j=storage.evaluate(state, temperature).total_internal_energy_j))
    return column, tuple(states)


def test_activity_changes_actual_phase_drive_and_enthalpy(monkeypatch):
    column, states = setup(monkeypatch)
    out = column.evaluate(states)
    for storage, state, cell in zip(column.storages, states, out.cells):
        point = cell.inverse.point
        plain = evaluate_wet_phase(column.chemical, point, state.gas_amounts_mol[2], 1e-9, 'existing_liquid')
        sorption = cell.phase
        assert sorption.phase_water_mol_s < plain.phase_water_mol_s
        assert sorption.equilibrium.equilibrium_partial_pressure_pa == pytest.approx(
            plain.equilibrium.equilibrium_partial_pressure_pa*point.activity, rel=1e-14)
        assert sorption.equilibrium.phase_enthalpy_difference_j_mol == pytest.approx(
            plain.equilibrium.phase_enthalpy_difference_j_mol-point.excess_partial_water_enthalpy_j_mol)
        assert sorption.entropy_production_w_k >= 0
        assert not sorption.equilibrium.material_qualified


def test_shared_faces_and_every_step_preserve_water_and_U(monkeypatch):
    column, states = setup(monkeypatch)
    run = integrate_source_column(column, states, duration_s=1/128, steps=2)
    assert run.status == 'completed', run.reason
    assert len(run.ledgers) == 2
    assert any(s.liquid_water_mol != n.liquid_water_mol for s,n in zip(states,run.states[-1]))
    for old, new, ledger in zip(run.states, run.states[1:], run.ledgers):
        for i in range(2):
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == (
                ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i])
        water = lambda row: sum((F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in row), F())
        assert water(new)-water(old) == sum(ledger.roundoff.liquid_mol)+sum(r[2] for r in ledger.roundoff.gas_mol)
        assert sum(F(s.internal_energy_j) for s in new)-sum(F(s.internal_energy_j) for s in old) == sum(ledger.roundoff.energy_j)
    assert run.observations[-1].faces[1].energy_w != 0
    assert not run.material_qualified


def test_new_branch_refuses_mixed_material_and_dry_mode(monkeypatch):
    column, states = setup(monkeypatch)
    with pytest.raises(ValueError):
        replace(column, storages=(column.storages[0], column.storages[0].base))
    with pytest.raises(ValueError):
        replace(column, interface_modes=('depleted_no_nucleation',)*2)
    with pytest.raises(ValueError):
        column.evaluate((replace(states[0], energy_model_identity=column.storages[0].base.model_identity), states[1]))


def test_old_exact_record_protocol_refuses_sorption_before_packing(monkeypatch):
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    column, _ = setup(monkeypatch)
    with pytest.raises(ValueError, match='actual_fixed_source_column_required'):
        ExactSourceColumn(column)


def test_sorption_condensation_and_liquid_transport_rejection(monkeypatch):
    column, states = setup(monkeypatch)
    storage = column.storages[0]
    state = storage.state(.2, (.008, .025, .002), 0.)
    point = storage.evaluate(state, 330.)
    phase = evaluate_sorption_phase(storage, column.chemical, point, .002, 1e-9, 'existing_liquid')
    assert phase.phase_water_mol_s < 0
    assert phase.chemical_driving_force_j_mol < 0 and phase.entropy_production_w_k > 0
    with pytest.raises(ValueError, match='sorption_liquid_transport_not_supported'):
        replace(column, liquid_transport=object())


def test_plain_column_refuses_new_storage_semantics(monkeypatch):
    column, _ = setup(monkeypatch)
    values = {f.name: getattr(column, f.name) for f in fields(SourceWetColumn) if f.init}
    with pytest.raises(ValueError, match='explicit_sorption_column_type_required'):
        SourceWetColumn(**values)
