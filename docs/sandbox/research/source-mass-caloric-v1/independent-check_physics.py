"""Independent Decimal/quadratic oracle, outside the repository tests."""
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path
import hashlib,json
from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric
from sludge_sandbox.source_mass_caloric import ArlabosseMassCaloric,FixedMassCaloricStorage,ReactionDisabled,SourceMassCaloricError
from sludge_sandbox.phase_storage import InversePolicy
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
def decimal_fraction(f):return D(f.numerator)/D(f.denominator)
with localcontext() as ctx:
 ctx.prec=80
 m=D('0.2');b=D(1434);c=D('1.645');A=D(40);B=D(60);T=D(80)
 H=lambda x,y:b*(y-x)+c*(y*y-x*x)
 expected1=m*H(A,T);expected2=m*H(B,T)
 assert expected1==D('13051.2') and expected2==D('6657.2')
 Q=c*A*A+b*A+expected1/m
 disc=b*b+4*c*Q
 independent_T=2*Q/(b+disc.sqrt())
 assert independent_T==80
 provider=ArlabosseDryCaloric(root/'data/sandbox/research/arlabosse2005/source.json',root)
 outcomes=[]
 models=[]
 for anchor,energy in [(A,expected1),(B,expected2)]:
  cal=ArlabosseMassCaloric(provider,F(anchor+D('273.15')))
  mod=FixedMassCaloricStorage(cal,F(m),ReactionDisabled((cal.component_id,),(),'Independent fixed-composition review'))
  models.append(mod)
  point=mod.evaluate(F(T+D('273.15')))
  assert decimal_fraction(point.internal_energy_j)==energy
  assert decimal_fraction(point.minimum_heat_capacity_j_k)==m*(b+2*c*35)==D('309.83')
  assert decimal_fraction(point.closed_heat_capacity_j_k)==m*(b+2*c*T)==D('339.44')
  out=mod.invert(mod.target(F(energy)),InversePolicy(1e-10,1e-8,100))
  true_error=abs(out.point.temperature_k-F(independent_T+D('273.15')))
  assert true_error<=out.temperature_error_bound_k
  assert out.final_temperature_bracket_k[0]<=F('353.15')<=out.final_temperature_bracket_k[1]
  assert out.point.fit_error is None and out.point.numerical_energy_error_bound_j==0
  assert not out.point.material_qualified and cal.specific_volume_m3_kg is None
  outcomes.append({'anchor_C':str(anchor),'expected_energy_J':str(energy),'temperature_error_K':str(true_error),'reported_temperature_bound_K':str(out.temperature_error_bound_k),'iterations':out.iterations})
 assert models[0].model_identity!=models[1].model_identity
 try:models[1].invert(models[0].target(F(expected1)),InversePolicy(1e-10,1e-8,100))
 except SourceMassCaloricError as exc:assert str(exc)=='target_identity_mismatch'
 else:raise AssertionError('Mismatched gauge accepted')
 result={'status':'passed_independent_nominal_physics_check','scope':'source fixed dry-mass point, not wet/reaction/N-cell validation','Decimal_precision':ctx.prec,'quadratic_discriminant':str(disc),'quadratic_root_C':str(independent_T),'coordinate_shift_J':str(expected1-expected2),'results':outcomes,'source_code_sha256':hashlib.sha256((root/'src/sludge_sandbox/source_mass_caloric.py').read_bytes()).hexdigest(),'source_metadata_sha256':hashlib.sha256((root/'data/sandbox/research/arlabosse2005/source.json').read_bytes()).hexdigest()}
 print(json.dumps(result,indent=2))
 Path('/private/tmp/brick-source-mass-caloric-review/PHYSICS_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
