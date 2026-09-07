"""Boundary interpolation contracts; artificial values are explicit design inputs."""
from dataclasses import FrozenInstanceError
from fractions import Fraction
import math

import pytest

from sludge_sandbox.boundary_program import (
    BoundaryProgram, BoundaryProgramError, ProgramIdentity, ScalarProgram,
)


def identity(**changes):
    fields = dict(program_id='test-boundary', version='1',
                  classification='virtual_design_choice', source_ids=('design:test',))
    fields.update(changes)
    return ProgramIdentity(**fields)


def program(**changes):
    fields = dict(identity=identity(), knot_times_s=[0, 10, 20, 40],
                  gas_temperature_k=[300, 900, 900, 300],
                  radiation_temperature_k=[400, 1000, 1000, 400],
                  total_pressure_pa=[1e5, 2e5, 2e5, 1e5],
                  species_order=['O2', 'N2', 'H2O'],
                  mole_fractions=[[.2, .8, 0], [.1, .8, .1],
                                  [.1, .8, .1], [0, .8, .2]])
    fields.update(changes)
    return BoundaryProgram(**fields)


def test_heat_hold_cool_channels_and_exact_endpoints():
    p = program()
    assert p.knot_times_s == (0, 10, 20, 40)
    for t, expected in [(0, 300), (5, 600), (10, 900), (15, 900), (30, 600), (40, 300)]:
        state = p.at(t)
        assert state.gas_temperature_k == expected
        assert state.radiation_temperature_k == expected + 100
        assert state.time_s == t
        assert state.identity == p.identity
    assert p.at(5).total_pressure_pa == 150000
    assert dict(p.at(5).mole_fractions) == pytest.approx({'O2': .15, 'N2': .8, 'H2O': .05})
    assert p.at(0).mole_fractions['H2O'] == 0
    assert p.at(40).mole_fractions['O2'] == 0
    assert p.breakpoints_s(5, 30) == (10, 20)
    assert p.breakpoints_s(0, 40) == (10, 20)
    assert p.breakpoints_s(10, 20) == ()


def test_owned_immutable_inputs_and_output():
    times = [0, 1]
    fractions = [[0, 1], [1, 0]]
    p = program(knot_times_s=times, gas_temperature_k=[300, 400],
                radiation_temperature_k=[300, 400], total_pressure_pa=[1e5, 1e5],
                species_order=['O2', 'N2'], mole_fractions=fractions)
    times[1] = 5
    fractions[0][0] = .4
    assert p.knot_times_s == (0, 1)
    assert p.at(0).mole_fractions['O2'] == 0
    with pytest.raises(FrozenInstanceError):
        p.identity.version = '2'
    with pytest.raises(FrozenInstanceError):
        p.knot_times_s = (0, 4)
    with pytest.raises(TypeError):
        p.at(.5).mole_fractions['O2'] = .9


@pytest.mark.parametrize('times', [[0], [0, 0], [1, 0], [0, math.inf], [0, math.nan], [False, 1]])
def test_invalid_knots(times):
    with pytest.raises(BoundaryProgramError):
        ScalarProgram(identity=identity(), knot_times_s=times, values=[1] * len(times), unit='K')


@pytest.mark.parametrize('t', [-1, 41, math.inf, math.nan, True, '5'])
def test_no_extrapolation_or_invalid_time(t):
    with pytest.raises(BoundaryProgramError):
        program().at(t)


@pytest.mark.parametrize('field,value', [
    ('gas_temperature_k', [0, 1, 1, 1]),
    ('radiation_temperature_k', [-1, 1, 1, 1]),
    ('total_pressure_pa', [1, 1, math.inf, 1]),
    ('gas_temperature_k', [300, 400]),
    ('species_order', ['N2', 'N2', 'H2O']),
    ('species_order', [' O2', 'N2', 'H2O']),
    ('mole_fractions', [[.2, .7, 0]] * 4),
    ('mole_fractions', [[.2, .9, -.1]] * 4),
    ('mole_fractions', [[.2, .8]] * 4),
    ('mole_fractions', [[math.nan, .8, .2]] * 4),
])
def test_invalid_boundary(field, value):
    with pytest.raises(BoundaryProgramError):
        program(**{field: value})


def test_near_unity_input_retained_not_normalized():
    row = [.2, .8, 2**-52]
    p = program(mole_fractions=[row] * 4)
    assert tuple(p.at(0).mole_fractions.values()) == tuple(row)
    with pytest.raises(BoundaryProgramError):
        program(mole_fractions=[[.2, .8, 1e-10]] * 4)


def test_extreme_float_time_and_values_exact_reference():
    s = ScalarProgram(identity=identity(), knot_times_s=(-1e308, 1e308),
                      values=(-1e308, 1e308), unit='Pa')
    assert s.at(0) == 0
    assert s.at(5e307) == 5e307
    start = 1e16
    end = math.nextafter(math.nextafter(start, math.inf), math.inf)
    mid = math.nextafter(start, math.inf)
    s = ScalarProgram(identity=identity(), knot_times_s=(start, end),
                      values=(1e-300, 1e308), unit='K')
    weight = (Fraction(mid) - Fraction(start)) / (Fraction(end) - Fraction(start))
    expected = float((1 - weight) * Fraction(1e-300) + weight * Fraction(1e308))
    assert s.at(mid) == expected
    assert s.at(end) == 1e308


@pytest.mark.parametrize('changes', [dict(classification='unknown'), dict(source_ids=()),
                                    dict(source_ids=('x', 'x')), dict(version=''),
                                    dict(program_id=''), dict(source_ids=(' ',))])
def test_identity_required(changes):
    with pytest.raises(BoundaryProgramError):
        identity(**changes)


def test_scalar_unit_and_signed_values():
    s = ScalarProgram(identity=identity(), knot_times_s=(0, 1), values=(-2, 2), unit='W')
    assert s.at(.5) == 0
    with pytest.raises(BoundaryProgramError):
        ScalarProgram(identity=identity(), knot_times_s=(0, 1), values=(1, 2), unit='Celsius')
    with pytest.raises(BoundaryProgramError):
        program().breakpoints_s(20, 10)


def test_boundary_extreme_positive_values_and_adjacent_time_knots():
    tiny = math.ulp(0.0)
    p = program(knot_times_s=[0, tiny], gas_temperature_k=[tiny, 1e308],
                radiation_temperature_k=[1e308, tiny], total_pressure_pa=[tiny, 1e308],
                species_order=['inert'], mole_fractions=[[1], [1]])
    assert p.at(0).gas_temperature_k == tiny
    assert p.at(tiny).radiation_temperature_k == tiny
    assert p.breakpoints_s(0, tiny) == ()
    p = program(knot_times_s=[-1e308, 1e308], gas_temperature_k=[tiny, 1e308],
                radiation_temperature_k=[tiny, 1e308], total_pressure_pa=[tiny, 1e308],
                species_order=['inert'], mole_fractions=[[1], [1]])
    assert p.at(0).gas_temperature_k == 5e307


@pytest.mark.parametrize('values', [[1, math.inf], [1, True], '12', {0: 1, 1: 2}, None])
def test_scalar_rejects_invalid_values(values):
    with pytest.raises(BoundaryProgramError):
        ScalarProgram(identity=identity(), knot_times_s=(0, 1), values=values, unit='K')


def test_evidence_labels_preserved_without_claiming_source_resolution():
    for classification in ('measured_public_data', 'derived_from_evidence'):
        p = program(identity=identity(classification=classification))
        assert p.at(5).identity.classification == classification
        assert p.provenance_status == 'input_identity_only_not_material_admission'


def test_actual_integrator_lands_on_program_knots_and_matches_analytic_energy():
    # Manufactured external power Q = (1 W/K)*(T_design - 300 K), independent
    # of cell temperature. This tests forcing plumbing, not convective physics.
    from sludge_sandbox.integration import ConservedState, IntegrationPolicy, Rates, integrate

    p = program()
    seen = []

    def operator(state, t):
        seen.append(t)
        power = p.at(t).gas_temperature_k - 300
        return Rates([[0], [0]], [0, 0], [[0]], [power])

    policy = IntegrationPolicy(
        initial_step_s=7, maximum_step_s=7, minimum_step_s=1e-10,
        relative_tolerance=1e-9, amount_absolute_tolerance_mol=1e-12,
        energy_absolute_tolerance_j=1e-8, amount_scale_mol=1, energy_scale_j=15000,
        maximum_steps=100, maximum_rejections=100, maximum_wall_seconds=20,
    )
    result = integrate(ConservedState([[1]], [100]), operator, start_s=0, end_s=40,
                       policy=policy, breakpoints_s=p.breakpoints_s(0, 40))
    assert result.status == 'completed'
    assert result.rejected_trials == 0
    assert all(knot in result.times_s for knot in p.knot_times_s)
    assert all(knot in seen for knot in p.knot_times_s)

    def accumulated(t):
        if t <= 10:
            return 30 * t**2
        if t <= 20:
            return 3000 + 600 * (t-10)
        elapsed = t-20
        return 9000 + 600 * elapsed - 15 * elapsed**2

    for t, state in zip(result.times_s, result.states):
        assert state.internal_energy_j[0] == pytest.approx(100+accumulated(t), abs=1e-8, rel=0)
        assert state.amounts_mol[0, 0] == 1
    for step in result.steps:
        assert step.cell_work_j[0] == pytest.approx(
            accumulated(step.end_s)-accumulated(step.start_s), abs=1e-8, rel=0)
    assert math.fsum(step.cell_work_j[0] for step in result.steps) == pytest.approx(15000, abs=1e-8, rel=0)
