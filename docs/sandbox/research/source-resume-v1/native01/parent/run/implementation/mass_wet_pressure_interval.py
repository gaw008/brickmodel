"""Explicit conditional single-query ordinary-liquid pressure research proof.

No native calls, global phase theorem, generic wet admission or consumer edits.
"""
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path
from collections.abc import Mapping, Callable
import hashlib
import inspect
import json
import math
import marshal
import time

from sludge_sandbox import water_interval_eos as eos
from sludge_sandbox import water_coexistence as coex
from sludge_sandbox import water_coupled_rectangle as coupled
from sludge_sandbox import water_density_tube as tube
from sludge_sandbox import water_native_output as native
from sludge_sandbox.mass_wet_transport import WetPair, WetCellRate
from sludge_sandbox.mass_wet_storage import WetMixedState, WetMixedInverse
from sludge_sandbox.water_heos import HEOSWaterProperties
from sludge_sandbox.water_properties import WaterState
from sludge_sandbox.deforming_solid_storage import _canonical
from sludge_sandbox.water_chemical_potential import WaterPhaseEquilibrium

OFFICIAL_SHA = '512879217b94f4d0741c88cab743d41098268914d538d73e680a736cb1c3aad7'
COEFFICIENT_SHA = 'a10a0da6c55e623cccc1f56a70cb348c772d8fc1710a6a142b459abb0dec4586'
PINS = ((eos,'28bcfac0829a4d7cf55a58a71a5ddf9383687872808525841f3f1395a90cedc0'),
        (coex,'0ed817e98bbbbc50b6273ce804b8d43c3a7a5ddce377d74cb68d10b6a3de7826'),
        (coupled,'b214102b545e1c6a54b0d4d2af91bedb673c2aff9208639fe20dcc56ef63d117'),
        (tube,'92f54fa6280d9d799e5500c90948a624b9548dddb39554b7667923bdf1b8723d'),
        (native,'38d9309ec3ae1f37e829a424c8f57d4ffa4f86fdbbbd6cc914dc266e9cace1ea'))
QUALIFICATION = 'conditional_native_liquid_pressure_interval_original_U_Cp_volume_assumptions_not_material_admission'


class PressureProofError(ValueError):
    """Unresolved or unsupported query; never an implicit fallback."""


def need(condition: object, reason: str) -> None:
    if not condition:
        raise PressureProofError(reason)


def sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def data(value: object) -> object:
    """Immutable evidence is stored as lossless JSON bytes, not live providers."""
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float:
        need(math.isfinite(value), 'finite_evidence_float')
        return {'float_hex': value.hex()}
    if type(value) is bytes: return {'bytes_hex':value.hex()}
    if type(value) is F: return {'fraction': [value.numerator, value.denominator]}
    if type(value) is D:
        need(value.is_finite(), 'finite_evidence_decimal')
        return {'decimal': str(value)}
    if is_dataclass(value):
        return {'type': type(value).__module__+'.'+type(value).__qualname__,
                'fields': {f.name: data(getattr(value,f.name)) for f in fields(value)}}
    if isinstance(value, Mapping):
        need(all(type(k) is str for k in value), 'string_evidence_keys')
        return {k:data(v) for k,v in value.items()}
    if type(value) in (tuple,list): return [data(v) for v in value]
    raise PressureProofError('unsupported_evidence_value:'+type(value).__name__)


def encoded(value: object) -> bytes:
    return json.dumps(data(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def identity(value: object) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def interval(value: object) -> eos.Interval:
    need(type(value) is eos.Interval and type(value.lo) is D and type(value.hi) is D,
         'explicit_decimal_interval')
    value.__post_init__()
    return value


def within(inner: eos.Interval, outer: eos.Interval) -> bool:
    return outer.lo<=inner.lo<=inner.hi<=outer.hi


@dataclass(frozen=True)
class LiquidBranchModelPolicy:
    official_pdf: str
    coefficient_json: str
    provider_descriptor_sha256: str
    temperature_domain_k: tuple[F,F] = (F(295),F(310))
    pressure_domain_pa: tuple[F,F] = (F(10000),F(10000000))
    model: str = 'iapws95_ordinary_water_liquid_branch'
    branch_interpretation: str = 'source_supported_model_selection'
    source_locator: str = 'IAPWS95-2018 sections 4-5 and Table 3'
    qualification: str = QUALIFICATION

    def __post_init__(self):
        need(self.model=='iapws95_ordinary_water_liquid_branch' and
             self.branch_interpretation=='source_supported_model_selection' and
             self.source_locator=='IAPWS95-2018 sections 4-5 and Table 3' and
             self.qualification==QUALIFICATION,'explicit_conditional_branch_model')
        for limits,allowed in ((self.temperature_domain_k,(F(295),F(310))),
                               (self.pressure_domain_pa,(F(10000),F(10000000)))):
            need(type(limits) is tuple and len(limits)==2 and all(type(v) is F for v in limits)
                 and allowed[0]<=limits[0]<limits[1]<=allowed[1],'limited_ordinary_liquid_domain')
        need(type(self.provider_descriptor_sha256) is str and len(self.provider_descriptor_sha256)==64
             and all(c in '0123456789abcdef' for c in self.provider_descriptor_sha256),'provider_sha256')
        need(type(self.official_pdf) is str and type(self.coefficient_json) is str,'explicit_source_paths')
        self.check_sources()

    def check_sources(self) -> tuple[str,...]:
        current=(sha(self.official_pdf),sha(self.coefficient_json),*(sha(m.__file__) for m,_ in PINS))
        need(current==(OFFICIAL_SHA,COEFFICIENT_SHA,*(pin for _,pin in PINS)), 'pinned_sources_changed')
        return current


@dataclass(frozen=True)
class ProofBudget:
    maximum_proof_operations: int
    maximum_boxes_per_primitive: int
    maximum_wall_seconds: float
    precision: int = 60

    def __post_init__(self):
        need(type(self.maximum_proof_operations) is int and self.maximum_proof_operations>=0,'proof_operation_budget')
        need(type(self.maximum_boxes_per_primitive) is int and self.maximum_boxes_per_primitive>=4,'primitive_box_budget')
        need(type(self.maximum_wall_seconds) is float and math.isfinite(self.maximum_wall_seconds)
             and self.maximum_wall_seconds>0,'positive_wall_budget')
        need(type(self.precision) is int and 40<=self.precision<=1000,'bounded_precision')


@dataclass(frozen=True)
class QueryBoxes:
    """Untrusted numerical proposals: every rectangle is proved afresh."""
    mechanical_density: eos.Interval
    observed_density: eos.Interval
    coexistence_log_density: tuple[eos.Interval,eos.Interval]
    center: tuple[D,D]
    preconditioner: tuple[tuple[D,D],tuple[D,D]]
    weights: tuple[D,D]

    def __post_init__(self):
        for x in (self.mechanical_density,self.observed_density):
            interval(x);need(0<x.lo<x.hi,'positive_nonzero_density_box')
        need(type(self.coexistence_log_density) is tuple and len(self.coexistence_log_density)==2,'two_coexistence_boxes')
        for x in self.coexistence_log_density: interval(x)
        need(type(self.center) is tuple and len(self.center)==2 and
             all(type(x) is D and x.is_finite() for x in self.center),'decimal_center')
        need(type(self.weights) is tuple and len(self.weights)==2 and
             all(type(x) is D and x.is_finite() and x>0 for x in self.weights),'positive_weighted_norm')
        need(type(self.preconditioner) is tuple and len(self.preconditioner)==2 and
             all(type(row) is tuple and len(row)==2 and all(type(x) is D and x.is_finite() for x in row)
                 for row in self.preconditioner),'decimal_preconditioner')


def _host_identity(pair: WetPair) -> str:
    need(type(pair) is WetPair,'actual_mixed_pair')
    binding=pair.binding()
    waters=tuple(st.water for st in pair.storages)+(pair.chemical.water,)
    for water in waters:
        need(type(water) is HEOSWaterProperties,'explicit_HEOS_hybrid_only')
        water._guard()
    callbacks=tuple((type(w).__module__,type(w).__qualname__,w.implementation,
                     sha(inspect.getfile(type(w))),
                     tuple((name,getattr(w,name).__func__.__module__,getattr(w,name).__func__.__qualname__,hashlib.sha256(marshal.dumps(getattr(w,name).__func__.__code__)).hexdigest())
                           for name in ('state_tp','state_tp_response'))) for w in waters)
    return identity((binding,_canonical(pair),callbacks))


@dataclass(frozen=True)
class BoundLiquidPressureRequest:
    """Actual rate + host references are rechecked before/after, not serialized live."""
    pair: WetPair
    states: tuple[WetMixedState,WetMixedState]
    rate: WetCellRate
    cell: int
    host_identity: str
    numeric_identity: str
    captured_query_json: bytes = b''
    captured_source_json: bytes = b''

    @classmethod
    def capture(cls,pair: WetPair,states: tuple,rate: WetCellRate,cell: int):
        need(type(cell) is int and cell in (0,1),'explicit_cell_index')
        need(type(states) is tuple and len(states)==2 and all(type(s) is WetMixedState for s in states),'complete_mixed_state')
        need(type(rate) is WetCellRate and type(rate.inverse) is WetMixedInverse,'actual_cell_rate_inverse')
        for st,state in zip(pair.storages,states):st.check(state)
        need(pair.interfaces[cell]=='existing_liquid' and states[cell].liquid_water_mol>0,'existing_liquid_query')
        return cls(pair,states,rate,cell,_host_identity(pair),identity((states,rate,cell)),
                   encoded((states,rate,cell)),encoded((_canonical(pair),tuple((type(st.water).__module__,type(st.water).__qualname__,st.water.implementation) for st in pair.storages),pair.chemical.water.implementation)))

    def check(self) -> None:
        need(type(self.cell) is int and self.cell in (0,1),'explicit_cell_index')
        need(type(self.captured_query_json) is bytes and self.captured_query_json==encoded((self.states,self.rate,self.cell)),'captured_actual_query_bytes')
        need(_host_identity(self.pair)==self.host_identity and identity((self.states,self.rate,self.cell))==self.numeric_identity,
             'actual_query_or_source_changed')
        need(type(self.captured_source_json) is bytes and self.captured_source_json==encoded((_canonical(self.pair),tuple((type(st.water).__module__,type(st.water).__qualname__,st.water.implementation) for st in self.pair.storages),self.pair.chemical.water.implementation)),'captured_actual_source_bytes')
        need(self.pair.interfaces[self.cell]=='existing_liquid','mode_changed')
        for st,state in zip(self.pair.storages,self.states):st.check(state)


@dataclass(frozen=True)
class QueryParameters:
    temperature: eos.Interval
    effective_volume: eos.Interval
    liquid_mol: float
    gas_mol: eos.Interval
    gas_constant: float
    public_native_scale: eos.Interval
    nominal_pressure_pa: float
    original_fixed_T_error_pa: float
    pressure_domain: eos.Interval
    observed_query: tuple
    inverse_error_required: F
    inverse_error_saved: F
    original_numeric_record: bytes


def inverse_temperature_interval(*,returned_temperature: float,total_energy: float,target_energy: float,
        energy_error: float,minimum_cp: float,epsilon: float,energy_tolerance: float,
        temperature_tolerance: float,domains: tuple,precision: int) -> tuple[eos.Interval,F]:
    """Original saved inverse hypotheses and complete interval, without EOS calls."""
    values=(returned_temperature,total_energy,target_energy,energy_error,minimum_cp,
            epsilon,energy_tolerance,temperature_tolerance)
    need(all(type(x) in (float,int) and math.isfinite(x) for x in values),'finite_original_inverse_scalars')
    need(energy_error>=0 and minimum_cp>0 and epsilon>=0 and energy_tolerance>0 and temperature_tolerance>0,
         'original_inverse_sign_conditions')
    residual=abs(F(total_energy)-F(target_energy))+F(energy_error)
    required=residual/F(minimum_cp)
    need(F(epsilon)>=required and residual<=F(energy_tolerance) and F(epsilon)<=F(temperature_tolerance),
         'original_inverse_energy_temperature_gates')
    need(type(precision) is int and 40<=precision<=1000,'bounded_precision')
    need(type(domains) is tuple and domains,'explicit_original_temperature_domains')
    with localcontext() as ctx:
        ctx.prec=precision
        t=eos.I(returned_temperature);e=eos.I(epsilon)
        temperature=eos.Interval((t-e).lo,(t+e).hi)
    for domain in domains:
        need(type(domain) is tuple and len(domain)==2 and
             all(type(x) in (float,int) and math.isfinite(x) for x in domain) and domain[0]<domain[1],
             'ordered_original_temperature_domain')
        need(within(temperature,eos.Interval(D(domain[0]),D(domain[1]))),'full_inverse_temperature_domain')
    return temperature,required


def parameters(request: BoundLiquidPressureRequest,policy: LiquidBranchModelPolicy,precision: int) -> QueryParameters:
    """No EOS: bind the full original U inverse and saved native observation."""
    request.check();policy.check_sources()
    pair=request.pair;cell=request.cell;state=request.states[cell];st=pair.storages[cell]
    inv=request.rate.inverse;p=inv.point;m=p.fluid.mechanical;water=st.water
    eq=request.rate.equilibrium
    need(type(eq) is WaterPhaseEquilibrium and type(eq.liquid.state) is WaterState,'actual_equilibrium_liquid_snapshot')
    w=eq.liquid.state
    need(p.model_identity==state.energy_model_identity==st._identity,'original_storage_model')
    need(w.implementation==water.implementation and water.implementation.sha256==policy.provider_descriptor_sha256
         and w.reference==water.reference and pair.chemical.water.implementation==water.implementation,'same_actual_water_source')
    descriptor=json.loads(water.implementation.canonical_descriptor)['real_fluid']
    coefficients=json.loads(Path(policy.coefficient_json).read_bytes())[0]['EOS'][0]
    mp=float.fromhex(descriptor['public_mass_hex']);mn=float.fromhex(descriptor['native_mass_hex'])
    need(descriptor['runtime']['fluid_sha256']==COEFFICIENT_SHA and mn==coefficients['molar_mass']
         and mp==w.reference.molar_mass_kg_mol and coefficients['gas_constant']==w.reference.native_molar_gas_constant_j_mol_k,
         'native_public_mass_and_R_binding')
    need(w.phase=='liquid' and w.method_id=='iapws95_real_fluid_helmholtz' and
         w.temperature_k==m.temperature_k and w.pressure_pa==m.liquid_pressure_pa==m.pressure_pa,
         'same_fixed_native_T_P_liquid_query')
    need(m.liquid_inventory_mol==state.liquid_water_mol and
         dict(m.gas_inventory_mol)==dict(zip(st.gas_ids,state.gas_amounts_mol)) and
         inv.target_energy_j==state.internal_energy_j and inv.energy_residual_j==float(F(p.total_internal_energy_j)-F(inv.target_energy_j)),'actual_inverse_inventory_target')
    need(m.gas_constant_j_mol_k==st.fluid_template.mechanical.gas_constant_j_mol_k and
         dict(m.source_asset_sha256)==dict(water.source_asset_sha256) and m.policy==st.fluid_template.mechanical.policy and p.fluid.envelope==st.fluid_template.envelope and m.liquid_native_molar_gas_constant_j_mol_k==water.reference.native_molar_gas_constant_j_mol_k,'original_mechanical_source_and_R')
    vs=sum((F(mass)*F(solid.volume_m3_kg) for mass,solid in zip(state.solid_mass_kg,st.solids)),F())
    exact_available=F(st.bulk_volume_m3)-vs
    need(exact_available>0 and p.available_pore_volume_m3==float(exact_available) and p.solid_volume_m3==float(vs),
         'actual_kg_solid_available_volume')
    need(m.gas_volume_m3==math.fsum((p.available_pore_volume_m3,-m.liquid_volume_m3)), 'actual_open_gas_volume')
    need(F(p.available_volume_error_m3)>=F(st.bulk_volume_error_m3)+abs(F(p.available_pore_volume_m3)-exact_available),
         'original_available_volume_error_not_shrunk')
    net=st.reference.network
    solid_terms=tuple(F(mass)*(h+F(solid.cp_j_kg_k)*(F(m.temperature_k)-net.reference_temperature_k)
                   -net.reference_pressure_pa*F(solid.volume_m3_kg))
                   for mass,solid,h in zip(state.solid_mass_kg,st.solids,st.reference.particular_h0_j_kg))
    total=F(p.fluid.internal_energy_j)+sum(solid_terms,F())
    need(p.total_internal_energy_j==float(total) and p.solid_internal_energy_j==tuple(map(float,solid_terms)),
         'original_common_total_U_binding')
    capacity_lower=F(p.fluid.minimum_heat_capacity_j_k)+sum((F(mass)*F(s.cp_j_kg_k) for mass,s in zip(state.solid_mass_kg,st.solids)),F())
    need(0<F(p.minimum_heat_capacity_j_k)<=capacity_lower,'original_Cp_lower_not_inflated')
    energy_error=F(p.fluid.energy_error_bound_j)+abs(F(p.total_internal_energy_j)-total)+F(state.liquid_water_mol)*F(st.fluid_template.envelope.liquid_abs_du_dp_bound_j_mol_pa)*F(p.extra_pressure_error_pa)
    need(F(p.extra_pressure_error_pa)>=0 and F(p.energy_error_j)>=energy_error,'original_total_U_error_not_shrunk')
    need(F(p.minimum_heat_capacity_j_k)>0 and F(p.energy_error_j)>=0 and F(p.pressure_error_pa)>=0,'original_positive_Cp_nonnegative_errors')
    ip=pair.inverse_policies[cell]
    temperature,required=inverse_temperature_interval(returned_temperature=m.temperature_k,
        total_energy=p.total_internal_energy_j,target_energy=inv.target_energy_j,
        energy_error=p.energy_error_j,minimum_cp=p.minimum_heat_capacity_j_k,
        epsilon=inv.temperature_error_bound_k,energy_tolerance=ip.energy_tolerance_j,
        temperature_tolerance=ip.temperature_tolerance_k,
        domains=(st.temperature_domain_k,st.fluid_template.envelope.temperature_range_k,inv.final_temperature_bracket_k),
        precision=precision)
    epsilon=F(inv.temperature_error_bound_k)
    with localcontext() as ctx:
        ctx.prec=precision
        need(F(temperature.lo)>=policy.temperature_domain_k[0] and F(temperature.hi)<=policy.temperature_domain_k[1],
             'ordinary_branch_temperature_domain')
        available=eos.I(st.bulk_volume_m3)
        for mass,solid in zip(state.solid_mass_kg,st.solids):available=available-eos.I(mass)*eos.I(solid.volume_m3_kg)
        nl=eos.I(state.liquid_water_mol);envelope=st.fluid_template.envelope
        need(st.bulk_volume_error_m3>=0 and envelope.liquid_v_error_m3_mol>0,'original_volume_error_contract')
        error=eos.I(st.bulk_volume_error_m3)+nl*eos.I(envelope.liquid_v_error_m3_mol)
        effective=eos.Interval((available-error).lo,(available+error).hi)
        pressure_domain=eos.Interval(max(D(envelope.pressure_range_pa[0]),D(st.fluid_template.mechanical.pressure_bracket_pa[0])),min(D(envelope.pressure_range_pa[1]),D(st.fluid_template.mechanical.pressure_bracket_pa[1])))
        lo=max(F(pressure_domain.lo),policy.pressure_domain_pa[0]);hi=min(F(pressure_domain.hi),policy.pressure_domain_pa[1])
        need(lo<=F(m.pressure_pa)<=hi,'ordinary_branch_pressure_domain')
        # Keep original exact Decimal envelope; model Fraction domain is checked separately.
        q=(w.temperature_k,w.pressure_pa,w.density_kg_m3,mp,mn,state.liquid_water_mol,m.liquid_volume_m3,envelope.liquid_v_error_m3_mol)
        need(all(type(v) is float and math.isfinite(v) and v>0 for v in q),'positive_actual_native_query')
        need((q[5]*q[3])/q[2]==q[6],'literal_original_host_liquid_volume')
        return QueryParameters(temperature,effective,state.liquid_water_mol,
            sum((eos.I(v) for v in state.gas_amounts_mol),eos.I(0)),m.gas_constant_j_mol_k,
            eos.I(mp)/eos.I(mn),m.pressure_pa,p.pressure_error_pa,pressure_domain,q,required,epsilon,
            encoded({'state':state,'rate':request.rate,'cell':cell,'interfaces':pair.interfaces,
                     'envelope':st.fluid_template.envelope,'inverse_policy':ip,'storage_source':_canonical(st),
                     'pair_source':_canonical(pair),'provider_concrete_type':(type(water).__module__,type(water).__qualname__),
                     'host_identity':request.host_identity,'mechanical_policy':m.policy}))


@dataclass(frozen=True)
class ProofOperation:
    name: str
    status: str
    elapsed_seconds: float
    evidence_json: bytes | None
    reason: str | None


@dataclass(frozen=True)
class LiquidPressureEvidence:
    status: str
    reason: str | None
    request_sha256: str
    pressure_radius_pa: F | None
    parameters_json: bytes | None
    operations: tuple[ProofOperation,...]
    attempted_proof_operations: int
    completed_proof_operations: int
    elapsed_seconds: float
    budget: ProofBudget
    source_before: tuple[str,...]
    source_after: tuple[str,...] | None
    policy_json: bytes
    proposals_json: bytes
    original_query_json: bytes
    original_source_json: bytes
    qualification: str = QUALIFICATION
    bottom_level_residual_evaluation_count: None = None
    native_calls: int = 0
    consumer_admission: bool = False


def connected_tube_density(coexistence_density: eos.Interval, mechanical_density: eos.Interval,
                           observed_density: eos.Interval, observed_native_density: eos.Interval) -> eos.Interval:
    """The entire union is reproved; disjoint endpoint boxes confer no proof."""
    boxes=(coexistence_density,mechanical_density,observed_density,observed_native_density)
    for box in boxes:interval(box)
    need(coexistence_density.hi<mechanical_density.lo,'liquid_coexistence_below_mechanical_root')
    need(within(observed_native_density,observed_density),'actual_native_density_in_fixed_query_box')
    return eos.Interval(min(b.lo for b in boxes),max(b.hi for b in boxes))


def pressure_radius_checked(nominal: float, pressure: eos.Interval, fixed_error: float,
                            pressure_domain: eos.Interval, model_domain: tuple[F,F],
                            saturation: eos.Interval) -> F:
    """Exact outward radius and the unchanged original ambiguity convention."""
    for box in (pressure,pressure_domain,saturation):interval(box)
    need(type(nominal) is float and math.isfinite(nominal) and type(fixed_error) is float
         and math.isfinite(fixed_error) and fixed_error>=0,'finite_pressure_error')
    need(type(model_domain) is tuple and len(model_domain)==2 and all(type(v) is F for v in model_domain) and model_domain[0]<model_domain[1],'exact_model_pressure_domain')
    lower=F(pressure.lo)-F(fixed_error);upper=F(pressure.hi)+F(fixed_error)
    need(F(pressure_domain.lo)<=lower<=upper<=F(pressure_domain.hi) and model_domain[0]<=lower<=upper<=model_domain[1],
         'full_pressure_interval_inside_original_domain')
    ambiguity=max(F(0.01),F(2e-8)*F(saturation.hi))
    need(F(pressure.lo)>F(saturation.hi)+ambiguity,'strict_original_saturation_ambiguity')
    return max(abs(F(nominal)-F(pressure.lo)),abs(F(nominal)-F(pressure.hi)))+F(fixed_error)


class IAPWS95LiquidPressureProvider:
    """Concrete pinned mathematical implementation; no pressure callback input."""

    def evaluate(self, request: BoundLiquidPressureRequest, *, branch_policy: LiquidBranchModelPolicy,
                 boxes: QueryBoxes, budget: ProofBudget,
                 cancel: Callable[[],bool] | None=None) -> LiquidPressureEvidence:
        need(type(request) is BoundLiquidPressureRequest and type(branch_policy) is LiquidBranchModelPolicy
             and type(boxes) is QueryBoxes and type(budget) is ProofBudget,'explicit_typed_query_contract')
        begun=time.monotonic();operations=[];attempted=completed=0
        original_policy_json=encoded(branch_policy);original_proposals_json=encoded(boxes)
        original_request_sha256=request.numeric_identity
        original_query_json=request.captured_query_json
        original_source_json=request.captured_source_json
        need(type(original_request_sha256) is str and type(original_query_json) is bytes
             and type(original_source_json) is bytes,'immutable_original_request_snapshot')
        limits=ProofBudget(**{f.name:getattr(budget,f.name) for f in fields(budget)})
        before=();after=None;params=None;radius=None;status='unresolved';reason=None
        stage='preflight'
        def snapshot():
            request.check()
            return (request.host_identity,request.numeric_identity,identity(branch_policy),identity(boxes),identity(budget),
                    *branch_policy.check_sources())
        def guard():
            need(cancel is None or not cancel(),'cancelled')
            need(time.monotonic()-begun<=limits.maximum_wall_seconds,'cumulative_proof_wall_budget')
            need(snapshot()==before,'source_or_request_changed')
        def remaining():
            guard()
            value=limits.maximum_wall_seconds-(time.monotonic()-begun)
            need(value>0,'cumulative_proof_wall_budget')
            return value
        def operation(name,call):
            nonlocal attempted,completed,stage
            guard();need(attempted<limits.maximum_proof_operations,'proof_operation_budget_exhausted')
            stage=name;attempted+=1;start=time.monotonic()
            try:
                value=call();completed+=1
                raw=encoded(value)
                operations.append(ProofOperation(name,'completed',time.monotonic()-start,raw,None))
            except Exception as exc:
                operations.append(ProofOperation(name,'failed',time.monotonic()-start,None,type(exc).__name__+': '+str(exc)))
                raise
            guard();return value
        try:
            branch_policy.__post_init__();budget.__post_init__();boxes.__post_init__()
            before=snapshot();guard()
            params=parameters(request,branch_policy,limits.precision);guard()
            source=branch_policy.coefficient_json
            with localcontext() as context:
                context.prec=limits.precision
                coexistence=operation('coexistence',lambda:coex.enclose_coexistence(
                    source,COEFFICIENT_SHA,params.temperature,boxes.coexistence_log_density,
                    boxes.center,boxes.preconditioner,precision=limits.precision,weights=boxes.weights))
                need(coexistence.proved and coexistence.pressure is not None,'coexistence_unresolved')
                mechanical=operation('coupled_mechanical_root',lambda:coupled.enclose_local_root(
                    source,COEFFICIENT_SHA,temperature=params.temperature,
                    liquid_molar_density=boxes.mechanical_density,effective_available_volume=params.effective_volume,
                    liquid_mol=params.liquid_mol,gas_mol=params.gas_mol,gas_constant=params.gas_constant,
                    liquid_volume_scale=params.public_native_scale,precision=limits.precision))
                q=params.observed_query
                observed_density=eos.I(q[2])/eos.I(q[4])
                density=connected_tube_density(coexistence.domain.density[0],boxes.mechanical_density,
                                               boxes.observed_density,observed_density)
                full_tube=operation('full_temperature_connected_density_tube',lambda:tube.prove_density_tube(
                    source,COEFFICIENT_SHA,params.temperature,density,precision=limits.precision,
                    maximum_boxes=limits.maximum_boxes_per_primitive,
                    maximum_wall_seconds=remaining()))
                need(full_tube.proved and full_tube.temperature==params.temperature and full_tube.density==density,
                     'whole_connected_density_tube_unresolved')
                observed=operation('observed_native_query',lambda:native.analyze(
                    q,boxes.observed_density,
                    pressure=lambda tt,rr:eos.pressure_interval(source,COEFFICIENT_SHA,tt,rr,precision=limits.precision),
                    binding=snapshot,maximum_boxes=limits.maximum_boxes_per_primitive,
                    maximum_wall_seconds=remaining()))
                need(observed['status']=='passed_observed_query','observed_native_volume_contract_unresolved')
                radius=pressure_radius_checked(params.nominal_pressure_pa,mechanical.pressure,
                    params.original_fixed_T_error_pa,params.pressure_domain,branch_policy.pressure_domain_pa,
                    coexistence.pressure)
                guard();status='proved_conditional_query'
        except Exception as exc:
            reason=stage+': '+type(exc).__name__+': '+str(exc)
            radius=None
        try:
            after=snapshot()
        except Exception as exc:
            status='unresolved';reason='final_binding: '+type(exc).__name__+': '+str(exc);radius=None
        elapsed=time.monotonic()-begun
        if after!=before or elapsed>limits.maximum_wall_seconds:
            status='unresolved';radius=None;reason=reason or 'final_source_or_cumulative_wall'
        return LiquidPressureEvidence(status,reason,original_request_sha256,radius,
            None if params is None else encoded(params),tuple(operations),attempted,completed,elapsed,limits,
            before,after,original_policy_json,original_proposals_json,original_query_json,original_source_json)
