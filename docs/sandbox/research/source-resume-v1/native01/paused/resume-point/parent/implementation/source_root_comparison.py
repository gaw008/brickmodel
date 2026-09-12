"""Actual partitioned source paths and surrogate-root comparison.

A shifted panel is not a 2:1 Richardson refinement. Positive common endpoints
are compared separately from surrogate root times; neither admits a dry event.
"""
from dataclasses import dataclass, fields, replace
from fractions import Fraction as F

from .exact_event_clock import ExactEventTime as T, ExactTimeInterval
from .exact_integration import _duration_control
from .integration import IntegrationError
from .source_approach import (
    PositiveApproachChoice, SourceApproachResult, SourceApproachProposal,
    propose_source_approach,
)
from .source_endpoint_comparison import (
    SourceEndpointDifferences, _copy_policy, measure_source_endpoint_pair,
)
from .source_inverse_pressure import SourceInversePressure, enclose_source_inverse_pressure
from .source_net_panel import SavedSourceSample
from .source_net_prefix import _same
from .source_net_roots import QuadraticRoot, refine_first_root
from .source_prefix_trial import SourcePrefixTrial, evaluate_source_prefix_trial


def _require(ok, reason):
    if not ok:
        raise IntegrationError(reason)


@dataclass(frozen=True)
class SourceRootClockComparison:
    choices: tuple[PositiveApproachChoice, PositiveApproachChoice]
    starts: tuple[T, T]
    time_absolute_s: F
    refined_roots: tuple[QuadraticRoot, QuadraticRoot]
    additional_rounds: tuple[int, int]
    intervals: tuple[ExactTimeInterval, ExactTimeInterval]
    distance_lower_s: F
    distance_upper_s: F
    gate: bool
    qualification: str = 'partitioned_surrogate_root_comparison_not_physical_time_error'

    def check(self):
        expected = compare_source_root_clocks(self.choices,self.starts,time_absolute_s=self.time_absolute_s)
        _require(_same(self,expected), 'source_root_clock_comparison_changed')


def compare_source_root_clocks(choices, starts, *, time_absolute_s: F) -> SourceRootClockComparison:
    """Compare absolute root intervals; further narrowing uses each remaining budget."""
    _require(type(choices) is tuple and len(choices)==2
             and all(type(c) is PositiveApproachChoice for c in choices), 'two_actual_root_choices_required')
    _require(type(starts) is tuple and len(starts)==2
             and all(type(t) is T and type(t.seconds) is F for t in starts)
             and type(time_absolute_s) is F and time_absolute_s>0, 'exact_root_comparison_times_required')
    for c in choices:
        c.check()
        _require(c.status=='positive_numerical_proposal', 'two_positive_root_proposals_required')
    _require(choices[0].order.earliest_labels==choices[1].order.earliest_labels,
             'partitioned_first_inventory_label_changed')
    roots, rounds, intervals = [], [], []
    for c,start in zip(choices,starts):
        root = c.selected_root
        remaining = c.order.maximum_refinements-c.order.refinement_level-c.additional_refinement_rounds
        used = 0
        while root.upper-root.lower>time_absolute_s/4 and used<remaining:
            root = refine_first_root(root)
            used += 1
        roots.append(root)
        rounds.append(used)
        intervals.append(ExactTimeInterval(start.shifted(root.lower),start.shifted(root.upper)))
    a,b = intervals
    lower = max(F(),a.lower.elapsed_since(b.upper),b.lower.elapsed_since(a.upper))
    upper = max(abs(a.lower.elapsed_since(b.upper)),abs(a.upper.elapsed_since(b.lower)))
    return SourceRootClockComparison(choices,starts,time_absolute_s,tuple(roots),tuple(rounds),
        tuple(intervals),lower,upper,upper<=time_absolute_s)


def _snapshot_approach(approach):
    _require(type(approach) is SourceApproachResult, 'actual_source_approach_required')
    approach.check()
    _require(approach.status=='validated_positive_numerical_approach', 'validated_source_approach_required')
    proposal = replace(approach.proposal,event_policy=_copy_policy(approach.proposal.event_policy))
    return replace(approach,proposal=proposal)


@dataclass(frozen=True)
class SourceRootRefinement:
    approach: SourceApproachResult
    shifted_trial: SourcePrefixTrial
    shifted_proposal: SourceApproachProposal
    clock: SourceRootClockComparison | None
    status: str
    reason: str | None
    new_evaluations: int
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self):
        expected = compare_source_root_trials(self.approach,self.shifted_trial)
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name)) for f in fields(self)
                     if f.name not in ('approach','shifted_trial')), 'source_root_refinement_changed')


def compare_source_root_trials(approach, shifted_trial) -> SourceRootRefinement:
    """Bind a fresh shifted trial to the actual preceding reference endpoint."""
    approach = _snapshot_approach(approach)
    _require(type(shifted_trial) is SourcePrefixTrial, 'actual_shifted_source_trial_required')
    shifted_trial.check()
    prior, original = approach.trial, approach.proposal.original_trial
    _require(_same((shifted_trial.initial,shifted_trial.start,shifted_trial.end,shifted_trial.policy),
                  (prior.reference.states[-1],prior.end,original.end,original.policy))
             and shifted_trial.operator_identity==original.operator_identity
             and shifted_trial.energy_identity==original.energy_identity
             and shifted_trial.fixed_dry_mass_kg==original.fixed_dry_mass_kg,
             'shifted_trial_reference_connection_changed')
    _require(shifted_trial.start<original.start.shifted(approach.proposal.choice.selected_root.lower),
             'shifted_start_not_before_coarse_first_root')
    proposal = propose_source_approach(shifted_trial,event_policy=approach.proposal.event_policy)
    clock = None
    status,reason = 'root_comparison_not_available',proposal.status
    if proposal.status=='positive_numerical_proposal':
        if proposal.roots.order.earliest_labels!=approach.proposal.roots.order.earliest_labels:
            reason = 'partitioned_first_inventory_label_changed'
        else:
            clock = compare_source_root_clocks((approach.proposal.choice,proposal.choice),
                (original.start,shifted_trial.start),time_absolute_s=F(proposal.event_policy.time_absolute_s))
            status = 'partitioned_surrogate_roots_compared'
            reason = None
    return SourceRootRefinement(approach,shifted_trial,proposal,clock,status,reason,len(shifted_trial.captures))


class SourceRootStudyError(IntegrationError):
    """Execution/assessment failure retaining every already returned actual trial."""

    def __init__(self, stage: str, records: tuple, cause: Exception):
        self.stage, self.records = stage, records
        self.exception_type, self.exception_message = type(cause).__name__, str(cause)
        super().__init__(f'source_root_study_failed:{stage}:{type(cause).__name__}:{cause}')


def evaluate_source_root_refinement(approach, *, maximum_callbacks: int, cancel=None) -> SourceRootRefinement:
    """Run one shifted source trial, with the original integration/event policies."""
    approach = _snapshot_approach(approach)
    _require(type(maximum_callbacks) is int and maximum_callbacks>0
             and (cancel is None or callable(cancel)), 'explicit_root_refinement_resources_required')
    original,prior = approach.proposal.original_trial,approach.trial
    trial = evaluate_source_prefix_trial(original.adapter,prior.reference.states[-1],
        start=prior.end,end=original.end,integration_policy=original.policy,
        maximum_callbacks=maximum_callbacks,cancel=cancel)
    try:
        result = compare_source_root_trials(approach,trial)
        result.check()
        return result
    except Exception as exc:
        raise SourceRootStudyError('shifted_root_assessment',(approach,trial),exc) from exc


def positive_source_common_end(refinement: SourceRootRefinement) -> T:
    """Select a positive extension capped by the original maximum reference step.

    The coarse trial's full interval may span several reference steps. Its
    integrate_exact reference still enforces the original per-step maximum;
    the cross-method trial discrepancy checks its longer affine approximation.
    """
    _require(type(refinement) is SourceRootRefinement, 'actual_source_root_refinement_required')
    refinement.check()
    _require(refinement.clock is not None, 'compared_source_roots_required')
    start = refinement.shifted_trial.start
    lower = min(x.lower for x in refinement.clock.intervals)
    policy = refinement.approach.proposal.original_trial.policy
    fraction = F(refinement.approach.proposal.event_policy.safe_inventory_fraction)
    _require(start<lower, 'no_common_positive_interval')
    h = _duration_control(min(fraction*lower.elapsed_since(start),F(policy.maximum_step_s),
        refinement.shifted_trial.end.elapsed_since(start)))
    _require(h>=F(policy.minimum_step_s), 'common_interval_below_original_minimum_step')
    return start.shifted(h)


def _joined_reference_residuals(trials):
    """Check every cumulative prefix from the shared origin, without restarting its budget."""
    first = trials[0]
    original,policy = first.initial,first.policy
    ncell,nvar = original.amounts_mol.shape
    sums_n, sums_u = [F()]*(ncell*nvar), [F()]*ncell
    previous,time = original,first.start
    rows = []
    for trial in trials:
        _require(trial.status=='validated_positive_numerical_trial'
                 and _same((trial.initial,trial.start,trial.policy),(previous,time,policy)),
                 'source_reference_chain_connection_changed')
        for state,ledger in zip(trial.reference.states[1:],trial.reference.steps):
            nr,ur = [],[]
            for i in range(ncell):
                for j in range(nvar):
                    index = i*nvar+j
                    sums_n[index] += F(float(ledger.face_species_mol[i,j]))-F(float(ledger.face_species_mol[i+1,j]))+F(float(ledger.reaction_species_mol[i,j]))
                    nr.append(F(float(state.amounts_mol[i,j]))-F(float(original.amounts_mol[i,j]))-sums_n[index])
                sums_u[i] += F(float(ledger.face_energy_j[i]))-F(float(ledger.face_energy_j[i+1]))+F(float(ledger.cell_work_j[i]))
                ur.append(F(float(state.internal_energy_j[i]))-F(float(original.internal_energy_j[i]))-sums_u[i])
            _require(all(abs(v)<=F(policy.amount_absolute_tolerance_mol) for v in nr),
                     'joined_source_cumulative_amount_roundoff')
            _require(all(abs(v)<=F(policy.energy_absolute_tolerance_j) for v in ur),
                     'joined_source_cumulative_energy_roundoff')
            rows.append((ledger.end_s,tuple(nr),tuple(ur)))
        previous,time = trial.reference.states[-1],trial.end
    return tuple(rows)


@dataclass(frozen=True)
class SourceCommonEndpointComparison:
    refinement: SourceRootRefinement
    coarse_trial: SourcePrefixTrial
    shifted_trial: SourcePrefixTrial
    common_end: T
    cumulative_residuals: tuple
    differences: SourceEndpointDifferences
    pressure_pairs: tuple[tuple[SourceInversePressure, SourceInversePressure], ...]
    conditional_pressure_bounds_pa: tuple[F | None, ...]
    gates: tuple[bool, ...]
    conditional_pressure_gate: bool | None
    status: str
    new_evaluations: int
    qualification: str = 'positive_common_reference_endpoint_not_event_state_comparison'
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self):
        expected = compare_source_common_trials(self.refinement,self.coarse_trial,self.shifted_trial)
        _require(type(self.pressure_pairs) is tuple and bool(self.pressure_pairs)
                 and all(type(pair) is tuple and len(pair)==2
                         and all(type(v) is SourceInversePressure for v in pair) for pair in self.pressure_pairs),
                 'actual_common_pressure_pairs_required')
        for pair in self.pressure_pairs:
            for value in pair:
                value.check()
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name)) for f in fields(self)
                     if f.name not in ('refinement','coarse_trial','shifted_trial')),
                 'source_common_endpoint_comparison_changed')


def _common_inputs(refinement, end):
    _require(type(refinement) is SourceRootRefinement, 'actual_source_root_refinement_required')
    refinement.check()
    _require(refinement.clock is not None and type(end) is T and type(end.seconds) is F
             and refinement.shifted_trial.start<end<min(x.lower for x in refinement.clock.intervals),
             'common_endpoint_must_precede_both_first_roots')
    original = refinement.approach.proposal.original_trial
    _require(not original.adapter.breakpoints(original.start,end), 'common_interval_crosses_program_knot')
    for choice,start in zip(refinement.clock.choices,refinement.clock.starts):
        duration = end.elapsed_since(start)
        _require(duration>=F(original.policy.minimum_step_s)
                 and all(p.minimum(duration)[0]>0 for p in choice.order.polynomials),
                 'common_interval_not_strictly_positive')
    return original


def compare_source_common_trials(refinement, coarse_trial, shifted_trial) -> SourceCommonEndpointComparison:
    """Compare two actual reference endpoints after checking their complete path connection."""
    _require(type(coarse_trial) is type(shifted_trial) is SourcePrefixTrial,
             'two_actual_common_source_trials_required')
    original = _common_inputs(refinement,coarse_trial.end)
    previous = refinement.approach.trial
    for trial,initial,start in ((coarse_trial,original.initial,original.start),
                                (shifted_trial,previous.reference.states[-1],previous.end)):
        trial.check()
        _require(trial.status=='validated_positive_numerical_trial'
                 and _same((trial.initial,trial.start,trial.end,trial.policy),
                           (initial,start,coarse_trial.end,original.policy))
                 and trial.operator_identity==original.operator_identity
                 and trial.energy_identity==original.energy_identity
                 and trial.fixed_dry_mass_kg==original.fixed_dry_mass_kg,
                 'common_source_path_connection_changed')
    residuals = (_joined_reference_residuals((coarse_trial,)),
                 _joined_reference_residuals((previous,shifted_trial)))
    captures = (coarse_trial.captures[-1],shifted_trial.captures[-1])
    samples = tuple(SavedSourceSample(c.state,c.evaluation,c.role) for c in captures)
    differences = measure_source_endpoint_pair(*samples,operator_identity=original.operator_identity,
        energy_identity=original.energy_identity,fixed_dry_mass_kg=original.fixed_dry_mass_kg)
    event = refinement.approach.proposal.event_policy
    limits = (event.amount_absolute_mol,event.energy_absolute_j,event.temperature_absolute_k,event.pressure_absolute_pa)
    gates = tuple(value<=F(limit) for value,limit in zip(differences.maxima,limits))
    pairs = tuple(tuple(enclose_source_inverse_pressure(storage,c.evaluation.source_states[i],
                    c.evaluation.source_evaluation.cells[i].inverse) for c in captures)
                  for i,storage in enumerate(original.adapter.column.storages))
    bounds = tuple(abs(F(a.inverse.point.pressure_pa)-F(b.inverse.point.pressure_pa))
                   +a.continuation.radius_pa+b.continuation.radius_pa
                   if a.continuation.status==b.continuation.status=='conditional_pressure_enclosure' else None
                   for a,b in pairs)
    pressure_gate = (max(bounds)<=F(event.pressure_absolute_pa) if all(v is not None for v in bounds) else None)
    status = 'positive_endpoint_gates_satisfied' if all(gates) else 'positive_endpoint_tolerance_not_certified'
    return SourceCommonEndpointComparison(refinement,coarse_trial,shifted_trial,coarse_trial.end,residuals,
        differences,pairs,bounds,gates,pressure_gate,status,len(coarse_trial.captures)+len(shifted_trial.captures))


def evaluate_source_common_endpoint(refinement, *, end: T, maximum_callbacks_per_trial: int,
        cancel=None) -> SourceCommonEndpointComparison:
    """Run both positive paths once. Budgets are per trial, not a whole-study allowance.

    A trial interval may cover multiple original maximum_step_s reference steps;
    that policy limits integration steps, not the complete study interval.
    Failures retain returned trials in SourceRootStudyError. The caller controls
    the outer study's total runtime; no automatic retry or dry transition occurs.
    """
    original = _common_inputs(refinement,end)
    _require(type(maximum_callbacks_per_trial) is int and maximum_callbacks_per_trial>0
             and (cancel is None or callable(cancel)), 'explicit_common_trial_resources_required')
    # Detach the complete event policy before either path calls external physics.
    refinement = replace(refinement,approach=_snapshot_approach(refinement.approach))
    previous = refinement.approach.trial
    records = []
    stage = 'coarse_common_trial'
    try:
        for initial,start in ((original.initial,original.start),(previous.reference.states[-1],previous.end)):
            trial = evaluate_source_prefix_trial(original.adapter,initial,start=start,end=end,
                integration_policy=original.policy,maximum_callbacks=maximum_callbacks_per_trial,cancel=cancel)
            records.append(trial)
            _require(trial.status=='validated_positive_numerical_trial',
                     'common_trial_not_validated:'+trial.status+':'+str(trial.reason))
            stage = 'shifted_common_trial'
        stage = 'common_endpoint_assessment'
        result = compare_source_common_trials(refinement,*records)
        result.check()
        return result
    except Exception as exc:
        raise SourceRootStudyError(stage,(refinement,*records),exc) from exc
