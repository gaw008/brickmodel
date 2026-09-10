from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
import pytest
from test_source_wet_storage import setup
from sludge_sandbox.mass_storage_bridge import MixedError
from sludge_sandbox.phase_storage import InversePolicy

@pytest.mark.parametrize('field',['caloric','fluid_template','volume','chemistry','water_element_convention'])
def test_invalid_collaborators_rejected_before_closure(monkeypatch,field):
 op,state,calls=setup(monkeypatch);n=len(calls)
 def forbidden(*a,**k):pytest.fail('unadmitted collaborator callback')
 object.__setattr__(op,field,SimpleNamespace(binding=forbidden,check=forbidden,_check=forbidden))
 with pytest.raises(ValueError):op.evaluate(state,330.)
 assert len(calls)==n

def test_direct_exact_aggregate_error_and_cp_bound(monkeypatch):
 op,state,_=setup(monkeypatch)
 env=replace(op.fluid_template.envelope,liquid_abs_du_dp_bound_j_mol_pa=1e-6)
 op=replace(op,fluid_template=replace(op.fluid_template,envelope=env),volume=replace(op.volume,error_m3=1e-12))
 state=op.state(.2,(.2,.2,.001),0.)
 t=340.;out=op.evaluate(state,t)
 mass=F(.2);c=F(t)-F('273.15');r=F(40)
 expected_u=mass*(1434*(c-r)+F('1.645')*(c*c-r*r))
 assert out.solid_internal_energy_j==expected_u
 exact=F(out.fluid.internal_energy_j)+expected_u
 error=F(out.fluid.energy_error_bound_j)+abs(F(out.total_internal_energy_j)-exact)+F(.2)*F(env.liquid_abs_du_dp_bound_j_mol_pa)*F(out.extra_pressure_error_pa)
 assert F(out.energy_error_j)>=error
 minimum=F(out.fluid.minimum_heat_capacity_j_k)+mass*(1434+F('3.29')*(F(310)-F('273.15')))
 assert F(out.minimum_heat_capacity_j_k)<=minimum
 assert out.total_enthalpy_j is None and out.solid_volume_m3 is None and out.fit_error is None

def test_state_identity_and_domain_reject_before_liquid_queries(monkeypatch):
 op,state,calls=setup(monkeypatch);n=len(calls)
 for bad in [replace(state,solid_mass_kg=(.21,)),replace(state,energy_model_identity='f'*64)]:
  with pytest.raises(ValueError):op.invert(bad,InversePolicy(1e-5,1e-5,100))
 for temp in [309.,351.,F(330)+F(1,10**100)]:
  with pytest.raises(ValueError):op.evaluate(state,temp)
 assert len(calls)==n
