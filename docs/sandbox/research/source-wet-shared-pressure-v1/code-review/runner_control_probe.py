"""Synthetic wrapper control flow only. No physical provider or old run invoked."""
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
from unittest.mock import patch
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import time
import numpy  # Keep passive serializer dependency outside synthetic sys.modules isolation.

ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github')
BASE=Path('/private/tmp/brick-source-wet-shared-pressure-v1/code-review')
RUNNER=BASE.parent/'root/run_native.py'

def passive_load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

wrapper=passive_load(RUNNER,'reviewed_wet_wrapper')
parent=passive_load(ROOT/'docs/sandbox/research'/wrapper.PARENT,'frozen_parent_serializer_only')
serializer=passive_load(ROOT/'docs/sandbox/research'/wrapper.SERIALIZER,'frozen_value_serializer_only')
assert hashlib.sha256((ROOT/'docs/sandbox/research'/wrapper.PARENT).read_bytes()).hexdigest()==wrapper.PARENT_SHA
assert hashlib.sha256((ROOT/'docs/sandbox/research'/wrapper.SERIALIZER).read_bytes()).hexdigest()==wrapper.SERIALIZER_SHA

@dataclass
class ControlVolume:
    value_m3:float=.001
    error_m3:float=1e-12
@dataclass
class ControlDeclaration:
    storage:object
    volume:ControlVolume
@dataclass
class ControlReturnedState:
    temperature_k:float
    pressure_pa:float
    phase:str
    original_fraction:F=F(1,3)
@dataclass
class ControlPair:
    status:str='conditional_shared_wet_pressure_enclosure'
    bound_pa:F=F(1,10**6)
@dataclass
class ControlTransition:
    pressure_strategy:str='explicit_shared_source_wet_and_dry_volume'
    numerical_event_accepted:bool=False
    material_qualified:bool=False

results=[]
started=time.monotonic()
for scenario in ('success','second_request_failure','collector_validation_failure','resource_limit','pure_compare_call','cap_exhausted'):
    package=ModuleType('sludge_sandbox'); package.__path__=[]
    transition=ModuleType('sludge_sandbox.source_dry_transition')
    wet=ModuleType('sludge_sandbox.source_wet_shared_pressure')
    heos=ModuleType('sludge_sandbox.water_heos')
    calls=[]
    class ControlProvider:
        def state_tp(self,temperature,pressure,*,phase):
            calls.append((temperature,pressure,phase))
            if scenario=='second_request_failure' and len(calls)==2:
                raise RuntimeError('synthetic_second_request_failure')
            if scenario=='resource_limit':
                raise TimeoutError('synthetic_parent_resource_limit')
            return ControlReturnedState(temperature,pressure,phase)
    provider=ControlProvider()
    heos.HEOSWaterProperties=ControlProvider
    storages=tuple(NS(model_identity='synthetic-control',volume=ControlVolume(),water=provider) for _ in range(3))
    column=NS(cell_count=3,storages=storages)
    refinement=NS(approach=NS(proposal=NS(original_trial=NS(adapter=NS(column=column)),choice=NS(selected_root=NS(polynomial=NS(cell=1))))))
    wet.declare_source_shared_wet_volume=lambda storage:ControlDeclaration(storage,storage.volume)
    def collect(a,b,*,shared_volume,cancel=None):
        count=17 if scenario=='cap_exhausted' else 2
        for index in range(count):
            shared_volume.storage.water.state_tp(325.,100000.+index,phase='liquid')
        if scenario=='collector_validation_failure':
            exc=ValueError('synthetic_validation_after_two_returns')
            exc.attempts=({'returned':True},)*2
            raise exc
        return ControlPair()
    wet.collect_source_wet_pressure_pair=collect
    def compare(*args,**kwargs):
        if scenario=='pure_compare_call':
            provider.state_tp(325.,100000.,phase='liquid')
        return ControlTransition()
    transition.compare_source_dry_candidates=compare
    def evaluate(refinement,*,shared_wet_volumes,**kwargs):
        for phase in range(2):
            for declaration in shared_wet_volumes:
                if declaration is not None:
                    wet.collect_source_wet_pressure_pair(F(phase),F(phase+1),shared_volume=declaration)
        return transition.compare_source_dry_candidates()
    transition.evaluate_source_dry_transition=evaluate
    package.source_dry_transition=transition
    package.source_wet_shared_pressure=wet
    package.water_heos=heos
    def fake_parent_run(root,output):
        data={'pressure_strategy':'explicit_shared_source_dry_volume','numerical_event_accepted':False,
              'old_pressure_gates':[False,True,False], 'physical_scope':'synthetic control only'}
        try:
            value=transition.evaluate_source_dry_transition(refinement)
            data.update(status='completed',transition=parent.saved_record(value,serializer.serialize))
            code=0
        except Exception as exc:
            data.update(status='resource_limit' if scenario=='resource_limit' else 'failed',
                        exception_type=type(exc).__name__,exception=str(exc))
            code=1
        Path(output).write_text(json.dumps(data,indent=2)+'\n')
        print('synthetic preserved parent stdout')
        return code
    def fake_load(root,name,digest):
        if name==wrapper.PARENT:
            return NS(saved_record=parent.saved_record,run=fake_parent_run)
        if name==wrapper.SERIALIZER:
            return serializer
        raise AssertionError(name)
    out=BASE/'runner-control-output-final'/scenario
    out.parent.mkdir(exist_ok=True)
    modules={name:getattr(package,name.rsplit('.',1)[-1]) for name in ('sludge_sandbox.source_dry_transition','sludge_sandbox.source_wet_shared_pressure','sludge_sandbox.water_heos')}
    modules['sludge_sandbox']=package
    captured=io.StringIO()
    with patch.dict(sys.modules,modules), patch.object(wrapper,'load',fake_load),contextlib.redirect_stdout(captured):
        code=wrapper.run(ROOT,out)
    summary=json.loads((out/'pressure-observations.json').read_text())
    final=json.loads((out/'native-result.json').read_text())
    raw=(out/'parent-native-result.json').read_bytes()
    assert summary['parent_output_sha256']==hashlib.sha256(raw).hexdigest()
    assert final['inherited_parent_initial_strategy_label']=='explicit_shared_source_dry_volume'
    assert final['old_pressure_gates']==[False,True,False]
    assert 'synthetic preserved parent stdout' in (out/'parent-stdout.log').read_text()
    assert summary['parent_exit_code']==code
    if scenario=='success':
        assert code==0 and summary['status']=='completed'
        assert len(calls)==len(summary['extra_requests'])==8
        assert summary['distinct_extra_request_keys']==2
        assert final['pressure_strategy']=='explicit_shared_source_wet_and_dry_volume'
        assert all(r['status']=='returned' and 'water_state' in r for r in summary['extra_requests'])
    elif scenario=='second_request_failure':
        assert code==1 and len(calls)==2 and len(summary['extra_requests'])==2
        assert summary['extra_requests'][0]['status']=='returned'
        assert summary['extra_requests'][1]['status']=='failed'
        assert summary['wet_pairs'][0]['status']=='failed'
    elif scenario=='collector_validation_failure':
        assert code==1 and len(calls)==2
        assert all(r['status']=='returned' and 'water_state' in r for r in summary['extra_requests'])
        assert len(summary['wet_pairs'][0]['attempts'])==2
    elif scenario=='resource_limit':
        assert code==1 and summary['status']=='resource_limit'
        assert summary['extra_requests'][0]['exception_type']=='TimeoutError'
    elif scenario=='pure_compare_call':
        assert code==1 and summary['pure_comparison_eos_attempts']==1 and len(calls)==8
    elif scenario=='cap_exhausted':
        assert code==1 and len(calls)==len(summary['extra_requests'])==16
        assert 'wet_pair_request_cap' in summary['wet_pairs'][0]['exception']
    results.append({'case':scenario,'status':summary['status'],'code':code,'synthetic_requests':len(calls),
                    'returned_records':sum(r['status']=='returned' for r in summary['extra_requests']),
                    'pure_comparison_eos_attempts':summary['pure_comparison_eos_attempts'],'passed':True})
output={'scope':'synthetic wrapper control probes; no physical modules imported, no actual EOS/provider construction/old parent.run',
        'runner_sha256':hashlib.sha256(RUNNER.read_bytes()).hexdigest(),'cases':results,
        'elapsed_seconds':time.monotonic()-started,'actual_eos_calls':0}
(BASE/'RUNNER_CONTROL_RESULT.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
