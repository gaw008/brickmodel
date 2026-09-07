import json,warnings
from pathlib import Path
from heos_candidate import HEOSCandidate
from sludge_sandbox.water_properties import WaterNumericalError,WaterSourceError
root=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage3')
w=HEOSCandidate(case/'expected.json',root/'data/sandbox/water')
results=[]
class Proxy:
    def __init__(self,target,name,replacement):self.target,self.name,self.replacement=target,name,replacement
    def __getattr__(self,name):return self.replacement if name==self.name else getattr(self.target,name)
def failure(name,action,kind):
    try:action()
    except kind as e:results.append({'test':name,'error':type(e).__name__,'message':str(e)})
    else:raise AssertionError('fault accepted:'+name)
try:
    original=w._flash
    object.__setattr__(w,'_flash',Proxy(original,'umass',lambda:original.umass()+.01))
    try:failure('native_u_corruption',lambda:w.saturation_pair(300.),WaterNumericalError)
    finally:object.__setattr__(w,'_flash',original)
    original=w._check
    object.__setattr__(w,'_check',Proxy(original,'d2alphar_dDelta2',lambda:float('nan')))
    try:failure('nonfinite_derivative',lambda:w.saturation_pair(300.),WaterNumericalError)
    finally:object.__setattr__(w,'_check',original)
    original=w._flash
    def warned(*args):
        warnings.warn('injected_native_warning',RuntimeWarning)
        return original.update(*args)
    object.__setattr__(w,'_flash',Proxy(original,'update',warned))
    try:failure('native_warning',lambda:w.saturation_pair(300.),WaterNumericalError)
    finally:object.__setattr__(w,'_flash',original)
    CP=w._cp;key=CP.ENABLE_SUPERANCILLARIES;before=CP.get_config_bool(key)
    CP.set_config_bool(key,not before)
    try:failure('runtime_config_change',lambda:w.saturation_pair(300.),WaterSourceError)
    finally:CP.set_config_bool(key,before)
    bad=json.loads((case/'expected.json').read_text());bad['adapter_sha256']='0'*64
    path=case/'bad-manifest.json';path.write_text(json.dumps(bad))
    failure('bad_adapter_manifest',lambda:HEOSCandidate(path,root/'data/sandbox/water'),WaterSourceError)
finally:
    (case/'fault-results.json').write_text(json.dumps({'passed':len(results)==5,'cases':results},indent=2)+'\n')
assert len(results)==5
