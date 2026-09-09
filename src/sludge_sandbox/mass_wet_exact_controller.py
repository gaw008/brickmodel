"""Unit-separated autonomous exact wet-to-dry packet research controller."""
from dataclasses import dataclass, replace
from fractions import Fraction as F
import time
from sludge_sandbox.mass_storage_bridge import require
from sludge_sandbox.mass_wet_transport import WetPair
from sludge_sandbox.mass_wet_exact_stage import (
    MixedStagePolicy, ManufacturedConstantLiquidFixture, Sample,
    try_step_doubling, pressure_radius, inventory_derivatives, initial_value,
)
from sludge_sandbox.mass_wet_exact_terminal import prepare_mixed_terminal, source_labels
from sludge_sandbox.mass_wet_writeback import MixedWritebackContext, MixedWritebackTotals
from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.integration import DomainExit


@dataclass(frozen=True)
class MixedControllerPolicy:
    approach_cap_s: F
    safe_inventory_fraction: F
    terminal_window_s: F
    maximum_refinements: int
    maximum_evaluations: int
    maximum_panel_attempts: int
    maximum_wall_seconds: float

    def __post_init__(self):
        for value in (self.approach_cap_s,self.safe_inventory_fraction,self.terminal_window_s):
            require(type(value) is F and value>0,'exact_positive_controller_control')
        require(self.safe_inventory_fraction<1,'strict_safe_inventory_fraction')
        for value in (self.maximum_refinements,self.maximum_evaluations,self.maximum_panel_attempts):
            require(type(value) is int and value>=0,'integer_cumulative_budget')
        require(self.maximum_refinements>=2,'two_successive_comparisons_required')
        require(type(self.maximum_wall_seconds) is float and 0<self.maximum_wall_seconds<float('inf'),'finite_positive_wall_budget')


@dataclass(frozen=True)
class MixedEventFrame:
    step_index: int
    terminal: object
    time: T
    state: tuple
    observation: Sample | None
    old_binding: str
    new_binding: str
    modes_before: tuple
    modes_after: tuple
    operator: WetPair


@dataclass(frozen=True)
class ObservationAttempt:
    branch_index: int
    role: str
    time: T
    states: tuple
    binding: str
    modes: tuple
    status: str
    sample: Sample | None = None
    reason: str | None = None


@dataclass(frozen=True)
class MixedPath:
    status: str
    reason: str | None
    times: tuple
    states: tuple
    steps: tuple
    frames: tuple
    operator: WetPair
    totals: MixedWritebackTotals
    approach_grid: tuple
    attempts: tuple
    final_observation: Sample | None


@dataclass(frozen=True)
class MixedRefinement:
    level: int
    role: str
    terminal_window_s: F
    approach_cap_s: F
    safe_fraction: F
    status: str
    path: MixedPath
    comparison: tuple
    costs: tuple


@dataclass(frozen=True)
class MixedControllerResult:
    status: str
    reason: str | None
    times: tuple
    states: tuple
    steps: tuple
    packets: tuple
    operator: WetPair
    roundoff_totals: MixedWritebackTotals
    refinements: tuple
    observation_journal: tuple
    costs: tuple
    elapsed_seconds: float
    original_initial: tuple
    original_start: T
    original_end: T
    stage_policy: MixedStagePolicy
    roundoff_policy: DepletionRoundoffPolicy
    original_liquid_fraction_limit: F
    controller_policy: MixedControllerPolicy
    qualification: str='autonomous_research_single_atomic_packet_no_native_wet_certificate_no_codec_service_or_resume'


class Stop(ValueError):
    def __init__(self,status,reason):
        super().__init__(reason);self.status=status


def integrate_mixed_exact(pair: WetPair, initial: tuple, *, start: T, end: T,
        stage_policy: MixedStagePolicy, roundoff_policy: DepletionRoundoffPolicy,
        original_liquid_fraction_limit: F, controller_policy: MixedControllerPolicy,
        constant_liquid_fixture: ManufacturedConstantLiquidFixture | None=None,
        cancel=None) -> MixedControllerResult:
    require(type(pair) is WetPair and type(initial) is tuple and len(initial)==2,'typed_original_mixed_host_state')
    require(type(start) is T and type(end) is T and start<end,'original_exact_interval')
    require(type(stage_policy) is MixedStagePolicy and type(roundoff_policy) is DepletionRoundoffPolicy and type(controller_policy) is MixedControllerPolicy,'explicit_original_policies')
    controller_policy.__post_init__();stage_policy.__post_init__()
    cp=controller_policy;sp=stage_policy
    require(cp.approach_cap_s<=F(sp.maximum_step_s),'approach_within_original_step_domain')
    original_binding=pair.binding()
    context=MixedWritebackContext(initial,start,original_binding,source_labels(pair),pair.storages[0].water.reference.molar_mass_kg_mol,roundoff_policy,original_liquid_fraction_limit)
    empty=MixedWritebackTotals.empty(context)
    original_digest=_digest((initial,start,end,sp,roundoff_policy,original_liquid_fraction_limit,cp,context))
    begun=time.monotonic();refs=[];accepted=None;observation_journal=[]
    costs={k:0 for k in ('evaluations_attempted','evaluations_completed','ordinary_trials','ordinary_rejected','terminal_attempts','panel_attempts','observation_attempts','observation_completed')}

    def elapsed():return time.monotonic()-begun
    def guard():
        require(pair.binding()==original_binding and _digest((initial,start,end,sp,roundoff_policy,original_liquid_fraction_limit,cp,context))==original_digest,'original_binding_or_policy_changed')
        if constant_liquid_fixture is not None:constant_liquid_fixture.check(pair)
        if cancel is not None and cancel():raise Stop('cancelled','cancel_requested')
        if elapsed()>=cp.maximum_wall_seconds:raise Stop('resource_limit','original_cumulative_wall_budget')
        if costs['evaluations_attempted']>cp.maximum_evaluations or costs['panel_attempts']>cp.maximum_panel_attempts:raise Stop('resource_limit','original_cumulative_work_budget')
    def remaining_wall():
        guard();return max(0.,cp.maximum_wall_seconds-elapsed())
    def fixture_for(op):
        if constant_liquid_fixture is None:return None
        require(op.storages==pair.storages and op.face==pair.face and op.rate_constants_per_s==pair.rate_constants_per_s and op.transfer_coefficients_mol_s_pa==pair.transfer_coefficients_mol_s_pa,'mode_change_only_physics_binding')
        return ManufacturedConstantLiquidFixture.capture(op,volume_m3_mol=constant_liquid_fixture.volume_m3_mol)
    def observe(op,states,at,role):
        guard()
        if costs['evaluations_attempted']>=cp.maximum_evaluations:raise Stop('resource_limit','original_cumulative_evaluation_budget')
        before=op.binding();costs['evaluations_attempted']+=1;costs['observation_attempts']+=1
        entry=ObservationAttempt(len(refs),role,at,states,before,op.interfaces,'attempted')
        observation_journal.append(entry);index=len(observation_journal)-1
        try:r=op.evaluate(states)
        except (ValueError,OverflowError) as exc:
            status='domain_exit' if isinstance(exc,DomainExit) else 'failed'
            observation_journal[index]=replace(entry,status=status,reason=str(exc))
            raise Stop(status,str(exc)) from exc
        costs['evaluations_completed']+=1;costs['observation_completed']+=1
        sample=Sample(role,at,states,r,before,op.interfaces)
        observation_journal[index]=replace(entry,status='completed',sample=sample)
        require(op.binding()==before,'observed_mode_host_changed');guard()
        return sample

    def account(result):
        costs['evaluations_attempted']+=result.evaluations_attempted
        costs['evaluations_completed']+=result.evaluations_completed
        guard()
    def reserve_panels(n):
        guard()
        if costs['panel_attempts']+n>cp.maximum_panel_attempts:raise Stop('resource_limit','original_cumulative_panel_budget')
        costs['panel_attempts']+=n

    def proposal(window,cap,safe):
        op=pair;ctx=context;total=empty;times=[start];states=[initial];steps=[];frames=[];grid=[];attempts=[];last=None
        status='completed';reason=None
        try:
            while times[-1]<end:
                guard();now=times[-1];state=states[-1]
                obs=observe(op,state,now,'approach_observation');last=obs
                positive=[F(s.liquid_water_mol)/F(c.phase_water_mol_s) for s,c,m in zip(state,obs.rates.cells,op.interfaces) if m=='existing_liquid' and c.phase_water_mol_s>0]
                tau=min(positive) if positive else None
                if tau is not None and tau<=window and now.shifted(tau)<end:
                    reserve_panels(1);costs['terminal_attempts']+=1
                    terminal=prepare_mixed_terminal(op,state,start=now,upper=end,context=ctx,totals=total,time_absolute_s=sp.time_absolute_s,
                        maximum_evaluations=min(2,max(0,cp.maximum_evaluations-costs['evaluations_attempted'])),maximum_wall_seconds=remaining_wall(),cancel=cancel)
                    attempts.append(('terminal',terminal));account(terminal)
                    if terminal.status!='prepared':raise Stop(terminal.status,terminal.reason)
                    old=op;projected=terminal.projection;chosen=terminal.root_order.selected_cell
                    op=op.with_depleted_cells(projected.states,(chosen,))
                    # Only mode binding changes. Original initial inventory/time,
                    # all original policies and every correction accumulator stay.
                    newctx=replace(ctx,operator_identity=op.binding(),source_ids=source_labels(op))
                    total=MixedWritebackTotals(newctx,projected.totals.per_cell);ctx=newctx
                    t=terminal.ledger.end
                    steps.append(terminal.ledger);times.append(t);states.append(projected.states)
                    frame=MixedEventFrame(len(steps)-1,terminal,t,projected.states,None,old.binding(),op.binding(),old.interfaces,op.interfaces,op)
                    frames.append(frame)
                    endpoint=observe(op,projected.states,t,'event_endpoint');last=endpoint
                    frames[-1]=replace(frame,observation=endpoint)
                    continue
                duration=min(cap,end.elapsed_since(now),safe*tau if tau is not None else end.elapsed_since(now))
                # Avoid a representable cap leaving an inadmissible final tail.
                remainder=end.elapsed_since(now)-duration
                if 0<remainder<2*F(sp.minimum_step_s):duration=end.elapsed_since(now)/2
                while True:
                    reserve_panels(3);costs['ordinary_trials']+=1
                    policy=replace(sp,maximum_evaluations=min(sp.maximum_evaluations,max(0,cp.maximum_evaluations-costs['evaluations_attempted'])),maximum_wall_seconds=min(sp.maximum_wall_seconds,remaining_wall()))
                    trial=try_step_doubling(op,state,start=now,end=now.shifted(duration),policy=policy,constant_liquid_fixture=fixture_for(op),cancel=cancel)
                    attempts.append(('ordinary',trial));account(trial)
                    if trial.status=='rejected':
                        costs['ordinary_rejected']+=1;duration/=2
                        if duration/2<F(sp.minimum_step_s):raise Stop('failed','ordinary_error_at_original_minimum_step')
                        continue
                    if trial.status!='accepted':raise Stop(trial.status,trial.reason)
                    for half in trial.steps[1:]:
                        steps.append(half.ledger);times.append(half.end);states.append(half.endpoint_state)
                        if not frames:grid.append(half.end)
                    last=trial.steps[-1].endpoint_sample
                    break
            last=observe(op,states[-1],end,'common_endpoint')
            audit_prefix(MixedPath('completed',None,tuple(times),tuple(states),tuple(steps),tuple(frames),op,total,tuple(grid),tuple(attempts),last),initial,sp)
        except Stop as exc:status=exc.status;reason=str(exc)
        except DomainExit as exc:status='domain_exit';reason=str(exc)
        except (ValueError,OverflowError) as exc:status='failed';reason=str(exc)
        return MixedPath(status,reason,tuple(times),tuple(states),tuple(steps),tuple(frames),op,total,tuple(grid),tuple(attempts),last)

    def differences(a,b,op_a,op_b,obs_a,obs_b,ta,tb,width_a=F(),width_b=F()):
        mass=max(abs(F(x)-F(y)) for s,t in zip(a,b) for x,y in zip(s.solid_mass_kg,t.solid_mass_kg))
        mol=max(abs(F(x)-F(y)) for s,t in zip(a,b) for x,y in zip((s.liquid_water_mol,*s.gas_amounts_mol),(t.liquid_water_mol,*t.gas_amounts_mol)))
        energy=max(abs(F(s.internal_energy_j)-F(t.internal_energy_j)) for s,t in zip(a,b))
        temp=F();pressure=F()
        for i,(ca,cb) in enumerate(zip(obs_a.rates.cells,obs_b.rates.cells)):
            va,vb=ca.inverse,cb.inverse
            temp=max(temp,abs(F(va.point.temperature_k)-F(vb.point.temperature_k))+F(va.temperature_error_bound_k)+F(vb.temperature_error_bound_k))
            pressure=max(pressure,abs(F(va.point.pressure_pa)-F(vb.point.pressure_pa))+pressure_radius(op_a,a[i],va,i,fixture_for(op_a))+pressure_radius(op_b,b[i],vb,i,fixture_for(op_b)))
        return mass,mol,energy,temp,pressure,abs(ta.elapsed_since(tb))+width_a+width_b
    def compare(a,b):
        require(a.status==b.status=='completed','completed_comparison_paths')
        require(tuple(f.terminal.root_order.selected_cell for f in a.frames)==tuple(f.terminal.root_order.selected_cell for f in b.frames) and a.operator.interfaces==b.operator.interfaces and a.frames,'matching_complete_event_sequence')
        rows=[]
        for fa,fb in zip(a.frames,b.frames):
            require(fa.modes_before==fb.modes_before and fa.modes_after==fb.modes_after,'per_event_mode_alignment')
            ea,eb=fa.terminal.evidence.clock,fb.terminal.evidence.clock
            values=differences(fa.state,fb.state,fa.operator,fb.operator,fa.observation,fb.observation,fa.time,fb.time,ea.upper.elapsed_since(ea.lower),eb.upper.elapsed_since(eb.lower))
            rows.append(('event',fa.terminal.root_order.selected_cell,values))
        rows.append(('common',None,differences(a.states[-1],b.states[-1],a.operator,b.operator,a.final_observation,b.final_observation,a.times[-1],b.times[-1])))
        bounds=tuple(map(F,(sp.solid_mass_absolute_kg,sp.amount_absolute_mol,sp.energy_absolute_j,sp.temperature_absolute_k,sp.pressure_absolute_pa,sp.time_absolute_s)))
        return all(all(v<=bound for v,bound in zip(row[2],bounds)) for row in rows),tuple(rows)

    status='failed';reason='no_accepted_packet';previous=None;passes=0
    try:
        guard()
        for level in range(cp.maximum_refinements+1):
            window=cp.terminal_window_s/2**level;before=costs.copy()
            path=proposal(window,cp.approach_cap_s,cp.safe_inventory_fraction)
            if path.status!='completed':
                refs.append(MixedRefinement(level,'terminal',window,cp.approach_cap_s,cp.safe_inventory_fraction,path.status,path,(),tuple((k,costs[k]-before[k]) for k in costs)))
                raise Stop(path.status,path.reason)
            try:
                ok,comparison=(False,()) if previous is None else compare(previous,path)
            except (ValueError,OverflowError) as exc:
                refs.append(MixedRefinement(level,'terminal',window,cp.approach_cap_s,cp.safe_inventory_fraction,'comparison_error:'+str(exc),path,(),tuple((k,costs[k]-before[k]) for k in costs)))
                raise
            label='coarse_reference' if previous is None else 'comparison_pass' if ok else 'comparison_fail'
            refs.append(MixedRefinement(level,'terminal',window,cp.approach_cap_s,cp.safe_inventory_fraction,label,path,comparison,tuple((k,costs[k]-before[k]) for k in costs)))
            passes=passes+1 if ok else 0
            if passes>=2:
                before=costs.copy();fine=proposal(window,cp.approach_cap_s/2,cp.safe_inventory_fraction/2)
                detail=();ok=False
                try:
                    if fine.status!='completed':raise Stop(fine.status,fine.reason)
                    require(path.approach_grid and fine.approach_grid and path.approach_grid!=fine.approach_grid,'independent_pre_first_approach_grid_uninformative')
                    ok,detail=compare(path,fine)
                finally:
                    refs.append(MixedRefinement(level,'independent',window,cp.approach_cap_s/2,cp.safe_inventory_fraction/2,'comparison_pass' if ok else 'comparison_fail',fine,detail,tuple((k,costs[k]-before[k]) for k in costs)))
                if not ok:raise Stop('failed','independent_approach_comparison_failed')
                audit_prefix(path,initial,sp)
                guard();accepted=path;status='completed';reason=None;break
            previous=path
        else:raise Stop('failed','original_refinement_budget_exhausted')
    except Stop as exc:status=exc.status;reason=str(exc)
    except (ValueError,OverflowError) as exc:status='failed';reason=str(exc)
    return MixedControllerResult(status,reason,accepted.times if accepted else (start,),accepted.states if accepted else (initial,),accepted.steps if accepted else (), (accepted.frames,) if accepted else (),accepted.operator if accepted else pair,accepted.totals if accepted else empty,tuple(refs),tuple(observation_journal),tuple(costs.items()),elapsed(),initial,start,end,sp,roundoff_policy,original_liquid_fraction_limit,cp)


def audit_prefix(path: MixedPath, initial: tuple, policy: MixedStagePolicy) -> None:
    """Original-initial exact and represented inventory/U prefix accounting."""
    require(len(path.times)==len(path.states)==len(path.steps)+1 and path.states[0]==initial,'complete_original_prefix_layout')
    frame_by_step={f.step_index:f for f in path.frames}
    correction_records=[]
    require(len(frame_by_step)==len(path.frames),'unique_terminal_step_binding')
    sums={};exact_sums={};abs_roundoff={};energy=[F(),F()];exact_energy=[F(),F()];energy_roundoff=[F(),F()];components=[F(),F()]
    for index,(before,after,ledger) in enumerate(zip(path.states,path.states[1:],path.steps)):
        require(ledger.start==path.times[index] and ledger.end==path.times[index+1] and ledger.start<ledger.end,'exact_prefix_time_binding')
        values=inventory_derivatives(tuple((k,F(v)) for k,v in ledger.represented_integrals));true=inventory_derivatives(ledger.exact_integrals)
        correction=frame_by_step.get(index);record=correction.terminal.projection.record if correction else None
        if correction:
            require(correction.terminal.ledger is ledger and correction.state==after and correction.terminal.projection.states==after and correction.time==ledger.end,'unique_actual_terminal_projection_binding')
            if record:correction_records.append((correction.terminal.root_order.selected_cell,record))
        for (key,inc),(_,ex) in zip(values,true):
            inc=F(inc);ex=F(ex)
            if record and key[1]==correction.terminal.root_order.selected_cell:
                if key[0]=='liquid':inc+=record.ideal_liquid_increment_mol;ex+=record.ideal_liquid_increment_mol
                if key[0]=='gas' and key[2]==2:inc+=record.actual_vapor_increment_mol;ex+=record.ideal_vapor_increment_mol
            sums[key]=sums.get(key,F())+inc;exact_sums[key]=exact_sums.get(key,F())+ex
            abs_roundoff[key]=abs_roundoff.get(key,F())+abs(inc-ex)
            bound=F(policy.solid_mass_absolute_kg if key[0]=='solid' else policy.amount_absolute_mol)
            local=initial_value(after,key)-initial_value(before,key);change=initial_value(after,key)-initial_value(initial,key)
            require(max(abs(local-inc),abs(local-ex),abs(change-sums[key]),abs(change-exact_sums[key]),abs_roundoff[key])<=bound,'original_unit_specific_prefix_budget')
        rep=dict(ledger.represented_integrals);ex=dict(ledger.exact_integrals)
        component_error=F(rep['face_energy',])-F(rep['heat',])-sum((F(rep['diffusion_energy',j])+F(rep['advection_energy',j]) for j in range(3)),F())
        for i,sign in enumerate((-1,1)):
            inc=sign*F(rep['face_energy',]);true=sign*ex['face_energy',]
            energy[i]+=inc;exact_energy[i]+=true;energy_roundoff[i]+=abs(inc-true);components[i]+=abs(component_error)
            local=F(after[i].internal_energy_j)-F(before[i].internal_energy_j);change=F(after[i].internal_energy_j)-F(initial[i].internal_energy_j)
            require(max(abs(local-inc),abs(local-true),abs(change-energy[i]),abs(change-exact_energy[i]),energy_roundoff[i],components[i])<=F(policy.energy_absolute_j),'original_energy_component_prefix_budget')

    # Recompute correction totals from this path's actual event records. Modes
    # may change the context identity, never the original states or budgets.
    require(path.totals.context.original_states==initial,'original_correction_context_states')
    for i,total in enumerate(path.totals.per_cell):
        records=[r for cell,r in correction_records if cell==i]
        require(total.signed_storage_roundoff_mol==sum((r.vapor_storage_roundoff_mol for r in records),F()) and total.absolute_storage_roundoff_mol==sum((abs(r.vapor_storage_roundoff_mol) for r in records),F()) and total.numerical_phase_correction_mol==sum((r.ideal_vapor_increment_mol for r in records),F()) and total.events==len(records),'once_only_original_correction_totals')
