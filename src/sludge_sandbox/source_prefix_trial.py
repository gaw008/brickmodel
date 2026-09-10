"""Actually evaluated positive source prefix, not a physical event executor."""
from dataclasses import dataclass, fields, replace
from fractions import Fraction as F
import math
import time
import numpy as np
from .exact_event_clock import ExactEventTime as T
from .exact_source_column import ExactSourceColumn, SourceExactEvaluation
from .exact_integration import advance_exact_euler, integrate_exact, ExactIntegrationResult
from .integration import ConservedState, IntegrationPolicy, IntegrationError, DomainExit, _Reject
from .source_net_panel import SavedSourceSample, build_source_panel, _validate
from .source_net_prefix import SourcePrefix, build_source_prefix, audit_source_prefixes, _same
from .source_wet_storage import SourceWetInverse


def _require(ok, reason):
    if not ok:
        raise IntegrationError(reason)


def _policy_binding(policy):
    return tuple((f.name, getattr(policy, f.name)) for f in fields(policy))


def _positive(state):
    return np.all(state.amounts_mol > 0)


def normalized_prefix_discrepancy(prefix: ConservedState, reference: ConservedState,
                                  policy: IntegrationPolicy) -> float:
    """Direct cross-construction discrepancy, without an error-estimator factor."""
    _require(type(policy) is IntegrationPolicy, 'actual_trial_policy_required')
    policy.__post_init__()
    _require(type(prefix) is type(reference) is ConservedState, 'trial_comparison_state_binding')
    _require(all(type(a) is np.ndarray and a.dtype==np.float64 and a.size>0
                 and np.all(np.isfinite(a)) for s in (prefix,reference)
                 for a in (s.amounts_mol,s.internal_energy_j)), 'trial_comparison_finite_binary64_arrays')
    _require(type(prefix) is type(reference) is ConservedState
             and prefix.amounts_mol.shape == reference.amounts_mol.shape
             and prefix.internal_energy_j.shape == reference.internal_energy_j.shape
             and prefix.energy_model_identity == reference.energy_model_identity
             and prefix.mechanical_stretches is reference.mechanical_stretches is None,
             'trial_comparison_state_binding')
    nscale=policy.amount_absolute_tolerance_mol+policy.relative_tolerance*policy.amount_scale_mol
    uscale=policy.energy_absolute_tolerance_j+policy.relative_tolerance*policy.energy_scale_j
    _require(all(math.isfinite(x) and x>0 for x in (nscale,uscale)), 'finite_trial_comparison_scales')
    value=max(float(np.max(np.abs(prefix.amounts_mol-reference.amounts_mol)))/nscale,
              float(np.max(np.abs(prefix.internal_energy_j-reference.internal_energy_j)))/uscale)
    _require(math.isfinite(value), 'finite_trial_discrepancy')
    return value


def _bounds(evaluation):
    result=[]
    for cell in evaluation.source_evaluation.cells:
        inverse=cell.inverse
        _require(type(inverse) is SourceWetInverse, 'actual_source_terminal_inverse')
        point=inverse.point
        row=(point.temperature_k,inverse.temperature_error_bound_k,
             point.pressure_pa,point.pressure_error_pa)
        _require(all(type(v) is float and math.isfinite(v) for v in row)
                 and row[0]>0 and row[1]>=0 and row[2]>0 and row[3]>=0,
                 'finite_source_terminal_bounds')
        result.append(row)
    return tuple(result)


def _attempt_input(ordinal,role,state,when):
    _require(type(when) is T and type(when.seconds) is F, 'trial_attempt_exact_time_required')
    _require(type(state) is ConservedState and state.mechanical_stretches is None
             and all(type(a) is np.ndarray and a.dtype==np.float64 and np.all(np.isfinite(a))
                     for a in (state.amounts_mol,state.internal_energy_j)),
             'trial_attempt_binary64_input_required')
    return (ordinal,role,T(when.seconds),state.energy_model_identity,
            tuple(tuple(map(float,row)) for row in state.amounts_mol),
            tuple(map(float,state.internal_energy_j)))


@dataclass(frozen=True)
class TrialCapture:
    ordinal: int
    role: str
    state: ConservedState
    time: T
    evaluation: SourceExactEvaluation | None = None
    binding: str | None = None
    failure: str | None = None
    input_binding: tuple = ()
    failure_binding: tuple = (None,None)
    failure_kind: str | None = None


@dataclass(frozen=True)
class SourcePrefixTrial:
    adapter: ExactSourceColumn
    initial: ConservedState
    start: T
    end: T
    policy: IntegrationPolicy
    policy_binding: tuple
    maximum_callbacks: int
    controls_binding: tuple
    operator_identity: tuple
    energy_identity: tuple
    fixed_dry_mass_kg: tuple
    captures: tuple[TrialCapture, ...]
    predictor: ConservedState | None
    prefix: SourcePrefix | None
    terminal_bounds: tuple
    reference_policy: IntegrationPolicy | None
    reference_policy_binding: tuple | None
    reference: ExactIntegrationResult | None
    discrepancy: float | None
    status: str
    reason: str | None
    outcome_binding: tuple
    elapsed_seconds: float
    qualification: str = 'source_numerical_trial_not_event_material_or_dry_mode_admission'

    def check(self) -> None:
        """Recheck retained numerical/binding evidence, without another evaluation."""
        _require(_same(self.outcome_binding,(self.status,self.reason)), 'trial_original_outcome_binding')
        _require(_same(self.controls_binding,(self.start,self.end,self.maximum_callbacks)),
                 'trial_original_controls_binding')
        _require(type(self.adapter) is ExactSourceColumn and type(self.policy) is IntegrationPolicy,
                 'trial_original_types')
        _require(_same(self.policy_binding,_policy_binding(self.policy)), 'trial_original_policy_binding')
        self.policy.__post_init__()
        _require(self.adapter.operator_identity==self.operator_identity
                 and self.adapter.energy_model_identity==self.energy_identity
                 and tuple(s.dry_mass_kg for s in self.adapter.column.storages)==self.fixed_dry_mass_kg,
                 'trial_operator_binding_changed')
        _require(type(self.captures) is tuple and type(self.maximum_callbacks) is int
                 and self.maximum_callbacks>0 and len(self.captures)<=self.maximum_callbacks,
                 'trial_callback_accounting')
        _check_source_captures(self.captures,start=self.start,end=self.end,
            operator_identity=self.operator_identity,energy_identity=self.energy_identity,masses=self.fixed_dry_mass_kg)
        if self.captures:
            _require(self.captures[0].time==self.start and self.captures[0].role=='initial'
                     and _same(self.captures[0].state,self.initial),'trial_initial_capture_binding')
        if self.predictor is not None:
            _require(bool(self.captures) and self.captures[0].evaluation is not None,'trial_predictor_initial_observation')
            expected=advance_exact_euler(self.initial,self.captures[0].evaluation.rates,
                                         self.end.elapsed_since(self.start)/2,self.policy)
            _require(_same(expected,self.predictor),'trial_predictor_changed')
        if self.prefix is not None:
            _require(type(self.prefix) is SourcePrefix,'actual_source_trial_prefix_required')
            self.prefix.check()
            _require(_same(self.prefix.policy_binding,self.policy_binding),'trial_prefix_policy_changed')
            _require(len(self.captures)>=2 and _same(self.prefix.panel.first.state,self.initial)
                     and _same(self.prefix.panel.interior.state,self.predictor)
                     and self.prefix.end==self.end
                     and self.captures[1].time==self.start.shifted(self.end.elapsed_since(self.start)/2)
                     and self.prefix.panel.sample_bindings[:2]==(self.captures[0].binding,self.captures[1].binding),
                     'trial_prefix_capture_binding')
        for capture in self.captures:
            if capture.role=='euler_midpoint':
                _require(self.predictor is not None and _same(capture.state,self.predictor)
                         and capture.time==self.start.shifted(self.end.elapsed_since(self.start)/2),
                         'trial_midpoint_attempt_binding')
            if capture.role=='prefix_terminal':
                _require(self.prefix is not None and _same(capture.state,self.prefix.raw_state)
                         and capture.time==self.end,'trial_terminal_attempt_binding')
        if self.reference_policy is not None:
            _require(type(self.reference_policy) is IntegrationPolicy and
                     _same(self.reference_policy_binding,_policy_binding(self.reference_policy)),
                     'trial_reference_policy_binding')
            self.reference_policy.__post_init__()
            _require(all(_same(getattr(self.reference_policy,f.name),getattr(self.policy,f.name))
                         for f in fields(self.policy) if f.name!='maximum_wall_seconds')
                     and 0<self.reference_policy.maximum_wall_seconds<=self.policy.maximum_wall_seconds,
                     'trial_reference_policy_changed')
        if self.status=='validated_positive_numerical_trial':
            _require(self.reason is None and self.prefix is not None
                     and self.prefix.status=='strictly_positive_numerical_prefix'
                     and len(self.captures)>=4 and [c.role for c in self.captures[:3]]==
                     ['initial','euler_midpoint','prefix_terminal'], 'trial_success_evidence_missing')
            terminal=self.captures[2]
            _require(terminal.time==self.end and _same(terminal.state,self.prefix.raw_state)
                     and _same(self.terminal_bounds,_bounds(terminal.evaluation)), 'trial_terminal_binding')
            _complete_reference(self.reference,self.start,self.end,self.initial)
            _require(self.reference_policy is not None and all(c.role=='reference' for c in self.captures[3:])
                     and all(c.evaluation is not None and c.binding is not None and c.failure is None for c in self.captures[:3])
                     and all((c.evaluation is not None and c.binding is not None and c.failure is None)
                             or (c.failure_kind=='DomainExit' and type(c.failure) is str)
                             for c in self.captures[3:])
                     and len(self.captures)-3==self.reference.evaluations
                     and _same(self.captures[-1].state,self.reference.states[-1])
                     and self.captures[-1].time==self.end,'trial_reference_capture_binding')
            _replay_reference(self)
            value=normalized_prefix_discrepancy(self.prefix.raw_state,self.reference.states[-1],self.policy)
            _require(type(self.discrepancy) is float and value==self.discrepancy and value<=1,
                     'trial_discrepancy_changed')
        _require(self.qualification=='source_numerical_trial_not_event_material_or_dry_mode_admission',
                 'trial_qualification_changed')


def _check_source_captures(captures,*,start,end,operator_identity,energy_identity,masses):
    """Revalidate saved attempts for one unchanged source operator, without EOS."""
    for i,capture in enumerate(captures):
        _require(type(capture) is TrialCapture and type(capture.ordinal) is int
                 and capture.ordinal==i+1 and type(capture.time) is T
                 and start<=capture.time<=end, 'trial_capture_order')
        _require(_same(capture.input_binding,_attempt_input(capture.ordinal,capture.role,capture.state,capture.time))
                 and _same(capture.failure_binding,(capture.failure_kind,capture.failure)), 'trial_attempt_input_failure_binding')
        _require((capture.binding is not None and capture.evaluation is not None)
                 or type(capture.failure) is str and capture.failure_kind in ('DomainExit','IntegrationError','TrialStop','UnexpectedException'),
                 'trial_capture_validation_or_failure_required')
        if capture.evaluation is not None and capture.binding is not None:
            _require(capture.time==capture.evaluation.time,'trial_capture_exact_time_binding')
            binding=_validate(SavedSourceSample(capture.state,capture.evaluation,capture.role),
                              operator_identity,energy_identity,masses)
            _require(binding==capture.binding, 'trial_capture_source_binding')


def _replay_reference(trial):
    return _replay_source_reference(trial.initial,trial.start,trial.end,
        replace(trial.reference_policy,maximum_wall_seconds=trial.policy.maximum_wall_seconds),
        trial.captures[3:],trial.reference)


def _replay_source_reference(initial, start, end, policy, captures, reference, *, breakpoints=()):
    """Replay retained RHS outputs in the original integrator, with no physics.

    All original numerical gates and requested input states/times must match.
    Replay wall duration is not an execution-cost certificate.
    """
    saved=captures;cursor=0
    def callback(state,when):
        nonlocal cursor
        _require(cursor<len(saved),'trial_reference_replay_missing_capture')
        capture=saved[cursor];cursor+=1
        _require(capture.time==when and _same(capture.state,state),
                 'trial_reference_replay_input_changed')
        if capture.failure_kind=='DomainExit':
            raise DomainExit(capture.failure)
        _require(capture.failure is None and capture.evaluation is not None,
                 'trial_reference_replay_unexpected_failure')
        return capture.evaluation.rates
    replay=integrate_exact(initial,callback,start_s=start,end_s=end,
        policy=policy,breakpoints_s=breakpoints)
    _require(cursor==len(saved) and all(_same(getattr(replay,f.name),getattr(reference,f.name))
             for f in fields(replay) if f.name!='elapsed_seconds'), 'trial_reference_replay_changed')


def _complete_reference(reference,start,end,initial):
    _require(type(reference) is ExactIntegrationResult and reference.status=='completed'
             and bool(reference.times_s) and reference.times_s[0]==start and reference.times_s[-1]==end
             and len(reference.times_s)==len(reference.states)==len(reference.steps)+1
             and _same(reference.states[0],initial),'trial_reference_incomplete_interval')


class _TrialStop(Exception):
    def __init__(self,status,reason):
        super().__init__(reason)
        self.status=status


def _capture_source_observation(adapter,state,when,role,captures,*,maximum_callbacks,
        guard,operator_identity,energy_identity,masses):
    """Save actual attempts and returns before validation or cancellation can fail."""
    guard()
    if len(captures)>=maximum_callbacks:raise _TrialStop('resource_limit','trial_callback_limit')
    ordinal=len(captures)+1
    captures.append(TrialCapture(ordinal,role,state,when,
        input_binding=_attempt_input(ordinal,role,state,when)))
    try:
        evaluation=adapter.evaluate(state,when)
        captures[-1]=replace(captures[-1],evaluation=evaluation)
        value=_validate(SavedSourceSample(state,evaluation,role),operator_identity,energy_identity,masses)
        captures[-1]=replace(captures[-1],binding=value)
        guard()
        return evaluation
    except (DomainExit,IntegrationError,_TrialStop) as exc:
        kind='DomainExit' if isinstance(exc,DomainExit) else 'TrialStop' if isinstance(exc,_TrialStop) else 'IntegrationError'
        captures[-1]=replace(captures[-1],failure=str(exc),failure_kind=kind,failure_binding=(kind,str(exc)))
        raise
    except ValueError as exc:
        captures[-1]=replace(captures[-1],failure=str(exc),failure_kind='IntegrationError',failure_binding=('IntegrationError',str(exc)))
        raise IntegrationError('source_column_callback:'+str(exc)) from exc
    except Exception as exc:
        diagnostic=type(exc).__name__+':'+str(exc)
        captures[-1]=replace(captures[-1],failure=diagnostic,failure_kind='UnexpectedException',failure_binding=('UnexpectedException',diagnostic))
        raise IntegrationError('unexpected_source_callback_exception:'+diagnostic) from exc


def evaluate_source_prefix_trial(adapter: ExactSourceColumn, initial: ConservedState, *,
        start: T, end: T, integration_policy: IntegrationPolicy,
        maximum_callbacks: int, cancel=None) -> SourcePrefixTrial:
    _require(type(adapter) is ExactSourceColumn and type(initial) is ConservedState
             and type(integration_policy) is IntegrationPolicy,'actual_source_trial_inputs_required')
    integration_policy.__post_init__()
    _require(type(start) is type(end) is T and start<end,'exact_source_trial_interval')
    _require(type(maximum_callbacks) is int and maximum_callbacks>0
             and (cancel is None or callable(cancel)), 'source_trial_resource_controls')
    policy=replace(integration_policy)
    binding=_policy_binding(policy)
    operator_identity=adapter.operator_identity; energy_identity=adapter.energy_model_identity
    masses=tuple(s.dry_mass_kg for s in adapter.column.storages)
    begin=time.monotonic();captures=[];predictor=prefix=reference_policy=reference=discrepancy=None
    terminal_bounds=();stop=None;reference_policy_binding=None
    def guard():
        _require(_same(binding,_policy_binding(policy)),'trial_original_policy_binding')
        _require(adapter.operator_identity==operator_identity,'trial_operator_binding_changed')
        if cancel is not None and cancel():raise _TrialStop('cancelled','cancel_requested')
        if time.monotonic()-begin>=policy.maximum_wall_seconds:raise _TrialStop('resource_limit','trial_total_wall_time_limit')
    def observe(state,when,role):
        return _capture_source_observation(adapter,state,when,role,captures,
            maximum_callbacks=maximum_callbacks,guard=guard,operator_identity=operator_identity,
            energy_identity=energy_identity,masses=masses)
    def callback(state,when):
        nonlocal stop
        try:return observe(state,when,'reference').rates
        except _TrialStop as exc:
            stop=exc
            raise IntegrationError(str(exc)) from exc
    try:
        guard();adapter.unpack(initial)
        if not _positive(initial):raise _TrialStop('unsupported','source_trial_nonpositive_initial_inventory')
        if adapter.breakpoints(start,end):raise _TrialStop('unsupported','source_trial_interior_program_knot')
        first=observe(initial,start,'initial')
        midpoint=start.shifted(end.elapsed_since(start)/2)
        predictor=advance_exact_euler(initial,first.rates,midpoint.elapsed_since(start),policy)
        if not _positive(predictor):raise _TrialStop('unsupported','source_trial_nonpositive_predictor_inventory')
        middle=observe(predictor,midpoint,'euler_midpoint')
        panel=build_source_panel(SavedSourceSample(initial,first,'initial'),
            SavedSourceSample(predictor,middle,'euler_midpoint'),end,
            operator_identity=operator_identity,energy_identity=energy_identity,fixed_dry_mass_kg=masses)
        prefix=build_source_prefix(panel,end,policy=policy)
        if prefix.status!='strictly_positive_numerical_prefix':
            raise _TrialStop('unsupported','source_trial_numerical_boundary')
        audit_source_prefixes((prefix,))
        terminal=observe(prefix.raw_state,end,'prefix_terminal')
        terminal_bounds=_bounds(terminal)
        guard()
        remaining=policy.maximum_wall_seconds-(time.monotonic()-begin)
        if remaining<=0:raise _TrialStop('resource_limit','trial_total_wall_time_limit')
        reference_policy=replace(policy,maximum_wall_seconds=remaining)
        reference_policy_binding=_policy_binding(reference_policy)
        reference=integrate_exact(initial,callback,start_s=start,end_s=end,policy=reference_policy,
                                  breakpoints_s=adapter.breakpoints(start,end),cancel=cancel)
        if stop is not None:raise stop
        guard()
        if reference.status!='completed':raise _TrialStop(reference.status,'reference:'+str(reference.reason))
        _complete_reference(reference,start,end,initial)
        discrepancy=normalized_prefix_discrepancy(prefix.raw_state,reference.states[-1],policy)
        if discrepancy>1:raise _TrialStop('numerical_failure','source_trial_reference_discrepancy')
        status='validated_positive_numerical_trial';reason=None
    except _TrialStop as exc:status=exc.status;reason=str(exc)
    except DomainExit as exc:status='domain_exit';reason=str(exc)
    except _Reject as exc:status='numerical_failure';reason=str(exc)
    except (ValueError,TypeError,AttributeError,OverflowError) as exc:status='numerical_failure';reason=str(exc)
    result=SourcePrefixTrial(adapter,initial,start,end,policy,binding,maximum_callbacks,(start,end,maximum_callbacks),
        operator_identity,energy_identity,masses,tuple(captures),predictor,prefix,terminal_bounds,
        reference_policy,reference_policy_binding,reference,discrepancy,status,reason,(status,reason),time.monotonic()-begin)
    if status=='validated_positive_numerical_trial':
        try:
            result.check()
            guard()
        except _TrialStop as exc:
            result=replace(result,status=exc.status,reason=str(exc),outcome_binding=(exc.status,str(exc)))
        except (ValueError,TypeError,AttributeError,OverflowError) as exc:
            result=replace(result,status='numerical_failure',reason=str(exc),outcome_binding=('numerical_failure',str(exc)))
    return replace(result,elapsed_seconds=time.monotonic()-begin)
