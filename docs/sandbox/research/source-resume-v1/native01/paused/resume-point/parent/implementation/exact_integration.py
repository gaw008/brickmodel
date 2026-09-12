"""Exact-time SSPRK2 candidate: explicit separate types, no legacy time casts."""
from dataclasses import dataclass, field
from collections.abc import Mapping
from fractions import Fraction
from types import MappingProxyType
from typing import Callable, TYPE_CHECKING
import math
import time
import numpy as np
from numpy.typing import NDArray
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.integration import (ConservedState, Rates, IntegrationPolicy, IntegrationError,
    DomainExit, _Reject, _Stop, _array, _components, _scalar, _updated, _sum_arrays, _check_update)

if TYPE_CHECKING:
    from .exact_integration_checkpoint import ExactIntegrationCheckpoint, ExactCheckpointRun


def _scaled(duration: Fraction, values: NDArray[np.float64]) -> NDArray[np.float64]:
    """Round each exact rational duration times represented rate once."""
    try:
        out = np.array([float(duration*Fraction(float(v))) for v in values.flat]).reshape(values.shape)
    except (OverflowError,ValueError) as exc:
        raise _Reject('unrepresentable_exact_duration_product') from exc
    if not np.all(np.isfinite(out)):
        raise _Reject('unrepresentable_exact_duration_product')
    return out


def _duration_control(desired: Fraction) -> Fraction:
    """Choose a downward binary64 nominal duration, then adopt it exactly.

    This limits controller denominator growth; it never projects an absolute
    callback time or any actual quadrature interval to binary64.
    """
    try:
        value = float(desired)
    except OverflowError as exc:
        raise IntegrationError("unrepresentable_control_duration") from exc
    if not math.isfinite(value):
        raise IntegrationError("unrepresentable_control_duration")
    if Fraction(value) > desired:
        value = math.nextafter(value, -math.inf)
    return Fraction(value)


def advance_exact_euler(state: ConservedState, rates: Rates, duration: Fraction,
                        policy: IntegrationPolicy) -> ConservedState:
    """Original represented Euler predictor; no new acceptance or error estimator.

    Exact duration multiplies each represented net derivative before the state
    update. Preserve the driver's product underflow and trial-rejection behavior;
    this is not the affine panel's exact shared-face quadrature.
    """
    if (not isinstance(state, ConservedState) or not isinstance(rates, Rates)
            or not isinstance(policy, IntegrationPolicy)):
        raise IntegrationError('validated_euler_state_rates_policy_required')
    if type(duration) is not Fraction or duration <= 0:
        raise IntegrationError('exact_positive_euler_duration_required')
    IntegrationPolicy.__post_init__(policy)
    if state.mechanical_stretches is not None and policy.stretch_absolute_tolerance is None:
        raise IntegrationError('explicit_stretch_scales_required')
    dn, du = rates.derivatives(state)
    n = _updated(state.amounts_mol, _scaled(duration,dn), policy.amount_absolute_tolerance_mol, "amount")
    u = _updated(state.internal_energy_j, _scaled(duration,du), policy.energy_absolute_tolerance_j, "energy")
    if np.any(n < 0) or not np.all(np.isfinite(n)) or not np.all(np.isfinite(u)):
        raise _Reject("trial_inventory_or_energy_invalid")
    stretches = None
    if state.mechanical_stretches is not None:
        stretches = _updated(state.mechanical_stretches, _scaled(duration,rates.mechanical_rates_per_s),
                             policy.stretch_absolute_tolerance, "stretch")
        if np.any(stretches <= 0):
            raise _Reject("trial_stretch_not_positive")
    return ConservedState(n, u, energy_model_identity=state.energy_model_identity,
                          mechanical_stretches=stretches)


@dataclass(frozen=True)
class ExactStepLedger:
    """Accepted quadrature, including optional power-component decomposition.

    component_sum_residual_j = represented total - exact sum of represented
    component integrals. component_quadrature_roundoff_j records each represented
    integral minus the exact sum of represented stage powers times RK weights;
    it includes products and both levels of summation, not truncation/EOS error.
    Manually constructed ledgers may omit the latter unavailable stage evidence.
    """
    start_s: ExactEventTime
    end_s: ExactEventTime
    face_species_mol: NDArray[np.float64]
    face_energy_j: NDArray[np.float64]
    reaction_species_mol: NDArray[np.float64]
    cell_work_j: NDArray[np.float64]
    cell_work_components_j: Mapping[str, NDArray[np.float64]] | None = None
    component_quadrature_roundoff_j: Mapping[str, tuple[Fraction, ...]] | None = None
    component_sum_residual_j: tuple[Fraction, ...] | None = field(init=False, default=None)
    stretch_increment: NDArray[np.float64] | None = None
    # Represented increment minus exact represented-stage rate quadrature.
    stretch_quadrature_roundoff: tuple[Fraction, ...] | None = None

    def __post_init__(self):
        if type(self.start_s) is not ExactEventTime or type(self.end_s) is not ExactEventTime or self.end_s <= self.start_s:
            raise IntegrationError("ordered_exact_ledger_times_required")
        for name, dimensions in (("face_species_mol", 2), ("face_energy_j", 1),
                                 ("reaction_species_mol", 2), ("cell_work_j", 1)):
            object.__setattr__(self, name, _array(getattr(self, name), name, dimensions))
        if self.stretch_increment is not None:
            increment = _array(self.stretch_increment, "stretch_increment", 1)
            if increment.shape != (len(self.cell_work_j)+1,):
                raise IntegrationError("stretch_increment_shape_mismatch")
            object.__setattr__(self, "stretch_increment", increment)
            rounding = self.stretch_quadrature_roundoff
            if (not isinstance(rounding, tuple) or len(rounding) != len(increment) or
                    any(type(value) is not Fraction for value in rounding)):
                raise IntegrationError("stretch_quadrature_roundoff_required")
        elif self.stretch_quadrature_roundoff is not None:
            raise IntegrationError("stretch_increment_required")
        components, residual = _components(self.cell_work_components_j, self.cell_work_j, rate=False)
        object.__setattr__(self, "cell_work_components_j", components)
        object.__setattr__(self, "component_sum_residual_j", residual)
        rounding = self.component_quadrature_roundoff_j
        if rounding is not None:
            if components is None or set(rounding) != set(components):
                raise IntegrationError("invalid_component_roundoff_keys")
            rounding = {key: tuple(value) for key, value in rounding.items()}
            if any(len(v) != len(self.cell_work_j) or any(type(x) is not Fraction for x in v)
                   for v in rounding.values()):
                raise IntegrationError("invalid_component_roundoff")
            object.__setattr__(self, "component_quadrature_roundoff_j", MappingProxyType(rounding))


@dataclass(frozen=True)
class ExactIntegrationResult:
    status: str
    reason: str | None
    times_s: tuple[ExactEventTime, ...]
    states: tuple[ConservedState, ...]
    steps: tuple[ExactStepLedger, ...]
    evaluations: int
    rejected_trials: int
    elapsed_seconds: float
    attempted_trials: int
    cumulative_absolute_component_residual_j: tuple[Fraction, ...] | None = None


def integrate_exact(initial: ConservedState, operator: Callable[[ConservedState, ExactEventTime], Rates], *,
              start_s: ExactEventTime, end_s: ExactEventTime, policy: IntegrationPolicy,
              breakpoints_s: tuple[ExactEventTime, ...] = (),
              cancel: Callable[[], bool] | None = None) -> ExactIntegrationResult:
    """Two-half SSPRK2 with exact semantic stage times and original error gates.

    Explicit opt-in: callbacks receive ExactEventTime, never display floats.
    Policy durations retain their exact binary64 meaning. Clipped remaining
    intervals below minimum_step_s are refused, including breakpoint remainders.
    No legacy checkpoint/codec or depletion-packet admission is provided.
    """
    return _integrate_exact(initial, operator, start_s=start_s, end_s=end_s, policy=policy,
                            breakpoints_s=breakpoints_s, cancel=cancel)


def integrate_exact_checkpointed(initial: ConservedState,
              operator: Callable[[ConservedState, ExactEventTime], Rates], *,
              start_s: ExactEventTime, end_s: ExactEventTime, policy: IntegrationPolicy,
              breakpoints_s: tuple[ExactEventTime, ...] = (),
              cancel: Callable[[], bool] | None = None,
              continuation: 'ExactIntegrationCheckpoint | None' = None,
              pause_after_commit: 'Callable[[ExactIntegrationCheckpoint], bool] | None' = None,
              on_commit: 'Callable[[ExactIntegrationCheckpoint], None] | None' = None,
              admission_elapsed_seconds: float = 0.0) -> 'ExactCheckpointRun':
    """Opt-in accepted-boundary pause/continuation; the old result stays unchanged.

    Checkpoint and observation types live in exact_integration_checkpoint.
    Immediate mid-trial cancellation does not grant a resumable checkpoint.
    """
    from .exact_integration_checkpoint import run_checkpointed
    return run_checkpointed(initial, operator, start_s=start_s, end_s=end_s,
        policy=policy, breakpoints_s=breakpoints_s, cancel=cancel, continuation=continuation,
        pause_after_commit=pause_after_commit, on_commit=on_commit,
        admission_elapsed_seconds=admission_elapsed_seconds)


def _integrate_exact(initial, operator, *, start_s, end_s, policy,
                     breakpoints_s=(), cancel=None, _tracking=None):
    """One arithmetic loop for both original and opt-in checkpoint entry points."""
    if not isinstance(initial, ConservedState) or not isinstance(policy, IntegrationPolicy):
        raise IntegrationError("validated_initial_state_and_policy_required")
    if initial.mechanical_stretches is not None:
        if policy.stretch_absolute_tolerance is None:
            raise IntegrationError("explicit_stretch_scales_required")
        _scalar(policy.stretch_absolute_tolerance+policy.relative_tolerance*policy.stretch_scale,
                "combined_stretch_scale", positive=True)
    if not callable(operator) or (cancel is not None and not callable(cancel)):
        raise IntegrationError("invalid_callback")
    if type(start_s) is not ExactEventTime or type(end_s) is not ExactEventTime:
        raise IntegrationError("exact_time_endpoints_required")
    start, end = start_s.seconds, end_s.seconds
    if end <= start:
        raise IntegrationError("end_must_follow_start")
    if not isinstance(breakpoints_s, (list, tuple)):
        raise IntegrationError("invalid_breakpoints")
    if any(type(t) is not ExactEventTime for t in breakpoints_s):
        raise IntegrationError("exact_breakpoints_required")
    knots = [t.seconds for t in breakpoints_s]
    if any(not start < t < end for t in knots) or knots != sorted(set(knots)):
        raise IntegrationError("breakpoints_must_be_strictly_ordered_interior_times")
    knots.append(end)
    times, states, ledgers = [start], [initial], []
    evaluations, rejected, knot_index, attempted = 0, 0, 0, 0
    component_schema = ...
    cumulative_components = [Fraction() for _ in initial.internal_energy_j]
    begin = time.monotonic()
    cumulative_n = [Fraction(0) for _ in initial.amounts_mol.flat]
    cumulative_u = [Fraction(0) for _ in initial.internal_energy_j.flat]
    mechanical = initial.mechanical_stretches is not None
    cumulative_stretch = [Fraction() for _ in initial.mechanical_stretches] if mechanical else None
    cumulative_stretch_exact = list(cumulative_stretch) if mechanical else None
    cumulative_stretch_roundoff = list(cumulative_stretch) if mechanical else None
    resumed = None if _tracking is None else _tracking.continuation
    if resumed is not None:
        prior = resumed.result
        times = [stamp.seconds for stamp in prior.times_s]
        states, ledgers = list(prior.states), list(prior.steps)
        evaluations, rejected, attempted = prior.evaluations, prior.rejected_trials, prior.attempted_trials
        knot_index, component_schema = resumed.knot_index, resumed.component_schema
        cumulative_n, cumulative_u = list(resumed.cumulative_n), list(resumed.cumulative_u)
        cumulative_components = list(resumed.cumulative_components)
        if mechanical:
            cumulative_stretch = list(resumed.cumulative_stretch)
            cumulative_stretch_exact = list(resumed.cumulative_stretch_exact)
            cumulative_stretch_roundoff = list(resumed.cumulative_stretch_roundoff)

    def accumulated_exchange(previous, before, after, terms, tolerance, name):
        # Exact binary-float sums avoid building a second drifting float ledger.
        # This guards numerical representation only, not physical source balance.
        proposed = []
        for index, old_sum in zip(np.ndindex(before.shape), previous):
            total = old_sum + sum((Fraction(float(term[index])) for term in terms), Fraction(0))
            residual = Fraction(float(after[index]))-Fraction(float(before[index]))-total
            if abs(residual) > Fraction(tolerance):
                raise IntegrationError(f"cumulative_{name}_roundoff")
            proposed.append(total)
        return proposed

    def finish(status, reason=None):
        result = ExactIntegrationResult(status, reason, tuple(ExactEventTime(t) for t in times), tuple(states), tuple(ledgers),
                                 evaluations, rejected, elapsed(), attempted,
                                 tuple(cumulative_components) if component_schema not in (..., None) else None)
        if _tracking is not None:
            _tracking.finish(result)
        return result

    def elapsed():
        return time.monotonic()-begin if _tracking is None else _tracking.elapsed()

    def guard():
        if cancel is not None and cancel():
            raise _Stop("cancelled", "cancel_requested")
        if elapsed() >= policy.maximum_wall_seconds:
            raise _Stop("resource_limit", "wall_time_limit")

    def smaller_step(at, endpoint, desired):
        return _duration_control(desired if desired < endpoint-at else (endpoint-at)/2)

    def evaluate(state, at, role):
        nonlocal evaluations, component_schema
        guard()
        evaluations += 1
        if _tracking is not None:
            _tracking.started(state, ExactEventTime(at), evaluations, attempted, role)
        try:
            rates = operator(state, ExactEventTime(at))
            if _tracking is not None:
                _tracking.returned(rates)
            guard()
            if not isinstance(rates, Rates):
                raise IntegrationError("operator_must_return_rates")
            if _tracking is not None and type(rates) is not Rates:
                raise IntegrationError('checkpoint_requires_exact_rates')
            rates.derivatives(state)
            schema = None if rates.cell_power_components_w is None else tuple(rates.cell_power_components_w)
            if component_schema is ...:
                component_schema = schema
            elif schema != component_schema:
                raise IntegrationError("component_work_schema_changed")
        except BaseException as exc:
            if _tracking is not None:
                _tracking.failed(exc)
            raise
        if _tracking is not None:
            _tracking.validated()
        return rates

    def advance(state, rates, step):
        return advance_exact_euler(state, rates, step, policy)

    def rk2(state, at, endpoint, role):
        step = endpoint-at
        first = evaluate(state, at, role+'_first')
        stage = advance(state, first, step)
        second = evaluate(stage, endpoint, role+'_second')
        # Validate the second Euler stage before forming its SSP convex average.
        advance(stage, second, step)
        fields = [_sum_arrays(_scaled(step/2,getattr(first, name)), _scaled(step/2,getattr(second, name))) for name in (
            "face_species_mol_s", "face_energy_w", "reaction_species_mol_s", "cell_power_w")]
        faces_n, faces_u, sources, work = fields
        stretches, stretch_increment, exact_stretch = None, None, None
        if mechanical:
            stretch_increment = _sum_arrays(_scaled(step/2,first.mechanical_rates_per_s),
                                            _scaled(step/2,second.mechanical_rates_per_s))
            stretches = _updated(state.mechanical_stretches, stretch_increment,
                                 policy.stretch_absolute_tolerance, "stretch")
            if np.any(stretches <= 0):
                raise _Reject("trial_stretch_not_positive")
            exact_stretch = tuple(Fraction(step/2)*(Fraction(float(a))+Fraction(float(b)))
                                  for a,b in zip(first.mechanical_rates_per_s, second.mechanical_rates_per_s))
        result = ConservedState(
            _updated(state.amounts_mol, _sum_arrays(faces_n[:-1], -faces_n[1:], sources),
                     policy.amount_absolute_tolerance_mol, "amount"),
            _updated(state.internal_energy_j, _sum_arrays(faces_u[:-1], -faces_u[1:], work),
                     policy.energy_absolute_tolerance_j, "energy"),
            energy_model_identity=state.energy_model_identity, mechanical_stretches=stretches)
        parts, exact_parts = None, None
        if first.cell_power_components_w is not None:
            parts, exact_parts = {}, {}
            for key in first.cell_power_components_w:
                a, b = first.cell_power_components_w[key], second.cell_power_components_w[key]
                parts[key] = _sum_arrays(_scaled(step/2,a), _scaled(step/2,b))
                exact_parts[key] = tuple(Fraction(step/2)*(Fraction(float(x))+Fraction(float(y)))
                                         for x, y in zip(a, b))
        return result, fields, parts, exact_parts, stretch_increment, exact_stretch

    h = Fraction(policy.initial_step_s) if resumed is None else resumed.next_step_s
    last_domain = None
    try:
        # Initial domain failure is not a reason to try infinitesimal time steps.
        if resumed is None:
            evaluate(initial, start, 'initial')
        else:
            guard()
    except DomainExit as exc:
        return finish("domain_exit", str(exc))
    except IntegrationError as exc:
        return finish("numerical_failure", str(exc))
    except _Stop as exc:
        return finish(exc.status, exc.reason)
    except Exception as exc:
        if _tracking is None:
            raise
        _tracking.failure = exc
        return finish('failed', type(exc).__name__+':'+str(exc))
    while times[-1] < end:
        if len(ledgers) >= policy.maximum_steps:
            return finish("resource_limit", "accepted_step_limit")
        if rejected >= policy.maximum_rejections:
            return finish("resource_limit", "rejected_trial_limit")
        at, state = times[-1], states[-1]
        if at == knots[knot_index]:
            knot_index += 1
        target = knots[knot_index]
        next_time = min(at+h,target)
        # Avoid manufacturing a sub-minimum tail at a fixed endpoint. Both
        # planned intervals must still obey the original min/max bounds.
        if 0 < target-next_time < Fraction(policy.minimum_step_s):
            half_remaining = (target-at)/2
            if Fraction(policy.minimum_step_s) <= half_remaining <= h:
                next_time = at+half_remaining
        step = next_time-at
        if step < Fraction(policy.minimum_step_s) or step <= 0:
            return finish("domain_exit" if last_domain else "numerical_failure",
                          last_domain or "minimum_time_step")
        attempted += 1
        try:
            midpoint = at+step/2
            # These semantic subintervals are exactly equal, independent of origin.
            left_step, right_step = midpoint-at, next_time-midpoint
            if (not at < midpoint < next_time or left_step/2 == 0 or right_step/2 == 0):
                raise IntegrationError("unresolvable_stage_time")
            full, _, _, _, _, _ = rk2(state, at, next_time, 'full')
            half, first_fields, first_parts, first_exact, first_stretch, first_stretch_exact = rk2(state, at, midpoint, 'left')
            accepted, second_fields, second_parts, second_exact, second_stretch, second_stretch_exact = rk2(half, midpoint, next_time, 'right')
            nscale = policy.amount_absolute_tolerance_mol+policy.relative_tolerance*policy.amount_scale_mol
            uscale = policy.energy_absolute_tolerance_j+policy.relative_tolerance*policy.energy_scale_j
            # Leading local SSPRK2 error is C*h^3. For the two actual substeps,
            # q=(h1^3+h2^3)/h^3 and fine error=(fine-full)*q/(1-q).
            # Equal halves recover 1/3 without assuming rounded times are equal.
            q = (left_step/step)**3+(right_step/step)**3
            if not 0 < q < 1:
                raise IntegrationError("unresolvable_stage_time")
            error = max(float(np.max(np.abs(accepted.amounts_mol-full.amounts_mol)))/nscale,
                        float(np.max(np.abs(accepted.internal_energy_j-full.internal_energy_j)))/uscale)*q/(1-q)
            if mechanical:
                stretch_scale = policy.stretch_absolute_tolerance+policy.relative_tolerance*policy.stretch_scale
                stretch_error = float(np.max(np.abs(accepted.mechanical_stretches-full.mechanical_stretches)))/stretch_scale*q/(1-q)
                if not math.isfinite(stretch_error):
                    raise _Reject("nonfinite_mechanical_error_estimate")
                error = max(error, stretch_error)
            if not math.isfinite(error):
                raise _Reject("nonfinite_error_estimate")
            if error > 1:
                rejected += 1
                h = smaller_step(at, next_time, step*Fraction(max(0.2, 0.9*error**(-1/3))))
                last_domain = None
                continue
            # Validate the accepted combination in the actual physical operator.
            evaluate(accepted, next_time, 'accepted')
            fields = [_sum_arrays(a, b) for a, b in zip(first_fields, second_fields)]
            faces_n, faces_u, sources, work = fields
            _check_update(state.amounts_mol, accepted.amounts_mol,
                          _sum_arrays(faces_n[:-1], -faces_n[1:], sources),
                          policy.amount_absolute_tolerance_mol, "amount")
            _check_update(state.internal_energy_j, accepted.internal_energy_j,
                          _sum_arrays(faces_u[:-1], -faces_u[1:], work),
                          policy.energy_absolute_tolerance_j, "energy")
            proposed_n = accumulated_exchange(cumulative_n, initial.amounts_mol, accepted.amounts_mol,
                                              (faces_n[:-1], -faces_n[1:], sources),
                                              policy.amount_absolute_tolerance_mol, "amount")
            proposed_u = accumulated_exchange(cumulative_u, initial.internal_energy_j, accepted.internal_energy_j,
                                              (faces_u[:-1], -faces_u[1:], work),
                                              policy.energy_absolute_tolerance_j, "energy")
            parts, rounding = None, None
            if first_parts is not None:
                parts = {key: _sum_arrays(first_parts[key], second_parts[key]) for key in first_parts}
                rounding = {key: tuple(Fraction(float(value))-a-b for value, a, b in
                                      zip(parts[key], first_exact[key], second_exact[key])) for key in parts}
            stretch_increment, stretch_rounding = None, None
            proposed_stretch, proposed_stretch_exact = cumulative_stretch, cumulative_stretch_exact
            proposed_stretch_roundoff = cumulative_stretch_roundoff
            if mechanical:
                stretch_increment = _sum_arrays(first_stretch, second_stretch)
                exact_stretch = tuple(a+b for a,b in zip(first_stretch_exact, second_stretch_exact))
                stretch_rounding = tuple(Fraction(float(value))-exact for value,exact in zip(stretch_increment, exact_stretch))
                _check_update(state.mechanical_stretches, accepted.mechanical_stretches, stretch_increment,
                              policy.stretch_absolute_tolerance, "stretch")
                proposed_stretch = accumulated_exchange(cumulative_stretch, initial.mechanical_stretches,
                    accepted.mechanical_stretches, (stretch_increment,), policy.stretch_absolute_tolerance, "stretch")
                proposed_stretch_exact = [old+delta for old,delta in zip(cumulative_stretch_exact, exact_stretch)]
                proposed_stretch_roundoff = [old+abs(delta) for old,delta in zip(cumulative_stretch_roundoff, stretch_rounding)]
                for index, (exact, total) in enumerate(zip(exact_stretch, proposed_stretch_exact)):
                    value = Fraction(float(accepted.mechanical_stretches[index]))
                    local = value-Fraction(float(state.mechanical_stretches[index]))-exact
                    cumulative = value-Fraction(float(initial.mechanical_stretches[index]))-total
                    if (abs(local) > Fraction(policy.stretch_absolute_tolerance) or
                            abs(cumulative) > Fraction(policy.stretch_absolute_tolerance) or
                            proposed_stretch_roundoff[index] > Fraction(policy.stretch_absolute_tolerance)):
                        raise IntegrationError("cumulative_stretch_quadrature_roundoff")
            ledger = ExactStepLedger(ExactEventTime(at), ExactEventTime(next_time), *fields, parts, rounding,
                                stretch_increment=stretch_increment, stretch_quadrature_roundoff=stretch_rounding)
            proposed_components = cumulative_components
            if ledger.component_sum_residual_j is not None:
                proposed_components = [old+abs(delta) for old, delta in
                                       zip(cumulative_components, ledger.component_sum_residual_j)]
                if any(x > Fraction(policy.energy_absolute_tolerance_j) for x in proposed_components):
                    raise IntegrationError("cumulative_component_sum_roundoff")
            guard()
            cumulative_n, cumulative_u = proposed_n, proposed_u
            cumulative_components = proposed_components
            cumulative_stretch, cumulative_stretch_exact = proposed_stretch, proposed_stretch_exact
            cumulative_stretch_roundoff = proposed_stretch_roundoff
            ledgers.append(ledger)
            states.append(accepted)
            times.append(next_time)
            h = max(Fraction(policy.minimum_step_s), _duration_control(min(Fraction(policy.maximum_step_s), step*Fraction(2 if error == 0 else min(2, max(0.2, 0.9*error**(-1/3)))))))
            last_domain = None
            if _tracking is not None:
                checkpoint_result = ExactIntegrationResult('running', None,
                    tuple(ExactEventTime(t) for t in times), tuple(states), tuple(ledgers),
                    evaluations, rejected, elapsed(), attempted,
                    tuple(cumulative_components) if component_schema is not None else None)
                _tracking.committed(checkpoint_result, h, knot_index, component_schema,
                    cumulative_n, cumulative_u, cumulative_components,
                    cumulative_stretch, cumulative_stretch_exact, cumulative_stretch_roundoff, guard)
        except (DomainExit, _Reject) as exc:
            rejected += 1
            h = smaller_step(at, next_time, step/2)
            last_domain = str(exc) if isinstance(exc, DomainExit) else None
        except IntegrationError as exc:
            return finish("numerical_failure", str(exc))
        except _Stop as exc:
            return finish(exc.status, exc.reason)
        except Exception as exc:
            if _tracking is None:
                raise
            _tracking.failure = exc
            return finish('failed', type(exc).__name__+':'+str(exc))
    return finish("completed")
