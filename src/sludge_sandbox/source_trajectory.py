"""Advance a selected source-study endpoint with a real reconstructed column.

This is a new ordinary segment after an admitted numerical transition. Its
accepted-boundary checkpoint is local to this live session; it does not restore
the historical study controller or authorize archived source-run resume.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
import math
from pathlib import Path
import time

from .exact_event_clock import ExactEventTime as T
from .integration import IntegrationError, IntegrationPolicy
from .run_service import RunError, read_run_with_source_record, runtime_identity
from .source_dry_transition import _audit_balance_fields
from .source_net_prefix import _same
from .source_run_builder import _snapshot, build_source_run
from .source_run_config import load_source_run_config, validate_source_run_assets
from .source_run_observer import observer_scope
from .source_run_service import KIND, _Recorder, _read
from .source_study_schema import reify


def _require(condition, reason):
    if not condition:
        raise IntegrationError(reason)


def _upper_float(value):
    result = float(value)
    return math.nextafter(result, math.inf) if F(result) < value else result


@dataclass(frozen=True)
class SourceOrdinaryStepSizes:
    """Explicit time-step selection for a new segment, never a resumed prefix.

    Event localization can require much shorter steps than subsequent ordinary
    transport. This selection changes only the initial/maximum step; all error,
    minimum-step and resource policies of the accepted source reference remain.
    """
    initial_step_s: float
    maximum_step_s: float
    rationale: str
    classification: str = 'numerical_policy'

    def __post_init__(self):
        self.check()

    def check(self):
        _require(type(self) is SourceOrdinaryStepSizes and
                 all(type(x) is float and math.isfinite(x) and x > 0
                     for x in (self.initial_step_s, self.maximum_step_s)) and
                 self.initial_step_s <= self.maximum_step_s,
                 'source_ordinary_finite_positive_step_sizes')
        _require(type(self.rationale) is str and bool(self.rationale.strip()) and
                 type(self.classification) is str and
                 self.classification == 'numerical_policy',
                 'source_ordinary_explicit_numerical_rationale_required')

    def binding(self):
        self.check()
        return (self.initial_step_s, self.maximum_step_s, self.rationale, self.classification)

    def apply(self, reference: IntegrationPolicy) -> IntegrationPolicy:
        self.check()
        _require(type(reference) is IntegrationPolicy, 'source_ordinary_original_policy_required')
        reference.__post_init__()
        return replace(reference, initial_step_s=self.initial_step_s,
                       maximum_step_s=self.maximum_step_s)


@dataclass(frozen=True)
class SourceTrajectoryResult:
    execution: object
    balances: tuple
    counts: tuple
    cumulative_outer_seconds: float
    parent_study_sha256: str
    selected_candidate_index: int
    journal_events: int
    status: str
    reason: str | None
    material_qualified: bool = False
    full_firing_cycle: bool = False
    archived_resume_authorized: bool = False
    qualification: str = 'ordinary_source_segment_with_original_transition_balance_not_material_validation'


class SourceTrajectorySession:
    """An admitted live session; construct with :func:`open_source_trajectory`.

    The new segment's original integration policy is fixed at construction.
    The old study's actual callback counts and wall debit remain charged to the
    original source-run lifetime limits. Time spent while this session is open,
    including pauses, counts toward those wall limits.
    """

    def _binding(self):
        return _snapshot((self.record.sha256, self.initial, self.start, self.end,
            self.policy, self.adapter.operator_identity, self.adapter.energy_model_identity,
            self.adapter.interfaces, self.parent_counts, self.parent_elapsed_seconds,
            self.built.config.sha256, self.built.assets.sha256, self.selected_candidate_index,
            self.begin, self.recorder.begin, self.reference_policy,
            None if self.step_sizes is None else self.step_sizes.binding()))

    def _check(self):
        _require(self.checkpoint is self._continuation_state[0]
                 and self.last_result is self._continuation_state[1]
                 and self.closed is self._continuation_state[2],
                 'source_trajectory_continuation_state_changed')
        self.built.check()
        _require(self._binding() == self.original_binding, 'source_trajectory_definition_changed')
        _require(runtime_identity() == self.runtime, 'source_trajectory_runtime_changed')
        _require(all(a is b for a, b in zip(self.adapter.column.storages, self.built.storages)),
                 'source_trajectory_original_live_storage_changed')
        _require(self.recorder.limits is self.built.config.values['resources'],
                 'source_trajectory_original_limits_changed')
        parent = dict(self.parent_counts)
        _require(self.recorder.counts['rhs_started'] == parent['rhs_started'] + len(self.recorder.captures)
                 and self.recorder.counts['rhs_returned'] == parent['rhs_returned'] + sum(
                     'evaluation' in capture or 'invalid_return_evidence' in capture
                     for capture in self.recorder.captures)
                 and all(self.recorder.counts[key] == value for key, value in self.constructor_counts),
                 'source_trajectory_actual_costs_changed')

    def _audit(self, reference):
        transition = self.record.roots['transition']
        candidate = transition.candidates[self.selected_candidate_index]
        first = transition.refinement.approach.trial
        terminal = candidate.terminal
        _require(_same(reference.states[0], self.initial) and reference.times_s[0] == self.start,
                 'source_trajectory_original_segment_connection_changed')
        masses = tuple(g.molar_masses_kg_mol
            for g in reify(candidate.captures[0].evaluation).source_evaluation.gas_states)
        return _audit_balance_fields(reify(first.initial), first.start, self.reference_policy, masses,
            wet_references=(reify(first.reference),), terminal_prefix=reify(terminal.prefix),
            corrected_state=reify(terminal.corrected_state),
            selected_cell_index=terminal.selected_cell_index,
            signed_storage_roundoff_mol=terminal.totals.signed_storage_roundoff_mol,
            dry_reference=reify(candidate.reference), post_dry_references=(reference,))

    def advance(self, *, pause_after_steps=None):
        """Advance, or continue this session's last clean committed checkpoint.

        ``pause_after_steps`` counts new accepted steps in this call. Immediate
        cancellation is supplied to the factory and remains a different stop.
        An execution/publication failure or completed session cannot be restarted
        through this method. Invalid preflight arguments are rejected unchanged.
        """
        from .exact_integration import integrate_exact_checkpointed
        _require(pause_after_steps is None or
                 (type(pause_after_steps) is int and pause_after_steps > 0),
                 'source_trajectory_positive_pause_steps_required')
        _require(not self.closed, 'source_trajectory_session_not_resumable')
        self._check()
        _require(tuple(sorted(self.recorder.counts.items())) == self.last_counts,
                 'source_trajectory_prior_costs_changed')
        checkpoint = self.checkpoint
        previous_steps = 0 if checkpoint is None else len(checkpoint.result.steps)
        prior_segment_wall = F() if checkpoint is None else F(checkpoint.result.elapsed_seconds)
        extra = F(time.monotonic() - self.begin) - prior_segment_wall
        _require(extra >= 0, 'source_trajectory_wall_accounting_changed')

        def committed(frame):
            self._check()
            self.balances = self._audit(frame.result)

        def pause(frame):
            return pause_after_steps is not None and len(frame.result.steps) - previous_steps >= pause_after_steps

        try:
            with observer_scope(self.recorder):
                self.recorder.phase = 'ordinary_source_segment'
                execution = integrate_exact_checkpointed(self.initial, self.adapter,
                    start_s=self.start, end_s=self.end, policy=self.policy,
                    breakpoints_s=self.adapter.breakpoints(self.start, self.end),
                    cancel=self.recorder.cancelled, continuation=checkpoint,
                    admission_elapsed_seconds=_upper_float(extra),
                    on_commit=committed, pause_after_commit=pause)
        except BaseException as exc:
            self.last_failure = exc
            self.checkpoint, self.closed = None, True
            self._continuation_state = (self.checkpoint, self.last_result, self.closed)
            try:
                self.recorder.journal.append('ordinary_segment_failed', dict(
                    exception=exc, counts=self.recorder.counts))
            except BaseException as notification_error:
                exc.add_note('source trajectory failure journal also failed: '
                             + type(notification_error).__name__)
            raise
        # A post-commit audit failure leaves the returned numerical prefix as
        # evidence; it does not become a resumable accepted source trajectory.
        self.checkpoint = execution.checkpoint
        self.closed = self.checkpoint is None
        status, reason = execution.result.status, execution.result.reason
        if self.checkpoint is not None:
            status = 'paused'
        if self.recorder.stop_status is not None:
            status, reason = self.recorder.stop_status, self.recorder.stop_reason
            self.checkpoint, self.closed = None, True
        elapsed = _upper_float(F(self.parent_elapsed_seconds) + F(time.monotonic() - self.begin))
        result = SourceTrajectoryResult(execution, self.balances,
            tuple(sorted(self.recorder.counts.items())), elapsed, self.record.sha256,
            self.selected_candidate_index, self.recorder.journal.count, status, reason)
        self.last_result = result
        self.last_counts = tuple(sorted(self.recorder.counts.items()))
        self._continuation_state = (self.checkpoint, self.last_result, self.closed)
        try:
            self.recorder.journal.append('ordinary_segment_returned', result)
        except BaseException as exc:
            self.publication_failure = exc
            self.checkpoint, self.closed = None, True
            self._continuation_state = (self.checkpoint, self.last_result, self.closed)
            raise
        return result


def open_source_trajectory(directory, output, *, end: T, cancel=None,
                           step_sizes: SourceOrdinaryStepSizes | None = None):
    """Read a same-version frozen source run and reconstruct its live dry view.

    Only candidate 1 of a numerically accepted transition is currently admitted.
    The historical source study stays passive. New provider constructors execute
    under the observer, and their real cost is charged before any new RHS call.
    Raw events are durable; this API does not yet serialize a resume controller.
    Optional ``step_sizes`` declares only the new segment's initial/maximum
    steps. Original tolerances and resource limits remain; later pauses cannot
    replace the selected policy.
    """
    begin = time.monotonic()
    _require(type(end) is T and type(end.seconds) is F,
             'source_trajectory_exact_end_required')
    _require(cancel is None or callable(cancel), 'source_trajectory_cancel_callback_required')
    _require(step_sizes is None or type(step_sizes) is SourceOrdinaryStepSizes,
             'source_trajectory_explicit_step_sizes_required')
    if step_sizes is not None:
        step_sizes.check()
        step_sizes = replace(step_sizes)
    directory = Path(directory)
    summary, _, record = read_run_with_source_record(directory)
    if summary.get('integration_kind') != KIND or summary.get('status') != 'completed':
        raise RunError('source_trajectory_completed_source_study_required')
    runtime = runtime_identity()
    if runtime != summary['runtime_before'] or runtime != summary['runtime_after']:
        raise RunError('source_trajectory_runtime_changed')
    _require(record is not None, 'source_trajectory_source_record_required')
    transition = record.roots['transition']
    _require(transition.numerical_event_accepted is True and transition.material_qualified is False,
             'source_trajectory_accepted_numerical_transition_required')
    candidate = transition.candidates[1]
    reference_policy = reify(candidate.seed.policy)
    policy = reference_policy if step_sizes is None else step_sizes.apply(reference_policy)
    initial, start = reify(candidate.reference.states[-1]), candidate.reference.times_s[-1]
    _require(start < end, 'source_trajectory_end_must_follow_original_study')
    config = load_source_run_config(_read(directory / 'case.json', 1024 * 1024))
    _require(config.sha256 == record.metadata['config_sha256'] == summary['config_sha256'],
             'source_trajectory_original_config_changed')
    assets = validate_source_run_assets(config, assets_root=directory / 'assets')
    _require(assets.sha256 == summary['asset_manifest_sha256'], 'source_trajectory_original_assets_changed')
    prior_wall = summary['elapsed_wall_seconds']
    _require(type(prior_wall) is float and math.isfinite(prior_wall) and prior_wall >= 0,
             'source_trajectory_parent_elapsed_required')
    original_counts = dict(summary['counts'])
    _require(all(type(n) is int and n >= 0 for n in original_counts.values()),
             'source_trajectory_parent_counts_required')
    limits = config.values['resources']

    def cancellation():
        if cancel is not None:
            requested = cancel()
            _require(type(requested) is bool, 'source_trajectory_cancel_must_return_bool')
            if requested:
                return True
        if F(prior_wall) + F(time.monotonic() - begin) >= F(limits['outer_seconds']):
            recorder.stop_status, recorder.stop_reason = 'resource_limit', 'source_trajectory_original_outer_limit'
            return False  # Preserve resource-limit classification in _Recorder.
        return False

    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    recorder = _Recorder(output, cancellation, begin)
    recorder.limits, recorder.counts = limits, original_counts.copy()
    try:
        with observer_scope(recorder):
            recorder.phase = 'source_trajectory_reconstruction'
            recorder.guard()
            built = build_source_run(config, assets)
            recorder.built = built
            recorder.guard()
            wet_identity = transition.refinement.approach.proposal.original_trial.adapter.identity
            _require(built.adapter.operator_identity == wet_identity,
                     'source_trajectory_original_wet_operator_changed')
            _require(built.adapter.energy_model_identity == initial.energy_model_identity,
                     'source_trajectory_original_energy_changed')
            saved_view = candidate.terminal.dry_adapter
            modes = saved_view.modes
            _require(type(modes) is tuple and len(modes) == built.column.cell_count,
                     'source_trajectory_explicit_saved_modes_required')
            depleted = tuple(i for i, mode in enumerate(modes) if mode == 'depleted_no_nucleation')
            built.adapter.unpack(initial)
            adapter = built.adapter.with_depleted_cells(initial, depleted)
            _require(adapter.operator_identity == saved_view.identity and adapter.interfaces == modes,
                     'source_trajectory_original_dry_operator_changed')
            _require(adapter.energy_model_identity == initial.energy_model_identity,
                     'source_trajectory_mode_change_redefined_energy')
            recorder.context(adapter)
            recorder.journal.append('source_trajectory_reconstructed', dict(
                parent_study_sha256=record.sha256, runtime=runtime, original_counts=original_counts,
                original_elapsed_wall_seconds=prior_wall, selected_candidate_index=1,
                start=start, end=end, adapter_provenance=adapter.provenance(),
                original_reference_policy=reference_policy, ordinary_policy=policy,
                step_sizes=step_sizes,
                scope='new_ordinary_segment_not_historical_controller_resume'))
            recorder.guard()
    except BaseException as exc:
        try:
            recorder.journal.append('source_trajectory_admission_failed', dict(
                exception=exc, counts=recorder.counts,
                cumulative_outer_seconds=_upper_float(F(prior_wall) + F(time.monotonic() - begin))))
        except BaseException as notification_error:
            exc.add_note('source trajectory admission failure journal also failed: '
                         + type(notification_error).__name__)
        raise
    session = SourceTrajectorySession()
    session.record, session.built, session.adapter = record, built, adapter
    session.initial, session.start, session.end = initial, start, end
    session.policy, session.reference_policy, session.step_sizes = policy, reference_policy, step_sizes
    session.parent_elapsed_seconds, session.parent_counts = prior_wall, tuple(sorted(original_counts.items()))
    session.runtime, session.begin, session.recorder = runtime, begin, recorder
    session.constructor_counts = tuple(sorted((key, value) for key, value in recorder.counts.items()
                                              if not key.startswith('rhs_')))
    session.last_counts = tuple(sorted(recorder.counts.items()))
    session.selected_candidate_index = 1
    session.checkpoint, session.last_result, session.closed, session.balances = None, None, False, ()
    session._continuation_state = (session.checkpoint, session.last_result, session.closed)
    session.original_binding = session._binding()
    session._check()
    return session
