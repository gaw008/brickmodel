"""Execute and compare actual single-cell source wet-to-dry candidates.

The original integrator advances dry states. Candidate execution is separate
from conditional numerical event acceptance and from material qualification.
"""
from dataclasses import dataclass, fields, replace
from fractions import Fraction as F
import time

from .exact_event_clock import ExactEventTime as T
from .exact_integration import integrate_exact, ExactIntegrationResult
from .integration import IntegrationPolicy, IntegrationError, DomainExit
from .source_endpoint_comparison import _copy_policy, _policy_binding as _event_binding
from .source_prefix_trial import (SourcePrefixTrial, TrialCapture, _TrialStop,
    _policy_binding, _capture_source_observation, _check_source_captures,
    _complete_reference, _replay_source_reference)
from .source_net_prefix import _same
from .source_terminal import SourceTerminal, build_source_terminal, _require
from .source_dry_pressure import SourceDryPressure, enclose_source_dry_pressure
from .source_dry_shared_pressure import SourceSharedDryVolume, enclose_source_dry_pressure_pair
from .source_root_comparison import SourceRootRefinement


@dataclass(frozen=True)
class SourceDryCandidate:
    seed: SourcePrefixTrial
    event_policy: object
    event_policy_binding: str
    end: T
    maximum_callbacks: int
    controls_binding: tuple
    terminal: SourceTerminal | None
    dry_policy: IntegrationPolicy | None
    dry_policy_binding: tuple | None
    reference: ExactIntegrationResult | None
    captures: tuple[TrialCapture, ...]
    pressure_endpoints: tuple[SourceDryPressure, ...]
    status: str
    reason: str | None
    outcome_binding: tuple
    elapsed_seconds: float
    qualification: str = 'executed_source_candidate_not_event_acceptance_or_material_validation'
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self):
        self.seed.check()
        _require(_same(self.controls_binding,(self.end,self.maximum_callbacks))
                 and type(self.end) is T and type(self.end.seconds) is F
                 and type(self.maximum_callbacks) is int and self.maximum_callbacks>0,
                 'source_dry_candidate_controls_changed')
        _require(self.event_policy_binding==_event_binding(self.event_policy)
                 and _same(self.outcome_binding,(self.status,self.reason)), 'source_dry_candidate_policy_or_outcome_changed')
        _require(type(self.captures) is tuple and len(self.captures)<=self.maximum_callbacks,
                 'source_dry_actual_capture_budget')
        if self.terminal is not None:
            self.terminal.check()
            _require(_same(self.terminal.seed,self.seed)
                     and self.terminal.policy_binding==self.event_policy_binding, 'source_dry_terminal_binding_changed')
            view=self.terminal.dry_adapter
            _check_source_captures(self.captures,start=self.terminal.clock.lower,end=self.end,
                operator_identity=view.operator_identity,energy_identity=self.seed.energy_identity,
                masses=self.seed.fixed_dry_mass_kg)
            _require(all(c.role=='dry_reference' for c in self.captures), 'source_dry_capture_role_changed')
        else:
            _require(not self.captures and self.reference is None and not self.pressure_endpoints,
                     'source_dry_evaluation_without_terminal')
        if self.dry_policy is not None:
            _require(_same(self.dry_policy_binding,_policy_binding(self.dry_policy)),
                     'source_dry_execution_policy_binding_changed')
            self.dry_policy.__post_init__()
            _require(all(_same(getattr(self.dry_policy,f.name),getattr(self.seed.policy,f.name))
                         for f in fields(self.seed.policy) if f.name!='maximum_wall_seconds')
                     and 0<self.dry_policy.maximum_wall_seconds<=self.seed.policy.maximum_wall_seconds,
                     'source_dry_original_integration_policy_changed')
        else:
            _require(self.dry_policy_binding is None, 'source_dry_policy_binding_without_policy')
        for bound in self.pressure_endpoints:
            _require(type(bound) is SourceDryPressure, 'source_dry_actual_pressure_record_required')
            bound.check()
        if self.status=='executed_dry_candidate':
            _require(self.reason is None and self.terminal is not None and self.dry_policy is not None
                     and len(self.pressure_endpoints)==2 and bool(self.captures), 'source_dry_success_evidence_missing')
            _complete_reference(self.reference,self.terminal.clock.lower,self.end,self.terminal.corrected_state)
            _require(bool(self.reference.steps) and self.reference.evaluations==len(self.captures)
                     and all((c.evaluation is not None and c.binding is not None and c.failure is None)
                             or (c.failure_kind=='DomainExit' and type(c.failure) is str) for c in self.captures),
                     'source_dry_complete_attempt_history_required')
            _replay_source_reference(self.terminal.corrected_state,self.terminal.clock.lower,self.end,
                replace(self.dry_policy,maximum_wall_seconds=self.seed.policy.maximum_wall_seconds),
                self.captures,self.reference,breakpoints=view.breakpoints(self.terminal.clock.lower,self.end))
            for c,bound in zip((self.captures[0],self.captures[-1]),self.pressure_endpoints):
                _require(c.evaluation is not None and c.failure is None
                         and _same(bound.state,c.evaluation.source_states[0])
                         and _same(bound.inverse,c.evaluation.source_evaluation.cells[0].inverse),
                         'source_dry_endpoint_pressure_binding_changed')
        _require(self.qualification=='executed_source_candidate_not_event_acceptance_or_material_validation'
                 and self.event_admitted is False and self.material_qualified is False,
                 'source_dry_candidate_qualification_changed')


def execute_source_dry_candidate(seed, *, event_policy, end: T, maximum_callbacks: int,
                                 cancel=None, prior_clock=None, root_index=None) -> SourceDryCandidate:
    """Execute one candidate once, retaining failed dry integrations and callbacks."""
    _require(type(seed) is SourcePrefixTrial and type(end) is T and type(end.seconds) is F
             and seed.start<end and type(maximum_callbacks) is int and maximum_callbacks>0
             and (cancel is None or callable(cancel)), 'explicit_source_dry_execution_controls_required')
    begin=time.monotonic()
    event=_copy_policy(event_policy)
    _require(event is not None, 'explicit_source_dry_event_policy_required')
    binding=_event_binding(event); seed.check()
    terminal=dry_policy=dry_policy_binding=reference=None
    captures=[]; bounds=[]; stop=None

    def guard():
        _require(binding==_event_binding(event)
                 and _same(seed.policy_binding,_policy_binding(seed.policy)), 'source_dry_original_policy_changed')
        _require(seed.adapter.operator_identity==seed.operator_identity, 'source_dry_wet_operator_changed')
        if cancel is not None and cancel():
            raise _TrialStop('cancelled','cancel_requested')
        if time.monotonic()-begin>=seed.policy.maximum_wall_seconds:
            raise _TrialStop('resource_limit','source_dry_total_wall_limit')

    def callback(state,when):
        nonlocal stop
        try:
            return _capture_source_observation(terminal.dry_adapter,state,when,'dry_reference',captures,
                maximum_callbacks=maximum_callbacks,guard=guard,
                operator_identity=terminal.dry_adapter.operator_identity,energy_identity=seed.energy_identity,
                masses=seed.fixed_dry_mass_kg).rates
        except _TrialStop as exc:
            stop=exc
            raise IntegrationError(str(exc)) from exc

    try:
        guard()
        terminal=build_source_terminal(seed,event_policy=event,prior_clock=prior_clock,root_index=root_index)
        _require(terminal.clock.upper<end, 'source_dry_common_end_must_follow_entire_root_interval')
        guard()
        remaining=seed.policy.maximum_wall_seconds-(time.monotonic()-begin)
        _require(remaining>0, 'source_dry_no_remaining_wall_budget')
        dry_policy=replace(seed.policy,maximum_wall_seconds=remaining)
        dry_policy_binding=_policy_binding(dry_policy)
        reference=integrate_exact(terminal.corrected_state,callback,start_s=terminal.clock.lower,end_s=end,
            policy=dry_policy,breakpoints_s=terminal.dry_adapter.breakpoints(terminal.clock.lower,end),cancel=cancel)
        if stop is not None:
            raise stop
        if reference.status!='completed':
            raise _TrialStop(reference.status,'dry_reference:'+str(reference.reason))
        guard()
        for capture in (captures[0],captures[-1]):
            obs=capture.evaluation
            bounds.append(enclose_source_dry_pressure(terminal.dry_adapter.column.storages[0],
                obs.source_states[0],obs.source_evaluation.cells[0].inverse))
        status,reason='executed_dry_candidate',None
    except _TrialStop as exc:
        status,reason=exc.status,str(exc)
    except DomainExit as exc:
        status,reason='domain_exit',str(exc)
    except Exception as exc:
        status,reason='failed',type(exc).__name__+':'+str(exc)
    result=SourceDryCandidate(seed,event,binding,end,maximum_callbacks,(T(end.seconds),maximum_callbacks),terminal,
        dry_policy,dry_policy_binding,reference,tuple(captures),tuple(bounds),status,reason,(status,reason),time.monotonic()-begin)
    if status=='executed_dry_candidate':
        try:
            result.check()
            guard()
        except _TrialStop as exc:
            result=replace(result,status=exc.status,reason=str(exc),outcome_binding=(exc.status,str(exc)))
        except Exception as exc:
            reason=type(exc).__name__+':'+str(exc)
            result=replace(result,status='failed',reason=reason,outcome_binding=('failed',reason))
    return replace(result,elapsed_seconds=time.monotonic()-begin)


@dataclass(frozen=True)
class SourceTransitionBalance:
    time: T
    phase: str
    inventory_residual_mol: tuple
    energy_residual_j: F
    full_inventory_residual_mol: tuple
    full_energy_residual_j: F
    water_balance_residual_mol: F
    event_water_storage_roundoff_mol: F
    fluid_element_residuals_mol: tuple
    fluid_mass_residual_kg: F


def _audit_path(candidate, ordinary=()):
    """All prefixes share one origin; writeback storage error stays explicit."""
    seed=candidate.seed; terminal=candidate.terminal
    initial=ordinary[0].initial if ordinary else seed.initial
    previous=initial; previous_time=ordinary[0].start if ordinary else seed.start
    exchange=[F()]*4; full=[F()]*4; energy=F(); full_energy=F()
    correction=[F()]*4; storage=F(); rows=[]
    masses=candidate.captures[0].evaluation.source_evaluation.gas_states[0].molar_masses_kg_mol
    policy=seed.policy

    def record(state,when,phase):
        nr=tuple(F(float(x))-F(float(y))-n-c for x,y,n,c in
                 zip(state.amounts_mol[0],initial.amounts_mol[0],exchange,correction))
        fnr=tuple(F(float(x))-F(float(y))-n-c for x,y,n,c in
                 zip(state.amounts_mol[0],initial.amounts_mol[0],full,correction))
        ur=F(float(state.internal_energy_j[0]))-F(float(initial.internal_energy_j[0]))-energy
        fur=F(float(state.internal_energy_j[0]))-F(float(initial.internal_energy_j[0]))-full_energy
        _require(all(abs(v)<=F(policy.amount_absolute_tolerance_mol) for v in (*nr,*fnr))
                 and max(abs(ur),abs(fur))<=F(policy.energy_absolute_tolerance_j),
                 'source_transition_cumulative_original_balance_budget')
        water=nr[0]+nr[3]+storage
        elements=(('H',2*water),('O',water+2*nr[1]),('N',2*nr[2]))
        mass=F(masses['H2O'])*water+F(masses['O2'])*nr[1]+F(masses['N2'])*nr[2]
        rows.append(SourceTransitionBalance(when,phase,nr,ur,fnr,fur,water,storage,elements,mass))

    def step(state,ledger,phase,exact=None):
        nonlocal energy,full_energy,previous,previous_time
        _require(ledger.start_s==previous_time, 'source_transition_ledger_time_gap')
        n=[F(float(ledger.face_species_mol[0,j]))-F(float(ledger.face_species_mol[1,j]))
           +F(float(ledger.reaction_species_mol[0,j])) for j in range(4)]
        u=F(float(ledger.face_energy_j[0]))-F(float(ledger.face_energy_j[1]))+F(float(ledger.cell_work_j[0]))
        exact_n,exact_u=(n,u) if exact is None else exact
        for j in range(4):
            exchange[j]+=n[j];full[j]+=exact_n[j]
        energy+=u;full_energy+=exact_u
        record(state,ledger.end_s,phase)
        previous,previous_time=state,ledger.end_s

    for trial in ordinary:
        trial.check()
        _require(trial.status=='validated_positive_numerical_trial'
                 and _same((trial.initial,trial.start,trial.policy),(previous,previous_time,policy)),
                 'source_transition_ordinary_path_connection_changed')
        for state,ledger in zip(trial.reference.states[1:],trial.reference.steps):
            step(state,ledger,'wet_reference')
    _require(_same((seed.initial,seed.start),(previous,previous_time)), 'source_transition_terminal_connection_changed')
    pieces={name:values for name,values,_ in terminal.prefix.integrals}
    fn=pieces['face_species_mol_s'];rn=pieces['reaction_species_mol_s']
    exact_n=[fn[j]-fn[j+4]+rn[j] for j in range(4)]
    fu=pieces['face_energy_w'];power=pieces['cell_power_w']
    step(terminal.prefix.raw_state,terminal.prefix.ledger,'wet_terminal',(exact_n,fu[0]-fu[1]+power[0]))
    corrected=terminal.corrected_state
    correction=[F(float(a))-F(float(b)) for a,b in zip(corrected.amounts_mol[0],previous.amounts_mol[0])]
    storage=terminal.totals.signed_storage_roundoff_mol
    _require(sum(correction,F())==storage and _same(previous.internal_energy_j,corrected.internal_energy_j),
             'source_transition_writeback_water_or_energy_changed')
    record(corrected,previous_time,'writeback')
    previous=corrected
    for state,ledger in zip(candidate.reference.states[1:],candidate.reference.steps):
        step(state,ledger,'dry_reference')
    return tuple(rows)


@dataclass(frozen=True)
class SourceDryTransition:
    refinement: SourceRootRefinement
    candidates: tuple[SourceDryCandidate, SourceDryCandidate]
    balance_paths: tuple
    clock_distance_upper_s: F
    clock_gate: bool
    endpoint_differences: tuple
    endpoint_gates: tuple
    conditional_pressure_bounds_pa: tuple
    conditional_pressure_gates: tuple
    numerical_event_accepted: bool
    status: str
    qualification: str = 'declared_model_numerical_wet_dry_comparison_not_material_validation'
    material_qualified: bool = False
    shared_volume: SourceSharedDryVolume | None = None
    shared_pressure_pairs: tuple = ()
    selected_pressure_bounds_pa: tuple = ()
    selected_pressure_gates: tuple = ()
    pressure_strategy: str = 'original_independent_source_pressure'

    def check(self):
        expected=compare_source_dry_candidates(self.refinement,self.candidates,shared_volume=self.shared_volume)
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name)) for f in fields(self)
                     if f.name not in ('refinement','candidates')), 'source_dry_transition_comparison_changed')


def _check_shared_volume(refinement, shared_volume):
    if shared_volume is not None:
        _require(type(shared_volume) is SourceSharedDryVolume, 'explicit_source_shared_volume_required')
        shared_volume.check()
        storage=refinement.approach.proposal.original_trial.adapter.column.storages[0]
        _require(shared_volume.storage is storage, 'source_shared_volume_must_belong_to_original_path')


def compare_source_dry_candidates(refinement, candidates, *, shared_volume=None) -> SourceDryTransition:
    _require(type(refinement) is SourceRootRefinement and type(candidates) is tuple
             and len(candidates)==2 and all(type(c) is SourceDryCandidate for c in candidates),
             'actual_source_dry_comparison_inputs_required')
    refinement.check()
    _check_shared_volume(refinement,shared_volume)
    expected=(refinement.approach.proposal.original_trial,refinement.shifted_trial)
    _require(refinement.clock is not None, 'source_dry_compared_prior_clock_required')
    for index,(candidate,seed) in enumerate(zip(candidates,expected)):
        candidate.check()
        _require(candidate.status=='executed_dry_candidate' and _same(candidate.seed,seed)
                 and candidate.event_policy_binding==refinement.approach.proposal.policy_binding,
                 'source_dry_comparison_original_path_binding')
        _require(_same(candidate.terminal.prior_clock,refinement.clock)
                 and type(candidate.terminal.root_index) is int and candidate.terminal.root_index==index,
                 'source_dry_comparison_prior_clock_binding_changed')
    a,b=candidates
    _require(a.end==b.end and a.terminal.dry_adapter.operator_identity==b.terminal.dry_adapter.operator_identity,
             'source_dry_paths_require_same_final_time_and_operator')
    event=a.event_policy
    ca,cb=a.terminal.clock,b.terminal.clock
    distance=max(abs(ca.lower.elapsed_since(cb.upper)),abs(ca.upper.elapsed_since(cb.lower)))
    differences=[];gates=[];pressure=[];pgates=[];pairs=[];selected=[];selected_gates=[]
    limits=tuple(map(F,(event.amount_absolute_mol,event.energy_absolute_j,event.temperature_absolute_k,event.pressure_absolute_pa)))
    for k,label in ((0,'event'),(-1,'common')):
        ac,bc=a.captures[k],b.captures[k]
        ai,bi=(c.evaluation.source_evaluation.cells[0].inverse for c in (ac,bc))
        row=(max(abs(F(float(x))-F(float(y))) for x,y in zip(ac.state.amounts_mol.flat,bc.state.amounts_mol.flat)),
             abs(F(float(ac.state.internal_energy_j[0]))-F(float(bc.state.internal_energy_j[0]))),
             abs(F(ai.point.temperature_k)-F(bi.point.temperature_k))+F(ai.temperature_error_bound_k)+F(bi.temperature_error_bound_k),
             abs(F(ai.point.pressure_pa)-F(bi.point.pressure_pa))+F(ai.point.pressure_error_pa)+F(bi.point.pressure_error_pa))
        pa,pb=a.pressure_endpoints[k],b.pressure_endpoints[k]
        bound=(abs(F(ai.point.pressure_pa)-F(bi.point.pressure_pa))+pa.continuation.radius_pa+pb.continuation.radius_pa
               if pa.continuation.status==pb.continuation.status=='conditional_dry_pressure_enclosure' else None)
        differences.append((label,ac.time,bc.time,row));gates.append(tuple(v<=limit for v,limit in zip(row,limits)))
        pressure.append(bound);pgates.append(bound<=F(event.pressure_absolute_pa) if bound is not None else None)
        if shared_volume is None:
            chosen=max(row[3],bound) if bound is not None else None
        else:
            pair=enclose_source_dry_pressure_pair(pa,pb,shared_volume=shared_volume)
            pairs.append(pair)
            chosen=pair.bound_pa if pair.status=='conditional_shared_dry_pressure_enclosure' else None
        selected.append(chosen)
        selected_gates.append(chosen<=F(event.pressure_absolute_pa) if chosen is not None else None)
    balances=(_audit_path(a),_audit_path(b,(refinement.approach.trial,)))
    accepted=distance<=F(event.time_absolute_s) and all(all(row[:3]) for row in gates) and all(v is True for v in selected_gates)
    return SourceDryTransition(refinement,candidates,balances,distance,distance<=F(event.time_absolute_s),
        tuple(differences),tuple(gates),tuple(pressure),tuple(pgates),accepted,
        'conditional_numerical_event_accepted' if accepted else 'candidate_comparison_not_certified',
        shared_volume=shared_volume,shared_pressure_pairs=tuple(pairs),
        selected_pressure_bounds_pa=tuple(selected),selected_pressure_gates=tuple(selected_gates),
        pressure_strategy='explicit_shared_source_dry_volume' if shared_volume is not None
                          else 'original_independent_source_pressure')


class SourceDryTransitionError(IntegrationError):
    def __init__(self,stage,refinement,candidates,cause):
        self.stage,self.refinement,self.candidates=stage,refinement,tuple(candidates)
        self.exception_type,self.exception_message=type(cause).__name__,str(cause)
        super().__init__(f'source_dry_transition_failed:{stage}:{type(cause).__name__}:{cause}')


def evaluate_source_dry_transition(refinement, *, end: T, maximum_callbacks_per_path: int,
                                   cancel=None, shared_volume=None) -> SourceDryTransition:
    """Execute two actual wet/dry paths once; the caller owns outer study limits."""
    _require(type(refinement) is SourceRootRefinement, 'actual_source_root_refinement_required')
    refinement.check()
    _check_shared_volume(refinement,shared_volume)
    _require(refinement.clock is not None, 'source_dry_compared_prior_clock_required')
    candidates=[];stage='coarse_candidate'
    try:
        for index,seed in enumerate((refinement.approach.proposal.original_trial,refinement.shifted_trial)):
            candidate=execute_source_dry_candidate(seed,event_policy=refinement.approach.proposal.event_policy,
                end=end,maximum_callbacks=maximum_callbacks_per_path,cancel=cancel,
                prior_clock=refinement.clock,root_index=index)
            candidates.append(candidate)
            _require(candidate.status=='executed_dry_candidate',candidate.status+':'+str(candidate.reason))
            stage='shifted_candidate'
        stage='source_event_comparison'
        result=compare_source_dry_candidates(refinement,tuple(candidates),shared_volume=shared_volume)
        result.check()
        return result
    except Exception as exc:
        raise SourceDryTransitionError(stage,refinement,candidates,exc) from exc
