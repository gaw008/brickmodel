"""Manufactured single-cell diagonal free-traction instantaneous rate solve.

Normal and common tangential rates remain separate because the existing internal
surface energy is oriented. No timestep, thermal source, material admission or
free-sintering calibration is provided here. Residuals retain represented-rate
roundoff; balance bounds distinguish it from final evaluation uncertainty.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from .skeleton_energy import (
    DiagonalSkeletonEnergy,
    SkeletonEnergyError,
    SkeletonEnergyState,
    _Interval,
    _iv,
    _number,
    _output,
)


class FreeSkeletonRatesError(SkeletonEnergyError):
    """Unsupported free-rate contract or unrepresentable certified arithmetic."""


@dataclass(frozen=True)
class FreeSkeletonRates:
    rates: tuple[float, float]
    rate_error_bounds: tuple[float, float]
    state: SkeletonEnergyState
    volume_rate_m3_s: float
    volume_rate_error_m3_s: float
    external_power_w: float
    external_power_error_w: float
    power_residual_w: float
    power_residual_error_w: float
    power_evaluation_error_w: float
    power_rate_roundoff_bound_w: float
    traction_residual_pa: tuple[float, float, float]
    traction_residual_error_pa: tuple[float, float, float]
    traction_evaluation_error_pa: tuple[float, float, float]
    traction_rate_roundoff_bound_pa: tuple[float, float, float]
    zero_balance_enclosed: bool
    pore_pressure_pa: float
    external_pressure_pa: float
    model_identity: tuple
    qualification: str = 'manufactured_single_cell_diagonal_instantaneous_free_traction_only'
    error_scope: str = (
        'Residuals use represented final-state values. Evaluation errors enclose '
        'the fixed represented-rate arithmetic and stress evaluation. Combined '
        'balance errors additionally propagate the solved-rate enclosure, including '
        'rate representation error. Zero balance is enclosed only when the explicit '
        'zero_balance_enclosed check passes. No parameter uncertainty, constitutive '
        'accuracy, time-integration accuracy or material qualification is asserted.'
    )


def _enclosure(value: float, error: float) -> _Interval:
    center, bound = Fraction(value), Fraction(error)
    return _Interval(center-bound, center+bound)


def _upper(value: Fraction) -> float:
    """The existing symmetric-zero enclosure gives an outward-rounded radius."""
    if value < 0:
        raise FreeSkeletonRatesError('negative_numerical_bound')
    _, bound = _output(_Interval(-value, value))
    return bound


def solve_free_rates(
    skeleton: DiagonalSkeletonEnergy,
    *,
    normal_stretch: float,
    tangential_stretch: float,
    pore_pressure_pa: float,
    external_pressure_pa: float,
    solid_inventory_mol: Mapping[str, float],
) -> FreeSkeletonRates:
    """Solve two free diagonal rates and independently audit final traction/power.

    Pvisc_i = eta*lambda_dot_i/lambda_i**2. The balanced Piola stress
    is (pore_pressure-external_pressure)*J/lambda_i, giving the explicit
    positive-viscosity solve. Final energy accounting satisfies
    Eelastic_dot + Einterface_dot + D - p*Vdot = -pext*Vdot within the
    returned numerical balance bounds. D is already part of that identity;
    this function does not add another dissipative thermal source.
    """
    if type(skeleton) is not DiagonalSkeletonEnergy:
        raise FreeSkeletonRatesError('fixed_diagonal_skeleton_required')
    if skeleton.reference.cells != 1 or skeleton.cell_index != 0:
        raise FreeSkeletonRatesError('single_reference_cell_required')
    if (skeleton.classification != 'manufactured_test_fixture' or
            skeleton.allow_manufactured is not True):
        raise FreeSkeletonRatesError('explicit_manufactured_model_required')
    eta = _number(skeleton.viscosity_pa_s, 'viscosity', positive=True)
    pore = _number(pore_pressure_pa, 'pore_pressure', nonnegative=True)
    external = _number(external_pressure_pa, 'external_pressure', nonnegative=True)
    # This call preserves the original inventory, stretch and source contract.
    static = skeleton.evaluate(normal_stretch=normal_stretch,
        tangential_stretch=tangential_stretch, normal_rate_per_s=0.0,
        tangential_rate_per_s=0.0, solid_inventory_mol=solid_inventory_mol)
    normal, tangent = static.normal_stretch, static.tangential_stretch
    stretch = (Fraction(normal), Fraction(tangent), Fraction(tangent))
    jacobian = stretch[0]*stretch[1]*stretch[2]
    volume = Fraction(skeleton.reference_volume_m3)
    pressure_difference = Fraction(pore)-Fraction(external)
    solved = []
    for index in (0, 1):
        elastic = _enclosure(static.elastic_piola_pa[index],
                             static.numerical_error_bounds['elastic_piola_pa'][index])
        interface = _enclosure(static.interface_piola_pa[index],
                               static.numerical_error_bounds['interface_piola_pa'][index])
        drive = pressure_difference*jacobian/stretch[index]-elastic-interface
        solved.append(_output(stretch[index]**2/Fraction(eta)*drive))
    rates = (solved[0][0], solved[1][0])
    errors = (solved[0][1], solved[1][1])
    # Do not clamp to the allowed rate: an out-of-domain free rate must fail.
    state = skeleton.evaluate(normal_stretch=normal, tangential_stretch=tangent,
        normal_rate_per_s=rates[0], tangential_rate_per_s=rates[1],
        solid_inventory_mol=solid_inventory_mol)
    principal_rates = (Fraction(rates[0]), Fraction(rates[1]), Fraction(rates[1]))
    principal_errors = (Fraction(errors[0]), Fraction(errors[1]), Fraction(errors[1]))
    volume_rate_exact = volume*sum((jacobian*rate/lam for rate, lam in
                                   zip(principal_rates, stretch)), Fraction())
    volume_rate, volume_error = _output(volume_rate_exact)
    external_power, external_error = _output(-Fraction(external)*volume_rate_exact)

    traction_values, evaluation_errors, rate_bounds, combined_errors = [], [], [], []
    for index in range(3):
        traction = sum((_enclosure(getattr(state, name)[index],
                        state.numerical_error_bounds[name][index]) for name in
                        ('elastic_piola_pa', 'interface_piola_pa', 'viscous_piola_pa')), _iv(0))
        traction -= pressure_difference*jacobian/stretch[index]
        residual, evaluation_error = _output(traction)
        rate_bound = Fraction(eta)*principal_errors[index]/stretch[index]**2
        traction_values.append(residual)
        evaluation_errors.append(evaluation_error)
        rate_bounds.append(_upper(rate_bound))
        combined_errors.append(_upper(Fraction(evaluation_error)+rate_bound))

    # Independent final-state powers, not the traction residual multiplied back
    # into a manufactured zero. Include displayed Vdot and external-power errors.
    power = sum((_enclosure(getattr(state, name), state.numerical_error_bounds[name])
                 for name in ('elastic_rate_w', 'interface_rate_w', 'dissipation_w')), _iv(0))
    power -= Fraction(pore)*_enclosure(volume_rate, volume_error)
    power -= _enclosure(external_power, external_error)
    power_residual, power_evaluation_error = _output(power)
    power_rate_bound = volume*sum((abs(rate)*Fraction(eta)*error/lam**2 for rate, error, lam in
                                  zip(principal_rates, principal_errors, stretch)), Fraction())
    power_error = _upper(Fraction(power_evaluation_error)+power_rate_bound)
    enclosed = (all(abs(Fraction(value)) <= Fraction(bound) for value, bound in
                    zip(traction_values, combined_errors)) and
                abs(Fraction(power_residual)) <= Fraction(power_error))
    return FreeSkeletonRates(
        rates=rates, rate_error_bounds=errors, state=state,
        volume_rate_m3_s=volume_rate, volume_rate_error_m3_s=volume_error,
        external_power_w=external_power, external_power_error_w=external_error,
        power_residual_w=power_residual, power_residual_error_w=power_error,
        power_evaluation_error_w=power_evaluation_error,
        power_rate_roundoff_bound_w=_upper(power_rate_bound),
        traction_residual_pa=tuple(traction_values),
        traction_residual_error_pa=tuple(combined_errors),
        traction_evaluation_error_pa=tuple(evaluation_errors),
        traction_rate_roundoff_bound_pa=tuple(rate_bounds),
        zero_balance_enclosed=enclosed, pore_pressure_pa=pore, external_pressure_pa=external,
        model_identity=('manufactured_free_diagonal_rates_v1', skeleton.identity,
                        'two_dof_positive_viscosity_piola_pressure_balance',
                        'fixed_represented_rate_residual_plus_solution_interval_bound'))
