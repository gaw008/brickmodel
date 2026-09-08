"""Manufactured dynamic stretches are genuine RK state, not inventory columns."""
from fractions import Fraction
import math
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState, IntegrationError, IntegrationPolicy, Rates, integrate


def policy(**changes):
    values = dict(initial_step_s=.1, maximum_step_s=.1, minimum_step_s=1e-12,
        relative_tolerance=1e-8, amount_absolute_tolerance_mol=1e-12,
        energy_absolute_tolerance_j=1e-10, amount_scale_mol=1., energy_scale_j=1.,
        maximum_steps=10000, maximum_rejections=1000, maximum_wall_seconds=10,
        stretch_absolute_tolerance=1e-11, stretch_scale=1.)
    return IntegrationPolicy(**(values | changes))


def rates(state, stretch_rates=None, power=0.):
    return Rates([[0.], [0.]], [0., 0.], [[0.]], [power], mechanical_rates_per_s=stretch_rates)


def test_coupled_exponential_stretch_and_energy_share_stage_state_and_ledger():
    initial = ConservedState([[1.]], [0.], mechanical_stretches=[1., 1.])
    def operator(state, time):
        n = state.mechanical_stretches[0]
        return rates(state, [n, 0.], n)
    result = integrate(initial, operator, start_s=0., end_s=.5, policy=policy())
    assert result.status == 'completed' and len(result.steps) > 1
    assert result.states[-1].mechanical_stretches == pytest.approx([math.exp(.5), 1.], abs=2e-6)
    assert result.states[-1].internal_energy_j[0] == pytest.approx(math.exp(.5)-1, abs=2e-6)
    cumulative = [Fraction(), Fraction()]
    for state, ledger in zip(result.states[1:], result.steps):
        assert ledger.stretch_increment is not None
        assert ledger.stretch_quadrature_roundoff is not None
        for index, increment in enumerate(ledger.stretch_increment):
            cumulative[index] += Fraction(float(increment))
            residual = Fraction(float(state.mechanical_stretches[index]))-Fraction(1)-cumulative[index]
            assert abs(residual) <= Fraction(1e-11)
        assert state.amounts_mol.shape == (1, 1) and state.amounts_mol[0, 0] == 1


def test_mechanical_error_alone_controls_rejection_and_positive_stages():
    initial = ConservedState([[1.]], [0.], mechanical_stretches=[1., 1.])
    seen = []
    def operator(state, time):
        seen.append(tuple(state.mechanical_stretches))
        return rates(state, [-10*state.mechanical_stretches[0], 0.])
    result = integrate(initial, operator, start_s=0., end_s=.2,
        policy=policy(initial_step_s=.2, maximum_step_s=.2))
    assert result.status == 'completed' and result.rejected_trials > 0
    assert all(value[0] > 0 for value in seen)
    assert result.states[-1].mechanical_stretches[0] == pytest.approx(math.exp(-2), abs=2e-6)
    assert result.states[-1].internal_energy_j[0] == 0
    assert result.steps[0].end_s < .2


def test_cancel_during_trial_preserves_initial_stretches_without_ledger():
    initial = ConservedState([[1.]], [0.], mechanical_stretches=[1., 1.])
    calls = 0
    def operator(state, time):
        nonlocal calls
        calls += 1
        return rates(state, [1., .5], 1.)
    result = integrate(initial, operator, start_s=0., end_s=.1,
        policy=policy(), cancel=lambda: calls >= 3)
    assert result.status == 'cancelled' and not result.steps
    assert len(result.states) == 1 and np.array_equal(result.states[0].mechanical_stretches, [1., 1.])


def test_rates_state_pair_and_explicit_scales_are_required():
    initial = ConservedState([[1.]], [0.], mechanical_stretches=[1., 1.])
    result = integrate(initial, lambda s,t: rates(s), start_s=0., end_s=.1, policy=policy())
    assert result.status == 'numerical_failure' and not result.steps
    with pytest.raises(IntegrationError):
        integrate(initial, lambda s,t: rates(s, [0., 0.]), start_s=0., end_s=.1,
                  policy=policy(stretch_absolute_tolerance=None, stretch_scale=None))
    plain = ConservedState([[1.]], [0.])
    result = integrate(plain, lambda s,t: rates(s, [0., 0.]), start_s=0., end_s=.1, policy=policy())
    assert result.status == 'numerical_failure'


@pytest.mark.parametrize('values', ([1.], [1., 1., 1.], [0., 1.], [-1., 1.], [True, 1.], [float('nan'), 1.]))
def test_stretch_state_requires_positive_finite_correct_shape(values):
    with pytest.raises(IntegrationError):
        ConservedState([[1.]], [0.], mechanical_stretches=values)


def test_stretches_are_immutable_snapshot_and_rate_shape_checked():
    values = [1., 1.]
    state = ConservedState([[1.]], [0.], mechanical_stretches=values)
    values[0] = 2.
    assert state.mechanical_stretches[0] == 1.
    with pytest.raises(ValueError):
        state.mechanical_stretches.setflags(write=True)
    result = integrate(state, lambda s,t: rates(s, [0.]), start_s=0., end_s=.1, policy=policy())
    assert result.status == 'numerical_failure' and not result.steps


def test_legacy_state_policy_and_positional_rates_remain_unchanged():
    initial = ConservedState([[1.]], [2.])
    result = integrate(initial, lambda s,t: Rates([[0.],[0.]], [0.,0.], [[0.]], [0.]),
        start_s=0., end_s=.1, policy=policy(stretch_absolute_tolerance=None, stretch_scale=None))
    assert result.status == 'completed'
    assert result.states[-1].mechanical_stretches is None
    assert result.steps[0].stretch_increment is None
    assert result.steps[0].stretch_quadrature_roundoff is None
