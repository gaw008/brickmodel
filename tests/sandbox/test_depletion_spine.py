"""Independent numerical oracles for nested wet approach; never native EOS."""
from dataclasses import fields, is_dataclass, replace
from decimal import Decimal, localcontext
from fractions import Fraction
import math

import numpy as np
import pytest

from sludge_sandbox.integration import ConservedState, Rates
from test_depletion_integration import policies

from sludge_sandbox import depletion_integration as candidate


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Fraction):
        return (value.numerator, value.denominator)
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict) or hasattr(value, 'items'):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def configured(*, reuse=True):
    integration, old = policies()
    event = candidate.DepletionPolicy(**({f.name: getattr(old, f.name) for f in fields(old)} | {
        "nested_approach": candidate.NestedApproachPolicy(maximum_step_s=.001, reuse_ordinary_spine=reuse)}))
    return integration, event


def oracle(b, *, deterministic=True):
    counter = {'calls': 0}

    def evaluate(state, t, modes):
        counter['calls'] += 1
        sink = .001+b*t if modes[0] == 'existing_liquid' else 0.
        extent = .1*float(state.amounts_mol[0, 2])
        power = .3 if modes[0] == 'existing_liquid' else 2.
        rates = Rates(np.zeros((2, 4)), np.zeros(2),
            np.array([[-sink, sink, -extent, extent]]), np.array([power]),
            cell_power_components_w={'elastic': [.1], 'pore': [-.1], 'body': [power]})
        return candidate.DepletionEvaluation(rates, (sink,),
            (float(state.internal_energy_j[0])/2,), (0.,), (0.,), (0.,))

    op = candidate.ManufacturedDepletionAdapter(evaluate_callback=evaluate,
        liquid_index=0, water_vapor_index=1, interfaces=('existing_liquid',),
        program_knots_s=(.05, .15), source_ids=('manufactured:independent-spine-v1',),
        deterministic_contract=('same-input-same-output:v1',) if deterministic else ())
    return op, counter


def initial():
    return ConservedState([[1e-4, 0., 2., 0.]], [600.],
        energy_model_identity=('manufactured-spine-total-energy', '1'))


def run(b, *, reuse=True, deterministic=True, cancel=None, maximum_steps=None):
    policy, event = configured(reuse=reuse)
    if maximum_steps is not None:
        policy = replace(policy, maximum_steps=maximum_steps)
    op, counter = oracle(b, deterministic=deterministic)
    result = candidate.integrate_depletion(initial(), op, start_s=0., end_s=.2,
        integration_policy=policy, event_policy=event, cancel=cancel)
    return result, counter


def exact_event(b):
    with localcontext() as ctx:
        ctx.prec = 70
        a, slope, n = map(Decimal.from_float, (.001, b, 1e-4))
        return float(n/a if not b else 2*n/(a+(a*a+2*slope*n).sqrt()))


def audit(result, b):
    assert result.status == 'completed', result.reason
    assert len(result.events) == 1
    assert abs(result.events[0].time_s-exact_event(b)) <= 1e-7
    assert result.times_s[-1] == .2
    assert result.operator.interfaces == ('depleted_no_nucleation',)
    assert result.states[-1].amounts_mol[0, 0] == 0.
    assert abs(result.states[-1].internal_energy_j[0]-(600+.3*exact_event(b)+2*(.2-exact_event(b)))) <= 1e-6
    accumulated = Fraction()
    for t, state, ledger in zip(result.times_s[1:], result.states[1:], result.steps, strict=True):
        assert state.energy_model_identity == initial().energy_model_identity
        row = state.amounts_mol[0]
        assert abs(Fraction(float(row[0]))+Fraction(float(row[1]))-Fraction(1e-4)) <= Fraction(1e-12)
        assert abs(Fraction(float(row[2]))+Fraction(float(row[3]))-2) <= Fraction(1e-12)
        assert abs(row[2]-2*math.exp(-.1*t)) <= 1e-7
        assert np.all(ledger.face_species_mol == 0) and np.all(ledger.face_energy_j == 0)
        parts = sum((Fraction(float(v[0])) for v in ledger.cell_work_components_j.values()), Fraction())
        assert parts+ledger.component_sum_residual_j[0] == Fraction(float(ledger.cell_work_j[0]))
        accumulated += Fraction(float(ledger.cell_work_j[0]))
        assert abs(Fraction(float(state.internal_energy_j[0]))-600-accumulated) <= Fraction(1e-8)


@pytest.mark.parametrize('b', [0., .002])
def test_nested_cached_and_uncached_match_independent_oracles(b):
    cached, cached_calls = run(b, reuse=True)
    uncached, uncached_calls = run(b, reuse=False)
    audit(cached, b)
    audit(uncached, b)
    for field in ('times_s', 'states', 'steps', 'events', 'corrections', 'roundoff_totals',
                  'cumulative_amounts_mol', 'cumulative_energy_j', 'cumulative_absolute_component_residual_j'):
        assert plain(getattr(cached, field)) == plain(getattr(uncached, field)), field
    assert cached_calls['calls'] == cached.evaluations
    assert uncached_calls['calls'] == uncached.evaluations
    assert cached_calls['calls'] < uncached_calls['calls']


def test_immediate_cancel_has_no_committed_or_speculative_event():
    out, calls = run(.002, cancel=lambda: True)
    assert out.status == 'cancelled'
    assert not out.steps and not out.events and not out.corrections
    assert plain(out.states) == plain((initial(),))
    assert calls['calls'] == 0


def test_attempt_limit_keeps_only_committed_positive_wet_prefix():
    out, _ = run(.002, maximum_steps=2)
    assert out.status == 'resource_limit'
    assert not out.events and not out.corrections
    assert out.operator.interfaces == ('existing_liquid',)
    assert all(state.amounts_mol[0, 0] > 0 for state in out.states)


def test_reuse_rejects_missing_deterministic_contract():
    with pytest.raises(candidate.DepletionIntegrationError, match='determin'):
        run(.002, deterministic=False)


def check_costs(out):
    for cost, attr in [('evaluations', 'evaluations'), ('panels', 'attempted_steps'),
                       ('rejections', 'rejected_trials')]:
        actual = sum(phase[cost] for phase in out.phase_costs.values())
        assert actual == getattr(out, attr)
        recorded = sum(phase[cost] for row in out.refinements for phase in row.phase_costs.values())
        assert recorded <= actual


def test_diagnostics_detached_and_actual_costs():
    out, _ = run(.002)
    check_costs(out)
    assert out.reuse_counts['panels'] > 0
    with pytest.raises(TypeError):
        out.phase_costs['approach']['evaluations'] = -1
    comparisons = [row for row in out.refinements if row.comparison_details]
    assert comparisons[-1].status == 'independent_approach_pass'
    assert comparisons[-1].comparison_details['approach_grid_a_s'] != comparisons[-1].comparison_details['approach_grid_b_s']
    with pytest.raises(TypeError):
        comparisons[-1].comparison_details['event_amounts']['maximum'] = 0


@pytest.mark.parametrize('test_name', [
    'test_two_separated_events_inside_original_preview_horizon',
    'test_two_event_full_physical_and_correction_prefix',
    'test_accelerating_second_event_replans_common_time_after_first_switch',
    'test_horizon_restart_discards_all_old_comparisons_and_charges_cost',
    'test_resource_failure_after_horizon_restart_does_not_commit_trial_modes',
])
def test_nested_multicell_existing_analytic_and_rollback_contracts(monkeypatch, test_name):
    import test_depletion_multicell as old

    def wrapped(state, op, **kwargs):
        op = candidate.ManufacturedDepletionAdapter(**({f.name: getattr(op, f.name) for f in fields(op)} | {
            'deterministic_contract': ('same-input-same-output:multicell-v1',)}))
        previous = kwargs.pop('event_policy')
        event = candidate.DepletionPolicy(**({f.name: getattr(previous, f.name) for f in fields(previous)} | {
            "nested_approach": candidate.NestedApproachPolicy(maximum_step_s=.001, reuse_ordinary_spine=True)}))
        out = candidate.integrate_depletion(state, op, event_policy=event, **kwargs)
        check_costs(out)
        return out

    monkeypatch.setattr(old, 'DepletionEvaluation', candidate.DepletionEvaluation)
    monkeypatch.setattr(old, 'integrate_depletion', wrapped)
    getattr(old, test_name)()


def test_mutable_observation_buffer_has_value_semantics():
    def one(reuse):
        p, e = configured(reuse=reuse)
        op, _ = oracle(.002)
        original = op.evaluate_callback
        buffers = [[0.] for _ in range(5)]

        def shared(state, t, modes):
            value = original(state, t, modes)
            for buf, name in zip(buffers, ('evaporation_mol_s', 'temperatures_k', 'temperature_errors_k',
                                         'pressures_pa', 'pressure_errors_pa'), strict=True):
                buf[:] = getattr(value, name)
            return candidate.DepletionEvaluation(value.rates, *buffers)

        op = replace(op, evaluate_callback=shared)
        return candidate.integrate_depletion(initial(), op, start_s=0, end_s=.2,
            integration_policy=p, event_policy=e)

    cached, uncached = one(True), one(False)
    audit(cached, .002)
    audit(uncached, .002)
    for name in ('times_s', 'states', 'steps', 'events', 'corrections', 'roundoff_totals'):
        assert plain(getattr(cached, name)) == plain(getattr(uncached, name))


def biased_run(*, cancel=None):
    p, e = configured()
    p = replace(p, relative_tolerance=1e-2, amount_absolute_tolerance_mol=1e-5)
    e = replace(e, maximum_refinements=20)
    op, counter = oracle(0.)
    original = op.evaluate_callback

    def accelerated(state, t, modes):
        value = original(state, t, modes)
        n = np.array(value.rates.reaction_species_mol_s)
        n[0, 2] = -100*float(state.amounts_mol[0, 2])
        n[0, 3] = -n[0, 2]
        return replace(value, rates=replace(value.rates, reaction_species_mol_s=n))

    op = replace(op, evaluate_callback=accelerated, program_knots_s=())
    state = ConservedState([[1e-6, 0., 2., 0.]], [600.], energy_model_identity=initial().energy_model_identity)
    out = candidate.integrate_depletion(state, op, start_s=0., end_s=.01,
        integration_policy=p, event_policy=e, cancel=(lambda: counter['calls'] >= cancel) if cancel else None)
    return out, counter


def test_independent_approach_rejects_shared_bias_without_commit():
    out, count = biased_run()
    assert out.reason == 'independent_approach_comparison_failed', (out.status, out.reason)
    assert sum(row.status == 'comparison_pass' for row in out.refinements) >= 2
    assert out.status == 'unsupported'
    assert out.reuse_counts['panels'] > 0
    assert not out.events and not out.corrections and out.roundoff_totals.events == 0
    assert out.operator.interfaces == ('existing_liquid',)
    assert out.states[-1].amounts_mol[0, 0] > 0
    assert count['calls'] == out.evaluations
    check_costs(out)


def test_cancel_after_reuse_does_not_commit_speculative_branch():
    baseline, calls = biased_run()
    out, _ = biased_run(cancel=max(1, calls['calls']//2))
    assert out.status == 'cancelled', out.reason
    assert out.reuse_counts['observations'] > 0
    assert not out.events and not out.corrections and out.roundoff_totals.events == 0
    assert out.operator.interfaces == ('existing_liquid',)
    assert out.states[-1].amounts_mol[0, 0] > 0
    check_costs(out)
