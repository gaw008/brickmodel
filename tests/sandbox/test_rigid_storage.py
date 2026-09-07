"""Conditional numerical contracts are fixtures, not material or EOS certificates."""
from dataclasses import replace
from pathlib import Path
import math

import pytest
from scipy.optimize import brentq

from sludge_sandbox.phase_storage import IdealGasPhase, InversePolicy, PhaseStorageError
from sludge_sandbox.rigid_water_gas import RigidWaterGas, PressurePolicy
from sludge_sandbox.rigid_storage import RigidStorage, RigidStorageError, DeclaredNumericalEnvelope
from sludge_sandbox.thermochemistry import ShomateGas, ShomateSegment
from sludge_sandbox.water_properties import load_water_properties

pytest.importorskip('iapws')
DATA = Path(__file__).resolve().parents[2] / 'data/sandbox/water'
R = 8.31446261815324


@pytest.fixture
def water():
    return load_water_properties(DATA)


def model(water, **changes):
    curve = ShomateGas('fixture', (ShomateSegment((100., 2000.),
        (30., 0., 0., 0., 0., 0., 0., 0.), 0., R, ('manufactured-cp30',)),),
        'manufactured_test_fixture', ('manufactured-cp30',))
    phase = IdealGasPhase(curve, .028, 0, ('nist-codata-2022',))
    mechanical = RigidWaterGas(water, ('fixture',), 1e-4, (1e4, 1e6),
        'planar_interface_no_capillary_pressure', PressurePolicy(1e-13, 1e-5, 150))
    envelope = DeclaredNumericalEnvelope((295., 310.), (1e4, 1e6),
        1e-8, 1e-16, 1e-4, {'fixture': 1e-9}, {'fixture': 20.},
        'explicit_manufactured_numerical_verification_envelope_not_eos_certificate',
        ('manufactured-error-envelope',))
    return RigidStorage(**({'mechanical': mechanical, 'gas_phases': {'fixture': phase},
                           'envelope': envelope, 'allow_manufactured': True} | changes))


def independent(water, t, nl=2., ng=.01):
    mass = water.reference.molar_mass_kg_mol
    p = brentq(lambda p: nl * mass / water.state_tp(t, p, phase='liquid').density_kg_m3
               + ng * R * t / p - 1e-4, 1e4, 1e6, xtol=1e-7)
    w = water.state_tp(t, p, phase='liquid')
    return p, nl * w.internal_energy_j_mol + ng * (30. - R) * t


def test_actual_closed_path_inverse_independent_pressure_and_energy(water):
    m = model(water)
    reference_p, target = independent(water, 300.)
    out = m.temperature_from_energy(target, 2., {'fixture': .01}, (295., 310.),
                                    InversePolicy(1e-5, 1e-4, 100))
    assert out.state.mechanical.temperature_k == pytest.approx(300., rel=0, abs=1e-4)
    assert out.state.mechanical.pressure_pa == pytest.approx(reference_p, rel=0, abs=.2)
    assert abs(out.energy_residual_j) <= 1e-5
    assert out.temperature_error_bound_k <= 1e-4
    assert out.final_temperature_bracket_k[0] <= 300. <= out.final_temperature_bracket_k[1]
    assert out.state.mechanical.liquid_inventory_mol == 2.
    assert out.state.mechanical.gas_inventory_mol == {'fixture': .01}
    assert 'conditional' in out.state.qualification
    assert out.state.envelope is m.envelope


def test_heat_capacity_matches_independent_closed_pressure_derivative(water):
    m = model(water)
    point = m.evaluate_at_temperature(300., 2., {'fixture': .01})
    _, plus = independent(water, 300.01)
    _, minus = independent(water, 299.99)
    assert point.closed_heat_capacity_j_k == pytest.approx((plus-minus)/.02, rel=0, abs=1e-4)
    assert point.enthalpy_j - point.internal_energy_j == pytest.approx(
        point.mechanical.pressure_pa * 1e-4, rel=0, abs=1e-8)
    assert point.closed_heat_capacity_j_k > point.minimum_heat_capacity_j_k


def test_pressure_feedback_differs_from_fixed_pressure_storage(water):
    m = model(water)
    a = m.evaluate_at_temperature(300., 2., {'fixture': .01})
    b = m.evaluate_at_temperature(310., 2., {'fixture': .01})
    assert b.mechanical.pressure_pa > a.mechanical.pressure_pa
    fixed = 2 * water.state_tp(310., a.mechanical.pressure_pa, phase='liquid').internal_energy_j_mol + .01*(30-R)*310
    assert abs(b.internal_energy_j-fixed) > .01


def test_large_declared_error_rejects_precision_instead_of_rounding_success(water):
    m = model(water)
    m = replace(m, envelope=replace(m.envelope, liquid_u_error_j_mol=1.))
    _, target = independent(water, 300.)
    with pytest.raises(RigidStorageError, match='exceeds_inverse'):
        m.temperature_from_energy(target, 2., {'fixture': .01}, (295., 310.), InversePolicy(1e-5, 1e-4, 100))


def test_false_pressure_sensitivity_declaration_detected_at_real_state(water):
    m = model(water)
    m = replace(m, envelope=replace(m.envelope, liquid_abs_du_dp_bound_j_mol_pa=0.))
    with pytest.raises(RigidStorageError, match='pressure_bound_violation'):
        m.evaluate_at_temperature(300., 2., {'fixture': .01})


def test_false_cv_bound_detected(water):
    m = model(water)
    m = replace(m, envelope=replace(m.envelope, gas_cv_lower_j_mol_k={'fixture': 25.}))
    with pytest.raises(RigidStorageError, match='cv_bound_violation'):
        m.evaluate_at_temperature(300., 2., {'fixture': .01})


def test_pure_gas_high_temperature_skips_all_liquid_properties(water, monkeypatch):
    m = model(water)
    m = replace(m, envelope=replace(m.envelope, temperature_range_k=(500., 1200.),
                liquid_u_error_j_mol=1e100, liquid_v_error_m3_mol=1e100,
                liquid_abs_du_dp_bound_j_mol_pa=1e100))
    def fail(*args, **kwargs):
        pytest.fail('zero liquid branch called water')
    monkeypatch.setattr(type(water), 'state_tp', fail)
    monkeypatch.setattr(type(water), 'state_tp_response', fail)
    target = .01*(30-R)*800.
    out = m.temperature_from_energy(target, 0., {'fixture': .01}, (600., 1000.),
                                   InversePolicy(1e-7, 1e-6, 100))
    assert out.state.mechanical.temperature_k == pytest.approx(800., rel=0, abs=1e-6)
    assert out.state.closed_heat_capacity_j_k == pytest.approx(.01*(30-R), rel=0, abs=1e-12)
    assert out.state.energy_error_bound_j < 1e-7


def test_manufactured_opt_in_identity_and_complete_gas_contract(water):
    m = model(water)
    with pytest.raises(RigidStorageError, match='opt_in'):
        replace(m, allow_manufactured=False)
    with pytest.raises(RigidStorageError, match='matching_gas'):
        replace(m, envelope=replace(m.envelope, gas_u_error_j_mol={'missing': 0.}))
    with pytest.raises(TypeError):
        m.gas_phases['new'] = next(iter(m.gas_phases.values()))
    with pytest.raises(TypeError):
        m.envelope.gas_cv_lower_j_mol_k['fixture'] = 0.


@pytest.mark.parametrize('bad', [True, math.nan, math.inf, -1.])
def test_invalid_temperature_rejected(water, bad):
    with pytest.raises(RigidStorageError):
        model(water).evaluate_at_temperature(bad, 2., {'fixture': .01})


def test_error_domain_and_target_bracket_fail_explicitly(water):
    m = model(water)
    with pytest.raises(RigidStorageError, match='outside_error_envelope'):
        m.evaluate_at_temperature(320., 2., {'fixture': .01})
    with pytest.raises(RigidStorageError, match='outside_closed'):
        m.temperature_from_energy(1e10, 2., {'fixture': .01}, (295., 310.), InversePolicy(1e-5, 1e-4, 100))
    target = m.evaluate_at_temperature(295., 2., {'fixture': .01}).internal_energy_j
    with pytest.raises(RigidStorageError, match='sign_uncertain'):
        m.temperature_from_energy(target, 2., {'fixture': .01}, (295., 310.), InversePolicy(1e-5, 1e-4, 100))


def test_h2o_cross_phase_molar_identity_cannot_be_changed(water):
    m = model(water)
    old = m.gas_phases['fixture']
    wrong = replace(old, caloric=replace(old.caloric, species_id='H2O'), molar_mass_kg_mol=.1)
    mechanical = replace(m.mechanical, gas_species_ids=('H2O',))
    envelope = replace(m.envelope, gas_u_error_j_mol={'H2O': 1e-9}, gas_cv_lower_j_mol_k={'H2O': 20.})
    with pytest.raises(RigidStorageError, match='molar_identity'):
        RigidStorage(mechanical, {'H2O': wrong}, envelope, True)


def test_large_absolute_reference_refuses_unresolvable_inverse(water):
    m = model(water)
    old = m.gas_phases['fixture']
    curve = ShomateGas('fixture', (ShomateSegment((100., 2000.),
        (30., 0., 0., 0., 0., 1e15, 0., 1e15), 1e18, R, ('large-reference-fixture',)),),
        'manufactured_test_fixture', ('large-reference-fixture',))
    m = replace(m, gas_phases={'fixture': replace(old, caloric=curve)})
    # The existing phase H-U-PV identity guard rejects this input even earlier
    # than the new inverse budget; preserve that upstream diagnostic.
    with pytest.raises(PhaseStorageError, match='phase_h_u_pv_identity'):
        m.temperature_from_energy(1e16, 2., {'fixture': .01}, (295., 310.), InversePolicy(1e-5, 1e-4, 100))


def test_coarse_pressure_policy_propagates_to_inverse_refusal(water):
    m = model(water)
    m = replace(m, mechanical=replace(m.mechanical, policy=PressurePolicy(1e-8, 1e4, 150)))
    _, target = independent(water, 300.)
    with pytest.raises(RigidStorageError, match='exceeds_inverse'):
        m.temperature_from_energy(target, 2., {'fixture': .01}, (295., 310.), InversePolicy(1e-5, 1e-4, 100))


def test_reported_temperature_interval_rounds_outward(water):
    from fractions import Fraction
    m = model(water)
    m = replace(m, envelope=replace(m.envelope, temperature_range_k=(500., 1200.)))
    out = m.temperature_from_energy(.01*(30-R)*800.123456, 0., {'fixture': .01},
                                    (600., 1000.), InversePolicy(1e-7, 1e-6, 100))
    center = Fraction(out.state.mechanical.temperature_k)
    radius = Fraction(out.temperature_error_bound_k)
    assert Fraction(out.final_temperature_bracket_k[0]) <= center-radius
    assert Fraction(out.final_temperature_bracket_k[1]) >= center+radius


def test_real_integrator_uses_closed_water_gas_decode_for_every_thermal_trial(water):
    import numpy as np
    from sludge_sandbox.integration import ConservedState, IntegrationPolicy, Rates, integrate
    m = model(water)
    initial = m.evaluate_at_temperature(300., 2., {'fixture': .01})
    decoded = []
    def heat(state, time):
        point = m.temperature_from_energy(state.internal_energy_j[0], state.amounts_mol[0, 0],
            {'fixture': state.amounts_mol[0, 1]}, (295., 310.), InversePolicy(1e-5, 1e-4, 100)).state
        decoded.append(point)
        # Declared manufactured electrical feedback: 10 W/K*(310K-T).
        power = 10. * (310. - point.mechanical.temperature_k)
        return Rates([[0., 0.], [0., 0.]], [0., 0.], [[0., 0.]], [power])
    state = ConservedState([[2., .01]], [initial.internal_energy_j])
    result = integrate(state, heat, start_s=0., end_s=.1,
        policy=IntegrationPolicy(initial_step_s=.1, maximum_step_s=.1, minimum_step_s=1e-8,
            relative_tolerance=1e-9, amount_absolute_tolerance_mol=1e-12,
            energy_absolute_tolerance_j=1e-3, amount_scale_mol=1., energy_scale_j=100.,
            maximum_steps=10, maximum_rejections=10, maximum_wall_seconds=90.))
    assert result.status == 'completed'
    assert len(decoded) == result.evaluations
    assert len(decoded) > 1
    final = result.states[-1]
    total_work = math.fsum(step.cell_work_j[0] for step in result.steps)
    assert final.internal_energy_j[0] - initial.internal_energy_j == pytest.approx(total_work, rel=0, abs=1e-8)
    assert all(np.array_equal(s.amounts_mol, state.amounts_mol) for s in result.states)
    assert max(s.mechanical.pressure_pa for s in decoded) > initial.mechanical.pressure_pa
    actual = m.temperature_from_energy(final.internal_energy_j[0], 2., {'fixture': .01},
                                       (295., 310.), InversePolicy(1e-5, 1e-4, 100)).state
    reference = brentq(lambda t: independent(water, t)[1] - final.internal_energy_j[0],
                       300., 301., xtol=1e-8)
    assert actual.mechanical.temperature_k == pytest.approx(reference, rel=0, abs=1e-4)
