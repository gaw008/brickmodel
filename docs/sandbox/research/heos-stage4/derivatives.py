"""Same seven cases, finite-difference steps and acceptance gates as production test_water_response.py."""
from dataclasses import asdict
from pathlib import Path
import json,math,traceback
from heos_candidate import HEOSCandidate
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage4')
w=HEOSCandidate(case/'expected.json',repo/'data/sandbox/water')
rows=[]
for t,p,phase in [(300.,1e5,'liquid'),(350.,1e6,'liquid'),(450.,1e7,'liquid'),(499.,9e7,'liquid'),(300.,1e3,'vapor'),(400.,1e5,'vapor'),(499.,1e5,'vapor')]:
    row={'t':t,'p':p,'phase':phase}
    try:
        dt=.01;dp=max(1.,1e-4*p)
        c=w.state_tp(t,p,phase=phase)
        tp=w.state_tp(t+dt,p,phase=phase);tm=w.state_tp(t-dt,p,phase=phase)
        pp=w.state_tp(t,p+dp,phase=phase);pm=w.state_tp(t,p-dp,phase=phase)
        def volume(s):return w.reference.molar_mass_kg_mol/s.density
        def energy(s):return s.u*w.reference.molar_mass_kg_mol+w.reference.energy_offset_j_mol
        approximations=((volume(tp)-volume(tm))/(2*dt),(volume(pp)-volume(pm))/(2*dp),(energy(pp)-energy(pm))/(2*dp))
        actual=(c.dv_dt,c.dv_dp,c.du_dp)
        limits=((2e-5,1e-13),(2e-5,1e-17),(2e-4,1e-8))
        row.update({'dt':dt,'dp':dp,'snapshots':[asdict(s) for s in (c,tp,tm,pp,pm)],'finite_difference':approximations,'analytic':actual,'limits':limits,'public_mass':w.reference.molar_mass_kg_mol,'offset':w.reference.energy_offset_j_mol})
        assert all(math.isclose(a,b,rel_tol=r,abs_tol=z) for a,b,(r,z) in zip(actual,approximations,limits))
        assert c.kappa>0 and c.dv_dp<0 and c.residuals[-1]<=1e-7
        row['status']='passed'
    except Exception as e:row.update({'status':'failed','error':repr(e),'traceback':traceback.format_exc()})
    rows.append(row)
    (case/'derivative-result.json').write_text(json.dumps({'rows':rows},indent=2)+'\n')
passed=all(r['status']=='passed' for r in rows)
(case/'derivative-result.json').write_text(json.dumps({'passed':passed,'rows':rows},indent=2)+'\n')
print(json.dumps({'passed':passed,'cases':len(rows),'failures':[r.get('error') for r in rows if r['status']=='failed']}))
raise SystemExit(0 if passed else 1)
