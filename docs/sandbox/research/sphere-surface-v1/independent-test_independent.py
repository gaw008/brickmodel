from dataclasses import replace
import math
import mpmath as mp
import pytest
from test_spherical_programmed_heat import programmed_sphere,initial,water
from capture_slab import cases

def test_high_precision_nonlinear_reference(water):
 op=programmed_sphere(water,emissivity=.8,radiation=400.)
 out=op.evaluate(initial(op),0.)
 with mp.workdps(90):
  r=mp.mpf('.02');rc=mp.mpf('.01');g=4*mp.pi*mp.mpf('.5')/(1/rc-1/r);area=4*mp.pi*r*r
  h=area*20;b=area*mp.mpf('.8')*mp.mpf('5.670374419e-8');tc=mp.mpf(out.base_evaluation.gas_states[0].temperature_k)
  def f(t):return b*t**4+(g+h)*t-(g*tc+h*310+b*400**4)
  lo,hi=mp.mpf(300),mp.mpf(400)
  for _ in range(310):
   mid=(lo+hi)/2
   if f(mid)<0:lo=mid
   else:hi=mid
  ref=(lo+hi)/2
  assert abs(mp.mpf(out.surface_temperature_k)-ref)<mp.mpf(out.surface_balance_limit_w)/(g+h)+mp.mpf('1e-11')
 assert out.rates.face_energy_w[-1]==-out.conductive_into_cell_w

def test_selected_current_transport_changes_both_area_and_resistance():
 _,prior,op,state=next(cases())
 base=op.transport
 # Positive physical slabvolume preserved while current area/thickness change.
 current=replace(base,face_area_m2=base.face_area_m2*2,cell_widths_m=tuple(w/2 for w in base.cell_widths_m))
 boundary=op.program.at(.05)
 observed=op._surface(300.,boundary,transport=current)
 g=current.face_area_m2*current.conductivities_w_m_k[-1]/(current.cell_widths_m[-1]/2)
 h=current.face_area_m2*op.convection_w_m2_k
 ref=(g*300+h*310)/(g+h)
 assert observed[0]==pytest.approx(ref,abs=1e-8,rel=0)
 assert observed[2]==pytest.approx(g*(ref-300),abs=1e-8,rel=0)
 assert observed[0]!=op._surface(300.,boundary)[0]

def test_zero_k_gas_inflow_preserves_actual_donor_enthalpy(water):
 op=programmed_sphere(water,conductivity=0.)
 host=op.base_model;op=replace(op,base_model=replace(host,transport=replace(host.transport,permeability_m2=(1e-15,))))
 out=op.evaluate(initial(op),0.)
 flow=out.rates.face_species_mol_s[-1,1]
 assert flow<0 and out.conductive_into_cell_w==0
 # Fixture Cp=30 with identical donor curve; inspect actual reservoir temperature.
 enthalpy=host.storages[0].fluid_template.gas_phases['fixture']._curve.enthalpy_j_mol(out.reservoir.temperature_k)
 assert out.rates.face_energy_w[-1]==pytest.approx(flow*enthalpy,rel=1e-13)
