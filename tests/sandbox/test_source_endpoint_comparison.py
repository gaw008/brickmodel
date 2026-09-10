"""Actual source trials with manufactured water; event gates remain distinct."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from test_depletion_integration import policies
from test_source_prefix_trial import fixture, run, POLICY
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.integration import DomainExit
from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
from sludge_sandbox.source_endpoint_comparison import (
    compare_source_trial_endpoints, measure_source_endpoint_pair,
)


@pytest.fixture(scope='module')
def actual_trials():
    trials = []
    for count in (1, 3):
        with pytest.MonkeyPatch.context() as patch:
            adapter, state = fixture(patch, count)
            trial = run(adapter, state)
            assert trial.status == 'validated_positive_numerical_trial', trial.reason
            trials.append(trial)
    with pytest.MonkeyPatch.context() as patch:
        from test_programmed_source_wet_column import setup as furnace_setup
        from test_source_liquid_column import config
        column, states = furnace_setup(patch, count=3)
        column = replace(column, base=replace(column.base, liquid_transport=config(3)))
        adapter = ExactSourceColumn(column)
        trial = run(adapter, adapter.pack(states))
        assert trial.status == 'validated_positive_numerical_trial', trial.reason
        trials.append(trial)
    return tuple(trials)


def test_real_same_endpoints_exact_bounds_and_no_new_physics(actual_trials, monkeypatch):
    def forbidden(*args):
        pytest.fail('endpoint comparison evaluated source physics')
    monkeypatch.setattr(ExactSourceColumn, 'evaluate', forbidden)
    for trial in actual_trials:
        result = compare_source_trial_endpoints(trial, event_policy=policies()[1])
        data = result.differences
        assert data.comparison_time_offset_s == F()
        for i, (a, b) in enumerate(zip(trial.captures[2].evaluation.source_evaluation.cells,
                                      trial.captures[-1].evaluation.source_evaluation.cells)):
            ia, ib = a.inverse, b.inverse
            assert data.temperature_bounds_k[i] == (
                abs(F(ia.point.temperature_k)-F(ib.point.temperature_k))
                + F(ia.temperature_error_bound_k)+F(ib.temperature_error_bound_k))
            assert data.reported_pressure_bounds_pa[i] == (
                abs(F(ia.point.pressure_pa)-F(ib.point.pressure_pa))
                + F(ia.point.pressure_error_pa)+F(ib.point.pressure_error_pa))
        assert result.full_inverse_pressure_gate == 'unresolved'
        assert result.event_time_gate == 'not_evaluated'
        assert result.event_admitted is False and result.material_qualified is False
        result.check()


def test_missing_explicit_event_policy_retains_actual_differences(actual_trials):
    result = compare_source_trial_endpoints(actual_trials[1], event_policy=None)
    assert result.status == 'missing_explicit_event_policy'
    assert result.gates == (None,)*4 and result.event_policy is None
    assert len(result.differences.amount_differences_mol) == 3
    result.check()


@pytest.mark.parametrize('index,field', enumerate((
    'amount_absolute_mol', 'energy_absolute_j',
    'temperature_absolute_k', 'pressure_absolute_pa')))
def test_each_event_gate_cannot_be_replaced_by_normalized_D(actual_trials, index, field):
    trial = actual_trials[2]
    original = compare_source_trial_endpoints(trial, event_policy=policies()[1])
    maximum = original.differences.maxima[index]
    assert maximum > 0 and trial.discrepancy <= 1
    # Deliberately manufactured test tolerances, not a declared material policy.
    limits = dict(zip(('amount_absolute_mol','energy_absolute_j',
                      'temperature_absolute_k','pressure_absolute_pa'),
                     (max(1.,float(v)*2) for v in original.differences.maxima)))
    limits[field] = float(maximum/2)
    result = compare_source_trial_endpoints(trial, event_policy=replace(policies()[1], **limits))
    assert result.gates == tuple(i != index for i in range(4))
    assert result.status == 'endpoint_tolerance_not_certified'


def test_loose_reported_gates_do_not_admit_event(actual_trials):
    policy = replace(policies()[1], amount_absolute_mol=1., energy_absolute_j=1.,
                     temperature_absolute_k=1., pressure_absolute_pa=1e6)
    result = compare_source_trial_endpoints(actual_trials[1], event_policy=policy)
    assert result.gates == (True,)*4
    assert result.status == 'reported_endpoint_gates_satisfied'
    assert result.event_admitted is False and result.full_inverse_pressure_gate == 'unresolved'


def test_policy_nested_copy_and_later_mutation_detected(actual_trials):
    policy = policies()[1]
    result = compare_source_trial_endpoints(actual_trials[0], event_policy=policy)
    object.__setattr__(policy.roundoff_policy, 'storage_absolute_mol', 1.)
    object.__setattr__(policy, 'temperature_absolute_k', 1.)
    assert result.event_policy.roundoff_policy.storage_absolute_mol == 1e-15
    assert result.event_policy.temperature_absolute_k == 1e-5
    result.check()
    object.__setattr__(result.event_policy.roundoff_policy, 'storage_absolute_mol', 2.)
    with pytest.raises(ValueError, match='policy_binding'):
        result.check()


@pytest.mark.parametrize('change', ('negative_roundoff','nan_nested'))
def test_invalid_nested_policy_rejected(actual_trials, change):
    from sludge_sandbox.depletion_integration import NestedApproachPolicy
    policy = replace(policies()[1], nested_approach=NestedApproachPolicy(maximum_step_s=.01))
    target, field, value = ((policy.roundoff_policy, 'storage_absolute_mol', -1.)
                            if change == 'negative_roundoff' else
                            (policy.nested_approach, 'maximum_step_s', float('nan')))
    object.__setattr__(target, field, value)
    with pytest.raises(ValueError):
        compare_source_trial_endpoints(actual_trials[0], event_policy=policy)


def test_changed_result_and_measurement_rejected(actual_trials):
    result = compare_source_trial_endpoints(actual_trials[1], event_policy=policies()[1])
    for changed in (replace(result, event_admitted=True), replace(result, gates=(True,)*4),
                    replace(result, full_inverse_pressure_gate='passed'),
                    replace(result, differences=replace(result.differences, maxima=(F(),)*4))):
        with pytest.raises(ValueError):
            changed.check()


def test_time_mismatch_rejected_by_passive_measurement(actual_trials):
    from sludge_sandbox.source_net_panel import SavedSourceSample
    trial = actual_trials[0]
    a, b = trial.captures[2], trial.captures[-1]
    with pytest.raises(ValueError, match='same_endpoint'):
        measure_source_endpoint_pair(
            SavedSourceSample(a.state,a.evaluation,a.role),
            SavedSourceSample(b.state,replace(b.evaluation,time=T(F(1))),b.role),
            operator_identity=trial.operator_identity, energy_identity=trial.energy_identity,
            fixed_dry_mass_kg=trial.fixed_dry_mass_kg)


def test_recovered_reference_domain_exit_is_still_usable(monkeypatch):
    adapter, state = fixture(monkeypatch)
    original = ExactSourceColumn.evaluate
    calls = []
    def once(self, state, when):
        calls.append(when)
        if len(calls) == 6:
            raise DomainExit('recoverable_endpoint_test')
        return original(self, state, when)
    monkeypatch.setattr(ExactSourceColumn, 'evaluate', once)
    trial = evaluate_source_prefix_trial(adapter,state,start=T(F()),end=T(F(1,1024)),
        integration_policy=replace(POLICY,initial_step_s=1/1024,maximum_step_s=1/1024,
                                   maximum_wall_seconds=25.),maximum_callbacks=32)
    assert trial.status == 'validated_positive_numerical_trial', trial.reason
    count = len(calls)
    result = compare_source_trial_endpoints(trial,event_policy=policies()[1])
    result.check()
    assert len(calls) == count and trial.reference.rejected_trials > 0


def test_incomplete_reference_cannot_enter_comparison(monkeypatch):
    adapter, state = fixture(monkeypatch)
    trial = evaluate_source_prefix_trial(adapter,state,start=T(F()),end=T(F(1,16384)),
                                        integration_policy=POLICY,maximum_callbacks=4)
    with pytest.raises(ValueError, match='validated_source_trial'):
        compare_source_trial_endpoints(trial,event_policy=policies()[1])
