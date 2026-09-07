"""Independent arithmetic tests; no native water provider or physical fixture."""
from decimal import Decimal, localcontext
from fractions import Fraction
import math

import pytest

from sludge_sandbox.affine_depletion_clock import (
    AffineDepletionClockError, AffineDepletionClockEvidence,
    locate_affine_depletion_clock,
)


def test_constant_sink_exact_root_and_each_component() -> None:
    clock = locate_affine_depletion_clock(0., .25, 1., (-3., 1.), (-3., 1.), 1., 1e-12)
    assert clock.end_s == .5
    assert clock.inventory_residual(1., (-1.5, .5)) == 0
    assert clock.event_time_rounding_s == 0
    with pytest.raises(AffineDepletionClockError, match='term_mismatch'):
        clock.inventory_residual(1., (-1., 0.))  # Same net, wrong individual terms.


def test_affine_irrational_root_decimal_oracle() -> None:
    # N(h)=1-h-h^2, rate -1-2h, midpoint .25 => -1.5.
    clock = locate_affine_depletion_clock(0., .25, 1., (-1.,), (-1.5,), 1., 1e-12)
    with localcontext() as context:
        context.prec = 100
        root = (Decimal(5).sqrt()-1)/2
        assert Decimal(clock.end_s) < root < Decimal(math.nextafter(clock.end_s, math.inf))
        assert root-Decimal(clock.end_s) <= Decimal(clock.event_time_rounding_s.numerator)/Decimal(clock.event_time_rounding_s.denominator)
    h = Fraction(clock.end_s)
    assert clock.inventory_residual(1., (float(-h-h*h),)) == 1-h-h*h


def test_decelerating_but_strictly_decreasing_enclosure() -> None:
    # N=1-2h+h^2/2; small root 2-sqrt(2), derivative negative up to1.
    clock = locate_affine_depletion_clock(0., .25, 1., (-2.,), (-1.75,), 1., 1e-12)
    with localcontext() as context:
        context.prec = 100
        root = 2-Decimal(2).sqrt()
        assert Decimal(clock.end_s) <= root < Decimal(math.nextafter(clock.end_s, math.inf))


def test_nearly_constant_coefficient_not_dropped() -> None:
    mid = math.nextafter(-1., -math.inf)
    clock = locate_affine_depletion_clock(0., .25, 1., (-1.,), (mid,), 2., 1e-12)
    assert clock.end_s < 1.
    h = Fraction(clock.end_s)
    coefficient = 2*(Fraction(mid)+1)
    assert clock.inventory_residual(1., (float(-h+coefficient*h*h),)) == 1-h+coefficient*h*h


@pytest.mark.parametrize('start_rates,mid_rates,maximum,reason', [
    ((0.,), (-1.,), 1., 'nonmonotone'),
    ((1.,), (1.,), 1., 'nonmonotone'),
    ((-1.,), (-1.,), .5, 'no_root'),
    ((-2.,), (-1.,), 1., 'nonmonotone'),
    ((-2.,), (-1.,), 2., 'nonmonotone'),
])
def test_uncertified_crossings_fail(start_rates: tuple[float, ...], mid_rates: tuple[float, ...], maximum: float, reason: str) -> None:
    with pytest.raises(AffineDepletionClockError, match=reason):
        locate_affine_depletion_clock(0., .25, 1., start_rates, mid_rates, maximum, 1e-12)


def test_large_origin_exact_represented_midpoint_and_downward_root() -> None:
    start = float(2**40)
    clock = locate_affine_depletion_clock(start, start+.25, 1., (-3.,), (-3.,), start+1., .001)
    exact = Fraction(start)+Fraction(1, 3)
    assert Fraction(clock.end_s) <= exact < Fraction(math.nextafter(clock.end_s, math.inf))
    h = Fraction(clock.end_s)-Fraction(start)
    assert clock.inventory_residual(1., (float(-3*h),)) == 1-3*h
    assert 0 < exact-Fraction(clock.end_s) <= clock.event_time_rounding_s


def test_insufficient_time_budget_fails() -> None:
    with pytest.raises(AffineDepletionClockError, match='time_budget'):
        locate_affine_depletion_clock(float(2**40), float(2**40)+.25, 1., (-3.,), (-3.,), float(2**40)+1., 1e-8)


def test_clock_with_no_representable_interior_midpoint_fails() -> None:
    start = float(2**53)
    with pytest.raises(AffineDepletionClockError, match='interval'):
        locate_affine_depletion_clock(start, start+1., 1., (-1.,), (-1.,), start+4., 1.)


def test_negative_origin_crosses_zero() -> None:
    clock = locate_affine_depletion_clock(-1., -.75, 2., (-1.,), (-1.,), 2., 1e-12)
    assert clock.end_s == 1.


@pytest.mark.parametrize('end', [.49, .51])
def test_manually_selected_nonroot_endpoint_rejected(end: float) -> None:
    clock = AffineDepletionClockEvidence(0., end, (-2.,), (-2.,), .25, 1e-12, 1.)
    with pytest.raises(AffineDepletionClockError, match='root'):
        clock.inventory_residual(1., (float(-2*Fraction(end)),))


@pytest.mark.parametrize('start,mid,amount,rates,midrates', [
    (False, .25, 1., (-1.,), (-1.,)),
    (0., math.nan, 1., (-1.,), (-1.,)),
    (0., .25, 0., (-1.,), (-1.,)),
    (0., .25, 1., (), ()),
    (0., .25, 1., (-1.,), (-1., 0.)),
    (0., .25, 1., (math.inf,), (-1.,)),
])
def test_invalid_arguments(start: float, mid: float, amount: float, rates: tuple[float, ...], midrates: tuple[float, ...]) -> None:
    with pytest.raises(AffineDepletionClockError):
        locate_affine_depletion_clock(start, mid, amount, rates, midrates, 2., 1e-12)


def test_exact_root_at_maximum_and_immutable_inventory_binding() -> None:
    clock = locate_affine_depletion_clock(0., .25, 1., (-2.,), (-2.,), .5, 1e-100)
    assert clock.end_s == .5 and clock.event_time_rounding_s == 0
    with pytest.raises(AffineDepletionClockError, match='start_inventory_mismatch'):
        clock.inventory_residual(2., (-1.,))


def test_next_representable_exact_root_cannot_be_skipped() -> None:
    end = math.nextafter(.5, -math.inf)
    clock = AffineDepletionClockEvidence(0., end, (-2.,), (-2.,), .25, 1e-12, 1.)
    with pytest.raises(AffineDepletionClockError, match='nearest_downward_root'):
        _ = clock.event_time_rounding_s


def test_actual_midpoint_delta_is_used_at_large_origin() -> None:
    start = float(2**40)
    midpoint = start+.1  # Stored difference is not exactly .1.
    hm = Fraction(midpoint)-Fraction(start)
    clock = locate_affine_depletion_clock(start, midpoint, 1., (-1.,), (-1.25,), start+1., .001)
    h = Fraction(clock.end_s)-Fraction(start)
    b = Fraction(-1, 8)/hm
    actual = 1-h+b*h*h
    neighbor_h = Fraction(math.nextafter(clock.end_s, math.inf))-Fraction(start)
    assert actual >= 0 > 1-neighbor_h+b*neighbor_h*neighbor_h
    assert clock.inventory_residual(1., (float(-h+b*h*h),)) == actual
