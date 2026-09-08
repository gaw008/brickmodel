"""Manufactured scheduling regressions with independent constant-source oracles."""
from dataclasses import fields, is_dataclass, replace
from collections.abc import Mapping
from fractions import Fraction
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sludge_sandbox.depletion_integration import (
    DepletionEvaluation, ManufacturedDepletionAdapter, integrate_depletion,
)
from sludge_sandbox.integration import ConservedState, Rates, integrate
from test_depletion_integration import policies


def _encoded(value: Any) -> Any:
    if isinstance(value, Fraction):
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if is_dataclass(value):
        return {field.name: _encoded(getattr(value, field.name)) for field in fields(value) if field.name != 'operator'}
    if isinstance(value, Mapping):
        return {key: _encoded(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_encoded(item) for item in value]
    return value


def _save(label: str, result: Any, evaluations: list[float]) -> None:
    directory = os.environ.get('BRICK_KNOT_EVIDENCE_DIR')
    if directory is None:
        return
    target = Path(directory)/f'{label}.json'
    record = {'result': _encoded(result), 'accepted_times_hex': [t.hex() for t in result.times_s],
              'callback_times_hex': [t.hex() for t in evaluations],
              'last_time_hex': result.times_s[-1].hex(), 'knot_hex': .05.hex(),
              'last_time_next_float_hex': math.nextafter(result.times_s[-1], math.inf).hex(),
              'remaining_to_knot_exact_s': str(Fraction(.05)-Fraction(result.times_s[-1]))}
    with target.open('x') as output:
        json.dump(record, output, indent=2, allow_nan=False)
        output.write('\n')


def _adapter(evaluations: list[float], *, knots: tuple[float, ...] = (.05,), sink: float = .001,
             power: float = 2.) -> ManufacturedDepletionAdapter:
    def callback(state: ConservedState, time_s: float, modes: tuple[str, ...]) -> DepletionEvaluation:
        evaluations.append(time_s)
        assert modes == ('existing_liquid',)
        rates = Rates(np.zeros((2, 2)), np.zeros(2), np.array([[-sink, sink]]), np.array([power]))
        return DepletionEvaluation(rates, (sink,), (float(state.internal_energy_j[0])/2,), (0.,), (0.,), (0.,))
    return ManufacturedDepletionAdapter(evaluate_callback=callback, liquid_index=0, water_vapor_index=1,
        interfaces=('existing_liquid',), program_knots_s=knots,
        source_ids=('manufactured:constant-wet-program-knot',))


def _run(label: str, *, step: float = .005, start: float = 0., end: float = .06,
         knots: tuple[float, ...] = (.05,), cancel: Any = None, initial: ConservedState | None = None,
         sink: float = .001, power: float = 2., minimum_step: float = 1e-14) -> Any:
    policy, event = policies()
    policy = replace(policy, initial_step_s=step, maximum_step_s=step, minimum_step_s=minimum_step, maximum_wall_seconds=10.)
    state = initial if initial is not None else ConservedState([[1., 0.]], [600.])
    evaluations: list[float] = []
    out = integrate_depletion(state, _adapter(evaluations, knots=knots, sink=sink, power=power),
        start_s=start, end_s=end, integration_policy=policy, event_policy=event, cancel=cancel)
    _save(label, out, evaluations)
    return out


def _prefix_oracle(out: Any, *, start: float = 0., initial: ConservedState | None = None,
                   sink: float = .001, power: float = 2., knot: float | None = .05) -> None:
    state0 = initial if initial is not None else ConservedState([[1., 0.]], [600.])
    assert len(out.states) == len(out.times_s) == len(out.steps)+1
    assert not getattr(out, 'events', ())
    for left, right in zip(out.times_s, out.times_s[1:]):
        assert left < right
        if knot is not None:
            assert not left < knot < right
    for at, state in zip(out.times_s, out.states):
        duration = Fraction(at)-Fraction(start)
        expected_liquid = Fraction(float(state0.amounts_mol[0, 0]))-duration*Fraction(sink)
        expected_vapor = Fraction(float(state0.amounts_mol[0, 1]))+duration*Fraction(sink)
        expected_energy = Fraction(float(state0.internal_energy_j[0]))+duration*Fraction(power)
        assert abs(Fraction(float(state.amounts_mol[0, 0]))-expected_liquid) <= Fraction(1e-12)
        assert abs(Fraction(float(state.amounts_mol[0, 1]))-expected_vapor) <= Fraction(1e-12)
        assert abs(Fraction(float(state.internal_energy_j[0]))-expected_energy) <= Fraction(1e-8)
    for index, ledger in enumerate(out.steps):
        duration = Fraction(out.times_s[index+1])-Fraction(out.times_s[index])
        assert np.all(ledger.face_species_mol == 0) and np.all(ledger.face_energy_j == 0)
        assert abs(Fraction(float(ledger.reaction_species_mol[0, 0]))+duration*Fraction(sink)) <= Fraction(1e-15)
        assert abs(Fraction(float(ledger.reaction_species_mol[0, 1]))-duration*Fraction(sink)) <= Fraction(1e-15)
        assert abs(Fraction(float(ledger.cell_work_j[0]))-duration*Fraction(power)) <= Fraction(1e-12)


def test_decimal_step_integrates_complete_interval_through_program_knot() -> None:
    out = _run('decimal-knot')
    _prefix_oracle(out)
    assert out.status == 'completed', (out.status, out.reason, out.times_s[-1].hex())
    assert out.times_s[-1] == .06 and out.times_s.count(.05) == 1


def test_dyadic_step_control_has_complete_conserved_knot_path() -> None:
    out = _run('dyadic-knot', step=1/256)
    _prefix_oracle(out)
    assert out.status == 'completed', out.reason
    assert out.times_s[-1] == .06 and out.times_s.count(.05) == 1


def test_standalone_ordinary_clock_control() -> None:
    policy, _ = policies()
    policy = replace(policy, initial_step_s=.005, maximum_step_s=.005, maximum_wall_seconds=10.)
    evaluations: list[float] = []
    operator = _adapter(evaluations)
    out = integrate(ConservedState([[1., 0.]], [600.]), operator, start_s=0., end_s=.06,
                    policy=policy, breakpoints_s=(.05,))
    _save('standalone-knot', out, evaluations)
    _prefix_oracle(out)
    assert out.status == 'completed' and out.times_s[-1] == .06
    assert out.times_s.count(.05) == 1


def test_resolvable_small_interval_is_actually_integrated() -> None:
    out = _run('resolvable-neighbor', start=.05, end=.05+1e-12, knots=())
    _prefix_oracle(out, start=.05, knot=None)
    assert out.status == 'completed' and out.times_s[-1] == .05+1e-12
    assert len(out.steps) > 0
    assert out.states[-1].amounts_mol[0, 1] > 0
    assert out.states[-1].internal_energy_j[0] > 600.


def test_nonresolvable_interval_is_not_timestamp_only_success() -> None:
    end = math.nextafter(.05, math.inf)
    out = _run('unresolvable-neighbor', start=.05, end=end, knots=())
    assert out.status != 'completed'
    assert out.times_s == (.05,) and not out.steps
    assert 'time' in out.reason


def test_immediate_cancellation_retains_initial_prefix() -> None:
    out = _run('cancel-initial', cancel=lambda: True)
    assert out.status == 'cancelled' and out.times_s == (0.,) and not out.steps
    _prefix_oracle(out)


def test_cancel_after_accepted_prefix_preserves_ledger() -> None:
    calls = 0
    def cancel() -> bool:
        nonlocal calls
        calls += 1
        return calls >= 100
    out = _run('cancel-prefix', cancel=cancel)
    assert out.status == 'cancelled'
    assert len(out.steps) > 0 and out.times_s[-1] < .06
    _prefix_oracle(out)


def test_piecewise_restart_uses_its_own_one_sided_operator() -> None:
    first = _run('piecewise-before', end=.05, knots=(), sink=.001, power=2.)
    _prefix_oracle(first)
    assert first.status == 'completed' and first.times_s[-1] == .05
    initial = first.states[-1]
    second = _run('piecewise-after', start=.05, end=.06, knots=(), initial=initial, sink=.002, power=3.)
    _prefix_oracle(second, start=.05, initial=initial, sink=.002, power=3., knot=None)
    assert second.status == 'completed' and second.times_s[-1] == .06


def test_rounded_cap_tie_cannot_exceed_exact_inventory_safety_duration() -> None:
    initial = ConservedState([[.02, 0.]], [600.])
    start, end = .045, .05
    # The decimal binary64 cap and .25*N/sink round to the same float,
    # while the actual boundary interval is strictly longer in exact arithmetic.
    assert .005 == .25*.02
    assert Fraction(end)-Fraction(start) > Fraction(.25)*Fraction(.02)
    out = _run('safe-cap-alias', start=start, end=end, knots=(), initial=initial, sink=1.)
    _prefix_oracle(out, start=start, initial=initial, sink=1., knot=None)
    assert out.status != 'completed' and out.reason == 'unresolvable_stage_time'
    assert out.times_s[-1] == math.nextafter(end, -math.inf)
    assert len(out.steps) > 0 and not out.events
    for index in range(len(out.steps)):
        elapsed = Fraction(out.times_s[index+1])-Fraction(out.times_s[index])
        available = Fraction(float(out.states[index].amounts_mol[0, 0]))
        assert elapsed <= Fraction(.25)*available


@pytest.mark.parametrize('start,end,knot', [(-.01, .01, 0.), (-.06, -.04, -.05)])
def test_negative_absolute_times_and_zero_knot_conserve(start: float, end: float, knot: float) -> None:
    out = _run('negative-'+str(knot), start=start, end=end, knots=(knot,))
    _prefix_oracle(out, start=start, knot=knot)
    assert out.status == 'completed', out.reason
    assert out.times_s[-1] == end and out.times_s.count(knot) == 1


def test_boundary_adjustment_cannot_inflate_sub_ulp_nominal_cap() -> None:
    start = 1.
    end = math.nextafter(math.nextafter(start, math.inf), math.inf)
    cap = .75*math.ulp(start)
    # Full two-ULP interval has an interior float, but is far larger than
    # this cap's own floating representation allowance. Never promote it.
    assert start < math.nextafter(start, math.inf) < end
    out = _run('large-origin-narrow-cap', start=start, end=end, knots=(),
               step=cap, minimum_step=1e-20)
    assert out.status != 'completed'
    assert out.times_s == (start,) and not out.steps
    _prefix_oracle(out, start=start, knot=None)


@pytest.mark.parametrize('slope', [0., .002])
def test_decimal_cap_affine_events_with_current_accuracy_configuration(slope: float) -> None:
    from test_depletion_spine import configured, oracle, initial, exact_event, audit, check_costs
    policy, event = configured()
    # CURRENT affine tests already use this tighter ordinary accuracy.
    # Retained original .005 fixtures at rel1e-7 remain separate unchanged evidence.
    policy = replace(policy, initial_step_s=.005, maximum_step_s=.005, relative_tolerance=1e-11)
    event = replace(event, terminal_method='affine_midpoint', amount_absolute_mol=1e-10)
    operator, counts = oracle(slope)
    out = integrate_depletion(initial(), operator, start_s=0., end_s=.2,
        integration_policy=policy, event_policy=event)
    _save('affine-current-accuracy-'+str(slope), out, [])
    audit(out, slope)
    check_costs(out)
    assert out.status == 'completed' and out.times_s[-1] == .2
    assert out.times_s.count(.05) == out.times_s.count(.15) == 1
    assert counts['calls'] == out.evaluations
    assert len(out.events) == 1
    observed_event = out.events[0]
    assert abs(observed_event.time_s-exact_event(slope)) < 1e-10
    row = out.states[out.times_s.index(observed_event.time_s)].amounts_mol[0]
    assert abs(row[2]-2*math.exp(-.1*observed_event.time_s)) < 1e-10
    assert any(item.status == 'independent_approach_pass' for item in out.refinements)
