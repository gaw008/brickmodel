"""Single-owner cumulative mathematical pressure session, no native calls."""
from dataclasses import dataclass, fields
from fractions import Fraction as F
from pathlib import Path
from typing import Callable
import hashlib
import math
import threading
import time
from sludge_sandbox.mass_wet_transport import WetPair
from sludge_sandbox.deforming_solid_storage import _canonical
from sludge_sandbox.mass_wet_pressure_interval import (
    BoundLiquidPressureRequest,LiquidBranchModelPolicy,ProofBudget,encoded,identity,need,
)
from sludge_sandbox.mass_wet_pressure_provider_v2 import StructuredLiquidPressureProvider,StructuredPressureEvidence,BindingFailure,category
from sludge_sandbox.mass_wet_pressure_seed import LiquidSeedPolicy,SeedAttempt,propose_liquid_boxes
from sludge_sandbox import mass_wet_pressure_provider_v2 as provider_module
from sludge_sandbox import mass_wet_pressure_seed as seed_module
from sludge_sandbox import mass_wet_pressure_interval as base_module


@dataclass(frozen=True)
class PressureSessionBudget:
    maximum_seed_evaluations: int
    maximum_proof_operations: int
    maximum_wall_seconds: float
    maximum_boxes_per_primitive: int=256

    def __post_init__(self):
        for n in (self.maximum_seed_evaluations,self.maximum_proof_operations):
            need(type(n) is int and n>=0,'nonnegative_session_work_limits')
        need(type(self.maximum_boxes_per_primitive) is int and self.maximum_boxes_per_primitive>=4,'primitive_box_budget')
        need(type(self.maximum_wall_seconds) is float and math.isfinite(self.maximum_wall_seconds) and self.maximum_wall_seconds>0,'positive_session_wall')


@dataclass(frozen=True)
class PressureQueryAttempt:
    index: int
    context: bytes
    status: str
    failure_kind: str | None
    reason: str | None
    pressure_radius_pa: F | None
    request_sha256: str | None
    current_host_identity: str | None
    modes: tuple
    seed: SeedAttempt | None
    proof: StructuredPressureEvidence | None
    elapsed_seconds: float
    cumulative_seed_attempted: int
    cumulative_seed_completed: int
    cumulative_proof_attempted: int
    cumulative_proof_completed: int
    cost_complete: bool


@dataclass(frozen=True)
class PressureSessionSnapshot:
    original_configuration_json: bytes
    original_physics_json: bytes
    source_before: tuple[str,...]
    attempts: tuple[PressureQueryAttempt,...]
    seed_attempted: int
    seed_completed: int
    proof_attempted: int
    proof_completed: int
    elapsed_seconds: float
    cost_complete: bool
    started_monotonic_s: float
    qualification: str='conditional_mathematical_pressure_session_no_controller_commit_or_native_count'
    bottom_level_residual_evaluation_count: None=None
    native_calls: int=0


def _physics(pair: WetPair) -> bytes:
    need(type(pair) is WetPair,'actual_mixed_pair')
    pair.binding()
    # Exactly two permitted non-physical fields: mode and its derived identity.
    return encoded(tuple((f.name,_canonical(getattr(pair,f.name))) for f in fields(pair)
                         if f.name not in ('interface_modes','_identity')))


def _down(value: F) -> float:
    need(type(value) is F and value>0,'positive_remaining_wall')
    out=float(value)
    if F(out)>value:out=math.nextafter(out,-math.inf)
    if out<=0:raise TimeoutError('remaining_wall_unrepresentable')
    return out


class PressureSession:
    """Synchronous, non-reentrant session; construction starts its one deadline."""

    def __init__(self, original_pair: WetPair, *, branch_policy: LiquidBranchModelPolicy,
                 seed_policy: LiquidSeedPolicy,budget: PressureSessionBudget,
                 caller_guard: Callable[[],None] | None=None,
                 remaining_caller_wall: Callable[[],float] | None=None,
                 cancel: Callable[[],bool] | None=None):
        self._origin=time.monotonic();self._owner=threading.get_ident();self._busy=False
        need(type(branch_policy) is LiquidBranchModelPolicy and type(seed_policy) is LiquidSeedPolicy
             and type(budget) is PressureSessionBudget,'explicit_session_policies')
        branch_policy.__post_init__();seed_policy.__post_init__();budget.__post_init__()
        self._pair=original_pair;self._physics_json=_physics(original_pair)
        self._branch=branch_policy;self._seed=seed_policy;self._budget=budget
        self._config_json=encoded((branch_policy,seed_policy,budget))
        self._caller_guard=caller_guard;self._remaining=remaining_caller_wall;self._cancel=cancel
        self._source=self._source_now();self._attempts=[]
        self._seed_a=self._seed_c=self._proof_a=self._proof_c=0;self._cost_complete=True

    def _source_now(self) -> tuple[str,...]:
        return (*self._branch.check_sources(),*(hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
                 for m in (provider_module,seed_module,base_module)),hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

    def _elapsed(self) -> float:
        return time.monotonic()-self._origin

    def _guard(self, caller_guard=None,cancel=None) -> None:
        if threading.get_ident()!=self._owner:raise RuntimeError('session_single_owner_required')
        if not self._cost_complete:raise RuntimeError('session_child_cost_unknown_no_further_work')
        if encoded((self._branch,self._seed,self._budget))!=self._config_json:raise BindingFailure('session_original_policy_changed')
        try:
            if self._source_now()!=self._source or _physics(self._pair)!=self._physics_json:
                raise BindingFailure('session_original_source_or_physics_changed')
        except Exception as exc:raise BindingFailure(str(exc)) from exc
        if self._caller_guard is not None:self._caller_guard()
        if caller_guard is not None:caller_guard()
        if (self._cancel is not None and self._cancel()) or (cancel is not None and cancel()):raise InterruptedError('session_cancelled')
        if F(self._elapsed())>=F(self._budget.maximum_wall_seconds):raise TimeoutError('session_original_wall_exhausted')

    def _remaining_wall(self, caller_guard=None,remaining=None,cancel=None) -> float:
        self._guard(caller_guard,cancel)
        value=F(self._budget.maximum_wall_seconds)-F(self._elapsed())
        for callback in (self._remaining,remaining):
            if callback is not None:
                bound=callback()
                need(type(bound) in (float,int) and math.isfinite(bound),'finite_caller_remaining_wall')
                value=min(value,F(bound))
        if value<=0:raise TimeoutError('caller_or_session_wall_exhausted')
        return _down(value)

    def snapshot(self) -> PressureSessionSnapshot:
        """Read immutable history even after a binding or callback failure."""
        if threading.get_ident()!=self._owner:raise RuntimeError('session_single_owner_required')
        return PressureSessionSnapshot(self._config_json,self._physics_json,self._source,tuple(self._attempts),
            self._seed_a,self._seed_c,self._proof_a,self._proof_c,self._elapsed(),self._cost_complete,self._origin)

    def query(self, pair: WetPair, states: tuple, cell_rate,cell: int,*,context: bytes,
              caller_guard: Callable[[],None] | None=None,
              remaining_caller_wall: Callable[[],float] | None=None,
              cancel: Callable[[],bool] | None=None) -> PressureQueryAttempt:
        need(type(context) is bytes and context,'immutable_query_context')
        if threading.get_ident()!=self._owner or self._busy:raise RuntimeError('session_single_owner_nonreentrant')
        self._busy=True;start=time.monotonic();seed=proof=request=None
        status='unresolved';failure_kind=None;reason=None;radius=None;unreturned_child=False
        request_sha=current_host_identity=None
        modes=pair.interfaces if type(pair) is WetPair else ()
        def guard():self._guard(caller_guard,cancel)
        def remaining():return self._remaining_wall(caller_guard,remaining_caller_wall,cancel)
        try:
            guard()
            if _physics(pair)!=self._physics_json:raise BindingFailure('query_physics_changed_only_modes_allowed')
            request=BoundLiquidPressureRequest.capture(pair,states,cell_rate,cell)
            request_sha=request.numeric_identity;current_host_identity=request.host_identity
            guard()
            seed_remaining=self._budget.maximum_seed_evaluations-self._seed_a
            if seed_remaining<=0:raise TimeoutError('session_seed_budget_exhausted')
            if self._proof_a>=self._budget.maximum_proof_operations:raise TimeoutError('session_proof_budget_exhausted')
            wall=remaining();unreturned_child=True
            seed=propose_liquid_boxes(request,self._branch,policy=self._seed,
                maximum_evaluations=seed_remaining,maximum_wall_seconds=wall,caller_guard=guard,cancel=cancel)
            need(type(seed) is SeedAttempt and type(seed.attempted) is int and type(seed.completed) is int
                 and 0<=seed.completed<=seed.attempted<=seed_remaining,'typed_child_seed_costs')
            self._seed_a+=seed.attempted;self._seed_c+=seed.completed;unreturned_child=False
            guard()
            if seed.status!='completed_untrusted_proposals':
                failure_kind=seed.failure_kind;reason=seed.reason
            else:
                proof_remaining=self._budget.maximum_proof_operations-self._proof_a
                if proof_remaining<=0:raise TimeoutError('session_proof_budget_exhausted')
                proof_budget=ProofBudget(proof_remaining,self._budget.maximum_boxes_per_primitive,remaining(),self._seed.precision)
                unreturned_child=True
                proof=StructuredLiquidPressureProvider().evaluate(request,branch_policy=self._branch,boxes=seed.boxes,
                    budget=proof_budget,caller_guard=guard,cancel=cancel)
                need(type(proof) is StructuredPressureEvidence and type(proof.attempted_proof_operations) is int
                     and type(proof.completed_proof_operations) is int
                     and 0<=proof.completed_proof_operations<=proof.attempted_proof_operations<=proof_remaining,'typed_child_proof_costs')
                self._proof_a+=proof.attempted_proof_operations;self._proof_c+=proof.completed_proof_operations;unreturned_child=False
                guard()
                if proof.status=='proved_conditional_query':
                    need(proof.request_sha256==request.numeric_identity and type(proof.pressure_radius_pa) is F and proof.pressure_radius_pa>=0,'matching_proved_current_query')
                    status='proved_conditional_query';radius=proof.pressure_radius_pa
                else:failure_kind=proof.failure_kind;reason=proof.reason
        except Exception as exc:
            if unreturned_child:self._cost_complete=False
            failure_kind=category(exc);reason=type(exc).__name__+': '+str(exc);radius=None
        finally:
            self._busy=False
        if status=='proved_conditional_query':
            try:guard()
            except Exception as exc:
                status='unresolved';failure_kind=category(exc);reason=type(exc).__name__+': '+str(exc);radius=None
        attempt=PressureQueryAttempt(len(self._attempts),context,status,failure_kind,reason,radius,
            request_sha,current_host_identity,
            modes,seed,proof,time.monotonic()-start,self._seed_a,self._seed_c,self._proof_a,self._proof_c,self._cost_complete)
        self._attempts.append(attempt)
        return attempt
