from dataclasses import dataclass
from pathlib import Path
import math

import pytest

from sludge_sandbox.phase_storage import (
    PhaseMetadata, PhasePoint, PhaseStorage, PhaseStorageError, MonotonicPath,
    IdealGasPhase, LiquidWaterPhase, InversePolicy,
)
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.water_properties import load_water_properties

DATA=Path(__file__).resolve().parents[2]/'data/sandbox/water'
REF='nist_298.15K_element_standard_formation'

@dataclass(frozen=True)
class LinearSolid:
    metadata: PhaseMetadata
    temperature_range_k: tuple = (293.,500.)
    def evaluate(self,t,p):
        return PhasePoint(t,p,20*t-10000,20*t-10000+p*1e-5,1e-5)


def solid():
    return LinearSolid(PhaseMetadata('test-solid','solid',.05,'mol_of_declared_species',REF,('manufactured://linear',),'manufactured_test_fixture'))


def policy(**kw):
    return InversePolicy(**({'energy_tolerance_j':1e-8,'temperature_tolerance_k':1e-8,'maximum_iterations':150}|kw))


def path(p=1e5,bounds=(293.,500.)):
    return MonotonicPath(bounds,p,20.,('manufactured://linear-derivative',),'analytic_constant_derivative')


def test_linear_fixed_inventory_analytic_inverse():
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    result=store.evaluate({'s':2.},{'s':1e5},350.)
    assert result.internal_energy_j==-6000
    assert result.enthalpy_j==-5998
    assert result.phase_volumes_m3['s']==2e-5
    assert result.energy_scope=='species_thermal_storage_only'
    inverse=store.temperature_from_energy(-6000,{'s':2.},{'s':1e5},paths={'s':path()},policy=policy())
    assert inverse.temperature_k==pytest.approx(350,rel=0,abs=1e-8)
    assert abs(inverse.internal_energy_j+6000)<1e-8


def test_manufactured_requires_opt_in_and_unknown_never_ignored():
    with pytest.raises(PhaseStorageError):PhaseStorage({'s':solid()})
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    with pytest.raises(PhaseStorageError,match='unknown'):store.evaluate({'missing':0},{},350)


def test_zero_inventory_does_not_consult_property_or_pressure():
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    result=store.evaluate({'s':0},{},1000)
    assert result.internal_energy_j==0
    with pytest.raises(PhaseStorageError,match='no_active'):store.temperature_from_energy(0,{'s':0},{},paths={},policy=policy())


def test_inverse_needs_explicit_fixed_pressure_monotonic_domain():
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    with pytest.raises(PhaseStorageError,match='qualification'):store.temperature_from_energy(-3000,{'s':1},{'s':1e5},paths={},policy=policy())
    with pytest.raises(PhaseStorageError,match='pressure'):store.temperature_from_energy(-3000,{'s':1},{'s':1e5},paths={'s':path(2e5)},policy=policy())
    with pytest.raises(PhaseStorageError,match='out_of'):store.temperature_from_energy(1e9,{'s':1},{'s':1e5},paths={'s':path()},policy=policy())


def test_water_gas_real_energy_and_volume_are_separate():
    pytest.importorskip('iapws')
    water=load_water_properties(DATA);vapor=IdealWaterVapor(DATA)
    liquid=LiquidWaterPhase(water)
    gas=IdealGasPhase(vapor,vapor.molar_mass_kg_mol)
    store=PhaseStorage({'l':liquid,'v':gas})
    result=store.evaluate({'l':2,'v':.2},{'l':1e5,'v':1e5},300)
    l=water.state_tp(300,1e5,phase='liquid')
    assert result.internal_energy_j==pytest.approx(2*l.internal_energy_j_mol+.2*vapor.internal_energy_j_mol(300),rel=0,abs=1e-9)
    assert result.phase_volumes_m3['l']==pytest.approx(2*l.molar_mass_kg_mol/l.density_kg_m3)
    assert result.phase_volumes_m3['v']==pytest.approx(.2*vapor.gas_constant_j_mol_k*300/1e5)
    with pytest.raises(TypeError):result.phase_volumes_m3['l']=0


@pytest.mark.parametrize('amount',[True,-1,math.nan,math.inf])
def test_bad_inventory(amount):
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    with pytest.raises(PhaseStorageError):store.evaluate({'s':amount},{'s':1e5},350)


def test_reference_mismatch_fails():
    from dataclasses import replace
    other=replace(solid(),metadata=replace(solid().metadata,energy_reference_id='arbitrary_zero'))
    with pytest.raises(PhaseStorageError,match='reference'):PhaseStorage({'a':solid(),'b':other},allow_manufactured=True)


def test_unresolvable_energy_precision_is_not_success():
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    with pytest.raises(PhaseStorageError,match='precision'):store.temperature_from_energy(-3000,{'s':1},{'s':1e5},paths={'s':path()},policy=policy(energy_tolerance_j=1e-30))


def test_nist_adapter_preserves_gas_identity_and_fixture_gate():
    from sludge_sandbox.thermochemistry import ShomateGas,ShomateSegment
    segment=ShomateSegment((293.,500.),(30.,0.,0.,0.,0.,0.,0.,0.),0.,8.31446261815324,('manufactured://gas',))
    gas=ShomateGas('test-gas',(segment,),'manufactured_test_fixture',('manufactured://gas',))
    adapter=IdealGasPhase(gas,.02,segment_index=0,additional_source_ids=('manufactured://molar-mass-and-R',))
    assert adapter.metadata.species_id=='test-gas'
    with pytest.raises(PhaseStorageError,match='manufactured'):PhaseStorage({'g':adapter})
    with pytest.raises(PhaseStorageError):IdealGasPhase(segment,.02)


def test_provider_metadata_mutation_rejected():
    @dataclass(frozen=True)
    class Nested:
        contents: dict
        temperature_range_k: tuple = (293.,500.)
        @property
        def metadata(self):return self.contents['metadata']
        def evaluate(self,t,p):return solid().evaluate(t,p)
    nested=Nested({'metadata':solid().metadata})
    store=PhaseStorage({'s':nested},allow_manufactured=True)
    from dataclasses import replace
    nested.contents['metadata']=replace(solid().metadata,energy_reference_id='different')
    with pytest.raises(PhaseStorageError,match='changed'):store.evaluate({'s':1},{'s':1e5},350)


def test_temperature_precision_not_inferred_from_zero_energy_residual():
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    with pytest.raises(PhaseStorageError,match='precision'):
        store.temperature_from_energy(-2070,{'s':1},{'s':1e5},paths={'s':path()},policy=policy(temperature_tolerance_k=1e-30))


def test_quantized_large_energy_plateau_cannot_claim_small_temperature_error():
    @dataclass(frozen=True)
    class LargeEnergySolid:
        metadata: PhaseMetadata = solid().metadata
        temperature_range_k: tuple = (300.,400.)
        def evaluate(self,t,p):return PhasePoint(t,p,1e10+20*t,1e10+20*t+1,1/p)
    store=PhaseStorage({'s':LargeEnergySolid()},allow_manufactured=True)
    target=store.evaluate({'s':1},{'s':1e5},350.123456789).internal_energy_j
    with pytest.raises(PhaseStorageError,match='precision'):
        store.temperature_from_energy(target,{'s':1},{'s':1e5},paths={'s':path(bounds=(300.,400.))},policy=policy(energy_tolerance_j=1e-5,temperature_tolerance_k=1e-12))


def test_cancelling_phase_energies_retain_resolution_warning():
    @dataclass(frozen=True)
    class OffsetSolid:
        offset: float
        metadata: PhaseMetadata = solid().metadata
        temperature_range_k: tuple = (300.,400.)
        def evaluate(self,t,p):return PhasePoint(t,p,self.offset+20*t,self.offset+20*t+1,1/p)
    store=PhaseStorage({'a':OffsetSolid(1e10),'b':OffsetSolid(-1e10)},allow_manufactured=True)
    target=store.evaluate({'a':1,'b':1},{'a':1e5,'b':1e5},350.123456789).internal_energy_j
    with pytest.raises(PhaseStorageError,match='precision'):
        store.temperature_from_energy(target,{'a':1,'b':1},{'a':1e5,'b':1e5},paths={'a':path(bounds=(300.,400.)),'b':path(bounds=(300.,400.))},policy=policy(energy_tolerance_j=1e-5,temperature_tolerance_k=1e-10))


def test_water_fixed_pressure_path_derivative_is_not_cv_and_inverse_is_conditional():
    pytest.importorskip('iapws')
    water=load_water_properties(DATA);provider=LiquidWaterPhase(water)
    store=PhaseStorage({'l':provider})
    p=1e8;t=300.;dt=.01
    plus=store.evaluate({'l':1},{'l':p},t+dt)
    minus=store.evaluate({'l':1},{'l':p},t-dt)
    derivative=(plus.internal_energy_j-minus.internal_energy_j)/(2*dt)
    native=water.state_tp(t,p,phase='liquid')
    cv=native.cv_j_kg_k*native.molar_mass_kg_mol
    assert abs(derivative-cv)>.01
    # External test declaration, not an interval proof or material admission.
    assumption=MonotonicPath((299.,301.),p,1.,provider.metadata.source_ids,'explicit_test_path_assumption_not_interval_certificate')
    target=store.evaluate({'l':1},{'l':p},300.123).internal_energy_j
    found=store.temperature_from_energy(target,{'l':1},{'l':p},paths={'l':assumption},policy=policy())
    assert found.temperature_k==pytest.approx(300.123,rel=0,abs=1e-8)
    assert found.inverse_status=='conditional_on_declared_monotonic_paths_not_independently_admitted'
    assert found.inverse_paths['l']==assumption
    with pytest.raises(TypeError):found.inverse_paths['l']=None


def test_disjoint_path_domains_are_rejected():
    store=PhaseStorage({'a':solid(),'b':solid()},allow_manufactured=True)
    with pytest.raises(PhaseStorageError,match='no_common'):
        store.temperature_from_energy(-6000,{'a':1,'b':1},{'a':1e5,'b':1e5},paths={'a':path(bounds=(293.,320.)),'b':path(bounds=(350.,400.))},policy=policy())


def test_false_large_derivative_bound_does_not_buy_fake_precision():
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    bad=MonotonicPath((293.,500.),1e5,1e20,('manufactured://bad-bound',),'deliberately_wrong')
    with pytest.raises(PhaseStorageError,match='contradicted'):
        store.temperature_from_energy(-3000,{'s':1},{'s':1e5},paths={'s':bad},policy=policy())


def test_real_nist_gas_preserves_branch_sources():
    from sludge_sandbox.thermochemistry import load_thermochemistry
    thermo=load_thermochemistry(DATA.parent/'thermochemistry/nist_gases_v1.json')
    gas=thermo.gases['N2']
    # Explicit amount basis and mass declaration from model input; these source
    # labels remain declarations, not a new atomic-weight source verification.
    adapter=IdealGasPhase(gas,.0280134,segment_index=0,additional_source_ids=('nist-codata-2022','test://declared-N2-mass'))
    store=PhaseStorage({'n':adapter})
    out=store.evaluate({'n':2},{'n':1e5},300)
    assert out.internal_energy_j==2*gas.segments[0].internal_energy_j_mol(300)
    assert adapter.metadata.species_id=='N2'
    assert adapter.metadata.classification==gas.classification
    assert 'nist-codata-2022' in out.source_ids


def test_real_liquid_and_ideal_vapor_conditional_roundtrip():
    pytest.importorskip('iapws')
    water=load_water_properties(DATA);vapor=IdealWaterVapor(DATA)
    store=PhaseStorage({'l':LiquidWaterPhase(water),'v':IdealGasPhase(vapor,vapor.molar_mass_kg_mol)})
    amounts={'l':2.,'v':.2};pressures={'l':1e5,'v':1e5}
    target=store.evaluate(amounts,pressures,325.4321)
    paths={key:MonotonicPath((293.,350.),1e5,1.,store.providers[key].metadata.source_ids,
         'explicit_test_path_assumption_not_interval_certificate') for key in amounts}
    found=store.temperature_from_energy(target.internal_energy_j,amounts,pressures,paths=paths,policy=policy())
    assert found.temperature_k==pytest.approx(325.4321,rel=0,abs=1e-8)
    assert found.internal_energy_j==pytest.approx(target.internal_energy_j,rel=0,abs=1e-8)
    assert found.inverse_paths.keys()==amounts.keys()


def test_underflowing_extensive_derivative_bound_is_structured_failure():
    store=PhaseStorage({'s':solid()},allow_manufactured=True)
    tiny=MonotonicPath((293.,500.),1e5,5e-324,('manufactured://tiny',),'deliberate_resolution_probe')
    with pytest.raises(PhaseStorageError,match='derivative'):
        store.temperature_from_energy(-300,{'s':.1},{'s':1e5},paths={'s':tiny},policy=policy())
