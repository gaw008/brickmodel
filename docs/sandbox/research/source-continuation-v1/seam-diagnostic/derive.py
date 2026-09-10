"""Fraction arithmetic on already extracted fields; no decode or model calls."""
from fractions import Fraction as F
from pathlib import Path
import math,json
p=Path(__file__).parent
raw=json.loads((p/'RESULT.json').read_text())
def f(x):return F(x['exact']) if isinstance(x,dict) else F(x)
rows=[]
for index,pair in enumerate(raw['pairs'][:2]):
 e=pair['endpoints'][0];m=e['fluid']['mechanical'];parts=pair['error_parts']
 c=sum(map(F,m['gas_inventory_mol'].values()),F())*F(m['gas_constant_j_mol_k'])*F(m['temperature_k'])/F(1e7)**2
 actual=sum((f(q['actual_fluid_error_pa']) for q in parts),F())
 temp=sum((f(q['original_temperature_error_pa'])+f(q['added_temperature_error_pa']) for q in parts),F())
 joint=f(pair['joint_bound_pa'])
 gamma=f(parts[0]['machine_residual_bound_m3'])
 J=pair['evidence']['support']['interval_pa']
 L=sum(map(F,m['gas_inventory_mol'].values()),F())*F(m['gas_constant_j_mol_k'])*F(m['temperature_k'])/f(J[0])**2
 target=F(1e-7)
 # At the recorded state/whole J, manufactured v(P) is constant. If a nested
 # numerical sign bracket has width delta, its midpoint's represented F can
 # be enclosed by L*delta/2 + 2*Gamma (endpoint and midpoint machine errors).
 midpoint_projection = F(math.ulp(float(f(J[1]))))
 predicted_F=L*(target/2+midpoint_projection)+2*gamma
 epsi=F(e['state']['liquid_water_mol'])*F(1e-16)
 predicted_fluid=(predicted_F+F(m['volume_resolution_m3'])+epsi)/c
 rows.append({'wet_cell_index':0 if index==0 else 2,'saved_joint_pa':float(joint),
   'saved_two_actual_fluid_terms_pa':float(actual),'saved_temperature_terms_pa':float(temp),
   'saved_joint_even_if_all_temperature_terms_zero_pa':float(joint-temp),
   'actual_fluid_fraction_of_joint':float(actual/joint),'declared_global_compliance_m3_pa':float(c),
   'per_endpoint_fluid_budget_pa':4e-5,
   'allowed_abs_saved_volume_residual_for_that_budget_m3':float(c*F(4e-5)-F(m['volume_resolution_m3'])-epsi),
   'actual_abs_saved_volume_residual_m3':abs(m['volume_residual_m3']),
   'actual_pressure_resolution_pa':m['pressure_resolution_pa'],
   'max_initial_bracket_ulp_pa':max(map(math.ulp,m['pressure_bracket_pa'])),
   'saved_final_bracket_width_pa':m['final_numerical_pressure_bracket_pa'][1]-m['final_numerical_pressure_bracket_pa'][0],
   'saved_final_bracket_width_after_seven_additional_halves_pa':(m['final_numerical_pressure_bracket_pa'][1]-m['final_numerical_pressure_bracket_pa'][0])/128,
   'candidate_mechanical_pressure_tolerance_pa':float(target),
   'recorded_midpoint_projection_allowance_pa':float(midpoint_projection),
   'recorded_box_analytic_midpoint_volume_residual_estimate_m3':float(predicted_F),
   'recorded_box_predicted_per_endpoint_actual_fluid_bound_pa':float(predicted_fluid),
   'scope':'allocation at saved state/common support for constant-volume manufactured liquid; future run must revalidate actual endpoints and full old gates'})
 assert actual>F(1e-4) and joint-temp>F(1e-4)
 assert predicted_fluid<F(4e-5)
 assert max(map(math.ulp,m['pressure_bracket_pa']))<float(target) and m['pressure_resolution_pa']<float(target)
out={'record_sha256':raw['sha256'],'rows':rows,'input_decode_count':0,'EOS_calls':0,
     'recommended_only_change':'manufactured case pressure_policy.pressure_tolerance_pa 1e-5 -> 1e-7; restore inverse temperature_tolerance_k 1e-6',
     'must_remain_unchanged':['event pressure gate 1e-4 Pa','volume uncertainty 1e-12 m3','liquid v error 1e-16 m3/mol','full physical error envelope','original real HEOS case'],'future_acceptance_not_claimed':True}
(p/'ALLOCATION.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
