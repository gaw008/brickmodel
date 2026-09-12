"""Declared passive association/arithmetic audit, without provider reconstruction."""
from collections import Counter
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction as F
from types import MappingProxyType

import numpy as np

from .exact_event_clock import ExactEventTime as T
from .integration import ConservedState, IntegrationPolicy
from .source_net_panel import SavedSourceSample
from .source_observation_record import (SourceObservationContext, create_source_sample_record)
from .source_prefix_trial import (_check_source_captures, _attempt_input, _policy_binding,
    _complete_reference, _replay_source_reference, normalized_prefix_discrepancy, _bounds)
from .source_endpoint_comparison import _policy_binding as event_binding
from .source_study_schema import SourceStudyNode, REGISTRY, require, validate_node, reify, has_capture_failure


def _same(first: object, second: object) -> bool:
    """Strict field equality with bounded work on repeated immutable DAG nodes."""
    pending=[(first,second)];seen=set();visits=0
    while pending:
        a,b=pending.pop();visits+=1
        require(visits<=2_000_000,'source_study_comparison_resource_limit')
        if type(a) is not type(b):return False
        key=id(a),id(b)
        if key in seen:continue
        seen.add(key)
        if type(a) is np.ndarray:
            if a.dtype!=b.dtype or a.shape!=b.shape or a.tobytes()!=b.tobytes():return False
        elif is_dataclass(a):pending.extend((getattr(a,f.name),getattr(b,f.name)) for f in fields(a))
        elif isinstance(a,Mapping):
            if a.keys()!=b.keys():return False
            pending.extend((a[k],b[k]) for k in a)
        elif type(a) is tuple:
            if len(a)!=len(b):return False
            pending.extend(zip(a,b))
        elif a!=b:return False
    return True


def _name(node):
    return node.kind.rsplit('.',1)[-1] if type(node) is SourceStudyNode else None


def _walk(value):
    pending=[value];seen=set()
    while pending:
        item=pending.pop()
        if type(item) is SourceStudyNode:
            if id(item) in seen:continue
            seen.add(id(item));yield item;pending.extend(item.values.values())
        elif isinstance(item,Mapping):
            if id(item) in seen:continue
            seen.add(id(item));pending.extend(item.values())
        elif type(item) is tuple:
            if id(item) in seen:continue
            seen.add(id(item));pending.extend(item)


def _context_for(state,evaluation,contexts,modes=None):
    options=[c for c in contexts if c.operator_identity==evaluation.operator_identity
        and c.energy_identity==state.energy_model_identity
        and c.fixed_dry_mass_kg==tuple(s.solid_mass_kg[0] for s in evaluation.source_states)
        and (modes is None or c.interface_modes==modes)]
    require(bool(options),'source_study_missing_observation_context')
    # Unknown modes stay unknown; identical numeric context with two explicitly
    # different vectors is never silently chosen for an unlabelled observation.
    if modes is None and len(options)>1:
        require(all(c.interface_modes==options[0].interface_modes for c in options),
                'source_study_ambiguous_observation_context')
    return options[0]


def _sample_record(state,evaluation,role,contexts,modes=None):
    context=_context_for(state,evaluation,contexts,modes)
    sample=SavedSourceSample(state,evaluation,role)
    return create_source_sample_record(sample,context=context)


def _reference_shape(reference,policy):
    require(type(reference.times_s) is tuple and len(reference.times_s)==len(reference.states)==len(reference.steps)+1,
            'source_study_reference_lengths')
    require(all(type(t) is T and type(t.seconds) is F for t in reference.times_s)
            and all(a<b for a,b in zip(reference.times_s,reference.times_s[1:])),
            'source_study_reference_times')
    require(type(reference.evaluations) is int and reference.evaluations>=0
            and type(reference.rejected_trials) is int and reference.rejected_trials>=0
            and type(reference.attempted_trials) is int and reference.attempted_trials>=0,
            'source_study_reference_counts')
    for i,ledger in enumerate(reference.steps):
        before,after=reference.states[i:i+2]
        require(ledger.start_s==reference.times_s[i] and ledger.end_s==reference.times_s[i+1],
                'source_study_ledger_time_binding')
        n,cols=before.amounts_mol.shape
        require(after.amounts_mol.shape==(n,cols) and before.internal_energy_j.shape==after.internal_energy_j.shape==(n,)
                and ledger.face_species_mol.shape==(n+1,cols) and ledger.reaction_species_mol.shape==(n,cols)
                and ledger.face_energy_j.shape==(n+1,) and ledger.cell_work_j.shape==(n,),
                'source_study_ledger_shape')
        require(before.energy_model_identity==after.energy_model_identity,'source_study_reference_energy_identity')
        for cell in range(n):
            for species in range(cols):
                residual=F(float(after.amounts_mol[cell,species]))-F(float(before.amounts_mol[cell,species]))-(
                    F(float(ledger.face_species_mol[cell,species]))-F(float(ledger.face_species_mol[cell+1,species]))+
                    F(float(ledger.reaction_species_mol[cell,species])))
                require(abs(residual)<=F(policy.amount_absolute_tolerance_mol),'source_study_reference_inventory_budget')
            residual=F(float(after.internal_energy_j[cell]))-F(float(before.internal_energy_j[cell]))-(
                F(float(ledger.face_energy_j[cell]))-F(float(ledger.face_energy_j[cell+1]))+F(float(ledger.cell_work_j[cell])))
            require(abs(residual)<=F(policy.energy_absolute_tolerance_j),'source_study_reference_energy_budget')


def _trial(node,memo,checks,contexts):
    policy=reify(node.policy,memo);policy.__post_init__()
    require(_same(node.policy_binding,_policy_binding(policy)),'source_study_trial_policy_binding')
    require(_same(node.controls_binding,(node.start,node.end,node.maximum_callbacks))
            and type(node.maximum_callbacks) is int and node.maximum_callbacks>0,
            'source_study_trial_controls_binding')
    require(_same(node.outcome_binding,(node.status,node.reason)),'source_study_trial_outcome_binding')
    require(type(node.start) is T and type(node.end) is T and node.start<node.end,
            'source_study_trial_exact_interval')
    captures=reify(node.captures,memo);initial=reify(node.initial,memo)
    require(len(captures)<=node.maximum_callbacks,'source_study_trial_callback_budget')
    _check_source_captures(captures,start=node.start,end=node.end,operator_identity=node.operator_identity,
                          energy_identity=node.energy_identity,masses=node.fixed_dry_mass_kg)
    checks['trial_attempt_bindings']+=len(captures)
    for capture in captures:
        if capture.evaluation is not None and capture.binding is not None:
            _sample_record(capture.state,capture.evaluation,capture.role,contexts)
            checks['nested_source_observations']+=1
    if captures:
        require(_same(captures[0].state,initial) and captures[0].time==node.start
                and captures[0].role=='initial','source_study_trial_initial_capture')
    if node.predictor is not None:
        from .exact_integration import advance_exact_euler
        require(bool(captures) and captures[0].evaluation is not None,'source_study_predictor_observation')
        wanted=advance_exact_euler(initial,captures[0].evaluation.rates,node.end.elapsed_since(node.start)/2,policy)
        require(_same(wanted,reify(node.predictor,memo)),'source_study_predictor_changed')
        checks['euler_predictors']+=1
    if node.prefix is not None:
        prefix=reify(node.prefix,memo)
        require(len(captures)>=2 and prefix.end==node.end
                and _same(prefix.panel.first.state,initial)
                and _same(prefix.panel.interior.state,reify(node.predictor,memo))
                and prefix.panel.sample_bindings[:2]==(captures[0].binding,captures[1].binding),
                'source_study_trial_prefix_binding')
    for capture in captures:
        if capture.role=='euler_midpoint':
            require(node.predictor is not None and _same(capture.state,reify(node.predictor,memo))
                    and capture.time==node.start.shifted(node.end.elapsed_since(node.start)/2),
                    'source_study_midpoint_attempt')
        if capture.role=='prefix_terminal':
            require(node.prefix is not None and _same(capture.state,reify(node.prefix.raw_state,memo))
                    and capture.time==node.end,'source_study_terminal_attempt')
    if node.reference_policy is not None:
        rp=reify(node.reference_policy,memo)
        require(_same(node.reference_policy_binding,_policy_binding(rp))
                and all(_same(getattr(policy,f.name),getattr(rp,f.name)) for f in fields(policy) if f.name!='maximum_wall_seconds')
                and 0<rp.maximum_wall_seconds<=policy.maximum_wall_seconds,'source_study_reference_policy_binding')
    else:require(node.reference_policy_binding is None,'source_study_reference_policy_missing')
    if node.reference is not None:
        reference=reify(node.reference,memo);_reference_shape(reference,policy)
        checks['reference_ledgers']+=len(reference.steps)
    if node.status=='validated_positive_numerical_trial':
        require(node.reason is None and node.prefix is not None and node.reference_policy is not None
                and node.reference is not None and len(captures)>=4
                and tuple(c.role for c in captures[:3])==('initial','euler_midpoint','prefix_terminal'),
                'source_study_success_trial_missing_evidence')
        require(_same(node.terminal_bounds,_bounds(captures[2].evaluation)),'source_study_terminal_bounds')
        _complete_reference(reference,node.start,node.end,initial)
        _replay_source_reference(initial,node.start,node.end,replace(rp,maximum_wall_seconds=policy.maximum_wall_seconds),
                                 captures[3:],reference)
        require(_same(node.discrepancy,normalized_prefix_discrepancy(prefix.raw_state,reference.states[-1],policy))
                and node.discrepancy<=1,'source_study_trial_discrepancy')
        checks['completed_reference_replays']+=1
    else:
        require(node.status in ('numerical_failure','domain_exit','cancelled','resource_limit','unsupported')
                and type(node.reason) is str,'source_study_trial_failure_status')
        checks['preserved_failed_trials']+=1


def _terminal(node,memo,checks):
    from .exact_affine_depletion import exact_depletion_writeback
    from .depletion_roundoff import DepletionRoundoffTotals
    event=reify(node.event_policy,memo);clock=reify(node.clock,memo);prefix=reify(node.prefix,memo)
    require(event_binding(event)==node.policy_binding,'source_study_terminal_policy_binding')
    cell=node.selected_cell_index
    require(type(cell) is int and 0<=cell<prefix.raw_state.amounts_mol.shape[0],
            'source_study_terminal_cell_index')
    from .source_terminal import _clock_from_order
    from .exact_affine_depletion import ExactAffineSamples
    panel=reify(node.panel,memo);roots=reify(node.root_order,memo);seed=node.seed
    require(event.terminal_method=='affine_midpoint' and event.ordered_event_policy is None
            and event.nested_approach is None and event.pressure_comparison is None
            and seed.status not in ('cancelled','resource_limit') and len(seed.captures)>=2,
            'source_study_terminal_original_policy_and_seed')
    require(roots.order.maximum_refinements==min(event.maximum_refinements,256)
            and _same(roots.panel,panel) and _same(prefix.panel,panel)
            and roots.order.complete and roots.order.status=='ordered'
            and roots.order.earliest_labels==(('liquid',cell,0),)
            and panel.sample_bindings[:2]==tuple(c.binding for c in seed.captures[:2])
            and panel.first.evaluation.time==seed.start and panel.upper==seed.end
            and all(p.initial>0 for p in panel.inventories),'source_study_terminal_selected_source_root')
    first,middle=(reify(c,memo) for c in seed.captures[:2])
    require((first.role,middle.role)==('initial','euler_midpoint') and all(
        c.evaluation is not None and c.binding is not None and c.failure is None for c in (first,middle)),
        'source_study_terminal_samples')
    rates=[c.evaluation.rates for c in (first,middle)]
    evaporation=[c.evaluation.source_evaluation.cells[cell].phase.phase_water_mol_s for c in (first,middle)]
    h=seed.end.elapsed_since(seed.start);hm=middle.time.elapsed_since(first.time)
    e0,em=map(F,evaporation)
    require(min(e0,e0+(em-e0)*h/hm)>0,'source_study_terminal_gross_evaporation')
    samples=ExactAffineSamples(first.time,middle.time,seed.end,float(reify(seed.initial,memo).amounts_mol[cell,0]),
        *[tuple((float(r.face_species_mol_s[cell,0]),-float(r.face_species_mol_s[cell+1,0]),
                 float(r.reaction_species_mol_s[cell,0]))) for r in rates],
        *evaporation,('source-operator:'+repr(seed.operator_identity),))
    selected=next(r for r in roots.order.roots if
        (r.polynomial.family,r.polynomial.cell,r.polynomial.index)==('liquid',cell,0))
    spent=roots.order.refinement_level
    if node.prior_clock is None:
        require(node.root_index is None,'source_study_terminal_root_index_without_prior')
    else:
        prior=reify(node.prior_clock,memo)
        require(type(node.root_index) is int and node.root_index in (0,1),'source_study_terminal_root_index')
        choice=prior.choices[node.root_index]
        require(prior.starts[node.root_index]==seed.start and prior.time_absolute_s==F(event.time_absolute_s)
                and _same(choice.order,roots.order)
                and _same((choice.safe_fraction,choice.minimum_step_s,choice.maximum_step_s,choice.horizon_s),
                          (F(event.safe_inventory_fraction),F(seed.policy.minimum_step_s),
                           F(seed.policy.maximum_step_s),h)),'source_study_terminal_prior_root_budget')
        selected=prior.refined_roots[node.root_index];spent=max(spent,selected.refinements)
    expected_clock,extra=_clock_from_order(samples,roots.order,event,selected,spent)
    require(_same((clock,node.reused_clock_rounds,node.additional_clock_rounds),(expected_clock,spent,extra))
            and middle.time<clock.lower and clock.upper.elapsed_since(seed.start)<=F(event.terminal_window_s)
            and all(p.minimum(clock.upper.elapsed_since(seed.start))[0]>0 for p in panel.inventories
                    if (p.family,p.cell,p.index)!=('liquid',cell,0)),
            'source_study_terminal_clock_or_other_inventory')
    ledger=prefix.ledger
    terms=(float(ledger.face_species_mol[cell,0]),-float(ledger.face_species_mol[cell+1,0]),
           float(ledger.reaction_species_mol[cell,0]))
    require(terms==clock.signed_terms_mol and prefix.end==clock.lower,'source_study_terminal_clock_ledger_binding')
    corrected,correction,totals=exact_depletion_writeback(prefix.raw_state,cell_index=cell,liquid_index=0,vapor_index=3,
        panel_liquid_start_mol=float(reify(node.seed.initial,memo).amounts_mol[cell,0]),
        panel_liquid_terms_mol=terms,positive_evaporated_mol=clock.positive_evaporated_mol,
        policy=event.roundoff_policy,totals=DepletionRoundoffTotals(event.roundoff_policy),clock_evidence=clock)
    require(_same(corrected,reify(node.corrected_state,memo)) and _same(correction,reify(node.correction,memo))
            and _same(totals,reify(node.totals,memo)),'source_study_writeback_changed')
    checks['terminal_writebacks']+=1


def _candidate(node,memo,checks,contexts):
    event=reify(node.event_policy,memo)
    require(node.event_policy_binding==event_binding(event)
            and _same(node.controls_binding,(node.end,node.maximum_callbacks))
            and _same(node.outcome_binding,(node.status,node.reason)),'source_study_candidate_binding')
    if node.terminal is not None:
        require(_same(node.terminal.seed,node.seed) and node.terminal.policy_binding==node.event_policy_binding,
                'source_study_candidate_terminal_binding')
    require(node.status in ('executed_dry_candidate','domain_exit','failed','numerical_failure','resource_limit','cancelled'),
            'source_study_candidate_status')
    captures=reify(node.captures,memo)
    require(type(node.maximum_callbacks) is int and 0<node.maximum_callbacks and len(captures)<=node.maximum_callbacks,
            'source_study_candidate_callback_budget')
    for i,capture in enumerate(captures):
        require(capture.ordinal==i+1 and capture.role=='dry_reference'
                and _same(capture.input_binding,_attempt_input(capture.ordinal,capture.role,capture.state,capture.time))
                and _same(capture.failure_binding,(capture.failure_kind,capture.failure)),
                'source_study_dry_attempt_binding')
        if capture.evaluation is not None and capture.binding is not None:
            record=_sample_record(capture.state,capture.evaluation,capture.role,contexts)
            require(record.sample_binding==capture.binding,'source_study_dry_capture_binding')
    checks['dry_attempt_bindings']+=len(captures)
    if node.terminal is None:
        require(not captures and node.reference is None and not node.cell_pressure_endpoints and not node.pressure_endpoints,
                'source_study_dry_without_terminal')
    if node.dry_policy is not None:
        policy=reify(node.dry_policy,memo);original=reify(node.seed.policy,memo)
        require(_same(node.dry_policy_binding,_policy_binding(policy))
                and all(_same(getattr(policy,f.name),getattr(original,f.name)) for f in fields(policy) if f.name!='maximum_wall_seconds')
                and 0<policy.maximum_wall_seconds<=original.maximum_wall_seconds,'source_study_dry_policy_binding')
    if node.reference is not None:
        require(node.dry_policy is not None and node.terminal is not None,'source_study_reference_without_execution_inputs')
        reference=reify(node.reference,memo);_reference_shape(reference,policy)
        checks['reference_ledgers']+=len(reference.steps)
        if node.status=='executed_dry_candidate':
            require(node.terminal is not None and node.reason is None and bool(captures),
                    'source_study_success_candidate_missing_evidence')
            initial=reify(node.terminal.corrected_state,memo)
            _complete_reference(reference,node.terminal.clock.lower,node.end,initial)
            _replay_source_reference(initial,node.terminal.clock.lower,node.end,
                replace(policy,maximum_wall_seconds=original.maximum_wall_seconds),captures,reference)
            checks['completed_reference_replays']+=1
    elif node.status=='executed_dry_candidate':
        require(False,'source_study_success_candidate_missing_reference')
    if node.terminal is not None:
        selected=node.terminal.selected_cell_index;count=len(node.seed.fixed_dry_mass_kg)
        require(len(node.cell_pressure_endpoints)<=2,'source_study_pressure_matrix_shape')
        if node.status=='executed_dry_candidate':
            require(len(node.cell_pressure_endpoints)==2 and all(len(row)==count for row in node.cell_pressure_endpoints),
                    'source_study_complete_candidate_pressure_matrix')
        for capture,row in zip((captures[0],captures[-1]) if captures else (),node.cell_pressure_endpoints):
            require(len(row)<=count and capture.evaluation is not None,'source_study_pressure_matrix_shape')
            for i,bound in enumerate(row):
                require(_same(reify(bound.state,memo),capture.evaluation.source_states[i])
                        and _same(reify(bound.inverse,memo),capture.evaluation.source_evaluation.cells[i].inverse)
                        and bound.storage_identity==node.seed.energy_identity[1][i],
                        'source_study_pressure_endpoint_binding')
        require(len(node.pressure_endpoints)==sum(len(row)>selected for row in node.cell_pressure_endpoints),
                'source_study_selected_pressure_projection')
        require(all(_same(bound,row[selected]) for bound,row in zip(node.pressure_endpoints,node.cell_pressure_endpoints)),
                'source_study_selected_pressure_projection')


def _proposal(node,memo,checks):
    from .source_approach import choose_positive_approach
    event=reify(node.event_policy,memo);trial=node.original_trial
    require(node.policy_binding==event_binding(event),'source_study_proposal_policy_binding')
    require(_same(node.effective_root_refinement_limit,min(event.maximum_refinements,256) if event else None),
            'source_study_proposal_budget')
    if node.roots is not None:
        roots=reify(node.roots,memo)
        require(len(trial.captures)>=2 and roots.sample_bindings[:2]==tuple(c.binding for c in trial.captures[:2])
                and roots.start==trial.start and roots.upper==trial.end
                and roots.operator_identity==trial.operator_identity
                and roots.order.maximum_refinements==node.effective_root_refinement_limit,
                'source_study_proposal_source_binding')
        wanted=choose_positive_approach(roots.order,safe_fraction=F(event.safe_inventory_fraction),
            minimum_step_s=F(trial.policy.minimum_step_s),maximum_step_s=F(trial.policy.maximum_step_s),
            horizon_s=trial.end.elapsed_since(trial.start))
        require(_same(reify(node.choice,memo),wanted),'source_study_proposal_choice')
        require(node.status==wanted.status and _same(node.end,
            trial.start.shifted(wanted.duration_s) if wanted.status=='positive_numerical_proposal' else None),
            'source_study_proposal_end')
    else:
        require(node.choice is None and node.end is None and node.status in (
            'missing_explicit_event_policy','stopped_seed_requires_explicit_restart',
            'seed_interval_crosses_program_knot','missing_actual_initial_midpoint'),
            'source_study_unexecuted_proposal')
    checks['proposal_source_and_choice_bindings']+=1


def _approach(node,memo,checks):
    proposal=node.proposal;trial=node.trial
    require(type(node.maximum_callbacks) is int and node.maximum_callbacks>0,'source_study_approach_budget')
    if trial is None:
        require(proposal.status!='positive_numerical_proposal' and node.status=='not_evaluated'
                and node.reason==proposal.status and node.comparison is None and node.pressure is None
                and node.new_evaluations==0,'source_study_approach_unexecuted')
    else:
        original=proposal.original_trial
        require(proposal.status=='positive_numerical_proposal'
                and _same((trial.initial,trial.start,trial.end,trial.policy),
                          (original.initial,original.start,proposal.end,original.policy))
                and trial.operator_identity==original.operator_identity and trial.energy_identity==original.energy_identity
                and trial.maximum_callbacks==node.maximum_callbacks and node.new_evaluations==len(trial.captures),
                'source_study_approach_trial_connection')
        if trial.status=='validated_positive_numerical_trial':
            require(node.status=='validated_positive_numerical_approach' and node.reason is None
                    and node.comparison is not None and node.pressure is not None
                    and _same(node.comparison.trial,trial) and _same(node.pressure.comparison,node.comparison)
                    and node.comparison.policy_binding==proposal.policy_binding,'source_study_approach_assessments')
        else:
            require(node.status==trial.status and node.reason==trial.reason
                    and node.comparison is None and node.pressure is None,'source_study_approach_failure')
    checks['approach_connections']+=1


def _refinement(node,memo,checks):
    prior=node.approach.trial;original=node.approach.proposal.original_trial;trial=node.shifted_trial
    require(node.approach.status=='validated_positive_numerical_approach'
            and _same((trial.initial,trial.start,trial.end,trial.policy),
                      (prior.reference.states[-1],prior.end,original.end,original.policy))
            and _same((trial.operator_identity,trial.energy_identity,trial.fixed_dry_mass_kg),
                      (original.operator_identity,original.energy_identity,original.fixed_dry_mass_kg))
            and _same(node.shifted_proposal.original_trial,trial)
            and node.shifted_proposal.policy_binding==node.approach.proposal.policy_binding
            and node.new_evaluations==len(trial.captures),'source_study_shifted_reference_connection')
    require(trial.start<original.start.shifted(node.approach.proposal.choice.selected_root.lower),
            'source_study_shifted_start_before_root')
    proposal=node.shifted_proposal
    if node.clock is not None:
        require(proposal.status=='positive_numerical_proposal' and node.status=='partitioned_surrogate_roots_compared'
                and node.reason is None and _same(node.clock.choices,(node.approach.proposal.choice,proposal.choice))
                and _same(node.clock.starts,(original.start,trial.start))
                and node.clock.time_absolute_s==F(proposal.event_policy.time_absolute_s),
                'source_study_root_clock_stage_binding')
    else:
        require(node.status=='root_comparison_not_available' and node.reason==(
            'partitioned_first_inventory_label_changed' if proposal.status=='positive_numerical_proposal' else proposal.status),
            'source_study_missing_clock_reason')
    checks['shifted_reference_connections']+=1


def _comparison(node,memo,checks):
    trial=node.trial;event=reify(node.event_policy,memo)
    require(trial.status=='validated_positive_numerical_trial' and node.policy_binding==event_binding(event),
            'source_study_comparison_trial_policy')
    first,last=trial.captures[2],trial.captures[-1]
    data=reify(node.differences,memo)
    require(_same((data.samples[0].state,data.samples[0].evaluation,data.samples[1].state,data.samples[1].evaluation),
                  tuple(reify(x,memo) for x in (first.state,first.evaluation,last.state,last.evaluation)))
            and _same(node.integration_discrepancy,trial.discrepancy),'source_study_endpoint_sample_binding')
    gates=tuple(x<=F(y) for x,y in zip(data.maxima,(event.amount_absolute_mol,event.energy_absolute_j,
        event.temperature_absolute_k,event.pressure_absolute_pa))) if event else (None,)*4
    status='missing_explicit_event_policy' if event is None else ('reported_endpoint_gates_satisfied'
        if all(gates) else 'endpoint_tolerance_not_certified')
    pgate='unresolved' if event is None or any(row[1] or row[5] for row in data.inverse_inputs) else (
        'within_tolerance' if gates[3] else 'not_certified')
    require(_same((node.gates,node.status,node.full_inverse_pressure_gate),(gates,status,pgate)),
            'source_study_reported_endpoint_gates')
    checks['reported_endpoint_associations']+=1


def _bound_pairs(pairs,captures,memo):
    require(len(pairs)==len(captures[0].evaluation.source_states),'source_study_pressure_pair_cells')
    bounds=[]
    for i,pair in enumerate(pairs):
        require(len(pair)==2,'source_study_pressure_pair_shape')
        for bound,capture in zip(pair,captures):
            require(_same(bound.state,capture.evaluation.source_states[i])
                    and _same(bound.inverse,capture.evaluation.source_evaluation.cells[i].inverse),
                    'source_study_pressure_observation_binding')
        a,b=pair
        bound=(abs(F(reify(a.inverse,memo).point.pressure_pa)-F(reify(b.inverse,memo).point.pressure_pa))
               +a.continuation.radius_pa+b.continuation.radius_pa
               if a.continuation.status==b.continuation.status=='conditional_pressure_enclosure' else None)
        bounds.append(bound)
    return tuple(bounds)


def _trial_pressure(node,memo,checks):
    comparison=node.comparison;trial=comparison.trial
    bounds=_bound_pairs(node.endpoint_bounds,(trial.captures[2],trial.captures[-1]),memo)
    maximum=max(bounds) if all(v is not None for v in bounds) else None
    event=comparison.event_policy
    gate=maximum<=F(event.pressure_absolute_pa) if maximum is not None and event is not None else None
    require(_same((node.conditional_cell_bounds_pa,node.maximum_conditional_bound_pa,node.conditional_gate),
                  (bounds,maximum,gate)),'source_study_trial_pressure_gates')
    checks['trial_pressure_associations']+=1


def _common(node,memo,checks):
    from collections import namedtuple
    from .source_root_comparison import _joined_reference_residuals
    refinement=node.refinement;end=node.common_end
    original=refinement.approach.proposal.original_trial;previous=refinement.approach.trial
    require(refinement.clock is not None and type(end) is T and type(end.seconds) is F
            and refinement.shifted_trial.start<end<min(x.lower for x in refinement.clock.intervals),
            'source_study_common_pre_root_interval')
    for choice,start in zip(refinement.clock.choices,refinement.clock.starts):
        duration=end.elapsed_since(start)
        require(duration>=F(original.policy.minimum_step_s) and all(p.minimum(duration)[0]>0
            for p in reify(choice.order,memo).polynomials),'source_study_common_positive_inventories')
    for trial,initial,start in ((node.coarse_trial,original.initial,original.start),
                               (node.shifted_trial,previous.reference.states[-1],previous.end)):
        require(trial.status=='validated_positive_numerical_trial'
                and _same((trial.initial,trial.start,trial.end,trial.policy),(initial,start,end,original.policy))
                and _same((trial.operator_identity,trial.energy_identity,trial.fixed_dry_mass_kg),
                          (original.operator_identity,original.energy_identity,original.fixed_dry_mass_kg)),
                'source_study_common_reference_connection')
    # This explicit numerical projection has no runtime methods or adapter.
    BalanceFields=namedtuple('ReferenceBalanceFields','initial policy start end status reference')
    def projection(trial):
        return BalanceFields(reify(trial.initial,memo),reify(trial.policy,memo),trial.start,trial.end,
                             trial.status,reify(trial.reference,memo))
    residuals=tuple(_joined_reference_residuals(tuple(projection(t) for t in path)) for path in
                    ((node.coarse_trial,),(previous,node.shifted_trial)))
    require(_same(node.cumulative_residuals,residuals),'source_study_common_cumulative_balances')
    captures=(node.coarse_trial.captures[-1],node.shifted_trial.captures[-1]);data=reify(node.differences,memo)
    require(all(_same((sample.state,sample.evaluation),(reify(c.state,memo),reify(c.evaluation,memo)))
        for sample,c in zip(data.samples,captures)),'source_study_common_endpoint_observations')
    event=refinement.approach.proposal.event_policy
    gates=tuple(v<=F(limit) for v,limit in zip(data.maxima,(event.amount_absolute_mol,event.energy_absolute_j,
                event.temperature_absolute_k,event.pressure_absolute_pa)))
    bounds=_bound_pairs(node.pressure_pairs,captures,memo)
    gate=max(bounds)<=F(event.pressure_absolute_pa) if all(v is not None for v in bounds) else None
    status='positive_endpoint_gates_satisfied' if all(gates) else 'positive_endpoint_tolerance_not_certified'
    require(_same((node.gates,node.conditional_pressure_bounds_pa,node.conditional_pressure_gate,node.status,
                   node.new_evaluations),(gates,bounds,gate,status,
                   len(node.coarse_trial.captures)+len(node.shifted_trial.captures))),
            'source_study_common_endpoint_gates')
    checks['common_reference_balance_rows']+=sum(map(len,residuals))


def _transition_balances(node,memo,checks):
    from .source_dry_transition import _audit_balance_fields
    expected=[]
    seeds=(node.refinement.approach.proposal.original_trial,node.refinement.shifted_trial)
    for index,(candidate,seed) in enumerate(zip(node.candidates,seeds)):
        require(_same(candidate.seed,seed)
                and candidate.event_policy_binding==node.refinement.approach.proposal.policy_binding
                and _same(candidate.terminal.prior_clock,node.refinement.clock)
                and type(candidate.terminal.root_index) is int and candidate.terminal.root_index==index,
                'source_study_transition_original_seed_and_prior_clock')
        ordinary=(node.refinement.approach.trial,) if index else ()
        first=ordinary[0] if ordinary else seed
        previous,start=first.initial,first.start
        for trial in ordinary:
            require(trial.status=='validated_positive_numerical_trial'
                    and _same((trial.initial,trial.start,trial.policy),(previous,start,seed.policy)),
                    'source_study_transition_wet_connection')
            previous,start=trial.reference.states[-1],trial.reference.times_s[-1]
        require(_same((seed.initial,seed.start),(previous,start)),'source_study_transition_terminal_connection')
        masses=tuple(g.molar_masses_kg_mol for g in reify(candidate.captures[0].evaluation,memo).source_evaluation.gas_states)
        terminal=candidate.terminal
        expected.append(_audit_balance_fields(reify(first.initial,memo),first.start,reify(seed.policy,memo),masses,
            wet_references=tuple(reify(t.reference,memo) for t in ordinary),terminal_prefix=reify(terminal.prefix,memo),
            corrected_state=reify(terminal.corrected_state,memo),selected_cell_index=terminal.selected_cell_index,
            signed_storage_roundoff_mol=terminal.totals.signed_storage_roundoff_mol,
            dry_reference=reify(candidate.reference,memo)))
    require(_same(reify(node.balance_paths,memo),tuple(expected)),'source_study_cumulative_all_cell_balances')
    checks['complete_transition_balance_rows']+=sum(map(len,expected))


def _pressure(node,memo,checks):
    from .deforming_solid_storage import _digest
    state,inverse=reify(node.state,memo),reify(node.inverse,memo)
    point=inverse.point;mechanical=point.fluid.mechanical;env=point.fluid.envelope
    require(node.input_binding==_digest((state,inverse))
            and node.storage_identity==state.energy_model_identity==point.model_identity,
            'source_study_pressure_input_binding')
    ng=sum(map(F,state.gas_amounts_mol),F());r=F(mechanical.gas_constant_j_mol_k)
    if _name(node)=='SourceInversePressure':
        expected=(F(state.liquid_water_mol),ng,r,F(env.liquid_abs_du_dp_bound_j_mol_pa),
            F(point.temperature_k),F(inverse.temperature_error_bound_k),F(point.pressure_pa),F(point.pressure_error_pa))
        require(state.liquid_water_mol>0,'source_study_wet_pressure_regime')
    else:
        expected=(ng,r,F(point.temperature_k),F(inverse.temperature_error_bound_k),
            F(point.available_pore_volume_m3),F(point.available_volume_error_m3),F(point.pressure_pa),F(point.pressure_error_pa))
        require(state.liquid_water_mol==0 and mechanical.liquid_pressure_pa is None,'source_study_dry_pressure_regime')
    require(_same(node.continuation.inputs,expected),'source_study_pressure_continuation_inputs')
    checks['pressure_input_associations']+=1


def _shared_volume(node,memo,checks):
    from .deforming_solid_storage import _digest
    volume=reify(node.volume,memo)
    require(_same(node.volume_interval_m3,(F(volume.value_m3)-F(volume.error_m3),
                                          F(volume.value_m3)+F(volume.error_m3)))
            and node.input_binding==_digest((node.storage_identity,volume,node.source_ids))
            and len(node.object_identity)==2 and all(type(v) is int and v>0 for v in node.object_identity),
            'source_study_shared_volume_declaration_fields')
    checks['saved_volume_declaration_fields']+=1


def _pair(node,memo,checks):
    require(len(node.endpoints)==2,'source_study_pressure_pair_shape')
    a,b=node.endpoints
    require(a.storage_identity==b.storage_identity==node.shared_volume.storage_identity,
            'source_study_pressure_pair_storage_identity')
    av,bv=reify(a.inverse,memo).point,reify(b.inverse,memo).point
    shared=node.shared_volume
    require(all(_same((F(point.available_pore_volume_m3),F(point.available_volume_error_m3)),
                      (F(shared.volume.value_m3),F(shared.volume.error_m3))) for point in (av,bv)),
            'source_study_shared_volume_endpoint_binding')
    if a.continuation.radius_pa is not None and b.continuation.radius_pa is not None:
        independent=abs(F(av.pressure_pa)-F(bv.pressure_pa))+a.continuation.radius_pa+b.continuation.radius_pa
        require(_same(node.independent_bound_pa,independent),'source_study_independent_pressure_bound')
    if node.status=='unresolved':
        require(node.bound_pa is None and node.joint_bound_pa is None and type(node.reason) is str,
                'source_study_unresolved_pressure_bound')
        return
    require(len(node.error_parts)==2 and node.reason is None,'source_study_pressure_parts_shape')
    for part,endpoint in zip(node.error_parts,node.endpoints):
        point=reify(endpoint.inverse,memo).point
        require(_same(part.actual_fluid_error_pa,F(point.fluid.pressure_error_bound_pa))
                and _same(part.total_error_pa,F(point.pressure_error_pa))
                and float(part.global_error_pa)==point.global_pressure_error_pa
                and float(part.extra_volume_error_pa)==point.extra_pressure_error_pa
                and part.projection_error_pa==abs(part.total_error_pa-part.actual_fluid_error_pa-part.extra_volume_error_pa),
                'source_study_pair_original_error_parts')
    if _name(node)=='SourceSharedDryPressurePair':
        require(node.status=='conditional_shared_dry_pressure_enclosure','source_study_pressure_pair_status')
        na,nb=(e.continuation.inputs[0] for e in node.endpoints)
        r=a.continuation.inputs[1];ta,tb=(e.continuation.temperature_interval_k for e in node.endpoints)
        numerator=(r*(na*ta[0]-nb*tb[1]),r*(na*ta[1]-nb*tb[0]))
        corners=tuple(n/v for n in numerator for v in node.shared_volume.volume_interval_m3)
        ideal=min(corners),max(corners)
        require(_same(node.ideal_interval_pa,ideal),'source_study_shared_dry_ideal_box')
        for part in node.error_parts:
            require(part.box_rounding_error_pa>=0 and part.retained_error_pa==part.actual_fluid_error_pa+part.projection_error_pa+part.box_rounding_error_pa,
                    'source_study_shared_dry_retained_parts')
        margin=sum((p.retained_error_pa for p in node.error_parts),F())
        joint=ideal[0]-margin,ideal[1]+margin
        require(_same(node.joint_interval_pa,joint),'source_study_shared_dry_joint_box')
        bound=max(map(abs,joint))
    else:
        from .rational_intervals import interval_difference,interval_divide_positive,interval_sum,residual_to_root_bound
        require(node.status=='conditional_shared_wet_pressure_enclosure','source_study_pressure_pair_status')
        from .deforming_solid_storage import _digest
        evidence=node.evidence;support=reify(evidence.support,memo);attempts=reify(evidence.attempts,memo)
        require(evidence.input_binding==node.input_binding and evidence.observation_binding==_digest((support,attempts))
                and support.reason is None and len(attempts)==len(support.requests)<=4,
                'source_study_wet_evidence_binding')
        for ordinal,(attempt,request) in enumerate(zip(attempts,support.requests)):
            state=attempt.state
            require(attempt.ordinal==ordinal and _same((attempt.temperature_k,attempt.pressure_pa,attempt.phase),request)
                    and attempt.failure_type is None and attempt.failure_message is None and state is not None
                    and _same((state.temperature_k,state.pressure_pa,state.phase),request)
                    and min(state.density_kg_m3,state.cp_j_kg_k,state.cv_j_kg_k)>0,
                    'source_study_wet_observation_request_binding')
            ratio=F(state.molar_mass_kg_mol)/F(state.density_kg_m3)
            require(_same((attempt.native_molar_volume_m3_mol,attempt.exact_mass_density_ratio_m3_mol,
                           attempt.ratio_projection_m3_mol),
                          (state.molar_mass_kg_mol/state.density_kg_m3,ratio,
                           F(state.molar_mass_kg_mol/state.density_kg_m3)-ratio)),
                    'source_study_wet_observation_ratio')
        require(all(part.low_root_sign_lower_m3>=0 and part.high_root_sign_upper_m3<=0
                    for part in node.error_parts),'source_study_wet_root_existence_gates')
        jlo,jhi=support.interval_pa
        liquid=interval_difference(tuple(F(a.state.liquid_water_mol)*x for x in node.error_parts[0].volume_interval_m3_mol),
            tuple(F(b.state.liquid_water_mol)*x for x in node.error_parts[1].volume_interval_m3_mol))
        ng_a,ng_b=(sum(map(F,e.state.gas_amounts_mol),F()) for e in node.endpoints)
        r=a.continuation.inputs[2];ta,tb=(F(p.temperature_k) for p in (av,bv))
        numerator=r*(ng_a*ta-ng_b*tb)
        residual=interval_sum((liquid,interval_divide_positive((numerator,numerator),(jlo,jhi))))
        compliance=min(ng_a*r*ta,ng_b*r*tb)/jhi**2
        root=residual_to_root_bound(residual,compliance)
        require(_same((node.residual_interval_m3,node.compliance_lower_m3_pa,node.root_difference_bound_pa),
                      (residual,compliance,root)),'source_study_shared_wet_root_arithmetic')
        for endpoint,part in zip(node.endpoints,node.error_parts):
            require(part.machine_residual_bound_m3==part.liquid_rounding_residual_m3+part.gas_rounding_residual_m3+part.sum_rounding_residual_m3
                    and min(part.liquid_rounding_residual_m3,part.gas_rounding_residual_m3,part.sum_rounding_residual_m3)>=0
                    and part.report_to_root_bound_pa==(abs(part.saved_volume_residual_m3)+part.machine_residual_bound_m3)/part.compliance_lower_m3_pa
                    and part.retained_report_error_pa==part.actual_fluid_error_pa+part.projection_error_pa+part.report_to_root_bound_pa,
                    'source_study_shared_wet_margin_arithmetic')
            et=F(endpoint.inverse.temperature_error_bound_k);old=endpoint.continuation.slope_pa_k
            require(part.original_temperature_error_pa==old*et
                    and part.added_temperature_error_pa==(max(old,part.continuation.slope_pa_k)-old)*et,
                    'source_study_shared_wet_temperature_margin')
        bound=root+sum((p.retained_report_error_pa+p.original_temperature_error_pa+p.added_temperature_error_pa
                        for p in node.error_parts),F())
    require(type(node.bound_pa) is F and _same((node.joint_bound_pa,node.bound_pa),(bound,bound)),
            'source_study_selected_joint_pressure_bound')
    checks['shared_pressure_interval_and_margin_sums']+=1


def _transition(node,memo,checks):
    require(len(node.candidates)==2,'source_study_two_event_candidates')
    a,b=node.candidates;event=reify(a.event_policy,memo)
    require(a.status==b.status=='executed_dry_candidate' and a.end==b.end
            and a.terminal.selected_cell_index==b.terminal.selected_cell_index==node.selected_cell_index,
            'source_study_event_candidate_binding')
    count=len(a.seed.fixed_dry_mass_kg)
    require((len(node.shared_pressure_pairs)==2 if node.shared_volume is not None else not node.shared_pressure_pairs),
            'source_study_shared_dry_strategy_records')
    if node.wet_pressure_pairs:
        require(len(node.wet_pressure_pairs)==2 and all(len(row)==count for row in node.wet_pressure_pairs)
                and all(row[node.selected_cell_index] is None for row in node.wet_pressure_pairs)
                and any(pair is not None for row in node.wet_pressure_pairs for pair in row),
                'source_study_shared_wet_strategy_records')
    strategy=(('explicit_shared_source_wet_and_dry_volume' if node.shared_volume is not None
               else 'explicit_shared_source_wet_volume') if node.wet_pressure_pairs else
              'explicit_shared_source_dry_volume' if node.shared_volume is not None else
              'original_independent_source_pressure')
    require(node.pressure_strategy==strategy,'source_study_pressure_strategy_binding')
    distance=max(abs(a.terminal.clock.lower.elapsed_since(b.terminal.clock.upper)),
                 abs(a.terminal.clock.upper.elapsed_since(b.terminal.clock.lower)))
    require(_same(node.clock_distance_upper_s,distance) and node.clock_gate==(distance<=F(event.time_absolute_s)),
            'source_study_event_clock_gate')
    limits=tuple(map(F,(event.amount_absolute_mol,event.energy_absolute_j,event.temperature_absolute_k,event.pressure_absolute_pa)))
    require(len(node.cell_endpoint_differences)==len(node.cell_endpoint_gates)==2,'source_study_event_matrix_rows')
    for phase_index,index in enumerate((0,-1)):
        ac,bc=a.captures[index],b.captures[index]
        ast,bst=reify(ac.state,memo),reify(bc.state,memo)
        rows=[];old_bounds=[];chosen=[]
        for i in range(len(a.seed.fixed_dry_mass_kg)):
            ai,bi=reify(ac.evaluation,memo).source_evaluation.cells[i].inverse,reify(bc.evaluation,memo).source_evaluation.cells[i].inverse
            row=(max(abs(F(float(x))-F(float(y))) for x,y in zip(ast.amounts_mol[i],bst.amounts_mol[i])),
                abs(F(float(ast.internal_energy_j[i]))-F(float(bst.internal_energy_j[i]))),
                abs(F(ai.point.temperature_k)-F(bi.point.temperature_k))+F(ai.temperature_error_bound_k)+F(bi.temperature_error_bound_k),
                abs(F(ai.point.pressure_pa)-F(bi.point.pressure_pa))+F(ai.point.pressure_error_pa)+F(bi.point.pressure_error_pa))
            rows.append(row)
            pa,pb=a.cell_pressure_endpoints[index][i],b.cell_pressure_endpoints[index][i]
            conditional=(abs(F(ai.point.pressure_pa)-F(bi.point.pressure_pa))+pa.continuation.radius_pa+pb.continuation.radius_pa
                         if pa.continuation.radius_pa is not None and pb.continuation.radius_pa is not None else None)
            old_bounds.append(conditional)
            if node.shared_volume is not None and i==node.selected_cell_index:
                pair=node.shared_pressure_pairs[phase_index]
                require(_same(pair.endpoints,(pa,pb)) and _same(pair.shared_volume,node.shared_volume),
                        'source_study_shared_dry_pair_endpoint_binding')
                chosen.append(pair.bound_pa)
            elif node.wet_pressure_pairs and node.wet_pressure_pairs[phase_index][i] is not None:
                pair=node.wet_pressure_pairs[phase_index][i]
                require(_same(pair.endpoints,(pa,pb)),'source_study_shared_wet_pair_endpoint_binding')
                chosen.append(pair.bound_pa)
            else:chosen.append(max(row[3],conditional) if conditional is not None else None)
        require(_same(node.cell_endpoint_differences[phase_index],tuple(rows))
                and _same(node.cell_endpoint_gates[phase_index],tuple(tuple(x<=limit for x,limit in zip(row,limits)) for row in rows)),
                'source_study_event_endpoint_gates')
        maxima=tuple(max(row[j] for row in rows) for j in range(4))
        require(_same(node.endpoint_differences[phase_index],(('event','common')[phase_index],ac.time,bc.time,maxima))
                and _same(node.endpoint_gates[phase_index],tuple(x<=limit for x,limit in zip(maxima,limits)))
                and _same(node.cell_conditional_pressure_bounds_pa[phase_index],tuple(old_bounds))
                and _same(node.cell_selected_pressure_bounds_pa[phase_index],tuple(chosen)),
                'source_study_event_pressure_selection_binding')
        old_gates=tuple(value<=limits[3] if value is not None else None for value in old_bounds)
        old_max=max(old_bounds) if all(value is not None for value in old_bounds) else None
        require(_same(node.cell_conditional_pressure_gates[phase_index],old_gates)
                and _same(node.conditional_pressure_bounds_pa[phase_index],old_max)
                and _same(node.conditional_pressure_gates[phase_index],
                          old_max<=limits[3] if old_max is not None else None),
                'source_study_original_conditional_pressure_gates')
        selected=node.cell_selected_pressure_bounds_pa[phase_index]
        require(len(selected)==len(rows) and _same(node.cell_selected_pressure_gates[phase_index],
            tuple(x<=limits[3] if x is not None else None for x in selected)), 'source_study_event_pressure_gate')
        aggregate=max(selected) if all(x is not None for x in selected) else None
        require(_same(node.selected_pressure_bounds_pa[phase_index],aggregate)
                and _same(node.selected_pressure_gates[phase_index],aggregate<=limits[3] if aggregate is not None else None),
                'source_study_event_pressure_aggregate')
    accepted=node.clock_gate and all(all(row[:3]) for row in node.endpoint_gates) and all(v is True for v in node.selected_pressure_gates)
    require(type(node.numerical_event_accepted) is bool and node.numerical_event_accepted==accepted
            and node.status==('conditional_numerical_event_accepted' if accepted else 'candidate_comparison_not_certified'),
            'source_study_event_acceptance_changed')
    checks['event_comparison_gates']+=1


def audit_study(roots,contexts,captures,metadata):
    checks=Counter();observations=[];memo={}
    expected_root={'seed':'SourcePrefixTrial','proposal':'SourceApproachProposal','approach':'SourceApproachResult',
        'refinement':'SourceRootRefinement','common_endpoint':'SourceCommonEndpointComparison',
        'transition':'SourceDryTransition','failure':'SourceStudyFailure'}
    for key,node in roots.items():
        require(_name(node)==expected_root[key],'source_study_root_type:'+key)
    links=(('proposal','seed',('original_trial',)),('approach','proposal',('proposal',)),
           ('refinement','approach',('approach',)),('transition','refinement',('refinement',)),
           ('common_endpoint','refinement',('refinement',)))
    for parent,child,path in links:
        if parent in roots and child in roots:
            value=roots[parent]
            for name in path:value=getattr(value,name)
            require(_same(value,roots[child]),'source_study_named_root_association')
    for i,capture in enumerate(captures):
        require(type(capture.get('ordinal')) is int and capture['ordinal']==i+1
                and type(capture.get('phase')) is str and type(capture.get('time')) is T,
                'source_study_capture_order')
        state=reify(capture.get('packed_input'),memo)
        require(type(state) is ConservedState and capture.get('energy_identity')==state.energy_model_identity,
                'source_study_capture_input_identity')
        evaluation=capture.get('evaluation')
        if has_capture_failure(capture):
            options=[context for context in contexts if context.operator_identity==capture.get('operator_identity')
                     and context.energy_identity==state.energy_model_identity
                     and (capture.get('interface_modes') is None or context.interface_modes==capture['interface_modes'])]
            require(bool(options) and state.amounts_mol.shape==(len(options[0].fixed_dry_mass_kg),4)
                    and state.internal_energy_j.shape==(len(options[0].fixed_dry_mass_kg),),
                    'source_study_failed_capture_input_context')
            # The entire closed typed return is retained in captures, without
            # calling it a validated observation after its recorded failure.
            observations.append(None);checks['failed_top_captures']+=1
            if evaluation is not None:checks['unvalidated_returned_top_captures']+=1
            continue
        require(evaluation is not None,'source_study_capture_missing_failure')
        evaluation=reify(evaluation,memo)
        require(evaluation.time==capture['time'] and evaluation.operator_identity==capture.get('operator_identity'),
                'source_study_capture_return_binding')
        record=_sample_record(state,evaluation,capture['phase'],contexts,capture.get('interface_modes'))
        observations.append(record);checks['top_source_observations']+=1
    pure_checks={'SourceAffinePanel','SourcePrefix','SourcePrefixAudit','SourcePanelRootOrder','InventoryRootOrder',
                 'QuadraticRoot','QuadraticNoRoot','PositiveApproachChoice','SourceRootClockComparison',
                 'SourceEndpointDifferences','PressureContinuation','DryPressureContinuation'}
    for node in _walk((roots,metadata)):
        validate_node(node);checks['complete_typed_nodes']+=1;name=_name(node)
        if name in pure_checks:
            obj=reify(node,memo);obj.check();checks['pure_'+name]+=1
        if name=='SourcePrefixTrial':_trial(node,memo,checks,contexts)
        elif name=='SourceTerminal':_terminal(node,memo,checks)
        elif name=='SourceDryCandidate':_candidate(node,memo,checks,contexts)
        elif name=='SourceDryTransition':
            _transition(node,memo,checks);_transition_balances(node,memo,checks)
        elif name in ('SourceInversePressure','SourceDryPressure'):_pressure(node,memo,checks)
        elif name in ('SourceSharedDryPressurePair','SourceSharedWetPressurePair'):_pair(node,memo,checks)
        elif name=='SourceApproachProposal':_proposal(node,memo,checks)
        elif name=='SourceApproachResult':_approach(node,memo,checks)
        elif name=='SourceRootRefinement':_refinement(node,memo,checks)
        elif name=='SourceEndpointComparison':_comparison(node,memo,checks)
        elif name=='SourceTrialPressure':_trial_pressure(node,memo,checks)
        elif name=='SourceCommonEndpointComparison':_common(node,memo,checks)
        elif name in ('SourceSharedDryVolume','SourceSharedWetVolume'):_shared_volume(node,memo,checks)
    if 'transition' in roots:
        require(metadata.get('numerical_event_accepted',roots['transition'].numerical_event_accepted)
                ==roots['transition'].numerical_event_accepted,'source_study_top_event_label')
    require(metadata.get('material_qualified',False) is False,'source_study_material_claim')
    audit=MappingProxyType(dict(validation_scope='passive_schema_source_observations_prefix_roots_writeback_reference_and_event_associations',
        checks=MappingProxyType(dict(sorted(checks.items()))),
        verified=('closed_complete_record_fields','successful_source_observation_associations','original_capture_positions_failures_and_unvalidated_returns',
                  'available_original_policy_and_attempt_bindings','available_pure_prefix_root_and_writeback_arithmetic',
                  'completed_saved_RHS_reference_replay_without_EOS','available_event_endpoint_and_gate_associations','complete_transition_local_and_global_cumulative_balances',
                  'pressure_input_associations_and_saved_joint_margin_sums'),
        not_verified=('live_adapter_storage_volume_identity','source_file_authentication','domain_wide_EOS_error_hypotheses',
                      'full_pressure_producer_decomposition_without_live_storage','terminal_live_configuration_and_transport_law','material_validation','continuation_or_resume'),
        material_qualified=False,resume_authorized=False,source_assets_verified=False))
    return tuple(observations),audit
