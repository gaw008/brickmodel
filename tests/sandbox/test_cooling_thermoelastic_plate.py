"""Short manufactured checks of the declared half-plate thermoelastic operator."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import math

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from sludge_sandbox.cooling_thermoelastic_plate import (
    CoolingThermoelasticPlate, ThermoelasticPlateError,
)
from sludge_sandbox.geometry import ReferenceSlab


def plate(**changes):
    values = dict(
        reference=ReferenceSlab(.02, .01, 2),
        biaxial_modulus_pa=1e9,
        linear_expansion_per_k=1e-4,
        stress_free_heat_capacity_j_m3_k=1e5,
        reference_temperature_k=300.,
        conductivity_w_m_k=1.,
        temperature_bounds_k=(290., 310.),
        strain_bounds=(-.01, .01),
        outer_temperature_k=295.,
        outer_boundary="adiabatic",
        coefficient_classification="manufactured",
        mechanical_regime="symmetric_free_plane_stress",
    )
    values.update(changes)
    return CoolingThermoelasticPlate(**values)


@pytest.mark.parametrize("temperature", [291., 300., 309.])
def test_uniform_free_state_and_uniform_in_plane_restrained_point(temperature):
    op = plate(reference=ReferenceSlab(.02, .01, 3))
    result = op.evaluate([temperature] * 3)
    assert all(p.stress_pa == 0. for p in result.points)
    assert result.in_plane_strain == op.linear_expansion_per_k * (temperature - 300.)
    assert result.temperature_rates_k_s == (0.,) * 3
    assert all(p.internal_energy_j_m3 == 1e5 * (temperature - 300.) for p in result.points)
    constrained = op.constitutive_point(temperature, 0.)
    assert constrained.stress_pa == pytest.approx(-1e5 * (temperature - 300.), abs=1e-8)


def test_independent_free_energy_derivatives_and_legendre_identity():
    op = plate()
    temperature, strain = 304., .0007
    p = op.constitutive_point(temperature, strain)
    dt, de = .001, 1e-7
    def psi(t, e):
        return 1e5 * ((t - 300.) - t * math.log(t / 300.)) + 1e9 * (e - 1e-4 * (t - 300.))**2
    assert p.entropy_j_m3_k == pytest.approx(-(psi(temperature + dt, strain) - psi(temperature - dt, strain)) / (2 * dt), rel=1e-8)
    assert 2 * p.stress_pa == pytest.approx((psi(temperature, strain + de) - psi(temperature, strain - de)) / (2 * de), rel=1e-8)
    assert p.internal_energy_j_m3 == pytest.approx(p.helmholtz_j_m3 + temperature * p.entropy_j_m3_k, rel=1e-13)
    assert p.internal_energy_j_m3 == pytest.approx(1e5 * 4 + 1e9 * (strain + .03)**2 - 10 * temperature**2, rel=1e-13)
    high = op.constitutive_point(temperature + dt, strain)
    low = op.constitutive_point(temperature - dt, strain)
    assert (high.internal_energy_j_m3 - low.internal_energy_j_m3) / (2 * dt) == pytest.approx(p.fixed_strain_heat_capacity_j_m3_k, rel=1e-9)


def test_fraction_two_cell_rates_local_work_and_entropy():
    op = plate()
    out = op.evaluate([304., 300.])
    F = Fraction
    c, b, volume = F(100000), F(10), F(1, 10000)
    t = [F(304), F(300)]
    q = [-F(4) / volume, F(4) / volume]
    ce = [c - 2 * b * v for v in t]
    mean_rate = sum((qq / dd for qq, dd in zip(q, ce)), F()) / (2 + sum((2 * b * tt / dd for tt, dd in zip(t, ce)), F()))
    td = [(qq - 2 * b * tt * mean_rate) / dd for tt, qq, dd in zip(t, q, ce)]
    np.testing.assert_allclose(out.temperature_rates_k_s, [float(x) for x in td], rtol=1e-14)
    assert out.face_heat_outward_w == (0., 4., 0.)
    assert out.cell_heat_in_w == (-4., 4.)
    assert out.points[0].stress_pa < 0. < out.points[1].stress_pa
    expected_power = [2 * volume * sigma * F(1, 10000) * mean_rate
                      for sigma in (-F(200000), F(200000))]
    assert expected_power[0] != 0
    np.testing.assert_allclose(out.cell_mechanical_power_w,
                               [float(x) for x in expected_power], rtol=1e-13)
    assert out.total_mechanical_power_w == pytest.approx(0., abs=1e-12)
    for i in range(2):
        assert out.reference_cell_volumes_m3[i] * out.cell_u_rates_j_m3_s[i] == pytest.approx(out.cell_heat_in_w[i] + out.cell_mechanical_power_w[i], abs=1e-12)
        assert float(t[i]) * out.cell_s_rates_j_m3_k_s[i] == pytest.approx(float(q[i]), abs=1e-9)
    assert out.total_entropy_production_w_k == pytest.approx(float(F(4) * (F(1, 300) - F(1, 304))), rel=1e-14)
    assert out.total_entropy_rate_w_k == pytest.approx(out.total_entropy_production_w_k, abs=1e-15)
    assert out.total_internal_energy_rate_w == pytest.approx(0., abs=1e-12)
    mean = 302.
    variance_energy = 1e5 * sum(v * (tt - 300.) for v, tt in zip(out.reference_cell_volumes_m3, t)) - 10 * sum(v * (float(tt) - mean)**2 for v, tt in zip(out.reference_cell_volumes_m3, t))
    assert out.total_internal_energy_j == pytest.approx(variance_energy, abs=1e-12)


def test_two_cell_adiabatic_relaxation_matches_independent_implicit_solution():
    op = plate()
    times = np.linspace(0., 2., 9)
    run = solve_ivp(lambda t, y: op.evaluate(y).temperature_rates_k_s,
                    (0., 2.), [304., 300.], rtol=1e-11, atol=1e-12,
                    t_eval=times, max_step=.05)
    assert run.success, run.message
    c, b, mean0, delta0, conductance, volume = 1e5, 10., 302., 2., 1., 1e-4
    k0 = c - 2 * b * mean0 + 2 * b**2 * delta0**2 / c
    expected = []
    for time in times:
        delta = delta0 if time == 0 else brentq(
            lambda dd: k0 * math.log(dd / delta0) - b**2 / c * (dd**2 - delta0**2) + 2 * conductance * time / volume,
            delta0 * 1e-3, delta0, xtol=1e-13, rtol=1e-14,
        )
        mean = mean0 + b / c * (delta**2 - delta0**2)
        expected.append([mean + delta, mean - delta])
    np.testing.assert_allclose(run.y.T, expected, rtol=0., atol=2e-9)
    initial_u = op.evaluate([304., 300.]).total_internal_energy_j
    for temperatures in run.y.T:
        assert op.evaluate(temperatures).total_internal_energy_j == pytest.approx(initial_u, abs=1e-9)


def test_fixed_surface_halfcell_and_zero_alpha_reduce_to_plain_conduction():
    op = plate(linear_expansion_per_k=0., outer_boundary="fixed_temperature")
    out = op.evaluate([304., 300.])
    assert out.face_heat_outward_w == (0., 4., 10.)
    assert out.cell_heat_in_w == (-4., -6.)
    np.testing.assert_allclose(out.temperature_rates_k_s, [-.4, -.6], atol=1e-15)
    assert out.in_plane_strain_rate_per_s == 0.
    assert out.cell_mechanical_power_w == (0., 0.)
    assert out.external_heat_in_w == -10.
    assert out.reservoir_entropy_rate_w_k == 10. / 295.
    assert out.total_entropy_rate_w_k + out.reservoir_entropy_rate_w_k == pytest.approx(out.total_entropy_production_w_k, abs=1e-16)
    assert min(out.face_entropy_production_w_k) >= 0.
    one = plate(reference=ReferenceSlab(.02, .01, 1), outer_boundary="fixed_temperature")
    uniform = one.evaluate([304.])
    assert uniform.points[0].stress_pa == 0.
    assert uniform.temperature_rates_k_s == pytest.approx((-9. / 20.,), abs=1e-14)


def test_one_coupled_cooling_stage_matches_independent_dense_matrix():
    op = plate(outer_boundary="fixed_temperature")
    temperature = np.array([304., 301.])
    out = op.evaluate(temperature)
    diagonal = 1e5 - 20 * temperature
    matrix = np.diag(diagonal) + np.outer(20 * temperature, [.5, .5])
    reference = np.linalg.solve(matrix, np.array([-3., -9.]) / 1e-4)
    np.testing.assert_allclose(out.temperature_rates_k_s, reference, rtol=1e-14)
    assert out.in_plane_strain_rate_per_s == pytest.approx(1e-4 * np.mean(reference), rel=1e-14)
    assert out.total_internal_energy_rate_w == pytest.approx(out.external_heat_in_w, abs=1e-11)
    assert out.total_entropy_rate_w_k + out.reservoir_entropy_rate_w_k == pytest.approx(out.total_entropy_production_w_k, abs=1e-15)
    # Deliberately omit thermal coupling. It does not reproduce the actual
    # coupled rates or local energy balance, although total mechanical work is 0.
    wrong_td = np.array(out.cell_heat_in_w) / 1e-4 / diagonal
    wrong_ed = 1e-4 * np.mean(wrong_td)
    wrong_udot = diagonal * wrong_td + 2e9 * (out.in_plane_strain + .03) * wrong_ed
    residual = 1e-4 * wrong_udot - np.array(out.cell_heat_in_w) - 2e-4 * np.array([p.stress_pa for p in out.points]) * wrong_ed
    assert np.max(np.abs(residual)) > .1
    assert np.max(np.abs(wrong_td - reference)) > .01


def test_outputs_and_model_are_immutable():
    op = plate()
    values = [304., 300.]
    out = op.evaluate(values)
    values[0] = 301.
    assert out.temperatures_k == (304., 300.)
    with pytest.raises(FrozenInstanceError):
        out.in_plane_strain = 0.
    with pytest.raises(FrozenInstanceError):
        out.points[0].stress_pa = 0.
    with pytest.raises(FrozenInstanceError):
        op.biaxial_modulus_pa = 1.
    assert isinstance(out.cell_heat_in_w, tuple)
    assert out.full_slab_mirror_factor == 2
    assert out.ledger_scope == "reference_half_slab"
    assert out.material_qualified is False


@pytest.mark.parametrize("changes", [
    {"biaxial_modulus_pa": 0.}, {"biaxial_modulus_pa": math.inf},
    {"biaxial_modulus_pa": True}, {"linear_expansion_per_k": math.nan},
    {"stress_free_heat_capacity_j_m3_k": 0.}, {"reference_temperature_k": 0.},
    {"conductivity_w_m_k": -1.}, {"conductivity_w_m_k": True},
    {"outer_temperature_k": 0.}, {"outer_temperature_k": math.inf},
    {"temperature_bounds_k": (310., 290.)}, {"temperature_bounds_k": (0., 310.)},
    {"strain_bounds": (-.01, True)}, {"strain_bounds": (.01, -.01)},
    {"linear_expansion_per_k": 1.},
    {"stress_free_heat_capacity_j_m3_k": 6200.},
    {"coefficient_classification": "literature"},
    {"coefficient_classification": ["manufactured"]},
    {"mechanical_regime": "asymmetric_bending"}, {"outer_boundary": "film"},
    {"outer_boundary": ["adiabatic"]},
    {"reference": None},
])
def test_invalid_model_inputs_fail_closed(changes):
    with pytest.raises(ThermoelasticPlateError):
        plate(**changes)


@pytest.mark.parametrize("values", [
    [304.], [], [[304., 300.]], [True, 300.], [304., "300"],
    [math.nan, 300.], [math.inf, 300.], [0., 300.], [289., 300.], [311., 300.],
])
def test_invalid_or_out_of_domain_temperatures_fail_closed(values):
    with pytest.raises(ThermoelasticPlateError):
        plate().evaluate(values)


def test_strain_and_unrepresentable_outputs_fail_closed():
    op = plate()
    with pytest.raises(ThermoelasticPlateError, match="strain"):
        op.constitutive_point(304., .02)
    with pytest.raises(ThermoelasticPlateError, match="strain"):
        op.constitutive_point(290., .01)
    with pytest.raises(ThermoelasticPlateError, match="strain"):
        replace(op, strain_bounds=(-1e-5, 1e-5)).evaluate([304., 300.])
    with pytest.raises(ThermoelasticPlateError):
        plate(reference=ReferenceSlab(1e-200, 1e-200, 2))


def test_nearly_zero_ce_single_cell_retains_exact_common_mode():
    # Independent-review regression: Ce ~ 1e-12 used to produce -5000.158...
    # while returning an edot belonging to the correct -5000 common mode.
    op = plate(
        reference=ReferenceSlab(.02, .01, 1),
        biaxial_modulus_pa=1., stress_free_heat_capacity_j_m3_k=1.,
        linear_expansion_per_k=math.sqrt((1. - 1e-12) / 600.),
        temperature_bounds_k=(299., 300.), strain_bounds=(-.1, .1),
        outer_temperature_k=299., outer_boundary="fixed_temperature",
    )
    out = op.evaluate([300.])
    assert 0. < out.points[0].fixed_strain_heat_capacity_j_m3_k < 2e-12
    expected = out.cell_heat_in_w[0] / out.reference_cell_volumes_m3[0]
    assert expected == -5000.
    assert out.temperature_rates_k_s == (expected,)
    assert out.in_plane_strain_rate_per_s == op.linear_expansion_per_k * expected
    assert out.total_internal_energy_rate_w == pytest.approx(-1., abs=1e-15)


def test_nearly_singular_multicell_unrepresentable_common_mode_is_rejected():
    op = plate(
        biaxial_modulus_pa=1., stress_free_heat_capacity_j_m3_k=1.,
        linear_expansion_per_k=math.sqrt((1. - 1e-12) / 600.),
        temperature_bounds_k=(299., 300.), strain_bounds=(-.1, .1),
        outer_temperature_k=299.123456789, outer_boundary="fixed_temperature",
    )
    # The contrast rates are ~1e16 K/s: binary64 cannot retain their much
    # smaller, nonintegral common cooling rate to a forcing-scaled roundoff bound.
    with pytest.raises(ThermoelasticPlateError, match="unresolved_thermal_rate"):
        op.evaluate([300., 300.])


def test_nearly_zero_ce_uniform_adiabatic_multicell_remains_at_rest():
    op = plate(
        reference=ReferenceSlab(.02, .01, 3),
        biaxial_modulus_pa=1., stress_free_heat_capacity_j_m3_k=1.,
        linear_expansion_per_k=math.sqrt((1. - 1e-12) / 600.),
        temperature_bounds_k=(299., 300.), strain_bounds=(-.1, .1),
    )
    out = op.evaluate([300.] * 3)
    assert out.temperature_rates_k_s == (0., 0., 0.)
    assert out.in_plane_strain_rate_per_s == 0.


@pytest.mark.parametrize("outer_boundary", ["adiabatic", "fixed_temperature"])
def test_zero_heat_face_skips_unused_unrepresentable_temperature_ratio(outer_boundary):
    # Independent-review regression: zero flux times an overflowing temperature
    # ratio must not create NaN entropy on an inactive/insulating boundary.
    op = plate(
        reference=ReferenceSlab(.02, .01, 1),
        biaxial_modulus_pa=1., stress_free_heat_capacity_j_m3_k=1.,
        linear_expansion_per_k=0., conductivity_w_m_k=0.,
        reference_temperature_k=1e-100, temperature_bounds_k=(5e-101, 2e-100),
        outer_temperature_k=1e308, outer_boundary=outer_boundary,
    )
    out = op.evaluate([1e-100])
    assert out.face_heat_outward_w == (0., 0.)
    assert out.face_entropy_production_w_k == (0., 0.)
    assert out.temperature_rates_k_s == (0.,)
    assert out.total_entropy_rate_w_k == out.reservoir_entropy_rate_w_k == 0.
