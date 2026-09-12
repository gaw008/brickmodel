"""Versioned mixed kg/mol data record and offline consistency audit; no resume."""
from dataclasses import dataclass, fields
from collections.abc import Mapping
from types import MappingProxyType, UnionType
from fractions import Fraction as F
import hashlib
import json
import math
import typing
from sludge_sandbox import mass_wet_exact_controller as control
from sludge_sandbox import mass_wet_exact_stage as stage
from sludge_sandbox import mass_wet_exact_terminal as terminal
from sludge_sandbox import mass_wet_writeback as writeback
from sludge_sandbox import mass_wet_storage as storage
from sludge_sandbox import mass_wet_transport as transport
from sludge_sandbox import exact_affine_depletion as affine
from sludge_sandbox import exact_root_order as roots
from sludge_sandbox import depletion_roundoff as roundoff
from sludge_sandbox import water_chemical_potential as chemical
from sludge_sandbox.rigid_storage import ClosedStorageState, DeclaredNumericalEnvelope
from sludge_sandbox.rigid_water_gas import RigidWaterGasState, PressureTrialRecord, PressurePolicy
from sludge_sandbox.water_properties import WaterState, WaterReference
from sludge_sandbox.gas_transport import GasState, GasFaceExchange
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.deforming_solid_storage import _canonical

SCHEMA='mixed_kg_solid_mol_fluid_exact_run_record_v1'
CLASSES=(control.MixedControllerPolicy,control.MixedEventFrame,control.ObservationAttempt,
 control.MixedPath,control.MixedRefinement,control.MixedControllerResult,
 stage.MixedStagePolicy,stage.Sample,stage.InventoryPolynomial,stage.AffinePanel,
 stage.ExactMixedLedger,stage.StepTrial,stage.EndpointAttempt,stage.MixedTrialResult,
 terminal.MixedRootOrder,terminal.TerminalAttempt,
 writeback.MixedWritebackContext,writeback.MixedWritebackTotals,writeback.MixedCellPanelTerms,
 writeback.MixedTerminalEvidence,writeback.MixedWritebackRecord,writeback.MixedWritebackCandidate,
 storage.WetMixedState,storage.WetMixedPoint,storage.WetMixedInverse,
 transport.WetCellRate,transport.WetRates,affine.ExactAffineSamples,affine.ExactAffineEvidence,
 roots.RootCandidate,roots.NoRootEvidence,roundoff.DepletionRoundoffPolicy,roundoff.DepletionRoundoffTotals,
 chemical.WaterPhaseEquilibrium,chemical.WaterVaporChemicalState,chemical.WaterLiquidChemicalState,
 DeclaredNumericalEnvelope,ClosedStorageState,RigidWaterGasState,PressureTrialRecord,PressurePolicy,WaterReference,WaterState,GasState,GasFaceExchange)
REGISTRY={c.__module__+'.'+c.__qualname__:c for c in CLASSES}


class MixedRecordError(ValueError):pass

class FrozenList(tuple):
    """Immutable representation retaining the JSON list-vs-tuple tag."""
    pass


def need(value: object,reason: str) -> None:
    if not value:raise MixedRecordError(reason)


def canonical(value: object) -> bytes:return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(raw: bytes) -> str:return hashlib.sha256(raw).hexdigest()


def digest(value: object) -> None:
    need(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'explicit_sha256')


@dataclass(frozen=True)
class Node:
    kind: str
    values: Mapping
    def __getattr__(self,key):
        try:return self.values[key]
        except KeyError as exc:raise AttributeError(key) from exc


@dataclass(frozen=True)
class MixedRunRecord:
    canonical_bytes: bytes
    binding: object
    result: Node
    qualification: str='mixed_data_record_not_source_authentication_native_physics_or_resume'
    @property
    def sha256(self):return sha(self.canonical_bytes)


@dataclass(frozen=True)
class MixedReplayAudit:
    status: str
    record_sha256: str
    accepted_steps: int
    refinements: int
    checked_path_steps: int
    checked_projections: int
    unknown_checks: tuple
    resume_allowed: bool=False
    qualification: str='offline_data_consistency_not_solver_reexecution_or_native_validation'


def pack(value: object) -> object:
    if value is None or type(value) in (str,int,bool):return value
    if type(value) is float:
        need(math.isfinite(value),'finite_float');return {'float_hex':value.hex()}
    if type(value) is F:return {'fraction':[value.numerator,value.denominator]}
    if type(value) is T:return {'time':value.to_record()}
    if type(value) is transport.WetPair:
        # Preserve failure evidence without invoking a potentially failed guard.
        return {'operator_reference':{'constructor_identity':value._identity,'captured_modes':list(value.interfaces)}}
    if type(value) is Node and value.kind=='operator_reference':return {'operator_reference':{'constructor_identity':value.constructor_identity,'captured_modes':list(value.captured_modes)}}
    if type(value) is FrozenList:return {'list':[pack(v) for v in value]}
    if type(value) is Node:return {'record':value.kind,'fields':{k:pack(v) for k,v in value.values.items()}}
    if type(value) in CLASSES:
        return {'record':type(value).__module__+'.'+type(value).__qualname__,'fields':{f.name:pack(getattr(value,f.name)) for f in fields(value)}}
    if isinstance(value,Mapping):
        need(all(type(k) is str for k in value),'string_mapping_keys')
        return {'mapping':{k:pack(v) for k,v in value.items()}}
    if type(value) is tuple:return {'tuple':[pack(v) for v in value]}
    if type(value) is list:return {'list':[pack(v) for v in value]}
    raise MixedRecordError('unsupported_record_type:'+type(value).__name__)


def match(value: object,hint: object) -> bool:
    if hint is typing.Any or hint is object:return True
    if hint is type(None):return value is None
    origin=typing.get_origin(hint);args=typing.get_args(hint)
    if origin is typing.Literal:return any(type(value) is type(v) and value==v for v in args)
    if origin in (typing.Union,UnionType):return any(match(value,h) for h in args)
    if hint is float:return type(value) in (int,float)
    if hint is tuple:return type(value) is tuple
    if origin is tuple:
        if type(value) is not tuple:return False
        if len(args)==2 and args[1] is Ellipsis:return all(match(v,args[0]) for v in value)
        return len(value)==len(args) and all(match(v,h) for v,h in zip(value,args))
    if hint in CLASSES:return type(value) is Node and value.kind==hint.__module__+'.'+hint.__qualname__
    if hint is transport.WetPair:return type(value) is Node and value.kind=='operator_reference'
    if origin in (dict,Mapping) or hint is Mapping:return isinstance(value,Mapping)
    return isinstance(value,hint) if hint not in (int,bool,F,T,str) else type(value) is hint


def unpack(value: object) -> object:
    if value is None or type(value) in (str,int,bool):return value
    need(type(value) is dict,'tagged_value_required')
    if set(value)=={'float_hex'}:
        need(type(value['float_hex']) is str,'float_hex_string')
        try:out=float.fromhex(value['float_hex'])
        except ValueError as exc:raise MixedRecordError('invalid_float_hex') from exc
        need(math.isfinite(out) and out.hex()==value['float_hex'],'canonical_finite_float');return out
    if set(value)=={'fraction'}:
        row=value['fraction'];need(type(row) is list and len(row)==2 and all(type(x) is int for x in row) and row[1]>0,'exact_fraction_pair')
        out=F(*row);need([out.numerator,out.denominator]==row,'reduced_fraction');return out
    if set(value)=={'time'}:return T.from_record(value['time'])
    if set(value)=={'tuple'} or set(value)=={'list'}:
        key=next(iter(value));need(type(value[key]) is list,'sequence_payload')
        values=tuple(unpack(v) for v in value[key]);return values if key=='tuple' else FrozenList(values)
    if set(value)=={'mapping'}:
        need(type(value['mapping']) is dict and all(type(k) is str for k in value['mapping']),'mapping_payload')
        return MappingProxyType({k:unpack(v) for k,v in value['mapping'].items()})
    if set(value)=={'operator_reference'}:
        r=value['operator_reference'];need(type(r) is dict and set(r)=={'constructor_identity','captured_modes'},'operator_reference_fields')
        digest(r['constructor_identity']);need(type(r['captured_modes']) is list and len(r['captured_modes'])==2 and all(m in ('existing_liquid','depleted_no_nucleation') for m in r['captured_modes']),'operator_mode_layout')
        return Node('operator_reference',MappingProxyType({'constructor_identity':r['constructor_identity'],'captured_modes':tuple(r['captured_modes'])}))
    need(set(value)=={'record','fields'} and value['record'] in REGISTRY,'known_mixed_record_kind')
    cls=REGISTRY[value['record']];payload=value['fields']
    need(type(payload) is dict and set(payload)=={f.name for f in fields(cls)},'complete_record_fields')
    values={k:unpack(v) for k,v in payload.items()};hints=typing.get_type_hints(cls)
    for k,hint in hints.items():
        if k in values:need(match(values[k],hint),'field_type:'+cls.__name__+'.'+k)
    return Node(value['record'],MappingProxyType(values))


def equal(a: object,b: object) -> bool:return canonical(pack(a))==canonical(pack(b))


def capture_binding(pair: transport.WetPair,initial: tuple[storage.WetMixedState, storage.WetMixedState],*,start: T,end: T,stage_policy: stage.MixedStagePolicy,roundoff_policy: roundoff.DepletionRoundoffPolicy,
        original_liquid_fraction_limit: F,controller_policy: control.MixedControllerPolicy,case_sha256: str,runtime_identity: Mapping,
        constant_liquid_fixture: stage.ManufacturedConstantLiquidFixture | None=None) -> bytes:
    """Capture externally retained original binding BEFORE running the controller."""
    need(type(pair) is transport.WetPair and pair.binding()==pair._identity,'fresh_original_host')
    digest(case_sha256)
    need(isinstance(runtime_identity,Mapping) and runtime_identity,'explicit_external_runtime_identity')
    for value,cls in ((stage_policy,stage.MixedStagePolicy),(roundoff_policy,roundoff.DepletionRoundoffPolicy),(controller_policy,control.MixedControllerPolicy)):
        need(type(value) is cls,'typed_original_policy')
        cls(**{f.name:getattr(value,f.name) for f in fields(cls) if f.init})
    need(type(original_liquid_fraction_limit) is F and 0<original_liquid_fraction_limit<=F('1e-8'),'original_fraction_limit')
    for state,st in zip(initial,pair.storages):st.check(state)
    need(type(initial) is tuple and len(initial)==2 and type(start) is T and type(end) is T and start<end,'original_request_shape')
    if constant_liquid_fixture is not None:constant_liquid_fixture.check(pair)
    declaration=None if constant_liquid_fixture is None else {
        'qualification':constant_liquid_fixture.qualification,
        'constant_volume_m3_mol':constant_liquid_fixture.volume_m3_mol,
        'temperature_domain_k':constant_liquid_fixture.temperature_domain_k,
        'pressure_domain_pa':constant_liquid_fixture.pressure_domain_pa,
        'callback_code_hashes':constant_liquid_fixture.callback_code_hashes,
    }
    return canonical(pack({'case_sha256':case_sha256,'runtime_identity':runtime_identity,
        'operator_identity':pair._identity,'operator_source_content':_canonical(pair),
        'source_ids':terminal.source_labels(pair),'original_modes':pair.interfaces,
        'pressure_fixture':declaration,'request':dict(original_initial=initial,original_start=start,
        original_end=end,stage_policy=stage_policy,roundoff_policy=roundoff_policy,
        original_liquid_fraction_limit=original_liquid_fraction_limit,controller_policy=controller_policy)}))


def encode_mixed_run(result: control.MixedControllerResult,*,original_binding: bytes) -> bytes:
    need(type(result) is control.MixedControllerResult and type(original_binding) is bytes,'explicit_mixed_capture')
    binding=unpack(json.loads(original_binding))
    for key,value in binding['request'].items():need(equal(getattr(result,key),value),'original_request_changed:'+key)
    raw=canonical({'schema':SCHEMA,'binding':json.loads(original_binding),'result':pack(result)})
    read_mixed_run(raw,expected_binding=original_binding)
    return raw


def read_mixed_run(raw: bytes,*,expected_binding: bytes | None=None) -> MixedRunRecord:
    need(type(raw) is bytes,'raw_bytes_required')
    def unique(pairs):
        d={}
        for k,v in pairs:need(k not in d,'duplicate_json_key');d[k]=v
        return d
    try:obj=json.loads(raw,object_pairs_hook=unique)
    except (ValueError,UnicodeError) as exc:raise MixedRecordError('invalid_json') from exc
    need(type(obj) is dict and set(obj)=={'schema','binding','result'} and obj['schema']==SCHEMA,'mixed_record_envelope')
    need(canonical(obj)==raw,'canonical_bytes_required')
    if expected_binding is not None:need(type(expected_binding) is bytes and canonical(obj['binding'])==expected_binding,'external_original_binding_mismatch')
    binding=unpack(obj['binding']);result=unpack(obj['result'])
    need(type(result) is Node and result.kind==control.MixedControllerResult.__module__+'.MixedControllerResult','mixed_controller_result_required')
    need(set(binding)=={'case_sha256','runtime_identity','operator_identity','operator_source_content','source_ids','original_modes','pressure_fixture','request'},'complete_original_binding')
    digest(binding['case_sha256']);digest(binding['operator_identity'])
    need(set(binding['request'])=={'original_initial','original_start','original_end','stage_policy','roundoff_policy','original_liquid_fraction_limit','controller_policy'},'complete_original_request')
    for key,value in binding['request'].items():need(key in result.values and equal(result.values[key],value),'original_request_changed:'+key)
    return MixedRunRecord(raw,binding,result)


def restore_proof(node):
    """Fixed data-only mathematical proof constructors; never restore a host."""
    allowed=(storage.WetMixedState,writeback.MixedCellPanelTerms,writeback.MixedTerminalEvidence,
        writeback.MixedWritebackContext,writeback.MixedWritebackTotals,
        roundoff.DepletionRoundoffPolicy,roundoff.DepletionRoundoffTotals,
        affine.ExactAffineSamples,affine.ExactAffineEvidence)
    if type(node) is Node:
        cls=REGISTRY.get(node.kind);need(cls in allowed,'not_a_restorable_mathematical_proof')
        return cls(**{k:restore_proof(v) for k,v in node.values.items()})
    if type(node) is tuple:return tuple(restore_proof(v) for v in node)
    return node


def state_values(state):
    need(type(state) is Node and state.kind==storage.WetMixedState.__module__+'.WetMixedState','mixed_state_node')
    need(type(state.solid_mass_kg) is tuple and len(state.solid_mass_kg)==2 and type(state.gas_amounts_mol) is tuple and len(state.gas_amounts_mol)==3,'unit_separated_state_layout')
    digest(state.energy_model_identity)
    values=(*state.solid_mass_kg,state.liquid_water_mol,*state.gas_amounts_mol,state.internal_energy_j)
    need(all(type(v) is float and math.isfinite(v) for v in values),'represented_state_values')
    need(all(v>=0 for v in values[:-1]),'nonnegative_inventory_state')
    return tuple(map(F,values))


def costs(row):
    need(type(row) is tuple and all(type(p) is tuple and len(p)==2 for p in row),'cost_pairs')
    d=dict(row)
    names={'evaluations_attempted','evaluations_completed','ordinary_trials','ordinary_rejected','terminal_attempts','panel_attempts','observation_attempts','observation_completed'}
    need(set(d)==names and len(row)==len(d) and all(type(v) is int and v>=0 for v in d.values()),'complete_nonnegative_costs')
    need(d['evaluations_attempted']>=d['evaluations_completed'] and d['observation_attempts']>=d['observation_completed'],'attempt_completed_cost_order')
    need(d['panel_attempts']==3*d['ordinary_trials']+d['terminal_attempts'],'conservative_panel_charge_binding')
    return d


def validate_context(ctx: writeback.MixedWritebackContext, run: Node, binding: Mapping, operator_identity: str) -> None:
    """Bind every context field; only the explicit mode transition changes identity."""
    need(
        equal(packless(ctx.original_states), run.original_initial)
        and equal(ctx.original_time, run.original_start)
        and equal(packless(ctx.policy), run.roundoff_policy)
        and equal(ctx.source_ids, binding['source_ids'])
        and equal(ctx.water_molar_mass_kg_mol, run.roundoff_policy.molar_mass_kg_mol)
        and equal(ctx.original_liquid_fraction_limit, run.original_liquid_fraction_limit)
        and equal(ctx.operator_identity, operator_identity),
        'complete_original_correction_context',
    )


def audit_path(path,run,binding):
    need(path.kind==control.MixedPath.__module__+'.MixedPath','mixed_path_node')
    need(len(path.times)==len(path.states)==len(path.steps)+1 and path.times[0]==run.original_start and equal(path.states[0],run.original_initial),'full_original_path_prefix')
    need(all(type(t) is T for t in path.times) and all(a<b for a,b in zip(path.times,path.times[1:])),'strict_exact_path_times')
    need(path.times[-1]<=run.original_end,'path_inside_original_interval')
    if path.status=='completed':need(path.times[-1]==run.original_end and path.final_observation is not None,'completed_common_endpoint')
    for row in path.states:
        need(type(row) is tuple and len(row)==2,'two_cell_states')
        for cell,s in enumerate(row):
            state_values(s)
            need(s.energy_model_identity==run.original_initial[cell].energy_model_identity,'original_cell_energy_model_identity')
    frame_map={f.step_index:f for f in path.frames}
    need(len(frame_map)==len(path.frames) and all(type(k) is int and 0<=k<len(path.steps) for k in frame_map),'unique_frame_step_indices')
    sums=[[F()]*7 for _ in range(2)];true_sums=[[F()]*7 for _ in range(2)];abs_roundoff=[[F()]*7 for _ in range(2)];component_totals=[F(),F()]
    cumulative=None;mode=binding['original_modes']
    previous_binding=binding['operator_identity'];projected_count=0
    for index,ledger in enumerate(path.steps):
        need(ledger.kind==stage.ExactMixedLedger.__module__+'.ExactMixedLedger' and ledger.start==path.times[index] and ledger.end==path.times[index+1],'exact_ledger_time_binding')
        rows=ledger.represented_integrals;exact_rows=ledger.exact_integrals;qrows=ledger.integral_roundoff
        need(len(dict(rows))==len(rows) and tuple(k for k,v in rows)==tuple(k for k,v in exact_rows)==tuple(k for k,v in qrows),'complete_ledger_key_binding')
        rep=dict(rows);ex=dict(exact_rows);quads=dict(qrows)
        expected={('heat',),('face_energy',)}|{(name,j) for name in ('face_species','diffusion_energy','advection_energy') for j in range(3)}|{('phase_water',i) for i in range(2)}|{('solid',i,j) for i in range(2) for j in range(2)}|{('chemical_gas',i,j) for i in range(2) for j in range(3)}
        need(set(rep)==expected,'full_unit_component_schema')
        for k in rep:need(type(rep[k]) is float and type(ex[k]) is F and type(quads[k]) is F and F(rep[k])-ex[k]==quads[k],'exact_represented_quadrature_binding')
        frame=frame_map.get(index);correction=None
        if frame:
            need(equal(frame.terminal.ledger,ledger) and equal(frame.state,path.states[index+1]) and frame.time==ledger.end,'frame_ledger_state_time_binding')
            need(frame.modes_before==mode and len(frame.modes_after)==2 and all(m in ('existing_liquid','depleted_no_nucleation') for m in frame.modes_after),'mode_lineage')
            need(frame.old_binding==previous_binding,'operator_lineage')
            cell=frame.terminal.root_order.selected_cell
            need(type(cell) is int and cell in (0,1) and frame.modes_before[cell]=='existing_liquid' and frame.modes_after==tuple('depleted_no_nucleation' if i==cell else m for i,m in enumerate(mode)),'single_selected_mode_transition')
            need(frame.old_binding==frame.terminal.evidence.operator_identity and frame.new_binding==frame.operator.constructor_identity,'transition_binding')
            mode=frame.modes_after;previous_binding=frame.new_binding
            ev=restore_proof(frame.terminal.evidence);ctx=restore_proof(frame.terminal.projection.totals.context)
            validate_context(ctx,run,binding,frame.old_binding)
            if cumulative is None:prior=writeback.MixedWritebackTotals.empty(ctx)
            else:prior=writeback.MixedWritebackTotals(ctx,cumulative.per_cell)
            expected_projection=writeback.project_mixed_depletion(ev,context=ctx,totals=prior)
            need(equal(expected_projection,frame.terminal.projection),'offline_projection_replay_mismatch')
            need(equal(frame.terminal.projection.states,path.states[index+1]),'projected_prefix_state')
            cumulative=expected_projection.totals;correction=expected_projection.record;projected_count+=1
        for i,sign in enumerate((-1,1)):
            def increments(values):
                phase=F(values['phase_water',i])
                return [F(values['solid',i,j]) for j in range(2)]+[-phase]+[F(values['chemical_gas',i,j])+sign*F(values['face_species',j])+(phase if j==2 else 0) for j in range(3)]+[sign*F(values['face_energy',])]
            represented=increments(rep);true=increments(ex)
            if correction and i==frame.terminal.root_order.selected_cell:
                represented[2]+=correction.ideal_liquid_increment_mol;true[2]+=correction.ideal_liquid_increment_mol
                represented[5]+=correction.actual_vapor_increment_mol;true[5]+=correction.ideal_vapor_increment_mol
            before=state_values(path.states[index][i]);after=state_values(path.states[index+1][i]);original=state_values(run.original_initial[i])
            bounds=[F(run.stage_policy.solid_mass_absolute_kg)]*2+[F(run.stage_policy.amount_absolute_mol)]*4+[F(run.stage_policy.energy_absolute_j)]
            for j,(inc,exact_inc,bound) in enumerate(zip(represented,true,bounds)):
                sums[i][j]+=inc;true_sums[i][j]+=exact_inc;abs_roundoff[i][j]+=abs(inc-exact_inc)
                need(max(abs(after[j]-before[j]-inc),abs(after[j]-before[j]-exact_inc),abs(after[j]-original[j]-sums[i][j]),abs(after[j]-original[j]-true_sums[i][j]),abs_roundoff[i][j])<=bound,'original_prefix_numeric_budget')
            component_totals[i]+=abs(F(rep['face_energy',])-F(rep['heat',])-sum((F(rep['diffusion_energy',j])+F(rep['advection_energy',j]) for j in range(3)),F()))
            need(component_totals[i]<=F(run.stage_policy.energy_absolute_j),'original_component_budget')
    ctx=restore_proof(path.totals.context)
    validate_context(ctx,run,binding,previous_binding)
    expected_totals=cumulative if cumulative is not None else writeback.MixedWritebackTotals.empty(ctx)
    need(equal(packless(expected_totals.per_cell),path.totals.per_cell),'cumulative_corrections_not_reset')
    need(path.operator.constructor_identity==previous_binding and path.operator.captured_modes==mode,'final_path_operator_lineage')
    return len(path.steps),projected_count


def packless(value):
    """Convert a locally reconstructed proof back to immutable numeric nodes."""
    return unpack(pack(value))


def audit_mixed_record(record: MixedRunRecord,*,expected_binding: bytes) -> MixedReplayAudit:
    """Reparse saved bytes; do not trust a manually constructed frozen wrapper."""
    need(type(record) is MixedRunRecord,'typed_mixed_record')
    fresh=read_mixed_run(record.canonical_bytes,expected_binding=expected_binding)
    r=fresh.result;b=fresh.binding
    for value,cls in ((r.stage_policy,stage.MixedStagePolicy),(r.roundoff_policy,roundoff.DepletionRoundoffPolicy),(r.controller_policy,control.MixedControllerPolicy)):
        cls(**dict(value.values))
    need(r.status in ('completed','failed','cancelled','resource_limit','domain_exit'),'known_run_status')
    need((r.reason is None)==(r.status=='completed'),'status_reason_binding')
    need(type(r.elapsed_seconds) is float and r.elapsed_seconds>=0,'nonnegative_elapsed')
    need(len(r.times)==len(r.states)==len(r.steps)+1 and r.times[0]==r.original_start and equal(r.states[0],r.original_initial),'global_original_prefix')
    total=costs(r.costs);sums={k:0 for k in total};checked=projections=0
    terminal_index=0
    for ref_index,ref in enumerate(r.refinements):
        need(type(ref.level) is int and ref.level>=0 and ref.role in ('terminal','independent'),'refinement_level_role')
        if ref.role=='terminal':
            need(ref.level==terminal_index and ref.approach_cap_s==r.controller_policy.approach_cap_s and ref.safe_fraction==r.controller_policy.safe_inventory_fraction and ref.terminal_window_s==r.controller_policy.terminal_window_s/2**ref.level,'original_terminal_refinement_controls')
            if terminal_index==0 and ref.path.status=='completed':need(ref.status=='coarse_reference' and not ref.comparison,'explicit_coarse_reference_anchor')
            terminal_index+=1
        else:need(ref_index==len(r.refinements)-1 and ref.level==terminal_index-1,'last_independent_refinement')
        for row in ref.comparison:
            need(type(row) is tuple and len(row)==3 and row[0] in ('event','common') and type(row[2]) is tuple and len(row[2])==6 and all(type(v) is F and v>=0 for v in row[2]),'strict_six_numeric_differences')
        if ref.status=='comparison_pass':
            limits=tuple(map(F,(r.stage_policy.solid_mass_absolute_kg,r.stage_policy.amount_absolute_mol,r.stage_policy.energy_absolute_j,r.stage_policy.temperature_absolute_k,r.stage_policy.pressure_absolute_pa,r.stage_policy.time_absolute_s)))
            need(ref.comparison and all(all(v<=limit for v,limit in zip(row[2],limits)) for row in ref.comparison),'reported_comparison_exceeds_original_gates')
        c=costs(ref.costs)
        for k,v in c.items():sums[k]+=v
        n,p=audit_path(ref.path,r,b);checked+=n;projections+=p
    need(sums==total,'all_refinement_costs_once')
    journal=r.observation_journal
    need(len(journal)==total['observation_attempts'] and sum(j.status=='completed' for j in journal)==total['observation_completed'],'actual_observation_journal_costs')
    for entry in journal:
        need(entry.status in ('completed','failed','domain_exit','attempted') and type(entry.branch_index) is int and 0<=entry.branch_index<len(r.refinements),'journal_status_branch')
        if entry.status=='completed':need(entry.sample is not None and equal(entry.sample.state,entry.states) and entry.sample.time==entry.time,'actual_completed_observation')
    if r.status!='completed':
        need(len(r.times)==1 and not r.steps and not r.packets and equal(r.operator.constructor_identity,b['operator_identity']),'atomic_failed_packet_not_published')
        empty_context=restore_proof(r.roundoff_totals.context)
        validate_context(empty_context,r,b,b['operator_identity'])
        need(equal(packless(writeback.MixedWritebackTotals.empty(empty_context)),r.roundoff_totals),'failed_no_uncommitted_corrections')
    else:
        need(r.times[-1]==r.original_end and len(r.packets)==1 and len(r.refinements)>=4,'completed_atomic_packet')
        validate_context(restore_proof(r.roundoff_totals.context),r,b,r.operator.constructor_identity)
        main=r.refinements[-2];independent=r.refinements[-1]
        need(all(x.status=='comparison_pass' for x in r.refinements[-3:]) and independent.role=='independent' and all(x.role=='terminal' for x in r.refinements[:-1]),'two_passes_and_independent_roles')
        need(independent.approach_cap_s==main.approach_cap_s/2 and independent.safe_fraction==main.safe_fraction/2 and independent.terminal_window_s==main.terminal_window_s,'independent_original_controls')
        need(main.path.approach_grid and independent.path.approach_grid and main.path.approach_grid!=independent.path.approach_grid,'actual_independent_grid')
        need(equal(r.roundoff_totals,main.path.totals) and equal(r.operator,main.path.operator),'committed_totals_and_operator')
        need(equal(r.steps,main.path.steps) and equal(r.states,main.path.states) and equal(r.times,main.path.times) and equal(r.packets[0],main.path.frames),'single_main_packet_commit')
    limits=r.controller_policy
    if r.status=='completed':need(r.elapsed_seconds<=limits.maximum_wall_seconds,'completed_original_wall_budget')
    need(total['evaluations_attempted']<=limits.maximum_evaluations and total['panel_attempts']<=limits.maximum_panel_attempts,'original_cumulative_work_budget')
    # Full physical sample authentication, six-gate recomputation and root-order
    # reproduction are deliberately not inferred from schema or PASS strings.
    return MixedReplayAudit('partial_audit',fresh.sha256,len(r.steps),len(r.refinements),checked,projections,
        ('physical_provider_and_external_source_authentication','full_six_gate_recomputation','all_candidate_root_order_and_whole_panel_proof','independent_native_validation','resume_admission'))


def export_mixed_record(record: MixedRunRecord) -> str:
    """Lossless raw JSON text; never JavaScript-number parse/re-encode."""
    need(type(record) is MixedRunRecord,'typed_mixed_record')
    return read_mixed_run(record.canonical_bytes).canonical_bytes.decode('utf-8')
