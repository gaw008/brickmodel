"""Reconstructed reproducible form of the inline audit; not its byte-exact transcript.
No production imports or EOS. This file was saved after the successful inline audit
and has not been rerun. Original measured output is audit-metrics.json.
"""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib

b=Path(__file__).parent
p=json.loads((b/'attempt01.json').read_text())
h=json.loads((b/'source-before.json').read_text())
assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in h.items())
s=json.loads((b/'attempt01.status.json').read_text())
assert s['exit_code']==0 and s['source_unchanged'] and p['status']=='passed'
def q(x):return F(x['numerator'],x['denominator'])
metrics=[];temperatures=[]
for run in p['runs']:
 r=run['result'];s0=p['initial']
 assert r['status']=='completed' and r['times_s'][-1]==1e-4 and r['states'][0]==s0
 assert all(k in r['times_s'] for k in (3e-5,7e-5))
 mx=dict(water=F(),localE=F(),globalE=F(),mech=F(),mechq=F())
 ei=[F()]*2;mi=[F()]*3;mq=[F()]*3;ma=[F()]*3;boundary=cr=ce=F()
 for j,(state,ledger) in enumerate(zip(r['states'][1:],r['steps'])):
  assert ledger['start_s']==r['times_s'][j] and ledger['end_s']==r['times_s'][j+1]
  assert not any(ledger['start_s']<k<ledger['end_s'] for k in (3e-5,7e-5))
  assert state['energy_model_identity']==s0['energy_model_identity'] and min(state['mechanical_stretches'])>0
  assert set(ledger['cell_work_components_j'])=={'external_traction','mechanical_constraint','body'}
  assert all(v==0 for row in ledger['face_species_mol'] for v in row)
  for i,row in enumerate(state['amounts_mol']):
   old=s0['amounts_mol'][i];assert row[1]==old[1] and row[3]==old[3]
   mx['water']=max(mx['water'],abs(F(row[0])+F(row[2])-F(old[0])-F(old[2])))
   ei[i]+=F(ledger['face_energy_j'][i])-F(ledger['face_energy_j'][i+1])+F(ledger['cell_work_j'][i])
   mx['localE']=max(mx['localE'],abs(F(state['internal_energy_j'][i])-F(s0['internal_energy_j'][i])-ei[i]))
  for i in range(3):
   mi[i]+=F(ledger['stretch_increment'][i]);z=q(ledger['stretch_quadrature_roundoff'][i]);mq[i]+=z;ma[i]+=abs(z)
   delta=F(state['mechanical_stretches'][i])-1
   mx['mech']=max(mx['mech'],abs(delta-mi[i]),abs(delta-mi[i]+mq[i]));mx['mechq']=max(mx['mechq'],ma[i])
  cs=ledger['cell_work_components_j']['mechanical_constraint'];cq=ledger['component_quadrature_roundoff_j']['mechanical_constraint']
  cr+=abs(sum(map(F,cs),F()));ce+=abs(sum((F(v)-q(z) for v,z in zip(cs,cq)),F()))
  boundary+=F(ledger['face_energy_j'][0])-F(ledger['face_energy_j'][-1])
  n0,n1,t=map(F,state['mechanical_stretches']);de=sum((F(v)-F(z) for v,z in zip(state['internal_energy_j'],s0['internal_energy_j'])),F())
  mx['globalE']=max(mx['globalE'],abs(de+101325*F(.00014)*((n0+n1)*t*t-2)-boundary))
 assert boundary>0 and max(cr,ce)<F(1e-6)
 for k,v in mx.items():assert v<F(1e-11 if k=='water' else 4e-6 if k=='globalE' else 1e-9 if k.startswith('mech') else 1e-6)
 snap=run['final_callback'];n0,n1,t=map(F,r['states'][-1]['mechanical_stretches'])
 area=F(.014)*t*t;width=F(.01)*n1;ts=F(snap['surface_temperature_k']);tc=F(snap['gas_states'][-1]['temperature_k'])
 cond=F(.2)*area*(ts-tc)/(width/2);conv=20*area*(F(304)-ts);rad=F(.5)*F(5.670374419e-8)*area*(F(306)**4-ts**4)
 assert abs(cond-F(snap['conductive_into_cell_w']))<F(1e-8)
 assert abs(conv-F(snap['heat']['convective_in_w']))<F(1e-10) and abs(rad-F(snap['heat']['radiative_in_w']))<F(1e-10)
 assert abs(cond-conv-rad)<F(1e-8) and abs(snap['surface_balance_residual_w'])<=snap['surface_balance_limit_w']
 assert snap['operator_identity']==p['operator_identity'] and set(snap['source_ids'])<=set(p['source_ids'])
 temperatures.append([v['temperature_k'] for v in snap['gas_states']])
 metrics.append(dict(steps=len(r['steps']),evaluations=r['evaluations'],maxima={k:float(v) for k,v in mx.items()},boundary_input_j=float(boundary),constraint_rep=float(cr),constraint_exact=float(ce),surface_independent_residual_w=float(cond-conv-rad)))
a,c=[r['result']['states'][-1] for r in p['runs']];diff={}
for key,tol in [('amounts_mol',1e-11),('internal_energy_j',2e-6),('mechanical_stretches',2e-7)]:
 aa=sum(a[key],[]) if key=='amounts_mol' else a[key];cc=sum(c[key],[]) if key=='amounts_mol' else c[key]
 d=max(abs(F(x)-F(y)) for x,y in zip(aa,cc));assert d<F(tol);diff[key]=float(d)
diff['temperature_k']=max(abs(x-y) for x,y in zip(*temperatures));assert diff['temperature_k']<2e-6
assert metrics[1]['steps']>metrics[0]['steps'] and p['runs'][0]['result']['times_s']!=p['runs'][1]['result']['times_s']
print(json.dumps(dict(metrics=metrics,endpoint_differences=diff),indent=2))
