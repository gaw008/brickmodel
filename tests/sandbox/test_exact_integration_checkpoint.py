"""Ordinary accepted-prefix pause/resume, manufactured rates only; no EOS."""
from dataclasses import fields, replace
from fractions import Fraction as F
import math

import numpy as np
import pytest

from sludge_sandbox.exact_integration import integrate_exact, integrate_exact_checkpointed
from sludge_sandbox.exact_integration_checkpoint import (ExactCheckpointError, PAUSE_REASON,
    _same, _seal)
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.integration import ConservedState, Rates, DomainExit
from test_exact_integration import initial, policy, rates


def go(p, operator=None, *, start=F(), end=None, state=None, **kwargs):
    return integrate_exact_checkpointed(initial() if state is None else state,
        (lambda s, t: rates(s)) if operator is None else operator,
        start_s=T(start), end_s=T(start + 4 * F(p.initial_step_s)) if end is None else T(end),
        policy=p, **kwargs)


def numerical_result(result):
    return replace(result, elapsed_seconds=0.)


def test_repeated_pause_continuation_matches_every_actual_callback_and_history():
    p = policy()
    uninterrupted_calls, continued_calls = [], []
    def operator(calls):
        def evaluate(state, when):
            calls.append((state, when))
            return rates(state)
        return evaluate
    expected = go(p, operator(uninterrupted_calls))
    first = go(p, operator(continued_calls), pause_after_commit=lambda cp: True)
    assert first.result.status == 'cancelled' and first.result.reason == PAUSE_REASON
    assert first.checkpoint is not None and len(first.result.steps) == 1
    first.checkpoint.check()
    second = go(p, operator(continued_calls), continuation=first.checkpoint,
                pause_after_commit=lambda cp: len(cp.result.steps) == 2)
    assert second.checkpoint is not None and len(second.result.steps) == 2
    final = go(p, operator(continued_calls), continuation=second.checkpoint)
    assert final.result.status == 'completed'
    assert _same(numerical_result(final.result), numerical_result(expected.result))
    assert _same(tuple(continued_calls), tuple(uninterrupted_calls))
    assert _same(final.observations, expected.observations)
    assert final.result.elapsed_seconds >= second.result.elapsed_seconds >= first.result.elapsed_seconds
    assert [x.role for x in final.observations[:8]] == [
        'initial', 'full_first', 'full_second', 'left_first', 'left_second', 'right_first', 'right_second', 'accepted']


def test_pause_at_final_endpoint_completes_without_false_checkpoint():
    p = policy()
    out = go(p, end=F(p.initial_step_s), pause_after_commit=lambda cp: True)
    assert out.result.status == 'completed' and out.checkpoint is None
    assert out.committed_checkpoint.result.times_s[-1] == T(F(p.initial_step_s))


def test_nonlinear_rejections_and_adapted_h_are_not_reset():
    p = replace(policy(), initial_step_s=.1, maximum_step_s=.1,
                relative_tolerance=1e-5, amount_absolute_tolerance_mol=1e-8)
    calls = []
    def nonlinear(state, when):
        calls.append(when)
        return replace(rates(state), reaction_species_mol_s=np.array([[state.amounts_mol[0, 0], 0.], [0., 0.]]))
    baseline = go(p, nonlinear, end=F(.1))
    calls.clear()
    partial = go(p, nonlinear, end=F(.1), pause_after_commit=lambda cp: True)
    assert partial.result.rejected_trials > 0 and partial.checkpoint.next_step_s != F(p.initial_step_s)
    cost = len(calls)
    partial.checkpoint.check()
    assert len(calls) == cost
    final = go(p, nonlinear, end=F(.1), continuation=partial.checkpoint)
    assert _same(numerical_result(final.result), numerical_result(baseline.result))
    assert len(calls) == baseline.result.evaluations


def test_actual_domain_rejection_observation_replays_without_new_operator():
    p = policy()
    calls = []
    def once_domain(state, when):
        calls.append(when)
        if len(calls) == 3:
            raise DomainExit('')
        return rates(state)
    partial = go(p, once_domain, pause_after_commit=lambda cp: True)
    assert partial.result.rejected_trials == 1
    failed = partial.observations[2]
    assert failed.failure_kind == 'DomainExit' and failed.failure_message == '' and failed.rates is None
    before = len(calls)
    partial.checkpoint.check()
    assert len(calls) == before
    out = go(p, once_domain, continuation=partial.checkpoint)
    assert out.result.status == 'completed' and out.result.rejected_trials == 1
    assert _same(out.observations[:before], partial.observations)


def test_exact_large_origin_breakpoint_and_final_tail_selection():
    p = replace(policy(), initial_step_s=.3, maximum_step_s=.3, minimum_step_s=.01)
    origin = F(10**12)
    end = origin + F(1)
    knots = (T(origin + F(3, 10)),)
    def op(state, when):
        return replace(rates(state), reaction_species_mol_s=np.zeros((2, 2)))
    baseline = go(p, op, start=origin, end=end, breakpoints_s=knots)
    partial = go(p, op, start=origin, end=end, breakpoints_s=knots,
                 pause_after_commit=lambda cp: cp.result.times_s[-1] == knots[0])
    assert partial.checkpoint is not None and partial.checkpoint.knot_index == 0
    final = go(p, op, start=origin, end=end, breakpoints_s=knots, continuation=partial.checkpoint)
    assert _same(numerical_result(final.result), numerical_result(baseline.result))
    assert all(type(o.time.seconds) is F for o in final.observations)
    assert final.result.times_s[-1] == T(end)


@pytest.mark.parametrize('mutation', ['h', 'evaluations', 'rejections', 'n_balance', 'u_balance',
                                     'stretch_balance', 'stretch_exact', 'stretch_roundoff',
                                     'component_balance', 'schema', 'observation_role'])
def test_resealed_derived_tampering_is_rejected_before_physics(mutation):
    p = policy()
    cp = go(p, pause_after_commit=lambda x: True).checkpoint
    if mutation == 'h':
        cp = replace(cp, next_step_s=cp.next_step_s / 2)
    elif mutation == 'evaluations':
        cp = replace(cp, result=replace(cp.result, evaluations=cp.result.evaluations - 1))
    elif mutation == 'rejections':
        cp = replace(cp, result=replace(cp.result, rejected_trials=cp.result.rejected_trials + 1))
    elif mutation == 'schema':
        cp = replace(cp, component_schema=None)
    elif mutation == 'observation_role':
        cp = replace(cp, observations=(replace(cp.observations[0], role='accepted'), *cp.observations[1:]))
    else:
        field = {'n_balance':'cumulative_n', 'u_balance':'cumulative_u',
                 'stretch_balance':'cumulative_stretch', 'stretch_exact':'cumulative_stretch_exact',
                 'stretch_roundoff':'cumulative_stretch_roundoff',
                 'component_balance':'cumulative_components'}[mutation]
        row = getattr(cp, field)
        cp = replace(cp, **{field:(row[0] + F(1, 10**20), *row[1:])})
    cp = _seal(cp)
    calls = []
    with pytest.raises(ExactCheckpointError):
        go(p, lambda s, t: (calls.append(t) or rates(s)), continuation=cp)
    assert calls == []


def test_original_problem_and_underlying_exact_clock_types_are_required():
    p = policy()
    cp = go(p, pause_after_commit=lambda x: True).checkpoint
    calls = []
    def op(s, t):
        calls.append(t)
        return rates(s)
    for changes in ({'p':replace(p, maximum_steps=p.maximum_steps + 1)},
                    {'start':F(1)}, {'end':F(1)}, {'state':replace(initial(), internal_energy_j=[11., 20.])}):
        changed = dict(changes)
        arg_policy = changed.pop('p', p)
        with pytest.raises(ExactCheckpointError):
            go(arg_policy, op, continuation=cp, **changed)
    for wrong in (1, True, 0.):
        stamp = T(F())
        object.__setattr__(stamp, 'seconds', wrong)
        with pytest.raises(ExactCheckpointError, match='exact_fraction_time'):
            integrate_exact_checkpointed(initial(), op, start_s=stamp, end_s=T(F(1)), policy=p)
    assert calls == []


@pytest.mark.parametrize('cancel_at', range(1, 9))
def test_immediate_midtrial_cancel_never_grants_resumable_checkpoint(cancel_at):
    p = policy()
    calls = []
    def op(s, t):
        calls.append(t)
        return rates(s)
    out = go(p, op, cancel=lambda: len(calls) >= cancel_at)
    assert out.result.status == 'cancelled' and out.checkpoint is None
    assert out.result.evaluations == len(calls) == len(out.observations) == cancel_at
    assert out.observations[-1].failure_kind == '_Stop'
    assert out.observations[-1].rates is not None
    assert not out.observations[-1].validated


def test_midtrial_cancel_after_commit_retains_full_spent_tail():
    p = policy()
    calls = []
    out = go(p, lambda s, t: (calls.append(t) or rates(s)), cancel=lambda: len(calls) >= 10)
    assert out.checkpoint is None and out.committed_checkpoint is not None
    assert out.result.attempted_trials == 2 and out.result.evaluations == 10
    assert len(out.committed_checkpoint.observations) == 8 and len(out.observations) == 10
    with pytest.raises(ExactCheckpointError, match='clean_boundary_pause'):
        go(p, continuation=out.committed_checkpoint)


def test_observer_failure_preserves_original_exception_and_atomic_commit():
    p = policy()
    failure = RuntimeError('save failed')
    def observer(cp):
        assert cp.result.status == 'running'
        assert cp.elapsed_seconds == cp.result.elapsed_seconds
        raise failure
    out = go(p, on_commit=observer)
    assert out.result.status == 'failed' and out.failure is failure and out.checkpoint is None
    assert len(out.result.steps) == len(out.committed_checkpoint.result.steps) == 1
    assert len(out.observations) == 8


def test_unknown_callback_failure_retains_observation_and_original_exception():
    p = policy()
    failure = RuntimeError('physics seam failed')
    def op(s, t):
        raise failure
    out = go(p, op)
    assert out.result.status == 'failed' and out.failure is failure
    assert out.result.evaluations == 1 and out.observations[0].failure_kind == 'RuntimeError'
    assert out.checkpoint is None


def test_original_step_limit_and_admission_wall_exhaustion_make_zero_physics_calls(monkeypatch):
    p = replace(policy(), maximum_steps=1)
    cp = go(p, pause_after_commit=lambda x: True).checkpoint
    calls = []
    out = go(p, lambda s, t: (calls.append(t) or rates(s)), continuation=cp)
    assert out.result.reason == 'accepted_step_limit' and not calls
    assert _same(out.result.steps, cp.result.steps)
    import sludge_sandbox.exact_integration_checkpoint as module
    ticks = [100.]
    monkeypatch.setattr(module.time, 'monotonic', lambda: ticks[0])
    p = policy()
    cp = go(p, pause_after_commit=lambda x: True).checkpoint
    actual = module._admit
    def slow_admission(*args):
        actual(*args)
        ticks[0] += p.maximum_wall_seconds
    monkeypatch.setattr(module, '_admit', slow_admission)
    out = go(p, lambda s, t: (calls.append(t) or rates(s)), continuation=cp)
    assert out.result.reason == 'wall_time_limit' and not calls
    assert out.result.elapsed_seconds >= cp.elapsed_seconds + p.maximum_wall_seconds


def test_external_reconstruction_time_and_observer_wall_are_charged(monkeypatch):
    import sludge_sandbox.exact_integration_checkpoint as module
    ticks = [100.]
    monkeypatch.setattr(module.time, 'monotonic', lambda: ticks[0])
    p = policy()
    def observer(cp):
        ticks[0] += 1.
    out = go(p, on_commit=observer, pause_after_commit=lambda x: True, admission_elapsed_seconds=2.)
    assert out.checkpoint.elapsed_seconds == 3.
    assert out.result.elapsed_seconds == 3.
    continued = go(p, continuation=out.checkpoint, admission_elapsed_seconds=4.)
    assert continued.result.elapsed_seconds == 7.
    exhausted = go(p, continuation=out.checkpoint, admission_elapsed_seconds=30.)
    assert exhausted.result.reason == 'wall_time_limit' and exhausted.result.evaluations == out.result.evaluations


def test_zero_dry_inventory_is_an_ordinary_valid_segment_not_a_source_prefix_trial():
    p = policy()
    state = ConservedState([[.1, .2], [0., .3], [.4, .5]], [1., 2., 3.])
    def op(s, t):
        return Rates(np.zeros((4, 2)), np.zeros(4), np.zeros((3, 2)), np.zeros(3))
    cp = go(p, op, state=state, pause_after_commit=lambda x: True).checkpoint
    out = go(p, op, state=state, continuation=cp)
    assert out.result.status == 'completed' and _same(out.result.states[-1], state)


def test_legacy_default_full_result_and_actual_callback_sequence_unchanged():
    p = policy()
    calls = []
    direct = integrate_exact(initial(), lambda s, t: (calls.append((s, t)) or rates(s)),
        start_s=T(F()), end_s=T(4 * F(p.initial_step_s)), policy=p)
    checkpointed_calls = []
    other = go(p, lambda s, t: (checkpointed_calls.append((s, t)) or rates(s)))
    assert _same(numerical_result(direct), numerical_result(other.result))
    assert _same(tuple(calls), tuple(checkpointed_calls))


@pytest.mark.parametrize('quantity,reason', [('amount', 'cumulative_amount_roundoff'),
    ('energy', 'cumulative_energy_roundoff'), ('stretch', 'cumulative_stretch_roundoff')])
def test_original_cumulative_roundoff_trap_is_not_reset_at_pause(quantity, reason):
    # Each accepted increment loses exactly 1 under the original 1.5 tolerance;
    # the second step exceeds the original cumulative tolerance, not its local one.
    p = replace(policy(), initial_step_s=1., maximum_step_s=1., minimum_step_s=.5,
                amount_absolute_tolerance_mol=1.5, energy_absolute_tolerance_j=1.5,
                stretch_absolute_tolerance=1.5)
    state = ConservedState([[float(2**53) if quantity == 'amount' else 1.]],
        [float(2**53) if quantity == 'energy' else 0.],
        mechanical_stretches=[float(2**53), 1.] if quantity == 'stretch' else None)
    def op(s, t):
        return Rates(np.zeros((2, 1)), np.zeros(2),
            np.array([[1. if quantity == 'amount' else 0.]]),
            np.array([1. if quantity == 'energy' else 0.]),
            mechanical_rates_per_s=np.array([1., 0.]) if quantity == 'stretch' else None)
    baseline = go(p, op, state=state, end=F(3))
    partial = go(p, op, state=state, end=F(3), pause_after_commit=lambda cp: True)
    assert len(partial.result.steps) == 1 and partial.checkpoint is not None
    continued = go(p, op, state=state, end=F(3), continuation=partial.checkpoint)
    assert continued.result.reason == baseline.result.reason == reason
    assert _same(numerical_result(continued.result), numerical_result(baseline.result))
    # A fresh segment really would lose the original debt; demonstrate the
    # counterexample rather than assuming the resumed fixture is sensitive.
    naive = integrate_exact(partial.result.states[-1], op, start_s=T(F(1)), end_s=T(F(2)), policy=p)
    assert naive.status == 'completed'


def test_absolute_component_budget_does_not_reset_between_prefixes():
    p = replace(policy(), initial_step_s=.25, maximum_step_s=.25, minimum_step_s=.125,
                energy_absolute_tolerance_j=1e-17)
    state = ConservedState([[1.]], [0.])
    def op(s, t):
        return Rates(np.zeros((2, 1)), np.zeros(2), np.zeros((1, 1)), np.array([.5]),
                     {'elastic': np.array([.1]), 'body': np.array([.4])})
    baseline = go(p, op, state=state, end=F(1))
    partial = go(p, op, state=state, end=F(1), pause_after_commit=lambda cp: True)
    delta = abs(F(.125) - F(.025) - F(.1))
    assert partial.checkpoint.cumulative_components == (delta,)
    assert delta <= F(p.energy_absolute_tolerance_j) < 2 * delta
    continued = go(p, op, state=state, end=F(1), continuation=partial.checkpoint)
    assert continued.result.reason == baseline.result.reason == 'cumulative_component_sum_roundoff'
    assert _same(numerical_result(continued.result), numerical_result(baseline.result))


@pytest.mark.parametrize('hook', ['final_observer', 'interior_pause'])
def test_commit_callback_wall_exhaustion_is_not_success_or_resumable_pause(monkeypatch, hook):
    import sludge_sandbox.exact_integration_checkpoint as module
    ticks = [0.]
    monkeypatch.setattr(module.time, 'monotonic', lambda: ticks[0])
    p = replace(policy(), maximum_wall_seconds=1.)
    def callback(cp):
        ticks[0] += 2.
        return True
    kwargs = {'on_commit': callback, 'end': F(p.initial_step_s)} if hook == 'final_observer' else {
        'pause_after_commit': callback}
    out = go(p, **kwargs)
    assert out.result.status == 'resource_limit' and out.result.reason == 'wall_time_limit'
    assert out.result.elapsed_seconds == 2. and len(out.result.steps) == 1
    assert out.checkpoint is None and out.committed_checkpoint is not None


def test_resealed_saved_rates_cannot_forge_derived_component_residual():
    p = policy()
    cp = go(p, pause_after_commit=lambda cp: True).checkpoint
    forged_rates = replace(cp.observations[0].rates)
    object.__setattr__(forged_rates, 'component_sum_residual_w', (F(1), F(1)))
    forged = _seal(replace(cp, observations=(replace(cp.observations[0], rates=forged_rates),
                                           *cp.observations[1:])))
    with pytest.raises(ExactCheckpointError, match='rate_schema'):
        forged.check()


@pytest.mark.parametrize('final', [False, True])
def test_cancel_from_commit_observer_is_honoured_before_pause_or_completion(final):
    p = policy()
    cancelled = [False]
    pause_calls = []
    def observer(cp):
        cancelled[0] = True
    def pause(cp):
        pause_calls.append(cp)
        return True
    kwargs = {'end': F(p.initial_step_s)} if final else {}
    out = go(p, on_commit=observer, pause_after_commit=pause, cancel=lambda: cancelled[0], **kwargs)
    assert out.result.status == 'cancelled' and out.result.reason == 'cancel_requested'
    assert out.checkpoint is None and len(out.result.steps) == 1
    assert out.committed_checkpoint.result.status == 'cancelled'
    assert pause_calls == []


def test_saved_rates_keep_constructor_component_order():
    from types import MappingProxyType
    p = policy()
    cp = go(p, pause_after_commit=lambda cp: True).checkpoint
    changed = []
    for observation in cp.observations:
        rate = replace(observation.rates)
        object.__setattr__(rate, 'cell_power_components_w',
                           MappingProxyType(dict(reversed(tuple(rate.cell_power_components_w.items())))))
        changed.append(replace(observation, rates=rate))
    forged = _seal(replace(cp, observations=tuple(changed), component_schema=tuple(reversed(cp.component_schema))))
    with pytest.raises(ExactCheckpointError, match='rate_schema'):
        forged.check()


@pytest.mark.parametrize('kind', ['DomainExit', '_Reject'])
def test_cancel_callback_exception_after_commit_is_never_a_rejected_trial(kind):
    from sludge_sandbox.integration import _Reject
    p = policy()
    committed = [False]
    failure = {'DomainExit': DomainExit, '_Reject': _Reject}[kind]('post-commit cancel failed')
    def observer(cp):
        committed[0] = True
    def cancel():
        if committed[0]:
            raise failure
        return False
    out = go(p, on_commit=observer, cancel=cancel)
    assert out.result.status == 'failed' and out.failure is failure
    assert out.result.attempted_trials == len(out.result.steps) == 1
    assert out.result.rejected_trials == 0 and out.result.evaluations == 8
    assert out.checkpoint is None and out.committed_checkpoint.result.status == 'failed'
