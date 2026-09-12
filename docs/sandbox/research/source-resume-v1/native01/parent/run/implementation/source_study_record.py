"""Complete bounded source-study evidence DAG; passive read/write, never resume."""
from collections.abc import Mapping
from dataclasses import dataclass, fields
from fractions import Fraction as F
from types import MappingProxyType
import hashlib
import math

import numpy as np

from .exact_event_clock import ExactEventTime as T
from .exact_record import canonical, pack, unpack
from .source_observation_record import (
    SourceObservationContext, SourceObservationRecord, _context_check, encode_source_sample,
    decode_source_sample,
)
from .source_observation_schema import strict_json
from .source_study_schema import (
    CLASSES, REGISTRY, LIVE_FIELDS, SourceStudyNode, SourceLiveReference, SourceStudyFailure,
    SourceStudyRecordError, require, validate_node, reify, has_capture_failure,
)

SCHEMA='source_study_record_v1'
VALIDATION_SCOPE='complete_passive_source_study_schema_observation_and_declared_association_audit_not_resume'
MAX_IMPORT_BYTES=64*1024*1024
MAX_RECORD_BYTES=64*1024*1024
MAX_VALUES=2_000_000
MAX_DEPTH=96
MAX_DAG_NODES=200_000
MAX_ARRAY_ELEMENTS=250_000
MAX_INTEGER_BITS=4096
ROOT_NAMES=frozenset(('seed','proposal','approach','refinement','common_endpoint','transition','failure'))


def _bounded(value: object) -> None:
    pending=[(value,0)]; count=0
    while pending:
        current,depth=pending.pop();count+=1
        require(count<=MAX_VALUES and depth<=MAX_DEPTH,'source_study_resource_limit')
        if type(current) is int:
            require(current.bit_length()<=MAX_INTEGER_BITS,'source_study_integer_limit')
        elif type(current) is dict:
            pending.extend((x,depth+1) for x in current.values())
        elif type(current) is list:
            pending.extend((x,depth+1) for x in current)


def _parse(raw: bytes, limit: int) -> object:
    require(type(raw) is bytes and len(raw)<=limit,'source_study_byte_limit')
    value=strict_json(raw);_bounded(value)
    return value


def _reference(value: object, kind: str) -> SourceLiveReference:
    if kind=='adapter':
        from .exact_source_column import ExactSourceColumn
        require(type(value) is ExactSourceColumn,'source_study_actual_adapter_required')
        return SourceLiveReference('ExactSourceColumn',True,value._identity,tuple(value.column.interface_modes))
    from .source_wet_storage import SourceWetStorage
    require(type(value) is SourceWetStorage,'source_study_actual_storage_required')
    return SourceLiveReference('SourceWetStorage',True,value._identity,None)


def _snapshot(value: object, memo: dict[int,object] | None=None, active: set[int] | None=None,
              depth: int=0, owners: dict[int,object] | None=None) -> object:
    memo={} if memo is None else memo;active=set() if active is None else active
    owners={} if owners is None else owners
    require(depth<=MAX_DEPTH,'source_study_resource_limit')
    cls=type(value)
    if value is None or cls in (str,bool,int,float,F,T):
        if cls is int: require(value.bit_length()<=MAX_INTEGER_BITS,'source_study_integer_limit')
        if cls is float: require(math.isfinite(value),'source_study_finite_float')
        if cls is F: require(max(value.numerator.bit_length(),value.denominator.bit_length())<=MAX_INTEGER_BITS,'source_study_integer_limit')
        if cls is T: require(type(value.seconds) is F,'source_study_exact_time')
        return value
    key=id(value)
    owners[key]=value
    require(key not in active,'source_study_cycle')
    if key in memo:return memo[key]
    require(len(memo)<MAX_VALUES,'source_study_resource_limit')
    active.add(key)
    child=lambda v:_snapshot(v,memo,active,depth+1,owners)
    if cls is np.ndarray:
        require(value.dtype==np.float64 and 1<=value.ndim<=2 and 0<value.size<=MAX_ARRAY_ELEMENTS
                and bool(np.all(np.isfinite(value))),'source_study_float64_array')
        result=np.frombuffer(value.tobytes(),dtype=np.float64).reshape(value.shape)
    elif cls is SourceStudyNode:
        result=SourceStudyNode(value.kind,MappingProxyType({k:child(v) for k,v in value.values.items()}))
        validate_node(result)
    elif cls in CLASSES:
        values={}
        for field in fields(value):
            v=getattr(value,field.name)
            if field.name in LIVE_FIELDS.get(cls,()):
                v=_reference(v,'adapter' if field.name in ('adapter','dry_adapter') else 'storage')
            values[field.name]=child(v)
        result=SourceStudyNode(cls.__module__+'.'+cls.__qualname__,MappingProxyType(values))
        validate_node(result)
    elif isinstance(value,BaseException):
        data={k:v for k,v in vars(value).items() if k not in ('exception_type','exception_message')}
        if value.__cause__ is not None:data['cause']=value.__cause__
        result=child(SourceStudyFailure(cls.__module__+'.'+cls.__qualname__,str(value),
                     getattr(value,'stage',None),data))
    elif isinstance(value,Mapping):
        require(all(type(k) is str for k in value),'source_study_string_keys')
        result=MappingProxyType({k:child(v) for k,v in value.items()})
    elif cls in (tuple,list):
        result=tuple(child(v) for v in value)
    else:
        raise SourceStudyRecordError('unsupported_source_study_type:'+cls.__name__)
    active.remove(key);memo[key]=result
    return result


def _array(shape: object, values: object, *, legacy: bool) -> np.ndarray:
    require(type(shape) is list and 1<=len(shape)<=2 and all(type(n) is int and n>0 for n in shape),
            'source_study_array_shape')
    count=math.prod(shape)
    require(count<=MAX_ARRAY_ELEMENTS,'source_study_array_limit')
    if legacy:
        require(type(values) is list,'source_study_array_values')
        rows=values if len(shape)==1 else [x for row in values for x in row] if all(type(row) is list for row in values) else ()
        require(len(rows)==count and all(type(x) is float and math.isfinite(x) for x in rows),
                'source_study_array_values')
        require(len(values)==shape[0] and (len(shape)==1 or all(len(row)==shape[1] for row in values)),
                'source_study_array_shape')
        flat=rows
    else:
        require(type(values) is list and len(values)==count,'source_study_array_values')
        flat=[unpack(v) for v in values]
        require(all(type(x) is float and math.isfinite(x) for x in flat),'source_study_array_values')
    array=np.asarray(flat,dtype=np.float64).reshape(shape)
    return np.frombuffer(array.tobytes(),dtype=np.float64).reshape(shape)


def _legacy(value: object, depth: int=0) -> object:
    require(depth<=MAX_DEPTH,'source_study_resource_limit')
    if type(value) is list:return tuple(_legacy(v,depth+1) for v in value)
    if type(value) is not dict:return _snapshot(value)
    if set(value)=={'numerator','denominator'}:
        n,d=value['numerator'],value['denominator']
        require(type(n) is type(d) is int and d>0 and math.gcd(n,d)==1,'source_study_canonical_fraction')
        return F(n,d)
    if set(value)=={'dtype','shape','values'}:
        require(value['dtype']=='float64','source_study_array_dtype')
        return _array(value['shape'],value['values'],legacy=True)
    if set(value)=={'type','fields'}:
        kind,body=value['type'],value['fields']
        if kind==T.__module__+'.'+T.__qualname__:
            require(type(body) is dict and set(body)=={'seconds'},'source_study_exact_time_fields')
            seconds=_legacy(body['seconds'],depth+1)
            require(type(seconds) is F,'source_study_exact_time')
            return T(seconds)
        require(type(kind) is str and kind in REGISTRY,'unknown_legacy_source_study_class')
        cls=REGISTRY[kind];live=LIVE_FIELDS.get(cls,())
        require(type(body) is dict and set(body)=={f.name for f in fields(cls)}-set(live),
                'source_study_legacy_complete_fields:'+cls.__name__)
        values={k:_legacy(v,depth+1) for k,v in body.items()}
        for name in live:
            identity=values.get('operator_identity') if name=='adapter' else values.get('storage_identity')
            values[name]=_snapshot(SourceLiveReference(
                'ExactSourceColumn' if name in ('adapter','dry_adapter') else 'SourceWetStorage',False,identity,None))
        node=SourceStudyNode(kind,MappingProxyType(values));validate_node(node)
        return node
    return MappingProxyType({k:_legacy(v,depth+1) for k,v in value.items()})


def _graph(value: object) -> tuple[dict[str,object],dict[str,str]]:
    nodes={};memo={};active=set()
    def visit(v,depth=0):
        require(depth<=MAX_DEPTH,'source_study_resource_limit')
        if v is None or type(v) in (str,bool,int,float,F,T):return {'value':pack(v)}
        identity=id(v)
        require(identity not in active,'source_study_cycle')
        if identity in memo:return {'ref':memo[identity]}
        active.add(identity)
        if type(v) is SourceStudyNode:
            body={'class':v.kind,'fields':{k:visit(x,depth+1) for k,x in v.values.items()}}
        elif type(v) is np.ndarray:
            body={'array':pack(v)['array']}
        elif type(v) is tuple:
            body={'tuple':[visit(x,depth+1) for x in v]}
        elif isinstance(v,Mapping):
            body={'mapping':{k:visit(x,depth+1) for k,x in v.items()}}
        else:raise SourceStudyRecordError('unsupported_study_graph_value')
        digest=hashlib.sha256(canonical(body)).hexdigest();nodes[digest]=body
        require(len(nodes)<=MAX_DAG_NODES,'source_study_dag_limit')
        memo[identity]=digest;active.remove(identity)
        return {'ref':digest}
    root=visit(value)
    return nodes,root


def _ungraph(nodes: object, root: object) -> object:
    require(type(nodes) is dict and len(nodes)<=MAX_DAG_NODES,'source_study_dag_limit')
    cache={};active=set();heights={}
    def resolve(token,depth=0):
        require(depth<=MAX_DEPTH and type(token) is dict,'source_study_graph_token')
        if set(token)=={'value'}:
            value=unpack(token['value'])
            require(value is None or type(value) in (str,bool,int,float,F,T),'source_study_primitive_token')
            require(pack(value)==token['value'],'source_study_noncanonical_primitive')
            return _snapshot(value)
        require(set(token)=={'ref'} and type(token['ref']) is str and token['ref'] in nodes,
                'source_study_missing_reference')
        key=token['ref'];require(key not in active,'source_study_cycle')
        if key in cache:
            require(depth+heights[key]<=MAX_DEPTH,'source_study_resource_limit')
            return cache[key]
        active.add(key);body=nodes[key]
        require(type(body) is dict and hashlib.sha256(canonical(body)).hexdigest()==key,'source_study_node_digest')
        if set(body)=={'class','fields'}:
            require(type(body['class']) is str and body['class'] in REGISTRY and type(body['fields']) is dict,
                    'unknown_source_study_class')
            value=SourceStudyNode(body['class'],MappingProxyType({k:resolve(v,depth+1) for k,v in body['fields'].items()}))
            validate_node(value)
        elif set(body)=={'array'}:
            require(type(body['array']) is dict and set(body['array'])=={'shape','values'},'source_study_array_fields')
            value=_array(body['array']['shape'],body['array']['values'],legacy=False)
        elif set(body)=={'tuple'}:
            require(type(body['tuple']) is list,'source_study_tuple_node')
            value=tuple(resolve(v,depth+1) for v in body['tuple'])
        elif set(body)=={'mapping'}:
            require(type(body['mapping']) is dict,'source_study_mapping_node')
            value=MappingProxyType({k:resolve(v,depth+1) for k,v in body['mapping'].items()})
        else:raise SourceStudyRecordError('source_study_node_fields')
        tokens=(body['fields'].values() if 'fields' in body else body['mapping'].values()
                if 'mapping' in body else body['tuple'] if 'tuple' in body else ())
        heights[key]=1+max((heights[t['ref']] if 'ref' in t else 0 for t in tokens),default=0)
        require(depth+heights[key]<=MAX_DEPTH,'source_study_resource_limit')
        active.remove(key);cache[key]=value;return value
    value=resolve(root)
    require(set(cache)==set(nodes),'source_study_unreachable_nodes')
    return value


def _contexts(values: object) -> tuple[SourceObservationContext,...]:
    require(type(values) is tuple,'source_study_contexts_tuple')
    result=[]
    for value in values:
        if isinstance(value,Mapping):
            require(set(value)=={f.name for f in fields(SourceObservationContext)},'source_study_context_fields')
            value=SourceObservationContext(**value)
        _context_check(value)
        require(value not in result,'source_study_duplicate_context')
        result.append(value)
    return tuple(result)


def _context_values(values: tuple[SourceObservationContext,...]) -> tuple[Mapping,...]:
    return tuple(MappingProxyType({f.name:getattr(v,f.name) for f in fields(v)}) for v in values)


def _provenance(value: object) -> Mapping:
    require(isinstance(value,Mapping) and all(type(k) is str and bool(k) and type(v) is str for k,v in value.items()),
            'source_study_provenance_strings')
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class SourceStudyRecord:
    canonical_bytes: bytes
    roots: Mapping[str,object]
    contexts: tuple[SourceObservationContext,...]
    captures: tuple[Mapping[str,object],...]
    metadata: Mapping[str,object]
    provenance: Mapping[str,str]
    observations: tuple[SourceObservationRecord | None,...]
    audit: Mapping[str,object]
    validation_scope: str = VALIDATION_SCOPE
    material_qualified: bool = False
    resume_authorized: bool = False

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    def check(self) -> None:
        expected=decode_source_study(self.canonical_bytes,expected_contexts=self.contexts)
        require(self.validation_scope==VALIDATION_SCOPE and self.material_qualified is False
                and self.resume_authorized is False,'source_study_authority_changed')
        actual=_document(self.roots,self.contexts,self.captures,self.metadata,self.provenance)
        require(actual==expected.canonical_bytes,'source_study_record_content_changed')
        require(pack(self.audit)==pack(expected.audit),'source_study_audit_changed')
        require(type(self.observations) is tuple and len(self.observations)==len(expected.observations),
                'source_study_observation_index_changed')
        for actual,original in zip(self.observations,expected.observations):
            require((actual is None)==(original is None),'source_study_observation_changed')
            if actual is not None:
                actual.check();require(actual.canonical_bytes==original.canonical_bytes,'source_study_observation_changed')


def _document(roots,contexts,captures,metadata,provenance) -> bytes:
    data=MappingProxyType(dict(roots=roots,contexts=_context_values(contexts),captures=captures,
                              metadata=metadata,provenance=provenance))
    nodes,root=_graph(data)
    raw=canonical(dict(schema=SCHEMA,validation_scope=VALIDATION_SCOPE,nodes=nodes,root=root,
                       material_qualified=False,resume_authorized=False))
    require(len(raw)<=MAX_RECORD_BYTES,'source_study_byte_limit')
    return raw


def encode_source_study(roots: Mapping[str,object], *, contexts: tuple[SourceObservationContext,...],
        captures: tuple[Mapping[str,object],...]=(), metadata: Mapping[str,object] | None=None,
        provenance: Mapping[str,str] | None=None) -> bytes:
    """Snapshot complete known evidence; no provider queries or runtime replay."""
    try:
        contexts=_contexts(contexts)
        roots,captures,metadata=_snapshot((roots,captures,{} if metadata is None else metadata))
        raw=_document(roots,contexts,captures,metadata,_provenance({} if provenance is None else provenance))
        decode_source_study(raw,expected_contexts=contexts)
        return raw
    except SourceStudyRecordError:raise
    except (ValueError,TypeError,AttributeError,KeyError,IndexError,ArithmeticError,RecursionError) as exc:
        raise SourceStudyRecordError('invalid_source_study:'+str(exc)) from exc


def decode_source_study(raw: bytes, *, expected_contexts=None) -> SourceStudyRecord:
    """Read all saved fields and audit only explicit passive associations."""
    try:
        data=_parse(raw,MAX_RECORD_BYTES)
        require(type(data) is dict and set(data)=={'schema','validation_scope','nodes','root','material_qualified','resume_authorized'},
                'source_study_record_fields')
        require(data['schema']==SCHEMA and data['validation_scope']==VALIDATION_SCOPE
                and data['material_qualified'] is False and data['resume_authorized'] is False,'source_study_schema_or_scope')
        value=_ungraph(data['nodes'],data['root'])
        require(isinstance(value,Mapping) and set(value)=={'roots','contexts','captures','metadata','provenance'},
                'source_study_payload_fields')
        roots,captures,metadata=value['roots'],value['captures'],value['metadata']
        require(isinstance(roots,Mapping) and set(roots)<=ROOT_NAMES and type(captures) is tuple
                and all(isinstance(c,Mapping) for c in captures) and isinstance(metadata,Mapping),'source_study_payload_types')
        contexts=_contexts(value['contexts'])
        if expected_contexts is not None:
            require(contexts==_contexts(expected_contexts),'external_source_study_context_mismatch')
        provenance=_provenance(value['provenance'])
        from .source_study_audit import audit_study
        observations,audit=audit_study(roots,contexts,captures,metadata)
        return SourceStudyRecord(canonical(data),roots,contexts,captures,metadata,provenance,observations,audit)
    except SourceStudyRecordError:raise
    except (ValueError,TypeError,AttributeError,KeyError,IndexError,ArithmeticError,RecursionError) as exc:
        raise SourceStudyRecordError('invalid_source_study:'+str(exc)) from exc


def import_saved_source_study(raw: bytes, *, source_format: str='source_multicell_native_v1',
        provenance: Mapping[str,str] | None=None) -> SourceStudyRecord:
    """Explicit whole old-study import; omitted live fields stay marked absent."""
    try:
        require(source_format=='source_multicell_native_v1','unsupported_source_study_import_format')
        data=_parse(raw,MAX_IMPORT_BYTES)
        require(type(data) is dict and type(data.get('captures')) is list,'source_study_legacy_captures_required')
        converted=_legacy(data)
        captures=converted['captures']
        contexts=[]
        for capture in captures:
            require(isinstance(capture,Mapping),'source_study_capture_mapping')
            state=reify(capture['packed_input'])
            energy=capture.get('energy_identity',state.energy_model_identity)
            evaluation=capture.get('evaluation')
            masses=(tuple(float(s.solid_mass_kg[0]) for s in evaluation.source_states)
                    if evaluation is not None and not has_capture_failure(capture) else
                    tuple(converted.get('adapter_provenance',{}).get('fixed_dry_mass_kg',())))
            context=SourceObservationContext(capture['operator_identity'],energy,masses,capture.get('interface_modes'))
            _context_check(context)
            if context not in contexts:contexts.append(context)
        roots={k:v for k,v in converted.items() if k in ROOT_NAMES}
        metadata={k:v for k,v in converted.items() if k not in ROOT_NAMES and k!='captures'}
        sources=dict({} if provenance is None else provenance)
        sources.update(source_format=source_format,original_file_sha256=hashlib.sha256(raw).hexdigest())
        return decode_source_study(encode_source_study(roots,contexts=tuple(contexts),captures=captures,
            metadata=metadata,provenance=sources))
    except SourceStudyRecordError:raise
    except (ValueError,TypeError,AttributeError,KeyError,IndexError,ArithmeticError,RecursionError) as exc:
        raise SourceStudyRecordError('invalid_legacy_source_study:'+str(exc)) from exc
