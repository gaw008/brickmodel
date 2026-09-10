from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
import pytest
from sludge_sandbox.source_mass_caloric import ArlabosseMassCaloric,FixedMassCaloricStorage,ReactionDisabled,SourceMassCaloricError
from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric
ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github')
def storage():
 raw=ArlabosseDryCaloric(ROOT/'data/sandbox/research/arlabosse2005/source.json',ROOT)
 caloric=ArlabosseMassCaloric(raw,F('313.15'))
 return FixedMassCaloricStorage(caloric,F(1,5),ReactionDisabled((caloric.component_id,),(),'fixed test'))
def test_replaced_provider_must_not_bypass_content_binding():
 model=storage();before=model.model_identity
 fake=SimpleNamespace(cp=lambda *a,**k:SimpleNamespace(value=F(99999)),delta_h=lambda *a,**k:SimpleNamespace(value=F(12345)))
 object.__setattr__(model.caloric,'provider',fake)
 with pytest.raises(SourceMassCaloricError):model.evaluate(F('353.15'))
def test_replaced_caloric_must_not_bypass_parent_binding():
 model=storage();original=model.caloric;old_binding=original.binding()
 fake=SimpleNamespace(_check=lambda:None,binding=lambda:old_binding,_temperature=lambda t:F(t),specific_internal_energy=lambda t:F(12345),cp=lambda t:F(99999),minimum_specific_heat_capacity=lambda *a:F(1),temperature_domain_k=original.temperature_domain_k)
 object.__setattr__(model,'caloric',fake)
 with pytest.raises(SourceMassCaloricError):model.evaluate(F('353.15'))

def test_independent_source_polynomial_and_inverse_certificate():
 from sludge_sandbox.phase_storage import InversePolicy
 model=storage();reference_c=F(40);mass=F(1,5)
 for c in [F(35),F(35)+F(1,10**14),F(41,1),F(551,10),F(10499,100),F(105)]:
  t=c+F(27315,100)
  # Independent direct coefficients from paper, no provider output as truth.
  exact=mass*(F(1434)*(c-reference_c)+F(329,200)*(c*c-reference_c*reference_c))
  assert model.evaluate(t).internal_energy_j==exact
  result=model.invert(model.target(exact),InversePolicy(1e-10,1e-10,100))
  assert abs(result.point.temperature_k-t)<=result.temperature_error_bound_k
  assert result.final_temperature_bracket_k[0]<=t<=result.final_temperature_bracket_k[1]
  assert result.energy_residual_j==result.point.internal_energy_j-exact
  assert result.point.fit_error is None and result.point.numerical_energy_error_bound_j==0

def test_near_endpoint_outside_target_is_not_tolerance_admitted():
 from sludge_sandbox.phase_storage import InversePolicy
 model=storage();lo,hi=model.caloric.temperature_domain_k
 for t,sign in [(lo,-1),(hi,1)]:
  target=model.evaluate(t).internal_energy_j+sign*F(1,10**200)
  with pytest.raises(SourceMassCaloricError,match='outside'):
   model.invert(model.target(target),InversePolicy(1.,1.,100))
