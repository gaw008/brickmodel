"""Adaptive conservative SSPRK2 with accepted-step exchange ledgers.

This integrator supplies no physical laws or material coefficients. A coupled
operator recomputes every active mechanism from each trial conserved state.
Species inventories and total internal energy use exactly the same face/source
weights. Rejected trials never enter the accepted trajectory or its ledgers.
"""

from dataclasses import dataclass, field
from fractions import Fraction
import math
import time
from typing import Callable, Mapping
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray


class IntegrationError(ValueError):
    """Invalid inputs or an operator violating the conservative interface."""


class DomainExit(ValueError):
    """The explicitly modelled material/thermodynamic domain is unavailable."""


def _scalar(value: object, name: str, *, positive: bool = False) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (positive and value <= 0):
        raise IntegrationError(f"invalid_{name}")
    return float(value)


def _array(value: object, name: str, dimensions: int) -> NDArray[np.float64]:
    try:
        raw = np.asarray(value, dtype=object)
        if any(isinstance(v, (bool, np.bool_)) for v in raw.flat):
            raise IntegrationError(f"boolean_{name}")
        raw = np.asarray(value)
        if raw.dtype.kind not in "ifu":
            raise IntegrationError(f"nonnumeric_{name}")
        array = np.array(raw, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise IntegrationError(f"invalid_{name}") from exc
    if array.ndim != dimensions or not array.size or not np.all(np.isfinite(array)):
        raise IntegrationError(f"invalid_{name}")
    # A bytes-backed snapshot cannot be made writable again by its consumer.
    return np.frombuffer(array.tobytes(), dtype=np.float64).reshape(array.shape)


def _sum_arrays(*terms: NDArray) -> NDArray:
    """Sum net exchanges before combining with a potentially tiny inventory."""
    try:
        result = np.array([math.fsum(float(t[index]) for t in terms)
                           for index in np.ndindex(terms[0].shape)]).reshape(terms[0].shape)
    except (OverflowError, ValueError) as exc:
        raise IntegrationError("nonfinite_exchange_sum") from exc
    if not np.all(np.isfinite(result)):
        raise IntegrationError("nonfinite_exchange_sum")
    return result


def _updated(old: NDArray, increment: NDArray, tolerance: float, name: str) -> NDArray:
    result = _sum_arrays(old, increment)
    _check_update(old, result, increment, tolerance, name)
    return result


def _check_update(old: NDArray, result: NDArray, increment: NDArray,
                  tolerance: float, name: str) -> None:
    residual = _sum_arrays(result, -old, -increment)
    if np.any(np.abs(residual) > tolerance):
        raise IntegrationError(f"unresolvable_{name}_increment")


_WORK_COMPONENTS = frozenset(("elastic", "interface", "dissipation", "pore", "body"))


def _components(value, total, *, rate):
    if value is None:
        return None, None
    if not isinstance(value, Mapping) or not value or not set(value) <= _WORK_COMPONENTS:
        raise IntegrationError("invalid_component_work_keys")
    snapshot = {key: _array(value[key], "work_component", 1) for key in sorted(value)}
    if any(v.shape != total.shape for v in snapshot.values()):
        raise IntegrationError("component_work_shape_mismatch")
    if "dissipation" in snapshot and np.any(snapshot["dissipation"] < 0):
        raise IntegrationError("negative_dissipation_component")
    residual = []
    for i, net in enumerate(total):
        exact = sum((Fraction(float(v[i])) for v in snapshot.values()), Fraction())
        if rate:
            try:
                rounded = float(exact)
            except OverflowError as exc:
                raise IntegrationError("component_power_sum_unrepresentable") from exc
            if rounded != float(net):
                raise IntegrationError("component_power_sum_mismatch")
        residual.append(Fraction(float(net))-exact)
    return MappingProxyType(snapshot), tuple(residual)


@dataclass(frozen=True)
class ConservedState:
    """Cell inventories and energy with an optional opaque model binding.

    None preserves the historical untagged energy interface. A non-None binding
    must be checked by its physical host; it does not certify sources or imply
    a universal definition of total energy. RK and inventory writeback preserve
    it without reinterpretation. Explicit strings/tuples exclude mutable keys.
    """
    amounts_mol: NDArray[np.float64]
    internal_energy_j: NDArray[np.float64]
    energy_model_identity: tuple | None = None

    def __post_init__(self):
        if self.energy_model_identity is not None:
            if type(self.energy_model_identity) is not tuple:
                raise IntegrationError("invalid_energy_model_identity")
            pending = [self.energy_model_identity]
            while pending:
                item = pending.pop()
                if type(item) is tuple and item:
                    pending.extend(item)
                elif type(item) is str and item and item == item.strip():
                    continue
                else:
                    raise IntegrationError("invalid_energy_model_identity")
        amounts = _array(self.amounts_mol, "amounts", 2)
        energy = _array(self.internal_energy_j, "energy", 1)
        if amounts.shape[0] != energy.size or np.any(amounts < 0):
            raise IntegrationError("invalid_state_shape_or_inventory")
        object.__setattr__(self, "amounts_mol", amounts)
        object.__setattr__(self, "internal_energy_j", energy)


@dataclass(frozen=True)
class Rates:
    """Face-positive left-to-right; reaction sources mol/s; external cell power W.

    Reaction formation energy is in the state: do not add it again to cell_power.
    Each interior face is stored once, not separately evaluated by its neighbors.
    Optional named components decompose cell power; total power must be the
    correctly rounded exact sum of their represented values. The exact residual
    is diagnostic, not a second power source. No material identity is inferred.
    """
    face_species_mol_s: NDArray[np.float64]
    face_energy_w: NDArray[np.float64]
    reaction_species_mol_s: NDArray[np.float64]
    cell_power_w: NDArray[np.float64]
    cell_power_components_w: Mapping[str, NDArray[np.float64]] | None = None
    component_sum_residual_w: tuple[Fraction, ...] | None = field(init=False, default=None)

    def __post_init__(self):
        for name, dimensions in (("face_species_mol_s", 2), ("face_energy_w", 1),
                                 ("reaction_species_mol_s", 2), ("cell_power_w", 1)):
            object.__setattr__(self, name, _array(getattr(self, name), name, dimensions))

        components, residual = _components(self.cell_power_components_w, self.cell_power_w, rate=True)
        object.__setattr__(self, "cell_power_components_w", components)
        object.__setattr__(self, "component_sum_residual_w", residual)

    def derivatives(self, state: ConservedState) -> tuple[NDArray, NDArray]:
        cells, species = state.amounts_mol.shape
        if (self.face_species_mol_s.shape != (cells+1, species)
                or self.face_energy_w.shape != (cells+1,)
                or self.reaction_species_mol_s.shape != (cells, species)
                or self.cell_power_w.shape != (cells,)):
            raise IntegrationError("rate_shape_mismatch")
        dn = _sum_arrays(self.face_species_mol_s[:-1], -self.face_species_mol_s[1:], self.reaction_species_mol_s)
        du = _sum_arrays(self.face_energy_w[:-1], -self.face_energy_w[1:], self.cell_power_w)
        if not np.all(np.isfinite(dn)) or not np.all(np.isfinite(du)):
            raise IntegrationError("nonfinite_derivative")
        if np.any((state.amounts_mol == 0) & (dn < 0)):
            raise IntegrationError("outflow_from_zero_inventory")
        return dn, du


@dataclass(frozen=True)
class StepLedger:
    """Accepted quadrature, including optional power-component decomposition.

    component_sum_residual_j = represented total - exact sum of represented
    component integrals. component_quadrature_roundoff_j records each represented
    integral minus the exact sum of represented stage powers times RK weights;
    it includes products and both levels of summation, not truncation/EOS error.
    Manually constructed ledgers may omit the latter unavailable stage evidence.
    """
    start_s: float
    end_s: float
    face_species_mol: NDArray[np.float64]
    face_energy_j: NDArray[np.float64]
    reaction_species_mol: NDArray[np.float64]
    cell_work_j: NDArray[np.float64]
    cell_work_components_j: Mapping[str, NDArray[np.float64]] | None = None
    component_quadrature_roundoff_j: Mapping[str, tuple[Fraction, ...]] | None = None
    component_sum_residual_j: tuple[Fraction, ...] | None = field(init=False, default=None)

    def __post_init__(self):
        for name, dimensions in (("face_species_mol", 2), ("face_energy_j", 1),
                                 ("reaction_species_mol", 2), ("cell_work_j", 1)):
            object.__setattr__(self, name, _array(getattr(self, name), name, dimensions))
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
class IntegrationPolicy:
    """Numerical choices, including explicit physical error scales, not material data."""
    initial_step_s: float
    maximum_step_s: float
    minimum_step_s: float
    relative_tolerance: float
    amount_absolute_tolerance_mol: float
    energy_absolute_tolerance_j: float
    amount_scale_mol: float
    energy_scale_j: float
    maximum_steps: int
    maximum_rejections: int
    maximum_wall_seconds: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name in {"maximum_steps", "maximum_rejections"}:
                if type(value) is not int or value < 1:
                    raise IntegrationError(f"invalid_{name}")
            else:
                _scalar(value, name, positive=True)
        if not self.minimum_step_s <= self.initial_step_s <= self.maximum_step_s:
            raise IntegrationError("inconsistent_step_bounds")


@dataclass(frozen=True)
class IntegrationResult:
    status: str
    reason: str | None
    times_s: tuple[float, ...]
    states: tuple[ConservedState, ...]
    steps: tuple[StepLedger, ...]
    evaluations: int
    rejected_trials: int
    elapsed_seconds: float
    cumulative_absolute_component_residual_j: tuple[Fraction, ...] | None = None


class _Reject(Exception):
    pass


class _Stop(Exception):
    def __init__(self, status: str, reason: str):
        self.status, self.reason = status, reason


def integrate(initial: ConservedState, operator: Callable[[ConservedState, float], Rates], *,
              start_s: float, end_s: float, policy: IntegrationPolicy,
              breakpoints_s: tuple[float, ...] = (),
              cancel: Callable[[], bool] | None = None) -> IntegrationResult:
    """Two half SSPRK2 steps accepted; a discarded full step estimates local error.

    Scales are supplied explicitly so a large formation energy cannot silently
    dominate temperature-error control. Positivity violations reject the trial;
    an operator extracting from a zero inventory fails immediately. Restarting
    from result.states[-1]/times_s[-1] is possible; persistent identity-checked
    checkpoint/resume belongs to the application layer, not this API yet.
    Optional component schemas are fixed across every evaluation in this call.
    Only accepted fine RK stages enter their ledger. Cumulative absolute per-cell
    decomposition residual is bounded by energy_absolute_tolerance_j. Net-energy
    adaptivity does not certify the truncation error of cancelling components.
    This optional contract is implemented here only; depletion terminal panels
    and wrappers must explicitly propagate it before claiming equivalent support.
    Breakpoints split continuous forcing. Discontinuous forcing requires explicit
    piecewise restarts with the appropriate one-sided operator on each interval.
    """
    if not isinstance(initial, ConservedState) or not isinstance(policy, IntegrationPolicy):
        raise IntegrationError("validated_initial_state_and_policy_required")
    if not callable(operator) or (cancel is not None and not callable(cancel)):
        raise IntegrationError("invalid_callback")
    start, end = _scalar(start_s, "start"), _scalar(end_s, "end")
    if end <= start:
        raise IntegrationError("end_must_follow_start")
    if not isinstance(breakpoints_s, (list, tuple)):
        raise IntegrationError("invalid_breakpoints")
    knots = [_scalar(t, "breakpoint") for t in breakpoints_s]
    if any(not start < t < end for t in knots) or knots != sorted(set(knots)):
        raise IntegrationError("breakpoints_must_be_strictly_ordered_interior_times")
    knots.append(end)
    times, states, ledgers = [start], [initial], []
    evaluations, rejected, knot_index = 0, 0, 0
    component_schema = ...
    cumulative_components = [Fraction() for _ in initial.internal_energy_j]
    begin = time.monotonic()
    cumulative_n = [Fraction(0) for _ in initial.amounts_mol.flat]
    cumulative_u = [Fraction(0) for _ in initial.internal_energy_j.flat]

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
        return IntegrationResult(status, reason, tuple(times), tuple(states), tuple(ledgers),
                                 evaluations, rejected, time.monotonic()-begin,
                                 tuple(cumulative_components) if component_schema not in (..., None) else None)

    def guard():
        if cancel is not None and cancel():
            raise _Stop("cancelled", "cancel_requested")
        if time.monotonic()-begin >= policy.maximum_wall_seconds:
            raise _Stop("resource_limit", "wall_time_limit")

    def smaller_step(at, endpoint, desired):
        if at+desired >= endpoint:
            return math.nextafter(endpoint, at)-at
        return desired

    def evaluate(state, at):
        nonlocal evaluations, component_schema
        guard()
        evaluations += 1
        rates = operator(state, at)
        guard()
        if not isinstance(rates, Rates):
            raise IntegrationError("operator_must_return_rates")
        rates.derivatives(state)
        schema = None if rates.cell_power_components_w is None else tuple(rates.cell_power_components_w)
        if component_schema is ...:
            component_schema = schema
        elif schema != component_schema:
            raise IntegrationError("component_work_schema_changed")
        return rates

    def advance(state, rates, step):
        dn, du = rates.derivatives(state)
        n = _updated(state.amounts_mol, step*dn, policy.amount_absolute_tolerance_mol, "amount")
        u = _updated(state.internal_energy_j, step*du, policy.energy_absolute_tolerance_j, "energy")
        if np.any(n < 0) or not np.all(np.isfinite(n)) or not np.all(np.isfinite(u)):
            raise _Reject("trial_inventory_or_energy_invalid")
        return ConservedState(n, u, energy_model_identity=state.energy_model_identity)

    def rk2(state, at, endpoint):
        step = endpoint-at
        first = evaluate(state, at)
        stage = advance(state, first, step)
        second = evaluate(stage, endpoint)
        # Validate the second Euler stage before forming its SSP convex average.
        advance(stage, second, step)
        fields = [_sum_arrays((step/2)*getattr(first, name), (step/2)*getattr(second, name)) for name in (
            "face_species_mol_s", "face_energy_w", "reaction_species_mol_s", "cell_power_w")]
        faces_n, faces_u, sources, work = fields
        result = ConservedState(
            _updated(state.amounts_mol, _sum_arrays(faces_n[:-1], -faces_n[1:], sources),
                     policy.amount_absolute_tolerance_mol, "amount"),
            _updated(state.internal_energy_j, _sum_arrays(faces_u[:-1], -faces_u[1:], work),
                     policy.energy_absolute_tolerance_j, "energy"),
            energy_model_identity=state.energy_model_identity)
        parts, exact_parts = None, None
        if first.cell_power_components_w is not None:
            parts, exact_parts = {}, {}
            for key in first.cell_power_components_w:
                a, b = first.cell_power_components_w[key], second.cell_power_components_w[key]
                parts[key] = _sum_arrays((step/2)*a, (step/2)*b)
                exact_parts[key] = tuple(Fraction(step/2)*(Fraction(float(x))+Fraction(float(y)))
                                         for x, y in zip(a, b))
        return result, fields, parts, exact_parts

    h = policy.initial_step_s
    last_domain = None
    try:
        # Initial domain failure is not a reason to try infinitesimal time steps.
        evaluate(initial, start)
    except DomainExit as exc:
        return finish("domain_exit", str(exc))
    except IntegrationError as exc:
        return finish("numerical_failure", str(exc))
    except _Stop as exc:
        return finish(exc.status, exc.reason)
    while times[-1] < end:
        if len(ledgers) >= policy.maximum_steps:
            return finish("resource_limit", "accepted_step_limit")
        if rejected >= policy.maximum_rejections:
            return finish("resource_limit", "rejected_trial_limit")
        at, state = times[-1], states[-1]
        if at == knots[knot_index]:
            knot_index += 1
        target = knots[knot_index]
        step = min(h, target-at)
        # Avoid leaving a one-ULP sliver solely from decimal time addition.
        # Integrate the complete remainder; never snap a state without its flux.
        if 0 < target-(at+step) <= min(math.ulp(target), 32*math.ulp(step)):
            step = target-at
        next_time = target if step == target-at else at+step
        step = next_time-at
        if h < policy.minimum_step_s or at+step <= at:
            return finish("domain_exit" if last_domain else "numerical_failure",
                          last_domain or "minimum_time_step")
        try:
            midpoint = at+step/2
            # Rounded absolute times need not divide into exactly equal halves.
            # Every stage uses its actual endpoint difference, including weights.
            left_step, right_step = midpoint-at, next_time-midpoint
            if (not at < midpoint < next_time or left_step/2 == 0 or right_step/2 == 0):
                raise IntegrationError("unresolvable_stage_time")
            full, _, _, _ = rk2(state, at, next_time)
            half, first_fields, first_parts, first_exact = rk2(state, at, midpoint)
            accepted, second_fields, second_parts, second_exact = rk2(half, midpoint, next_time)
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
            if not math.isfinite(error):
                raise _Reject("nonfinite_error_estimate")
            if error > 1:
                rejected += 1
                h = smaller_step(at, next_time, step*max(0.2, 0.9*error**(-1/3)))
                last_domain = None
                continue
            # Validate the accepted combination in the actual physical operator.
            evaluate(accepted, next_time)
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
            ledger = StepLedger(at, next_time, *fields, parts, rounding)
            proposed_components = cumulative_components
            if ledger.component_sum_residual_j is not None:
                proposed_components = [old+abs(delta) for old, delta in
                                       zip(cumulative_components, ledger.component_sum_residual_j)]
                if any(x > Fraction(policy.energy_absolute_tolerance_j) for x in proposed_components):
                    raise IntegrationError("cumulative_component_sum_roundoff")
            guard()
            cumulative_n, cumulative_u = proposed_n, proposed_u
            cumulative_components = proposed_components
            ledgers.append(ledger)
            states.append(accepted)
            times.append(next_time)
            h = max(policy.minimum_step_s, min(policy.maximum_step_s, step*(2 if error == 0 else min(2, max(0.2, 0.9*error**(-1/3))))))
            last_domain = None
        except (DomainExit, _Reject) as exc:
            rejected += 1
            h = smaller_step(at, next_time, step/2)
            last_domain = str(exc) if isinstance(exc, DomainExit) else None
        except IntegrationError as exc:
            return finish("numerical_failure", str(exc))
        except _Stop as exc:
            return finish(exc.status, exc.reason)
    return finish("completed")
