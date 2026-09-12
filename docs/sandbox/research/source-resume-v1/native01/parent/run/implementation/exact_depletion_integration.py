"""Exact autonomous ordered packets; separate research core, no legacy resume codec."""
from dataclasses import dataclass, field, replace
from fractions import Fraction as F
from types import MappingProxyType
from collections.abc import Mapping
import math
import time
import numpy as np
from sludge_sandbox.integration import ConservedState, IntegrationPolicy, IntegrationError, DomainExit
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_integration import integrate_exact
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer
from sludge_sandbox.exact_terminal_executor import execute_exact_terminal
from sludge_sandbox.depletion_integration import DepletionPolicy
from sludge_sandbox.depletion_roundoff import DepletionRoundoffTotals
from sludge_sandbox.pressure_comparison import compare_pressure_pair, pressure_comparison_binding


class _Stop(IntegrationError):
    def __init__(self,status,reason):
        super().__init__(reason); self.status=status


def _immutable(value):
    if isinstance(value,Mapping):return MappingProxyType({k:_immutable(v) for k,v in value.items()})
    if isinstance(value,(list,tuple)):return tuple(_immutable(v) for v in value)
    return value


def _down(value):
    out=float(value)
    if not math.isfinite(out):raise IntegrationError('unrepresentable_duration')
    return math.nextafter(out,0.) if F(out)>value else out


@dataclass(frozen=True)
class ExactPacketFrame:
    terminal: object
    coarse_time: T | None = None
    previous_time: T | None = None
    common_time: T | None = None
    packet_maximum_differences: tuple = ()


@dataclass(frozen=True)
class ExactPacketRefinement:
    level: int
    role: str
    terminal_cap_s: F
    approach_cap_s: F
    safe_fraction: F
    common_time: T
    status: str
    path: object
    comparison: object = None
    costs: object = None


@dataclass(frozen=True)
class ExactPacketPath:
    times: tuple
    states: tuple
    steps: tuple
    frames: tuple
    operator: ExactFreeWaterTransfer
    totals: DepletionRoundoffTotals
    approach_grid: tuple


@dataclass(frozen=True)
class ExactDepletionResult:
    status: str
    reason: str | None
    times_s: tuple
    states: tuple
    steps: tuple
    packets: tuple
    operator: ExactFreeWaterTransfer
    roundoff_totals: DepletionRoundoffTotals
    refinements: tuple
    terminal_attempts: tuple
    costs: object
    elapsed_seconds: float
    initial_policy: IntegrationPolicy
    event_policy: DepletionPolicy
    schema: str = 'exact_ordered_packet_core_v1'
    approach_strategy: str = 'independent_halved_controls_no_spine_reuse'
    qualification: str = 'research_core_not_legacy_record_resume_or_material_admission'


@dataclass
class _Path:
    times: list
    states: list
    steps: list
    operator: ExactFreeWaterTransfer
    totals: DepletionRoundoffTotals
    frames: list = field(default_factory=list)
    grid: list = field(default_factory=list)
    def frozen(self):
        return ExactPacketPath(tuple(self.times),tuple(self.states),tuple(self.steps),tuple(self.frames),self.operator,self.totals,tuple(self.grid))


def integrate_exact_depletion(initial,operator,*,start,end,integration_policy,event_policy,cancel=None,continuation=None,on_commit=None):
    continuation_entry=time.monotonic() if continuation is not None else None
    p,ep=integration_policy,event_policy
    if type(initial) is not ConservedState or type(operator) is not ExactFreeWaterTransfer or type(p) is not IntegrationPolicy or type(ep) is not DepletionPolicy:
        raise IntegrationError('explicit_exact_packet_inputs_required')
    if type(start) is not T or type(end) is not T or not start<end:
        raise IntegrationError('exact_packet_times_required')
    if ep.terminal_method!='affine_midpoint' or ep.ordered_event_policy!='ordered_affine_packet_v1' or ep.nested_approach is None:
        raise IntegrationError('explicit_ordered_affine_nested_policy_required')
    if cancel is not None and not callable(cancel):raise IntegrationError('invalid_cancel_callback')
    if on_commit is not None and not callable(on_commit):raise IntegrationError('invalid_commit_observer')
    if ep.roundoff_policy.molar_mass_kg_mol!=operator.operator.chemical.reference.molar_mass_kg_mol:
        raise IntegrationError('roundoff_water_molar_mass_mismatch')
    energy=operator.energy_model_identity
    if initial.energy_model_identity!=energy:raise IntegrationError('original_energy_binding_required')
    if initial.mechanical_stretches is None:
        raise IntegrationError('exact_free_packet_mechanics_required')
    if initial.mechanical_stretches is not None and p.stretch_absolute_tolerance is None:
        raise IntegrationError('explicit_stretch_policy_required')
    if ep.pressure_comparison is not None:
        declared=pressure_comparison_binding(operator.operator)
        if len(ep.pressure_comparison.cell_boxes)!=len(initial.amounts_mol) or ep.pressure_comparison.to_record()['cell_boxes']!=declared['boxes']:
            raise IntegrationError('original_pressure_boxes_mismatch')
    begin=time.monotonic() if continuation_entry is None else continuation_entry;times=[start];states=[initial];steps=[];packets=[];refs=[];attempts=[]
    totals=DepletionRoundoffTotals(ep.roundoff_policy)
    costs={k:0 for k in ('evaluations_attempted','evaluations_completed','ordinary_trials','ordinary_rejected','ordinary_panels','predictor_attempts','terminal_attempts','terminal_panels','endpoint_attempts','endpoint_completed','stage_replans')}
    prior_elapsed=0.;parent_resource_reason=None
    if continuation is not None:
        from sludge_sandbox.exact_continuation_admission import admit
        parent,credit=admit(continuation,operator,initial,start,end,p,ep)
        times=list(parent.times_s);states=list(parent.states);steps=list(parent.steps);packets=list(parent.packets)
        refs=list(parent.refinements);attempts=list(parent.terminal_attempts)
        totals=parent.roundoff_totals;costs=dict(parent.costs);operator=parent.operator
        prior_elapsed=parent.elapsed_seconds
        if parent.status=='resource_limit':parent_resource_reason=parent.reason
    def elapsed():
        delta=time.monotonic()-begin
        if continuation is None:return delta
        exact=F(prior_elapsed)+F(delta);value=float(exact)
        return math.nextafter(value,math.inf) if F(value)<exact else value
    schema=[None if steps and steps[0].cell_work_components_j is None else (tuple(steps[0].cell_work_components_j) if steps else ...)]
    li=operator.operator.liquid_index
    def charged_panels():
        # Original ordered driver: accepted ordinary panels, interrupted replans,
        # and terminal attempts. Predictor/trial counts remain independent diagnostics.
        return costs['ordinary_panels']+costs['stage_replans']+costs['terminal_attempts']
    def guard():
        if cancel is not None and cancel():raise _Stop('cancelled','cancel_requested')
        if elapsed()>=p.maximum_wall_seconds:raise _Stop('resource_limit','wall_time_limit')
        if charged_panels()>=p.maximum_steps:
            raise _Stop('resource_limit','global_panel_limit')
        if costs['ordinary_rejected']>=p.maximum_rejections:raise _Stop('resource_limit','global_rejection_limit')
    def check(value,state):
        if state.energy_model_identity!=energy:raise IntegrationError('energy_binding_changed')
        value.rates.derivatives(state)
        keys=None if value.rates.cell_power_components_w is None else tuple(value.rates.cell_power_components_w)
        if schema[0] is ...:schema[0]=keys
        elif schema[0]!=keys:raise IntegrationError('component_schema_changed')
        return value
    def observe(view,state,t):
        guard();costs['evaluations_attempted']+=1
        out=view.evaluate(state,t);costs['evaluations_completed']+=1
        guard();return check(out,state)
    def choice(view,state,obs):
        options=[]
        for i,mode in enumerate(view.operator.interfaces):
            if mode!='existing_liquid':continue
            n=F(float(state.amounts_mol[i,li]));r=obs.rates
            rate=F(float(r.face_species_mol_s[i,li]))-F(float(r.face_species_mol_s[i+1,li]))+F(float(r.reaction_species_mol_s[i,li]))
            if n<=0:raise IntegrationError('wet_mode_zero_inventory')
            if rate<0:
                if obs.cell_transfers[i].rate_mol_s<=0:raise IntegrationError('non_evaporative_depletion_unsupported')
                options.append((n/-rate,i))
        return min(options) if options else None
    def remaining_policy(cap):
        guard();wall=_down(F(p.maximum_wall_seconds)-F(elapsed()))
        remaining=p.maximum_steps-charged_panels()
        nominal=_down(min(cap,F(p.maximum_step_s)))
        if wall<=0 or remaining<=0:raise _Stop('resource_limit','remaining_budget_exhausted')
        if nominal<p.minimum_step_s:raise _Stop('unsupported','event_step_below_configured_minimum')
        return replace(p,initial_step_s=nominal,maximum_step_s=nominal,maximum_steps=remaining,
            maximum_rejections=p.maximum_rejections-costs['ordinary_rejected'],maximum_wall_seconds=wall)
    def ordinary(path,finish,cap,preview=False):
        pending=[False];outer_stop=[None]
        def op(state,t):
            try:
                obs=observe(path.operator,state,t)
            except _Stop as exc:
                outer_stop[0]=exc
                raise
            c=choice(path.operator,state,obs) if preview else None
            if c is not None and t.shifted(c[0])<=finish:
                pending[0]=True;costs['stage_replans']+=1
                raise IntegrationError('packet_stage_replan')
            return obs.rates
        bounded=remaining_policy(cap)
        run=integrate_exact(path.states[-1],op,start_s=path.times[-1],end_s=finish,policy=bounded,cancel=cancel)
        costs['ordinary_trials']+=run.attempted_trials;costs['ordinary_rejected']+=run.rejected_trials;costs['ordinary_panels']+=len(run.steps)
        path.times.extend(run.times_s[1:]);path.states.extend(run.states[1:]);path.steps.extend(run.steps)
        if not path.frames:path.grid.extend(run.times_s[1:])
        if outer_stop[0] is not None:raise outer_stop[0]
        if pending[0]:return False
        if run.status!='completed':raise _Stop(run.status,run.reason)
        return True
    def terminal(path,common):
        guard()
        if p.maximum_steps-charged_panels()<1:
            raise _Stop('resource_limit','insufficient_terminal_panel_budget')
        # Callee cancellation also enforces the original outer wall deadline.
        def stopped():
            return (cancel is not None and cancel()) or elapsed()>=p.maximum_wall_seconds
        bounded=remaining_policy(F(p.maximum_step_s))
        attempt=execute_exact_terminal(path.states[-1],path.operator,start=path.times[-1],common_endpoint=common,
            integration_policy=bounded,event_policy=ep,totals=path.totals,cancel=stopped)
        attempts.append(attempt);c=attempt.costs
        costs['evaluations_attempted']+=c.evaluation_attempts;costs['evaluations_completed']+=c.evaluation_completed
        costs['predictor_attempts']+=c.predictor_panel_attempts;costs['terminal_attempts']+=c.terminal_panel_attempts;costs['terminal_panels']+=c.terminal_panels
        if attempt.status!='speculative_completed':
            status='resource_limit' if elapsed()>=p.maximum_wall_seconds else attempt.status
            raise _Stop(status,attempt.reason)
        for obs in attempt.observations:check(obs.evaluation,obs.state)
        path.steps.append(attempt.terminal_panel.ledger);path.times.append(attempt.terminal_panel.ledger.end_s)
        path.states.append(attempt.corrected_state);path.operator=attempt.candidate_operator;path.totals=attempt.candidate_totals
        path.frames.append(ExactPacketFrame(attempt))
    def proposal(view,state,t,common,cap,approach,safe,total):
        path=_Path([t],[state],[],view,total);force=False
        try:
            while path.times[-1]<common:
                guard();now=path.times[-1];obs=observe(path.operator,path.states[-1],now);c=choice(path.operator,path.states[-1],obs)
                if force and (c is None or now.shifted(c[0])>=common):
                    raise _Stop('unsupported','stage_replan_without_localizable_root')
                if c is not None and (force or c[0]<=cap) and now.shifted(c[0])<common:
                    terminal(path,common);force=False;continue
                duration=min(approach,common.elapsed_since(now),safe*c[0] if c else common.elapsed_since(now))
                finish=now.shifted(duration)
                if not ordinary(path,finish,approach,preview=True):force=True
            return path
        except (ValueError,TypeError,AttributeError,OverflowError) as exc:
            exc.exact_partial_path=path.frozen()
            raise
    def vectors(obs):
        base=obs.base_evaluation
        result=(tuple(s.mechanical.temperature_k for s in base.storage_states),tuple(i.temperature_error_bound_k for i in base.storage_inverses),
                tuple(s.mechanical.pressure_pa for s in base.storage_states),tuple(s.pressure_error_bound_pa for s in base.storage_states))
        if any(len(v)!=len(initial.amounts_mol) or any(type(x) is bool or not math.isfinite(x) for x in v) for v in result) or any(x<0 for v in (result[1],result[3]) for x in v):
            raise IntegrationError('complete_finite_observation_bounds_required')
        return result
    def diff(a,b):return float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
    def compare(a,b,common):
        if tuple(f.terminal.root_order.selected_cell for f in a.frames)!=tuple(f.terminal.root_order.selected_cell for f in b.frames) or a.operator.operator.interfaces!=b.operator.operator.interfaces or not a.frames:
            raise _Stop('unsupported','refinement_event_order_or_modes_changed')
        ca=observe(a.operator,a.states[-1],common);cb=observe(b.operator,b.states[-1],common)
        rows=[];maxima=[F(),0.,0.,0.,0.,0.]
        def before():guard();costs['endpoint_attempts']+=1
        def after(actual):costs['endpoint_completed']+=1;guard()
        for fa,fb in zip(a.frames,b.frames):
            ta,tb=fa.terminal,fb.terminal;ea,eb=ta.observations[-1],tb.observations[-1]
            ra=next(c.evidence for c in ta.root_order.candidates if c.cell_index==ta.root_order.selected_cell)
            rb=next(c.evidence for c in tb.root_order.candidates if c.cell_index==tb.root_order.selected_cell)
            def clock_error(evidence):
                # An exactly zero lower polynomial value proves the surrogate root itself.
                return F() if evidence.samples.inventory(evidence.lower.elapsed_since(evidence.samples.start))==0 else evidence.upper.elapsed_since(evidence.lower)
            dt=abs(ea.time.elapsed_since(eb.time))+clock_error(ra)+clock_error(rb)
            va,vb=vectors(ea.evaluation),vectors(eb.evaluation);vc,vd=vectors(ca),vectors(cb)
            temp=max(diff(va[0],vb[0])+max(va[1])+max(vb[1]),diff(vc[0],vd[0])+max(vc[1])+max(vd[1]))
            pressure=max(diff(va[2],vb[2])+max(va[3])+max(vb[3]),diff(vc[2],vd[2])+max(vc[3])+max(vd[3]))
            paired=[]
            if ep.pressure_comparison is not None:
                for viewa,sa,oa,viewb,sb,ob in ((ta.candidate_operator,ea.state,ea.evaluation,tb.candidate_operator,eb.state,eb.evaluation),(a.operator,a.states[-1],ca,b.operator,b.states[-1],cb)):
                    value=compare_pressure_pair(viewa.operator,sa,oa.base_evaluation.total_inverses,viewb.operator,sb,ob.base_evaluation.total_inverses,policy=ep.pressure_comparison,before_endpoint=before,after_endpoint=after)
                    paired.append(_immutable(value.to_record()))
            selected=max(v['bound_pa'] for v in paired) if paired else pressure
            row=(dt,max(diff(ea.state.amounts_mol,eb.state.amounts_mol),diff(a.states[-1].amounts_mol,b.states[-1].amounts_mol)),
                max(diff(ea.state.internal_energy_j,eb.state.internal_energy_j),diff(a.states[-1].internal_energy_j,b.states[-1].internal_energy_j)),temp,selected,
                max(diff(ea.state.mechanical_stretches,eb.state.mechanical_stretches),diff(a.states[-1].mechanical_stretches,b.states[-1].mechanical_stretches)))
            maxima=[max(x,y) for x,y in zip(maxima,row)]
            rows.append(MappingProxyType({'differences':row,'event_a':ea,'event_b':eb,'common_a':ca,'common_b':cb,'independent_pressure_bound_pa':pressure,'paired':tuple(paired),'common_state_a':a.states[-1],'common_state_b':b.states[-1],
                'event_amount_differences':tuple(tuple(float(v) for v in row) for row in np.abs(ea.state.amounts_mol-eb.state.amounts_mol)),
                'common_amount_differences':tuple(tuple(float(v) for v in row) for row in np.abs(a.states[-1].amounts_mol-b.states[-1].amounts_mol)),
                'event_energy_differences':tuple(map(float,np.abs(ea.state.internal_energy_j-eb.state.internal_energy_j))),
                'common_energy_differences':tuple(map(float,np.abs(a.states[-1].internal_energy_j-b.states[-1].internal_energy_j))),
                'event_stretch_differences':tuple(map(float,np.abs(ea.state.mechanical_stretches-eb.state.mechanical_stretches))),
                'common_stretch_differences':tuple(map(float,np.abs(a.states[-1].mechanical_stretches-b.states[-1].mechanical_stretches)))}))
        gates=(F(ep.time_absolute_s),ep.amount_absolute_mol,ep.energy_absolute_j,ep.temperature_absolute_k,ep.pressure_absolute_pa,p.stretch_absolute_tolerance)
        return all(math.isfinite(v) and v<=g for v,g in zip(maxima,gates)),tuple(maxima),tuple(rows)
    def audit_commit(path,*,allow_stopped_prefix=False):
        nonlocal operator,totals
        allsteps=steps+path.steps;allstates=states+path.states[1:]
        frames=[f for packet in packets for f in packet]+path.frames
        mapping={id(f.terminal.terminal_panel.ledger):f.terminal.correction for f in frames}
        if len(mapping)!=len(frames):raise IntegrationError('duplicate_terminal_panel')
        corrections=[f.terminal.correction for f in frames if f.terminal.correction is not None]
        expected_totals=DepletionRoundoffTotals(ep.roundoff_policy,
            sum((c.vapor_storage_roundoff_mol for c in corrections),F()),
            sum((abs(c.vapor_storage_roundoff_mol) for c in corrections),F()),
            sum((c.ideal_vapor_increment_mol for c in corrections),F()),len(corrections))
        if expected_totals!=path.totals:raise IntegrationError('original_correction_totals_mismatch')
        alltimes=times+path.times[1:]
        if len(allsteps)+1!=len(allstates) or len(alltimes)!=len(allstates):raise IntegrationError('complete_prefix_required')
        cn=[F() for _ in initial.amounts_mol.flat];cu=[F() for _ in initial.internal_energy_j];cs=[F() for _ in initial.mechanical_stretches];ce=cs.copy();cr=cs.copy();cp=cu.copy()
        for index,(step,state) in enumerate(zip(allsteps,allstates[1:])):
            before=allstates[index]
            if step.start_s!=alltimes[index] or step.end_s!=alltimes[index+1] or step.end_s<=step.start_s:
                raise IntegrationError('prefix_ledger_time_mismatch')
            if state.energy_model_identity!=energy:raise IntegrationError('prefix_energy_binding')
            c=mapping.get(id(step))
            for flat,idx in enumerate(np.ndindex(initial.amounts_mol.shape)):
                cn[flat]+=F(float(step.face_species_mol[idx]))-F(float(step.face_species_mol[idx[0]+1,idx[1]]))+F(float(step.reaction_species_mol[idx]))
                if c is not None:
                    if idx==(c.cell_index,c.liquid_index):cn[flat]+=c.ideal_liquid_increment_mol
                    if idx==(c.cell_index,c.vapor_index):cn[flat]+=c.ideal_vapor_increment_mol+c.vapor_storage_roundoff_mol
                if abs(F(float(state.amounts_mol[idx]))-F(float(initial.amounts_mol[idx]))-cn[flat])>F(p.amount_absolute_tolerance_mol):raise IntegrationError('original_amount_prefix_budget')
            for i in range(len(cu)):
                cu[i]+=F(float(step.face_energy_j[i]))-F(float(step.face_energy_j[i+1]))+F(float(step.cell_work_j[i]))
                if abs(F(float(state.internal_energy_j[i]))-F(float(initial.internal_energy_j[i]))-cu[i])>F(p.energy_absolute_tolerance_j):raise IntegrationError('original_energy_prefix_budget')
                if step.component_sum_residual_j is not None:cp[i]+=abs(step.component_sum_residual_j[i])
                if cp[i]>F(p.energy_absolute_tolerance_j):raise IntegrationError('original_component_prefix_budget')
            for i,(inc,q) in enumerate(zip(step.stretch_increment,step.stretch_quadrature_roundoff)):
                inc=F(float(inc));exact=inc-q;cs[i]+=inc;ce[i]+=exact;cr[i]+=abs(q)
                local=F(float(state.mechanical_stretches[i]))-F(float(before.mechanical_stretches[i]));change=F(float(state.mechanical_stretches[i]))-F(float(initial.mechanical_stretches[i]))
                if max(abs(local-inc),abs(local-exact),abs(change-cs[i]),abs(change-ce[i]),cr[i])>F(p.stretch_absolute_tolerance):raise IntegrationError('original_stretch_prefix_budget')
        if not allow_stopped_prefix:
            if cancel is not None and cancel():raise _Stop('cancelled','cancel_requested')
            if elapsed()>=p.maximum_wall_seconds:raise _Stop('resource_limit','wall_time_limit')
        path.operator.operator_identity
        times.extend(path.times[1:]);states.extend(path.states[1:]);steps.extend(path.steps)
        if path.frames:packets.append(tuple(path.frames))
        operator=path.operator;totals=path.totals
        if path.steps and on_commit is not None:
            try:on_commit((len(steps),len(packets),times[-1]))
            except Exception as exc:raise _Stop('failed','commit_observer_failed:'+type(exc).__name__+':'+str(exc)) from exc
    try:
        if parent_resource_reason is not None:raise _Stop('resource_limit',parent_resource_reason)
        while times[-1]<end:
            guard();t=times[-1];state=states[-1];obs=observe(operator,state,t);c=choice(operator,state,obs)
            if c and c[0]<=F(ep.terminal_window_s) and abs(t.shifted(c[0]).elapsed_since(end))<=F(ep.time_absolute_s):
                raise _Stop('unsupported','event_node_order_not_separated')
            if c and c[0]<=F(ep.terminal_window_s) and t.shifted(c[0])<=end:
                common=min(end,t.shifted(max(F(ep.common_time_horizon_s),2*F(ep.terminal_window_s))))
                original=operator.operator_identity;previous=None;coarse=None;successes=0
                approach=min(F(ep.nested_approach.maximum_step_s),F(p.maximum_step_s));safe=F(ep.safe_inventory_fraction)
                for level in range(ep.maximum_refinements+1):
                    cap=min(F(ep.terminal_window_s),c[0])/2**level;costbefore=costs.copy();path=None;recorded=False
                    try:
                        path=proposal(operator,state,t,common,cap,approach,safe,totals)
                        if not path.frames:raise _Stop('unsupported','missing_packet_events')
                        if previous is None:
                            coarse=path;passed=False;values=();detail=None;status='coarse_reference'
                        else:
                            passed,values,detail=compare(previous,path,common);status='comparison_pass' if passed else 'comparison_fail';successes=successes+1 if passed else 0
                        refs.append(ExactPacketRefinement(level,'terminal',cap,approach,safe,common,status,path.frozen(),detail,MappingProxyType({k:costs[k]-costbefore[k] for k in costs})));recorded=True
                        if successes>=2:
                            guard()
                            if operator.operator_identity!=original:raise IntegrationError('root_source_changed')
                            fine=None;finebefore=costs.copy();fine_recorded=False
                            try:
                                fine=proposal(operator,state,t,common,cap,approach/2,safe/2,totals)
                                if fine.grid==path.grid:raise _Stop('unsupported','independent_approach_grid_uninformative')
                                ok,fvalues,fdetail=compare(path,fine,common)
                                refs.append(ExactPacketRefinement(level,'independent',cap,approach/2,safe/2,common,'comparison_pass' if ok else 'comparison_fail',fine.frozen(),fdetail,MappingProxyType({k:costs[k]-finebefore[k] for k in costs})))
                                fine_recorded=True
                                if not ok:raise _Stop('unsupported','independent_approach_comparison_failed')
                            except (ValueError,TypeError,AttributeError,OverflowError) as exc:
                                if not fine_recorded:
                                    refs.append(ExactPacketRefinement(level,'independent',cap,approach/2,safe/2,common,str(exc),getattr(exc,'exact_partial_path',None) if fine is None else fine.frozen(),costs=MappingProxyType({k:costs[k]-finebefore[k] for k in costs})))
                                raise
                            maximum=tuple(max(x,y) for x,y in zip(values,fvalues))
                            path.frames=[replace(f,coarse_time=coarse.frames[i].terminal.observations[-1].time,previous_time=previous.frames[i].terminal.observations[-1].time,common_time=common,packet_maximum_differences=maximum) for i,f in enumerate(path.frames)]
                            if operator.operator_identity!=original:raise IntegrationError('root_source_changed')
                            audit_commit(path);break
                        previous=path
                    except (ValueError,TypeError,AttributeError,OverflowError) as exc:
                        if not recorded:
                            refs.append(ExactPacketRefinement(level,'failed_attempt',cap,approach,safe,common,str(exc),getattr(exc,'exact_partial_path',None) if path is None else path.frozen(),costs=MappingProxyType({k:costs[k]-costbefore[k] for k in costs})))
                        raise
                else:raise _Stop('unsupported','event_refinement_limit')
            else:
                path=_Path([t],[state],[],operator,totals)
                duration=min(F(p.maximum_step_s),end.elapsed_since(t),F(ep.safe_inventory_fraction)*c[0] if c else end.elapsed_since(t))
                try:ordinary(path,t.shifted(duration),F(p.maximum_step_s))
                except _Stop:
                    audit_commit(path,allow_stopped_prefix=True);raise
                audit_commit(path)
        status='completed';reason=None
    except (ValueError,TypeError,AttributeError,OverflowError) as exc:
        status=exc.status if isinstance(exc,_Stop) else ('domain_exit' if isinstance(exc,DomainExit) else 'failed');reason=str(exc)
    return ExactDepletionResult(status,reason,tuple(times),tuple(states),tuple(steps),tuple(packets),operator,totals,tuple(refs),tuple(attempts),MappingProxyType(costs.copy()),elapsed(),p,ep)
