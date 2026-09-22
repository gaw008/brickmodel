"""Reconstruct frozen states from source formulas without importing the cell.
The IAPWS backend is shared; this is not independent EOS verification.
"""
import json, math
from pathlib import Path
from iapws import IAPWS95
root=Path(__file__).resolve().parents[4]
settings=json.loads((root/'parameters.equilibrium_water_review.json').read_text())
config=json.loads((root/settings['source_parameters']).read_text())
facts=json.loads((root/config['water_facts_file']).read_text())
thermo=json.loads((root/config['thermochemistry_file']).read_text())
R=thermo['gas_constant']['value_j_mol_k']; pref=config['storage']['reference_pressure_pa']
mass=IAPWS95.M/1000; rn=facts['iapws_constants']['R_specific_j_kg_k']*mass
coeff=facts['ideal_formula_constants']; constants=facts['iapws_constants']
def ideal(T):
 tau=constants['T_critical_k']/T
 phi=math.log(pref/(constants['R_specific_j_kg_k']*T*constants['rho_critical_kg_m3']))+coeff['n1']+coeff['n2']*tau+coeff['n3']*math.log(tau)
 d=coeff['n2']*tau+coeff['n3']
 for n,g in zip(coeff['n4_to_n8'],coeff['gamma4_to_gamma8']):
  phi+=n*math.log1p(-math.exp(-g*tau));d+=n*g*tau/(math.exp(g*tau)-1)
 return rn*T*(1+d),rn*(d-phi)
offset=facts['gas_formation_h_j_mol']-ideal(facts['reference_temperature_k'])[0]
def gas_u(key,T):
 if key=='H2O': h=ideal(T)[0]+offset
 else:
  species=next(x for x in thermo['species'] if x['species_id']==key)
  segment=next(x for x in species['segments'] if x['temperature_range_k'][0]<=T<=x['temperature_range_k'][1])
  a,b,c,d,e,f,g,h0=segment['coefficients'];t=T/1000
  h=species['formation_enthalpy_298_j_mol']+1000*(a*t+b*t*t/2+c*t**3/3+d*t**4/4-e/t+f-h0)
 return h-R*T
rows=[]
for filename in settings['cases']:
 records=[json.loads(x) for x in (root/settings['records_directory']/filename).read_text().splitlines()]
 selected=[('initial',records[1]['state']),('final',records[-1]['final'])]
 dry=next((i for i,x in enumerate(records) if x['kind']=='step' and x['state']['phase']=='all_vapor'),None)
 if dry is not None: selected.extend([('last_wet',records[dry-1]['state']),('first_dry',records[dry]['state'])])
 for label,p in selected:
  T=p['temperature_k'];P=p['pressure_pa'];l=IAPWS95(T=T,P=P/1e6)
  ul=l.u*1000*mass+offset;hl=l.h*1000*mass+offset;sl=l.s*1000*mass
  Vg=config['storage']['available_fluid_volume_m3']-p['liquid_water_mol']*mass/l.rho
  P2=sum(p['amounts_mol'].values())*R*T/Vg
  U=p['liquid_water_mol']*ul+sum(n*gas_u(k,T) for k,n in p['amounts_mol'].items())
  pv=p['amounts_mol']['H2O']*R*T/Vg
  mu_v=ideal(T)[0]+offset-T*(ideal(T)[1]-R*math.log(pv/pref))
  mu_l=hl-T*sl
  pe=pref*math.exp((mu_l-(ideal(T)[0]+offset-T*ideal(T)[1]))/(R*T))
  rows.append({'file':filename,'point':label,'phase':p['phase'],'energy_residual_j':U-p['internal_energy_j'], 'mechanical_pressure_residual_pa':P2-P,'water_split_residual_mol':p['liquid_water_mol']+p['amounts_mol']['H2O']-p['inventories_mol']['H2O'],'chemical_gap_j_mol':mu_v-mu_l,'equilibrium_pressure_pa':pe,'stored_equilibrium_pressure_difference_pa':pe-p['equilibrium_partial_pressure_pa'],'liquid_h_u_pv_residual_j_mol':hl-ul-P*mass/l.rho})
budget=settings['numerical_comparison_budget']
result={'settings':settings,'runtime_backend':'iapws '+__import__('iapws').__version__,'rows':rows,
 'comparison':{'energy_within_budget':all(abs(x['energy_residual_j'])<=budget['energy_j'] for x in rows),'pressure_within_budget':all(abs(x['mechanical_pressure_residual_pa'])<=budget['pressure_pa'] for x in rows),'water_within_budget':all(abs(x['water_split_residual_mol'])<=budget['water_mol'] for x in rows),'phase_condition_within_numerical_budget':all(abs(x['chemical_gap_j_mol'])<=budget['chemical_potential_j_mol'] if x['phase']=='liquid_vapor' else x['chemical_gap_j_mol']<=budget['chemical_potential_j_mol'] for x in rows)},
 'material_qualified':False,'source_identity_attested':False}
(root/'data/sandbox/research/equilibrium-water-review-v1/reference_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'points':len(rows),'comparison':result['comparison'],'max_energy_residual_j':max(abs(x['energy_residual_j']) for x in rows)}))
