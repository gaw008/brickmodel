from fractions import Fraction as F

import pytest

from sludge_sandbox.rational_polynomial import polynomial_gcd, refine_descending_bracket


@pytest.mark.parametrize('coefficients,lower,upper,expected', [
    ((F(1), F(-2)), F(0), F(1), (F(1, 2), F(1))),
    ((F(1), F(-2)), F(1, 2), F(1), (F(1, 2), F(3, 4))),
    ((F(1), F(-1)), F(0), F(1), (F(1, 2), F(1))),
    # Zero derivative at either end of a valid descending quadratic branch.
    ((F(1), F(0), F(-2)), F(0), F(1), (F(1, 2), F(1))),
    ((F(1), F(-4), F(4)), F(0), F(1, 2), (F(1, 4), F(1, 2))),
])
def test_descending_sign_transition_including_legacy_zero_convention(coefficients, lower, upper, expected):
    assert refine_descending_bracket(coefficients, lower, upper) == expected


def test_gcd_common_later_root_is_arithmetic_only_and_does_not_mutate_inputs():
    a = (F(3, 16), F(-1), F(1))
    b = (F(3, 8), F(-5, 4), F(1))
    g = polynomial_gcd(a, b)
    assert g == (F(-3, 16), F(1, 4))
    assert -g[0]/g[1] == F(3, 4)
    assert a == (F(3, 16), F(-1), F(1))
    assert b == (F(3, 8), F(-5, 4), F(1))
    assert polynomial_gcd(a, tuple(2*x for x in a)) == tuple(2*x for x in a)
    assert polynomial_gcd((F(), F()), ()) == ()
    assert polynomial_gcd(a+(F(),), ()) == a


@pytest.mark.parametrize('coefficients,lower,upper', [
    ((1., F(-1)), F(), F(1)),
    ([F(1), F(-1)], F(), F(1)),
    ((F(1), F(-1)), 0., F(1)),
    ((F(1), F(-1)), F(), F()),
    ((), F(), F(1)),
])
def test_refinement_refuses_implicit_coercion_and_empty_brackets(coefficients, lower, upper):
    with pytest.raises(ValueError):
        refine_descending_bracket(coefficients, lower, upper)


def test_gcd_refuses_nonrational_coefficients():
    with pytest.raises(ValueError):
        polynomial_gcd((F(1), False), (F(1),))
