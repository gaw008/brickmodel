"""Manufactured conservative systems with independent analytic solutions."""
import math

import numpy as np
import pytest

from sludge_sandbox.integration import (
    ConservedState, DomainExit, IntegrationError, IntegrationPolicy, Rates, integrate,
)


def policy(**changes):
    values = dict(initial_step_s=0.1, maximum_step_s=0.2, minimum_step_s=1e-10,
                  relative_tolerance=1e-6, amount_absolute_tolerance_mol=1e-11,
                  energy_absolute_tolerance_j=1e-9, amount_scale_mol=1,
                  energy_scale_j=100, maximum_steps=10000, maximum_rejections=1000,
                  maximum_wall_seconds=20)
    return IntegrationPolicy(**(values | changes))


def zero_rates(state, t):
    cells, species = state.amounts_mol.shape
    return Rates(np.zeros((cells+1, species)), np.zeros(cells+1),
                 np.zeros((cells, species)), np.zeros(cells))


def test_closed_inert_state_and_breakpoints_are_preserved():
    state = ConservedState([[1, 0], [0.5, 0.5]], [100, 200])
    result = integrate(state, zero_rates, start_s=0, end_s=1, policy=policy(), breakpoints_s=(0.31, 0.73))
    assert result.status == "completed"
    assert result.times_s[-1] == 1
    assert 0.31 in result.times_s and 0.73 in result.times_s
    assert np.array_equal(result.states[-1].amounts_mol, state.amounts_mol)
    assert np.array_equal(result.states[-1].internal_energy_j, state.internal_energy_j)


def test_closed_first_order_transfer_matches_exponential_and_has_no_added_heat():
    def reaction(state, t):
        a = state.amounts_mol[0, 0]
        return Rates([[0, 0], [0, 0]], [0, 0], [[-2*a, 2*a]], [0])
    result = integrate(ConservedState([[1, 0]], [100]), reaction,
                       start_s=0, end_s=1, policy=policy())
    assert result.status == "completed"
    assert result.states[-1].amounts_mol[0, 0] == pytest.approx(math.exp(-2), abs=3e-5)
    for state in result.states:
        assert state.amounts_mol.min() >= 0
        assert state.amounts_mol.sum() == pytest.approx(1, abs=1e-12)
        assert state.internal_energy_j[0] == 100


def test_open_boundary_species_and_energy_use_the_same_accepted_step_weights():
    def feed(state, t):
        return Rates([[1+t], [0]], [10*(1+t), 0], [[0]], [0])
    result = integrate(ConservedState([[0]], [0]), feed, start_s=0, end_s=1, policy=policy())
    assert result.status == "completed"
    assert result.states[-1].amounts_mol[0, 0] == pytest.approx(1.5)
    assert result.states[-1].internal_energy_j[0] == pytest.approx(15)
    for before, after, step in zip(result.states, result.states[1:], result.steps):
        assert (after.amounts_mol-before.amounts_mol).sum() == pytest.approx(
            step.face_species_mol[0].sum()-step.face_species_mol[-1].sum(), abs=1e-13)
        assert (after.internal_energy_j-before.internal_energy_j).sum() == pytest.approx(
            step.face_energy_j[0]-step.face_energy_j[-1], abs=1e-12)


def test_internal_face_changes_cells_but_not_closed_system_totals():
    def diffuse(state, t):
        gradient = state.amounts_mol[0, 0]-state.amounts_mol[1, 0]
        return Rates([[0], [gradient], [0]], [0, 10*gradient, 0], [[0], [0]], [0, 0])
    result = integrate(ConservedState([[1], [0]], [100, 100]), diffuse,
                       start_s=0, end_s=1, policy=policy())
    assert result.status == "completed"
    assert result.states[-1].amounts_mol[:, 0] == pytest.approx(
        [0.5+0.5*math.exp(-2), 0.5-0.5*math.exp(-2)], abs=2e-5)
    assert sum(result.states[-1].internal_energy_j) == pytest.approx(200, abs=1e-10)


def test_invalid_operator_cannot_extract_a_species_from_zero_inventory_forever():
    def bad(state, t):
        return Rates([[0], [1]], [0, 0], [[0]], [0])
    result = integrate(ConservedState([[0]], [0]), bad, start_s=0, end_s=1, policy=policy())
    assert result.status == "numerical_failure"
    assert result.reason == "outflow_from_zero_inventory"
    assert result.evaluations == 1
    assert len(result.steps) == 0


def test_cancel_and_budget_preserve_the_last_complete_state():
    state = ConservedState([[1]], [100])
    result = integrate(state, zero_rates, start_s=0, end_s=1, policy=policy(), cancel=lambda: True)
    assert result.status == "cancelled" and result.times_s == (0.0,)
    result = integrate(state, zero_rates, start_s=0, end_s=1, policy=policy(maximum_steps=1))
    assert result.status == "resource_limit" and len(result.steps) == 1


def test_explicit_property_domain_exit_is_distinct_from_numerical_failure():
    def unavailable(state, t):
        raise DomainExit("missing_liquid_property")
    result = integrate(ConservedState([[1]], [100]), unavailable,
                       start_s=0, end_s=1, policy=policy())
    assert result.status == "domain_exit" and result.reason == "missing_liquid_property"


def test_unexpected_callback_bug_is_not_swallowed_as_a_physical_failure():
    def bug(state, t):
        raise KeyError("implementation_bug")
    with pytest.raises(KeyError):
        integrate(ConservedState([[1]], [100]), bug, start_s=0, end_s=1, policy=policy())


@pytest.mark.parametrize("amounts,energy", [([[True, 1]], [1]), ([[-1]], [1]), ([[1]], [float("nan")])])
def test_invalid_state_rejected(amounts, energy):
    with pytest.raises(IntegrationError):
        ConservedState(amounts, energy)


def test_states_cannot_be_changed_by_mutating_input_or_reenabling_array_writes():
    a = np.array([[1.0]])
    state = ConservedState(a, [100])
    a[0, 0] = 2
    assert state.amounts_mol[0, 0] == 1
    with pytest.raises(ValueError):
        state.amounts_mol.setflags(write=True)


def test_balanced_large_throughflow_does_not_erase_small_stored_inventory():
    def through(state, t):
        return Rates([[1e20], [1e20]], [1e20, 1e20], [[0]], [0])
    result = integrate(ConservedState([[1]], [1]), through, start_s=0, end_s=1,
                       policy=policy(initial_step_s=1, maximum_step_s=1))
    assert result.status == "completed"
    assert result.states[-1].amounts_mol[0, 0] == 1
    assert result.states[-1].internal_energy_j[0] == 1


def test_energy_roundoff_cannot_silently_discard_a_resolved_heat_input():
    def heater(state, t):
        return Rates([[0], [0]], [0, 0], [[0]], [1])
    result = integrate(ConservedState([[1]], [1e20]), heater, start_s=0, end_s=1,
                       policy=policy(initial_step_s=1, maximum_step_s=1, energy_scale_j=1))
    assert result.status == "numerical_failure"
    assert result.reason == "unresolvable_energy_increment"
    assert not result.steps


def test_two_half_steps_must_meet_the_combined_exchange_tolerance():
    def heater(state, t):
        return Rates([[0], [0]], [0, 0], [[0]], [2.8*2**-30])
    result = integrate(ConservedState([[1]], [1e7]), heater, start_s=0, end_s=1,
                       policy=policy(initial_step_s=1, maximum_step_s=1))
    assert result.status == 'numerical_failure'
    assert result.reason == 'unresolvable_energy_increment'
    assert not result.steps


def test_small_stepwise_roundoff_cannot_accumulate_past_the_run_budget():
    def heater(state, t):
        return Rates([[0], [0]], [0, 0], [[0]], [3])
    result = integrate(ConservedState([[1]], [1e16]), heater, start_s=0, end_s=100,
                       policy=policy(initial_step_s=1, maximum_step_s=1,
                                     energy_absolute_tolerance_j=1.1))
    assert result.status == 'numerical_failure'
    assert result.reason == 'cumulative_energy_roundoff'
    assert len(result.steps) == 1


@pytest.mark.parametrize('start,end', [(0., math.ulp(0.)), (1e16, 1e16+2)])
def test_unrepresentable_half_step_time_cannot_report_completion(start, end):
    width = end-start
    result = integrate(ConservedState([[1]], [0]), zero_rates, start_s=start, end_s=end,
                       policy=policy(initial_step_s=width, maximum_step_s=width, minimum_step_s=width))
    assert result.status == 'numerical_failure'
    assert result.reason == 'unresolvable_stage_time'
    assert not result.steps


@pytest.mark.parametrize('start,end,h', [(1e12, 1e12+1, .1), (1e16, 1e16+6, 6),
                                      (0, 2, .01), (0, 10, .1), (2000, 2001, .01)])
def test_actual_stage_endpoints_define_integrated_duration(start, end, h):
    seen = []
    def inflow(state, t):
        seen.append(t)
        return Rates([[1], [0]], [1, 0], [[0]], [0])
    result = integrate(ConservedState([[1]], [0]), inflow, start_s=start, end_s=end,
                       policy=policy(initial_step_s=h, maximum_step_s=h))
    assert min(seen) >= start and max(seen) <= end
    assert result.status == 'completed', result.reason
    assert math.fsum(s.face_species_mol[0, 0] for s in result.steps) == pytest.approx(end-start, abs=1e-12)


def test_rejected_step_must_reduce_its_represented_endpoint():
    start = 1e16
    def heating(state, t):
        return Rates([[0], [0]], [0, 0], [[0]], [(t-start)**2])
    result = integrate(ConservedState([[1]], [0]), heating, start_s=start, end_s=start+6,
                       policy=policy(initial_step_s=6, maximum_step_s=6, maximum_rejections=10,
                                     energy_absolute_tolerance_j=11.9, energy_scale_j=1))
    assert result.status == 'numerical_failure'
    assert result.reason == 'unresolvable_stage_time'
    assert result.rejected_trials < 10


@pytest.mark.parametrize("end,step,minimum", [(1, 0.1, 1e-10), (0.15, 0.1, 0.06)])
def test_final_clipped_interval_is_actually_integrated_below_adaptive_minimum(end, step, minimum):
    def inflow(state, t):
        return Rates([[1], [0]], [1, 0], [[0]], [0])
    result = integrate(ConservedState([[1]], [100]), inflow, start_s=0, end_s=end,
                       policy=policy(initial_step_s=step, maximum_step_s=step, minimum_step_s=minimum))
    assert result.status == "completed" and result.times_s[-1] == end
    assert result.states[-1].amounts_mol[0, 0] == pytest.approx(1+end)
    assert math.fsum(s.face_species_mol[0, 0] for s in result.steps) == pytest.approx(end)


@pytest.mark.parametrize("stop", ["cancel", "wall"])
def test_final_callback_cannot_commit_after_cancellation_or_expired_budget(monkeypatch, stop):
    import sludge_sandbox.integration as module
    clock = [0.0]
    cancelled = [False]
    count = [0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    def late(state, t):
        count[0] += 1
        if count[0] == 8:
            if stop == "cancel":
                cancelled[0] = True
            else:
                clock[0] = 2
        return zero_rates(state, t)
    result = integrate(ConservedState([[1]], [100]), late, start_s=0, end_s=1,
                       policy=policy(initial_step_s=1, maximum_step_s=1, maximum_wall_seconds=1),
                       cancel=lambda: cancelled[0])
    assert result.status == ("cancelled" if stop == "cancel" else "resource_limit")
    assert not result.steps and result.times_s == (0.0,)
