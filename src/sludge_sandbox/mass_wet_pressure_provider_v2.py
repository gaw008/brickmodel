"""V2 structured-failure wrapper; existing proof equations and gates unchanged."""
from dataclasses import dataclass, fields
from typing import Callable
from decimal import localcontext
import time
from sludge_sandbox.mass_wet_pressure_interval import (
    BoundLiquidPressureRequest, LiquidBranchModelPolicy, QueryBoxes, ProofBudget,
    LiquidPressureEvidence, ProofOperation, need, encoded, identity, parameters,
    connected_tube_density, pressure_radius_checked, COEFFICIENT_SHA,
    eos, coex, coupled, tube, native,
)
from sludge_sandbox.integration import DomainExit


class BindingFailure(ValueError):
    """Explicit source/request identity guard failure."""


def category(exc: Exception) -> str:
    """Classify exception types, never message substrings."""
    if isinstance(exc,BindingFailure):return 'binding_failure'
    if isinstance(exc,InterruptedError):return 'cancelled'
    if isinstance(exc,TimeoutError):return 'resource_limit'
    if isinstance(exc,DomainExit):return 'domain_exit'
    if isinstance(exc,(ValueError,ArithmeticError)):return 'unresolved'
    return 'callback_failure'


@dataclass(frozen=True)
class StructuredPressureEvidence(LiquidPressureEvidence):
    schema: str='conditional_pressure_evidence_v2'
    failure_kind: str | None=None
    failure_stage: str | None=None


class StructuredLiquidPressureProvider:
    """Concrete pinned mathematical implementation; no pressure callback input."""

    def evaluate(self, request: BoundLiquidPressureRequest, *, branch_policy: LiquidBranchModelPolicy,
                 boxes: QueryBoxes, budget: ProofBudget,
                 cancel: Callable[[],bool] | None=None, caller_guard: Callable[[],None] | None=None) -> StructuredPressureEvidence:
        need(type(request) is BoundLiquidPressureRequest and type(branch_policy) is LiquidBranchModelPolicy
             and type(boxes) is QueryBoxes and type(budget) is ProofBudget,'explicit_typed_query_contract')
        begun=time.monotonic();operations=[];attempted=completed=0
        original_policy_json=encoded(branch_policy);original_proposals_json=encoded(boxes)
        original_request_sha256=request.numeric_identity
        original_query_json=request.captured_query_json
        original_source_json=request.captured_source_json
        need(type(original_request_sha256) is str and type(original_query_json) is bytes
             and type(original_source_json) is bytes,'immutable_original_request_snapshot')
        limits=ProofBudget(**{f.name:getattr(budget,f.name) for f in fields(budget)})
        before=();after=None;params=None;radius=None;status='unresolved';reason=None
        stage='preflight';failure_kind=None
        def snapshot():
            try:
                request.check();branch_policy.check_sources()
            except Exception as exc:
                raise BindingFailure(str(exc)) from exc
            return (request.host_identity,request.numeric_identity,identity(branch_policy),identity(boxes),identity(budget),
                    *branch_policy.check_sources())
        def guard():
            if caller_guard is not None:caller_guard()
            if cancel is not None and cancel():raise InterruptedError('cancelled')
            if time.monotonic()-begun>limits.maximum_wall_seconds:raise TimeoutError('cumulative_proof_wall_budget')
            if snapshot()!=before:raise BindingFailure('source_or_request_changed')
        def remaining():
            guard()
            value=limits.maximum_wall_seconds-(time.monotonic()-begun)
            if value<=0:raise TimeoutError('cumulative_proof_wall_budget')
            return value
        def operation(name,call):
            nonlocal attempted,completed,stage
            guard()
            if attempted>=limits.maximum_proof_operations:raise TimeoutError('proof_operation_budget_exhausted')
            stage=name;attempted+=1;start=time.monotonic()
            try:
                value=call();completed+=1
                raw=encoded(value)
                operations.append(ProofOperation(name,'completed',time.monotonic()-start,raw,None))
            except Exception as exc:
                operations.append(ProofOperation(name,'failed',time.monotonic()-start,None,type(exc).__name__+': '+str(exc)))
                raise
            guard();return value
        try:
            branch_policy.__post_init__();budget.__post_init__();boxes.__post_init__()
            before=snapshot();guard()
            params=parameters(request,branch_policy,limits.precision);guard()
            source=branch_policy.coefficient_json
            with localcontext() as context:
                context.prec=limits.precision
                coexistence=operation('coexistence',lambda:coex.enclose_coexistence(
                    source,COEFFICIENT_SHA,params.temperature,boxes.coexistence_log_density,
                    boxes.center,boxes.preconditioner,precision=limits.precision,weights=boxes.weights))
                need(coexistence.proved and coexistence.pressure is not None,'coexistence_unresolved')
                mechanical=operation('coupled_mechanical_root',lambda:coupled.enclose_local_root(
                    source,COEFFICIENT_SHA,temperature=params.temperature,
                    liquid_molar_density=boxes.mechanical_density,effective_available_volume=params.effective_volume,
                    liquid_mol=params.liquid_mol,gas_mol=params.gas_mol,gas_constant=params.gas_constant,
                    liquid_volume_scale=params.public_native_scale,precision=limits.precision))
                q=params.observed_query
                observed_density=eos.I(q[2])/eos.I(q[4])
                density=connected_tube_density(coexistence.domain.density[0],boxes.mechanical_density,
                                               boxes.observed_density,observed_density)
                full_tube=operation('full_temperature_connected_density_tube',lambda:tube.prove_density_tube(
                    source,COEFFICIENT_SHA,params.temperature,density,precision=limits.precision,
                    maximum_boxes=limits.maximum_boxes_per_primitive,
                    maximum_wall_seconds=remaining()))
                need(full_tube.proved and full_tube.temperature==params.temperature and full_tube.density==density,
                     'whole_connected_density_tube_unresolved')
                observed=operation('observed_native_query',lambda:native.analyze(
                    q,boxes.observed_density,
                    pressure=lambda tt,rr:eos.pressure_interval(source,COEFFICIENT_SHA,tt,rr,precision=limits.precision),
                    binding=snapshot,maximum_boxes=limits.maximum_boxes_per_primitive,
                    maximum_wall_seconds=remaining()))
                need(observed['status']=='passed_observed_query','observed_native_volume_contract_unresolved')
                radius=pressure_radius_checked(params.nominal_pressure_pa,mechanical.pressure,
                    params.original_fixed_T_error_pa,params.pressure_domain,branch_policy.pressure_domain_pa,
                    coexistence.pressure)
                guard();status='proved_conditional_query'
        except Exception as exc:
            reason=stage+': '+type(exc).__name__+': '+str(exc)
            failure_kind=category(exc);radius=None
        try:
            after=snapshot()
        except Exception as exc:
            status='unresolved';reason='final_binding: '+type(exc).__name__+': '+str(exc);radius=None;failure_kind='binding_failure'
        elapsed=time.monotonic()-begun
        if after!=before or elapsed>limits.maximum_wall_seconds:
            status='unresolved';radius=None;reason=reason or 'final_source_or_cumulative_wall'
            failure_kind='binding_failure' if after!=before else 'resource_limit'
        return StructuredPressureEvidence(status,reason,original_request_sha256,radius,
            None if params is None else encoded(params),tuple(operations),attempted,completed,elapsed,limits,
            before,after,original_policy_json,original_proposals_json,original_query_json,original_source_json,
            failure_kind=failure_kind,failure_stage=None if status=='proved_conditional_query' else stage)
