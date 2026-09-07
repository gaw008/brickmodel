"""Bounded wet-to-dry event integration, with explicit terminal-panel accounting."""
from dataclasses import dataclass,replace
from fractions import Fraction
import math
import time
import numpy as np
from .integration import ConservedState,Rates,StepLedger,IntegrationPolicy,IntegrationError,DomainExit,integrate
from .depletion_roundoff import (DepletionRoundoffPolicy,DepletionRoundoffTotals,
    DepletionRoundoffError,DepletionClockEvidence,depletion_writeback)


class DepletionIntegrationError(IntegrationError):pass


def _number(v,positive=False):
    if type(v) not in (int,float) or not math.isfinite(v) or (positive and v<=0):
        raise DepletionIntegrationError('finite_depletion_policy_required')
    return float(v)


@dataclass(frozen=True,kw_only=True)
class DepletionPolicy:
    time_absolute_s: float
    amount_absolute_mol: float
    energy_absolute_j: float
    temperature_absolute_k: float
    pressure_absolute_pa: float
    terminal_window_s: float
    maximum_refinements: int
    roundoff_policy: DepletionRoundoffPolicy
    common_time_horizon_s: float = .01

    def __post_init__(self):
        for n in ('time_absolute_s','amount_absolute_mol','energy_absolute_j','temperature_absolute_k',
                  'pressure_absolute_pa','terminal_window_s','common_time_horizon_s'):
            _number(getattr(self,n),True)
        if type(self.maximum_refinements) is not int or self.maximum_refinements<2:
            raise DepletionIntegrationError('at_least_two_refinements_required')
        if type(self.roundoff_policy) is not DepletionRoundoffPolicy:
            raise DepletionIntegrationError('explicit_roundoff_policy_required')


@dataclass(frozen=True)
class DepletionEvaluation:
    rates: Rates
    evaporation_mol_s: tuple
    temperatures_k: tuple
    temperature_errors_k: tuple
    pressures_pa: tuple
    pressure_errors_pa: tuple


@dataclass(frozen=True,kw_only=True)
class ManufacturedDepletionAdapter:
    """Explicit numerical-oracle protocol; not a substitute material provider."""
    evaluate_callback: object
    liquid_index: int
    water_vapor_index: int
    interfaces: tuple
    program_knots_s: tuple
    source_ids: tuple
    classification: str = 'manufactured_numerical_oracle_not_material'

    def __post_init__(self):
        if (not callable(self.evaluate_callback) or type(self.liquid_index) is not int
                or type(self.water_vapor_index) is not int or min(self.liquid_index,self.water_vapor_index)<0
                or self.liquid_index==self.water_vapor_index or not self.interfaces
                or any(m not in ('existing_liquid','depleted_no_nucleation') for m in self.interfaces)
                or not self.source_ids or any(not isinstance(v,str) or not v.strip() for v in self.source_ids)
                or self.classification!='manufactured_numerical_oracle_not_material'):raise DepletionIntegrationError('explicit_manufactured_adapter_required')
        for name in ('interfaces','program_knots_s','source_ids'):object.__setattr__(self,name,tuple(getattr(self,name)))
        if any(not math.isfinite(v) for v in self.program_knots_s) or tuple(sorted(set(self.program_knots_s)))!=self.program_knots_s:
            raise DepletionIntegrationError('invalid_program_knots')

    def evaluate(self,state,t):return self.evaluate_callback(state,t,self.interfaces)
    def __call__(self,state,t):return self.evaluate(state,t).rates
    def breakpoints_s(self,start,end):return tuple(v for v in self.program_knots_s if start<v<end)
    def with_depleted_cells(self,state,cells):
        modes=list(self.interfaces)
        for i in cells:
            if state.amounts_mol[i,self.liquid_index]!=0:raise DepletionIntegrationError('depleted_cell_must_be_zero')
            modes[i]='depleted_no_nucleation'
        return replace(self,interfaces=tuple(modes))


@dataclass(frozen=True)
class DepletionEvent:
    cell_index: int
    time_s: float
    coarse_time_s: float
    previous_time_s: float
    common_time_s: float
    event_time_difference_s: float
    common_amount_difference_mol: float
    common_energy_difference_j: float
    common_temperature_difference_k: float
    common_pressure_difference_pa: float
    terminal_panel: StepLedger
    correction: object
    event_time_rounding_s: Fraction
    positive_evaporated_mol: float
    qualification: str = 'existing_interface_evaporation_depletion_refinement_indicator_not_ode_certificate'


@dataclass(frozen=True)
class DepletionRefinement:
    start_s: float
    level: int
    terminal_cap_s: float
    common_time_s: float
    event_time_s: float | None
    differences: tuple | None
    status: str
    evaluations: int
    elapsed_seconds: float


@dataclass(frozen=True)
class DepletionResult:
    status: str
    reason: str | None
    times_s: tuple
    states: tuple
    steps: tuple
    events: tuple
    corrections: tuple
    operator: object
    roundoff_totals: DepletionRoundoffTotals
    cumulative_amounts_mol: tuple
    cumulative_energy_j: tuple
    evaluations: int
    rejected_trials: int
    attempted_steps: int
    elapsed_seconds: float
    refinements: tuple = ()

    @property
    def accepted_trial_panels(self):
        """Accepted ordinary/terminal panels, including discarded refinement paths."""
        return self.attempted_steps


class _Failure(Exception):
    def __init__(self,status,reason):self.status=status;self.reason=reason


@dataclass
class _Path:
    times: list
    states: list
    steps: list
    op: object
    totals: DepletionRoundoffTotals
    event: object = None
    event_state: object = None
    event_observation: object = None


def integrate_depletion(initial,operator,*,start_s,end_s,integration_policy,event_policy,cancel=None):
    from .water_phase_transfer import WaterPhaseTransfer
    if (type(initial) is not ConservedState or type(operator) not in (WaterPhaseTransfer,ManufacturedDepletionAdapter)
            or type(integration_policy) is not IntegrationPolicy or type(event_policy) is not DepletionPolicy
            or (cancel is not None and not callable(cancel))):
        raise DepletionIntegrationError('explicit_depletion_host_state_policies_required')
    start=_number(start_s);end=_number(end_s)
    if end<=start:raise DepletionIntegrationError('end_must_follow_start')
    if (len(operator.interfaces)!=initial.amounts_mol.shape[0]
            or max(operator.liquid_index,operator.water_vapor_index)>=initial.amounts_mol.shape[1]):
        raise DepletionIntegrationError('interface_inventory_shape_mismatch')
    if (type(operator) is WaterPhaseTransfer and
            event_policy.roundoff_policy.molar_mass_kg_mol!=operator.chemical.reference.molar_mass_kg_mol):
        raise DepletionIntegrationError('roundoff_water_molar_mass_mismatch')
    policy=integration_policy;ep=event_policy;begin=time.monotonic()
    times=[start];states=[initial];steps=[];events=[];corrections=[]
    totals=DepletionRoundoffTotals(ep.roundoff_policy)
    cumulative_n=[Fraction(0) for _ in initial.amounts_mol.flat]
    cumulative_u=[Fraction(0) for _ in initial.internal_energy_j.flat]
    evaluations=rejected=attempted=0
    refinements=[]

    def guard():
        if cancel is not None and cancel():raise _Failure('cancelled','cancel_requested')
        if time.monotonic()-begin>=policy.maximum_wall_seconds:raise _Failure('resource_limit','wall_time_limit')
        if attempted>=policy.maximum_steps:raise _Failure('resource_limit','global_accepted_trial_panel_limit')
        if rejected>=policy.maximum_rejections:raise _Failure('resource_limit','total_rejection_limit')

    def observe(op,state,t):
        nonlocal evaluations
        guard();evaluations+=1
        raw=op.evaluate(state,t)
        if type(op) is ManufacturedDepletionAdapter:
            if type(raw) is not DepletionEvaluation:raise DepletionIntegrationError('oracle_evaluation_type')
            result=raw
        else:
            base=raw.base_evaluation
            result=DepletionEvaluation(raw.rates,tuple(v.rate_mol_s for v in raw.cell_transfers),
                tuple(s.mechanical.temperature_k for s in base.storage_states),
                tuple(s.temperature_error_bound_k for s in base.storage_inverses),
                tuple(s.mechanical.pressure_pa for s in base.storage_states),
                tuple(s.pressure_error_bound_pa for s in base.storage_states))
        count=state.amounts_mol.shape[0]
        if type(result.rates) is not Rates:raise DepletionIntegrationError('explicit_rates_required')
        result.rates.derivatives(state)
        for seq in (result.evaporation_mol_s,result.temperatures_k,result.temperature_errors_k,result.pressures_pa,result.pressure_errors_pa):
            if len(seq)!=count or any(not math.isfinite(v) for v in seq):raise DepletionIntegrationError('finite_complete_observations_required')
        if any(v<0 for v in result.temperature_errors_k+result.pressure_errors_pa):raise DepletionIntegrationError('negative_observation_error')
        guard();return result

    def normal(op,state,t,finish,maxstep):
        nonlocal evaluations,rejected,attempted
        guard()
        if finish<=t:raise _Failure('unsupported','unresolvable_time_panel')
        if maxstep<policy.minimum_step_s:raise _Failure('resource_limit','event_step_below_configured_minimum')
        bounded_step=max(policy.minimum_step_s,min(maxstep,finish-t))
        p=replace(policy,initial_step_s=bounded_step,maximum_step_s=bounded_step,
            maximum_steps=max(1,policy.maximum_steps-attempted),
            maximum_rejections=max(1,policy.maximum_rejections-rejected),
            maximum_wall_seconds=max(1e-12,policy.maximum_wall_seconds-(time.monotonic()-begin)))
        run=integrate(state,op,start_s=t,end_s=finish,policy=p,cancel=cancel)
        evaluations+=run.evaluations;rejected+=run.rejected_trials;attempted+=len(run.steps)
        return run

    def extend(path,run):
        path.times.extend(run.times_s[1:]);path.states.extend(run.states[1:]);path.steps.extend(run.steps)
        if run.status!='completed':raise _Failure(run.status,run.reason)

    def candidate(op,state,obs):
        obs.rates.derivatives(state);options=[]
        for i,mode in enumerate(op.interfaces):
            n=float(state.amounts_mol[i,op.liquid_index]);li=op.liquid_index
            rate=(Fraction(float(obs.rates.face_species_mol_s[i,li]))
                  -Fraction(float(obs.rates.face_species_mol_s[i+1,li]))
                  +Fraction(float(obs.rates.reaction_species_mol_s[i,li])))
            if mode=='existing_liquid' and n>0 and rate<0:
                if obs.evaporation_mol_s[i]<=0:raise _Failure('unsupported','unsupported_non_evaporative_liquid_depletion')
                options.append((Fraction(n)/-rate,i))
        if not options:return None
        options.sort()
        if len(options)>1 and abs(options[1][0]-options[0][0])<=Fraction(ep.time_absolute_s):
            raise _Failure('unsupported','simultaneous_events_not_separated')
        return options[0]

    def terminal(path,obs,tau,cell):
        nonlocal attempted
        t=path.times[-1];state=path.states[-1];exact=Fraction(t)+tau;endpoint=float(exact)
        if Fraction(endpoint)>exact:endpoint=math.nextafter(endpoint,-math.inf)
        if endpoint<=t:raise _Failure('unsupported','unresolvable_event_time')
        interval=Fraction(endpoint)-Fraction(t)
        def integrated(values):
            out=np.empty_like(values)
            for idx in np.ndindex(values.shape):out[idx]=float(interval*Fraction(float(values[idx])))
            return out
        fields=[integrated(getattr(obs.rates,n)) for n in ('face_species_mol_s','face_energy_w','reaction_species_mol_s','cell_power_w')]
        fn,fu,rn,work=fields
        increments=(fn[:-1],-fn[1:],rn);powers=(fu[:-1],-fu[1:],work)
        def update(before,terms):
            out=np.empty_like(before)
            for idx in np.ndindex(before.shape):out[idx]=float(Fraction(float(before[idx]))+sum((Fraction(float(v[idx])) for v in terms),Fraction()))
            return out
        amounts=update(state.amounts_mol,increments);energy=update(state.internal_energy_j,powers)
        if np.any(amounts<0) or not np.all(np.isfinite(amounts)) or not np.all(np.isfinite(energy)):
            raise _Failure('unsupported','terminal_panel_invalid_other_inventory_or_energy')
        raw=ConservedState(amounts,energy);record=None
        evap=float(Fraction(float(obs.evaporation_mol_s[cell]))*interval)
        li=path.op.liquid_index;vi=path.op.water_vapor_index
        if raw.amounts_mol[cell,li]>0:
            raw,record,path.totals=depletion_writeback(raw,cell_index=cell,liquid_index=li,vapor_index=vi,
                panel_liquid_start_mol=float(state.amounts_mol[cell,li]),
                panel_liquid_terms_mol=tuple(float(v[cell,li]) for v in increments),positive_evaporated_mol=evap,
                policy=ep.roundoff_policy,totals=path.totals,
                clock_evidence=DepletionClockEvidence(t,endpoint,
                    (float(obs.rates.face_species_mol_s[cell,li]),-float(obs.rates.face_species_mol_s[cell+1,li]),
                     float(obs.rates.reaction_species_mol_s[cell,li])),ep.time_absolute_s))
        guard()
        panel=StepLedger(t,endpoint,*fields);attempted+=1
        path.op=path.op.with_depleted_cells(raw,(cell,))
        path.times.append(endpoint);path.states.append(raw);path.steps.append(panel)
        path.event_state=raw;path.event_observation=observe(path.op,raw,endpoint)
        path.event=DepletionEvent(cell,endpoint,endpoint,endpoint,endpoint,0.,0.,0.,0.,0.,panel,record,
            exact-Fraction(endpoint),evap)

    def proposal(op,state,t,tc,cap,total):
        path=_Path([t],[state],[],op,total)
        while path.times[-1]<tc:
            at=path.times[-1];current=path.states[-1];obs=observe(path.op,current,at)
            choice=candidate(path.op,current,obs)
            if choice is not None:
                tau,cell=choice
                if tau<=Fraction(cap) and Fraction(at)+tau<=Fraction(tc):
                    terminal(path,obs,tau,cell)
                    if path.times[-1]>=tc:raise _Failure('unsupported','no_common_post_event_time')
                    # Ordinary dry continuation must not conceal a second interface event.
                    if any(m=='existing_liquid' for m in path.op.interfaces):
                        # Other wet cells are allowed only when their locally proposed
                        # crossing lies beyond the common comparison horizon.
                        next_obs=observe(path.op,path.states[-1],path.times[-1]);other=candidate(path.op,path.states[-1],next_obs)
                        if other is not None and Fraction(path.times[-1])+other[0]<=Fraction(tc):
                            raise _Failure('unsupported','second_event_in_common_time_preview')
                    extend(path,normal(path.op,path.states[-1],path.times[-1],tc,policy.maximum_step_s))
                    return path
            desired=min(cap,tc-at,float(choice[0])/4 if choice else cap)
            finish=min(tc,at+desired)
            extend(path,normal(path.op,current,at,finish,cap))
        return path

    def comparison(a,b,tc):
        if a.event is None or b.event is None:raise _Failure('unsupported','event_node_order_not_separated')
        if a.event.cell_index!=b.event.cell_index:raise _Failure('unsupported','event_identity_not_separated')
        ao=observe(a.op,a.states[-1],tc);bo=observe(b.op,b.states[-1],tc)
        def delta(x,y):return float(np.max(np.abs(np.asarray(x)-np.asarray(y))))
        dn=max(delta(a.event_state.amounts_mol,b.event_state.amounts_mol),delta(a.states[-1].amounts_mol,b.states[-1].amounts_mol))
        du=max(delta(a.event_state.internal_energy_j,b.event_state.internal_energy_j),delta(a.states[-1].internal_energy_j,b.states[-1].internal_energy_j))
        dt=max(delta(ao.temperatures_k,bo.temperatures_k)+max(ao.temperature_errors_k)+max(bo.temperature_errors_k),
            delta(a.event_observation.temperatures_k,b.event_observation.temperatures_k)+max(a.event_observation.temperature_errors_k)+max(b.event_observation.temperature_errors_k))
        dp=max(delta(ao.pressures_pa,bo.pressures_pa)+max(ao.pressure_errors_pa)+max(bo.pressure_errors_pa),
            delta(a.event_observation.pressures_pa,b.event_observation.pressures_pa)+max(a.event_observation.pressure_errors_pa)+max(b.event_observation.pressure_errors_pa))
        dtime=abs(a.event.time_s-b.event.time_s)+float(a.event.event_time_rounding_s+b.event.event_time_rounding_s)
        passed=(dtime<=ep.time_absolute_s and dn<=ep.amount_absolute_mol and du<=ep.energy_absolute_j
                and dt<=ep.temperature_absolute_k and dp<=ep.pressure_absolute_pa)
        return passed,(dtime,dn,du,dt,dp)

    def commit(path):
        nonlocal cumulative_n,cumulative_u,totals,operator
        event=path.event
        cn=list(cumulative_n);cu=list(cumulative_u)
        for j,step in enumerate(path.steps):
            after=path.states[j+1]
            nterms=(step.face_species_mol[:-1],-step.face_species_mol[1:],step.reaction_species_mol)
            uterms=(step.face_energy_j[:-1],-step.face_energy_j[1:],step.cell_work_j)
            for flat,idx in enumerate(np.ndindex(initial.amounts_mol.shape)):
                cn[flat]+=sum((Fraction(float(v[idx])) for v in nterms),Fraction())
                if event is not None and step is event.terminal_panel and event.correction is not None:
                    c=event.correction
                    if idx==(c.cell_index,c.liquid_index):cn[flat]+=c.ideal_liquid_increment_mol
                    if idx==(c.cell_index,c.vapor_index):cn[flat]+=c.ideal_vapor_increment_mol+c.vapor_storage_roundoff_mol
                error=Fraction(float(after.amounts_mol[idx]))-Fraction(float(initial.amounts_mol[idx]))-cn[flat]
                if abs(error)>Fraction(policy.amount_absolute_tolerance_mol):raise _Failure('failed','cross_segment_amount_prefix_roundoff')
            for flat,idx in enumerate(np.ndindex(initial.internal_energy_j.shape)):
                cu[flat]+=sum((Fraction(float(v[idx])) for v in uterms),Fraction())
                error=Fraction(float(after.internal_energy_j[idx]))-Fraction(float(initial.internal_energy_j[idx]))-cu[flat]
                if abs(error)>Fraction(policy.energy_absolute_tolerance_j):raise _Failure('failed','cross_segment_energy_prefix_roundoff')
        # Validate the entire speculative path before any global state/mode/prefix mutation.
        cumulative_n=cn;cumulative_u=cu
        times.extend(path.times[1:]);states.extend(path.states[1:]);steps.extend(path.steps)
        operator=path.op;totals=path.totals
        if event is not None:
            events.append(event)
            if event.correction is not None:corrections.append(event.correction)

    status='completed';reason=None
    try:
        knots=tuple(operator.breakpoints_s(start,end))+(end,)
        for tb in knots:
            while times[-1]<tb:
                guard();t=times[-1];state=states[-1];obs=observe(operator,state,t);choice=candidate(operator,state,obs)
                if (choice is not None and choice[0]<=Fraction(ep.terminal_window_s)
                        and abs(Fraction(t)+choice[0]-Fraction(tb))<=Fraction(ep.time_absolute_s)):
                    raise _Failure('unsupported','event_node_order_not_separated')
                if choice is not None and choice[0]<=Fraction(ep.terminal_window_s) and Fraction(t)+choice[0]<=Fraction(tb):
                    tc=min(tb,t+max(ep.common_time_horizon_s,2*ep.terminal_window_s))
                    previous=None;successes=0;first_time=None
                    for level in range(ep.maximum_refinements+1):
                        cap=min(ep.terminal_window_s,float(choice[0]))/(2**level)
                        level_start=time.monotonic();level_evaluations=evaluations
                        try:
                            path=proposal(operator,state,t,tc,cap,totals)
                        except (_Failure,IntegrationError,DomainExit,DepletionRoundoffError,ValueError,OverflowError) as exc:
                            refinements.append(DepletionRefinement(t,level,cap,tc,None,None,
                                getattr(exc,'reason',str(exc)),evaluations-level_evaluations,time.monotonic()-level_start))
                            raise
                        if path.event is None:raise _Failure('unsupported','event_node_order_not_separated')
                        if first_time is None:first_time=path.event.time_s
                        if previous is not None:
                            passed,diffs=comparison(previous,path,tc)
                            successes=successes+1 if passed else 0
                            refinements.append(DepletionRefinement(t,level,cap,tc,path.event.time_s,diffs,
                                'comparison_pass' if passed else 'comparison_fail',evaluations-level_evaluations,time.monotonic()-level_start))
                            if successes>=2:
                                path.event=replace(path.event,coarse_time_s=first_time,previous_time_s=previous.event.time_s,
                                    common_time_s=tc,event_time_difference_s=diffs[0],common_amount_difference_mol=diffs[1],
                                    common_energy_difference_j=diffs[2],common_temperature_difference_k=diffs[3],common_pressure_difference_pa=diffs[4])
                                commit(path);break
                        else:
                            refinements.append(DepletionRefinement(t,level,cap,tc,path.event.time_s,None,'coarse_reference',
                                evaluations-level_evaluations,time.monotonic()-level_start))
                        previous=path
                    else:raise _Failure('unsupported','event_refinement_limit')
                else:
                    finish=min(tb,t+policy.maximum_step_s,t+float(choice[0])/4 if choice else tb)
                    run=normal(operator,state,t,finish,policy.maximum_step_s)
                    path=_Path(list(run.times_s),list(run.states),list(run.steps),operator,totals)
                    commit(path)
                    if run.status!='completed':raise _Failure(run.status,run.reason)
    except _Failure as exc:status=exc.status;reason=exc.reason
    except DomainExit as exc:status='domain_exit';reason=str(exc)
    except (IntegrationError,DepletionRoundoffError,ValueError,OverflowError) as exc:status='failed';reason=str(exc)
    return DepletionResult(status,reason,tuple(times),tuple(states),tuple(steps),tuple(events),tuple(corrections),operator,
        totals,tuple(cumulative_n),tuple(cumulative_u),evaluations,rejected,attempted,time.monotonic()-begin,tuple(refinements))
