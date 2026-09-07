"""Preregistered no-EOS source/contract faults at event acceptance."""
from dataclasses import replace
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState, Rates
from sludge_sandbox.water_properties import WaterSourceError
from test_depletion_spine import candidate, configured, oracle, initial, plain, check_costs


def assert_no_trial_commit(out):
    assert not out.events and not out.corrections
    assert out.roundoff_totals.events == 0
    assert out.roundoff_totals.signed_storage_roundoff_mol == 0
    assert out.roundoff_totals.absolute_storage_roundoff_mol == 0
    assert out.roundoff_totals.numerical_phase_correction_mol == 0
    assert out.operator.interfaces == ('existing_liquid',)
    assert all(state.amounts_mol[0, 0] > 0 for state in out.states)
    assert out.reuse_counts['observations'] > 0
    check_costs(out)


@pytest.mark.parametrize('descriptor', ['source_ids', 'deterministic_contract'])
@pytest.mark.parametrize('terminal_offset', [-1, 0])
def test_original_source_contract_mutation_cannot_commit_stale_trial(monkeypatch, descriptor, terminal_offset):
    policy, event = configured()
    original_switch = candidate.ManufacturedDepletionAdapter.with_depleted_cells

    def execute(fault_switch=None):
        operator, calls = oracle(0.)
        switches = []

        def switch(self, state, cells):
            switched = original_switch(self, state, cells)
            switches.append(float(state.amounts_mol[0, 2]))
            if len(switches) == fault_switch:
                # Fault occurs after creating the new terminal operator,
                # which still carries its previous source declaration.
                object.__setattr__(operator, descriptor, ('injected:changed-during-localization',))
            return switched

        with monkeypatch.context() as patch:
            patch.setattr(candidate.ManufacturedDepletionAdapter, 'with_depleted_cells', switch)
            out = candidate.integrate_depletion(initial(), operator, start_s=0., end_s=.2,
                integration_policy=policy, event_policy=event)
        return out, calls, switches

    # This baseline schedules the fault at an actual terminal transition;
    # it supplies no numerical truth or looser acceptance criterion.
    baseline, _, baseline_switches = execute()
    assert baseline.status == 'completed', baseline.reason
    assert baseline.refinements[-1].status == 'independent_approach_pass'
    assert len(baseline_switches) >= 3
    fault_switch = len(baseline_switches)+terminal_offset
    out, calls, switches = execute(fault_switch)
    assert len(switches) >= fault_switch, (out.status, out.reason, fault_switch)
    assert out.status == 'failed', (out.status, out.reason, fault_switch)
    assert 'binding' in out.reason or 'identity' in out.reason
    assert_no_trial_commit(out)
    assert calls['calls'] == out.evaluations


def test_fresh_terminal_source_failure_after_reuse_rolls_back(monkeypatch):
    policy, event = configured()
    original_operator, calls = oracle(0.)
    ordinary_callback = original_operator.evaluate_callback
    switches = {'count': 0, 'faults': 0}
    original_switch = candidate.ManufacturedDepletionAdapter.with_depleted_cells

    def switch(self, state, cells):
        switched = original_switch(self, state, cells)
        switches['count'] += 1
        return switched

    def checked(state, t, modes):
        if switches['count'] == 3 and modes[0] == 'depleted_no_nucleation':
            switches['faults'] += 1
            raise WaterSourceError('manufactured_fresh_terminal_source_guard_failed')
        return ordinary_callback(state, t, modes)

    monkeypatch.setattr(candidate.ManufacturedDepletionAdapter, 'with_depleted_cells', switch)
    operator = replace(original_operator, evaluate_callback=checked)
    out = candidate.integrate_depletion(initial(), operator, start_s=0., end_s=.2,
        integration_policy=policy, event_policy=event)
    assert switches == {'count': 3, 'faults': 1}
    assert out.status == 'failed'
    assert out.reason == 'manufactured_fresh_terminal_source_guard_failed'
    assert_no_trial_commit(out)
    # The failed actual observation is counted even before the fixture's
    # successful callback counter is incremented.
    assert out.evaluations == calls['calls']+1


def test_nested_simultaneous_events_keep_original_unsupported_state():
    policy, event = configured()

    def evaluate(state, t, modes):
        sinks = tuple(.001 if mode == 'existing_liquid' else 0. for mode in modes)
        rates = Rates(np.zeros((3, 2)), np.zeros(3), [[-sink, sink] for sink in sinks], [0., 0.])
        return candidate.DepletionEvaluation(rates, sinks, (300., 300.), (0., 0.), (1e5, 1e5), (0., 0.))

    operator = candidate.ManufacturedDepletionAdapter(evaluate_callback=evaluate,
        liquid_index=0, water_vapor_index=1, interfaces=('existing_liquid', 'existing_liquid'),
        program_knots_s=(), source_ids=('manufactured:simultaneous-spine-source-guard',),
        deterministic_contract=('same-input-same-output:simultaneous-v1',))
    state = ConservedState([[1e-4, 0.], [1e-4, 0.]], [600., 600.])
    out = candidate.integrate_depletion(state, operator, start_s=0., end_s=.2,
        integration_policy=policy, event_policy=event)
    assert out.status == 'unsupported' and out.reason == 'simultaneous_events_not_separated'
    assert plain(out.states) == plain((state,))
    assert not out.steps and not out.events and not out.corrections
    assert out.operator.interfaces == operator.interfaces
    assert out.roundoff_totals.events == 0
    check_costs(out)
