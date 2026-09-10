"""Offline exact audit. Execute only after parent confirms terminal SHA."""
import json,math,hashlib,sys,time
from pathlib import Path
from fractions import Fraction as F
checks=0

def ck(v,label):
 global checks
 checks+=1
 if not v:raise AssertionError(label)
def dec(v):
 if isinstance(v,list):return [dec(x) for x in v]
 if isinstance(v,dict):
  if set(v)=={'numerator','denominator'}:return F(v['numerator'],v['denominator'])
  if set(v)=={'type','fields'}:return dec(v['fields'])
  if 'dtype' in v and 'values' in v:return dec(v['values'])
  return {k:dec(x) for k,x in v.items()}
 return v
def up(x):
 f=float(x);return F(math.nextafter(f,math.inf)) if F(f)<x else F(f)
def S(x):return F(math.ulp(float(up(x))))
def inspect(pair):
 es=pair['endpoints'];support=pair['evidence']['support'];jlo,jhi=support['interval_pa'];parts=pair['error_parts'];V=pair['shared_volume']['volume_interval_m3'];vals=[]
 boxes=[]
 for e in es:
  point=e['inverse']['point'];m=point['fluid']['mechanical'];boxes.append([F(m['pressure_pa'])-F(point['pressure_error_pa']),F(m['pressure_pa'])+F(point['pressure_error_pa'])])
 ck(support['reported_pressure_boxes_pa']==boxes,'raw report boxes')
 ck(jlo<=min(x[0] for x in boxes) and jhi>=max(x[1] for x in boxes),'outward hull')
 for e,part,ids in zip(es,parts,support['endpoint_indices']):
  lo,hi=[pair['evidence']['attempts'][i] for i in ids];eps=lo['declared_volume_error_m3_mol'];nl,ng,R,B,T,eT,P,eP=e['continuation']['inputs'];point=e['inverse']['point'];iv=[F(hi['native_molar_volume_m3_mol'])-eps,F(lo['native_molar_volume_m3_mol'])+eps];c=ng*R*T/jhi**2
  ck(part['volume_interval_m3_mol']==iv,'full J v interval');sl=nl*(F(lo['native_molar_volume_m3_mol'])-eps)+ng*R*T/jlo-V[1];sh=nl*(F(hi['native_molar_volume_m3_mol'])+eps)+ng*R*T/jhi-V[0];ck(sl>=0>=sh and [sl,sh]==[part['low_root_sign_lower_m3'],part['high_root_sign_upper_m3']],'all V signs')
  mass=F(lo['state']['reference']['molar_mass_kg_mol']);cap=2*(iv[1]+eps);rmin=mass/cap;prod=F(float(float(nl)*float(mass)));nrt=F(math.fsum(e['state']['gas_amounts_mol'])*float(R)*float(T));dp=abs(prod-nl*mass);dn=abs(nrt-ng*R*T);lr=S(prod/rmin);gr=S(nrt/jlo);gl=nl*(eps+S(cap))+dp/rmin+lr;gg=dn/jlo+gr;gs=2*S(prod/rmin+lr+nrt/jlo+gr+V[1]);gamma=gl+gg+gs
  ck([dp,dn,gl,gg,gs,gamma]==[part[k] for k in ('liquid_product_projection_kg','gas_product_projection_j','liquid_rounding_residual_m3','gas_rounding_residual_m3','sum_rounding_residual_m3','machine_residual_bound_m3')],'independent Gamma exact')
  fluid=F(point['fluid']['pressure_error_bound_pa']);extra=F(point['extra_pressure_error_pa']);total=F(point['pressure_error_pa']);proj=abs(total-fluid-extra);z=(abs(F(point['fluid']['mechanical']['volume_residual_m3']))+gamma)/c
  ck(part['actual_fluid_error_pa']==fluid and part['projection_error_pa']==proj and part['report_to_root_bound_pa']==z and part['retained_report_error_pa']==fluid+proj+z,'actual fluid projection zeta')
  co=part['continuation'];r0=max(eP,abs(P-jlo),abs(jhi-P));tmin=co['temperature_domain_k'][0];pmax=co['pressure_domain_pa'][1];Lg=pmax/tmin*(1+nl*B*pmax/(ng*R*tmin));g=r0+Lg*eT;newL=(P+g)/(T-eT)*(1+nl*B*(P+g)/(ng*R*(T-eT)));oldL=e['continuation']['slope_pa_k'];ck(co['inputs'][-1]==r0 and co['global_radius_pa']==g and co['slope_pa_k']==newL,'independent continuation');ck(part['original_temperature_error_pa']==oldL*eT and part['added_temperature_error_pa']==(max(oldL,newL)-oldL)*eT,'retained temperature')
  vals.append((nl,ng,R,T,iv,c))
 a,b=vals;num=a[2]*(a[1]*a[3]-b[1]*b[3]);gas=sorted([num/jlo,num/jhi]);d=[a[0]*a[4][0]-b[0]*b[4][1]+gas[0],a[0]*a[4][1]-b[0]*b[4][0]+gas[1]];root=max(map(abs,d))/min(a[5],b[5]);joint=root+sum((p['retained_report_error_pa']+p['original_temperature_error_pa']+p['added_temperature_error_pa'] for p in parts),F());ck(pair['residual_interval_m3']==d and pair['root_difference_bound_pa']==root and pair['bound_pa']==pair['joint_bound_pa']==joint,'joint only exact');ck(not pair['material_qualified'] and not pair['source_certified'] and not pair['event_admitted'],'qualification')
 return float(joint)
def main():
 start=time.monotonic();raw=Path(sys.argv[1]).read_bytes();sha=hashlib.sha256(raw).hexdigest();ck(sha==sys.argv[2],'terminal input SHA');r=dec(json.loads(raw));found={}
 def walk(x):
  if isinstance(x,dict):
   if x.get('qualification')=='conditional_full_temperature_shared_wet_volume_not_event_or_material_admission':found.setdefault(x['input_binding'],x)
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(r);ck(len(found)==4,'four distinct actual wet pairs');bounds=[inspect(p) for p in found.values()];result=dict(checks=checks,input_sha256=sha,elapsed_s=time.monotonic()-start,pair_bounds_pa=bounds,status='passed',scope='saved exact wet pair formulas only; full trajectory and old-input comparison separate')
 Path(__file__).with_name('SAVED_WET_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
