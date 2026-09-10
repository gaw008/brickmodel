"""Offline saved native source-trial audit. No project imports or EOS.
Run only after parent terminal notice: python audit.py PATH EXPECTED_SHA.
"""
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,math,sys,time
OUT=Path(__file__).parent
checks=0
def ck(ok,label):
 global checks
 checks+=1
 if not ok:raise AssertionError(label)
def decode(x):
 if isinstance(x,list):return [decode(v) for v in x]
 if isinstance(x,dict):
  if set(x)=={'numerator','denominator'}:return F(x['numerator'],x['denominator'])
  if set(x)=={'type','fields'}:return decode(x['fields'])
  if 'dtype' in x and 'values' in x:return decode(x['values'])
  return {k:decode(v) for k,v in x.items()}
 return x
def flat(a):return [v for row in a for v in row] if a and isinstance(a[0],list) else a
def matrix(a):return [a[i:i+4] for i in range(0,len(a),4)]
def values(s):return flat(s['amounts_mol'])+s['internal_energy_j']
def state(n,u,original):return dict(original,amounts_mol=matrix(n),internal_energy_j=u)
def rounded(x):return float(x)
def fsum(*x):return float(sum(map(F,x),F()))
def incidence(fields):
 fn,fu,rn,w=fields
 return [fsum(fn[i],-fn[i+4],rn[i]) for i in range(len(rn))],[fsum(fu[i],-fu[i+1],w[i]) for i in range(len(w))]
NAMES=('face_species_mol_s','face_energy_w','reaction_species_mol_s','cell_power_w')
LEDGER=('face_species_mol','face_energy_j','reaction_species_mol','cell_work_j')
def ratefields(c):return [flat(c['evaluation']['rates'][k]) for k in NAMES]
def euler(s,c,h):
 dn,du=incidence(ratefields(c))
 return state([fsum(x,float(h*F(d))) for x,d in zip(flat(s['amounts_mol']),dn)], [fsum(x,float(h*F(d))) for x,d in zip(s['internal_energy_j'],du)],s)
def heun(s,c0,c1,h):
 ck(c1['state']==euler(s,c0,h),'reference Euler input')
 ff=[[fsum(float(h/2*F(x)),float(h/2*F(y))) for x,y in zip(a,b)] for a,b in zip(ratefields(c0),ratefields(c1))]
 dn,du=incidence(ff)
 return state([fsum(x,d) for x,d in zip(flat(s['amounts_mol']),dn)],[fsum(x,d) for x,d in zip(s['internal_energy_j'],du)],s),ff
def normalized(a,b,policy):
 ns=policy['amount_absolute_tolerance_mol']+policy['relative_tolerance']*policy['amount_scale_mol'];us=policy['energy_absolute_tolerance_j']+policy['relative_tolerance']*policy['energy_scale_j']
 return max(max(abs(x-y) for x,y in zip(flat(a['amounts_mol']),flat(b['amounts_mol'])))/ns,max(abs(x-y) for x,y in zip(a['internal_energy_j'],b['internal_energy_j']))/us)
def run(path,expected):
 begin=time.monotonic();sha=hashlib.sha256(path.read_bytes()).hexdigest();ck(sha==expected,'input SHA');r=decode(json.loads(path.read_text()));summary={'input_sha256':sha,'original_status':r['status']}
 # Honest terminal failure handling: preserve it and map available captures,
 # without pretending incomplete data supplies successful numerical evidence.
 outer=r.get('captures',[]);t=r.get('trial')
 if t is None:
  summary.update(status='terminal_without_returned_trial',actual_captures=len(outer),completed_captures=sum('evaluation' in x for x in outer),checks=checks)
  return summary
 caps=t['captures'];ck(len(outer)==len(caps),'all actual callbacks retained')
 for i,(o,c) in enumerate(zip(outer,caps)):
  ck(o['ordinal']==c['ordinal']==i+1 and o['time']==c['time'] and o['packed_input']==c['state'],'outer/wrapper inputs')
  if 'evaluation' in o:ck(o['evaluation']==c['evaluation'],'outer/wrapper output')
 if r['status']!='validated_positive_numerical_trial':
  summary.update(status='failure_preserved_no_success_claim',trial_status=t['status'],reason=t['reason'],actual_captures=len(caps),completed_captures=sum(c['evaluation'] is not None for c in caps),checks=checks)
  return summary
 ck(t['status']==r['status'] and t['reason'] is None,'success status')
 pol=t['policy'];ck(pol==r['policy'],'original policy');ck(dict(t['policy_binding'])==pol,'policy binding')
 expectedscience=[1/1024,1/1024,1/16384,1e-8,1e-7,1e-3,1.,1e5,4,4,180.]
 ck(r['policy_values']==expectedscience and r['maximum_callbacks']==32 and r['outer_seconds']==210.,'prepared science/resources')
 ck(t['maximum_callbacks']==32 and len(caps)<=32,'callback cap')
 rp=t['reference_policy'];ck(all(rp[k]==v for k,v in pol.items() if k!='maximum_wall_seconds') and 0<rp['maximum_wall_seconds']<=180.,'reference science/resource')
 start,end=t['start']['seconds'],t['end']['seconds'];h=end-start;ck(h==F(1,16384),'same exact requested span')
 initial=t['initial'];ck(initial==r['initial'] and caps[0]['state']==initial,'initial')
 ck([c['role'] for c in caps[:3]]==['initial','euler_midpoint','prefix_terminal'],'three actual roles')
 ck([c['time']['seconds'] for c in caps[:3]]==[start,start+h/2,end],'three exact times')
 ck(t['predictor']==caps[1]['state']==euler(initial,caps[0],h/2),'independent predictor')
 for c in caps:
  ck(c['evaluation'] is not None and c['failure'] is None and c['binding'] is not None,'successful capture')
  ev=c['evaluation'];ck(ev['time']==c['time'] and ev['operator_identity']==t['operator_identity'],'capture time/operator')
  ck(c['state']['energy_model_identity']==t['energy_identity'],'capture energy identity')
  ck(ev['material_qualified'] is False and ev['source_evaluation']['material_qualified'] is False,'no material grant')
  for i,s in enumerate(ev['source_states']):ck(s['solid_mass_kg']==[t['fixed_dry_mass_kg'][i]],'fixed dry mass')
 p=t['prefix'];ck(p['raw_state']==caps[2]['state'] and p['status']=='strictly_positive_numerical_prefix','actual terminal state')
 # Serialized SourcePrefix includes its bound panel. Its midpoint is actual.
 ck(p['panel']['first']['state']==initial and p['panel']['interior']['state']==caps[1]['state'],'prefix panel actual inputs')
 ck(p['policy']==pol and dict(p['policy_binding'])==pol,'prefix unchanged policy')
 ck(p['panel']['sample_bindings'][:2]==[caps[0]['binding'],caps[1]['binding']],'prefix sample bindings')
 ff=ratefields(caps[1]);exact=[[h*F(x) for x in row] for row in ff];rep=[[float(x) for x in row] for row in exact];records={n:(x,e) for n,x,e in p['integrals']}
 for name,field,x,v in zip(NAMES,LEDGER,exact,rep):
  ck(records[name][0]==x and records[name][1]==[F(a)-b for a,b in zip(v,x)],'prefix exact integral/projection')
  ck(flat(p['ledger'][field])==v,'prefix ledger integral')
  tol=F(pol['energy_absolute_tolerance_j'] if name in ('face_energy_w','cell_power_w') else pol['amount_absolute_tolerance_mol']);ck(all(abs(e)<=tol for e in records[name][1]),'prefix integral budget')
 for energy in (False,True):
  w=1 if energy else 4
  idx=1 if energy else 0;loc=3 if energy else 2;old=initial['internal_energy_j'] if energy else flat(initial['amounts_mol']);after=p['raw_state']['internal_energy_j'] if energy else flat(p['raw_state']['amounts_mol']);suffix='j' if energy else 'mol'
  exactdelta=[exact[idx][i]-exact[idx][i+w]+exact[loc][i] for i in range(len(old))];repdelta=[F(rep[idx][i])-F(rep[idx][i+w])+F(rep[loc][i]) for i in range(len(old))]
  ck(after==[float(F(x)+d) for x,d in zip(old,repdelta)],'prefix state projection')
  estate=[F(y)-F(x)-d for x,y,d in zip(old,after,repdelta)];full=[F(y)-F(x)-d for x,y,d in zip(old,after,exactdelta)]
  ck(p['state_roundoff_'+suffix]==estate and p['full_residual_'+suffix]==full,'prefix state/full residual')
  tol=F(pol['energy_absolute_tolerance_j'] if energy else pol['amount_absolute_tolerance_mol']);ck(all(abs(x)<=tol for x in estate+full),'prefix original state/full budget')
 # Whole-prefix minima and source energy decomposition are independently saved.
 for q,row in zip(p['panel']['inventories'],p['minima']):
  nn,rr,qq=q['initial'],q['linear'],q['quadratic'];points=[F(),h]
  if qq>0 and 0 < -rr/(2*qq) < h:points.append(-rr/(2*qq))
  minimum,when=min((nn+rr*x+qq*x*x,x) for x in points)
  ck(row==[q['family'],q['cell'],q['index'],minimum,when] and nn>0 and minimum>0,'whole prefix positive')
 for face,d in zip(caps[1]['evaluation']['source_evaluation']['faces'],p['face_diagnostics']):
  ck(face['face_id']==d['face_id'],'diagnostic face id')
  for src,dst in [('gas_mol_s','gas_mol'),('diffusive_enthalpy_w','diffusive_enthalpy_j'),('advective_enthalpy_w','advective_enthalpy_j')]:ck(d[dst]==[h*F(x) for x in face[src]],'diagnostic vector')
  for src,dst in [('energy_w','energy_j'),('conduction_w','conduction_j')]:ck(d[dst]==h*F(face[src]),'diagnostic scalar')
  lh=F(face.get('liquid_enthalpy_w',0))
  if 'liquid_mol_s' in face:
   ck(d['liquid_mol']==h*F(face['liquid_mol_s']) and d['liquid_enthalpy_j']==h*lh,'paired liquid donor integral')
   ck(d['liquid_enthalpy_projection_j']==h*face['liquid_enthalpy_projection_w'],'exact donor projection')
  else:ck('liquid_mol' not in d,'gas-only boundary schema')
  ck(d['energy_decomposition_roundoff_j']==h*(F(face['energy_w'])-F(face['conduction_w'])-sum(map(F,face['diffusive_enthalpy_w']))-sum(map(F,face['advective_enthalpy_w']))-lh),'total U authoritative decomposition')
 # Actual source inverse bounds: source-total pressure error includes volume.
 for row,cell in zip(t['terminal_bounds'],caps[2]['evaluation']['source_evaluation']['cells']):
  inv=cell['inverse'];point=inv['point']
  ck(row==[point['fluid']['mechanical']['temperature_k'],inv['temperature_error_bound_k'],point['fluid']['mechanical']['pressure_pa'],point['pressure_error_pa']],'terminal source bounds')
  ck(point['pressure_error_pa']>=point['fluid']['pressure_error_bound_pa'] and point['extra_pressure_error_pa']>0,'volume extra pressure bound')
 # Reference initial preflight + actual six-stage attempts + accepted endpoint.
 ref=t['reference'];rc=caps[3:];ck(all(c['role']=='reference' for c in rc) and len(rc)==ref['evaluations'],'reference callback accounting')
 ck(ref['status']=='completed' and ref['times_s'][0]==t['start'] and ref['times_s'][-1]==t['end'] and ref['states'][0]==initial,'complete reference interval')
 ck(rc[0]['state']==initial and rc[0]['time']==t['start'],'reference initial check')
 cursor=1;accepted=0;rejected=0;current=initial;at=start;trials=[];ledgerN=[F()]*len(flat(initial['amounts_mol']));ledgerU=[F()]*len(initial['internal_energy_j'])
 while cursor<len(rc):
  ck(cursor+6<len(rc),'complete saved attempt')
  c0,c1,l0,l1,r0,r1=rc[cursor:cursor+6];endpoint=c1['time']['seconds'];step=endpoint-at
  ck(step>0 and c0['time']['seconds']==at and c0['state']==current and l0['time']['seconds']==at and l0['state']==current,'attempt initial input')
  ck(l1['time']['seconds']==r0['time']['seconds']==at+step/2 and r1['time']['seconds']==endpoint,'actual half clocks')
  coarse,_=heun(current,c0,c1,step);half,fleft=heun(current,l0,l1,step/2);ck(r0['state']==half,'second half input');fine,fright=heun(half,r0,r1,step/2)
  error=normalized(fine,coarse,pol)*F(1,4)/(1-F(1,4));cursor+=6
  if error>1:
   rejected+=1;trials.append({'status':'rejected_error','start':str(at),'end':str(endpoint),'normalized_error':float(error)});continue
  cap=rc[cursor];ck(cap['time']['seconds']==endpoint and cap['state']==fine,'accepted actual endpoint');cursor+=1
  ledger=ref['steps'][accepted];fields=[[fsum(x,y) for x,y in zip(a,b)] for a,b in zip(fleft,fright)]
  for name,expected in zip(LEDGER,fields):ck(flat(ledger[name])==expected,'reference two-level rounded ledger')
  ck(ledger['start_s']['seconds']==at and ledger['end_s']['seconds']==endpoint,'reference ledger clocks')
  ck(ref['states'][accepted+1]==fine and ref['times_s'][accepted+1]['seconds']==endpoint,'reference accepted states')
  fn,fu,rn,w=fields
  for i in range(len(ledgerN)):ledgerN[i]+=F(fn[i])-F(fn[i+4])+F(rn[i])
  for i in range(len(ledgerU)):ledgerU[i]+=F(fu[i])-F(fu[i+1])+F(w[i])
  for v,old,delta in zip(flat(fine['amounts_mol']),flat(initial['amounts_mol']),ledgerN):ck(abs(F(v)-F(old)-delta)<=F(pol['amount_absolute_tolerance_mol']),'reference cumulative amount')
  for v,old,delta in zip(fine['internal_energy_j'],initial['internal_energy_j'],ledgerU):ck(abs(F(v)-F(old)-delta)<=F(pol['energy_absolute_tolerance_j']),'reference cumulative energy')
  accepted+=1;current=fine;at=endpoint;trials.append({'status':'accepted','start':str(ledger['start_s']['seconds']),'end':str(endpoint),'normalized_error':float(error)})
 ck(accepted==len(ref['steps']) and rejected==ref['rejected_trials'] and accepted+rejected==ref['attempted_trials'],'actual reference trial counts')
 ck(current==ref['states'][-1] and at==end,'reference final reconstruction')
 direct=normalized(p['raw_state'],current,pol);ck(direct==t['discrepancy'] and direct<=1,'direct cross-method gate no div3')
 prefixU=sum((F(y)-F(x) for x,y in zip(initial['internal_energy_j'],p['raw_state']['internal_energy_j'])),F())
 prefixW=sum((F(p['raw_state']['amounts_mol'][i][j])-F(initial['amounts_mol'][i][j]) for i in range(3) for j in (0,3)),F())
 ck(prefixU==exact[1][0]-exact[1][-1]+sum(p['full_residual_j'],F()),'prefix global U')
 ck(prefixW==sum((exact[0][j]-exact[0][12+j] for j in (0,3)),F())+sum((p['full_residual_mol'][4*i+j] for i in range(3) for j in (0,3)),F()),'prefix global water')
 for i in range(3):ck(exact[2][4*i]==-exact[2][4*i+3] and rep[2][4*i]==-rep[2][4*i+3],'paired phase')
 for d in p['face_diagnostics']:
  ck(abs(d['energy_decomposition_roundoff_j'])<=F(pol['energy_absolute_tolerance_j']),'energy decomposition budget')
  if 'liquid_enthalpy_projection_j' in d:ck(abs(d['liquid_enthalpy_projection_j'])<=F(pol['energy_absolute_tolerance_j']),'liquid donor projection budget')
 reference_deltaU=sum((F(y)-F(x) for x,y in zip(initial['internal_energy_j'],current['internal_energy_j'])),F())
 reference_resU=reference_deltaU-sum(ledgerU,F())
 reference_deltaW=sum((F(current['amounts_mol'][i][j])-F(initial['amounts_mol'][i][j]) for i in range(3) for j in (0,3)),F())
 reference_resW=reference_deltaW-sum((ledgerN[4*i+j] for i in range(3) for j in (0,3)),F())
 ck(sum(ledgerU,F())==sum((F(step['face_energy_j'][0])-F(step['face_energy_j'][-1])+sum(map(F,step['cell_work_j']),F()) for step in ref['steps']),F()),'reference global U telescoping')
 ck(sum((ledgerN[4*i+j] for i in range(3) for j in (0,3)),F())==sum((sum((F(step['face_species_mol'][0][j])-F(step['face_species_mol'][-1][j]) for j in (0,3)),F()) for step in ref['steps']),F()),'reference global water telescoping')
 ck(r['wall_seconds']<=210. and t['elapsed_seconds']<=180. and not r.get('outer_timeout_requested',False),'actual total resource limits')
 summary.update(prefix_delta_U_j=float(prefixU),prefix_delta_water_mol=float(prefixW),reference_delta_U_j=float(reference_deltaU),reference_delta_water_mol=float(reference_deltaW),reference_global_U_residual_j=float(reference_resU),reference_global_water_residual_mol=float(reference_resW),terminal_bounds=t['terminal_bounds'])
 summary.update(status='passed' ,checks=checks,callbacks=len(caps),reference_callbacks=len(rc),reference_accepted=accepted,reference_rejected=rejected,direct_discrepancy=direct,reference_trials=trials,elapsed_s=time.monotonic()-begin,scope='Independent saved arithmetic audit; no new EOS, physical trajectory/event or material validation')
 return summary
if __name__=='__main__':
 result=run(Path(sys.argv[1]),sys.argv[2]);(OUT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
