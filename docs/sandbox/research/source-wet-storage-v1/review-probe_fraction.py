from fractions import Fraction as F
import math,pytest
from test_mass_wet_storage import setup
from sludge_sandbox.mass_wet_storage import evaluate_wet_fluid
m=pytest.MonkeyPatch();st,state,calls=setup(m)
gas=list(state.gas_amounts_mol);gas[0]=F(gas[0])+F(math.ulp(gas[0]))*F(49,100)
ng=sum(map(F,state.gas_amounts_mol));raw=sum(map(F,gas));rt=F(st.fluid_template.mechanical.gas_constant_j_mol_k)*305;maxp=F(st.fluid_template.envelope.pressure_range_pa[1]);q=F(1)+F(math.ulp(1.))*F(1,100)
err=q*ng*rt/maxp**2
out=evaluate_wet_fluid(st.fluid_template,st.gas_ids,state.liquid_water_mol,tuple(gas),305.,.000989,err)
actualng=sum(F(v) for v in out.point.mechanical.gas_inventory_mol.values())
print('raw_ng_equals_actual',raw==actualng,'actual matches original',actualng==ng)
print('raw ng',raw,'actual ng',actualng)
# Global extra should enclose originalexact gas compliance at actual inventory.
base=F(out.point.pressure_error_bound_pa)
print('global combined bound>=actual unrounded',out.global_pressure_error_pa>=base+q,'delta',float(out.global_pressure_error_pa-base-q))
print('returned global',float(out.global_pressure_error_pa),'base',float(base),'nominal extra',float(q))
m.undo()
from sludge_sandbox.mass_storage_bridge import upper
for i in range(1,2001):
 e=F(1e-12)*(1+F(i,2000))
 glob=F(upper(base+F(upper(e*maxp**2/(raw*rt)))))
 certified=min(maxp,F(out.point.mechanical.pressure_pa)+glob)
 extra=F(upper(e*certified**2/(raw*rt)))
 correct=e*certified**2/(actualng*rt)
 if extra<correct:
  print('actualchosenerror',str(e),'underboundlocal',float(extra-correct))
  monkey=pytest.MonkeyPatch();st,state,calls=setup(monkey)
  actual=evaluate_wet_fluid(st.fluid_template,st.gas_ids,state.liquid_water_mol,tuple(gas),305.,.000989,e)
  bound=e*min(maxp,F(actual.point.mechanical.pressure_pa)+actual.global_pressure_error_pa)**2/(actualng*rt)
  print('actual_extra_underbounds_local_exact_using_actual_inventory',actual.extra_pressure_error_pa<bound, 'difference',float(actual.extra_pressure_error_pa-bound))
  monkey.undo();break
else:print('No underbound sample found')
