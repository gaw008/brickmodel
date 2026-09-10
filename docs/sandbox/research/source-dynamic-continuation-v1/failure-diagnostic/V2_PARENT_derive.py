"""Independent exact saved-field arithmetic; no production imports or EOS."""
from pathlib import Path
from fractions import Fraction as F
import json,math,time
began=time.monotonic();path=Path(__file__).with_name('V2_PARENT_EXTRACT.json');data=json.loads(path.read_text())
case=json.loads(Path('/private/tmp/brick-source-dynamic-continuation-v1/native02/parent/case.json').read_text())
def q(v):
 if isinstance(v,dict) and 'fraction' in v:return F(v['fraction'])
 return F(v)
def up(v):
 x=float(v);return math.nextafter(x,math.inf) if F(x)<v else x
def down(v):
 x=float(v);return math.nextafter(x,-math.inf) if F(x)>v else x
rows=[]
for pair in data['wet_pairs']:
 parts=pair['error_parts'];root=q(pair['root_difference_bound_pa']);joint=q(pair['joint_bound_pa'])
 totals={k:sum(q(p[k]) for p in parts) for k in ['actual_fluid_error_pa','projection_error_pa','report_to_root_bound_pa','original_temperature_error_pa','added_temperature_error_pa']}
 assert root+sum(totals.values())==joint
 endpoints=[]
 for part,endpoint in zip(parts,pair['endpoints']):
  mech=endpoint['mechanical'];point=endpoint['point'];inverse=endpoint['inverse'];inputs=part['continuation']['inputs'];nl,ng,r,B,t,et,p,old_ep=map(q,inputs)
  cglobal=F(down(ng*r*t/F(case['envelope']['pressure_range_pa'][1])**2))
  savedF=abs(q(part['saved_volume_residual_m3']));vr=F(mech['volume_resolution_m3']);eps=F(case['envelope']['liquid_v_error_m3_mol'])
  epsF=F(up(savedF+vr+F(up(nl*eps))));actual=up(epsF/cglobal)
  assert actual.hex()==float(q(part['actual_fluid_error_pa'])).hex()
  cmin=F(point['minimum_heat_capacity_j_k']);u_res=abs(q(inverse['energy_residual_j']));u_err=F(point['energy_error_j'])
  assert up((u_res+u_err)/cmin).hex()==inverse['temperature_error_bound_k'].hex()
  L=q(part['original_temperature_error_pa'])/et
  endpoints.append({'original_pressure_residual_contribution_pa':float(savedF/cglobal),'original_pressure_resolution_contribution_pa':float(vr/cglobal),'unchanged_liquid_volume_error_contribution_pa':float(nl*eps/cglobal),'actual_fluid_pa':actual,'rounding_over_exact_parts_pa':float(F(actual)-(savedF+vr+nl*eps)/cglobal),'original_global_compliance_m3_pa':float(cglobal),'original_local_compliance_m3_pa':float(q(part['compliance_lower_m3_pa'])),'temperature_lipschitz_pa_k':float(L),'energy_residual_j':float(u_res),'energy_error_j':float(u_err),'temperature_inverse_bound_k':float(et),'temperature_from_residual_pressure_pa':float(L*u_res/cmin),'temperature_unchanged_error_floor_pressure_pa':float(L*u_err/cmin),'pressure_bound_if_residual_zero_pa':float((vr+nl*eps)/cglobal),'remaining_report_to_root_floor_pa':float(q(part['machine_residual_bound_m3'])/q(part['compliance_lower_m3_pa'])),'allowed_saved_abs_F_for_fluid_budget_2e_minus5_m3':float(F('0.00002')*cglobal-vr-F(up(nl*eps))),'inverse_bound_from_proposed_energy_tolerance_1e_minus6_k':float(F('0.000001')/cmin),'T_contribution_from_proposed_energy_tolerance_pa':float(L*F('0.000001')/cmin),'pressure_initial_bracket_max_ulp_pa':max(math.ulp(v) for v in mech['pressure_bracket_pa']),'pressure_resolution_pa':mech['pressure_resolution_pa'],'pressure_bisection_old_iterations':mech['iterations'],'old_final_pressure_bracket_width_pa':mech['final_numerical_pressure_bracket_pa'][1]-mech['final_numerical_pressure_bracket_pa'][0],'width_after_7_additional_halves_pa':(mech['final_numerical_pressure_bracket_pa'][1]-mech['final_numerical_pressure_bracket_pa'][0])/128,'inverse_iterations':inverse['iterations']})
 rows.append({'phase_index':pair['phase_index'],'cell':pair['cell'],'joint_pa':float(joint),'joint_terms_pa':{'root_difference':float(root),**{k:float(v) for k,v in totals.items()}},'joint_if_all_T_terms_zero_pa':float(joint-totals['original_temperature_error_pa']-totals['added_temperature_error_pa']),'T_terms_alone_pa':float(totals['original_temperature_error_pa']+totals['added_temperature_error_pa']),'endpoints':endpoints})
for row in rows:
 for endpoint in row['endpoints']:
  endpoint['saved_pressure_bisection_iterations']=endpoint.pop('pressure_bisection_old_iterations')
  endpoint['saved_final_pressure_bracket_width_pa']=endpoint.pop('old_final_pressure_bracket_width_pa')
  for key in list(endpoint):
   if key.startswith(('allowed_saved_abs_F_for_', 'inverse_bound_from_proposed_', 'T_contribution_from_proposed_', 'width_after_7_')):
    del endpoint[key]
result={'clock_gate':data['clock_gate'],'clock_upper_s':q(data['clock_distance_upper_s']).__float__(),'original_gate_pressure_pa':case['event_policy']['pressure_absolute_pa'],'original_other_gates_all_true':all(all(row[:3]) for row in data['endpoint_gates']),'selected_failed_cells':[[i for i,v in enumerate(row) if v is not True] for row in data['cell_selected_pressure_gates']],'rows':rows,'applied_new_numerical_profile':{'pressure_policy.pressure_tolerance_pa':1e-7,'inverse_policy.energy_tolerance_j':1e-6,'inverse_policy.temperature_tolerance_k_unchanged':1e-6,'all_other_physical_envelope_event_and_resource_fields_unchanged':True},'review_scope':'Actual completed V2 parent decomposition; no claim about ordinary branch completion','elapsed_seconds':time.monotonic()-began,'eos_calls':0,'full_study_decodes':0}
Path(__file__).with_name('V2_PARENT_DIAGNOSIS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
