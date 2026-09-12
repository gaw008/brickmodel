"""Strict numerical-evidence codec. No provider restoration or resume authority."""
from dataclasses import dataclass, fields, replace
from fractions import Fraction
from collections.abc import Mapping
from types import MappingProxyType, UnionType
import hashlib
import json
import math
import re
import typing
import numpy as np
from sludge_sandbox import integration as integ
from sludge_sandbox import exact_integration as xi
from sludge_sandbox import exact_depletion_integration as xd
from sludge_sandbox import exact_terminal_executor as xe
from sludge_sandbox import exact_terminal_panel as xp
from sludge_sandbox import exact_root_order as xr
from sludge_sandbox import exact_affine_depletion as xa
from sludge_sandbox import depletion_roundoff as dr
from sludge_sandbox import depletion_integration as di
from sludge_sandbox import water_chemical_potential as wc
from sludge_sandbox import water_phase_transfer as wp
from sludge_sandbox import pressure_comparison as pc
from sludge_sandbox.paired_pressure_host import SharedConstantParameterBox
from sludge_sandbox.water_properties import WaterState,WaterReference
from sludge_sandbox.water_implementation import WaterImplementation
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer
from sludge_sandbox.exact_event_clock import ExactEventTime

SCHEMA='exact_depletion_run_record_v1'
CAPTURE='schema_complete_numerical_evidence'
CLASSES=(WaterState,WaterReference,WaterImplementation,integ.ConservedState,integ.Rates,integ.IntegrationPolicy,xi.ExactStepLedger,
 xd.ExactDepletionResult,xd.ExactPacketFrame,xd.ExactPacketRefinement,xd.ExactPacketPath,
 xe.ExactTerminalAttempt,xe.TerminalObservation,xe.TerminalCosts,xp.ExactAffinePanel,
 xr.ExactRootOrder,xr.RootCandidate,xr.NoRootEvidence,xa.ExactAffineSamples,xa.ExactAffineEvidence,
 xa.ExactDepletionWritebackRecord,dr.DepletionRoundoffPolicy,dr.DepletionRoundoffTotals,
 di.DepletionPolicy,di.NestedApproachPolicy,pc.PressureComparisonPolicy,SharedConstantParameterBox,
 wp.CellWaterTransfer,wc.WaterPhaseEquilibrium,wc.WaterVaporChemicalState,wc.WaterLiquidChemicalState)
REGISTRY={cls.__name__:cls for cls in CLASSES}
COSTS={'evaluations_attempted','evaluations_completed','ordinary_trials','ordinary_rejected','ordinary_panels',
 'predictor_attempts','terminal_attempts','terminal_panels','endpoint_attempts','endpoint_completed','stage_replans'}
MODES={'existing_liquid','depleted_no_nucleation'}

class ExactRecordError(ValueError):pass

def require(condition,reason):
    if not condition:raise ExactRecordError(reason)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

@dataclass(frozen=True)
class EvidenceNode:
    kind:str
    values:Mapping
    def __getattr__(self,name):
        try:return self.values[name]
        except KeyError as exc:raise AttributeError(name) from exc

@dataclass(frozen=True)
class ExactRunRecord:
    canonical_bytes:bytes
    binding:Mapping
    result:EvidenceNode
    start:ExactEventTime
    end:ExactEventTime
    times:tuple
    states:tuple
    ledgers:tuple
    validation_scope:str='strict_schema_and_committed_associations_not_resume_or_full_numerical_audit'
    @property
    def sha256(self):return hashlib.sha256(self.canonical_bytes).hexdigest()


def _node(kind,values):return EvidenceNode(kind,MappingProxyType(values))

def _operator(view):
    # Frozen constructor identity survives a later source failure. Never call the
    # live guard while capturing an already failed result.
    require(type(view) is ExactFreeWaterTransfer,'explicit_operator_reference')
    return _node('OperatorReference',{'identity':view._identity,'modes':tuple(view.operator.interfaces)})

def _observation(value):
    b=value.base_evaluation
    return _node('Observation',dict(rates=value.rates,
        temperatures_k=tuple(float(x.mechanical.temperature_k) for x in b.storage_states),
        temperature_errors_k=tuple(float(x.temperature_error_bound_k) for x in b.storage_inverses),
        pressures_pa=tuple(float(x.mechanical.pressure_pa) for x in b.storage_states),
        pressure_errors_pa=tuple(float(x.pressure_error_bound_pa) for x in b.storage_states),
        **{k:getattr(value,k) for k in ('cell_transfers','interface_modes','source_ids','coefficient_set_id',
            'coefficient_version','coefficient_classification','dry_policy','qualification')}))

SPECIAL={'OperatorReference':{'identity','modes'},'Observation':{'rates','temperatures_k','temperature_errors_k',
 'pressures_pa','pressure_errors_pa','cell_transfers','interface_modes','source_ids','coefficient_set_id',
 'coefficient_version','coefficient_classification','dry_policy','qualification'}}

def pack(v):
    if v is None or type(v) in (str,bool,int):return v
    if isinstance(v,np.generic):return pack(v.item())
    if type(v) is float:
        require(math.isfinite(v),'finite_float');return {'float_hex':v.hex()}
    if type(v) is Fraction:return {'fraction':[v.numerator,v.denominator]}
    if type(v) is ExactEventTime:return {'exact_time':v.to_record()}
    if type(v) is ExactFreeWaterTransfer:return pack(_operator(v))
    if type(v) is wp.WaterTransferEvaluation:return pack(_observation(v))
    if isinstance(v,np.ndarray):
        require(v.dtype==np.float64 and np.all(np.isfinite(v)),'finite_float64_array')
        return {'array':{'shape':list(v.shape),'values':[pack(float(x)) for x in v.flat]}}
    if type(v) in CLASSES:return {'record':type(v).__name__,'fields':{f.name:pack(getattr(v,f.name)) for f in fields(v)}}
    if type(v) is EvidenceNode:return {'record':v.kind,'fields':{k:pack(x) for k,x in v.values.items()}}
    if isinstance(v,Mapping):
        require(all(type(k) is str for k in v),'string_mapping_keys')
        return {'mapping':{k:pack(x) for k,x in v.items()}}
    if type(v) in (tuple,list):return {'sequence':[pack(x) for x in v]}
    raise ExactRecordError('unsupported_capture_type:'+type(v).__name__)


def _matches(value,hint):
    if hint is typing.Any or hint is object:return True
    if hint is None or hint is type(None):return value is None
    origin=typing.get_origin(hint);args=typing.get_args(hint)
    if origin is typing.Literal:return any(type(value) is type(x) and value==x for x in args)
    if origin in (typing.Union,UnionType):return any(_matches(value,a) for a in args)
    # Match the existing numerical policies: Python integers are valid real
    # inputs to float-annotated fields. Preserve their representation/identity;
    # bool remains distinct despite being an int subclass.
    if hint is float:return type(value) in (int,float)
    if hint in (int,str,bool,Fraction,ExactEventTime):return type(value) is hint
    if origin is tuple or hint is tuple:
        if type(value) is not tuple:return False
        if not args:return True
        if len(args)==2 and args[1] is Ellipsis:return all(_matches(x,args[0]) for x in value)
        return len(value)==len(args) and all(_matches(x,h) for x,h in zip(value,args))
    if origin is np.ndarray or hint is np.ndarray:return type(value) is np.ndarray
    if isinstance(hint,type) and hint in CLASSES:return type(value) is EvidenceNode and value.kind==hint.__name__
    if hint is ExactFreeWaterTransfer:return type(value) is EvidenceNode and value.kind=='OperatorReference'
    if hint is wp.WaterTransferEvaluation:return type(value) is EvidenceNode and value.kind=='Observation'
    return True  # Broad Mapping/object annotations have explicit checks below.


def unpack(v):
    if v is None or type(v) in (str,bool,int):return v
    require(type(v) is dict,'tagged_value_required')
    if set(v)=={'float_hex'}:
        require(type(v['float_hex']) is str,'hex_string_required')
        x=float.fromhex(v['float_hex']);require(math.isfinite(x) and x.hex()==v['float_hex'],'canonical_float_hex');return x
    if set(v)=={'fraction'}:
        a=v['fraction'];require(type(a) is list and len(a)==2 and all(type(x) is int for x in a),'fraction_integer_pair')
        require(a[1]>0 and math.gcd(*a)==1,'canonical_fraction');return Fraction(*a)
    if set(v)=={'exact_time'}:return ExactEventTime.from_record(v['exact_time'])
    if set(v)=={'sequence'}:
        require(type(v['sequence']) is list,'sequence_list');return tuple(unpack(x) for x in v['sequence'])
    if set(v)=={'mapping'}:
        require(type(v['mapping']) is dict,'mapping_object');return MappingProxyType({k:unpack(x) for k,x in v['mapping'].items()})
    if set(v)=={'array'}:
        a=v['array'];require(type(a) is dict and set(a)=={'shape','values'},'array_fields')
        shape=a['shape'];require(type(shape) is list and 1<=len(shape)<=2 and all(type(x) is int and x>0 for x in shape),'array_shape')
        require(type(a['values']) is list and math.prod(shape)==len(a['values']),'array_count')
        values=[unpack(x) for x in a['values']];require(all(type(x) is float for x in values),'float_array_values')
        result=np.frombuffer(np.array(values,dtype=float).tobytes(),dtype=float).reshape(shape);return result
    require(set(v)=={'record','fields'} and type(v['record']) is str and type(v['fields']) is dict,'record_tag')
    kind=v['record'];require(kind in REGISTRY or kind in SPECIAL,'unknown_record_kind')
    names=SPECIAL[kind] if kind in SPECIAL else {f.name for f in fields(REGISTRY[kind])}
    require(set(v['fields'])==names,'exact_record_fields:'+kind)
    values={k:unpack(x) for k,x in v['fields'].items()}
    if kind in REGISTRY:
        cls=REGISTRY[kind];hints=typing.get_type_hints(cls)
        for key,x in values.items():require(_matches(x,hints.get(key,object)),'field_type:'+kind+'.'+key)
    result=_node(kind,values)
    if kind=='OperatorReference':
        require(type(result.identity) is tuple and len(result.identity)==3,'operator_identity')
        require(type(result.modes) is tuple and all(type(x) is str and x in MODES for x in result.modes),'interface_modes')
    if kind in ('ConservedState','Rates','ExactStepLedger'):
        _typed(result,REGISTRY[kind])
    if kind=='TerminalObservation':
        st=_typed(result.state,integ.ConservedState);rates=_typed(result.evaluation.rates,integ.Rates)
        n,m=st.amounts_mol.shape
        require(rates.face_species_mol_s.shape==(n+1,m) and rates.reaction_species_mol_s.shape==(n,m) and rates.face_energy_w.shape==(n+1,) and rates.cell_power_w.shape==(n,),'observation_state_rate_shape')
        require((rates.mechanical_rates_per_s is None)==(st.mechanical_stretches is None),'observation_state_mechanics')
        if rates.mechanical_rates_per_s is not None:require(rates.mechanical_rates_per_s.shape==st.mechanical_stretches.shape,'observation_stretch_shape')
    if kind=='Observation':
        require(type(result.rates) is EvidenceNode and result.rates.kind=='Rates','observation_rates')
        n=result.rates.reaction_species_mol_s.shape[0]
        for key in ('temperatures_k','temperature_errors_k','pressures_pa','pressure_errors_pa'):
            values=getattr(result,key)
            require(type(values) is tuple and len(values)==n and all(type(x) is float and x>=0 for x in values),'observation_vectors')
        require(len(result.cell_transfers)==n and len(result.interface_modes)==n,'observation_cells')
        require(all(type(x) is str and x in MODES for x in result.interface_modes),'observation_modes')
    return result


def _typed(node,cls):
    require(type(node) is EvidenceNode and node.kind==cls.__name__,'typed_record_required:'+cls.__name__)
    obj=cls(**{f.name:getattr(node,f.name) for f in fields(cls) if f.init})
    require(pack(obj)==pack(node),'derived_field_mismatch:'+cls.__name__)
    return obj


POLICY_CLASSES=(integ.IntegrationPolicy,di.DepletionPolicy,di.NestedApproachPolicy,
    dr.DepletionRoundoffPolicy,dr.DepletionRoundoffTotals,pc.PressureComparisonPolicy,SharedConstantParameterBox)

def _policy(value):
    if type(value) is EvidenceNode:
        cls=REGISTRY.get(value.kind)
        require(cls in POLICY_CLASSES,'policy_record_kind')
        result=cls(**{f.name:_policy(getattr(value,f.name)) for f in fields(cls) if f.init})
        require(pack(result)==pack(value),'policy_derived_fields')
        return result
    if type(value) is tuple:return tuple(_policy(x) for x in value)
    return value

def _sha(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None

def _binding(view,case_sha256,runtime_identity,*,live):
    require(type(view) is ExactFreeWaterTransfer and _sha(case_sha256),'binding_inputs')
    if live:view.operator_identity
    return dict(original_operator=_operator(view),case_sha256=case_sha256,runtime_identity=runtime_identity,
        liquid_index=view.operator.liquid_index,water_vapor_index=view.operator.water_vapor_index,
        reconstruction='external_frozen_case_water_and_implementation_required')


def encode_exact_run(run,*,original_operator,start,end,case_sha256,runtime_identity):
    require(type(run) is xd.ExactDepletionResult,'explicit_exact_result')
    data=dict(schema=SCHEMA,capture_kind=CAPTURE,start=pack(start),end=pack(end),
        binding=pack(_binding(original_operator,case_sha256,runtime_identity,live=False)),result=pack(run))
    raw=canonical(data)
    read_exact_run(raw)
    return raw


def _unique(items):
    result={}
    for k,v in items:
        require(k not in result,'duplicate_json_key');result[k]=v
    return result


def read_exact_run(raw,*,expected_binding=None):
    try:
        require(type(raw) is bytes,'record_bytes_required')
        d=json.loads(raw,object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(ExactRecordError('nonfinite_json')))
        require(type(d) is dict and set(d)=={'schema','capture_kind','start','end','binding','result'},'exact_run_fields')
        require(d['schema']==SCHEMA and d['capture_kind']==CAPTURE,'unsupported_capture_schema')
        start,end=unpack(d['start']),unpack(d['end'])
        require(type(start) is ExactEventTime and type(end) is ExactEventTime and start<end,'run_time_interval')
        b=unpack(d['binding']);r=unpack(d['result'])
        require(isinstance(b,Mapping) and set(b)=={'original_operator','case_sha256','runtime_identity','reconstruction','liquid_index','water_vapor_index'},'binding_fields')
        require(_sha(b['case_sha256']) and isinstance(b['runtime_identity'],Mapping),'binding_identity')
        require(type(r) is EvidenceNode and r.kind=='ExactDepletionResult','exact_result_node')
        if expected_binding is not None:require(pack(b)==pack(expected_binding),'external_binding_mismatch')
        times=r.times_s;states=tuple(_typed(x,integ.ConservedState) for x in r.states)
        ledgers=tuple(_typed(x,xi.ExactStepLedger) for x in r.steps)
        _associations(r,b,start,end,times,states,ledgers)
        return ExactRunRecord(canonical(d),b,r,start,end,times,states,ledgers)
    except ExactRecordError:raise
    except (ValueError,TypeError,AttributeError,KeyError,OverflowError,RecursionError) as exc:
        raise ExactRecordError('invalid_exact_record:'+str(exc)) from exc


def _associations(r,b,start,end,times,states,ledgers):
    require(r.schema=='exact_ordered_packet_core_v1','core_schema')
    require(r.approach_strategy=='independent_halved_controls_no_spine_reuse' and r.qualification=='research_core_not_legacy_record_resume_or_material_admission','core_contract')
    _policy(r.initial_policy)
    require(r.event_policy.kind=='DepletionPolicy' and r.roundoff_totals.kind=='DepletionRoundoffTotals','original_policy_records')
    event_policy=_policy(r.event_policy);totals=_policy(r.roundoff_totals)
    require(totals.policy==event_policy.roundoff_policy,'original_roundoff_policy_binding')
    require(r.status in {'completed','cancelled','resource_limit','domain_exit','failed','unsupported','numerical_failure'},'core_status')
    require((r.status=='completed' and r.reason is None) or (r.status!='completed' and type(r.reason) is str and bool(r.reason)),'status_reason')
    require(type(r.elapsed_seconds) is float and r.elapsed_seconds>=0,'elapsed_seconds')
    require(type(times) is tuple and len(times)==len(states)==len(ledgers)+1 and times[0]==start,'prefix_lengths')
    require(all(type(t) is ExactEventTime for t in times) and all(a<b for a,b in zip(times,times[1:])) and times[-1]<=end,'prefix_times')
    if r.status=='completed':require(times[-1]==end,'completed_endpoint')
    cells,cols=states[0].amounts_mol.shape
    li,vi=b['liquid_index'],b['water_vapor_index']
    require(type(li) is int and type(vi) is int and 0<=li<cols and 0<=vi<cols and li!=vi,'species_indices')
    require(all((st.mechanical_stretches is None)==(states[0].mechanical_stretches is None) for st in states),'whole_prefix_mechanics_presence')
    require(all(s.amounts_mol.shape==(cells,cols) and s.energy_model_identity==states[0].energy_model_identity for s in states),'state_shape_identity')
    for i,l in enumerate(ledgers):
        require(l.start_s==times[i] and l.end_s==times[i+1],'ledger_time_binding')
        require(l.face_species_mol.shape==(cells+1,cols) and l.reaction_species_mol.shape==(cells,cols) and l.face_energy_j.shape==(cells+1,) and l.cell_work_j.shape==(cells,),'ledger_shapes')
        require((l.stretch_increment is None)==(states[i].mechanical_stretches is None),'ledger_mechanics_presence')
    require(isinstance(r.costs,Mapping) and set(r.costs)==COSTS,'cost_fields')
    require(all(type(v) is int and v>=0 for v in r.costs.values()),'nonnegative_integer_costs')
    require(r.costs['evaluations_completed']<=r.costs['evaluations_attempted'] and r.costs['endpoint_completed']<=r.costs['endpoint_attempts'],'cost_completion_order')
    require(r.costs['ordinary_panels']+r.costs['ordinary_rejected']<=r.costs['ordinary_trials'],'ordinary_trial_accounting')
    modes=list(b['original_operator'].modes);require(len(modes)==cells,'initial_mode_shape')
    require(len(r.operator.modes)==cells,'final_mode_shape')
    for state,m in ((states[0],modes),(states[-1],r.operator.modes)):
        require(len(m)==state.amounts_mol.shape[0],'state_mode_cells')
        require(all((state.amounts_mol[i,li]>0 if mode=='existing_liquid' else state.amounts_mol[i,li]==0) for i,mode in enumerate(m)),'state_mode_inventory')
    used=set();previous=start
    for packet in r.packets:
        require(type(packet) is tuple and bool(packet),'nonempty_committed_packet')
        for frame in packet:
            a=frame.terminal;require(a.status=='speculative_completed','committed_terminal_status')
            panel=a.terminal_panel;order=a.root_order;cell=order.selected_cell
            require(type(cell) is int and 0<=cell<cells and cell not in used,'committed_unique_cell')
            require(a.original_operator.modes==tuple(modes),'event_original_modes')
            modes[cell]='depleted_no_nucleation';require(a.candidate_operator.modes==tuple(modes),'event_candidate_modes')
            require(panel.ledger.end_s>previous,'event_time_order');previous=panel.ledger.end_s
            matches=[i for i,l in enumerate(ledgers) if pack(l)==pack(panel.ledger)]
            require(len(matches)==1,'committed_ledger_membership')
            i=matches[0];require(pack(states[i])==pack(a.initial_state) and pack(states[i+1])==pack(a.corrected_state),'committed_state_binding')
            require(frame.common_time is not None and frame.common_time>=panel.ledger.end_s,'event_common_time')
            delta=frame.packet_maximum_differences
            require(type(delta) is tuple and len(delta)==6 and type(delta[0]) is Fraction and all(type(x) is float for x in delta[1:]) and all(x>=0 for x in delta),'six_gate_diagnostics')
            c=a.correction;raw=a.terminal_panel.raw_state;corrected=a.corrected_state
            require(corrected.amounts_mol[cell,li]==0,'corrected_selected_dry')
            if c is not None:
                require((c.cell_index,c.liquid_index,c.vapor_index)==(cell,li,vi),'correction_selected_indices')
                require(c.liquid_before_mol==raw.amounts_mol[cell,li] and c.vapor_before_mol==raw.amounts_mol[cell,vi] and c.vapor_after_mol==corrected.amounts_mol[cell,vi],'correction_state_values')
            else:require(raw.amounts_mol[cell,li]==0,'uncorrected_exact_zero')
            used.add(cell)
    require(tuple(modes)==r.operator.modes,'final_modes_from_committed_events')
    require(len(used)==sum(len(p) for p in r.packets),'event_once_only')
    require(totals.events==sum(f.terminal.correction is not None for packet in r.packets for f in packet),'correction_event_count')


def validate_binding(record,actual_original_operator,*,case_sha256,runtime_identity):
    require(type(record) is ExactRunRecord,'explicit_record')
    # Reparse immutable bytes: a manually constructed frozen dataclass is not an audit token.
    expected=_binding(actual_original_operator,case_sha256,runtime_identity,live=True)
    checked=read_exact_run(record.canonical_bytes,expected_binding=expected)
    def references(v):
        if type(v) is EvidenceNode:
            if v.kind=='OperatorReference':yield v
            for child in v.values.values():yield from references(child)
        elif isinstance(v,Mapping):
            for child in v.values():yield from references(child)
        elif type(v) is tuple:
            for child in v:yield from references(child)
    cache={tuple(actual_original_operator.operator.interfaces):pack(_operator(actual_original_operator))}
    for ref in references(checked.result):
        if ref.modes not in cache:
            current=ExactFreeWaterTransfer(replace(actual_original_operator.operator,interface_modes=ref.modes))
            cache[ref.modes]=pack(_operator(current))
        require(pack(ref)==cache[ref.modes],'actual_mode_source_binding_mismatch')
    return checked
