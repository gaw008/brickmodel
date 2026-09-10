"""Independent integral and two-layer representation-error examples."""
from fractions import Fraction as F
import numpy as np
import pytest

from sludge_sandbox.exact_terminal_panel import affine_integral, affine_integral_value, affine_update
from sludge_sandbox.integration import IntegrationError


def test_rational_diagnostic_is_integrated_without_float_roundtrip():
    assert affine_integral_value(F(1, 3), F(1, 3), F(1), F(1, 2)) == F(1, 3)
    # Integral of 2+6t over [0,1/3], with the second observation at1/4.
    assert affine_integral_value(F(2), F(7, 2), F(1, 3), F(1, 4)) == 1


def test_matrix_integrals_and_opposite_phase_share_exact_rounding():
    first = np.array([[2., -2.], [.5, -.5]])
    middle = np.array([[5., -5.], [2., -2.]])
    values, exact = affine_integral(first, middle, F(1, 3), F(1, 2))
    assert exact == (F(1), F(-1), F(1, 3), F(-1, 3))
    np.testing.assert_array_equal(values, [[1., -1.], [float(F(1, 3)), -float(F(1, 3))]])
    assert all(F(float(row[0]))+F(float(row[1])) == 0 for row in values)


def test_zero_state_projection_does_not_hide_integral_projection_error():
    scale = float(2**53)
    left, exact_left = affine_integral(np.array([scale]), np.array([scale+2]), F(1), F(1))
    right, exact_right = affine_integral(np.array([scale]), np.array([scale]), F(1), F(1))
    state, state_error = affine_update(np.array([1.]), (left, -right), 1e-12)
    assert exact_left == (F(2**53+1),) and exact_right == (F(2**53),)
    assert state.tolist() == [1.] and state_error == (F(),)
    # True represented-rate quadrature yields2; only component projection lost1.
    assert F(float(state[0]))-F(2) == F(-1)
    assert F(float(left[0]))-exact_left[0] == F(-1)


def test_state_residual_preserved_and_original_gate_refuses_it():
    before, increment = np.array([1.]), np.array([.1])
    state, error = affine_update(before, (increment,), 1e-12)
    assert state.tolist() == [1.1]
    assert error == (F(1.1)-F(1)-F(.1),)
    assert error[0] > 0
    with pytest.raises(IntegrationError, match='affine_state_roundoff_budget'):
        affine_update(before, (increment,), 1e-30)
    np.testing.assert_array_equal(before, [1.])


@pytest.mark.parametrize('value,h', [(1e-320, F(1, 10**50)), (1e308, F(2))])
def test_integral_overflow_and_nonzero_underflow_refused(value, h):
    a = np.array([value])
    with pytest.raises(IntegrationError, match='affine_unrepresentable_integral'):
        affine_integral(a, a, h, h/2)


@pytest.mark.parametrize('duration', [1., F(), F(-1), True])
def test_exact_positive_duration_contract(duration):
    with pytest.raises(IntegrationError, match='exact_affine_integral'):
        affine_integral(np.array([1.]), np.array([2.]), duration, F(1))


def test_mismatched_or_nonfinite_arrays_and_boolean_budget_are_rejected():
    for a,b in ((np.array([1.]), np.array([1., 2.])), (np.array([float('nan')]), np.array([1.]))):
        with pytest.raises(IntegrationError):
            affine_integral(a, b, F(1), F(1, 2))
    with pytest.raises(IntegrationError):
        affine_update(np.array([1.]), (np.array([1.]),), True)
    with pytest.raises(IntegrationError):
        affine_update(np.array([1.]), (np.array([1., 2.]),), 1e-12)
