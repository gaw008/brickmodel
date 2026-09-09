"""No EOS: adapter refusal plus exact volume accounting helpers, not wet validation."""
from fractions import Fraction as F
from types import SimpleNamespace as NS
import math
import pytest

from sludge_sandbox import paired_pressure_host as m


def test_generic_contract_unavailable_without_provider_or_water_calls():
 def forbidden(*args):raise AssertionError('water called')
 result=m.prepare_paired_pressure(None,None,None,None,None,cell_index=0,endpoint_observer=forbidden)
 assert isinstance(result,m.PairedPressureUnavailable)
 assert result.original_pressure_errors_pa is None
 assert result.qualification=='original_independent_point_certificate_unchanged'

@pytest.mark.parametrize('untyped',[True,{},'manufactured_shared_constant_volume_parameters_v1'])
def test_untyped_correlation_claim_refused(untyped):
 with pytest.raises(m.PairedPressureHostError,match='typed_shared'):
  m.prepare_paired_pressure(None,None,None,None,None,cell_index=0,shared_constant_parameters=untyped)


def test_typed_box_does_not_admit_arbitrary_provider():
 box=m.SharedConstantParameterBox('fake',('A',),(F(1),),(F(0),),F(1),F(0))
 with pytest.raises(m.PairedPressureHostError,match='direct_actual'):
  m.prepare_paired_pressure(None,None,None,None,None,cell_index=0,shared_constant_parameters=box)

@pytest.mark.parametrize('p,e',[(F(100000),F(1,10**10)),(F(100000),F(0)),(F(1),F(1,3))])
def test_root_endpoints_outward_preserve_full_original_interval(p,e):
 lo,hi=m._outward_root(p,e,(F(1,10),F(200000)))
 assert lo<=p-e<=p+e<=hi
 assert lo==F(float(lo)) and hi==F(float(hi))
 assert p-e-lo<=F(math.ulp(float(lo)))
 assert hi-p-e<=F(math.ulp(float(hi)))


def test_outward_root_must_stay_in_original_domain():
 with pytest.raises(m.PairedPressureHostError,match='outside_domain'):
  m._outward_root(F(1),F(1,3),(F(2,3),F(4,3)))


def volume_fixture(extra):
 # Explicit algebra helper fixture, not a fabricated material/water provider.
 ref=NS(reference_area_m2=.01,half_thickness_m=.02,cells=2)
 v0=F(.01)*F(.02)/2
 point=NS(skeleton=NS(reference=ref),template=NS(bulk_volume_m3=float(v0),bulk_volume_error_m3=1e-18),
          error_bounds=NS(additional_bulk_volume_error_m3=extra))
 j=F(.97)*F(.99)**2;volume=float(j*v0)
 shared=F(1e-18)+abs(F(float(v0))-v0)
 raw=j*shared+abs(F(volume)-j*v0)+F(extra)
 upper=float(raw)
 if F(upper)<raw:upper=math.nextafter(upper,math.inf)
 current=NS(bulk_volume_m3=volume,bulk_volume_error_m3=upper,solid_phases={'A':NS(molar_volume_m3_mol=2e-5)})
 return point,current,{'A':2.},j


def test_additional_error_never_enters_shared_cancelled_reference_error():
 base=m._volume_terms(*volume_fixture(0.))
 changed=m._volume_terms(*volume_fixture(1e-12))
 assert base[:3]==changed[:3]
 assert changed[3]>=F(1e-12)
 # Outward rounding may differ, so exact difference need not equal added input.
 assert abs((changed[3]-base[3])-F(1e-12))<=F(math.ulp(1e-12))


def test_underreported_prepared_bulk_error_refused():
 point,current,solids,j=volume_fixture(1e-12);current.bulk_volume_error_m3=0.
 with pytest.raises(m.PairedPressureHostError,match='bulk_error_mismatch'):
  m._volume_terms(point,current,solids,j)


def test_prepared_pair_matches_frozen_pure_kernel_api():
 from sludge_sandbox import paired_pressure as kernel
 identity='a'*64
 state=kernel.PressureState(identity,F(300),F(1),F(0),(F(1),),F(10),F(1),F(0),(F(33),F(34)))
 shared=kernel.SharedVolumes(identity,('A',),(F(1),),(F(1,1000),),F(10),F(1,1000))
 pair=m.PreparedPair(state,state,shared,None,None,F(1),(F(1),F(100)),(F(290),F(310)),0,
                     (F(1,2),F(1,2)),(F(1,1000),F(1,1000)),identity)
 certificate=pair.certify()
 assert certificate.exact_bound_pa==0
 assert pair.endpoint_evaluations==0
 assert pair.original_temperature_errors_k==(F(1,1000),F(1,1000))
 assert certificate.to_record()['temperature_uncertainty_included'] is False


def _endpoint_sentinel(monkeypatch):
 """Control-flow sentinel only: no source constructor, state solve or EOS.

 The physical point preparation is stubbed. The real provider canonicalization
 is retained: it deliberately excludes implementation, reproducing the gap.
 """
 from sludge_sandbox.water_heos import HEOSWaterProperties
 from sludge_sandbox.water_properties import WaterReference, WaterState, NumericalLimits
 from sludge_sandbox.water_implementation import WaterImplementation
 original_digest=m._digest
 original=WaterImplementation('water_implementation_v1','sentinel','1',('sentinel',),'{}')
 changed=WaterImplementation('water_implementation_v1','sentinel','2',('sentinel',),'{}')
 water=object.__new__(HEOSWaterProperties)
 reference=WaterReference(.018,461.,8.3,0.,300.,0.,source_ids=('sentinel',))
 for key,value in {'reference':reference,'source_asset_sha256':{'sentinel':'a'*64},
                   'numerical_limits':NumericalLimits(),'implementation':original}.items():
  object.__setattr__(water,key,value)
 before_digest=original_digest(water)
 phase=object.__new__(m.IncompressibleSolidPhase)
 for key,value in {'allow_manufactured':True,'molar_volume_m3_mol':1e-5,'declared_v_error_m3_mol':1e-12}.items():
  object.__setattr__(phase,key,value)
 template=NS(solid_phases={'A':phase})
 point=NS(template=template,_template_digest=before_digest,identity=('sentinel',))
 host=object.__new__(m.FreeSolidSlab)
 for key,value in {'allow_manufactured':True,'solid_inventory_regime':'reacting_manufactured',
                   'point_storages':(point,),'source_ids':('sentinel',)}.items():
  object.__setattr__(host,key,value)
 chemical_water=object.__new__(HEOSWaterProperties)
 for key in ('reference','source_asset_sha256','numerical_limits','implementation'):
  object.__setattr__(chemical_water,key,getattr(water,key))
 chemical=NS(water=chemical_water,method_id='sentinel',source_ids=('sentinel',),_check_identity=lambda:None)
 operator=object.__new__(m.WaterPhaseTransfer)
 for key,value in {'base_model':host,'chemical':chemical,'coefficients_mol_s_pa':(1.,),
                   'coefficient_set_id':'sentinel','coefficient_version':'1','coefficient_source_ids':('sentinel',)}.items():
  object.__setattr__(operator,key,value)
 def digest(value):
  if value is operator or value is chemical or value is template:return original_digest(water)
  return original_digest(value)
 monkeypatch.setattr(m,'_digest',digest)
 box=m.SharedConstantParameterBox('a'*64,('A',),(F(1,100000),),(F(1,10**12),),F(1),F(0))
 monkeypatch.setattr(m,'declare_manufactured_constant_box',lambda p:box)
 current=NS(fluid_template=NS(mechanical=NS(water=water,gas_constant_j_mol_k=8.3),
                              envelope=NS(liquid_v_error_m3_mol=1e-16)))
 values=(point,current,{'gas_mol':{'fixture':.1},'liquid_mol':1.,'solid_mol':{'A':1.}},
         F(300),(F(100000),F(100001)),F(1),(F(1),F(0),F(1),F(0)),(F(1),F(200000)),(F(290),F(310)))
 monkeypatch.setattr(m,'_point',lambda *args:values)
 calls=[]
 def endpoint(self,temperature,pressure,*,phase):
  calls.append(pressure)
  return WaterState(temperature,0.,0.,1.,1.,reference,'sentinel',pressure,phase,1000.,0.,0.,0.,implementation=self.implementation)
 monkeypatch.setattr(HEOSWaterProperties,'state_tp',endpoint)
 inverse=NS(state=NS(thermal_state=NS(pressure_error_bound_pa=1.)),temperature_error_bound_k=.001)
 def prepare(**kwargs):return m.prepare_paired_pressure(operator,None,inverse,None,inverse,cell_index=0,
                          shared_constant_parameters=box,**kwargs)
 return NS(prepare=prepare,calls=calls,water=water,chemical_water=chemical_water,original=original,
           changed=changed,original_digest=original_digest,before_digest=before_digest,endpoint=endpoint,
           water_type=HEOSWaterProperties)


@pytest.mark.parametrize('change_implementation', ['none', 'water', 'chemical'])
def test_last_endpoint_observer_keeps_current_implementation_bound(monkeypatch, change_implementation):
 env=_endpoint_sentinel(monkeypatch)
 def observer(actual):
  if change_implementation!='none' and len(env.calls)==4:
   target=env.water if change_implementation=='water' else env.chemical_water
   object.__setattr__(target,'implementation',env.changed)
   assert env.original_digest(target)==env.before_digest
 if change_implementation!='none':
  with pytest.raises(m.PairedPressureHostError,match='provider_changed_during_endpoint_evaluation'):
   env.prepare(endpoint_observer=observer)
 else:
  prepared=env.prepare(endpoint_observer=observer);assert prepared.endpoint_evaluations==4
  assert env.water.implementation==env.original
 assert len(env.calls)==4


def test_before_endpoint_cancel_prevents_water_call(monkeypatch):
 env=_endpoint_sentinel(monkeypatch);attempts=[];completed=[]
 def cancel():
  attempts.append('attempt')
  raise RuntimeError('cancel-before-water')
 with pytest.raises(RuntimeError,match='cancel-before-water'):
  env.prepare(before_endpoint=cancel,endpoint_observer=completed.append)
 assert attempts==['attempt'] and not env.calls and not completed


def test_second_endpoint_failure_charges_attempt_not_completion(monkeypatch):
 env=_endpoint_sentinel(monkeypatch);attempts=[];completed=[];water_calls=[]
 def endpoint(self,temperature,pressure,*,phase):
  water_calls.append(pressure)
  if len(water_calls)==2:raise RuntimeError('second-water-failed')
  return env.endpoint(self,temperature,pressure,phase=phase)
 monkeypatch.setattr(env.water_type,'state_tp',endpoint)
 with pytest.raises(RuntimeError,match='second-water-failed'):
  env.prepare(before_endpoint=lambda:attempts.append('attempt'),endpoint_observer=completed.append)
 assert len(attempts)==2 and len(water_calls)==2 and len(completed)==1


def test_four_endpoint_hooks_have_before_water_after_order(monkeypatch):
 env=_endpoint_sentinel(monkeypatch);order=[]
 def endpoint(self,temperature,pressure,*,phase):
  order.append('water')
  return env.endpoint(self,temperature,pressure,phase=phase)
 monkeypatch.setattr(env.water_type,'state_tp',endpoint)
 prepared=env.prepare(before_endpoint=lambda:order.append('before'),
                      endpoint_observer=lambda actual:order.append('after'))
 assert order==['before','water','after']*4
 assert prepared.endpoint_evaluations==4
