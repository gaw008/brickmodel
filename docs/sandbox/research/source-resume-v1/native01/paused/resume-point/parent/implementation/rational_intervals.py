"""Exact signed interval algebra; caller supplies every physical hypothesis.

No root existence, EOS validity, material qualification or event permission is
established by these arithmetic functions.
"""
from fractions import Fraction

RationalInterval = tuple[Fraction, Fraction]


class RationalIntervalError(ValueError):
    """An interval or denominator violates the exact arithmetic contract."""


def _interval(value: RationalInterval) -> None:
    if (type(value) is not tuple or len(value) != 2
            or any(type(v) is not Fraction for v in value) or value[0] > value[1]):
        raise RationalIntervalError('ordered_exact_fraction_interval_required')


def interval_difference(a: RationalInterval, b: RationalInterval) -> RationalInterval:
    """Enclose every a-b with independently varying interval arguments."""
    _interval(a)
    _interval(b)
    return a[0] - b[1], a[1] - b[0]


def interval_sum(intervals: tuple[RationalInterval, ...]) -> RationalInterval:
    """Sum endpoints exactly; the empty sum is the zero interval."""
    if type(intervals) is not tuple:
        raise RationalIntervalError('explicit_interval_tuple_required')
    for value in intervals:
        _interval(value)
    return (sum((v[0] for v in intervals), Fraction()),
            sum((v[1] for v in intervals), Fraction()))


def interval_divide_positive(numerator: RationalInterval,
                             denominator: RationalInterval) -> RationalInterval:
    """Enclose signed division over a strictly positive denominator interval."""
    _interval(numerator)
    _interval(denominator)
    if denominator[0] <= 0:
        raise RationalIntervalError('strict_positive_denominator_required')
    corners = tuple(n / d for n in numerator for d in denominator)
    return min(corners), max(corners)


def residual_to_root_bound(residual: RationalInterval, compliance_lower: Fraction) -> Fraction:
    """Return max|residual|/c; a root/compliance proof is the caller's duty."""
    _interval(residual)
    if type(compliance_lower) is not Fraction or compliance_lower <= 0:
        raise RationalIntervalError('strict_positive_exact_compliance_required')
    return max(abs(residual[0]), abs(residual[1])) / compliance_lower
