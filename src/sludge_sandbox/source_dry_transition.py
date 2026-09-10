"""Execute and compare source columns across one selected wet-to-dry event.

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
from .source_inverse_pressure import SourceInversePressure, enclose_source_inverse_pressure
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
    # Two time rows, each retaining every cell's actual dry or wet enclosure.
    # pressure_endpoints remains the selected dry cell's two records.
    cell_pressure_endpoints: tuple = ()

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
            _require(not self.captures and self.reference is None and not self.pressure_endpoints
                     and not self.cell_pressure_endpoints,
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
            _require(self.terminal is not None and bound.storage is
                     self.terminal.dry_adapter.column.storages[self.terminal.selected_cell_index],
                     'source_selected_pressure_storage_changed')
            bound.check()
        _require(type(self.cell_pressure_endpoints) is tuple and len(self.cell_pressure_endpoints)<=2,
                 'source_cell_pressure_time_rows_required')
        if self.terminal is not None:
            selected=self.terminal.selected_cell_index
            count=view.column.cell_count
            _require(not self.cell_pressure_endpoints or bool(self.captures),
                     'source_cell_pressure_without_actual_capture')
            for capture,row in zip((self.captures[0],self.captures[-1]) if self.captures else (),
                                   self.cell_pressure_endpoints):
                _require(type(row) is tuple and len(row)<=count and capture.evaluation is not None,
                         'source_cell_pressure_row_shape')
                observation=capture.evaluation
                for i,bound in enumerate(row):
                    state=observation.source_states[i]
                    expected_type=SourceDryPressure if state.liquid_water_mol==0 else SourceInversePressure
                    _require(type(bound) is expected_type
                             and bound.storage is view.column.storages[i]
                             and _same(bound.state,state)
                             and _same(bound.inverse,observation.source_evaluation.cells[i].inverse),
                             'source_cell_pressure_binding_changed')
                    bound.check()
            _require(_same(self.pressure_endpoints,
                          tuple(row[selected] for row in self.cell_pressure_endpoints if len(row)>selected)),
                     'source_selected_pressure_cell_changed')
        if self.status=='executed_dry_candidate':
            _require(self.reason is None and self.terminal is not None and self.dry_policy is not None
                     and len(self.pressure_endpoints)==2 and bool(self.captures)
                     and len(self.cell_pressure_endpoints)==2
                     and all(len(row)==count for row in self.cell_pressure_endpoints),
                     'source_dry_success_evidence_missing')
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
                         and _same(bound.state,c.evaluation.source_states[selected])
                         and _same(bound.inverse,c.evaluation.source_evaluation.cells[selected].inverse),
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
    captures=[]; bounds=[]; cell_bounds=[]; stop=None

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
            cell_bounds.append(())
            for i,storage in enumerate(terminal.dry_adapter.column.storages):
                state=obs.source_states[i]
                enclose=enclose_source_dry_pressure if state.liquid_water_mol==0 else enclose_source_inverse_pressure
                bound=enclose(storage,state,obs.source_evaluation.cells[i].inverse)
                cell_bounds[-1]=(*cell_bounds[-1],bound)
                if i==terminal.selected_cell_index:
                    bounds.append(bound)
        status,reason='executed_dry_candidate',None
    except _TrialStop as exc:
        status,reason=exc.status,str(exc)
    except DomainExit as exc:
        status,reason='domain_exit',str(exc)
    except Exception as exc:
        status,reason='failed',type(exc).__name__+':'+str(exc)
    result=SourceDryCandidate(seed,event,binding,end,maximum_callbacks,(T(end.seconds),maximum_callbacks),terminal,
        dry_policy,dry_policy_binding,reference,tuple(captures),tuple(bounds),status,reason,(status,reason),time.monotonic()-begin,
        cell_pressure_endpoints=tuple(cell_bounds))
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
class SourceTransitionCellBalance:
    cell_index: int
    inventory_residual_mol: tuple
    energy_residual_j: F
    full_inventory_residual_mol: tuple
    full_energy_residual_j: F
    water_balance_residual_mol: F
    event_water_storage_roundoff_mol: F
    fluid_element_residuals_mol: tuple
    fluid_mass_residual_kg: F


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
    cell_balances: tuple[SourceTransitionCellBalance, ...] = ()


def _audit_path(candidate, ordinary=()):
    """Validate live path connections, then share the exact saved-field audit."""
    seed=candidate.seed; terminal=candidate.terminal
    initial=ordinary[0].initial if ordinary else seed.initial
    start=ordinary[0].start if ordinary else seed.start
    policy=seed.policy

    def references():
        previous,previous_time=initial,start
        for trial in ordinary:
            trial.check()
            _require(trial.status=='validated_positive_numerical_trial'
                     and _same((trial.initial,trial.start,trial.policy),(previous,previous_time,policy)),
                     'source_transition_ordinary_path_connection_changed')
            yield trial.reference
            if trial.reference.steps:
                previous=trial.reference.states[-1]
                previous_time=trial.reference.steps[-1].end_s
        _require(_same((seed.initial,seed.start),(previous,previous_time)),
                 'source_transition_terminal_connection_changed')

    masses=tuple(g.molar_masses_kg_mol for g in candidate.captures[0].evaluation.source_evaluation.gas_states)
    return _audit_balance_fields(initial,start,policy,masses,wet_references=references(),
        terminal_prefix=terminal.prefix,corrected_state=terminal.corrected_state,
        selected_cell_index=terminal.selected_cell_index,
        signed_storage_roundoff_mol=terminal.totals.signed_storage_roundoff_mol,
        dry_reference=candidate.reference)


def _audit_balance_fields(initial, start, policy, masses, *, wet_references,
        terminal_prefix, corrected_state, selected_cell_index,
        signed_storage_roundoff_mol, dry_reference):
    """Pure balances for already validated saved states and ledger fields.

    No adapter or provider is accepted. Callers validate reference connections
    and complete records before supplying this numerical projection. Original
    local and global absolute budgets are each retained without a grid factor.
    """
    previous,previous_time=initial,start
    count=initial.amounts_mol.shape[0]
    exchange=[[F()]*4 for _ in range(count)]; full=[[F()]*4 for _ in range(count)]
    energy=[F()]*count; full_energy=[F()]*count
    correction=[[F()]*4 for _ in range(count)]; storage=[F()]*count; rows=[]

    def bounded(nr,fnr,ur,fur):
        _require(all(abs(v)<=F(policy.amount_absolute_tolerance_mol) for v in (*nr,*fnr))
                 and max(abs(ur),abs(fur))<=F(policy.energy_absolute_tolerance_j),
                 'source_transition_cumulative_original_balance_budget')

    def record(state,when,phase):
        cells=[]
        for i in range(count):
            nr=tuple(F(float(x))-F(float(y))-n-c for x,y,n,c in
                     zip(state.amounts_mol[i],initial.amounts_mol[i],exchange[i],correction[i]))
            fnr=tuple(F(float(x))-F(float(y))-n-c for x,y,n,c in
                     zip(state.amounts_mol[i],initial.amounts_mol[i],full[i],correction[i]))
            ur=F(float(state.internal_energy_j[i]))-F(float(initial.internal_energy_j[i]))-energy[i]
            fur=F(float(state.internal_energy_j[i]))-F(float(initial.internal_energy_j[i]))-full_energy[i]
            bounded(nr,fnr,ur,fur)
            water=nr[0]+nr[3]+storage[i]
            elements=(('H',2*water),('O',water+2*nr[1]),('N',2*nr[2]))
            mass=F(masses[i]['H2O'])*water+F(masses[i]['O2'])*nr[1]+F(masses[i]['N2'])*nr[2]
            cells.append(SourceTransitionCellBalance(i,nr,ur,fnr,fur,water,storage[i],elements,mass))
        nr=tuple(sum((c.inventory_residual_mol[j] for c in cells),F()) for j in range(4))
        fnr=tuple(sum((c.full_inventory_residual_mol[j] for c in cells),F()) for j in range(4))
        ur=sum((c.energy_residual_j for c in cells),F())
        fur=sum((c.full_energy_residual_j for c in cells),F())
        bounded(nr,fnr,ur,fur)
        water=sum((c.water_balance_residual_mol for c in cells),F())
        elements=tuple((label,sum((dict(c.fluid_element_residuals_mol)[label] for c in cells),F()))
                       for label in ('H','O','N'))
        mass=sum((c.fluid_mass_residual_kg for c in cells),F())
        rows.append(SourceTransitionBalance(when,phase,nr,ur,fnr,fur,water,sum(storage,F()),elements,mass,
                                            tuple(cells)))

    def step(state,ledger,phase,exact=None):
        nonlocal previous,previous_time
        _require(ledger.start_s==previous_time, 'source_transition_ledger_time_gap')
        n=[[F(float(ledger.face_species_mol[i,j]))-F(float(ledger.face_species_mol[i+1,j]))
            +F(float(ledger.reaction_species_mol[i,j])) for j in range(4)] for i in range(count)]
        u=[F(float(ledger.face_energy_j[i]))-F(float(ledger.face_energy_j[i+1]))
           +F(float(ledger.cell_work_j[i])) for i in range(count)]
        exact_n,exact_u=(n,u) if exact is None else exact
        for i in range(count):
            for j in range(4):
                exchange[i][j]+=n[i][j];full[i][j]+=exact_n[i][j]
            energy[i]+=u[i];full_energy[i]+=exact_u[i]
        record(state,ledger.end_s,phase)
        previous,previous_time=state,ledger.end_s

    for reference in wet_references:
        for state,ledger in zip(reference.states[1:],reference.steps):
            step(state,ledger,'wet_reference')
    pieces={name:values for name,values,_ in terminal_prefix.integrals}
    fn=pieces['face_species_mol_s'];rn=pieces['reaction_species_mol_s']
    exact_n=[[fn[i*4+j]-fn[(i+1)*4+j]+rn[i*4+j] for j in range(4)] for i in range(count)]
    fu=pieces['face_energy_w'];power=pieces['cell_power_w']
    exact_u=[fu[i]-fu[i+1]+power[i] for i in range(count)]
    step(terminal_prefix.raw_state,terminal_prefix.ledger,'wet_terminal',(exact_n,exact_u))
    corrected=corrected_state
    correction=[[F(float(a))-F(float(b)) for a,b in zip(row_a,row_b)]
                for row_a,row_b in zip(corrected.amounts_mol,previous.amounts_mol)]
    selected=selected_cell_index
    storage[selected]=signed_storage_roundoff_mol
    _require(all(sum(row,F())==storage[i] for i,row in enumerate(correction))
             and all(v==0 for i,row in enumerate(correction) if i!=selected for v in row)
             and correction[selected][1]==correction[selected][2]==0
             and _same(previous.internal_energy_j,corrected.internal_energy_j),
             'source_transition_writeback_water_or_energy_changed')
    record(corrected,previous_time,'writeback')
    previous=corrected
    for state,ledger in zip(dry_reference.states[1:],dry_reference.steps):
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
    selected_cell_index: int = 0
    cell_endpoint_differences: tuple = ()
    cell_endpoint_gates: tuple = ()
    cell_conditional_pressure_bounds_pa: tuple = ()
    cell_conditional_pressure_gates: tuple = ()
    cell_selected_pressure_bounds_pa: tuple = ()
    cell_selected_pressure_gates: tuple = ()
    wet_pressure_pairs: tuple = ()

    def check(self):
        expected=compare_source_dry_candidates(self.refinement,self.candidates,
            shared_volume=self.shared_volume,wet_pressure_pairs=self.wet_pressure_pairs)
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name)) for f in fields(self)
                     if f.name not in ('refinement','candidates')), 'source_dry_transition_comparison_changed')


def _check_shared_volume(refinement, shared_volume):
    if shared_volume is not None:
        _require(type(shared_volume) is SourceSharedDryVolume, 'explicit_source_shared_volume_required')
        shared_volume.check()
        choice=refinement.approach.proposal.choice
        _require(choice is not None and choice.selected_root is not None,
                 'source_shared_volume_requires_selected_liquid_root')
        selected=choice.selected_root.polynomial.cell
        storage=refinement.approach.proposal.original_trial.adapter.column.storages[selected]
        _require(shared_volume.storage is storage, 'source_shared_volume_must_belong_to_original_path')


def compare_source_dry_candidates(refinement, candidates, *, shared_volume=None,
                                  wet_pressure_pairs=()) -> SourceDryTransition:
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
    selected_cell=a.terminal.selected_cell_index
    count=a.terminal.dry_adapter.column.cell_count
    _require(type(wet_pressure_pairs) is tuple, 'explicit_source_wet_pressure_grid_required')
    if wet_pressure_pairs:
        from .source_wet_shared_pressure import SourceSharedWetPressurePair
        _require(len(wet_pressure_pairs)==2 and all(type(row) is tuple and len(row)==count
                 for row in wet_pressure_pairs), 'complete_source_wet_pressure_grid_required')
        _require(any(pair is not None for row in wet_pressure_pairs for pair in row),
                 'nonempty_source_wet_pressure_strategy_required')
        for phase_index,row in enumerate(wet_pressure_pairs):
            for cell,pair in enumerate(row):
                if pair is None:
                    continue
                _require(type(pair) is SourceSharedWetPressurePair,
                         'actual_source_shared_wet_pressure_pair_required')
                _require(type(pair.endpoints) is tuple and len(pair.endpoints)==2,
                         'two_source_wet_pressure_endpoints_required')
                pair.check()
                endpoints=(a.cell_pressure_endpoints[phase_index][cell],
                           b.cell_pressure_endpoints[phase_index][cell])
                _require(cell!=selected_cell and all(type(end) is SourceInversePressure for end in endpoints)
                         and pair.endpoints[0] is endpoints[0] and pair.endpoints[1] is endpoints[1],
                         'source_wet_pressure_pair_original_cell_and_time_required')
                storage=refinement.approach.proposal.original_trial.adapter.column.storages[cell]
                _require(pair.shared_volume.storage is storage,
                         'source_wet_pressure_volume_original_cell_required')
    _require(a.end==b.end and a.terminal.dry_adapter.operator_identity==b.terminal.dry_adapter.operator_identity
             and selected_cell==b.terminal.selected_cell_index,
             'source_dry_paths_require_same_final_time_and_operator')
    event=a.event_policy
    ca,cb=a.terminal.clock,b.terminal.clock
    distance=max(abs(ca.lower.elapsed_since(cb.upper)),abs(ca.upper.elapsed_since(cb.lower)))
    differences=[];gates=[];pressure=[];pgates=[];pairs=[];selected=[];selected_gates=[]
    cell_differences=[];cell_gates=[];cell_pressure=[];cell_pgates=[];cell_selected=[];cell_selected_gates=[]
    limits=tuple(map(F,(event.amount_absolute_mol,event.energy_absolute_j,event.temperature_absolute_k,event.pressure_absolute_pa)))
    for phase_index,(k,label) in enumerate(((0,'event'),(-1,'common'))):
        ac,bc=a.captures[k],b.captures[k]
        rows=[];original_bounds=[];chosen_bounds=[]
        for i in range(count):
            ai,bi=(c.evaluation.source_evaluation.cells[i].inverse for c in (ac,bc))
            row=(max(abs(F(float(x))-F(float(y))) for x,y in zip(ac.state.amounts_mol[i],bc.state.amounts_mol[i])),
                 abs(F(float(ac.state.internal_energy_j[i]))-F(float(bc.state.internal_energy_j[i]))),
                 abs(F(ai.point.temperature_k)-F(bi.point.temperature_k))+F(ai.temperature_error_bound_k)+F(bi.temperature_error_bound_k),
                 abs(F(ai.point.pressure_pa)-F(bi.point.pressure_pa))+F(ai.point.pressure_error_pa)+F(bi.point.pressure_error_pa))
            pa,pb=a.cell_pressure_endpoints[k][i],b.cell_pressure_endpoints[k][i]
            _require(type(pa) is type(pb), 'source_compared_cell_phase_changed')
            expected_status=('conditional_dry_pressure_enclosure' if type(pa) is SourceDryPressure
                             else 'conditional_pressure_enclosure')
            bound=(abs(F(ai.point.pressure_pa)-F(bi.point.pressure_pa))+pa.continuation.radius_pa+pb.continuation.radius_pa
                   if pa.continuation.status==pb.continuation.status==expected_status else None)
            rows.append(row);original_bounds.append(bound)
            if shared_volume is not None and i==selected_cell:
                pair=enclose_source_dry_pressure_pair(pa,pb,shared_volume=shared_volume)
                pairs.append(pair)
                chosen=pair.bound_pa if pair.status=='conditional_shared_dry_pressure_enclosure' else None
            elif wet_pressure_pairs and wet_pressure_pairs[phase_index][i] is not None:
                wet_pair=wet_pressure_pairs[phase_index][i]
                chosen=(wet_pair.bound_pa if wet_pair.status=='conditional_shared_wet_pressure_enclosure'
                        else None)
            else:
                chosen=max(row[3],bound) if bound is not None else None
            chosen_bounds.append(chosen)
        maxima=tuple(max(row[j] for row in rows) for j in range(4))
        conditional=max(original_bounds) if all(v is not None for v in original_bounds) else None
        chosen=max(chosen_bounds) if all(v is not None for v in chosen_bounds) else None
        differences.append((label,ac.time,bc.time,maxima))
        gates.append(tuple(v<=limit for v,limit in zip(maxima,limits)))
        pressure.append(conditional);pgates.append(conditional<=limits[3] if conditional is not None else None)
        selected.append(chosen);selected_gates.append(chosen<=limits[3] if chosen is not None else None)
        cell_differences.append(tuple(rows))
        cell_gates.append(tuple(tuple(v<=limit for v,limit in zip(row,limits)) for row in rows))
        cell_pressure.append(tuple(original_bounds))
        cell_pgates.append(tuple(v<=limits[3] if v is not None else None for v in original_bounds))
        cell_selected.append(tuple(chosen_bounds))
        cell_selected_gates.append(tuple(v<=limits[3] if v is not None else None for v in chosen_bounds))
    balances=(_audit_path(a),_audit_path(b,(refinement.approach.trial,)))
    accepted=distance<=F(event.time_absolute_s) and all(all(row[:3]) for row in gates) and all(v is True for v in selected_gates)
    return SourceDryTransition(refinement,candidates,balances,distance,distance<=F(event.time_absolute_s),
        tuple(differences),tuple(gates),tuple(pressure),tuple(pgates),accepted,
        'conditional_numerical_event_accepted' if accepted else 'candidate_comparison_not_certified',
        shared_volume=shared_volume,shared_pressure_pairs=tuple(pairs),
        selected_pressure_bounds_pa=tuple(selected),selected_pressure_gates=tuple(selected_gates),
        pressure_strategy=('explicit_shared_source_wet_and_dry_volume' if shared_volume is not None
                           else 'explicit_shared_source_wet_volume') if wet_pressure_pairs
                          else 'explicit_shared_source_dry_volume' if shared_volume is not None
                          else 'original_independent_source_pressure',
        selected_cell_index=selected_cell,cell_endpoint_differences=tuple(cell_differences),
        cell_endpoint_gates=tuple(cell_gates),cell_conditional_pressure_bounds_pa=tuple(cell_pressure),
        cell_conditional_pressure_gates=tuple(cell_pgates),cell_selected_pressure_bounds_pa=tuple(cell_selected),
        cell_selected_pressure_gates=tuple(cell_selected_gates),wet_pressure_pairs=wet_pressure_pairs)

class SourceDryTransitionError(IntegrationError):
    def __init__(self,stage,refinement,candidates,cause,*,records=()):
        self.stage,self.refinement,self.candidates=stage,refinement,tuple(candidates)
        self.records=tuple(records)
        self.exception_type,self.exception_message=type(cause).__name__,str(cause)
        super().__init__(f'source_dry_transition_failed:{stage}:{type(cause).__name__}:{cause}')


def _check_shared_wet_volumes(refinement, shared_wet_volumes):
    _require(type(shared_wet_volumes) is tuple, 'explicit_source_shared_wet_volumes_required')
    if not shared_wet_volumes:
        return
    from .source_wet_shared_pressure import SourceSharedWetVolume
    column=refinement.approach.proposal.original_trial.adapter.column
    selected=refinement.approach.proposal.choice.selected_root.polynomial.cell
    _require(len(shared_wet_volumes)==column.cell_count and shared_wet_volumes[selected] is None
             and any(value is not None for value in shared_wet_volumes),
             'complete_source_shared_wet_cell_declarations_required')
    for i,declaration in enumerate(shared_wet_volumes):
        if declaration is not None:
            _require(type(declaration) is SourceSharedWetVolume,
                     'actual_source_shared_wet_volume_required')
            declaration.check()
            _require(declaration.storage is column.storages[i],
                     'source_shared_wet_volume_original_cell_required')


def evaluate_source_dry_transition(refinement, *, end: T, maximum_callbacks_per_path: int,
                                   cancel=None, shared_volume=None, shared_wet_volumes=()) -> SourceDryTransition:
    """Execute two actual wet/dry paths once; the caller owns outer study limits."""
    _require(type(refinement) is SourceRootRefinement, 'actual_source_root_refinement_required')
    refinement.check()
    _check_shared_volume(refinement,shared_volume)
    _require(refinement.clock is not None, 'source_dry_compared_prior_clock_required')
    _check_shared_wet_volumes(refinement,shared_wet_volumes)
    candidates=[];pressure_records=[];stage='coarse_candidate'
    try:
        for index,seed in enumerate((refinement.approach.proposal.original_trial,refinement.shifted_trial)):
            candidate=execute_source_dry_candidate(seed,event_policy=refinement.approach.proposal.event_policy,
                end=end,maximum_callbacks=maximum_callbacks_per_path,cancel=cancel,
                prior_clock=refinement.clock,root_index=index)
            candidates.append(candidate)
            _require(candidate.status=='executed_dry_candidate',candidate.status+':'+str(candidate.reason))
            stage='shifted_candidate'
        wet_pairs=()
        if shared_wet_volumes:
            from .source_wet_shared_pressure import collect_source_wet_pressure_pair
            grid=[]
            for phase_index in range(2):
                row=[]
                for cell,declaration in enumerate(shared_wet_volumes):
                    if declaration is None:
                        row.append(None)
                        continue
                    stage=f'wet_shared_pressure:{phase_index}:{cell}'
                    record={'phase_index':phase_index,'cell_index':cell}
                    pressure_records.append(record)
                    try:
                        _require(cancel is None or not cancel(), 'source_wet_pressure_collection_cancelled')
                        endpoints=tuple(c.cell_pressure_endpoints[phase_index][cell] for c in candidates)
                        pair=collect_source_wet_pressure_pair(*endpoints,shared_volume=declaration,cancel=cancel)
                        record['pair']=pair
                        row.append(pair)
                    except Exception as exc:
                        record.update(exception_type=type(exc).__name__,exception=str(exc),
                                      attempts=getattr(exc,'attempts',()))
                        raise
                grid.append(tuple(row))
            wet_pairs=tuple(grid)
        stage='source_event_comparison'
        result=compare_source_dry_candidates(refinement,tuple(candidates),shared_volume=shared_volume,
                                            wet_pressure_pairs=wet_pairs)
        result.check()
        return result
    except Exception as exc:
        raise SourceDryTransitionError(stage,refinement,candidates,exc,records=pressure_records) from exc
