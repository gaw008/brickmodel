"""Opt-in live accepted-prefix checkpoints for the ordinary exact RK driver.

This is an in-memory numerical continuation API, not a persistent codec or live
provider restoration. Admission passively replays saved callbacks in the same
arithmetic loop. It verifies controller/balance data, not historical wall clocks
or physical truth of a caller's observations; source admission remains external.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, replace
from fractions import Fraction as F
import hashlib
import json
import math
import time
from types import MappingProxyType

import numpy as np

from .exact_event_clock import ExactEventTime as T
from .exact_integration import ExactIntegrationResult, ExactStepLedger, _integrate_exact
from .integration import ConservedState, Rates, IntegrationPolicy, IntegrationError, DomainExit, _Reject, _Stop

PAUSE_REASON = 'accepted_boundary_pause_requested'


class ExactCheckpointError(IntegrationError):
    """A stopped prefix is inconsistent or lacks exact continuation evidence."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExactCheckpointError(reason)


def _copy(value):
    """Snapshot only known numeric containers, without interpreting a raw return."""
    if value is None or type(value) in (str, bool, int, float, F):
        return value
    if type(value) is np.ndarray:
        return np.frombuffer(value.tobytes(), dtype=value.dtype).reshape(value.shape)
    if type(value) is tuple:
        return tuple(_copy(item) for item in value)
    if type(value) in (dict, MappingProxyType):
        return MappingProxyType({key: _copy(item) for key, item in value.items()})
    if type(value) in (T, ConservedState, Rates, IntegrationPolicy, ExactStepLedger, ExactIntegrationResult,
                       ExactCallbackObservation, ExactIntegrationProblem, ExactIntegrationCheckpoint):
        clone = object.__new__(type(value))
        for field in fields(value):
            object.__setattr__(clone, field.name, _copy(getattr(value, field.name)))
        return clone
    raise ExactCheckpointError('checkpoint_unsupported_value:' + type(value).__name__)


def _plain(value):
    """Typed comparison spelling, separate from any public persistence format."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        _require(math.isfinite(value), 'checkpoint_nonfinite_float')
        return {'float': value.hex()}
    if type(value) is F:
        return {'fraction': (value.numerator, value.denominator)}
    if type(value) is np.ndarray:
        _require(value.dtype == np.float64 and np.all(np.isfinite(value)), 'checkpoint_finite_float64_array')
        return {'array': (value.shape, value.tobytes().hex())}
    if type(value) is tuple:
        return {'tuple': [_plain(item) for item in value]}
    if type(value) in (dict, MappingProxyType):
        _require(all(type(key) is str for key in value), 'checkpoint_mapping_keys')
        # Rates' component order is part of the driver's schema state.
        return {'mapping': [(key, _plain(item)) for key, item in value.items()]}
    if type(value) in (T, ConservedState, Rates, IntegrationPolicy, ExactStepLedger, ExactIntegrationResult,
                       ExactCallbackObservation, ExactIntegrationProblem, ExactIntegrationCheckpoint):
        return {'type': type(value).__name__, 'fields':
                {field.name: _plain(getattr(value, field.name)) for field in fields(value)
                 if field.name != 'binding_sha256'}}
    raise ExactCheckpointError('checkpoint_unsupported_value:' + type(value).__name__)


def _same(a, b) -> bool:
    return _plain(a) == _plain(b)


def _digest(value) -> str:
    raw = json.dumps(_plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _seal(checkpoint):
    return replace(checkpoint, binding_sha256=_digest(checkpoint))


def _time(value: T) -> None:
    _require(type(value) is T and type(value.seconds) is F, 'checkpoint_exact_fraction_time')


def _state(value: ConservedState) -> None:
    _require(type(value) is ConservedState, 'checkpoint_state_type')
    _plain(value)
    rebuilt = ConservedState(value.amounts_mol, value.internal_energy_j,
        value.energy_model_identity, value.mechanical_stretches)
    _require(_same(rebuilt, value), 'checkpoint_state_schema')


def _policy(value: IntegrationPolicy) -> None:
    _require(type(value) is IntegrationPolicy, 'checkpoint_policy_type')
    IntegrationPolicy.__post_init__(value)
    _plain(value)


@dataclass(frozen=True)
class ExactCallbackObservation:
    ordinal: int
    attempt_index: int
    role: str
    state: ConservedState
    time: T
    rates: Rates | None = None
    returned_type: str | None = None
    validated: bool = False
    failure_kind: str | None = None
    failure_message: str | None = None


@dataclass(frozen=True)
class ExactIntegrationProblem:
    initial: ConservedState
    start_s: T
    end_s: T
    policy: IntegrationPolicy
    breakpoints_s: tuple[T, ...]

    def check(self) -> None:
        _state(self.initial)
        _policy(self.policy)
        _time(self.start_s)
        _time(self.end_s)
        _require(self.start_s < self.end_s, 'checkpoint_original_interval')
        _require(type(self.breakpoints_s) is tuple, 'checkpoint_breakpoint_tuple')
        for stamp in self.breakpoints_s:
            _time(stamp)
        seconds = tuple(stamp.seconds for stamp in self.breakpoints_s)
        _require(seconds == tuple(sorted(set(seconds))) and
                 all(self.start_s.seconds < x < self.end_s.seconds for x in seconds),
                 'checkpoint_original_breakpoints')


@dataclass(frozen=True)
class ExactIntegrationCheckpoint:
    problem: ExactIntegrationProblem
    result: ExactIntegrationResult
    next_step_s: F
    knot_index: int
    component_schema: tuple[str, ...] | None
    cumulative_n: tuple[F, ...]
    cumulative_u: tuple[F, ...]
    cumulative_components: tuple[F, ...]
    cumulative_stretch: tuple[F, ...] | None
    cumulative_stretch_exact: tuple[F, ...] | None
    cumulative_stretch_roundoff: tuple[F, ...] | None
    observations: tuple[ExactCallbackObservation, ...]
    binding_sha256: str = ''
    phase: str = 'accepted_boundary'
    initial_probe_done: bool = True

    @property
    def elapsed_seconds(self) -> float:
        return self.result.elapsed_seconds

    def check(self) -> None:
        """Reproduce saved arithmetic without calling a physical operator."""
        _admit(self, self.problem)


@dataclass(frozen=True)
class ExactCheckpointRun:
    result: ExactIntegrationResult
    checkpoint: ExactIntegrationCheckpoint | None
    observations: tuple[ExactCallbackObservation, ...]
    committed_checkpoint: ExactIntegrationCheckpoint | None
    failure: Exception | None = None


def _structural(checkpoint: ExactIntegrationCheckpoint) -> None:
    _require(type(checkpoint) is ExactIntegrationCheckpoint and
             type(checkpoint.problem) is ExactIntegrationProblem and
             type(checkpoint.result) is ExactIntegrationResult, 'checkpoint_explicit_types')
    checkpoint.problem.check()
    _require(type(checkpoint.binding_sha256) is str and checkpoint.binding_sha256 == _digest(checkpoint),
             'checkpoint_content_binding')
    _require(checkpoint.phase == 'accepted_boundary' and checkpoint.initial_probe_done is True,
             'checkpoint_clean_accepted_boundary')
    result, problem = checkpoint.result, checkpoint.problem
    _require(result.status == 'cancelled' and result.reason == PAUSE_REASON,
             'checkpoint_requires_clean_boundary_pause')
    _require(type(result.elapsed_seconds) is float and math.isfinite(result.elapsed_seconds) and
             result.elapsed_seconds >= 0., 'checkpoint_elapsed')
    _require(all(type(value) is int and value >= 0 for value in
                 (result.evaluations, result.rejected_trials, result.attempted_trials)), 'checkpoint_cost_types')
    _require(type(result.times_s) is tuple and type(result.states) is tuple and type(result.steps) is tuple and
             len(result.states) == len(result.times_s) == len(result.steps) + 1 and bool(result.steps),
             'checkpoint_accepted_history_shape')
    _require(result.attempted_trials == len(result.steps) + result.rejected_trials and
             type(checkpoint.observations) is tuple and result.evaluations == len(checkpoint.observations) and
             1 + 7 * len(result.steps) + result.rejected_trials <= result.evaluations <=
             1 + 7 * result.attempted_trials, 'checkpoint_cost_history')
    for stamp in result.times_s:
        _time(stamp)
    for state in result.states:
        _state(state)
    _require(result.times_s[0] == problem.start_s and problem.start_s < result.times_s[-1] < problem.end_s and
             _same(result.states[0], problem.initial), 'checkpoint_original_initial_and_time')
    _require(all(a < b for a, b in zip(result.times_s, result.times_s[1:])), 'checkpoint_time_order')
    _require(type(checkpoint.next_step_s) is F and F(problem.policy.minimum_step_s) <= checkpoint.next_step_s <=
             F(problem.policy.maximum_step_s), 'checkpoint_next_step_domain')
    knots = (*problem.breakpoints_s, problem.end_s)
    _require(type(checkpoint.knot_index) is int and 0 <= checkpoint.knot_index < len(knots) and
             checkpoint.knot_index == next(i for i, knot in enumerate(knots) if knot >= result.times_s[-1]),
             'checkpoint_knot_index')
    _require(checkpoint.component_schema is None or (type(checkpoint.component_schema) is tuple and
             all(type(name) is str for name in checkpoint.component_schema)), 'checkpoint_component_schema')
    n, cells = problem.initial.amounts_mol.size, problem.initial.internal_energy_j.size
    for row, size in ((checkpoint.cumulative_n, n), (checkpoint.cumulative_u, cells),
                       (checkpoint.cumulative_components, cells)):
        _require(type(row) is tuple and len(row) == size and all(type(x) is F for x in row),
                 'checkpoint_cumulative_shape')
    mechanical = problem.initial.mechanical_stretches is not None
    for row in (checkpoint.cumulative_stretch, checkpoint.cumulative_stretch_exact,
                checkpoint.cumulative_stretch_roundoff):
        _require((row is None and not mechanical) or (mechanical and type(row) is tuple and
                 len(row) == cells + 1 and all(type(x) is F for x in row)), 'checkpoint_stretch_cumulative_shape')
    for index, observation in enumerate(checkpoint.observations):
        _require(type(observation) is ExactCallbackObservation and type(observation.ordinal) is int and
                 observation.ordinal == index + 1 and type(observation.attempt_index) is int and
                 0 <= observation.attempt_index <= result.attempted_trials and
                 type(observation.validated) is bool, 'checkpoint_observation_schema')
        _state(observation.state)
        _time(observation.time)
        if observation.validated:
            _require(type(observation.rates) is Rates and observation.failure_kind is None and
                     observation.failure_message is None and observation.returned_type == 'sludge_sandbox.integration.Rates',
                     'checkpoint_successful_callback')
            observation.rates.derivatives(observation.state)
            try:
                rebuilt = Rates(**{field.name: getattr(observation.rates, field.name)
                                   for field in fields(Rates) if field.init})
                _require(_same(rebuilt, observation.rates), 'checkpoint_rate_schema')
            except IntegrationError as exc:
                raise ExactCheckpointError('checkpoint_rate_schema') from exc
        else:
            _require(observation.failure_kind in ('DomainExit', '_Reject') and
                     type(observation.failure_message) is str and observation.rates is None and
                     observation.returned_type is None, 'checkpoint_failed_callback')


def _numeric_checkpoint(checkpoint):
    # The current result disposition and active wall time are not RK arithmetic.
    return replace(checkpoint, result=replace(checkpoint.result, status='running', reason=None,
                   elapsed_seconds=0.), binding_sha256='')


def _admit(checkpoint: ExactIntegrationCheckpoint, problem: ExactIntegrationProblem) -> None:
    _structural(checkpoint)
    _require(_same(problem, checkpoint.problem), 'checkpoint_original_problem_changed')
    cursor = 0
    saved = checkpoint.observations
    def callback(state, when):
        nonlocal cursor
        _require(cursor < len(saved), 'checkpoint_replay_missing_callback')
        observation = saved[cursor]
        cursor += 1
        _require(_same(state, observation.state) and _same(when, observation.time),
                 'checkpoint_replay_callback_input')
        if observation.failure_kind == 'DomainExit':
            raise DomainExit(observation.failure_message)
        if observation.failure_kind == '_Reject':
            raise _Reject(observation.failure_message)
        return _copy(observation.rates)
    replay = _Tracking(problem, time.monotonic(), 0., None,
                       lambda cp: len(cp.result.steps) == len(checkpoint.result.steps), None, audit=True)
    result = _integrate_exact(problem.initial, callback, start_s=problem.start_s, end_s=problem.end_s,
        policy=problem.policy, breakpoints_s=problem.breakpoints_s, _tracking=replay)
    _require(result.status == 'cancelled' and result.reason == PAUSE_REASON and
             replay.resumable is not None and cursor == len(saved), 'checkpoint_replay_boundary')
    _require(_same(_numeric_checkpoint(replay.resumable), _numeric_checkpoint(checkpoint)),
             'checkpoint_replay_numeric_state_changed')


class _Tracking:
    def __init__(self, problem, entered, external, continuation, pause, observer, *, audit=False):
        self.problem = problem
        self.entered = entered
        self.external = external
        self.continuation = continuation
        self.pause = pause
        self.observer = observer
        self.audit = audit
        self.observations = [] if continuation is None else list(_copy(continuation.observations))
        self.last_committed = None if continuation is None else _copy(continuation)
        self.resumable = None
        self.failure = None

    def elapsed(self) -> float:
        if self.audit:
            return 0.
        prior = F() if self.continuation is None else F(self.continuation.elapsed_seconds)
        exact = prior + F(self.external) + F(time.monotonic() - self.entered)
        value = float(exact)
        return math.nextafter(value, math.inf) if F(value) < exact else value

    def started(self, state, when, ordinal, attempted, role):
        self.observations.append(ExactCallbackObservation(ordinal, attempted, role, _copy(state), _copy(when)))

    def returned(self, rates):
        self.observations[-1] = replace(self.observations[-1],
            rates=_copy(rates) if type(rates) is Rates else None,
            returned_type=type(rates).__module__ + '.' + type(rates).__qualname__)

    def validated(self):
        self.observations[-1] = replace(self.observations[-1], validated=True)

    def failed(self, exception):
        self.observations[-1] = replace(self.observations[-1],
            failure_kind=type(exception).__name__, failure_message=str(exception))

    def _notify(self, callback, checkpoint):
        try:
            return callback(_copy(checkpoint))
        except Exception as exc:
            self.failure = exc
            raise _Stop('failed', 'checkpoint_observer_failed:' + type(exc).__name__ + ':' + str(exc)) from exc

    def _committed_guard(self, guard):
        try:
            guard()
        except _Stop:
            raise
        except Exception as exc:
            self.failure = exc
            # The accepted state is already committed. A user cancel callback
            # failure is not a DomainExit/_Reject of that completed RK trial.
            raise _Stop('failed', 'checkpoint_guard_failed:' + type(exc).__name__ + ':' + str(exc)) from exc

    def committed(self, result, h, knot, schema, n, u, components, stretch, stretch_exact,
                  stretch_roundoff, guard):
        optional = lambda row: None if row is None else tuple(row)
        checkpoint = _seal(ExactIntegrationCheckpoint(self.problem, _copy(result), h, knot, schema,
            tuple(n), tuple(u), tuple(components), optional(stretch), optional(stretch_exact),
            optional(stretch_roundoff), tuple(_copy(tuple(self.observations)))))
        self.last_committed = checkpoint
        if self.observer is not None:
            self._notify(self.observer, checkpoint)
            self._committed_guard(guard)
        pause = False if self.pause is None else self._notify(self.pause, checkpoint)
        _require(type(pause) is bool, 'checkpoint_pause_must_return_bool')
        self._committed_guard(guard)
        if pause and result.times_s[-1] < self.problem.end_s:
            raise _Stop('cancelled', PAUSE_REASON)

    def finish(self, result):
        checkpoint = self.last_committed
        if (checkpoint is not None and result.evaluations == checkpoint.result.evaluations and
                result.attempted_trials == checkpoint.result.attempted_trials and
                len(result.steps) == len(checkpoint.result.steps)):
            # No uncommitted tail: retain stop/observer/admission wall debit in
            # the latest evidence even when its status is not resumable.
            self.last_committed = _seal(replace(checkpoint, result=_copy(result)))
        if result.status == 'cancelled' and result.reason == PAUSE_REASON:
            checkpoint = self.last_committed
            if checkpoint is not None and result.times_s[-1] < self.problem.end_s:
                self.resumable = _seal(replace(checkpoint, result=_copy(result)))
                self.last_committed = self.resumable


def run_checkpointed(initial: ConservedState, operator: Callable[[ConservedState, T], Rates], *,
        start_s: T, end_s: T, policy: IntegrationPolicy, breakpoints_s: tuple[T, ...] = (),
        cancel: Callable[[], bool] | None = None,
        continuation: ExactIntegrationCheckpoint | None = None,
        pause_after_commit: Callable[[ExactIntegrationCheckpoint], bool] | None = None,
        on_commit: Callable[[ExactIntegrationCheckpoint], None] | None = None,
        admission_elapsed_seconds: float = 0.0) -> ExactCheckpointRun:
    entered = time.monotonic()
    _require(type(admission_elapsed_seconds) is float and math.isfinite(admission_elapsed_seconds) and
             admission_elapsed_seconds >= 0., 'checkpoint_external_elapsed')
    _require(callable(operator) and all(callback is None or callable(callback)
             for callback in (cancel, pause_after_commit, on_commit)), 'checkpoint_callbacks')
    problem = ExactIntegrationProblem(_copy(initial), _copy(start_s), _copy(end_s),
                                     _copy(policy), _copy(breakpoints_s))
    problem.check()
    if continuation is not None:
        _admit(continuation, problem)
        continuation = _copy(continuation)
    tracking = _Tracking(problem, entered, admission_elapsed_seconds, continuation, pause_after_commit, on_commit)
    result = _integrate_exact(problem.initial, operator, start_s=problem.start_s, end_s=problem.end_s,
        policy=problem.policy, breakpoints_s=problem.breakpoints_s, cancel=cancel, _tracking=tracking)
    return ExactCheckpointRun(result, tracking.resumable, tuple(tracking.observations),
                              tracking.last_committed, tracking.failure)
