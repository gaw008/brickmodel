"""N-cell coupling with declared artificial liquid/transport; not material data."""
from dataclasses import replace
from fractions import Fraction as F
import math

import pytest

from test_source_wet_storage import setup as storage_setup
from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.water_properties import WaterProperties
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.mass_wet_transport import WetFace
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.source_wet_column import SourceWetColumn, integrate_source_column


def setup(monkeypatch, count=3):
    storage, _, _ = storage_setup(monkeypatch)
    original = WaterProperties.state_tp
    def liquid(w, t, p, *, phase):
        value = original(w, t, p, phase=phase)
        return replace(value, native_entropy_j_kg_k=(75*math.log(t/300)+75)/w.reference.molar_mass_kg_mol,
                       method_id='iapws95_real_fluid_helmholtz')
    monkeypatch.setattr(WaterProperties, 'state_tp', liquid)
    widths = tuple(.25+.0625*i for i in range(count))
    faces = tuple(WetFace(.01, (widths[i]/2, widths[i+1]/2), (.5, .7),
                         (1e-5, 2e-5, 1.5e-5), 1e-13, 1.8e-5,
                         ('manufactured:source-column-transport',)) for i in range(count-1))
    column = SourceWetColumn((storage,)*count, (InversePolicy(1e-6, 1e-6, 100),)*count,
        WaterChemicalPotential(REPOSITORY/'data/sandbox/water'), (1e-9,)*count,
        faces, widths, .01, ('existing_liquid',)*count,
        ('manufactured:source-column-transport',))
    states = []
    for i in range(count):
        state = storage.state(.25, (.125+.03125*i, .25, .00390625*(i+1)), 0.)
        states.append(replace(state, internal_energy_j=storage.evaluate(state, 325.+2*i).total_internal_energy_j))
    return column, tuple(states)


@pytest.mark.parametrize('count', [1, 2, 3, 4])
def test_arbitrary_cell_topology_and_shared_face_count(monkeypatch, count):
    column, states = setup(monkeypatch, count)
    import sludge_sandbox.source_wet_column as module
    original = module.evaluate_wet_face
    calls = []
    def observed(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(module, 'evaluate_wet_face', observed)
    out = column.evaluate(states)
    assert len(calls) == count-1 and len(out.faces) == count+1 and len(out.cells) == count
    assert tuple(face.face_id for face in out.faces) == tuple(range(count+1))
    assert all(face.energy_w == 0 and face.gas_mol_s == (0.,)*3 for face in (out.faces[0], out.faces[-1]))
    assert all(cell.chemistry.solid_kg_s == (0,) and cell.chemistry.gas_mol_s == (0, 0, 0) for cell in out.cells)
    assert not out.material_qualified


def test_N3_midpoint_ledger_and_exact_global_roundoff_account(monkeypatch):
    column, initial = setup(monkeypatch)
    run = integrate_source_column(column, initial, duration_s=1/128, steps=2)
    assert run.status == 'completed', run.reason
    assert run.evaluations_attempted == run.evaluations_completed == 6
    assert run.times_s[-1] == F(1, 128) and len(run.ledgers) == 2
    for old, new, ledger in zip(run.states, run.states[1:], run.ledgers):
        assert len(ledger.faces) == 4
        for i in range(3):
            assert new[i].solid_mass_kg == old[i].solid_mass_kg
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == (
                ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i])
            assert F(new[i].liquid_water_mol)-F(old[i].liquid_water_mol) == -ledger.phase_water_mol[i]+ledger.roundoff.liquid_mol[i]
            for k in range(3):
                assert F(new[i].gas_amounts_mol[k])-F(old[i].gas_amounts_mol[k]) == (
                    ledger.faces[i].gas_mol[k]-ledger.faces[i+1].gas_mol[k]+
                    (ledger.phase_water_mol[i] if k == 2 else 0)+ledger.roundoff.gas_mol[i][k])
        assert sum(F(s.internal_energy_j) for s in new)-sum(F(s.internal_energy_j) for s in old) == sum(ledger.roundoff.energy_j)
        water = lambda states: sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in states)
        assert water(new)-water(old) == sum(ledger.roundoff.liquid_mol)+sum(row[2] for row in ledger.roundoff.gas_mol)
        assert ledger.predictor_roundoff is not ledger.roundoff
        assert ledger.faces[1].energy_j != ledger.faces[2].energy_j


def test_cancel_resource_failure_and_no_partial_step_commit(monkeypatch):
    column, initial = setup(monkeypatch)
    run = integrate_source_column(column, initial, duration_s=.01, steps=3, cancel=lambda: True)
    assert run.status == 'cancelled' and run.states == (initial,) and not run.ledgers
    run = integrate_source_column(column, initial, duration_s=100000., steps=1)
    assert run.status in ('failed', 'domain_exit') and run.states == (initial,) and not run.ledgers
    run = integrate_source_column(column, initial, duration_s=.01, steps=1, maximum_wall_seconds=1e-12)
    assert run.status == 'resource_limit' and run.evaluations_attempted == 0


def test_invalid_geometry_layout_and_false_material_admission(monkeypatch):
    column, states = setup(monkeypatch)
    for changes in ({'faces': column.faces[:1]}, {'cell_widths_m': (.25,)*3},
        {'boundary_conditions': ('open', 'closed_no_flux')}, {'transport_classification': 'measured_public_data'},
        {'face_area_m2': .00001}, {'storages': ()}, {'interface_modes': ('existing_liquid',)}):
        with pytest.raises(ValueError): replace(column, **changes)
    with pytest.raises(ValueError): column.evaluate(states[:2])
    with pytest.raises(ValueError): column.evaluate((replace(states[0], solid_mass_kg=(.3,)), *states[1:]))


def test_runtime_content_mutation_rejected_before_inverse(monkeypatch):
    column, states = setup(monkeypatch)
    object.__setattr__(column, 'transfer_coefficients_mol_s_pa', (2e-9,)*3)
    with pytest.raises(ValueError, match='content_changed'): column.evaluate(states)


def test_explicit_dry_mode_requires_exact_zero_and_is_not_an_event(monkeypatch):
    column, states = setup(monkeypatch)
    with pytest.raises(ValueError): column.with_depleted_cells(states, (1,))
    dry = replace(states[1], liquid_water_mol=0., gas_amounts_mol=(.25, .25, 0.))
    dry = replace(dry, internal_energy_j=column.storages[1].evaluate(dry, 327.).total_internal_energy_j)
    changed_states = (states[0], dry, states[2])
    switched = column.with_depleted_cells(changed_states, (1,))
    assert switched.model_identity != column.model_identity
    assert switched.evaluate(changed_states).cells[1].phase.phase_water_mol_s == 0
