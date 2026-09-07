import json,traceback
from pathlib import Path
from dataclasses import asdict
from heos_candidate import HEOSCandidate
from sludge_sandbox.water_properties import load_water_properties
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage4')
new=HEOSCandidate(case/'expected.json',repo/'data/sandbox/water');old=load_water_properties(repo/'data/sandbox/water')
result={'descriptor':json.loads(new.descriptor_json),'rows':[]}
for t in (293.,300.,350.,400.,450.,500.):
    oldpair=old.saturation_pair(t)
    for kind,phase,p in [('sat','liquid',oldpair.pressure_pa),('sat','vapor',oldpair.pressure_pa),('tp','vapor',.1*oldpair.pressure_pa),('tp','liquid',2*oldpair.pressure_pa),('tp','liquid',1e8)]:
        row={'t':t,'p':p,'phase':phase,'kind':kind,'status':'running'}
        try:
            if kind=='sat':
                pair=new.saturation_pair(t)
                a=pair[0 if phase=='liquid' else 1]
                b=oldpair.liquid if phase=='liquid' else oldpair.vapor
            else:
                a=new.state_tp(t,p,phase=phase);b=old.state_tp(t,p,phase=phase)
            row['candidate']=asdict(a);row['original']=asdict(b)
            diffs={k:abs(getattr(a,k)-getattr(b,n)) for k,n in [('density','density_kg_m3'),('h','native_enthalpy_j_kg'),('u','native_internal_energy_j_kg'),('s','native_entropy_j_kg_k'),('cp','cp_j_kg_k'),('cv','cv_j_kg_k')]}
            row['differences']=diffs
            assert diffs['density']<=2e-8*b.density_kg_m3
            assert max(diffs['h'],diffs['u'],t*diffs['s'])<=.002
            assert max(diffs['cp'],diffs['cv'])<=1e-5
            row['status']='passed'
        except Exception as e:
            row['status']='failed';row['error']=repr(e);row['traceback']=traceback.format_exc()
        row['coexistence']=new.last_coexistence
        result['rows'].append(row)
        (case/'grid-result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
result['passed']=all(r['status']=='passed' for r in result['rows'])
(case/'grid-result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({'passed':result['passed'],'passed_cases':sum(r['status']=='passed' for r in result['rows']),'failed':[{k:r[k] for k in ('t','p','kind','phase','error')} for r in result['rows'] if r['status']=='failed']},indent=2))
raise SystemExit(0 if result['passed'] else 1)
