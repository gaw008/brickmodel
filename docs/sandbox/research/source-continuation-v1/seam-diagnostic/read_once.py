from pathlib import Path
from fractions import Fraction
from collections.abc import Mapping
from dataclasses import fields,is_dataclass
import json, hashlib, time
from unittest.mock import patch
from sludge_sandbox.source_study_record import decode_source_study
from sludge_sandbox.source_study_schema import SourceStudyNode
from sludge_sandbox.source_run_observer import observer_scope
from sludge_sandbox.water_properties import WaterProperties
from sludge_sandbox.source_wet_storage import SourceWetStorage

path=Path('/private/var/folders/rs/k20kkfj95cq_ph554v_g_g480000gn/T/pytest-of-wanggaoying/pytest-340/source-trajectory-parent0/run/source-study-record.json')
out=Path(__file__).parent
attempts=[]
def forbidden(*a,**kw):
    attempts.append('forbidden physics')
    raise AssertionError('passive diagnostic must not invoke physics')
def plain(value,depth=4):
    if value is None or type(value) in (bool,str,int,float):return value
    if type(value) is Fraction:return {'exact':str(value),'float':float(value)}
    if depth<0:return {'type':type(value).__name__}
    if isinstance(value,SourceStudyNode):return {k:plain(v,depth-1) for k,v in value.values.items()}
    if isinstance(value,Mapping):return {str(k):plain(v,depth-1) for k,v in value.items()}
    if isinstance(value,tuple):return [plain(v,depth-1) for v in value]
    if is_dataclass(value):return {f.name:plain(getattr(value,f.name),depth-1) for f in fields(value)}
    return str(type(value))
def selected(node,names,depth=3):return {k:plain(getattr(node,k),depth) for k in names if hasattr(node,k)}
raw=path.read_bytes();start=time.monotonic()
with observer_scope(forbidden),patch.object(WaterProperties,'state_tp',forbidden),patch.object(SourceWetStorage,'evaluate',forbidden),patch.object(SourceWetStorage,'invert',forbidden):
    record=decode_source_study(raw)
t=record.roots['transition']
result={'source_path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'decode_seconds':time.monotonic()-start,'physics_attempts':attempts,'transition':selected(t,tuple(k for k in t.values if 'gate' in k or 'pressure' in k or k in ('numerical_event_accepted','material_qualified','clock_comparison'))),'pairs':[],'metadata':selected(record,('metadata',),1)}
result['transition'].pop('wet_pressure_pairs',None)
for row in t.wet_pressure_pairs:
    for pair in row:
        if pair is None:continue
        item=selected(pair,('status','reason','residual_interval_m3','compliance_lower_m3_pa','root_difference_bound_pa','joint_bound_pa','independent_bound_pa','selected_bound_pa','error_parts','evidence'),3)
        item['pair_fields']=list(pair.values)
        item['endpoints']=[]
        for e in pair.endpoints:
            item['endpoints'].append({'state':plain(e.state,2),'inverse':selected(e.inverse,('temperature_error_bound_k','temperature_bracket_k','energy_residual_j','iterations','temperature_error_k'),2),'point':selected(e.inverse.point,('temperature_k','pressure_pa','pressure_error_pa','energy_error_j','extra_pressure_error_pa','available_volume_error_m3'),2),'continuation':plain(e.continuation,2),'fluid':selected(e.inverse.point.fluid,('pressure_error_bound_pa','energy_error_bound_j','mechanical'),2)})
        result['pairs'].append(item)
(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'decode_seconds':result['decode_seconds'],'sha256':result['sha256'],'physics_attempts':attempts,'transition_fields':list(t.values),'pairs':len(result['pairs'])}))
