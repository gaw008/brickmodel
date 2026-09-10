"""One root-guided positive source trial using the existing integration path.

Saved inventory polynomials propose a duration, not a physical depletion time.
The proposed interval is re-evaluated in full; no correction, dry transition or
new adaptive controller is introduced here.
"""
from dataclasses import dataclass, fields, replace
from fractions import Fraction as F

from .depletion_integration import DepletionPolicy
from .exact_event_clock import ExactEventTime as T
from .exact_integration import _duration_control
from .integration import IntegrationError
from .source_endpoint_comparison import (
    SourceEndpointComparison, _copy_policy, _policy_binding, compare_source_trial_endpoints,
)
from .source_inverse_pressure import SourceTrialPressure, propagate_source_trial_pressure
from .source_net_panel import SavedSourceSample, build_source_panel
from .source_net_prefix import _same
from .source_net_roots import (
    InventoryRootOrder, QuadraticRoot, SourcePanelRootOrder,
    order_source_panel_roots, refine_first_root,
)
from .source_prefix_trial import SourcePrefixTrial, evaluate_source_prefix_trial


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise IntegrationError(reason)


@dataclass(frozen=True)
class PositiveApproachChoice:
    order: InventoryRootOrder
    safe_fraction: F
    minimum_step_s: F
    maximum_step_s: F
    horizon_s: F
    selected_root: QuadraticRoot | None
    additional_refinement_rounds: int
    desired_duration_s: F | None
    duration_s: F | None
    minima: tuple
    status: str
    qualification: str = 'positive_numerical_polynomial_interval_not_physical_event'

    def check(self) -> None:
        expected = choose_positive_approach(self.order, safe_fraction=self.safe_fraction,
            minimum_step_s=self.minimum_step_s, maximum_step_s=self.maximum_step_s,
            horizon_s=self.horizon_s)
        _require(_same(self, expected), 'source_approach_choice_changed')


def choose_positive_approach(order: InventoryRootOrder, *, safe_fraction: F,
        minimum_step_s: F, maximum_step_s: F, horizon_s: F) -> PositiveApproachChoice:
    """Spend the remaining ordering budget to obtain a strict positive lower bound."""
    _require(type(order) is InventoryRootOrder, 'actual_inventory_root_order_required')
    order.check()
    _require(all(type(x) is F for x in (safe_fraction,minimum_step_s,maximum_step_s,horizon_s))
             and 0 < safe_fraction < F(1,2) and 0 < minimum_step_s <= maximum_step_s
             and 0 < horizon_s <= order.duration, 'exact_positive_approach_controls_required')
    selected = None
    additional = 0
    desired = duration = None
    minima = ()

    def result(status):
        return PositiveApproachChoice(order,safe_fraction,minimum_step_s,maximum_step_s,horizon_s,
                                      selected,additional,desired,duration,minima,status)

    if not order.complete:
        return result(order.status)
    if order.status == 'no_roots':
        return result('no_roots_use_ordinary_integrator')
    if order.status != 'ordered' or len(order.earliest_labels) != 1:
        return result('competing_first_roots')
    label = order.earliest_labels[0]
    selected = next(r for r in order.roots
                    if (r.polynomial.family,r.polynomial.cell,r.polynomial.index) == label)
    if label[0] != 'liquid':
        return result('gas_first')
    if selected.root_kind == 'exact_tangent':
        return result('tangent_not_depletion')
    remaining = order.maximum_refinements-order.refinement_level
    while selected.lower <= 0 and additional < remaining:
        selected = refine_first_root(selected)
        additional += 1
    if selected.lower <= 0:
        return result('positive_root_lower_bound_unresolved')
    desired = min(safe_fraction*selected.lower,maximum_step_s,horizon_s)
    duration = _duration_control(desired)
    if duration < minimum_step_s:
        return result('approach_below_original_minimum_step')
    _require(0 < duration <= desired and duration < selected.lower, 'strict_root_approach_required')
    minima = tuple((p.family,p.cell,p.index,*p.minimum(duration)) for p in order.polynomials)
    _require(all(row[3] > 0 for row in minima), 'approach_inventory_not_strictly_positive')
    return result('positive_numerical_proposal')


@dataclass(frozen=True)
class SourceApproachProposal:
    original_trial: SourcePrefixTrial
    event_policy: DepletionPolicy | None
    policy_binding: str
    effective_root_refinement_limit: int | None
    roots: SourcePanelRootOrder | None
    choice: PositiveApproachChoice | None
    end: T | None
    status: str
    qualification: str = 'source_approach_proposal_requires_fresh_trial_not_event_admission'

    def check(self) -> None:
        _require(_policy_binding(self.event_policy) == self.policy_binding, 'source_approach_policy_changed')
        expected = propose_source_approach(self.original_trial,event_policy=self.event_policy)
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name))
                     for f in fields(self) if f.name != 'original_trial'), 'source_approach_proposal_changed')


def propose_source_approach(trial: SourcePrefixTrial, *,
        event_policy: DepletionPolicy | None) -> SourceApproachProposal:
    """Use actual retained first/midpoint observations, including failed full prefixes."""
    _require(type(trial) is SourcePrefixTrial, 'actual_source_trial_required')
    trial.check()
    policy = _copy_policy(event_policy)
    effective = min(policy.maximum_refinements,256) if policy is not None else None
    roots = choice = end = None

    def result(status):
        return SourceApproachProposal(trial,policy,_policy_binding(policy),effective,roots,choice,end,status)

    if policy is None:
        return result('missing_explicit_event_policy')
    if trial.status in ('cancelled','resource_limit'):
        return result('stopped_seed_requires_explicit_restart')
    if trial.adapter.breakpoints(trial.start,trial.end):
        return result('seed_interval_crosses_program_knot')
    if len(trial.captures) < 2:
        return result('missing_actual_initial_midpoint')
    first,middle = trial.captures[:2]
    if (first.role != 'initial' or middle.role != 'euler_midpoint'
            or any(c.evaluation is None or c.binding is None or c.failure is not None for c in (first,middle))):
        return result('missing_actual_initial_midpoint')
    panel = build_source_panel(SavedSourceSample(first.state,first.evaluation,first.role),
        SavedSourceSample(middle.state,middle.evaluation,middle.role),trial.end,
        operator_identity=trial.operator_identity,energy_identity=trial.energy_identity,
        fixed_dry_mass_kg=trial.fixed_dry_mass_kg)
    roots = order_source_panel_roots(panel,maximum_refinements=effective)
    choice = choose_positive_approach(roots.order,safe_fraction=F(policy.safe_inventory_fraction),
        minimum_step_s=F(trial.policy.minimum_step_s),maximum_step_s=F(trial.policy.maximum_step_s),
        horizon_s=trial.end.elapsed_since(trial.start))
    if choice.status != 'positive_numerical_proposal':
        return result(choice.status)
    end = trial.start.shifted(choice.duration_s)
    _require(not trial.adapter.breakpoints(trial.start,end), 'approach_crosses_program_knot')
    return result('positive_numerical_proposal')


@dataclass(frozen=True)
class SourceApproachResult:
    proposal: SourceApproachProposal
    maximum_callbacks: int
    trial: SourcePrefixTrial | None
    comparison: SourceEndpointComparison | None
    pressure: SourceTrialPressure | None
    status: str
    reason: str | None
    new_evaluations: int
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self) -> None:
        _require(type(self.proposal) is SourceApproachProposal, 'actual_source_approach_proposal_required')
        self.proposal.check()
        _require(type(self.maximum_callbacks) is int and self.maximum_callbacks > 0,
                 'explicit_approach_callback_budget')
        if self.trial is None:
            _require(self.proposal.status != 'positive_numerical_proposal'
                     and self.status == 'not_evaluated' and self.reason == self.proposal.status
                     and self.comparison is None and self.pressure is None
                     and type(self.new_evaluations) is int and self.new_evaluations == 0,
                     'source_approach_unexecuted_record_changed')
        else:
            _require(type(self.trial) is SourcePrefixTrial and self.proposal.status == 'positive_numerical_proposal',
                     'actual_source_approach_trial_required')
            self.trial.check()
            original = self.proposal.original_trial
            _require(_same((self.trial.initial,self.trial.start,self.trial.end,self.trial.policy),
                          (original.initial,original.start,self.proposal.end,original.policy))
                     and self.trial.operator_identity == original.operator_identity
                     and self.trial.energy_identity == original.energy_identity
                     and self.trial.maximum_callbacks == self.maximum_callbacks
                     and type(self.new_evaluations) is int and self.new_evaluations == len(self.trial.captures),
                     'source_approach_actual_interval_or_controls_changed')
            if self.trial.status == 'validated_positive_numerical_trial':
                _require(self.status == 'validated_positive_numerical_approach' and self.reason is None
                         and type(self.comparison) is SourceEndpointComparison and type(self.pressure) is SourceTrialPressure,
                         'source_approach_success_record_changed')
                self.comparison.check()
                self.pressure.check()
                _require(_same(self.comparison.trial,self.trial) and _same(self.pressure.comparison,self.comparison)
                         and self.comparison.policy_binding == self.proposal.policy_binding,
                         'source_approach_endpoint_evidence_changed')
            else:
                _require(self.status == self.trial.status and self.reason == self.trial.reason
                         and self.comparison is None and self.pressure is None,
                         'source_approach_failure_record_changed')
        _require(self.event_admitted is False and self.material_qualified is False, 'source_approach_qualification_changed')


class SourceApproachAssessmentError(IntegrationError):
    """Failed postprocessing with the actual trial and completed evidence retained.

    These fields are diagnostic evidence, not a validated approach result. The
    original exception is chained; no source callbacks are repeated here.
    """

    def __init__(self, stage, proposal, trial, comparison, pressure, cause):
        self.stage = stage
        self.proposal = proposal
        self.trial = trial
        self.comparison = comparison
        self.pressure = pressure
        self.exception_type = type(cause).__name__
        self.exception_message = str(cause)
        super().__init__(f'source_approach_assessment_failed:{stage}:{self.exception_type}:{cause}')


def evaluate_source_approach(proposal: SourceApproachProposal, *, maximum_callbacks: int,
        cancel=None) -> SourceApproachResult:
    """Execute one fresh trial; preserve failures and keep endpoint gates separate.

    Postprocessing failures raise SourceApproachAssessmentError with the actual
    completed trial attached, including all expensive callback evidence.
    """
    _require(type(proposal) is SourceApproachProposal and type(maximum_callbacks) is int
             and maximum_callbacks > 0 and (cancel is None or callable(cancel)), 'explicit_source_approach_inputs')
    proposal.check()
    # Isolate the complete nested event policy from caller mutation while the
    # fresh source callbacks run. Other saved bindings are rechecked below.
    proposal = replace(proposal,event_policy=_copy_policy(proposal.event_policy))
    if proposal.status != 'positive_numerical_proposal':
        return SourceApproachResult(proposal,maximum_callbacks,None,None,None,'not_evaluated',proposal.status,0)
    original = proposal.original_trial
    trial = evaluate_source_prefix_trial(original.adapter,original.initial,start=original.start,end=proposal.end,
        integration_policy=original.policy,maximum_callbacks=maximum_callbacks,cancel=cancel)
    comparison = pressure = None
    status,reason = trial.status,trial.reason
    stage = 'endpoint_comparison'
    try:
        if status == 'validated_positive_numerical_trial':
            comparison = compare_source_trial_endpoints(trial,event_policy=proposal.event_policy)
            stage = 'inverse_pressure'
            pressure = propagate_source_trial_pressure(comparison)
            status = 'validated_positive_numerical_approach'
        stage = 'result_check'
        result = SourceApproachResult(proposal,maximum_callbacks,trial,comparison,pressure,status,reason,len(trial.captures))
        result.check()
        return result
    except Exception as exc:
        raise SourceApproachAssessmentError(stage,proposal,trial,comparison,pressure,exc) from exc
