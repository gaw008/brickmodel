"""Independent bounded unit-converter controls, 0 EOS and no old arithmetic."""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCE=Path('/Users/wanggaoying/Desktop/brickmodel-github/data/sandbox/research/gnest2021/energy-source-check-v1')
OUT=Path(sys.argv[1])
OUT.mkdir(exist_ok=False)
script=(SOURCE/'check_units.py').read_bytes()
facts_raw=(SOURCE/'facts.json').read_bytes()
facts=json.loads(facts_raw)
expected={'Cp_J_kg_K':dict(zip(('feed','HRN1','HRN2','HRN3','HRN4','HRN5'),('1490','1550','1510','1580','1520','1480'))),
          'HHV_MJ_kg':dict(zip(('feed','char_250C','char_550C','char_700C'),('1311/100','7059/500','4307/500','4097/500'))),
          'reaction_heat_identified':False}
variants=[('normal',None,None,True),
          ('cp_wrong_unit',('thesis_table8_1','unit'),'J/kg/K',False),
          ('hhv_wrong_unit',('ion_figure7','unit'),'MJ/kg',False),
          ('hhv_wrong_basis',('ion_figure7','basis'),'wet',False),
          ('promote_material',('qualification','material_qualified'),True,False),
          ('promote_reaction_heat',('qualification','reaction_heat_identified'),True,False),
          ('promote_same_batch',('qualification','same_batch_GNEST2021'),True,False),
          ('cp_wrong_source',('thesis_table8_1','source_id'),'ion2026',False),
          ('promote_cp_moisture_basis',('thesis_table8_1','moisture_mass_basis_explicit_for_DSC'),'dry',False)]
results=[]
for name,path,value,allowed in variants:
    case=deepcopy(facts)
    if path:
        case[path[0]][path[1]]=value
    dest=OUT/name;dest.mkdir()
    (dest/'check_units.py').write_bytes(script)
    (dest/'facts.json').write_text(json.dumps(case,indent=2)+'\n')
    proc=subprocess.run([sys.executable,str(dest/'check_units.py')],capture_output=True,timeout=3)
    (dest/'stdout.txt').write_bytes(proc.stdout);(dest/'stderr.txt').write_bytes(proc.stderr)
    accepted=proc.returncode==0
    if accepted:
        assert json.loads(proc.stdout)==expected
    results.append(dict(case=name,expected_accept=allowed,actual_accept=accepted,
                        returncode=proc.returncode,passed=(allowed==accepted)))
result=dict(scope='unit conversion and declared unknown-basis/qualification guards only',
            script_sha256=hashlib.sha256(script).hexdigest(),facts_sha256=hashlib.sha256(facts_raw).hexdigest(),
            cases=results,passed=sum(r['passed'] for r in results),total=len(results),eos_calls=0)
(OUT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
