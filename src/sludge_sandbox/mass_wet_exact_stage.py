"""Unit-separated autonomous exact-time trials; no global commit or event switch."""
from dataclasses import dataclass,fields
from fractions import Fraction as F
import math,time
import hashlib, marshal
from typing import Callable
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.mass_wet_transport import WetPair,WetRates,represented
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.mass_storage_bridge import require
from sludge_sandbox.integration import DomainExit


def exact(x: int | float | F) -> F:
    require(type(x) in (int,float,F),'explicit_numeric')
    if type(x) is float:require(math.isfinite(x),'finite_numeric')
    return F(x)


@dataclass(frozen=True)
class MixedStagePolicy:
    solid_mass_absolute_kg: float
    amount_absolute_mol: float
    energy_absolute_j: float
    temperature_absolute_k: float
    pressure_absolute_pa: float
    time_absolute_s: float
    minimum_step_s: float
    maximum_step_s: float
    maximum_evaluations: int=9
    maximum_wall_seconds: float=30.

    def __post_init__(self):
        for field in fields(self):
            v=getattr(self,field.name)
            if field.name=='maximum_evaluations':require(type(v) is int and v>=0,'integer_evaluation_budget')
            else:require(exact(v)>0 and math.isfinite(float(v)),'positive_finite_policy')
        require(exact(self.minimum_step_s)<=exact(self.maximum_step_s),'ordered_step_domain')


@dataclass(frozen=True)
class ManufacturedConstantLiquidFixture:
    """Explicit analytic test-model declaration, never a native-water certificate.

    Actual non-production evaluator/response callbacks must carry matching
    fixture declarations. Their identities and full host binding are retained.
    A declaration does not prove arbitrary Python code is constant: it selects
    the explicitly manufactured model whose independent tests must establish it.
    """
    host_binding: str
    volume_m3_mol: F
    temperature_domain_k: tuple
    pressure_domain_pa: tuple
    evaluators: tuple
    responses: tuple
    callback_code_hashes: tuple
    qualification: str = 'manufactured_test_fixture_constant_liquid_only'

    @classmethod
    def capture(cls, pair: WetPair, *, volume_m3_mol: F):
        require(type(volume_m3_mol) is F and volume_m3_mol>0,'exact_positive_fixture_volume')
        evaluators=tuple(s.water.state_tp.__func__ for s in pair.storages)
        responses=tuple(s.water.state_tp_response.__func__ for s in pair.storages)
        out=cls(pair.binding(),volume_m3_mol,
                tuple(s.temperature_domain_k for s in pair.storages),
                tuple(s.fluid_template.envelope.pressure_range_pa for s in pair.storages),
                evaluators,responses,tuple(hashlib.sha256(marshal.dumps(fn.__code__)).hexdigest() for fn in (*evaluators,*responses)))
        out.check(pair)
        return out

    def check(self, pair: WetPair) -> None:
        require(self.qualification=='manufactured_test_fixture_constant_liquid_only','explicit_fixture_qualification')
        require(pair.binding()==self.host_binding,'fixture_host_binding_changed')
        require(self.temperature_domain_k==tuple(s.temperature_domain_k for s in pair.storages) and self.pressure_domain_pa==tuple(s.fluid_template.envelope.pressure_range_pa for s in pair.storages),'fixture_domain_binding_changed')
        require(type(self.volume_m3_mol) is F and self.volume_m3_mol>0,'fixture_volume')
        require(self.callback_code_hashes==tuple(hashlib.sha256(marshal.dumps(fn.__code__)).hexdigest() for fn in (*self.evaluators,*self.responses)),'fixture_callback_code_changed')
        for i,st in enumerate(pair.storages):
            functions=(st.water.state_tp.__func__,st.water.state_tp_response.__func__)
            require(functions==(self.evaluators[i],self.responses[i]),'fixture_callback_changed')
            for fn in functions:
                require(not fn.__module__.startswith('sludge_sandbox.'),'native_liquid_cannot_be_constant_fixture')
                require(getattr(fn,'constant_volume_temperature_domain_k',None)==self.temperature_domain_k[i] and getattr(fn,'constant_volume_pressure_domain_pa',None)==self.pressure_domain_pa[i],'fixture_callback_domain_declaration_required')
                require(getattr(fn,'manufactured_test_fixture',False) is True and type(getattr(fn,'constant_volume_m3_mol',None)) is F and fn.constant_volume_m3_mol==self.volume_m3_mol,'explicit_analytic_callback_declaration_required')


def pressure_radius(pair: WetPair, state: WetMixedState, inverse, cell: int,
                    fixture: ManufacturedConstantLiquidFixture | None, *, states=None, cell_rate=None,
                    pressure_session=None, query_context=None, caller_guard=None,
                    remaining_caller_wall=None) -> F:
    """Full inverse-temperature pressure enclosure for supported exact models."""
    st=pair.storages[cell];point=inverse.point
    t=exact(point.temperature_k);eps=exact(inverse.temperature_error_bound_k)
    require(eps>=0,'nonnegative_temperature_error')
    tlo,thi=t-eps,t+eps
    lo,hi=map(exact,st.temperature_domain_k)
    require(lo<=tlo<=thi<=hi,'inverse_temperature_interval_outside_domain')
    nl=exact(state.liquid_water_mol)
    if nl and pressure_session is not None:
        require(fixture is None,'native_pressure_and_fixture_are_exclusive')
        return _native_pressure_radius(pair,state,inverse,cell,states,cell_rate,pressure_session,query_context,caller_guard,remaining_caller_wall)
    if nl:
        require(type(fixture) is ManufacturedConstantLiquidFixture,'pressure_temperature_envelope_unavailable')
        fixture.check(pair)
        v=fixture.volume_m3_mol
        ev=exact(st.fluid_template.envelope.liquid_v_error_m3_mol)
    else:v=ev=F()
    available=exact(st.bulk_volume_m3)-sum((exact(m)*exact(s.volume_m3_kg) for m,s in zip(state.solid_mass_kg,st.solids)),F())
    volume_error=exact(st.bulk_volume_error_m3)
    vglo=available-volume_error-nl*(v+ev)
    vghi=available+volume_error-nl*(v-ev)
    require(0<vglo<=vghi,'positive_interval_gas_volume')
    nr=sum(map(exact,state.gas_amounts_mol),F())*exact(st.fluid_template.mechanical.gas_constant_j_mol_k)
    plo,phi=nr*tlo/vghi,nr*thi/vglo
    dl,dh=map(exact,st.fluid_template.envelope.pressure_range_pa)
    require(dl<=plo<=phi<=dh,'pressure_temperature_interval_outside_domain')
    # Preserve original fixed-T numerical certificate in addition to the
    # analytic temperature/volume interval; do not subtract shared errors.
    return max(abs(exact(point.pressure_pa)-plo),abs(exact(point.pressure_pa)-phi))+exact(point.pressure_error_pa)


@dataclass(frozen=True)
class Sample:
    role: str
    time: T
    state: tuple
    rates: WetRates
    source_binding: str
    interfaces: tuple


@dataclass(frozen=True)
class InventoryPolynomial:
    family: str
    cell: int
    index: int
    initial: F
    linear: F
    quadratic: F

    def minimum(self,duration: F) -> tuple[F, F]:
        require(type(duration) is F and duration>0,'exact_positive_panel_duration')
        for value in (self.initial,self.linear,self.quadratic):require(type(value) is F,'exact_polynomial_coefficients')
        points=[F(),duration]
        if self.quadratic>0:
            vertex=-self.linear/(2*self.quadratic)
            if 0<vertex<duration:points.append(vertex)
        return min((self.initial+self.linear*t+self.quadratic*t*t,t) for t in points)


@dataclass(frozen=True)
class AffinePanel:
    start: T
    midpoint: T
    end: T
    source_binding: str
    interfaces: tuple
    initial_state: tuple
    start_sample: Sample
    midpoint_sample: Sample
    component_coefficients: tuple
    inventories: tuple
    minimum_inventory: tuple


@dataclass(frozen=True)
class ExactMixedLedger:
    start: T
    end: T
    exact_integrals: tuple
    represented_integrals: tuple
    integral_roundoff: tuple


@dataclass(frozen=True)
class StepTrial:
    start: T
    end: T
    initial_state: tuple
    predictor_state: tuple
    endpoint_state: tuple
    panel: AffinePanel
    ledger: ExactMixedLedger
    endpoint_sample: Sample


@dataclass(frozen=True)
class EndpointAttempt:
    role: str
    time: T
    endpoint_state: tuple
    panel: AffinePanel
    ledger: ExactMixedLedger


@dataclass(frozen=True)
class MixedTrialResult:
    status: str
    reason: str | None
    initial_state: tuple
    start: T
    end: T
    candidate_state: tuple | None
    steps: tuple
    samples: tuple
    panels: tuple
    predictor_states: tuple
    endpoint_attempts: tuple
    comparisons: tuple
    evaluations_attempted: int
    evaluations_completed: int
    elapsed_seconds: float
    qualification: str='autonomous_local_trials_only_no_global_commit_no_event_admission'


@dataclass(frozen=True)
class NativePressureQueryContext:
    role: str
    time: T
    source_binding: str
    interfaces: tuple
    original_initial: tuple
    stage_start: T
    stage_end: T
    stage_policy: MixedStagePolicy


@dataclass(frozen=True, kw_only=True)
class NativePressureMixedTrialResult(MixedTrialResult):
    """Explicit unsupported-by-legacy-codec local trial with full proof history."""
    original_stage_policy_json: bytes
    original_stage_inputs_json: bytes
    pressure_session_before: object
    pressure_session_after: object
    pressure_query_contexts: tuple
    native_schema: str = 'mixed_native_pressure_trial_v1'


def _native_pressure_radius(pair,state,inverse,cell,states,cell_rate,session,context,
                            caller_guard,remaining_caller_wall):
    from sludge_sandbox.mass_wet_pressure_session import PressureSession
    from sludge_sandbox.mass_wet_pressure_interval import encoded
    from sludge_sandbox.mass_wet_transport import WetCellRate
    require(type(session) is PressureSession,'explicit_pressure_session')
    require(type(cell) is int and cell in (0,1),'native_pressure_cell_index')
    require(type(states) is tuple and len(states)==2 and all(type(s) is WetMixedState for s in states), 'native_pressure_full_states')
    require(states[cell] is state and type(cell_rate) is WetCellRate and cell_rate.inverse is inverse,'native_pressure_actual_state_inverse')
    require(type(context) is NativePressureQueryContext,'explicit_native_pressure_context')
    require(context.role in ('full','fine') and type(context.time) is T and context.time==context.stage_end
            and type(context.stage_start) is T and context.stage_start<context.stage_end
            and type(context.stage_policy) is MixedStagePolicy,'native_pressure_comparison_time_role')
    require(context.source_binding==pair.binding() and context.interfaces==pair.interfaces,'native_pressure_comparison_source_modes')
    if caller_guard is not None:caller_guard()
    # Session retains the attempted query and all costs before status is checked.
    attempt=session.query(pair,states,cell_rate,cell,context=encoded((context,states,cell_rate,cell)),
                          caller_guard=caller_guard,remaining_caller_wall=remaining_caller_wall)
    if attempt.status!='proved_conditional_query':
        reason=attempt.reason or 'native_pressure_unresolved'
        error={'cancelled':InterruptedError,'resource_limit':TimeoutError,'domain_exit':DomainExit}.get(attempt.failure_kind,ValueError)
        raise error(reason)
    require(attempt.failure_kind is None and type(attempt.pressure_radius_pa) is F and attempt.pressure_radius_pa>=0,'proved_exact_native_pressure_radius')
    if caller_guard is not None:caller_guard()
    return attempt.pressure_radius_pa


def components(r: WetRates) -> tuple:
    require(type(r) is WetRates and len(r.cells)==2,'typed_actual_wet_rates')
    result=[]
    for i,c in enumerate(r.cells):
        require(len(c.solid_kg_s)==2 and len(c.reaction_gas_mol_s)==3,'complete_component_layout')
        result.extend(((('solid',i,j),exact(x)) for j,x in enumerate(c.solid_kg_s)))
        result.extend(((('chemical_gas',i,j),exact(x)) for j,x in enumerate(c.reaction_gas_mol_s)))
        result.append((('phase_water',i),exact(c.phase_water_mol_s)))
    require(tuple(r.exchange.net_mol_s)==('O2','N2','H2O'),'full_gas_face_layout')
    result.extend(((('face_species',j),exact(r.exchange.net_mol_s[k])) for j,k in enumerate(('O2','N2','H2O'))))
    result.append((('heat',),exact(r.conduction_w)))
    require(len(r.diffusive_enthalpy_w)==len(r.advective_enthalpy_w)==3,'full_energy_component_layout')
    result.extend(((('diffusion_energy',j),exact(v)) for j,v in enumerate(r.diffusive_enthalpy_w)))
    result.extend(((('advection_energy',j),exact(v)) for j,v in enumerate(r.advective_enthalpy_w)))
    result.append((('face_energy',),exact(r.face_energy_w)))
    return tuple(result)


def inventory_derivatives(values: tuple) -> tuple:
    c=dict(values);result=[]
    for i,sign in enumerate((-1,1)):
        for j in range(2):result.append((('solid',i,j),c['solid',i,j]))
        result.append((('liquid',i,0),-c['phase_water',i]))
        for j in range(3):result.append((('gas',i,j),c['chemical_gas',i,j]+sign*c['face_species',j]+(c['phase_water',i] if j==2 else 0)))
    return tuple(result)


def initial_value(states: tuple, key: tuple) -> F:
    family,i,j=key;s=states[i]
    return exact(s.solid_mass_kg[j] if family=='solid' else s.liquid_water_mol if family=='liquid' else s.gas_amounts_mol[j])


def build_panel(first: Sample, middle: Sample, end: T) -> AffinePanel:
    require(type(first) is Sample and type(middle) is Sample and type(end) is T,'typed_panel_samples')
    h=end.elapsed_since(first.time)
    require(h>0 and middle.time.elapsed_since(first.time)==h/2,'exact_shared_midpoint')
    require(first.source_binding==middle.source_binding and first.interfaces==middle.interfaces,'shared_sample_source_modes')
    a=components(first.rates);b=components(middle.rates)
    require(tuple(k for k,v in a)==tuple(k for k,v in b),'component_schema_changed')
    coeff=tuple((k,x,2*(y-x)/h) for (k,x),(_,y) in zip(a,b))
    da=inventory_derivatives(a);db=inventory_derivatives(b)
    polynomials=tuple(InventoryPolynomial(*k,initial_value(first.state,k),x,(y-x)/h) for (k,x),(_,y) in zip(da,db))
    minima=tuple((p.family,p.cell,p.index,*p.minimum(h)) for p in polynomials)
    return AffinePanel(first.time,middle.time,end,first.source_binding,first.interfaces,first.state,first,middle,coeff,polynomials,minima)


def validate_positive_panel(panel: AffinePanel) -> None:
    """Ordinary autonomous panel: wet stays positive; dry is identically zero."""
    require(type(panel) is AffinePanel and len(panel.inventories)==12,'complete_typed_inventory_panel')
    require(type(panel.interfaces) is tuple and len(panel.interfaces)==2 and all(m in ('existing_liquid','depleted_no_nucleation') for m in panel.interfaces),'explicit_panel_modes')
    expected=tuple((family,i,j) for i in range(2) for family,count in (('solid',2),('liquid',1),('gas',3)) for j in range(count))
    require(tuple((p.family,p.cell,p.index) for p in panel.inventories)==expected,'complete_inventory_panel_layout')
    minima=tuple((p.family,p.cell,p.index,*p.minimum(panel.end.elapsed_since(panel.start))) for p in panel.inventories)
    require(minima==panel.minimum_inventory,'inventory_minima_binding')
    for polynomial,row in zip(panel.inventories,minima):
        if polynomial.family=='liquid':
            if panel.interfaces[polynomial.cell]=='existing_liquid':
                require(row[3]>0,'ordinary_wet_panel_requires_strict_positive_liquid')
            else:
                require(polynomial.initial==polynomial.linear==polynomial.quadratic==0,'dry_panel_requires_identically_zero_liquid')
        else:require(row[3]>=0,'whole_panel_negative_inventory')


def make_ledger(start: T, end: T, rates: WetRates) -> ExactMixedLedger:
    h=end.elapsed_since(start);require(h>0,'positive_exact_step')
    integrals=tuple((k,h*v) for k,v in components(rates))
    represented_values=tuple((k,represented(v)) for k,v in integrals)
    return ExactMixedLedger(start,end,integrals,represented_values,tuple((k,exact(w)-v) for (k,v),(_,w) in zip(integrals,represented_values)))


def advance(pair: WetPair, states: tuple, ledger: ExactMixedLedger) -> tuple:
    d=dict(ledger.represented_integrals);result=[]
    for i,(st,s,sign) in enumerate(zip(pair.storages,states,(-1,1))):
        masses=tuple(exact(v)+exact(d['solid',i,j]) for j,v in enumerate(s.solid_mass_kg))
        liquid=exact(s.liquid_water_mol)-exact(d['phase_water',i])
        gases=tuple(exact(v)+exact(d['chemical_gas',i,j])+sign*exact(d['face_species',j])+(exact(d['phase_water',i]) if j==2 else 0) for j,v in enumerate(s.gas_amounts_mol))
        require(all(v>=0 for v in (*masses,liquid,*gases)),'negative_trial_inventory')
        result.append(st.state(tuple(map(represented,masses)),represented(liquid),tuple(map(represented,gases)),represented(exact(s.internal_energy_j)+sign*exact(d['face_energy',]))))
    return tuple(result)


def try_step_doubling(pair: WetPair, initial: tuple, *, start: T, end: T, policy: MixedStagePolicy, cancel: Callable[[], bool] | None=None, constant_liquid_fixture: ManufacturedConstantLiquidFixture | None=None, pressure_session=None) -> MixedTrialResult:
    """Full-vs-two-half local attempt; returned candidate still is not a commit."""
    require(type(pair) is WetPair and type(policy) is MixedStagePolicy,'typed_mixed_trial_inputs')
    require(type(start) is T and type(end) is T and end>start,'exact_ordered_times')
    require(type(initial) is tuple and len(initial)==2 and all(type(s) is WetMixedState for s in initial),'two_initial_states')
    session_before=None;pressure_contexts=[];stage_policy_json=None;stage_inputs_json=None
    if pressure_session is not None:
        from sludge_sandbox.mass_wet_pressure_session import PressureSession
        require(type(pressure_session) is PressureSession,'explicit_pressure_session')
        require(constant_liquid_fixture is None,'native_pressure_and_fixture_are_exclusive')
        from sludge_sandbox.mass_wet_pressure_interval import encoded
        stage_policy_json=encoded(policy)
        stage_inputs_json=encoded((initial,start,end,policy))
        session_before=pressure_session.snapshot()
    h=end.elapsed_since(start);origin=time.monotonic();attempted=completed=0;samples=[];panels=[];steps=[];predictors=[];endpoint_attempts=[];comparison=();candidate=None
    source=pair.binding();modes=pair.interfaces
    def guard():
        if pressure_session is not None:
            require(encoded(policy)==stage_policy_json,'native_original_stage_policy_changed')
            require(encoded((initial,start,end,policy))==stage_inputs_json,'native_original_stage_inputs_changed')
        require(pair.binding()==source and pair.interfaces==modes,'trial_source_or_mode_changed')
        if constant_liquid_fixture is not None:constant_liquid_fixture.check(pair)
        if cancel is not None and cancel():raise InterruptedError('cancel_requested')
        if time.monotonic()-origin>float(policy.maximum_wall_seconds):raise TimeoutError('trial_wall_budget')
    def evaluate(s,t,role):
        nonlocal attempted,completed
        guard()
        if attempted>=policy.maximum_evaluations:raise TimeoutError('trial_evaluation_budget')
        attempted+=1;r=pair.evaluate(s);completed+=1
        sample=Sample(role,t,s,r,source,modes);samples.append(sample);guard();return sample
    def step(s,a,b,label):
        f=evaluate(s,a,label+':start');mid=T(a.seconds+b.elapsed_since(a)/2)
        predictor=advance(pair,s,make_ledger(a,mid,f.rates))
        predictors.append((label,mid,predictor))
        m=evaluate(predictor,mid,label+':midpoint')
        panel=build_panel(f,m,b);panels.append(panel)
        validate_positive_panel(panel)
        ledger=make_ledger(a,b,m.rates)
        for (key,r0,slope),(other,value) in zip(panel.component_coefficients,ledger.exact_integrals):
            require(key==other and r0*(b.elapsed_since(a))+slope*(b.elapsed_since(a))**2/2==value,'affine_integral_binding')
        new=advance(pair,s,ledger)
        endpoint_attempts.append(EndpointAttempt(label,b,new,panel,ledger))
        last=evaluate(new,b,label+':endpoint')
        out=StepTrial(a,b,s,predictor,new,panel,ledger,last);steps.append(out);return out
    status='accepted';reason=None
    try:
        guard()
        require(exact(policy.minimum_step_s)<=h/2 and h<=exact(policy.maximum_step_s),'step_doubling_outside_declared_step_domain')
        whole=step(initial,start,end,'full');middle=T(start.seconds+h/2)
        half1=step(initial,start,middle,'half1');half2=step(half1.endpoint_state,middle,end,'half2')
        full=whole.endpoint_state;fine=half2.endpoint_state
        mass=max(abs(exact(a)-exact(b)) for x,y in zip(full,fine) for a,b in zip(x.solid_mass_kg,y.solid_mass_kg))
        amount=max(abs(exact(a)-exact(b)) for x,y in zip(full,fine) for a,b in zip((x.liquid_water_mol,*x.gas_amounts_mol),(y.liquid_water_mol,*y.gas_amounts_mol)))
        energy=max(abs(exact(x.internal_energy_j)-exact(y.internal_energy_j)) for x,y in zip(full,fine))
        temp=F();pressure=F()
        for i,(a,b) in enumerate(zip(whole.endpoint_sample.rates.cells,half2.endpoint_sample.rates.cells)):
            temp=max(temp,abs(exact(a.inverse.point.temperature_k)-exact(b.inverse.point.temperature_k))+exact(a.inverse.temperature_error_bound_k)+exact(b.inverse.temperature_error_bound_k))
            if pressure_session is None:
                pressure=max(pressure,abs(exact(a.inverse.point.pressure_pa)-exact(b.inverse.point.pressure_pa))+pressure_radius(pair,full[i],a.inverse,i,constant_liquid_fixture)+pressure_radius(pair,fine[i],b.inverse,i,constant_liquid_fixture))
            else:
                radii=[]
                for role,states,sample,rate in (('full',full,whole.endpoint_sample,a),('fine',fine,half2.endpoint_sample,b)):
                    require(sample.state is states and sample.rates.cells[i] is rate and sample.time==end,'native_pressure_actual_endpoint_sample')
                    context=NativePressureQueryContext(role,sample.time,sample.source_binding,sample.interfaces,initial,start,end,policy)
                    pressure_contexts.append(context)
                    radii.append(pressure_radius(pair,states[i],rate.inverse,i,None,states=states,cell_rate=rate,
                        pressure_session=pressure_session,query_context=context,caller_guard=guard,
                        remaining_caller_wall=lambda:float(policy.maximum_wall_seconds)-(time.monotonic()-origin)))
                pressure=max(pressure,abs(exact(a.inverse.point.pressure_pa)-exact(b.inverse.point.pressure_pa))+sum(radii,F()))
        time_error=abs(whole.end.elapsed_since(half2.end))
        comparison=tuple(zip(('solid_kg','amount_mol','energy_j','temperature_k','pressure_pa','time_s'),(mass,amount,energy,temp,pressure,time_error)))
        bounds=(policy.solid_mass_absolute_kg,policy.amount_absolute_mol,policy.energy_absolute_j,policy.temperature_absolute_k,policy.pressure_absolute_pa,policy.time_absolute_s)
        guard()
        if all(v<=exact(b) for (_,v),b in zip(comparison,bounds)):candidate=fine
        else:status='rejected';reason='full_vs_half_original_gates'
    except DomainExit as exc:status='domain_exit';reason=str(exc)
    except InterruptedError as exc:status='cancelled';reason=str(exc)
    except TimeoutError as exc:status='resource_limit';reason=str(exc)
    except (ValueError,OverflowError) as exc:status='failed';reason=str(exc)
    result=MixedTrialResult(status,reason,initial,start,end,candidate,tuple(steps),tuple(samples),tuple(panels),tuple(predictors),tuple(endpoint_attempts),comparison,attempted,completed,time.monotonic()-origin,
        qualification=('autonomous_local_trials_only_no_global_commit_no_event_admission'+(';manufactured_test_fixture_constant_liquid_only' if constant_liquid_fixture is not None else '')+(';conditional_native_pressure_proofs_original_material_envelopes' if pressure_session is not None else '')))

    if pressure_session is None:return result
    return NativePressureMixedTrialResult(**{f.name:getattr(result,f.name) for f in fields(MixedTrialResult)},
        original_stage_policy_json=stage_policy_json,original_stage_inputs_json=stage_inputs_json,pressure_session_before=session_before,pressure_session_after=pressure_session.snapshot(),
        pressure_query_contexts=tuple(pressure_contexts))
