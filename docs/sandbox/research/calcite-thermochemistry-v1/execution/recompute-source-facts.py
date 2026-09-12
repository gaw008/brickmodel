from decimal import Decimal as D, localcontext
from pathlib import Path
import hashlib,json
ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github')
DATA=ROOT/'data/sandbox/research/calcite-thermochemistry-v1'
FACTS=DATA/'facts.json';SOURCE=DATA/'source.json'
facts=json.loads(FACTS.read_text());source=json.loads(SOURCE.read_text())
assert hashlib.sha256(FACTS.read_bytes()).hexdigest()==source['facts_sha256']
asset=source['assets'][0];raw=Path(asset['path']).read_bytes()
assert len(raw)==asset['bytes'] and hashlib.sha256(raw).hexdigest()==asset['sha256']
assert raw.startswith(b'%PDF-')
with localcontext() as ctx:
 ctx.prec=80
 t0=D(facts['reference_state']['temperature_k'])
 def cp(s,t):
  a,b,c,d,e=map(D,s['cp']['coefficients_nominal'].values())
  return a+b*t+c/t**2+d/t.sqrt()+e*t**2
 def dh(s,t):
  a,b,c,d,e=map(D,s['cp']['coefficients_nominal'].values())
  return a*(t-t0)+b*(t*t-t0*t0)/2+c*(1/t0-1/t)+2*d*(t.sqrt()-t0.sqrt())+e*(t**3-t0**3)/3
 def h(s,t):return D(s['reference_298']['hf_kj_mol'])*1000+dh(s,t)
 comparisons=[]
 for s in facts['species']:
  for row in s['check_points']:
   t=D(row['temperature_k'])
   for field,actual in (('cp_j_mol_k',cp(s,t)),('enthalpy_function_j_mol_k',dh(s,t)/t)):
    printed=D(row[field]);difference=actual-printed
    comparisons.append({'species_id':s['id'],'temperature_k':str(t),'quantity':field,'printed':row[field],
     'recomputed':str(actual),'recomputed_minus_printed':str(difference),'half_printed_last_digit':'0.005',
     'within_half_printed_last_digit':abs(difference)<=D('.005')})
 ca,ox,gas=facts['species'];reaction=[]
 for row in ca['check_points']:
  t=D(row['temperature_k']);q=h(ox,t)+h(gas,t)-h(ca,t)
  rows=[next(x for x in s['check_points'] if x['temperature_k']==row['temperature_k']) for s in (ca,ox,gas)]
  q_from_printed=(D(rows[1]['formation_enthalpy_kj_mol'])+D(rows[2]['formation_enthalpy_kj_mol'])-D(rows[0]['formation_enthalpy_kj_mol']))*1000
  reaction.append({'temperature_k':str(t),'delta_h_j_mol':str(q),'delta_cp_j_mol_k':str(cp(ox,t)+cp(gas,t)-cp(ca,t)),
   'delta_h_j_kg_calcite':str(q/(D(ca['molar_mass_g_mol'])/1000)),
   'reaction_h_from_printed_same_T_formation_columns_j_mol':str(q_from_printed),
   'nominal_polynomial_minus_printed_formation_combination_j_mol':str(q-q_from_printed)})
 nist_path=ROOT/'data/sandbox/thermochemistry/nist_gases_v1.json';nist=json.loads(nist_path.read_text())
 # Locate the original NIST CO2 node without using production thermochemistry imports.
 def find_co2(node):
  if isinstance(node,dict):
   if node.get('species_id')=='CO2' and 'segments' in node:return node
   for v in node.values():
    r=find_co2(v)
    if r is not None:return r
  elif isinstance(node,list):
   for v in node:
    r=find_co2(v)
    if r is not None:return r
 co2=find_co2(nist);assert co2 is not None
 nd=[]
 for row in gas['check_points']:
  t=D(row['temperature_k']);seg=next(x for x in co2['segments'] if D(str(x['temperature_range_k'][0]))<=t<=D(str(x['temperature_range_k'][1])))
  a,b,c,d,e,f,g,hh=map(lambda x:D(str(x)),seg['coefficients']);x=t/1000
  nh=D(str(co2['formation_enthalpy_298_j_mol']))+1000*(a*x+b*x*x/2+c*x**3/3+d*x**4/4-e/x+f-hh)
  nc=a+b*x+c*x*x+d*x**3+e/x**2
  nd.append({'temperature_k':str(t),'nist_h_j_mol':str(nh),'nist_minus_usgs_h_j_mol':str(nh-h(gas,t)),
   'nist_cp_j_mol_k':str(nc),'nist_minus_usgs_cp_j_mol_k':str(nc-cp(gas,t))})
 failed=[x for x in comparisons if not x['within_half_printed_last_digit']]
 out={'schema_version':1,'source_id':facts['source_id'],'facts_sha256':hashlib.sha256(FACTS.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'checker':{'path':'/private/tmp/brick-mineral-thermo-v1/recompute-source-facts.py','sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'precision_decimal_digits':80,'application_imports':0,'native_eos_calls':0,
 'scope':'Original PDF byte verification and independent Decimal evaluation of original nominal polynomials; does not validate physical fit error or upstream experiments.'},
 'original_printed_check':{'comparisons':len(comparisons),'within_half_last_digit':len(comparisons)-len(failed),'outside_half_last_digit':len(failed),'result':'differences_preserved_not_all_printed_rows_reproduced' if failed else 'all_selected_nominal_values_within_printed_half_digit','rows':comparisons},
 'reaction_nominal':reaction,'stoichiometry':{'molar_coefficients':['-1','1','1'],'molar_mass_balance_g_mol':str(-D(ca['molar_mass_g_mol'])+D(ox['molar_mass_g_mol'])+D(gas['molar_mass_g_mol'])),
 'CO2_mass_yield_kg_per_kg_calcite':str(D(gas['molar_mass_g_mol'])/D(ca['molar_mass_g_mol'])),
 'CaO_mass_yield_kg_per_kg_calcite':str(D(ox['molar_mass_g_mol'])/D(ca['molar_mass_g_mol'])),
 'solid_volume_change_298_cm3_per_mol_extent':str(D(ox['reference_298']['volume_cm3_mol'])-D(ca['reference_298']['volume_cm3_mol']))},
 'uncertainty':'No propagated physical interval assigned. Printed formation uncertainties share unknown correlations and apply only at 298.15 K; nominal polynomial/table residuals are not fit-error bounds.',
 'nist_parallel_comparison':{'path':str(nist_path.relative_to(ROOT)),'sha256':hashlib.sha256(nist_path.read_bytes()).hexdigest(),
 'nist_formation_298_declared_j_mol':str(co2['formation_enthalpy_298_j_mol']),'usgs_formation_298_j_mol':str(D(gas['reference_298']['hf_kj_mol'])*1000),
 'declared_formation_difference_nist_minus_usgs_j_mol':str(D(str(co2['formation_enthalpy_298_j_mol']))-D(gas['reference_298']['hf_kj_mol'])*1000),
 'comparison_only_never_spliced':True,'rows':nd}}
 (DATA/'derived_checks.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'comparisons':len(comparisons),'outside_half_digit':len(failed),'failure_rows':failed,'reaction':reaction,'nist_declared_difference':out['nist_parallel_comparison']['declared_formation_difference_nist_minus_usgs_j_mol']},indent=2))
