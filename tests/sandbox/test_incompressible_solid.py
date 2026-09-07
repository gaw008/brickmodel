"""Single-phase incompressible identities, independent caloric integral oracle."""
from dataclasses import replace, FrozenInstanceError
from decimal import Decimal, localcontext
import math

import pytest

from sludge_sandbox.incompressible_solid import SolidShomateCaloric, IncompressibleSolidPhase, SolidPhaseError


def caloric(**kw):
    values=dict(species_id='fixture_solid',crystal_phase_id='manufactured_single_phase',
        temperature_range_k=(290.,500.),coefficients=(5.,0.,0.,0.,0.,-100.,0.,-100.),
        formation_enthalpy_298_j_mol=-100000.,dataset_id='manufactured:solid',version='1',
        classification='manufactured_test_fixture',source_ids=('manufactured:solid',),
        source_asset_sha256=(('fixture','a'*64),))
    values.update(kw)
    return SolidShomateCaloric(**values)


def phase(**kw):
    values=dict(caloric=caloric(),molar_mass_kg_mol=.05,molar_volume_m3_mol=2e-5,
        reference_pressure_pa=1e5,pressure_range_pa=(1e4,1e7),volume_model_id='manufactured:constant-volume',
        volume_version='1',volume_classification='manufactured_test_fixture',
        volume_source_ids=('manufactured:volume',),volume_source_asset_sha256=(('fixture','b'*64),),
        declared_u_error_j_mol=2e-7,declared_v_error_m3_mol=1e-12,
        error_method_id='manufactured:declared',error_classification='manufactured_test_fixture',error_source_ids=('manufactured:error',),allow_manufactured=True)
    values.update(kw)
    return IncompressibleSolidPhase(**values)


def test_solid_cp_below_gas_R_and_pressure_work_identity():
    model=phase()
    a,b=model.evaluate(300.,1e5),model.evaluate(300.,3e5)
    assert model.cv_j_mol_k(300)==5
    assert model.cp_lower_bound_j_mol_k==5
    assert a.internal_energy_j_mol==pytest.approx(-98502.,rel=0,abs=1e-9)
    assert a.enthalpy_j_mol==pytest.approx(-98500.,rel=0,abs=1e-9)
    assert a.internal_energy_j_mol==b.internal_energy_j_mol
    assert b.enthalpy_j_mol-a.enthalpy_j_mol==pytest.approx(4.,rel=0,abs=1e-9)
    assert model.metadata.phase=='solid'
    assert model.metadata.classification=='manufactured_test_fixture'
    assert not model.material_qualified


@pytest.mark.parametrize('start,end',[(300.,450.),(450.,300.),(300.,math.nextafter(300.,math.inf))])
def test_exact_integral_against_independent_decimal_primitive(start,end):
    c=caloric(coefficients=(20.,2.,3.,4.,.05,-100.,0.,-100.))
    with localcontext() as ctx:
        ctx.prec=70
        a,b,cc,d,e,_,_,_=map(Decimal.from_float,c.coefficients)
        def primitive(t):
            x=Decimal.from_float(t)/1000
            return 1000*(a*x+b*x*x/2+cc*x**3/3+d*x**4/4-e/x)
        expected=float(primitive(end)-primitive(start))
    assert c.enthalpy_difference_j_mol(start,end)==pytest.approx(expected,rel=2e-15,abs=0)
    assert c.enthalpy_difference_j_mol(start,end)==-c.enthalpy_difference_j_mol(end,start)
    for i in range(101):
        assert c.cp_j_mol_k(290+i*2.1)>=c.cp_lower_bound_j_mol_k>0


def test_frozen_and_identity_preserves_independent_volume_source():
    model=phase()
    with pytest.raises(FrozenInstanceError):model.molar_volume_m3_mol=1
    assert model.identity!=replace(model,molar_volume_m3_mol=3e-5).identity
    assert model.identity!=replace(model,volume_version='2').identity
    assert 'manufactured:volume' in model.metadata.source_ids


@pytest.mark.parametrize('changes',[dict(allow_manufactured=False),dict(molar_volume_m3_mol=0.),
    dict(declared_u_error_j_mol=-1.),dict(declared_v_error_m3_mol=-1.),dict(volume_source_ids=()),
    dict(volume_classification='unknown'),dict(pressure_range_pa=(1e6,1e7)),dict(error_method_id='')])
def test_bad_contract(changes):
    with pytest.raises(SolidPhaseError):phase(**changes)


@pytest.mark.parametrize('t,p',[(289.,1e5),(501.,1e5),(300.,0.),(300.,1e8),(math.nan,1e5)])
def test_domain_exit(t,p):
    with pytest.raises(SolidPhaseError):phase().evaluate(t,p)


def test_cp_zero_or_sign_changing_cannot_claim_continuous_positive_path():
    with pytest.raises(SolidPhaseError):caloric(coefficients=(0.,0.,0.,0.,0.,-100.,0.,-100.))
    with pytest.raises(SolidPhaseError):caloric(coefficients=(-1.,3.,0.,0.,0.,-100.,0.,-100.))


def test_no_cross_phase_segment_or_gas_internal_energy_interface():
    c=caloric(temperature_range_k=(298.,847.))
    assert c.enthalpy_j_mol(847.)==pytest.approx(-95765.,rel=0,abs=1e-9)
    with pytest.raises(SolidPhaseError):c.enthalpy_j_mol(math.nextafter(847.,math.inf))
    assert not hasattr(c,'internal_energy_j_mol')


def test_existing_phase_storage_sum_and_real_temperature_inverse():
    from sludge_sandbox.phase_storage import PhaseStorage,MonotonicPath,InversePolicy
    model=phase()
    storage=PhaseStorage({'solid':model},allow_manufactured=True)
    state=storage.evaluate({'solid':2.},{'solid':3e5},320.)
    assert state.internal_energy_j==pytest.approx(2*(-100000+5*320-2),rel=0,abs=1e-9)
    assert state.phase_volumes_m3['solid']==pytest.approx(4e-5,rel=0,abs=1e-20)
    path=MonotonicPath((290.,500.),3e5,model.cp_lower_bound_j_mol_k,('manufactured:path',),'certified_fraction_cp')
    result=storage.temperature_from_energy(state.internal_energy_j,{'solid':2.},{'solid':3e5},
        paths={'solid':path},policy=InversePolicy(1e-7,1e-7,100))
    assert result.temperature_k==pytest.approx(320.,rel=0,abs=1e-7)
    assert result.inverse_status=='conditional_on_declared_monotonic_paths_not_independently_admitted'


def test_error_budget_cannot_omit_standard_pressure_volume_contribution():
    with pytest.raises(SolidPhaseError,match='reference_volume_contribution'):
        phase(declared_u_error_j_mol=0.)


def test_real_quartz_single_branch_preserves_source_and_rejects_transition_crossing():
    import hashlib,json
    from pathlib import Path
    asset=Path(__file__).resolve().parents[2]/'data/sandbox/solids/quartz/facts.json'
    facts=json.loads(asset.read_text())
    segment=facts['segments'][0]
    c=SolidShomateCaloric(species_id=facts['species'],crystal_phase_id='quartz_I_source_branch',
        temperature_range_k=tuple(segment['temperature_range_k']),coefficients=tuple(map(float,segment['coefficients'])),
        formation_enthalpy_298_j_mol=1000*float(segment['coefficients'][7]),
        dataset_id=facts['source_id'],version=str(facts['schema_version']),classification=facts['classification'],
        source_ids=(facts['source_id'],),source_asset_sha256=((str(asset.relative_to(asset.parents[4])),hashlib.sha256(asset.read_bytes()).hexdigest()),))
    # h(T)-h(298.15) from independent Decimal evaluation of original source coefficients.
    with localcontext() as ctx:
        ctx.prec=50
        a,b,cc,d,e,f,g,h=map(Decimal,segment['coefficients'])
        def primitive(t):
            x=Decimal(t)/1000
            return 1000*(a*x+b*x*x/2+cc*x**3/3+d*x**4/4-e/x)
        expected=float(primitive('847')-primitive('298.15'))
    assert c.enthalpy_difference_j_mol(298.15,847.)==pytest.approx(expected,rel=2e-15,abs=0)
    assert c.cp_lower_bound_j_mol_k>0
    with pytest.raises(SolidPhaseError):c.enthalpy_j_mol(math.nextafter(847.,math.inf))
    # No real volume data in facts: this remains a manufactured volume/error test.
    m=phase(caloric=c,molar_mass_kg_mol=float(facts['molar_mass_kg_mol']))
    assert m.metadata.classification=='manufactured_test_fixture'
    assert not m.material_qualified


def test_manufactured_error_contract_alone_preserves_gate():
    c=caloric(classification='literature_constitutive_model')
    with pytest.raises(SolidPhaseError,match='manufactured'):
        phase(caloric=c,volume_classification='literature_constitutive_model',allow_manufactured=False)


@pytest.mark.parametrize('changes',[dict(source_asset_sha256=(('asset','bad'),)),dict(source_ids=()),
    dict(formation_enthalpy_298_j_mol=-99999.),dict(coefficients=(math.inf,)*8)])
def test_invalid_caloric_sources_and_coefficients(changes):
    with pytest.raises(SolidPhaseError):caloric(**changes)


def test_unrepresentable_caloric_value_is_not_infinite_success():
    c=caloric(coefficients=(1e308,0.,0.,0.,0.,-100.,0.,-100.))
    with pytest.raises(SolidPhaseError,match='unrepresentable'):
        c.enthalpy_j_mol(300.)
