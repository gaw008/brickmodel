from dataclasses import asdict
import json,traceback
from pathlib import Path
from heos_candidate import HEOSCandidate
from sludge_sandbox.water_properties import load_water_properties,WaterDomainError
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
case=Path('/private/tmp/brick-heos-stage3')
result={'status':'running','rows':[]}
try:
    w=HEOSCandidate(case/'expected.json',root/'data/sandbox/water')
    old=load_water_properties(root/'data/sandbox/water')
    result['descriptor']=json.loads(w.descriptor_json)
    pair=w.saturation_pair(300.)
    original_pair=old.saturation_pair(300.)
    comparisons=[]
    for new,reference in zip(pair,(original_pair.liquid,original_pair.vapor)):
        comparisons.append((new,reference))
    for p in (304469.31354,567435.65536):
        comparisons.append((w.state_tp(300.,p,phase='liquid'),old.state_tp(300.,p,phase='liquid')))
    for new,reference in comparisons:
        differences={k:abs(getattr(new,k)-getattr(reference,name)) for k,name in [('density','density_kg_m3'),('h','native_enthalpy_j_kg'),('u','native_internal_energy_j_kg'),('s','native_entropy_j_kg_k'),('cp','cp_j_kg_k'),('cv','cv_j_kg_k')]}
        result['rows'].append({'candidate':asdict(new),'old':asdict(reference),'differences':differences})
        assert differences['density']<=2e-8*reference.density_kg_m3
        assert differences['h']<=.002 and differences['u']<=.002 and differences['s']*300<=.002
        assert differences['cp']<=1e-5 and differences['cv']<=1e-5
    result['domain_errors']=[]
    for t,p,phase in ((292.,1e5,'liquid'),(300.,-1.,'liquid'),(300.,1e8+1,'liquid'),(300.,1e5,'bad'),(300.,pair[0].pressure,'liquid'),(300.,1e5,'vapor')):
        try:w.state_tp(t,p,phase=phase)
        except WaterDomainError as e:result['domain_errors'].append(str(e))
        else:raise AssertionError('expected domain rejection')
    result['status']='passed'
except BaseException as e:
    result['status']='failed'
    result['error']=repr(e)
    result['traceback']=traceback.format_exc()
    raise
finally:
    (case/'result01.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
