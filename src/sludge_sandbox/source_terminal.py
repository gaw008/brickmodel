"""Actual N1 source samples, affine evaporation writeback and explicit dry mode.

This constructs a candidate from saved real evaluations. Event-state comparison
and subsequent actual dry integration belong to source_dry_transition.
"""
from dataclasses import dataclass, fields
from fractions import Fraction as F

from .depletion_integration import DepletionPolicy
from .depletion_roundoff import DepletionRoundoffError, DepletionRoundoffTotals
from .exact_affine_depletion import ExactAffineSamples, ExactAffineEvidence, exact_depletion_writeback
from .rational_polynomial import refine_descending_bracket
from .source_endpoint_comparison import _copy_policy, _policy_binding
from .source_net_panel import SavedSourceSample, SourceAffinePanel, build_source_panel
from .source_net_roots import SourcePanelRootOrder, order_source_panel_roots
from .source_net_prefix import SourcePrefix, build_source_prefix, _same
from .source_prefix_trial import SourcePrefixTrial
from .source_root_comparison import SourceRootClockComparison
from .exact_source_column import ExactSourceColumn
from .integration import ConservedState, IntegrationError


def _require(ok, reason):
    if not ok:
        raise IntegrationError(reason)


def _clock_from_order(samples, order, event, selected, spent):
    """Continue the existing dyadic depth; a point root needs a canonical bin."""
    h=samples.upper.elapsed_since(samples.start)
    limit=order.maximum_refinements
    _require(order.refinement_level<=spent<=limit, 'source_terminal_shared_root_budget_exhausted')
    coefficients=(F(samples.start_inventory_mol),
                  sum(map(F,samples.liquid_rates_start_mol_s),F()),sum(samples.accelerations,F())/2)
    _require(coefficients==(selected.polynomial.initial,selected.polynomial.linear,
                             selected.polynomial.quadratic), 'source_evaporation_clock_polynomial_changed')
    if selected.lower==selected.upper:
        depth=max(1,spent)
        width=h/2**depth
        lower=min(selected.lower//width,2**depth-1)*width
        upper=lower+width
    else:
        _require(selected.branch_lower==0 and selected.branch_upper==h
                 and selected.refinements==spent, 'source_clock_requires_same_descending_domain')
        depth=spent
        lower,upper=selected.lower,selected.upper
        if depth==0:
            lower,upper=refine_descending_bracket(coefficients,lower,upper)
            depth=1
    while depth<=limit:
        try:
            return ExactAffineEvidence(samples,samples.start.shifted(lower),samples.start.shifted(upper),
                depth,event.time_absolute_s,event.roundoff_policy),depth-spent
        except DepletionRoundoffError as exc:
            if str(exc) not in ('invalid_adjacent_lower_root_enclosure','exact_clock_original_correction_budget'):
                raise
        if depth==limit:
            break
        lower,upper=refine_descending_bracket(coefficients,lower,upper)
        depth+=1
    raise IntegrationError('source_terminal_shared_root_budget_exhausted')


@dataclass(frozen=True)
class SourceTerminal:
    seed: SourcePrefixTrial
    event_policy: DepletionPolicy
    policy_binding: str
    panel: SourceAffinePanel
    root_order: SourcePanelRootOrder
    prior_clock: SourceRootClockComparison | None
    root_index: int | None
    reused_clock_rounds: int
    clock: ExactAffineEvidence
    additional_clock_rounds: int
    prefix: SourcePrefix
    corrected_state: ConservedState
    correction: object
    totals: DepletionRoundoffTotals
    dry_adapter: ExactSourceColumn
    qualification: str = 'source_evaporation_candidate_requires_actual_dry_and_event_comparison'
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self):
        _require(self.policy_binding==_policy_binding(self.event_policy), 'source_terminal_policy_changed')
        expected=build_source_terminal(self.seed,event_policy=self.event_policy,
                                      prior_clock=self.prior_clock,root_index=self.root_index)
        _require(type(self.dry_adapter) is ExactSourceColumn
                 and self.dry_adapter.operator_identity==expected.dry_adapter.operator_identity
                 and self.dry_adapter.energy_model_identity==self.seed.energy_identity,
                 'source_terminal_dry_adapter_changed')
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name)) for f in fields(self)
                     if f.name not in ('seed','dry_adapter')), 'source_terminal_content_changed')


def build_source_terminal(seed: SourcePrefixTrial, *, event_policy: DepletionPolicy,
                          prior_clock=None, root_index=None) -> SourceTerminal:
    """Bind the full source ledger to existing bounded evaporation-only writeback."""
    _require(type(seed) is SourcePrefixTrial and type(event_policy) is DepletionPolicy,
             'actual_source_terminal_inputs_required')
    seed.check()
    event=_copy_policy(event_policy)
    _require(event.terminal_method=='affine_midpoint' and event.ordered_event_policy is None
             and event.nested_approach is None and event.pressure_comparison is None,
             'explicit_source_single_affine_terminal_policy_required')
    _require(seed.adapter.column.cell_count==1 and seed.adapter.interfaces==('existing_liquid',)
             and seed.initial.amounts_mol.shape==(1,4), 'source_single_wet_cell_required')
    base=getattr(seed.adapter.column,'base',seed.adapter.column)
    _require(base.liquid_transport is None, 'source_terminal_dry_liquid_transport_not_supported')
    _require(seed.status not in ('cancelled','resource_limit'), 'stopped_source_seed_requires_explicit_restart')
    _require(not seed.adapter.breakpoints(seed.start,seed.end), 'source_terminal_seed_crosses_program_knot')
    _require(len(seed.captures)>=2, 'source_terminal_actual_samples_missing')
    first,middle=seed.captures[:2]
    _require((first.role,middle.role)==('initial','euler_midpoint') and all(
        c.evaluation is not None and c.binding is not None and c.failure is None for c in (first,middle)),
        'source_terminal_actual_samples_missing')
    panel=build_source_panel(SavedSourceSample(first.state,first.evaluation,first.role),
        SavedSourceSample(middle.state,middle.evaluation,middle.role),seed.end,
        operator_identity=seed.operator_identity,energy_identity=seed.energy_identity,
        fixed_dry_mass_kg=seed.fixed_dry_mass_kg)
    _require(all(p.initial>0 for p in panel.inventories), 'source_terminal_positive_initial_inventory_required')
    rates=[c.evaluation.rates for c in (first,middle)]
    evaporation=[c.evaluation.source_evaluation.cells[0].phase.phase_water_mol_s for c in (first,middle)]
    _require(all(float(r.face_species_mol_s[i,0])==0 for r in rates for i in (0,1)),
             'source_terminal_transport_depletion_not_supported')
    hm=middle.time.elapsed_since(first.time); h=seed.end.elapsed_since(seed.start)
    e0,em=map(F,evaporation)
    _require(min(e0,e0+(em-e0)*h/hm)>0, 'source_terminal_requires_positive_evaporation_on_full_interval')
    _require(event.roundoff_policy.molar_mass_kg_mol==base.chemical.reference.molar_mass_kg_mol,
             'source_terminal_roundoff_water_molar_mass_mismatch')
    samples=ExactAffineSamples(first.time,middle.time,seed.end,float(seed.initial.amounts_mol[0,0]),
        *[tuple((float(r.face_species_mol_s[0,0]),-float(r.face_species_mol_s[1,0]),
                 float(r.reaction_species_mol_s[0,0]))) for r in rates],
        *evaporation,('source-operator:'+repr(seed.operator_identity),))
    roots=order_source_panel_roots(panel,maximum_refinements=min(event.maximum_refinements,256))
    _require(roots.order.complete and roots.order.status=='ordered'
             and roots.order.earliest_labels==( ('liquid',0,0), ), 'source_terminal_unique_liquid_first_root_required')
    selected=next(r for r in roots.order.roots if
        (r.polynomial.family,r.polynomial.cell,r.polynomial.index)==('liquid',0,0))
    spent=roots.order.refinement_level
    if prior_clock is None:
        _require(root_index is None, 'source_terminal_root_index_without_prior_clock')
    else:
        _require(type(prior_clock) is SourceRootClockComparison
                 and type(root_index) is int and root_index in (0,1),
                 'source_terminal_actual_prior_clock_required')
        prior_clock.check()
        choice=prior_clock.choices[root_index]
        _require(prior_clock.starts[root_index]==seed.start
                 and prior_clock.time_absolute_s==F(event.time_absolute_s)
                 and _same(choice.order,roots.order)
                 and _same((choice.safe_fraction,choice.minimum_step_s,choice.maximum_step_s,choice.horizon_s),
                           (F(event.safe_inventory_fraction),F(seed.policy.minimum_step_s),
                            F(seed.policy.maximum_step_s),h)),
                 'source_terminal_prior_clock_panel_or_policy_changed')
        selected=prior_clock.refined_roots[root_index]
        spent=max(spent,selected.refinements)
    clock,extra=_clock_from_order(samples,roots.order,event,selected,spent)
    _require(middle.time<clock.lower and clock.upper.elapsed_since(seed.start)<=F(event.terminal_window_s),
             'source_terminal_outside_original_window_or_after_midpoint_required')
    prefix=build_source_prefix(panel,clock.lower,policy=seed.policy)
    ledger=prefix.ledger
    terms=(float(ledger.face_species_mol[0,0]),-float(ledger.face_species_mol[1,0]),
           float(ledger.reaction_species_mol[0,0]))
    _require(terms==clock.signed_terms_mol, 'source_terminal_shared_liquid_projection_changed')
    corrected,correction,totals=exact_depletion_writeback(prefix.raw_state,cell_index=0,liquid_index=0,vapor_index=3,
        panel_liquid_start_mol=float(seed.initial.amounts_mol[0,0]),panel_liquid_terms_mol=terms,
        positive_evaporated_mol=clock.positive_evaporated_mol,policy=event.roundoff_policy,
        totals=DepletionRoundoffTotals(event.roundoff_policy),clock_evidence=clock)
    dry=seed.adapter.with_depleted_cells(corrected,(0,))
    _require(dry.interfaces==('depleted_no_nucleation',) and dry.energy_model_identity==seed.energy_identity
             and dry.operator_identity!=seed.operator_identity
             and _same(corrected.internal_energy_j,prefix.raw_state.internal_energy_j),
             'source_terminal_mode_or_energy_changed')
    return SourceTerminal(seed,event,_policy_binding(event),panel,roots,prior_clock,root_index,spent,clock,extra,prefix,
                          corrected,correction,totals,dry)
