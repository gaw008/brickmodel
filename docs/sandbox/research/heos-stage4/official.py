import json,math
from pathlib import Path
import CoolProp,CoolProp.CoolProp as CP
from heos_candidate import HEOSCandidate
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage4')
w=HEOSCandidate(case/'expected.json',repo/'data/sandbox/water')
a=CoolProp.AbstractState('HEOS','Water')
checks=json.loads((repo/'data/sandbox/water/official_verification.json').read_text())['checks']
rows=[]
methods=dict(fio='alpha0',fiod='dalpha0_dDelta',fiodd='d2alpha0_dDelta2',fiot='dalpha0_dTau',fiott='d2alpha0_dTau2',fiodt='d2alpha0_dDelta_dTau',fir='alphar',fird='dalphar_dDelta',firdd='d2alphar_dDelta2',firt='dalphar_dTau',firtt='d2alphar_dTau2',firdt='d2alphar_dDelta_dTau')
for check in checks:
    row={k:check[k] for k in ('source','temperature_k','property','expected_printed')}
    try:
        if 'density_kg_m3' in check:
            a.specify_phase(CP.iphase_liquid)
            try:
                a.update(CP.DmassT_INPUTS,check['density_kg_m3'],check['temperature_k'])
                value=getattr(a,methods[check['property']])()
            finally:a.unspecify_phase()
        else:
            prop=check['property'];a.update(CP.QT_INPUTS,1 if 'vapor' in prop else 0,check['temperature_k'])
            value=a.p()/1e6 if prop=='pressure_mpa' else (a.rhomass() if prop.startswith('rho') else (a.hmass()/1000 if prop.startswith('h_') else a.smass()/1000))
        row.update(actual=value,absolute_error=abs(value-check['expected_printed']),passed=math.isclose(value,check['expected_printed'],rel_tol=1e-8,abs_tol=1e-11))
    except Exception as e:row.update(passed=False,error=repr(e))
    rows.append(row)
passed=all(r['passed'] for r in rows)
(case/'official-result.json').write_text(json.dumps({'passed':passed,'scope':'backend_equation_not_material_validation','descriptor':json.loads(w.descriptor_json),'rows':rows},indent=2)+'\n')
print(json.dumps({'passed':passed,'count':len(rows),'failures':[r for r in rows if not r['passed']]}))
raise SystemExit(0 if passed else 1)
