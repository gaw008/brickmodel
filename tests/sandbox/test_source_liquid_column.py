"""Source Cp with explicitly manufactured liquid mobility and liquid fixture."""
from dataclasses import replace
from fractions import Fraction as F
import math
import pytest

from test_source_wet_column import setup as base_setup
from test_programmed_source_wet_column import setup as furnace_setup
from sludge_sandbox.solid_fluid_heat import LiquidTransportConfig
from sludge_sandbox.liquid_transport import SaturationMobilityTable, LiquidConnection
from sludge_sandbox.source_wet_column import SourceWetColumn, LiquidSourceColumnRates, integrate_source_column
from sludge_sandbox.exact_event_clock import ExactEventTime


def config(count, *, status='connected', permeability=1e-15):
    table = SaturationMobilityTable(saturation_knots=(0., 1.),
        permeability_m2=(permeability,)*2, relative_permeability=(.5,)*2, viscosity_pa_s=(.001,)*2,
        temperature_range_k=(310., 350.), pressure_range_pa=(1e4, 1e7),
        model_id='manufactured:source-column-liquid-mobility', version='1',
        classification='manufactured_test_fixture', source_ids=('manufactured:source-column-liquid-mobility',),
        source_asset_sha256=(('manufactured-table', 'c'*64),), relation_kind='frozen_manufactured')
    links = tuple(LiquidConnection(status=status, connection_id='manufactured:source-column-liquid-link-'+str(i),
        version='1', classification='manufactured_test_fixture', source_ids=('manufactured:source-column-liquid-links',))
        for i in range(count-1))
    return LiquidTransportConfig(relations=(table,)*count, connections=links, allow_manufactured=True)


def setup(monkeypatch, *, count=3, **kwargs):
    base, initial = base_setup(monkeypatch, count)
    return replace(base, liquid_transport=config(count, **kwargs)), initial


def test_actual_state_pressure_error_and_single_inverse(monkeypatch):
    model, initial = setup(monkeypatch)
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    original = SourceWetStorage.invert
    calls = []
    def observed(self, state, policy):
        calls.append(state)
        return original(self, state, policy)
    monkeypatch.setattr(SourceWetStorage, 'invert', observed)
    rates = model.evaluate(initial)
    assert type(rates) is LiquidSourceColumnRates and calls == list(initial)
    assert len(rates.liquid_states) == 3
    for cell, liquid in zip(rates.cells, rates.liquid_states):
        p = cell.inverse.point
        assert liquid.pressure_error_pa == p.pressure_error_pa
        assert liquid.pressure_pa == p.fluid.mechanical.liquid_pressure_pa
        assert liquid.saturation == p.fluid.mechanical.liquid_volume_m3/p.available_pore_volume_m3
    assert not rates.full_inverse_liquid_direction_certified
    assert rates.liquid_pressure_interval_scope == 'fixed_decoded_temperature'


def test_nonzero_available_volume_error_reaches_liquid_direction_interval(monkeypatch):
    model, initial = setup(monkeypatch)
    storages = tuple(replace(s, volume=replace(s.volume, error_m3=1e-12)) for s in model.storages)
    model = replace(model, storages=storages)
    initial = tuple(s.state(old.liquid_water_mol, old.gas_amounts_mol, old.internal_energy_j)
                    for s, old in zip(storages, initial))
    rates = model.evaluate(initial)
    for cell, liquid in zip(rates.cells, rates.liquid_states):
        point = cell.inverse.point
        assert point.extra_pressure_error_pa > 0
        assert point.pressure_error_pa > point.fluid.pressure_error_bound_pa
        assert liquid.pressure_error_pa == point.pressure_error_pa
    for i, face in enumerate(rates.faces[1:-1]):
        assert face.liquid_exchange.pressure_difference_error_pa == (
            rates.liquid_states[i].pressure_error_pa+rates.liquid_states[i+1].pressure_error_pa)


def test_original_programmed_complete_result_is_unchanged(monkeypatch):
    from sludge_sandbox.deforming_solid_storage import _digest
    model, initial = furnace_setup(monkeypatch)
    run = integrate_source_column(model, initial, duration_s=1/128, steps=1)
    assert run.status == 'completed', run.reason
    # Captured before this extension; only nondeterministic elapsed time removed.
    assert _digest(replace(run, elapsed_seconds=0.)) == '1599f15367c7a4f699476ba23d708c327e4d14398314a38873c857790006e168'


def test_independent_darcy_donor_enthalpy_and_physical_energy_decomposition(monkeypatch):
    model, initial = setup(monkeypatch)
    rates = model.evaluate(initial)
    for i, face in enumerate(rates.faces[1:-1]):
        left, right = rates.liquid_states[i:i+2]
        dl, dr = map(F, model.faces[i].half_widths_m)
        mobility = F(1e-15)*F(.5)/F(.001)
        volume_flow = F(model.face_area_m2)*(F(left.pressure_pa)-F(right.pressure_pa))/(dl/mobility+dr/mobility)
        donor = left if volume_flow > 0 else right
        flow = volume_flow/F(donor.molar_volume_m3_mol)
        power = flow*F(donor.enthalpy_j_mol)
        assert face.liquid_mol_s == float(flow)
        assert face.liquid_enthalpy_w == float(power)
        assert face.liquid_exchange.donor == ('left' if volume_flow > 0 else 'right')
        assert face.liquid_enthalpy_projection_w == F(float(power))-F(float(flow))*F(donor.enthalpy_j_mol)
        assert face.energy_w == math.fsum((face.conduction_w, *face.diffusive_enthalpy_w,
                                         *face.advective_enthalpy_w, face.liquid_enthalpy_w))
        assert face.liquid_mol_s != 0


def test_closed_N3_liquid_phase_and_energy_ledger(monkeypatch):
    model, initial = setup(monkeypatch)
    run = integrate_source_column(model, initial, duration_s=1/128, steps=2)
    assert run.status == 'completed', run.reason
    for old, new, ledger in zip(run.states, run.states[1:], run.ledgers):
        liquid = lambda f: f.liquid_mol if hasattr(f, 'liquid_mol') else F()
        for i in range(3):
            assert F(new[i].liquid_water_mol)-F(old[i].liquid_water_mol) == (
                liquid(ledger.faces[i])-liquid(ledger.faces[i+1])-ledger.phase_water_mol[i]+ledger.roundoff.liquid_mol[i])
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == (
                ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i])
        for f in ledger.faces[1:-1]:
            assert f.energy_decomposition_roundoff_j == (f.energy_j-f.conduction_j-sum(f.diffusive_enthalpy_j)
                -sum(f.advective_enthalpy_j)-f.liquid_enthalpy_j)
            assert abs(f.liquid_enthalpy_j) > 1000*abs(f.energy_decomposition_roundoff_j)
        water = lambda states: sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in states)
        assert water(new)-water(old) == sum(ledger.roundoff.liquid_mol)+sum(row[2] for row in ledger.roundoff.gas_mol)
        assert sum(F(s.internal_energy_j) for s in new)-sum(F(s.internal_energy_j) for s in old) == sum(ledger.roundoff.energy_j)


@pytest.mark.parametrize('status', ['disabled', 'unknown', 'disconnected'])
def test_connection_status_is_not_an_invented_zero(monkeypatch, status):
    model, initial = setup(monkeypatch, status=status)
    run = integrate_source_column(model, initial, duration_s=1/128, steps=1)
    if status == 'disabled':
        assert run.status == 'completed', run.reason
        base_run = integrate_source_column(replace(model, liquid_transport=None), initial, duration_s=1/128, steps=1)
        assert run.states == base_run.states
        assert all(f.liquid_exchange.status == 'disabled' for f in run.observations[0].faces[1:-1])
    else:
        assert run.status == 'domain_exit' and not run.ledgers and run.states == (initial,)


def test_open_furnace_preserves_interior_liquid_and_closed_liquid_boundaries(monkeypatch):
    model, initial = furnace_setup(monkeypatch, count=3)
    model = replace(model, base=replace(model.base, liquid_transport=config(3)))
    out = model.evaluate(initial, ExactEventTime(F()))
    assert len(out.liquid_states) == 3 and out.faces[1].liquid_mol_s != 0
    assert not hasattr(out.faces[0], 'liquid_mol_s') and not hasattr(out.faces[-1], 'liquid_mol_s')
    run = integrate_source_column(model, initial, duration_s=1/128, steps=1)
    assert run.status == 'completed', run.reason
    ledger = run.ledgers[0]
    assert ledger.faces[1].liquid_mol != 0 and ledger.boundary_integral.conductive_into_cell_j == -ledger.faces[-1].conduction_j
    water = lambda states: sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in states)
    assert water(run.states[-1])-water(initial) == (-ledger.faces[-1].gas_mol[2]
        +sum(ledger.roundoff.liquid_mol)+sum(row[2] for row in ledger.roundoff.gas_mol))


def test_bad_config_and_mutation_refused_before_inverse(monkeypatch):
    model, initial = setup(monkeypatch)
    with pytest.raises(ValueError): replace(model, liquid_transport=config(2))
    foreign = replace(model.liquid_transport.relations[0], classification='literature_constitutive_model',
                      relation_kind='tabulated_saturation_relation')
    with pytest.raises(ValueError): replace(model, liquid_transport=replace(model.liquid_transport, relations=(foreign,)*3))
    object.__setattr__(model.liquid_transport.relations[0], 'permeability_m2', (2e-15, 2e-15))
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    monkeypatch.setattr(SourceWetStorage, 'invert', lambda *a, **k: pytest.fail('mutated transport reached inverse'))
    with pytest.raises(ValueError, match='content_changed'): model.evaluate(initial)
