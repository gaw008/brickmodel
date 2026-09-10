"""Open-boundary aggregation with explicit artificial liquid and coefficients."""
from dataclasses import replace
from fractions import Fraction as F
import math

import pytest

from test_source_wet_column import setup as base_setup
from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.exact_boundary_program import ExactProgramView
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.source_wet_column import SourceWetColumn, integrate_source_column
from sludge_sandbox.programmed_source_wet_column import ProgrammedSourceWetColumn


def setup(monkeypatch, *, count=1, pressure=1e5, thermal_only=False, knots=(0., .25), translation=F()):
    base, initial = base_setup(monkeypatch, count)
    if thermal_only:
        base = replace(base, transfer_coefficients_mol_s_pa=(0.,)*count)
    program = BoundaryProgram(identity=ProgramIdentity(program_id='test-furnace', version='1',
        classification='virtual_design_choice', source_ids=('design:source-column-furnace',)),
        knot_times_s=knots, gas_temperature_k=(340.,)*len(knots),
        radiation_temperature_k=(340.,)*len(knots), total_pressure_pa=(pressure,)*len(knots),
        species_order=base.gas_ids, mole_fractions=((.25, .6875, .0625),)*len(knots))
    model = ProgrammedSourceWetColumn(base, ExactProgramView(program, translation),
        outer_conductivity_w_m_k=.5, convection_w_m2_k=10., emissivity=0.,
        stefan_boltzmann_w_m2_k4=5.670374419e-8,
        gas_diffusivities_m2_s=(0.,)*3 if thermal_only else (1e-5, 2e-5, 1.5e-5),
        gas_permeability_m2=0. if thermal_only else 1e-13, gas_viscosity_pa_s=1.8e-5,
        coefficient_source_ids=('manufactured:source-column-furnace-coefficients',),
        surface_policy=SurfacePolicy(absolute_residual_w=1e-10, relative_residual=1e-12, maximum_iterations=100))
    return model, initial


def test_series_robin_and_single_heat_path(monkeypatch):
    model, initial = setup(monkeypatch, thermal_only=True)
    out = model.evaluate(initial, ExactEventTime(F()))
    t = out.cells[-1].inverse.point.temperature_k
    expected = .01*(340.-t)/(.25/(2*.5)+1/10.)
    assert out.surface.conductive_into_cell_w == pytest.approx(expected, abs=1e-10, rel=0)
    assert out.faces[-1].energy_w == -out.surface.conductive_into_cell_w
    assert out.faces[-1].shared_evaluation.conduction_w == 0
    assert out.faces[-1].gas_mol_s == (0.,)*3
    assert out.faces[0].energy_w == 0 and out.faces[-1].face_id == 1
    assert abs(out.surface.balance_residual_w) <= out.surface.balance_limit_w
    assert out.boundary.time == ExactEventTime(F()) and not out.material_qualified
    assert 'design:source-column-furnace' in out.source_ids


@pytest.mark.parametrize(('pressure', 'donor'), [(1e5, 'left'), (2e6, 'right')])
def test_inflow_outflow_enthalpy_and_single_base_evaluation(monkeypatch, pressure, donor):
    model, initial = setup(monkeypatch, count=3, pressure=pressure)
    original = SourceWetColumn.evaluate
    calls = []
    def observed(self, states):
        calls.append(self.model_identity)
        return original(self, states)
    monkeypatch.setattr(SourceWetColumn, 'evaluate', observed)
    out = model.evaluate(initial, ExactEventTime(F(1, 128)))
    assert calls == [model.base.model_identity]
    face = out.faces[-1]
    exchange = face.shared_evaluation.exchange
    assert exchange.advective_donor == donor
    assert exchange.advective_donor_temperature_k == (
        out.gas_states[-1].temperature_k if donor == 'left' else out.reservoir.temperature_k)
    phases = model.storages[0].fluid_template.gas_phases
    expected_diff = tuple(exchange.diffusive_mol_s[k]*phases[k]._curve.enthalpy_j_mol(exchange.face_temperature_k) for k in model.gas_ids)
    expected_adv = tuple(exchange.advective_mol_s[k]*phases[k]._curve.enthalpy_j_mol(exchange.advective_donor_temperature_k) for k in model.gas_ids)
    assert face.diffusive_enthalpy_w == expected_diff and face.advective_enthalpy_w == expected_adv
    assert face.energy_w == math.fsum((*expected_diff, *expected_adv, -out.surface.conductive_into_cell_w))
    assert (face.left_cell, face.right_cell) == (2, None)
    assert out.reservoir.reservoir_input_mole_fractions == out.boundary.mole_fractions


def test_exact_nodes_stage_times_and_global_open_ledger(monkeypatch):
    origin = F(10**18)
    model, initial = setup(monkeypatch, count=3, knots=(0., .005, .015625), translation=origin)
    program = replace(model.program.program, gas_temperature_k=(320., 340., 330.),
        radiation_temperature_k=(330., 350., 340.), total_pressure_pa=(2e6, 1e5, 1e6),
        mole_fractions=((.25, .6875, .0625), (.5, .484375, .015625), (.125, .75, .125)))
    model = replace(model, program=ExactProgramView(program, origin), emissivity=.75)
    times = []
    original = ProgrammedSourceWetColumn.evaluate
    def observed(self, states, time):
        times.append(time.seconds)
        return original(self, states, time)
    monkeypatch.setattr(ProgrammedSourceWetColumn, 'evaluate', observed)
    run = integrate_source_column(model, initial, duration_s=1/64, steps=1,
                                  start_time=ExactEventTime(origin), maximum_wall_seconds=35.)
    knot, end = origin+F(.005), origin+F(1, 64)
    assert run.status == 'completed', run.reason
    assert run.times_s == (origin, knot, end)
    assert times == [origin, (origin+knot)/2, knot, knot, (knot+end)/2, end]
    assert len(run.ledgers) == 2 and run.evaluations_completed == 6
    assert run.model_identity == model.model_identity
    for index, (old, new, ledger) in enumerate(zip(run.states, run.states[1:], run.ledgers)):
        boundary = ledger.boundary_integral
        assert boundary.boundary.gas_temperature_k == (program.gas_temperature_k[index]+program.gas_temperature_k[index+1])/2
        assert boundary.boundary.total_pressure_pa == (program.total_pressure_pa[index]+program.total_pressure_pa[index+1])/2
        for k, name in enumerate(model.gas_ids):
            assert boundary.boundary.mole_fractions[name] == (program.mole_fractions[index][k]+program.mole_fractions[index+1][k])/2
        assert boundary.conductive_into_cell_j == -ledger.faces[-1].conduction_j
        assert boundary.exact_surface_balance_defect_j == (
            boundary.conductive_into_cell_j-boundary.convective_in_j-boundary.radiative_in_j)
        assert abs(boundary.reported_surface_residual_j) <= boundary.surface_balance_limit_j
        for i in range(3):
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == (
                ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i])
        assert sum(F(s.internal_energy_j) for s in new)-sum(F(s.internal_energy_j) for s in old) == (
            ledger.faces[0].energy_j-ledger.faces[-1].energy_j+sum(ledger.roundoff.energy_j))
        for k in (0, 1):
            assert sum(F(s.gas_amounts_mol[k]) for s in new)-sum(F(s.gas_amounts_mol[k]) for s in old) == (
                ledger.faces[0].gas_mol[k]-ledger.faces[-1].gas_mol[k]+sum(row[k] for row in ledger.roundoff.gas_mol))
        water = lambda states: sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in states)
        assert water(new)-water(old) == (ledger.faces[0].gas_mol[2]-ledger.faces[-1].gas_mol[2]
            +sum(ledger.roundoff.liquid_mol)+sum(row[2] for row in ledger.roundoff.gas_mol))


def test_domain_mutation_and_bad_configuration_before_inverse(monkeypatch):
    model, initial = setup(monkeypatch)
    with pytest.raises(ValueError): replace(model, coefficient_classification='measured_public_data')
    with pytest.raises(ValueError): replace(model, gas_diffusivities_m2_s=(1.,))
    with pytest.raises(ValueError): replace(model, emissivity=1.1)
    with pytest.raises(ValueError): replace(model, base=object())
    invalid = replace(model.program.program, gas_temperature_k=(100000., 100000.))
    with pytest.raises(ValueError): replace(model, program=ExactProgramView(invalid))
    def forbidden(*args, **kwargs): pytest.fail('invalid configuration reached cell inverse')
    monkeypatch.setattr(SourceWetColumn, 'evaluate', forbidden)
    run = integrate_source_column(model, initial, duration_s=1., steps=1)
    assert run.status == 'domain_exit' and not run.ledgers and run.states == (initial,)
    object.__setattr__(model, 'convection_w_m2_k', 20.)
    with pytest.raises(ValueError, match='content_changed'): model.evaluate(initial, ExactEventTime(F()))


def test_cancel_after_one_complete_open_step(monkeypatch):
    model, initial = setup(monkeypatch, thermal_only=True)
    calls = 0
    def cancel():
        nonlocal calls
        calls += 1
        return calls == 4
    run = integrate_source_column(model, initial, duration_s=1/128, steps=2, cancel=cancel)
    assert run.status == 'cancelled' and len(run.ledgers) == 1 and len(run.states) == 2
    assert run.times_s[-1] == F(1, 256) and run.evaluations_completed == 3


def test_closed_default_whole_run_parity(monkeypatch):
    from sludge_sandbox.deforming_solid_storage import _digest
    base, initial = base_setup(monkeypatch, 1)
    run = integrate_source_column(base, initial, duration_s=1/128, steps=1)
    assert run.status == 'completed', run.reason
    # Recorded from the complete pre-extension result, with only elapsed time removed.
    assert _digest(replace(run, elapsed_seconds=0.)) == '5a1a39e5eec4148a2cadc9c1744050610be06d359ff78300e14911506eefc6b1'
