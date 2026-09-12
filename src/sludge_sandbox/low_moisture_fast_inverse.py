"""Explicit safeguarded full-U inverse draft, with the original acceptance gates.

Only candidate selection differs from the existing bisection. The energy target
is never shifted by sorption excess, and a dry state keeps its full reference.
This module does not install or select itself in any production host.
"""
from dataclasses import replace
from fractions import Fraction as F
import math

from sludge_sandbox.arlabosse_low_moisture_storage import (
    LowMoistureSorptionPoint, LowMoistureSorptionStorage,
)
from sludge_sandbox.mass_storage_bridge import MixedError, require, upper
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.source_wet_storage import SourceWetInverse, _binary


NUMERICAL_POLICY_ID = 'LOW_MOISTURE_FULL_U_SAFEGUARDED_NEWTON_BISECTION_V1'
FORCED_BISECTION_PERIOD = 3


def strategy_definition() -> dict:
    """Fresh explicit numerical choices; no new physical coefficients or bounds."""
    return {
        'id': NUMERICAL_POLICY_ID,
        'classification': 'numerical_policy',
        'target': 'original complete U(state), including the dry-end excess constant',
        'endpoint_support': 'U(lo)+error(lo) <= target <= U(hi)-error(hi); no endpoint padding',
        'first_candidate': 'nominal endpoint secant projected to a strictly interior new binary64 T',
        'subsequent_candidates': 'T-residual/closed_Cv from the previous evaluated point',
        'fallback': 'invalid/outside/endpoint-rounded candidate uses an exact-rational midpoint projection',
        'forced_bisection_period': FORCED_BISECTION_PERIOD,
        'contraction': 'at least one midpoint evaluation every three candidate evaluations, unless already accepted or failed',
        'acceptance': 'abs(full-U residual)+energy_error <= original energy_tolerance and outward-rounded ((abs(residual)+error)/minimum_Cv) <= original temperature_tolerance',
        'sign': 'reject abs(residual)<=energy_error when acceptance has not passed',
        'limits': 'unchanged original maximum_iterations for candidate evaluations; exactly two initial endpoint evaluations',
        'endpoint_result': 'after both support gates pass, an endpoint may satisfy the original residual/Cv criterion; iterations=0',
        'qualification': 'numerical candidate strategy only, no material or native performance validation',
    }


def _interior_float(value: F, lo: float, hi: float) -> float | None:
    """An unusable Newton/secant proposal is not itself a physical-domain error."""
    try:
        t = float(value)
    except (OverflowError, ValueError):
        return None
    return t if math.isfinite(t) and lo < t < hi else None


def _checked_point(storage: LowMoistureSorptionStorage, state, t: float) -> LowMoistureSorptionPoint:
    point = storage.evaluate(state,t)  # Runs the unchanged actual storage guards.
    require(type(point) is LowMoistureSorptionPoint and point.model_identity == storage._identity
            and point.temperature_k == t, 'fast_inverse_actual_point_correspondence')
    _binary(point.total_internal_energy_j)
    error = _binary(point.energy_error_j)
    cv = _binary(point.closed_heat_capacity_j_k,positive=True)
    minimum = _binary(point.minimum_heat_capacity_j_k,positive=True)
    require(error >= 0 and minimum <= cv, 'fast_inverse_invalid_energy_or_capacity_bound')
    p = F(_binary(point.pressure_pa,positive=True))
    p_error = F(_binary(point.pressure_error_pa))
    p_lo,p_hi = map(F,storage.pressure_domain_pa)
    require(p_error >= 0 and p_lo <= p-p_error and p+p_error <= p_hi,
            'fast_inverse_pressure_domain_exit')
    return point


def _accepted(point, target: F, policy: InversePolicy, bracket, iteration) -> SourceWetInverse | None:
    residual = F(point.total_internal_energy_j)-target
    allowance = abs(residual)+F(point.energy_error_j)
    try:
        bound = upper(allowance/F(point.minimum_heat_capacity_j_k))
    except (OverflowError, ValueError) as exc:
        raise MixedError('fast_inverse_temperature_bound_unrepresentable') from exc
    if allowance <= F(policy.energy_tolerance_j) and F(bound) <= F(policy.temperature_tolerance_k):
        return SourceWetInverse(point,float(target),residual,bound,bracket,iteration)
    return None


def invert_low_moisture_safeguarded(storage: LowMoistureSorptionStorage, state,
                                  policy: InversePolicy) -> SourceWetInverse:
    """Strictly bracketed secant/Newton proposals with mandatory periodic bisection.

    Every returned result passes the existing full-U energy/minimum-Cv criterion.
    No proposal can skip endpoint source/pressure/support checks, invent a zero
    error bound, or suppress an error raised by an actual storage evaluation.
    """
    require(type(storage) is LowMoistureSorptionStorage, 'actual_low_moisture_storage_required')
    require(type(policy) is InversePolicy, 'explicit_inverse_policy')
    replace(policy)  # Revalidate declared policy fields, without changing them.
    storage.check(state)
    lo,hi = storage.temperature_domain_k
    lo,hi = _binary(lo,positive=True),_binary(hi,positive=True)
    require(lo < hi, 'fast_inverse_empty_temperature_domain')
    target = F(_binary(state.internal_energy_j))
    a,b = _checked_point(storage,state,lo),_checked_point(storage,state,hi)
    ua,ub = F(a.total_internal_energy_j),F(b.total_internal_energy_j)
    require(ua+F(a.energy_error_j) <= target <= ub-F(b.energy_error_j),
            'sorption_energy_target_outside_domain_or_resolution')
    require(ua < ub, 'fast_inverse_nonincreasing_endpoint_energy')
    for endpoint in (a,b):
        accepted = _accepted(endpoint,target,policy,(lo,hi),0)
        if accepted is not None:
            storage.check(state)
            return accepted
    proposal = F(lo)+(target-ua)*(F(hi)-F(lo))/(ub-ua)
    for iteration in range(1,policy.maximum_iterations+1):
        candidate = (None if iteration % FORCED_BISECTION_PERIOD == 0
                     else _interior_float(proposal,lo,hi))
        if candidate is None:
            candidate = _interior_float((F(lo)+F(hi))/2,lo,hi)
        require(candidate is not None, 'sorption_unresolvable_temperature')
        out = _checked_point(storage,state,candidate)
        accepted = _accepted(out,target,policy,(lo,hi),iteration)
        if accepted is not None:
            storage.check(state)
            return accepted
        residual = F(out.total_internal_energy_j)-target
        require(abs(residual) > F(out.energy_error_j), 'sorption_inverse_sign_unresolved')
        if residual > 0:
            hi = candidate
        else:
            lo = candidate
        # This is the existing representable-bracket gate, not a new tolerance.
        require(hi-lo > math.ulp(candidate), 'sorption_unresolvable_temperature')
        proposal = F(candidate)-residual/F(out.closed_heat_capacity_j_k)
    raise MixedError('sorption_inverse_iteration_limit')
