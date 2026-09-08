"""Bounded wet-to-dry event integration, with explicit terminal-panel accounting."""
from dataclasses import dataclass,replace,field
from fractions import Fraction
import math
import time
import numpy as np
from types import MappingProxyType
from collections.abc import Mapping
from .integration import ConservedState,Rates,StepLedger,IntegrationPolicy,IntegrationError,DomainExit,integrate
from .depletion_roundoff import (DepletionRoundoffPolicy,DepletionRoundoffTotals,
    DepletionRoundoffError,DepletionClockEvidence,depletion_writeback)
from .affine_depletion_clock import locate_affine_depletion_clock


class DepletionIntegrationError(IntegrationError):pass


def _ordinary_program_endpoint(start, target, proposed, maximum_step, safe_duration):
    """Absorb only a bounded cap-rounding tail into the preceding full panel.

    The actual duration may differ from the cap by at most 32 cap ULPs;
    integration still uses that entire duration in every stage and ledger.
    Never extend past an exact inventory safety limit or repair an already
    adjacent-float physical panel by advancing its timestamp alone.
    """
    if proposed != min(target, start+maximum_step) or proposed >= target:
        return proposed
    duration = Fraction(target)-Fraction(start)
    allowance = 32*Fraction(math.ulp(maximum_step))
    if abs(duration-Fraction(maximum_step)) > allowance:
        return proposed
    if safe_duration is not None and (
            Fraction(maximum_step) > safe_duration or duration > safe_duration):
        return proposed
    gap = Fraction(target)-Fraction(proposed)
    local_allowance = min(Fraction(math.ulp(target)),
                          32*Fraction(math.ulp(min(maximum_step, target-start))))
    return target if 0 < gap <= local_allowance else proposed


def _number(v,positive=False):
    if type(v) not in (int,float) or not math.isfinite(v) or (positive and v<=0):
        raise DepletionIntegrationError('finite_depletion_policy_required')
    return float(v)


def _freeze_diagnostic(value):
    """Detach nested diagnostic containers from mutable caller-owned inputs."""
    if isinstance(value,Mapping):
        return MappingProxyType({key:_freeze_diagnostic(item) for key,item in value.items()})
    if isinstance(value,(tuple,list)):
        return tuple(_freeze_diagnostic(item) for item in value)
    if isinstance(value,np.ndarray):
        return _freeze_diagnostic(value.tolist())
    return value


def _quadratic_inventory_minimum(n, a, b, h):
    """Exact minimum of n+a*s+b*s² over the represented panel [0,h]."""
    points=[Fraction(),h]
    if b>0 and 0<-a/(2*b)<h:points.append(-a/(2*b))
    return min(n+a*s+b*s*s for s in points)


def _positive_affine_integral(initial, slope, h):
    """Exact gross positive transfer; signed negative transfer is separate."""
    cuts=[Fraction(),h]
    if slope and 0<-initial/slope<h:cuts.insert(1,-initial/slope)
    total=Fraction()
    for left,right in zip(cuts,cuts[1:]):
        if initial+slope*(left+right)/2>0:
            total+=initial*(right-left)+slope*(right*right-left*left)/2
    return total


@dataclass(frozen=True,kw_only=True)
class NestedApproachPolicy:
    """Explicit event-local ordinary mesh; terminal threshold is separate."""
    maximum_step_s: float
    reuse_ordinary_spine: bool = False
    strategy_id: str = 'nested_wet_ordinary_spine_v1'

    def __post_init__(self):
        _number(self.maximum_step_s,True)
        if (type(self.reuse_ordinary_spine) is not bool
                or self.strategy_id!='nested_wet_ordinary_spine_v1'):
            raise DepletionIntegrationError('explicit_nested_approach_policy_required')


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
    safe_inventory_fraction: float = .25
    nested_approach: NestedApproachPolicy | None = None
    terminal_method: str = 'euler'

    def __post_init__(self):
        for n in ('time_absolute_s','amount_absolute_mol','energy_absolute_j','temperature_absolute_k',
                  'pressure_absolute_pa','terminal_window_s','common_time_horizon_s'):
            _number(getattr(self,n),True)
        fraction=_number(self.safe_inventory_fraction,True)
        if fraction>=.5:raise DepletionIntegrationError('safe_inventory_fraction_must_be_below_half')
        if type(self.maximum_refinements) is not int or self.maximum_refinements<2:
            raise DepletionIntegrationError('at_least_two_refinements_required')
        if type(self.roundoff_policy) is not DepletionRoundoffPolicy:
            raise DepletionIntegrationError('explicit_roundoff_policy_required')
        if self.nested_approach is not None and type(self.nested_approach) is not NestedApproachPolicy:
            raise DepletionIntegrationError('explicit_nested_approach_policy_required')
        if type(self.terminal_method) is not str or self.terminal_method not in ('euler','affine_midpoint'):
            raise DepletionIntegrationError('unsupported_terminal_method')


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
    deterministic_contract: tuple[str,...] = ()

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
        if (not isinstance(self.deterministic_contract,tuple)
                or any(not isinstance(v,str) or not v or v!=v.strip() for v in self.deterministic_contract)):
            raise DepletionIntegrationError('immutable_deterministic_contract_required')

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
    terminal_evidence: object = None
    stretch_difference: float | None = None


@dataclass(frozen=True)
class AffineTerminalEvidence:
    """Actual two rate samples and midpoint predictor, not material evidence."""
    clock: object
    midpoint_state: ConservedState
    initial_observation: DepletionEvaluation
    midpoint_observation: DepletionEvaluation


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
    next_common_time_s: float | None = None
    comparison_details: Mapping = field(default_factory=lambda: MappingProxyType({}))
    phase_costs: Mapping = field(default_factory=lambda: MappingProxyType({}))
    approach_role: str = 'legacy'
    approach_cap_s: float | None = None
    approach_safe_inventory_fraction: float | None = None

    def __post_init__(self):
        for name in ('comparison_details','phase_costs'):
            object.__setattr__(self,name,_freeze_diagnostic(getattr(self,name)))


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
    safe_inventory_fraction: float = .25
    cumulative_absolute_component_residual_j: tuple | None = None
    phase_costs: Mapping = field(default_factory=lambda: MappingProxyType({}))
    reuse_counts: Mapping = field(default_factory=lambda: MappingProxyType({}))
    approach_strategy: str = 'legacy'
    terminal_method: str = 'euler'

    def __post_init__(self):
        for name in ('phase_costs','reuse_counts'):
            object.__setattr__(self,name,_freeze_diagnostic(getattr(self,name)))

    @property
    def accepted_trial_panels(self):
        """Accepted ordinary/terminal panels, including discarded refinement paths."""
        return self.attempted_steps


class _Failure(Exception):
    def __init__(self,status,reason):self.status=status;self.reason=reason


class _ReduceCommonTime(Exception):
    def __init__(self, common_time_s, event_time_s):
        self.common_time_s=common_time_s
        self.event_time_s=event_time_s


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
    approach_grid: tuple = ()


@dataclass
class _WetSpine:
    """Internal ordinary-only records, scoped to one root/horizon/mesh."""
    binding: tuple
    observations: dict = field(default_factory=dict)
    segments: dict = field(default_factory=dict)


def _mechanical_panel(state,first,h,second=None,hm=None):
    if state.mechanical_stretches is None:return None,None,None
    values=first.mechanical_rates_per_s
    other=values if second is None else second.mechanical_rates_per_s
    if values is None or other is None or values.shape!=state.mechanical_stretches.shape or other.shape!=values.shape:
        raise DepletionIntegrationError('mechanical_panel_rate_shape')
    exact=[];after=[]
    for before,a,b in zip(state.mechanical_stretches,values,other):
        a=Fraction(float(a));slope=Fraction() if second is None else (Fraction(float(b))-a)/(2*hm)
        value=Fraction(float(before))
        if _quadratic_inventory_minimum(value,a,slope,h)<=0:
            raise _Failure('unsupported','mechanical_panel_nonpositive_path')
        integral=h*a+h*h*slope
        represented=float(integral)
        if not math.isfinite(represented) or (integral and represented==0):
            raise DepletionIntegrationError('unrepresentable_mechanical_panel_increment')
        result=float(value+Fraction(represented))
        if not math.isfinite(result) or result<=0:
            raise _Failure('unsupported','mechanical_panel_nonpositive_endpoint')
        exact.append(integral);after.append(result)
    increments=np.array([float(v) for v in exact])
    rounding=tuple(Fraction(float(v))-q for v,q in zip(increments,exact))
    return np.array(after),increments,rounding


def integrate_depletion(initial,operator,*,start_s,end_s,integration_policy,event_policy,cancel=None):
    from .water_phase_transfer import WaterPhaseTransfer
    if (type(initial) is not ConservedState or type(operator) not in (WaterPhaseTransfer,ManufacturedDepletionAdapter)
            or type(integration_policy) is not IntegrationPolicy or type(event_policy) is not DepletionPolicy
            or (cancel is not None and not callable(cancel))):
        raise DepletionIntegrationError('explicit_depletion_host_state_policies_required')
    mechanical=initial.mechanical_stretches is not None
    if mechanical:
        _number(integration_policy.stretch_absolute_tolerance,True)
        _number(integration_policy.stretch_scale,True)
    start=_number(start_s);end=_number(end_s)
    if end<=start:raise DepletionIntegrationError('end_must_follow_start')
    if (len(operator.interfaces)!=initial.amounts_mol.shape[0]
            or max(operator.liquid_index,operator.water_vapor_index)>=initial.amounts_mol.shape[1]):
        raise DepletionIntegrationError('interface_inventory_shape_mismatch')
    if (type(operator) is WaterPhaseTransfer and
            event_policy.roundoff_policy.molar_mass_kg_mol!=operator.chemical.reference.molar_mass_kg_mol):
        raise DepletionIntegrationError('roundoff_water_molar_mass_mismatch')
    policy=integration_policy;ep=event_policy;begin=time.monotonic()
    nested=ep.nested_approach
    if (nested is not None and nested.reuse_ordinary_spine
            and type(operator) is ManufacturedDepletionAdapter and not operator.deterministic_contract):
        raise DepletionIntegrationError('ordinary_reuse_requires_deterministic_adapter_contract')
    times=[start];states=[initial];steps=[];events=[];corrections=[]
    totals=DepletionRoundoffTotals(ep.roundoff_policy)
    cumulative_n=[Fraction(0) for _ in initial.amounts_mol.flat]
    cumulative_u=[Fraction(0) for _ in initial.internal_energy_j.flat]
    cumulative_stretch=([Fraction() for _ in initial.mechanical_stretches] if mechanical else [])
    cumulative_stretch_exact=list(cumulative_stretch)
    cumulative_stretch_roundoff=list(cumulative_stretch)
    evaluations=rejected=attempted=0
    refinements=[]
    energy_binding=initial.energy_model_identity
    component_schema=...
    component_residual_totals=[Fraction() for _ in initial.internal_energy_j]
    costs={name:{'evaluations':0,'panels':0,'rejections':0}
           for name in ('ordinary','approach','terminal','dry','comparison')}
    reused={'observations':0,'panels':0}

    def frozen_costs(before=None):
        return MappingProxyType({name:MappingProxyType({key:value-(before[name][key] if before else 0)
            for key,value in values.items()}) for name,values in costs.items()})

    def cost_snapshot():
        return {name:dict(values) for name,values in costs.items()}

    def check_component_schema(rates):
        nonlocal component_schema
        schema=None if rates.cell_power_components_w is None else tuple(rates.cell_power_components_w)
        if component_schema is ...:component_schema=schema
        elif schema!=component_schema:raise DepletionIntegrationError('component_work_schema_changed')

    def guard():
        if cancel is not None and cancel():raise _Failure('cancelled','cancel_requested')
        if time.monotonic()-begin>=policy.maximum_wall_seconds:raise _Failure('resource_limit','wall_time_limit')
        if attempted>=policy.maximum_steps:raise _Failure('resource_limit','global_accepted_trial_panel_limit')
        if rejected>=policy.maximum_rejections:raise _Failure('resource_limit','total_rejection_limit')

    def observe(op,state,t,phase='ordinary'):
        nonlocal evaluations
        guard();evaluations+=1;costs[phase]['evaluations']+=1
        if state.energy_model_identity!=energy_binding:raise DepletionIntegrationError(
            'energy_model_identity_changed')
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
        # A deterministic callback may reuse mutable output buffers. Detach
        # every observation sequence before ordinary caching or event storage.
        # Rates already owns immutable copies of its numeric arrays.
        result=replace(result,evaporation_mol_s=tuple(result.evaporation_mol_s),
            temperatures_k=tuple(result.temperatures_k),temperature_errors_k=tuple(result.temperature_errors_k),
            pressures_pa=tuple(result.pressures_pa),pressure_errors_pa=tuple(result.pressure_errors_pa))
        count=state.amounts_mol.shape[0]
        if type(result.rates) is not Rates:raise DepletionIntegrationError('explicit_rates_required')
        result.rates.derivatives(state)
        check_component_schema(result.rates)
        for seq in (result.evaporation_mol_s,result.temperatures_k,result.temperature_errors_k,result.pressures_pa,result.pressure_errors_pa):
            if len(seq)!=count or any(not math.isfinite(v) for v in seq):raise DepletionIntegrationError('finite_complete_observations_required')
        if any(v<0 for v in result.temperature_errors_k+result.pressure_errors_pa):raise DepletionIntegrationError('negative_observation_error')
        guard();return result

    def normal(op,state,t,finish,maxstep,stage_check=None,phase='ordinary'):
        nonlocal evaluations,rejected,attempted
        guard()
        if finish<=t:raise _Failure('unsupported','unresolvable_time_panel')
        if maxstep<policy.minimum_step_s:raise _Failure('resource_limit','event_step_below_configured_minimum')
        bounded_step=max(policy.minimum_step_s,min(maxstep,finish-t))
        p=replace(policy,initial_step_s=bounded_step,maximum_step_s=bounded_step,
            maximum_steps=max(1,policy.maximum_steps-attempted),
            maximum_rejections=max(1,policy.maximum_rejections-rejected),
            maximum_wall_seconds=max(1e-12,policy.maximum_wall_seconds-(time.monotonic()-begin)))
        pending=None
        def checked_operator(stage,at):
            nonlocal pending
            if stage.energy_model_identity!=energy_binding:raise DepletionIntegrationError(
                'energy_model_identity_changed')
            if stage_check is None:
                # Preserve the old ordinary-segment callback/evaluation counting;
                # only add the cross-segment schema guard, without another decode.
                rates=op(stage,at)
                if type(rates) is not Rates:raise DepletionIntegrationError('explicit_rates_required')
                check_component_schema(rates)
                return rates
            try:
                observed=observe(op,stage,at,phase)
                stage_check(stage,at,observed)
            except (_ReduceCommonTime,_Failure) as exc:
                pending=exc
                # Return through integrate's normal error boundary so its
                # already attempted evaluations/panels/rejections are retained.
                raise DepletionIntegrationError('preview_common_time_replan') from exc
            return observed.rates
        run=integrate(state,checked_operator,
                      start_s=t,end_s=finish,policy=p,cancel=cancel)
        if stage_check is None:
            evaluations+=run.evaluations;costs[phase]['evaluations']+=run.evaluations
        rejected+=run.rejected_trials;attempted+=len(run.steps)
        costs[phase]['rejections']+=run.rejected_trials;costs[phase]['panels']+=len(run.steps)
        if pending is not None:raise pending
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

    def affine_terminal(path,obs,tau,cell,tc):
        nonlocal attempted
        t=path.times[-1];state=path.states[-1];li=path.op.liquid_index;vi=path.op.water_vapor_index
        binding=spine_binding(path.op,state,t,tc,0.,0.,cell)
        midpoint=float(Fraction(t)+tau/2)
        upper_exact=min(Fraction(tc),Fraction(t)+2*tau)
        upper=float(upper_exact)
        if Fraction(upper)>upper_exact:upper=math.nextafter(upper,-math.inf)
        if not t<midpoint<upper or Fraction(midpoint)>=Fraction(t)+tau:
            raise _Failure('unsupported','unresolvable_affine_midpoint')
        hm=Fraction(midpoint)-Fraction(t)
        names=('face_species_mol_s','face_energy_w','reaction_species_mol_s','cell_power_w')

        def integrate_fields(interval,second=None):
            arrays=[]
            for name in names:
                values=getattr(obs.rates,name);other=getattr(second.rates,name) if second else values
                out=np.empty_like(values)
                for idx in np.ndindex(values.shape):
                    a=Fraction(float(values[idx]));b=Fraction(float(other[idx]))
                    out[idx]=float(interval*a+interval*interval*(b-a)/(2*hm))
                arrays.append(out)
            return arrays

        def advance(fields,stretches):
            fn,fu,rn,work=fields
            def add(before,terms):
                out=np.empty_like(before)
                for idx in np.ndindex(before.shape):
                    out[idx]=float(Fraction(float(before[idx]))+sum(
                        (Fraction(float(v[idx])) for v in terms),Fraction()))
                return out
            amounts=add(state.amounts_mol,(fn[:-1],-fn[1:],rn))
            energy=add(state.internal_energy_j,(fu[:-1],-fu[1:],work))
            if np.any(amounts<0) or not np.all(np.isfinite(amounts)) or not np.all(np.isfinite(energy)):
                raise _Failure('unsupported','affine_panel_invalid_inventory_or_energy')
            return ConservedState(amounts,energy,energy_model_identity=state.energy_model_identity,
                                  mechanical_stretches=stretches)

        predicted_stretches,_,_=_mechanical_panel(state,obs.rates,hm)
        predictor=advance(integrate_fields(hm),predicted_stretches)
        if any(predictor.amounts_mol[i,li]<=0 for i,mode in enumerate(path.op.interfaces)
               if mode=='existing_liquid'):
            raise _Failure('unsupported','affine_midpoint_not_wet')
        middle=observe(path.op,predictor,midpoint,'terminal')
        if binding!=spine_binding(path.op,state,t,tc,0.,0.,cell):
            raise DepletionIntegrationError('affine_terminal_source_binding_changed')
        guard()
        def liquid_rates(observed):
            r=observed.rates
            return (float(r.face_species_mol_s[cell,li]),-float(r.face_species_mol_s[cell+1,li]),
                    float(r.reaction_species_mol_s[cell,li]))
        clock=locate_affine_depletion_clock(t,midpoint,float(state.amounts_mol[cell,li]),
            liquid_rates(obs),liquid_rates(middle),upper,ep.time_absolute_s)
        endpoint=clock.end_s
        if not midpoint<endpoint<tc:raise _Failure('unsupported','affine_root_outside_terminal_interval')
        h=Fraction(endpoint)-Fraction(t)
        # Check the entire reconstructed inventory polynomial, including any
        # interior minimum. Endpoint positivity alone can miss a crossed zero.
        for idx in np.ndindex(state.amounts_mol.shape):
            i,j=idx
            def net(observed):
                r=observed.rates
                return (Fraction(float(r.face_species_mol_s[i,j]))-Fraction(float(r.face_species_mol_s[i+1,j]))
                        +Fraction(float(r.reaction_species_mol_s[i,j])))
            a=net(obs);b=(net(middle)-a)/(2*hm);n=Fraction(float(state.amounts_mol[idx]))
            minimum=_quadratic_inventory_minimum(n,a,b,h)
            competing=(j==li and i!=cell and path.op.interfaces[i]=='existing_liquid' and n>0)
            if minimum<0 or (competing and minimum==0):
                raise _Failure('unsupported','affine_competing_inventory_crossing')
        stretches,stretch_increment,stretch_rounding=_mechanical_panel(state,obs.rates,h,middle.rates,hm)
        fields=integrate_fields(h,middle);raw=advance(fields,stretches);fn,fu,rn,work=fields
        # Transfer observations are signed. Integrate their positive part
        # exactly; rounding this diagnostic upward would loosen a budget.
        e0=Fraction(float(obs.evaporation_mol_s[cell]));slope=(Fraction(float(middle.evaporation_mol_s[cell]))-e0)/hm
        gross=_positive_affine_integral(e0,slope,h)
        evap=float(gross)
        if Fraction(evap)>gross:evap=math.nextafter(evap,-math.inf)
        record=None
        if raw.amounts_mol[cell,li]>0:
            raw,record,path.totals=depletion_writeback(raw,cell_index=cell,liquid_index=li,vapor_index=vi,
                panel_liquid_start_mol=float(state.amounts_mol[cell,li]),
                panel_liquid_terms_mol=(float(fn[cell,li]),-float(fn[cell+1,li]),float(rn[cell,li])),
                positive_evaporated_mol=evap,policy=ep.roundoff_policy,totals=path.totals,clock_evidence=clock)
        components=rounding=None
        if obs.rates.cell_power_components_w is not None:
            components={};rounding={}
            for key,values in obs.rates.cell_power_components_w.items():
                other=middle.rates.cell_power_components_w[key]
                exact=[h*Fraction(float(a))+h*h*(Fraction(float(b))-Fraction(float(a)))/(2*hm)
                       for a,b in zip(values,other)]
                components[key]=np.array([float(v) for v in exact])
                rounding[key]=tuple(Fraction(float(v))-q for v,q in zip(components[key],exact))
        guard()
        if binding!=spine_binding(path.op,state,t,tc,0.,0.,cell):
            raise DepletionIntegrationError('affine_terminal_source_binding_changed')
        panel=StepLedger(t,endpoint,*fields,components,rounding,
            stretch_increment=stretch_increment,stretch_quadrature_roundoff=stretch_rounding)
        attempted+=1;costs['terminal']['panels']+=1
        original_op=path.op
        path.op=path.op.with_depleted_cells(raw,(cell,))
        if binding!=spine_binding(original_op,state,t,tc,0.,0.,cell):
            raise DepletionIntegrationError('affine_terminal_source_binding_changed')
        path.times.append(endpoint);path.states.append(raw);path.steps.append(panel)
        path.event_state=raw;path.event_observation=observe(path.op,raw,endpoint,'terminal')
        if binding!=spine_binding(original_op,state,t,tc,0.,0.,cell):
            raise DepletionIntegrationError('affine_terminal_source_binding_changed')
        path.event=DepletionEvent(cell,endpoint,endpoint,endpoint,endpoint,0.,0.,0.,0.,0.,panel,record,
            clock.event_time_rounding_s,evap,terminal_evidence=AffineTerminalEvidence(clock,predictor,obs,middle))

    def terminal(path,obs,tau,cell,tc):
        nonlocal attempted
        if ep.terminal_method=='affine_midpoint':
            return affine_terminal(path,obs,tau,cell,tc)
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
        stretches,stretch_increment,stretch_rounding=_mechanical_panel(state,obs.rates,interval)
        raw=ConservedState(amounts,energy,energy_model_identity=state.energy_model_identity,
                           mechanical_stretches=stretches);record=None
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
        components=rounding=None
        if obs.rates.cell_power_components_w is not None:
            components={key:integrated(value) for key,value in obs.rates.cell_power_components_w.items()}
            rounding={key:tuple(Fraction(float(value))-interval*Fraction(float(rate))
                       for value,rate in zip(components[key],obs.rates.cell_power_components_w[key]))
                      for key in components}
        panel=StepLedger(t,endpoint,*fields,components,rounding,
            stretch_increment=stretch_increment,stretch_quadrature_roundoff=stretch_rounding);attempted+=1;costs['terminal']['panels']+=1
        path.op=path.op.with_depleted_cells(raw,(cell,))
        path.times.append(endpoint);path.states.append(raw);path.steps.append(panel)
        path.event_state=raw;path.event_observation=observe(path.op,raw,endpoint,'terminal')
        path.event=DepletionEvent(cell,endpoint,endpoint,endpoint,endpoint,0.,0.,0.,0.,0.,panel,record,
            exact-Fraction(endpoint),evap)

    def continue_after_event(path,tc):
        # Replan at ordinary RK stages as well as accepted panel boundaries:
        # an accelerating remaining sink can invalidate a beginning-step tau.
        def check_remaining(current,at,obs):
            other=candidate(path.op,current,obs)
            if other is not None:
                predicted=Fraction(at)+other[0]
                if predicted<=Fraction(tc)+Fraction(ep.time_absolute_s):
                    first=Fraction(path.event.time_s)
                    midpoint=float((first+min(predicted,Fraction(tc)))/2)
                    if (Fraction(midpoint)-first<=Fraction(ep.time_absolute_s)
                            or predicted-Fraction(midpoint)<=Fraction(ep.time_absolute_s)
                            or not midpoint<tc):
                        raise _Failure('unsupported','successive_events_not_separated')
                    raise _ReduceCommonTime(midpoint,path.event.time_s)
            return other
        while path.times[-1]<tc:
            at=path.times[-1];current=path.states[-1]
            obs=observe(path.op,current,at,'dry');other=check_remaining(current,at,obs)
            desired=min(policy.maximum_step_s,tc-at,ep.safe_inventory_fraction*float(other[0]) if other else policy.maximum_step_s)
            finish=min(tc,at+desired)
            # Choose the named common endpoint directly when its entire exact
            # interval fits both limits; subtract/add can leave a one-ULP tail.
            remaining=Fraction(tc)-Fraction(at)
            safe_duration=Fraction(ep.safe_inventory_fraction)*other[0] if other else None
            if (remaining<=Fraction(policy.maximum_step_s) and
                    (safe_duration is None or remaining<=safe_duration)):
                finish=tc
            extend(path,normal(path.op,current,at,finish,policy.maximum_step_s,
                               check_remaining if any(m=='existing_liquid' for m in path.op.interfaces) else None,
                               phase='dry'))

    def spine_binding(op,state,t,tc,approach_cap,safe_fraction,event_cell):
        # Explicit immutable model/source descriptors, not a callback-result
        # cache across operators. Native source/config guards still run on
        # every newly executed observation, terminal and common-time decode.
        if type(op) is ManufacturedDepletionAdapter:
            source=(id(op.evaluate_callback),op.deterministic_contract,op.source_ids)
        else:
            implementation=op.chemical.water.implementation
            source=(op.source_ids,tuple(sorted(op.chemical.source_asset_sha256.items())),
                    None if implementation is None else implementation.sha256,
                    getattr(op.base_model,'energy_model_identity',None))
        return (id(op),id(state),state.energy_model_identity,t,tc,approach_cap,safe_fraction,
                event_cell,op.interfaces,op.liquid_index,op.water_vapor_index,source,ep.terminal_method)

    def proposal(op,state,t,tc,cap,total,*,approach_cap=None,safe_fraction=None,spine=None,event_cell=None):
        ordinary_cap=cap if approach_cap is None else approach_cap
        safe=ep.safe_inventory_fraction if safe_fraction is None else safe_fraction
        binding=spine_binding(op,state,t,tc,ordinary_cap,safe,event_cell) if spine is not None else None
        if spine is not None and spine.binding!=binding:
            raise DepletionIntegrationError('ordinary_spine_binding_changed')
        path=_Path([t],[state],[],op,total)
        while path.times[-1]<tc:
            guard()
            if spine is not None and spine.binding!=spine_binding(op,state,t,tc,ordinary_cap,safe,event_cell):
                raise DepletionIntegrationError('ordinary_spine_binding_changed')
            at=path.times[-1];current=path.states[-1]
            node=spine.observations.get(at) if spine is not None else None
            if node is not None:
                if node[0] is not current:raise DepletionIntegrationError('ordinary_spine_state_changed')
                obs=node[1];reused['observations']+=1
                # No new EOS work is charged for a previously evaluated node.
                # Still run cancellation/resource and state binding guards.
                if current.energy_model_identity!=energy_binding:
                    raise DepletionIntegrationError('energy_model_identity_changed')
            else:
                obs=observe(path.op,current,at,'approach')
            choice=candidate(path.op,current,obs)
            if choice is not None and event_cell is not None and choice[1]!=event_cell:
                raise _Failure('unsupported','event_identity_not_separated')
            if node is None and spine is not None:
                spine.observations[at]=(current,obs)
            if choice is not None:
                tau,cell=choice
                if tau<=Fraction(cap) and Fraction(at)+tau<=Fraction(tc):
                    path.approach_grid=tuple(path.times)
                    terminal(path,obs,tau,cell,tc)
                    if path.times[-1]>=tc:raise _Failure('unsupported','no_common_post_event_time')
                    continue_after_event(path,tc)
                    return path
            desired=min(ordinary_cap,tc-at,safe*float(choice[0]) if choice else ordinary_cap)
            finish=min(tc,at+desired)
            segment=spine.segments.get(at) if spine is not None else None
            if segment is not None:
                if segment.states[0] is not current or segment.times_s[-1]!=finish:
                    raise DepletionIntegrationError('ordinary_spine_edge_changed')
                reused['panels']+=len(segment.steps)
                extend(path,segment)
            else:
                segment=normal(path.op,current,at,finish,ordinary_cap,phase='approach')
                extend(path,segment)
                # extend raises on every non-completed ordinary segment: no
                # partial/failing path is eligible for later reuse.
                if spine is not None:spine.segments[at]=segment
        path.approach_grid=tuple(path.times)
        return path

    def comparison(a,b,tc):
        if a.event is None or b.event is None:raise _Failure('unsupported','event_node_order_not_separated')
        if a.event.cell_index!=b.event.cell_index:raise _Failure('unsupported','event_identity_not_separated')
        ao=observe(a.op,a.states[-1],tc,'comparison');bo=observe(b.op,b.states[-1],tc,'comparison')
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
        ds=None
        if mechanical:
            ds=max(delta(a.event_state.mechanical_stretches,b.event_state.mechanical_stretches),
                   delta(a.states[-1].mechanical_stretches,b.states[-1].mechanical_stretches))
            passed=passed and math.isfinite(ds) and ds<=policy.stretch_absolute_tolerance
        def difference_record(x,y):
            differences=np.abs(np.asarray(x)-np.asarray(y))
            index=tuple(int(i) for i in np.unravel_index(np.argmax(differences),differences.shape))
            return MappingProxyType({'absolute_differences':tuple(tuple(float(v) for v in row)
                for row in differences) if differences.ndim==2 else tuple(float(v) for v in differences),
                'maximum_index':index,'maximum':float(np.max(differences))})
        def observation_record(x,y):
            return MappingProxyType({'temperature_nominal_difference_k':delta(x.temperatures_k,y.temperatures_k),
                'temperature_errors_a_k':tuple(x.temperature_errors_k),'temperature_errors_b_k':tuple(y.temperature_errors_k),
                'pressure_nominal_difference_pa':delta(x.pressures_pa,y.pressures_pa),
                'pressure_errors_a_pa':tuple(x.pressure_errors_pa),'pressure_errors_b_pa':tuple(y.pressure_errors_pa)})
        details=MappingProxyType({'event_amounts':difference_record(a.event_state.amounts_mol,b.event_state.amounts_mol),
            'common_amounts':difference_record(a.states[-1].amounts_mol,b.states[-1].amounts_mol),
            'event_energy':difference_record(a.event_state.internal_energy_j,b.event_state.internal_energy_j),
            'common_energy':difference_record(a.states[-1].internal_energy_j,b.states[-1].internal_energy_j),
            'event_observations':observation_record(a.event_observation,b.event_observation),
            'common_observations':observation_record(ao,bo),
            'terminal_start_a_s':a.event.terminal_panel.start_s,'terminal_start_b_s':b.event.terminal_panel.start_s,
            'terminal_end_a_s':a.event.time_s,'terminal_end_b_s':b.event.time_s,
            'approach_grid_a_s':a.approach_grid,'approach_grid_b_s':b.approach_grid})
        if mechanical:
            details=MappingProxyType(dict(details,
                event_stretches=difference_record(a.event_state.mechanical_stretches,b.event_state.mechanical_stretches),
                common_stretches=difference_record(a.states[-1].mechanical_stretches,b.states[-1].mechanical_stretches)))
        return passed,((dtime,dn,du,dt,dp,ds) if mechanical else (dtime,dn,du,dt,dp)),details

    def commit(path):
        nonlocal cumulative_n,cumulative_u,totals,operator,component_residual_totals
        nonlocal cumulative_stretch,cumulative_stretch_exact,cumulative_stretch_roundoff
        event=path.event
        cn=list(cumulative_n);cu=list(cumulative_u);component_totals=list(component_residual_totals)
        cs=list(cumulative_stretch);ce=list(cumulative_stretch_exact);cr=list(cumulative_stretch_roundoff)
        for j,step in enumerate(path.steps):
            if step.component_sum_residual_j is not None:
                component_totals=[old+abs(delta) for old,delta in
                                  zip(component_totals,step.component_sum_residual_j)]
                if any(v>Fraction(policy.energy_absolute_tolerance_j) for v in component_totals):
                    raise _Failure('failed','cross_segment_component_sum_roundoff')
            after=path.states[j+1]
            before=path.states[j]
            if (after.energy_model_identity!=energy_binding or before.energy_model_identity!=energy_binding
                    or (after.mechanical_stretches is not None)!=mechanical):
                raise DepletionIntegrationError('mechanical_prefix_binding_changed')
            if mechanical:
                inc=step.stretch_increment;rounding=step.stretch_quadrature_roundoff
                if (inc is None or rounding is None or inc.shape!=initial.mechanical_stretches.shape
                        or len(rounding)!=len(inc) or before.mechanical_stretches is None):
                    raise DepletionIntegrationError('complete_mechanical_prefix_ledger_required')
                tol=Fraction(policy.stretch_absolute_tolerance)
                for i,(v,q) in enumerate(zip(inc,rounding)):
                    represented=Fraction(float(v));exact=represented-q
                    cs[i]+=represented;ce[i]+=exact;cr[i]+=abs(q)
                    local=Fraction(float(after.mechanical_stretches[i]))-Fraction(float(before.mechanical_stretches[i]))
                    change=Fraction(float(after.mechanical_stretches[i]))-Fraction(float(initial.mechanical_stretches[i]))
                    if (abs(local-represented)>tol or abs(local-exact)>tol or
                            abs(change-cs[i])>tol or abs(change-ce[i])>tol or cr[i]>tol):
                        raise _Failure('failed','cross_segment_stretch_prefix_roundoff')
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
        cumulative_n=cn;cumulative_u=cu;component_residual_totals=component_totals
        cumulative_stretch=cs;cumulative_stretch_exact=ce;cumulative_stretch_roundoff=cr
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
                    level=0;horizon_restarts=0
                    approach_cap=(min(nested.maximum_step_s,policy.maximum_step_s) if nested else None)
                    root_binding=(spine_binding(operator,state,t,tc,approach_cap,ep.safe_inventory_fraction,choice[1])
                                  if nested or ep.terminal_method=='affine_midpoint' else None)
                    spine=(_WetSpine(root_binding)
                           if nested and nested.reuse_ordinary_spine else None)
                    while level<=ep.maximum_refinements:
                        cap=min(ep.terminal_window_s,float(choice[0]))/(2**level)
                        level_start=time.monotonic();level_evaluations=evaluations
                        before_cost=cost_snapshot()
                        try:
                            path=proposal(operator,state,t,tc,cap,totals,approach_cap=approach_cap,
                                spine=spine,event_cell=choice[1] if nested else None)
                        except _ReduceCommonTime as exc:
                            refinements.append(DepletionRefinement(t,level,cap,tc,exc.event_time_s,None,
                                'common_time_horizon_reduced',evaluations-level_evaluations,time.monotonic()-level_start,
                                exc.common_time_s,phase_costs=frozen_costs(before_cost),
                                approach_role='terminal_refinement' if nested else 'legacy',approach_cap_s=approach_cap,
                                approach_safe_inventory_fraction=ep.safe_inventory_fraction if nested else None))
                            horizon_restarts+=1
                            if horizon_restarts>ep.maximum_refinements:
                                raise _Failure('resource_limit','common_time_restart_limit')
                            if (nested is not None or ep.terminal_method=='affine_midpoint') and root_binding!=spine_binding(operator,state,t,tc,approach_cap,
                                    ep.safe_inventory_fraction,choice[1]):
                                raise DepletionIntegrationError('ordinary_spine_binding_changed')
                            tc=exc.common_time_s;previous=None;successes=0;first_time=None;level=0
                            root_binding=(spine_binding(operator,state,t,tc,approach_cap,ep.safe_inventory_fraction,choice[1])
                                          if nested or ep.terminal_method=='affine_midpoint' else None)
                            spine=(_WetSpine(root_binding)
                                   if nested and nested.reuse_ordinary_spine else None)
                            continue
                        except (_Failure,IntegrationError,DomainExit,DepletionRoundoffError,ValueError,OverflowError) as exc:
                            refinements.append(DepletionRefinement(t,level,cap,tc,None,None,
                                getattr(exc,'reason',str(exc)),evaluations-level_evaluations,time.monotonic()-level_start,
                                phase_costs=frozen_costs(before_cost),approach_role='terminal_refinement' if nested else 'legacy',
                                approach_cap_s=approach_cap,approach_safe_inventory_fraction=ep.safe_inventory_fraction if nested else None))
                            raise
                        if path.event is None:raise _Failure('unsupported','event_node_order_not_separated')
                        if first_time is None:first_time=path.event.time_s
                        if previous is not None:
                            passed,diffs,details=comparison(previous,path,tc)
                            successes=successes+1 if passed else 0
                            refinements.append(DepletionRefinement(t,level,cap,tc,path.event.time_s,diffs,
                                'comparison_pass' if passed else 'comparison_fail',evaluations-level_evaluations,time.monotonic()-level_start,
                                comparison_details=details,phase_costs=frozen_costs(before_cost),
                                approach_role='terminal_refinement' if nested else 'legacy',approach_cap_s=approach_cap,
                                approach_safe_inventory_fraction=ep.safe_inventory_fraction if nested else None))
                            if successes>=2:
                                if nested is not None:
                                    guard()
                                    if root_binding!=spine_binding(operator,state,t,tc,approach_cap,
                                            ep.safe_inventory_fraction,choice[1]):
                                        raise DepletionIntegrationError('ordinary_spine_binding_changed')
                                    # Shared terminal agreement must survive a genuinely
                                    # different ordinary mesh. Both controls are halved:
                                    # an inactive maximum cap alone is not refinement.
                                    fine_cap=approach_cap/2
                                    fine_safe=ep.safe_inventory_fraction/2
                                    independent_start=time.monotonic();independent_evaluations=evaluations
                                    independent_cost=cost_snapshot()
                                    independent_recorded=False
                                    try:
                                        fine=proposal(operator,state,t,tc,cap,totals,
                                            approach_cap=fine_cap,safe_fraction=fine_safe,event_cell=choice[1])
                                        if fine.approach_grid==path.approach_grid:
                                            raise _Failure('unsupported','independent_approach_grid_uninformative')
                                        approach_pass,approach_diffs,approach_details=comparison(path,fine,tc)
                                        refinements.append(DepletionRefinement(t,level,cap,tc,fine.event.time_s,approach_diffs,
                                            'independent_approach_pass' if approach_pass else 'independent_approach_fail',
                                            evaluations-independent_evaluations,time.monotonic()-independent_start,
                                            comparison_details=approach_details,phase_costs=frozen_costs(independent_cost),
                                            approach_role='independent_halved_controls',approach_cap_s=fine_cap,
                                            approach_safe_inventory_fraction=fine_safe))
                                        independent_recorded=True
                                        if not approach_pass:
                                            raise _Failure('unsupported','independent_approach_comparison_failed')
                                        diffs=tuple(max(a,b) for a,b in zip(diffs,approach_diffs))
                                    except _ReduceCommonTime as exc:
                                        refinements.append(DepletionRefinement(t,level,cap,tc,exc.event_time_s,None,
                                            'common_time_horizon_reduced',evaluations-independent_evaluations,
                                            time.monotonic()-independent_start,exc.common_time_s,
                                            phase_costs=frozen_costs(independent_cost),approach_role='independent_halved_controls',
                                            approach_cap_s=fine_cap,approach_safe_inventory_fraction=fine_safe))
                                        horizon_restarts+=1
                                        if horizon_restarts>ep.maximum_refinements:
                                            raise _Failure('resource_limit','common_time_restart_limit')
                                        if root_binding!=spine_binding(operator,state,t,tc,approach_cap,
                                                ep.safe_inventory_fraction,choice[1]):
                                            raise DepletionIntegrationError('ordinary_spine_binding_changed')
                                        tc=exc.common_time_s;previous=None;successes=0;first_time=None;level=0
                                        root_binding=spine_binding(operator,state,t,tc,approach_cap,ep.safe_inventory_fraction,choice[1])
                                        spine=(_WetSpine(root_binding)
                                               if nested.reuse_ordinary_spine else None)
                                        continue
                                    except (_Failure,IntegrationError,DomainExit,DepletionRoundoffError,ValueError,OverflowError) as exc:
                                        if not independent_recorded:
                                            refinements.append(DepletionRefinement(t,level,cap,tc,None,None,
                                                getattr(exc,'reason',str(exc)),evaluations-independent_evaluations,
                                                time.monotonic()-independent_start,phase_costs=frozen_costs(independent_cost),
                                                approach_role='independent_halved_controls',approach_cap_s=fine_cap,
                                                approach_safe_inventory_fraction=fine_safe))
                                        raise
                                    # Commit the twice-terminal-verified candidate only;
                                    # the finer independent branch remains speculative.
                                path.event=replace(path.event,coarse_time_s=first_time,previous_time_s=previous.event.time_s,
                                    common_time_s=tc,event_time_difference_s=diffs[0],common_amount_difference_mol=diffs[1],
                                    common_energy_difference_j=diffs[2],common_temperature_difference_k=diffs[3],common_pressure_difference_pa=diffs[4],
                                    stretch_difference=diffs[5] if mechanical else None)
                                if nested is not None or ep.terminal_method=='affine_midpoint':
                                    guard()
                                    if root_binding!=spine_binding(operator,state,t,tc,approach_cap,
                                            ep.safe_inventory_fraction,choice[1]):
                                        raise DepletionIntegrationError('ordinary_spine_binding_changed')
                                commit(path);break
                        else:
                            refinements.append(DepletionRefinement(t,level,cap,tc,path.event.time_s,None,'coarse_reference',
                                evaluations-level_evaluations,time.monotonic()-level_start,
                                phase_costs=frozen_costs(before_cost),approach_role='terminal_refinement' if nested else 'legacy',
                                approach_cap_s=approach_cap,approach_safe_inventory_fraction=ep.safe_inventory_fraction if nested else None))
                        previous=path;level+=1
                    else:raise _Failure('unsupported','event_refinement_limit')
                else:
                    finish=(tb if all(m=='depleted_no_nucleation' for m in operator.interfaces) else
                            min(tb,t+policy.maximum_step_s,t+ep.safe_inventory_fraction*float(choice[0]) if choice else tb))
                    safe_duration=(Fraction(ep.safe_inventory_fraction)*choice[0] if choice else None)
                    finish=_ordinary_program_endpoint(t,tb,finish,policy.maximum_step_s,safe_duration)
                    run=normal(operator,state,t,finish,policy.maximum_step_s)
                    path=_Path(list(run.times_s),list(run.states),list(run.steps),operator,totals)
                    commit(path)
                    if run.status!='completed':raise _Failure(run.status,run.reason)
    except _Failure as exc:status=exc.status;reason=exc.reason
    except DomainExit as exc:status='domain_exit';reason=str(exc)
    except (IntegrationError,DepletionRoundoffError,ValueError,OverflowError) as exc:status='failed';reason=str(exc)
    return DepletionResult(status,reason,tuple(times),tuple(states),tuple(steps),tuple(events),tuple(corrections),operator,
        totals,tuple(cumulative_n),tuple(cumulative_u),evaluations,rejected,attempted,time.monotonic()-begin,tuple(refinements),ep.safe_inventory_fraction,
        tuple(component_residual_totals) if component_schema not in (...,None) else None,
        frozen_costs(),MappingProxyType(dict(reused)),nested.strategy_id if nested else 'legacy',ep.terminal_method)
