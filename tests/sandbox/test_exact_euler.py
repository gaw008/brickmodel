"""Public Euler predictor preserves the adaptive driver's represented arithmetic."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest

from sludge_sandbox.exact_integration import advance_exact_euler
from sludge_sandbox.integration import ConservedState, Rates, IntegrationError, _Reject
from test_exact_integration import initial, policy, rates


def test_predictor_uses_original_derivative_product_and_state_rounding():
    state = initial()
    r = rates(state)
    duration = F(1, 3)
    out = advance_exact_euler(state, r, duration, policy())
    # Independently specified derivatives from the fixture's actual shared faces.
    for before, derivative, after in (
        (state.amounts_mol, np.array([[-.4, .5], [-.15, .25]]), out.amounts_mol),
        (state.internal_energy_j, np.array([4., 3.]), out.internal_energy_j),
        (state.mechanical_stretches, np.array([.1, .2, .3]), out.mechanical_stretches)):
        expected = np.array([float(a)+float(duration*F(float(d))) for a, d in zip(before.flat, derivative.flat)]).reshape(before.shape)
        np.testing.assert_array_equal(after, expected)
    assert out.energy_model_identity == state.energy_model_identity


@pytest.mark.parametrize('duration', [0., True, 1, F(), F(-1)])
def test_exact_positive_duration_required(duration):
    with pytest.raises(IntegrationError, match='exact_positive_euler_duration_required'):
        advance_exact_euler(initial(), rates(initial()), duration, policy())


def test_no_mechanics_and_signed_energy_are_preserved():
    state = ConservedState([[1.]], [-2.])
    r = Rates([[0.], [0.]], [0., 0.], [[0.]], [.1])
    out = advance_exact_euler(state, r, F(1, 2), policy())
    assert out.internal_energy_j[0] == -1.95 and out.mechanical_stretches is None


def test_legacy_scaled_underflow_is_not_replaced_by_affine_refusal():
    state = ConservedState([[1.]], [1.])
    r = Rates([[0.], [0.]], [0., 0.], [[1e-320]], [0.])
    out = advance_exact_euler(state, r, F(1, 10**50), policy())
    assert out.amounts_mol[0, 0] == 1.


def test_original_rejection_and_roundoff_classifications():
    state = ConservedState([[1.]], [1.])
    r = Rates([[0.], [0.]], [0., 0.], [[-2.]], [0.])
    with pytest.raises(_Reject, match='trial_inventory_or_energy_invalid'):
        advance_exact_euler(state, r, F(1), policy())
    with pytest.raises(_Reject, match='unrepresentable_exact_duration_product'):
        advance_exact_euler(state, replace(r, reaction_species_mol_s=[[1e308]]), F(2), policy())
    with pytest.raises(IntegrationError, match='unresolvable_amount_increment'):
        advance_exact_euler(state, replace(r, reaction_species_mol_s=[[.1]]), F(1, 3),
                            replace(policy(), amount_absolute_tolerance_mol=1e-30))


def test_mutated_policy_is_revalidated_and_mechanical_scales_required():
    p = policy()
    object.__setattr__(p, 'amount_absolute_tolerance_mol', float('inf'))
    with pytest.raises(IntegrationError):
        advance_exact_euler(initial(), rates(initial()), F(1, 8), p)
    with pytest.raises(IntegrationError, match='explicit_stretch_scales_required'):
        advance_exact_euler(initial(), rates(initial()), F(1, 8),
                            replace(policy(), stretch_absolute_tolerance=None, stretch_scale=None))
