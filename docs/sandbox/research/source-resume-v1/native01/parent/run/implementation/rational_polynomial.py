"""Rational polynomial arithmetic; no physical event or correction permission."""
from fractions import Fraction


def _coefficients(values: tuple[Fraction, ...]) -> None:
    if type(values) is not tuple or any(type(x) is not Fraction for x in values):
        raise ValueError('exact_rational_polynomial_coefficients_required')


def refine_descending_bracket(
    coefficients: tuple[Fraction, ...], lower: Fraction, upper: Fraction,
) -> tuple[Fraction, Fraction]:
    """One step on a caller-validated descending branch, constant term first.

    The caller establishes root existence and branch membership. Zero values
    keep the lower half-endpoint convention used by the legacy dyadic clocks;
    in particular, an exact midpoint hit does not collapse the enclosure.
    """
    _coefficients(coefficients)
    if (not coefficients or type(lower) is not Fraction or type(upper) is not Fraction
            or lower >= upper):
        raise ValueError('exact_nonempty_polynomial_and_ordered_bracket_required')
    midpoint = (lower + upper) / 2
    value = Fraction()
    for coefficient in reversed(coefficients):
        value = value * midpoint + coefficient
    return (midpoint, upper) if value >= 0 else (lower, midpoint)


def polynomial_gcd(
    left: tuple[Fraction, ...], right: tuple[Fraction, ...],
) -> tuple[Fraction, ...]:
    """Unnormalized rational GCD, constant first; the zero polynomial is ()."""
    _coefficients(left)
    _coefficients(right)

    def trim(polynomial: list[Fraction]) -> list[Fraction]:
        while polynomial and polynomial[-1] == 0:
            polynomial.pop()
        return polynomial

    a, b = trim(list(left)), trim(list(right))
    while b:
        remainder = list(a)
        while remainder and len(remainder) >= len(b):
            offset = len(remainder) - len(b)
            factor = remainder[-1] / b[-1]
            for i, coefficient in enumerate(b):
                remainder[offset + i] -= factor * coefficient
            trim(remainder)
        a, b = b, remainder
    return tuple(a)
