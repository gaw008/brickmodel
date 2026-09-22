"""Reproduce the nominal entropy calculation from adjacent saved trajectories.

Uses only the standard library and embedded source coefficients; no host import.
Prints minima and writes pointwise_entropy.json in this evidence directory.
Pressure work and boundary enthalpy are already included in saved energy_out_w.
Internal liquid-vapor exchange has zero affinity under local equilibrium.
"""
import json, math
from pathlib import Path
base=Path(__file__).resolve().parent
results=[]
for path in sorted(base.glob('*.jsonl')):
 if path.name=='calorimetry.jsonl': continue
 rows=[json.loads(x) for x in path.read_text().splitlines()]
 inp=rows[0]; c=inp['parameters']; facts=inp['water_source']['facts']; th=inp['thermochemistry']; R=th['gas_constant']['value_j_mol_k']; pref=c['storage']['reference_pressure_pa']
 coeff=facts['ideal_formula_constants']; crit=facts['iapws_constants']; mass=c['molar_masses_kg_mol']['H2O']; Rn=crit['R_specific_j_kg_k']*mass
 def hs_native(T):
  tau=crit['T_critical_k']/T; delta=pref/(crit['R_specific_j_kg_k']*T*crit['rho_critical_kg_m3'])
  phi=math.log(delta)+coeff['n1']+coeff['n2']*tau+coeff['n3']*math.log(tau)
  derivative=coeff['n2']*tau+coeff['n3']
  for n,g in zip(coeff['n4_to_n8'],coeff['gamma4_to_gamma8']):
   phi+=n*math.log1p(-math.exp(-g*tau)); derivative+=n*g*tau*math.exp(-g*tau)/(1-math.exp(-g*tau))
  return Rn*T*(1+derivative), Rn*(derivative-phi)
 offset=facts['gas_formation_h_j_mol']-hs_native(facts['reference_temperature_k'])[0]
 def mu_over_t(key,T,p):
  if key=='H2O':
   h,s=hs_native(T);h+=offset
  else:
   spec=next(x for x in th['species'] if x['species_id']==key)
   seg=next(x for x in spec['segments'] if x['temperature_range_k'][0]<=T<=x['temperature_range_k'][1])
   a,b,cc,d,e,f,g,hh=seg['coefficients'];t=T/1000
   h=spec['formation_enthalpy_298_j_mol']+1000*(a*t+b*t*t/2+cc*t**3/3+d*t**4/4-e/t+f-hh)
   s=a*math.log(t)+b*t+cc*t*t/2+d*t**3/3-e/(2*t*t)+g
  return h/T-s+R*math.log(p/pref)
 res=c['cases'][inp['case']]['reservoir'];Tr=res['temperature_k']
 values=[]
 for row in rows:
  if row['kind']!='step':continue
  point=row['midpoint'];T=point['temperature_k'];rate=row['rate'];amounts=point['amounts_mol'];Vg=point['gas_volume_m3']
  sigma=rate['energy_out_w']*(1/Tr-1/T)
  for k,j in rate['exchange']['net_mol_s'].items():
   pc=amounts[k]*R*T/Vg;pr=res['pressure_pa']*res['mole_fractions'][k]
   sigma+=j*(mu_over_t(k,T,pc)-mu_over_t(k,Tr,pr))
  values.append({'step':row['index'],'entropy_generation_w_k':sigma})
 results.append({'file':path.name,'complete':rows[-1]['kind']=='summary','points':values,'minimum_w_k':min(v['entropy_generation_w_k'] for v in values)})
(base/'pointwise_entropy.json').write_text(json.dumps({'scope':'Nominal total entropy generation of cell plus ideal reservoir at recorded midpoint states; local phase equilibrium makes internal phase contribution zero. Not a discrete step entropy certificate or full-domain proof. Independent ideal caloric/entropy formula evaluation; reused saved fluxes.','formula':'sigma = E_out*(1/T_res-1/T_cell)+sum(j_out*(mu_cell/T_cell-mu_res/T_res))','runs':results},indent=2)+'\n')
for r in results: print(r['file'],r['complete'],r['minimum_w_k'])
