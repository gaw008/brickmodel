"""Bounded source-bound numerical proposals, never pressure certificates."""
from dataclasses import dataclass, replace
from decimal import Decimal as D, localcontext
from pathlib import Path
from typing import Callable
import hashlib
import json
import math
import time
from sludge_sandbox.water_interval_eos import I, Interval, residual
from sludge_sandbox.water_coexistence import evaluate_box
from sludge_sandbox.mass_wet_pressure_interval import (
    BoundLiquidPressureRequest,LiquidBranchModelPolicy,QueryBoxes,parameters,
    encoded,identity,need,COEFFICIENT_SHA,
)
from sludge_sandbox.mass_wet_pressure_provider_v2 import BindingFailure,category


@dataclass(frozen=True)
class LiquidSeedPolicy:
    strategy: str='iapws95_ancillary_point_newton_proposals_v1'
    maximum_iterations: int=12
    precision: int=60
    stopping_residual: D=D('1e-30')
    log_density_widths: tuple[D,D]=(D('4e-6'),D('1e-3'))
    density_expansion: D=D('.2')

    def __post_init__(self):
        need(type(self.strategy) is str and self.strategy=='iapws95_ancillary_point_newton_proposals_v1','fixed_seed_strategy')
        need(type(self.maximum_iterations) is int and self.maximum_iterations==12 and type(self.precision) is int and self.precision==60,'fixed_seed_numerics')
        need(type(self.stopping_residual) is D and self.stopping_residual==D('1e-30') and
             type(self.log_density_widths) is tuple and len(self.log_density_widths)==2 and
             all(type(x) is D for x in self.log_density_widths) and self.log_density_widths==(D('4e-6'),D('1e-3')) and
             type(self.density_expansion) is D and self.density_expansion==D('.2'),'fixed_seed_proposal_widths')


@dataclass(frozen=True)
class SeedIteration:
    iteration: int
    center: tuple[D,D]
    status: str
    value_json: bytes | None=None
    matrix: tuple | None=None
    residual_midpoints: tuple | None=None
    reason: str | None=None


@dataclass(frozen=True)
class SeedAttempt:
    status: str
    failure_kind: str | None
    reason: str | None
    boxes: QueryBoxes | None
    iterations: tuple[SeedIteration,...]
    ancillary_json: bytes | None
    attempted: int
    completed: int
    elapsed_seconds: float
    maximum_evaluations: int
    maximum_wall_seconds: float
    original_policy_json: bytes
    original_query_json: bytes
    original_source_json: bytes
    source_before: tuple[str,...]
    source_after: tuple[str,...] | None
    qualification: str='untrusted_numerical_proposals_not_certificates'


def propose_liquid_boxes(request: BoundLiquidPressureRequest, branch_policy: LiquidBranchModelPolicy, *,
        policy: LiquidSeedPolicy,maximum_evaluations: int,maximum_wall_seconds: float,
        caller_guard: Callable[[],None] | None=None,cancel: Callable[[],bool] | None=None) -> SeedAttempt:
    need(type(request) is BoundLiquidPressureRequest and type(branch_policy) is LiquidBranchModelPolicy and type(policy) is LiquidSeedPolicy,'typed_seed_inputs')
    policy.__post_init__()
    need(type(maximum_evaluations) is int and maximum_evaluations>=0 and type(maximum_wall_seconds) is float and math.isfinite(maximum_wall_seconds) and maximum_wall_seconds>0,'seed_work_wall_limits')
    origin=time.monotonic();entered=completed=0;rows=[];before=();after=None;ancillary_json=None;boxes=None
    original_policy=encoded(policy);original_query=request.captured_query_json;original_source=request.captured_source_json
    status='unresolved';failure_kind=None;reason=None
    def snapshot():
        try:
            request.check();sources=branch_policy.check_sources()
        except Exception as exc:raise BindingFailure(str(exc)) from exc
        return (request.host_identity,request.numeric_identity,identity(branch_policy),identity(policy),
                hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),*sources)
    def guard():
        if caller_guard is not None:caller_guard()
        if cancel is not None and cancel():raise InterruptedError('seed_cancelled')
        if time.monotonic()-origin>maximum_wall_seconds:raise TimeoutError('seed_wall_budget')
        if snapshot()!=before:raise BindingFailure('seed_source_or_policy_changed')
    try:
        before=snapshot();guard()
        params=parameters(request,branch_policy,policy.precision);guard()
        raw_bytes=Path(branch_policy.coefficient_json).read_bytes()
        need(hashlib.sha256(raw_bytes).hexdigest()==COEFFICIENT_SHA,'seed_coefficient_bytes_changed')
        raw=json.loads(raw_bytes)[0];equation=raw['EOS'][0]
        with localcontext() as context:
            context.prec=policy.precision
            temperature=request.rate.inverse.point.fluid.mechanical.temperature_k
            center=[];ancillary_values=[]
            for name,kind in (('rhoL','rhoLnoexp'),('rhoV','rhoV')):
                a=raw['ANCILLARIES'][name]
                need(a['type']==kind and a['Tmin']<=temperature<=a['Tmax'],'ancillary_seed_domain')
                theta=1-temperature/a['T_r']
                total=math.fsum(n*theta**power for n,power in zip(a['n'],a['t'],strict=True))
                rho=a['reducing_value']*(1+total if name=='rhoL' else math.exp(a['T_r']/temperature*total))
                center.append(D(rho).ln());ancillary_values.append((name,rho,center[-1]))
                ancillary_json=encoded(tuple(ancillary_values))
            center=tuple(center);guard()
            kwargs=dict(reducing_density=equation['STATES']['reducing']['rhomolar'],
                reducing_temperature=equation['STATES']['reducing']['T'],gas_constant=equation['gas_constant'],
                jet=lambda d,tau:residual(d,tau,equation['alphar']))
            def midpoint(value):return (value.lo+value.hi)/2
            for iteration in range(policy.maximum_iterations):
                guard()
                if entered>=maximum_evaluations:raise TimeoutError('cumulative_seed_evaluation_budget')
                entered+=1;rows.append(SeedIteration(iteration,center,'entered'))
                try:
                    value=evaluate_box(I(temperature),tuple(I(x) for x in center),**kwargs)
                    completed+=1;rows[-1]=replace(rows[-1],status='evaluated',value_json=encoded(value))
                    guard()
                    a,b=map(midpoint,value.jacobian[0]);c,d=map(midpoint,value.jacobian[1]);det=a*d-b*c
                    need(det!=0,'singular_seed_jacobian')
                    matrix=((d/det,-b/det),(-c/det,a/det));r=tuple(map(midpoint,value.residual))
                    rows[-1]=replace(rows[-1],status='completed',matrix=matrix,residual_midpoints=r)
                except Exception as exc:
                    rows[-1]=replace(rows[-1],status='failed',reason=type(exc).__name__+': '+str(exc));raise
                if max(map(abs,r))<policy.stopping_residual:break
                center=tuple(center[j]-sum((matrix[j][k]*r[k] for k in range(2)),D(0)) for j in range(2))
            else:raise ValueError('bounded_seed_not_converged')
            weights=policy.log_density_widths
            logs=tuple(Interval((I(x)-I(r)).lo,(I(x)+I(r)).hi) for x,r in zip(center,weights,strict=True))
            q=params.observed_query;observed=I(q[2])/I(q[4]);mechanical=I(params.liquid_mol)*params.public_native_scale/I(q[6])
            def expand(value):return Interval((value-I(policy.density_expansion)).lo,(value+I(policy.density_expansion)).hi)
            boxes=QueryBoxes(expand(mechanical),expand(observed),logs,center,matrix,weights)
            guard();status='completed_untrusted_proposals'
    except Exception as exc:
        reason=type(exc).__name__+': '+str(exc);failure_kind=category(exc);boxes=None
    try:after=snapshot()
    except Exception as exc:
        reason=type(exc).__name__+': '+str(exc);failure_kind='binding_failure';status='unresolved';boxes=None
    elapsed=time.monotonic()-origin
    if after!=before or elapsed>maximum_wall_seconds:
        status='unresolved';boxes=None;failure_kind='binding_failure' if after!=before else 'resource_limit'
        reason=reason or 'final_seed_binding_or_wall'
    return SeedAttempt(status,failure_kind,reason,boxes,tuple(rows),ancillary_json,entered,completed,elapsed,
                       maximum_evaluations,maximum_wall_seconds,original_policy,original_query,original_source,before,after)
