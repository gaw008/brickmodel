"""Read-only algebraic review of the candidate storage; no time integration."""

from dataclasses import replace
from fractions import Fraction as F
import math
import random
import sys

import pytest

sys.path.insert(0, "/private/tmp/brick-cooling-energy-v1/candidate")

from sludge_sandbox.cooling_thermoelastic_plate import CoolingThermoelasticPlate
from sludge_sandbox.geometry import ReferenceSlab
from thermoelastic_energy_storage import (
    EnergyDomainError,
    EnergyInversePolicy,
    EnergyResolutionError,
    EnergyStorageError,
    EnergyTarget,
    ThermoelasticEnergyStorage,
    _down,
    _sqrt_bounds,
    _up,
)


def plate() -> CoolingThermoelasticPlate:
    """The original two-cell B coefficients supplied by the candidate author."""
    return CoolingThermoelasticPlate(
        reference=ReferenceSlab(0.02, 0.01, 2),
        biaxial_modulus_pa=1e9,
        linear_expansion_per_k=1e-4,
        stress_free_heat_capacity_j_m3_k=1e5,
        reference_temperature_k=300.0,
        conductivity_w_m_k=1.0,
        temperature_bounds_k=(290.0, 310.0),
        strain_bounds=(-0.01, 0.01),
        outer_temperature_k=300.0,
        outer_boundary="fixed_temperature",
        coefficient_classification="manufactured",
        mechanical_regime="symmetric_free_plane_stress",
    )


def constants(p: CoolingThermoelasticPlate) -> tuple[F, F, F, F, F]:
    volume = F((p.reference.half_thickness_m / p.reference.cells) * p.reference.reference_area_m2)
    return (
        volume,
        F(p.stress_free_heat_capacity_j_m3_k),
        F(p.biaxial_modulus_pa),
        F(p.linear_expansion_per_k),
        F(p.reference_temperature_k),
    )


def energy(p: CoolingThermoelasticPlate, temperatures: tuple[float | F, ...]) -> tuple[F, ...]:
    """Independent original-input rational recomputation of free total U."""
    v, c, modulus, alpha, reference = constants(p)
    temperatures = tuple(map(F, temperatures))
    mean = sum(temperatures, F()) / len(temperatures)
    strain = alpha * (mean - reference)
    return tuple(
        v * (c * (t - reference) + modulus * (strain + alpha * reference) ** 2 - modulus * alpha**2 * t**2)
        for t in temperatures
    )


def policy(*, energy_j: float = 1e-9, temperature_k: float = 1e-9, bits: int = 256) -> EnergyInversePolicy:
    return EnergyInversePolicy(energy_j, temperature_k, 1024, bits)


def test_isqrt_enclosures_exact_inequalities() -> None:
    rng = random.Random(7281)
    cases = [(F(rng.randint(0, 10**30), rng.randint(1, 10**20)), rng.randint(8, 256)) for _ in range(1000)]
    cases += [(F(1, 2**2148), 4096), (F(2**2048 - 1), 256), (F(0), 8), (F(9, 16), 8)]
    for value, bits in cases:
        lower, upper = _sqrt_bounds(value, bits)
        assert lower**2 <= value <= upper**2
        assert upper - lower <= F(1, 2**bits)


def test_outward_binary64_bounds_including_subnormals() -> None:
    for value in (
        F(0), F(1, 2**1075), F(1, 2**4096), F(-1, 2**4096),
        F(math.nextafter(0.0, math.inf)), F(2**1023),
        F(1) + F(1, 2**100), F(-1) - F(1, 2**100),
    ):
        assert F(_down(value)) <= value <= F(_up(value))


def test_fixed_strain_total_u_and_psi_negative_control() -> None:
    p = plate()
    storage = ThermoelasticEnergyStorage(p)
    ts, strain = (303.0, 297.0), 0.0
    result = storage.at_strain(ts, strain)
    v, c, modulus, alpha, reference = constants(p)
    for t, represented, bound, point in zip(ts, result.cell_energy_j, result.energy_roundoff_bound_j, result.constitutive_points):
        exact = v * (c * (F(t) - reference) + modulus * (F(strain) + alpha * reference) ** 2 - modulus * alpha**2 * F(t)**2)
        assert abs(F(represented) - exact) <= F(bound)
        wrong = v * F(point.helmholtz_j_m3)
        assert abs(wrong - exact) > F(1)


@pytest.mark.parametrize("ts", [(304.0, 304.0), (304.0, 296.0), (290.0, 310.0), (300.0, 300.0)])
def test_forward_actual_float_energy_and_plate_discrepancy(ts: tuple[float, ...]) -> None:
    p = plate()
    result = ThermoelasticEnergyStorage(p).forward(ts)
    exact = energy(p, ts)
    v, _, _, alpha, reference = constants(p)
    for value, expected, bound, point, plate_bound in zip(
        result.cell_energy_j, exact, result.energy_roundoff_bound_j,
        result.plate_evaluation.points, result.plate_energy_difference_bound_j,
    ):
        assert abs(F(value) - expected) <= F(bound)
        assert abs(v * F(point.internal_energy_j_m3) - expected) <= F(plate_bound)
    exact_strain = alpha * (sum(map(F, ts), F()) / len(ts) - reference)
    assert abs(F(result.plate_evaluation.in_plane_strain) - exact_strain) <= F(result.plate_strain_difference_bound)
    assert not result.material_qualified


def test_exact_energy_directional_derivative_differs_from_rate_matrix() -> None:
    p = plate()
    v, c, modulus, alpha, _ = constants(p)
    b = modulus * alpha**2
    ts, direction, step = (F(304), F(296)), (F(3), F(-2)), F(1, 8)
    mean, mean_direction = sum(ts, F()) / 2, sum(direction, F()) / 2
    plus = energy(p, tuple(t + step * d for t, d in zip(ts, direction)))
    minus = energy(p, tuple(t - step * d for t, d in zip(ts, direction)))
    derivative = tuple((hi - lo) / (2 * step) for hi, lo in zip(plus, minus))
    expected = tuple(v * ((c - 2 * b * t) * d + 2 * b * mean * mean_direction) for t, d in zip(ts, direction))
    wrong_rate = tuple(v * ((c - 2 * b * t) * d + 2 * b * t * mean_direction) for t, d in zip(ts, direction))
    assert derivative == expected
    assert derivative != wrong_rate
    assert sum(d * value for d, value in zip(direction, derivative)) > 0


@pytest.mark.parametrize("ts", [(304.0, 304.0), (304.0, 296.0), (299.25, 300.75), (300.0, 300.0)])
def test_original_state_and_actual_returned_float_residual_bound(ts: tuple[float, ...]) -> None:
    p = plate()
    storage = ThermoelasticEnergyStorage(p)
    original = storage.forward(ts)
    target = EnergyTarget(original.cell_energy_j, original.energy_roundoff_bound_j)
    inverse = storage.inverse(target, policy())
    actual_energy = energy(p, inverse.state.temperatures_k)
    for actual, wanted, source_error, residual_bound, combined_bound in zip(
        actual_energy, target.cell_energy_j, target.absolute_error_j,
        inverse.energy_residual_abs_bound_j, inverse.combined_energy_residual_bound_j,
    ):
        assert abs(actual - F(wanted)) <= F(residual_bound)
        assert abs(actual - F(wanted)) + F(source_error) <= F(combined_bound)
        assert combined_bound <= inverse.policy.energy_tolerance_j
    error_squared = sum((F(actual) - F(original_t)) ** 2 for actual, original_t in zip(inverse.state.temperatures_k, ts))
    assert error_squared <= F(inverse.temperature_error_bound_k) ** 2
    v, c, modulus, alpha, _ = constants(p)
    true_dmin = v * (c - 2 * modulus * alpha**2 * F(p.temperature_bounds_k[1]))
    assert F(inverse.minimum_energy_jacobian_eigenvalue_j_k) <= true_dmin
    # The two public rounded certificate fields must also compose without
    # relying on the private exact heat-capacity lower bound.
    norm_squared = sum((abs(actual - F(wanted)) + F(source_error)) ** 2
                       for actual, wanted, source_error in zip(actual_energy, target.cell_energy_j, target.absolute_error_j))
    public_radius = F(inverse.temperature_error_bound_k)
    public_lower = F(inverse.minimum_energy_jacobian_eigenvalue_j_k)
    assert norm_squared <= (public_radius * public_lower) ** 2
    assert inverse.target is target
    assert inverse.target_interval_admissible


def test_zero_target_error_has_positive_separate_numerical_tolerance() -> None:
    storage = ThermoelasticEnergyStorage(plate())
    target = EnergyTarget((40.0, -40.0), (0.0, 0.0))
    result = storage.inverse(target, policy())
    assert result.target.absolute_error_j == (0.0, 0.0)
    assert result.policy.energy_tolerance_j > 0.0
    assert result.combined_energy_residual_bound_j == result.energy_residual_abs_bound_j
    with pytest.raises(EnergyResolutionError):
        storage.inverse(target, policy(energy_j=1e-30, temperature_k=1e-30))


def test_alpha_zero_linear_and_negative_alpha_controls() -> None:
    for alpha in (0.0, -plate().linear_expansion_per_k):
        p = replace(plate(), linear_expansion_per_k=alpha)
        storage = ThermoelasticEnergyStorage(p)
        original = storage.forward((304.0, 296.0))
        result = storage.inverse(EnergyTarget(original.cell_energy_j, original.energy_roundoff_bound_j), policy())
        assert max(abs(t - wanted) for t, wanted in zip(result.state.temperatures_k, (304.0, 296.0))) <= result.temperature_error_bound_k
        if alpha == 0.0:
            assert result.existence_certificate == "exact_linear_domain_solution"
            assert result.state.in_plane_strain == 0.0


def test_no_root_and_unresolved_are_distinct() -> None:
    storage = ThermoelasticEnergyStorage(plate())
    with pytest.raises(EnergyDomainError, match="empty_feasible_mean_square_interval"):
        storage.inverse(EnergyTarget((1e9, -1e9), (0.0, 0.0)), policy())
    # This target has a nonempty component-feasible q interval, but its scalar
    # closure has no root. Positive Ce / SPD alone would wrongly accept it.
    with pytest.raises(EnergyDomainError, match="monotone_scalar_has_no_domain_root"):
        storage.inverse(EnergyTarget((-100.0, 0.0), (0.0, 0.0)), policy())
    with pytest.raises(EnergyResolutionError):
        storage.inverse(EnergyTarget((40.0, -40.0), (0.0, 0.0)), policy(energy_j=1e-30, temperature_k=1e-30, bits=8))
    with pytest.raises(EnergyResolutionError, match="target_energy_error_exceeds_requested_budget"):
        storage.inverse(EnergyTarget((40.0, -40.0), (1e-6, 0.0)), policy())


@pytest.mark.parametrize("bounds", [(300.0, 310.0), (290.0, 300.0)])
def test_exact_domain_endpoint_and_uncertain_boundary(bounds: tuple[float, float]) -> None:
    storage = ThermoelasticEnergyStorage(replace(plate(), temperature_bounds_k=bounds))
    result = storage.inverse(EnergyTarget((0.0, 0.0), (0.0, 0.0)), policy())
    assert result.existence_certificate == "exact_scalar_endpoint_root"
    assert result.state.temperatures_k == (300.0, 300.0)
    assert result.temperature_error_bound_k == 0.0
    assert result.energy_residual_abs_bound_j == (0.0, 0.0)
    with pytest.raises(EnergyResolutionError, match="target_uncertainty_not_certified_inside_domain"):
        storage.inverse(EnergyTarget((0.0, 0.0), (1e-10, 1e-10)), policy())


def test_nonempty_q_interval_without_scalar_root_independently() -> None:
    p = plate()
    v, c, modulus, alpha, reference = constants(p)
    b = modulus * alpha**2
    lo, hi = map(F, p.temperature_bounds_k)
    h = lambda t: c * t - b * t**2
    xs = tuple(F(e) / v + c * reference for e in (-100.0, 0.0))
    qlo = max(lo**2, *( (x - h(hi)) / b for x in xs))
    qhi = min(hi**2, *( (x - h(lo)) / b for x in xs))
    assert qlo <= qhi
    # Independent rational bisection in T (no quadratic-root helper).
    lower_temperatures = []
    for x in xs:
        lower_t, upper_t = lo, hi
        for _ in range(128):
            trial = (lower_t + upper_t) / 2
            if h(trial) <= x - b * qhi:
                lower_t = trial
            else:
                upper_t = trial
        lower_temperatures.append(lower_t)
    lower_mean, upper_mean = lo, hi
    for _ in range(128):
        trial = (lower_mean + upper_mean) / 2
        if trial**2 <= qhi:
            lower_mean = trial
        else:
            upper_mean = trial
    assert sum(lower_temperatures, F()) / 2 - upper_mean > 0


def test_narrow_strain_domain_is_configuration_error_not_proved_no_root() -> None:
    p = replace(plate(), strain_bounds=(-0.0001, 0.0001))
    with pytest.raises(EnergyStorageError) as captured:
        ThermoelasticEnergyStorage(p)
    assert not isinstance(captured.value, EnergyDomainError)
    assert not isinstance(captured.value, EnergyResolutionError)


def test_nonscalar_input_and_invalid_budgets_fail_explicitly() -> None:
    with pytest.raises(EnergyStorageError):
        EnergyTarget((math.nan, 0.0), (0.0, 0.0))
    with pytest.raises(EnergyStorageError):
        EnergyInversePolicy(0.0, 1e-9, 1024, 256)
    with pytest.raises(EnergyStorageError):
        ThermoelasticEnergyStorage(plate()).forward((300.0,))
