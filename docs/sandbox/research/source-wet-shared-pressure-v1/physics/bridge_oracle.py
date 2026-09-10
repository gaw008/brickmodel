"""Manufactured actual producer bridge; exact constant-v root is independent."""
import sys,math,json,time,hashlib
from pathlib import Path
from fractions import Fraction as F
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
sys.path[:0]=[str(root/'src'),str(root/'tests/sandbox')]
from test_source_wet_shared_pressure import actual_wet_pair
from sludge_sandbox.source_wet_shared_pressure import declare_source_shared_wet_volume,collect_source_wet_pressure_pair
p=root/'src/sludge_sandbox/source_wet_shared_pressure.py';before=hashlib.sha256(p.read_bytes()).hexdigest();start=time.monotonic();checks=0

def ck(x):
 global checks
 checks+=1
 assert x

gen=actual_wet_pair.__wrapped__();storage,ends,calls=next(gen)
try:
 n0=len(calls);pair=collect_source_wet_pressure_pair(*ends,shared_volume=declare_source_shared_wet_volume(storage));ck(pair.status=='conditional_shared_wet_pressure_enclosure');ck(len(calls)-n0==4)
 lo,hi=pair.shared_volume.volume_interval_m3
 for fraction in (F(),F(1,4),F(1,2),F(3,4),F(1)):
  V=lo+(hi-lo)*fraction
  for ta in ends[0].continuation.temperature_interval_k:
   for tb in ends[1].continuation.temperature_interval_k:
    exact=[]
    for e,T in zip(ends,(ta,tb)):
     exact.append(sum(map(F,e.state.gas_amounts_mol),F())*e.continuation.inputs[2]*T/(V-F(e.state.liquid_water_mol)*F(1.8e-5)))
    ck(abs(exact[0]-exact[1])<=pair.bound_pa)
 for e,part in zip(ends,pair.error_parts):
  ck(part.machine_residual_bound_m3==part.liquid_rounding_residual_m3+part.gas_rounding_residual_m3+part.sum_rounding_residual_m3)
  ck(part.report_to_root_bound_pa==(abs(part.saved_volume_residual_m3)+part.machine_residual_bound_m3)/part.compliance_lower_m3_pa)
  ck(part.retained_report_error_pa==part.actual_fluid_error_pa+part.projection_error_pa+part.report_to_root_bound_pa)
  ck(part.original_temperature_error_pa+part.added_temperature_error_pa==max(e.continuation.slope_pa_k,part.continuation.slope_pa_k)*F(e.inverse.temperature_error_bound_k))
 ck(pair.bound_pa==pair.root_difference_bound_pa+sum((x.retained_report_error_pa+x.original_temperature_error_pa+x.added_temperature_error_pa for x in pair.error_parts),F()))
 ck(pair.bound_pa==pair.joint_bound_pa)
 ck(not pair.material_qualified and not pair.event_admitted and not pair.source_certified)
 after=hashlib.sha256(p.read_bytes()).hexdigest();ck(before==after)
 result=dict(checks=checks,elapsed_s=time.monotonic()-start,source_sha256=after,joint_bound_pa=float(pair.bound_pa),status='passed',scope='manufactured source producer bridge; independent exact constant-volume liquid roots, not HEOS',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 Path(__file__).with_name('BRIDGE_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
 gen.close()
