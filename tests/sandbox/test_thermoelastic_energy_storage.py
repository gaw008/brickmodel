"""Pure algebra, domain and returned-representation tests; no time integration."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction as F
import math

import numpy as np
import pytest

from sludge_sandbox.cooling_thermoelastic_plate import CoolingThermoelasticPlate
from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.thermoelastic_energy_storage import (
    EnergyDomainError, EnergyInversePolicy, EnergyResolutionError,
    EnergyStorageError, EnergyTarget, ThermoelasticEnergyStorage,
    _down, _sqrt_bounds, _up,
)


def make_plate(cells=2, **changes):
    """Declared manufactured B coefficients; no material-source qualification."""
    options = dict(reference=ReferenceSlab(.02, .01, cells),
        biaxial_modulus_pa=1e9, linear_expansion_per_k=1e-4,
        stress_free_heat_capacity_j_m3_k=1e5, reference_temperature_k=300.,
        conductivity_w_m_k=1., temperature_bounds_k=(290., 310.),
        strain_bounds=(-.01, .01), outer_temperature_k=300.,
        outer_boundary='fixed_temperature', coefficient_classification='manufactured',
        mechanical_regime='symmetric_free_plane_stress')
    return CoolingThermoelasticPlate(**{**options, **changes})


def dyadic_plate(cells=2, **changes):
    return make_plate(cells, **{**dict(reference=ReferenceSlab(.125, .25, cells),
        biaxial_modulus_pa=1., linear_expansion_per_k=.125,
        stress_free_heat_capacity_j_m3_k=16., reference_temperature_k=4.,
        conductivity_w_m_k=0., temperature_bounds_k=(3., 5.),
        strain_bounds=(-1., 1.), outer_temperature_k=4., outer_boundary='adiabatic'), **changes})


def policy(**changes):
    return EnergyInversePolicy(**{**dict(energy_tolerance_j=1e-10,
        temperature_tolerance_k=1e-9, maximum_iterations=200, square_root_bits=160), **changes})


def exact_energy(p, temperatures, strain=None):
    """Independent restrained u=U0+M(e+alpha*Tr)^2-M alpha^2 T^2."""
    ts = tuple(map(F, temperatures))
    m, a, c, tr = map(F, (p.biaxial_modulus_pa, p.linear_expansion_per_k,
                         p.stress_free_heat_capacity_j_m3_k, p.reference_temperature_k))
    e = a*(sum(ts, F())/len(ts)-tr) if strain is None else F(strain)
    v = F((p.reference.half_thickness_m/p.reference.cells)*p.reference.reference_area_m2)
    return tuple(v*(c*(t-tr)+m*(e+a*tr)**2-m*a*a*t*t) for t in ts)


def assert_returned_certificate(storage, result):
    actual = exact_energy(storage.plate, result.state.temperatures_k)
    norm2 = F()
    for e, target, error, reported, combined in zip(actual, result.target.cell_energy_j,
            result.target.absolute_error_j, result.energy_residual_abs_bound_j,
            result.combined_energy_residual_bound_j):
        residual = abs(e-F(target))
        assert residual <= F(reported)
        assert residual+F(error) <= F(combined) <= F(result.policy.energy_tolerance_j)
        norm2 += (residual+F(error))**2
    radius = F(result.temperature_error_bound_k)
    lower = F(result.minimum_energy_jacobian_eigenvalue_j_k)
    assert norm2 <= (radius*lower)**2
    assert radius <= F(result.policy.temperature_tolerance_k)
    assert result.target_interval_admissible
    assert result.state.material_qualified is False
    assert result.state.plate_evaluation.material_qualified is False


@pytest.mark.parametrize('temperatures', [(304.,), (304., 301.),
    (291., 299.125, 304.25, 308.), tuple(296.+i*.375 for i in range(16))])
def test_nonuniform_forward_inverse_and_actual_returned_residual(temperatures):
    storage = ThermoelasticEnergyStorage(make_plate(len(temperatures)))
    initial = storage.forward(temperatures)
    target = EnergyTarget(initial.cell_energy_j, (0.,)*storage.cells)
    result = storage.inverse(target, policy())
    assert result.target is target
    assert result.target.cell_energy_j == initial.cell_energy_j
    assert_returned_certificate(storage, result)
    # Input T is within forward rounding of the nominal energy target. Propagate
    # that separately instead of asserting the nominal target is exactly E(Tin).
    initial_error = np.linalg.norm(initial.energy_roundoff_bound_j)
    allowed = result.temperature_error_bound_k+initial_error/result.minimum_energy_jacobian_eigenvalue_j_k
    assert np.linalg.norm(np.array(result.state.temperatures_k)-temperatures) <= allowed
    assert result.elapsed_s >= 0.


@pytest.mark.parametrize('alpha', [0., .125, -.125])
@pytest.mark.parametrize('temperatures', [(3., 3.), (3., 5.), (5., 5.)])
def test_exact_dyadic_domain_boundaries(alpha, temperatures):
    storage = ThermoelasticEnergyStorage(dyadic_plate(linear_expansion_per_k=alpha))
    initial = storage.forward(temperatures)
    assert initial.energy_roundoff_bound_j == (0., 0.)
    result = storage.inverse(EnergyTarget(initial.cell_energy_j, (0., 0.)), policy())
    assert result.state.temperatures_k == temperatures
    assert result.energy_residual_abs_bound_j == (0., 0.)
    assert_returned_certificate(storage, result)


def test_alpha_zero_linear_arbitrary_target_and_no_domain_snap():
    storage = ThermoelasticEnergyStorage(dyadic_plate(linear_expansion_per_k=0.))
    result = storage.inverse(EnergyTarget((.125, -.0625), (0., 0.)), policy())
    assert result.state.temperatures_k == (4.5, 3.75)
    assert result.existence_certificate == 'exact_linear_domain_solution'
    assert result.iterations == 0
    with pytest.raises(EnergyDomainError, match='linear_energy_target_has_no'):
        storage.inverse(EnergyTarget((math.nextafter(.25, math.inf), 0.), (0., 0.)),
                        policy(energy_tolerance_j=100., temperature_tolerance_k=100.))


@pytest.mark.parametrize('energies,reason', [((1e6, -1e6), 'empty_feasible'),
                                           ((-100., 0.), 'monotone_scalar_has_no')])
def test_distinct_proven_nonlinear_no_root_conditions(energies, reason):
    storage = ThermoelasticEnergyStorage(make_plate())
    with pytest.raises(EnergyDomainError, match=reason):
        storage.inverse(EnergyTarget(energies, (0., 0.)), policy())


def test_exact_explicit_strain_and_free_force_elimination_are_separate():
    storage = ThermoelasticEnergyStorage(dyadic_plate())
    ts = (3.5, 4.75)
    free = storage.forward(ts)
    held = storage.at_strain(ts, 0.)
    expected = exact_energy(storage.plate, ts, strain=0.)
    assert held.cell_energy_j == tuple(map(float, expected))
    assert held.cell_energy_j != free.cell_energy_j
    volume = storage.reference_cell_volume_m3
    assert math.fsum(p.stress_pa*volume for p in free.plate_evaluation.points) == 0.
    for point, energy in zip(held.constitutive_points, held.cell_energy_j):
        assert point.internal_energy_j_m3 == pytest.approx(
            point.helmholtz_j_m3+point.temperature_k*point.entropy_j_m3_k, abs=2e-14)
        assert point.internal_energy_j_m3*volume == energy


def test_using_helmholtz_as_internal_energy_decodes_to_a_different_state():
    storage = ThermoelasticEnergyStorage(make_plate())
    ts = (304., 301.)
    forward = storage.forward(ts)
    wrong = tuple(p.helmholtz_j_m3*storage.reference_cell_volume_m3
                  for p in forward.plate_evaluation.points)
    assert max(abs(u-f) for u,f in zip(forward.cell_energy_j, wrong)) > 10.
    result = storage.inverse(EnergyTarget(wrong, (0., 0.)), policy())
    assert max(abs(a-b) for a,b in zip(ts, result.state.temperatures_k)) > 1.
    assert_returned_certificate(storage, result)


def test_energy_jacobian_is_symmetric_and_is_not_the_temperature_rate_matrix():
    p = dyadic_plate()
    ts, step = (F(7, 2), F(19, 4)), F(1, 1024)
    n = 2
    volume = F((p.reference.half_thickness_m/n)*p.reference.reference_area_m2)
    b, c, mean = F(p.biaxial_modulus_pa)*F(p.linear_expansion_per_k)**2, F(16), sum(ts)/n
    observed = []
    for j in range(n):
        plus, minus = list(ts), list(ts)
        plus[j] += step
        minus[j] -= step
        observed.append(tuple((a-bb)/(2*step) for a,bb in
                              zip(exact_energy(p, plus), exact_energy(p, minus))))
    actual = tuple(tuple(observed[j][i] for j in range(n)) for i in range(n))
    true_j = tuple(tuple(volume*((c-2*b*ts[i])*(i==j)+2*b*mean/n)
                         for j in range(n)) for i in range(n))
    rate_a = tuple(tuple(volume*((c-2*b*ts[i])*(i==j)+2*b*ts[i]/n)
                         for j in range(n)) for i in range(n))
    assert actual == true_j
    assert actual[0][1] == actual[1][0]
    assert actual != rate_a
    # Local work explains the difference; it cannot be dropped from the host.
    rates = (F(1, 2), F(-1, 4))
    mrate = sum(rates)/n
    for i in range(n):
        je_rate = sum(actual[i][j]*rates[j] for j in range(n))
        a_rate = sum(rate_a[i][j]*rates[j] for j in range(n))
        mechanical = 2*volume*b*(mean-ts[i])*mrate
        assert je_rate-a_rate == mechanical


def test_nonzero_target_uncertainty_has_a_separate_domain_certificate():
    storage = ThermoelasticEnergyStorage(make_plate())
    initial = storage.forward((304., 301.))
    errors = (1e-7, 2e-7)
    result = storage.inverse(EnergyTarget(initial.cell_energy_j, errors),
                             policy(energy_tolerance_j=1e-6, temperature_tolerance_k=1e-6))
    assert_returned_certificate(storage, result)
    for signs in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        energies = tuple(e+s*d for e,s,d in zip(initial.cell_energy_j, signs, errors))
        decoded = storage.inverse(EnergyTarget(energies, (0., 0.)), policy())
        distance = np.linalg.norm(np.subtract(decoded.state.temperatures_k, result.state.temperatures_k))
        assert distance <= result.temperature_error_bound_k+decoded.temperature_error_bound_k


def test_uncertainty_near_boundary_is_unresolved_not_a_proven_domain_exit():
    storage = ThermoelasticEnergyStorage(dyadic_plate())
    energy = storage.forward((3., 3.)).cell_energy_j
    with pytest.raises(EnergyResolutionError, match='uncertainty_not_certified'):
        storage.inverse(EnergyTarget(energy, (1e-8, 1e-8)),
                         policy(energy_tolerance_j=1e-6, temperature_tolerance_k=1e-6))


def test_uncertainty_over_budget_rejected_before_solving():
    storage = ThermoelasticEnergyStorage(make_plate())
    with pytest.raises(EnergyResolutionError, match='error_exceeds_requested_budget'):
        storage.inverse(EnergyTarget((0., 0.), (1., 0.)), policy())


def test_numerical_limit_and_binary64_budget_failures_are_not_domain_events():
    storage = ThermoelasticEnergyStorage(make_plate())
    target = EnergyTarget(storage.forward((303.125, 301.875)).cell_energy_j, (0., 0.))
    with pytest.raises(EnergyResolutionError, match='iteration_limit'):
        storage.inverse(target, policy(maximum_iterations=1))
    with pytest.raises(EnergyResolutionError, match='binary64_temperature_budget|cannot_meet_requested_budget'):
        storage.inverse(target, policy(energy_tolerance_j=1e-30, temperature_tolerance_k=1e-30))


def test_forward_roundoff_and_core_algebra_discrepancy_bounds_are_outward():
    storage = ThermoelasticEnergyStorage(make_plate(4))
    ts = (291.1, 298.123456789, 304.123456789, 308.6)
    result = storage.forward(ts)
    exact = exact_energy(storage.plate, ts)
    volume = F(storage.reference_cell_volume_m3)
    for e, represented, rnd, point, core in zip(exact, result.cell_energy_j,
            result.energy_roundoff_bound_j, result.plate_evaluation.points,
            result.plate_energy_difference_bound_j):
        assert abs(e-F(represented)) <= F(rnd)
        assert abs(e-volume*F(point.internal_energy_j_m3)) <= F(core)
    exact_strain = F(storage.plate.linear_expansion_per_k)*(sum(map(F, ts))/4-F(300))
    assert abs(exact_strain-F(result.plate_evaluation.in_plane_strain)) <= F(result.plate_strain_difference_bound)


def test_successful_inverse_evaluates_the_full_plate_exactly_once(monkeypatch):
    storage = ThermoelasticEnergyStorage(make_plate())
    target = EnergyTarget(storage.forward((304., 301.)).cell_energy_j, (0., 0.))
    original, calls = CoolingThermoelasticPlate.evaluate, []
    def counted(self, values):
        calls.append(tuple(values))
        return original(self, values)
    monkeypatch.setattr(CoolingThermoelasticPlate, 'evaluate', counted)
    result = storage.inverse(target, policy())
    assert calls == [result.state.temperatures_k]


def test_whole_temperature_box_strain_admission_is_a_configuration_restriction():
    # Individual states, e.g. uniform Tr, are valid, but the inverse's declared
    # complete rectangular domain is not admitted by the narrow strain bounds.
    p = make_plate(strain_bounds=(-.0015, .0015))
    assert p.evaluate((300., 300.)).in_plane_strain == 0.
    with pytest.raises(EnergyStorageError, match='complete_temperature_box') as caught:
        ThermoelasticEnergyStorage(p)
    assert not isinstance(caught.value, EnergyDomainError)


@pytest.mark.parametrize('values', [[], [300.], [True, 300.], [300., math.nan],
                                   [300., math.inf], ['300', 300.], None])
def test_temperature_input_validation(values):
    with pytest.raises(EnergyStorageError):
        ThermoelasticEnergyStorage(make_plate()).forward(values)


@pytest.mark.parametrize('values', [(289., 300.), (300., 311.)])
def test_true_temperature_domain_exit(values):
    with pytest.raises(EnergyDomainError, match='temperature_outside'):
        ThermoelasticEnergyStorage(make_plate()).forward(values)


@pytest.mark.parametrize('energy,error', [([], []), ([0.], []), ([True], [0.]),
    ([math.nan], [0.]), ([0.], [-1.]), ([0.], [math.inf]), ([0.], [False])])
def test_target_validation(energy, error):
    with pytest.raises(EnergyStorageError):
        EnergyTarget(energy, error)


@pytest.mark.parametrize('changes', [dict(energy_tolerance_j=0.), dict(temperature_tolerance_k=math.inf),
    dict(energy_tolerance_j=True), dict(maximum_iterations=True), dict(maximum_iterations=0),
    dict(square_root_bits=7), dict(square_root_bits=4097), dict(square_root_bits=160.)])
def test_policy_validation(changes):
    with pytest.raises(EnergyStorageError):
        policy(**changes)


def test_target_and_results_are_immutable_and_shape_is_checked():
    energies, errors = [0., 0.], [0., 0.]
    target = EnergyTarget(energies, errors)
    energies[0], errors[0] = 1., 1.
    assert target.cell_energy_j == target.absolute_error_j == (0., 0.)
    with pytest.raises(FrozenInstanceError):
        target.cell_energy_j = (1., 1.)
    storage = ThermoelasticEnergyStorage(make_plate())
    with pytest.raises(EnergyStorageError, match='shape'):
        storage.inverse(EnergyTarget([0.], [0.]), policy())
    with pytest.raises(EnergyStorageError, match='explicit_target'):
        storage.inverse([0., 0.], policy())
    state = storage.forward([300., 300.])
    with pytest.raises(FrozenInstanceError):
        state.temperatures_k = (301., 301.)


@pytest.mark.parametrize('value', [F(0), F(2), F(1, 3), F(123456789, 987654321), F(1, 2**1100)])
def test_rational_sqrt_enclosure_and_binary64_outward_conversion(value):
    lo, hi = _sqrt_bounds(value, 160)
    assert lo*lo <= value <= hi*hi
    assert hi-lo <= F(1, 2**160)
    assert F(_down(value)) <= value <= F(_up(value))


@pytest.mark.parametrize('left_width,right_width', [(F(1), F(3)), (F(3), F(1)), (F(2), F(2))])
def test_interval_newton_contains_independently_known_root_for_both_signs(left_width, right_width):
    storage = ThermoelasticEnergyStorage(dyadic_plate())
    temperatures = (F(7, 2), F(19, 4))
    known_root = (sum(temperatures)/2)**2
    energies = exact_energy(storage.plate, temperatures)
    x = tuple(e/F(storage.reference_cell_volume_m3)+F(16)*F(4) for e in energies)
    lo, hi = known_root-left_width, known_root+right_width
    midpoint = (lo+hi)/2
    _, sign = storage._scalar(midpoint, x, 160)
    mean_bounds = (_sqrt_bounds(lo, 160)[0], _sqrt_bounds(hi, 160)[1])
    newlo, newhi = storage._interval_newton(lo, hi, midpoint, sign, mean_bounds, 160)
    assert lo <= newlo <= known_root <= newhi <= hi
    assert newhi-newlo < (hi-lo)/10


def test_interval_newton_signed_division_must_include_both_negative_and_positive_bounds():
    storage = ThermoelasticEnergyStorage(dyadic_plate())
    # Uniform reference T=4 has exact F(16)=0. A deliberately wider valid
    # F enclosure crosses zero; all four signed quotients must be considered.
    lo, hi, midpoint = F(9), F(25), F(16)
    sign = (F(-1, 16), F(1, 8))
    mean_bounds = (F(3), F(5))
    newlo, newhi = storage._interval_newton(lo, hi, midpoint, sign, mean_bounds, 160)
    m, a, c = F(1), F(1, 8), F(16)
    slope_lower = m*a*a/(c-2*m*a*a*3)+F(1, 10)
    exact_lower, exact_upper = midpoint+sign[0]/slope_lower, midpoint+sign[1]/slope_lower
    assert newlo <= exact_lower < midpoint < exact_upper <= newhi
    assert F(9) <= newlo <= newhi <= F(25)


def test_interval_newton_uses_positive_domain_bound_if_dyadic_sqrt_underresolves():
    storage = ThermoelasticEnergyStorage(make_plate(1, biaxial_modulus_pa=1.,
        linear_expansion_per_k=.1, stress_free_heat_capacity_j_m3_k=1.,
        reference_temperature_k=1e-100, conductivity_w_m_k=0.,
        temperature_bounds_k=(5e-101, 2e-100), strain_bounds=(-1., 1.),
        outer_temperature_k=1e308, outer_boundary='adiabatic'))
    lo, hi = F(5e-101)**2, F(2e-100)**2
    root = F(1e-100)**2  # Uniform reference state: exactly zero energy and F.
    mean_bounds = (_sqrt_bounds(lo, 8)[0], _sqrt_bounds(hi, 8)[1])
    assert mean_bounds[0] == 0
    newlo, newhi = storage._interval_newton(lo, hi, root, (F(), F()), mean_bounds, 8)
    assert lo <= newlo <= root <= newhi <= hi


def test_interval_newton_invariant_failure_is_numerical_not_physical():
    storage = ThermoelasticEnergyStorage(dyadic_plate())
    with pytest.raises(EnergyResolutionError, match='lost_proved_root'):
        storage._interval_newton(F(9), F(25), F(16), (F(100), F(101)), (F(3), F(5)), 160)


def test_bisection_fallback_keeps_original_algebraic_contract(monkeypatch):
    storage = ThermoelasticEnergyStorage(make_plate())
    initial = storage.forward((304., 301.))
    target = EnergyTarget(initial.cell_energy_j, (0., 0.))
    # No Newton contraction: the previously certified sign still selects a
    # half interval. This is the old algorithm, with the original policy.
    widths = []
    def unchanged(self, lo, hi, *unused):
        widths.append(hi-lo)
        return lo, hi
    monkeypatch.setattr(ThermoelasticEnergyStorage, '_interval_newton', unchanged)
    result = storage.inverse(target, policy())
    assert_returned_certificate(storage, result)
    assert result.iterations == len(widths)+1
    assert len(widths) >= 2
    assert all(right*2 == left for left,right in zip(widths,widths[1:]))
