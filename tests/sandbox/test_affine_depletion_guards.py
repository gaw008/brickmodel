"""Manufactured affine source/cancellation boundaries; no native water calls."""
from dataclasses import replace
import inspect

import pytest

from sludge_sandbox import depletion_integration as model
from test_depletion_integration import policies
from test_depletion_spine import oracle, initial, check_costs


def configuration(mode):
    policy, event = policies()
    nested = None if mode == 'none' else model.NestedApproachPolicy(
        maximum_step_s=.001, reuse_ordinary_spine=mode == 'cached')
    return policy, replace(event, terminal_method='affine_midpoint', nested_approach=nested)


def assert_rollback(result):
    assert not result.events and not result.corrections
    assert result.roundoff_totals.events == 0
    assert result.roundoff_totals.signed_storage_roundoff_mol == 0
    assert result.roundoff_totals.absolute_storage_roundoff_mol == 0
    assert result.roundoff_totals.numerical_phase_correction_mol == 0
    assert result.operator.interfaces == ('existing_liquid',)
    assert all(state.amounts_mol[0, 0] > 0 for state in result.states)
    check_costs(result)


@pytest.mark.parametrize('mode', ['none', 'uncached', 'cached'])
@pytest.mark.parametrize('descriptor', ['source_ids', 'deterministic_contract'])
@pytest.mark.parametrize('boundary', ['switch', 'comparison'])
def test_affine_original_binding_survives_until_commit(monkeypatch, mode, descriptor, boundary):
    policy, event = configuration(mode)
    original_switch = model.ManufacturedDepletionAdapter.with_depleted_cells

    def execute(fault_index=None):
        original, calls = oracle(.002)
        visits = {'switch': 0, 'comparison': 0, 'faults': 0}

        def fault(kind):
            visits[kind] += 1
            if kind == boundary and visits[kind] == fault_index:
                visits['faults'] += 1
                object.__setattr__(operator, descriptor, ('manufactured:changed-at-affine-boundary',))

        def evaluate(state, t, modes):
            result = original.evaluate_callback(state, t, modes)
            # Only the fresh common-time comparison observation, after dry
            # continuation; never an ordinary integration or terminal callback.
            if any(frame.function == 'comparison' for frame in inspect.stack()):
                fault('comparison')
            return result

        operator = replace(original, evaluate_callback=evaluate, program_knots_s=())

        def switch(self, state, cells):
            changed = original_switch(self, state, cells)
            fault('switch')  # returned operator still has the old descriptor
            return changed

        with monkeypatch.context() as patch:
            patch.setattr(model.ManufacturedDepletionAdapter, 'with_depleted_cells', switch)
            result = model.integrate_depletion(initial(), operator, start_s=0., end_s=.2,
                integration_policy=policy, event_policy=event)
        assert calls['calls'] == result.evaluations
        return result, visits

    baseline, visits = execute()
    assert baseline.status == 'completed', baseline.reason
    assert len(baseline.events) == 1 and visits[boundary] > 0
    if mode != 'none':
        assert baseline.refinements[-1].status == 'independent_approach_pass'
    # Locate the actual final boundary using a no-fault run, not a guessed
    # switch count that could miss final precommit handling.
    result, faults = execute(visits[boundary])
    assert faults['faults'] == 1
    assert result.status == 'failed', result.reason
    assert 'binding' in result.reason or 'identity' in result.reason
    assert_rollback(result)


@pytest.mark.parametrize('mode', ['none', 'uncached', 'cached'])
def test_affine_midpoint_cancel_retains_accepted_wet_prefix(mode):
    policy, event = configuration(mode)
    original, calls = oracle(.002)
    triggered = []

    def evaluate(state, t, modes):
        result = original.evaluate_callback(state, t, modes)
        if modes == ('existing_liquid',) and any(
                frame.function == 'affine_terminal' for frame in inspect.stack()):
            triggered.append(t)
        return result

    operator = replace(original, evaluate_callback=evaluate, program_knots_s=())
    result = model.integrate_depletion(initial(), operator, start_s=0., end_s=.2,
        integration_policy=policy, event_policy=event, cancel=lambda: bool(triggered))
    assert len(triggered) == 1
    assert result.status == 'cancelled' and result.reason == 'cancel_requested'
    assert calls['calls'] == result.evaluations
    assert_rollback(result)


@pytest.mark.parametrize('method', ['', None, False, 1, [], {}])
def test_affine_malformed_method_is_rejected(method):
    _, event = policies()
    with pytest.raises(ValueError, match='terminal_method'):
        replace(event, terminal_method=method)
