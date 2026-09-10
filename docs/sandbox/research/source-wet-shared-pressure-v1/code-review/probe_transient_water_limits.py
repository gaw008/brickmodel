"""One actual source fixture; transient provider-binding probe; no native EOS."""
from dataclasses import replace
from pathlib import Path
import hashlib,json,time
import pytest
from test_source_wet_shared_pressure import actual_wet_pair
from sludge_sandbox.source_wet_shared_pressure import (
    collect_source_wet_pressure_pair,declare_source_shared_wet_volume,_water_metadata,
)
from sludge_sandbox.water_properties import WaterProperties

out=Path('/private/tmp/brick-source-wet-shared-pressure-v1/code-review/transient-water-limits-red')
out.mkdir(exist_ok=False)
start=time.monotonic()
generator=actual_wet_pair.__wrapped__()
try:
    storage,endpoints,calls=next(generator)
    fixture_count=len(calls)
    water=storage.water
    original_limits=water.numerical_limits
    changed_limits=replace(original_limits,pressure_relative=original_limits.pressure_relative*2)
    declaration=declare_source_shared_wet_volume(storage)
    initial_metadata=_water_metadata(storage)
    requests=[]
    actual=WaterProperties.state_tp
    cancel_checks=0
    def cancel():
        global cancel_checks
        object.__setattr__(water,'numerical_limits',changed_limits if cancel_checks==0 else original_limits)
        cancel_checks+=1
        return False
    def observe(w,t,p,*,phase):
        try:
            storage._check()
            binding_ok=True; binding_error=None
        except ValueError as exc:
            binding_ok=False; binding_error=str(exc)
        requests.append({'temperature_k':t,'pressure_pa':p,'original_numerical_limits':w.numerical_limits==original_limits,
                         'full_storage_binding_ok':binding_ok,'full_storage_binding_error':binding_error,
                         'per_point_metadata_unchanged':_water_metadata(storage)==initial_metadata})
        return actual(w,t,p,phase=phase)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(WaterProperties,'state_tp',observe)
        try:
            pair=collect_source_wet_pressure_pair(*endpoints,shared_volume=declaration,cancel=cancel)
            pair.check()
            outcome={'accepted':True,'status':pair.status,'pair_check_passed':True,'attempts':len(pair.evidence.attempts)}
        except Exception as exc:
            outcome={'accepted':False,'exception_type':type(exc).__name__,'exception':str(exc),
                     'attempts':len(getattr(exc,'attempts',()))}
        finally:
            object.__setattr__(water,'numerical_limits',original_limits)
    result={'scope':'Actual SourceWetStorage evaluate/invert under existing manufactured liquid seam; native EOS forbidden by fixture',
            'source_sha256':hashlib.sha256(Path('src/sludge_sandbox/source_wet_shared_pressure.py').read_bytes()).hexdigest(),
            'fixture_requests':fixture_count,'new_manufactured_requests':len(calls)-fixture_count,'native_eos_calls':0,
            'requests':requests,'outcome':outcome,'elapsed_seconds':time.monotonic()-start}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:
    generator.close()
