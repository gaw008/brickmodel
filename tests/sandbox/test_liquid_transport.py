from dataclasses import replace,FrozenInstanceError
import math
import pytest
from sludge_sandbox.phase_storage import PhaseMetadata
from sludge_sandbox.liquid_transport import (LiquidTransportState,SaturationMobilityTable,LiquidConnection,
    liquid_face_exchange,LiquidTransportError,LiquidTransportDomainError)


def state(p=120.,v=2.,h=11.,**kw):
    values=dict(temperature_k=300.,pressure_pa=p,inventory_mol=1.,saturation=.5,pressure_error_pa=.1,
        molar_volume_m3_mol=v,enthalpy_j_mol=h,
        metadata=PhaseMetadata('H2O','liquid',.018,'mol_of_declared_species','shared_reference',('fixture:water',),'manufactured_test_fixture'),
        provider_id='fixture:liquid',provider_version='1',source_asset_sha256=(('fixture','a'*64),))
    values.update(kw);return LiquidTransportState(**values)


def relation(k=2.,kr=.5,mu=2.,**kw):
    values=dict(saturation_knots=(0.,1.),permeability_m2=(k,k),relative_permeability=(kr,kr),viscosity_pa_s=(mu,mu),
        temperature_range_k=(290.,310.),pressure_range_pa=(1.,1e4),model_id='fixture:mobility',version='1',
        classification='manufactured_test_fixture',source_ids=('fixture:mobility',),source_asset_sha256=(('fixture','b'*64),),
        relation_kind='frozen_manufactured')
    values.update(kw);return SaturationMobilityTable(**values)


def connection(**kw):
    values=dict(status='connected',connection_id='virtual:connected',version='1',classification='virtual_design_choice',source_ids=('virtual:connected',))
    values.update(kw);return LiquidConnection(**values)


def face(left=None,right=None,**kw):
    values=dict(left_relation=relation(),right_relation=relation(1.,1.,1.),connection=connection(),
        area_m2=4.,left_distance_m=2.,right_distance_m=3.,allow_manufactured=True)
    values.update(kw)
    return liquid_face_exchange(left or state(),right or state(50.,5.,-7.),**values)


def test_independent_two_half_resistances_and_unequal_donor():
    f=face()
    assert f.volume_flow_m3_s==pytest.approx(40.,rel=0,abs=1e-12)
    assert f.molar_flow_mol_s==pytest.approx(20.,rel=0,abs=1e-12)
    assert f.enthalpy_flow_w==pytest.approx(220.,rel=0,abs=1e-12)
    assert f.donor=='left'
    rev=face(left=state(50.),right=state(120.,5.,-7.))
    assert rev.volume_flow_m3_s==-40
    assert rev.molar_flow_mol_s==-8
    assert rev.enthalpy_flow_w==56
    assert rev.donor=='right'


def test_table_queries_actual_saturation_without_claiming_admission():
    table=relation(relation_kind='tabulated_saturation_relation',relative_permeability=(0.,1.))
    low=face(left=state(saturation=.25),left_relation=table)
    high=face(left=state(saturation=.75),left_relation=table)
    assert low.left_mobility.relative_permeability==.25
    assert high.left_mobility.relative_permeability==.75
    assert high.molar_flow_mol_s>low.molar_flow_mol_s
    assert not table.material_qualified
    # A genuine sourced relation may be constant over its declared domain;
    # changing a label alone never makes the whole face material qualified.
    assert relation(relation_kind='tabulated_saturation_relation',classification='literature_constitutive_model').evaluate(state()).relative_permeability==.5


def test_zero_mobility_dry_state_and_disabled_do_not_invent_liquid():
    dry=state(inventory_mol=0.,saturation=0.,molar_volume_m3_mol=None,enthalpy_j_mol=None)
    f=face(left=dry,left_relation=relation(k=0.))
    assert f.molar_flow_mol_s==0 and f.donor is None
    assert f.status=='zero_mobility'
    assert face(left=dry,connection=connection(status='disabled')).status=='disabled'
    with pytest.raises(LiquidTransportDomainError,match='liquid'):
        face(left=dry)


def test_pressure_direction_qualification_never_clips_nominal_flux():
    uncertain=face(left=state(50.01,pressure_error_pa=1.))
    assert uncertain.molar_flow_mol_s>0
    assert uncertain.direction_qualification=='nominal_direction_not_certified'
    assert face().direction_qualification=='conditional_direction_resolved'
    zero=face(left=state(50.))
    assert zero.molar_flow_mol_s==0 and zero.donor is None
    assert zero.status=='zero_nominal_pressure_difference'


@pytest.mark.parametrize('status',['unknown','disconnected'])
def test_active_unproven_connection_exits(status):
    with pytest.raises(LiquidTransportDomainError,match='connection'):face(connection=connection(status=status))


def test_metadata_mismatch_and_manufactured_gate():
    with pytest.raises(LiquidTransportError,match='manufactured'):face(allow_manufactured=False)
    with pytest.raises(LiquidTransportError):relation(classification='literature_constitutive_model')
    with pytest.raises(LiquidTransportError,match='identity'):
        face(right=replace(state(50.),provider_version='2'))


def test_relation_domain_no_extrapolation_and_state_invalid():
    with pytest.raises(LiquidTransportDomainError):face(left=state(saturation=.1),left_relation=relation(saturation_knots=(.2,.8)))
    with pytest.raises(LiquidTransportError):state(saturation=1.1)
    with pytest.raises(LiquidTransportError):relation(kr=1.1)
    with pytest.raises(LiquidTransportError):state(inventory_mol=0.)
    with pytest.raises(FrozenInstanceError):state().pressure_pa=100.


def test_intermediate_mobility_overflow_avoided_and_nonzero_final_underflow_rejected():
    huge=relation(k=1e300,mu=1e-300)
    f=face(left_relation=huge,right_relation=huge,area_m2=1e-300,left_distance_m=1e300,right_distance_m=1e300)
    assert f.volume_flow_m3_s==pytest.approx(17.5,rel=2e-15,abs=0)
    with pytest.raises(LiquidTransportError,match='unrepresentable'):
        face(left_relation=relation(k=math.ulp(0.)),right_relation=relation(k=math.ulp(0.)),area_m2=math.ulp(0.))


@pytest.mark.parametrize('kw',[{'area_m2':0.},{'left_distance_m':-1.},{'right_distance_m':math.inf}])
def test_invalid_geometry_units_and_finite_values(kw):
    with pytest.raises(LiquidTransportError):face(**kw)


@pytest.mark.parametrize('kw',[{'viscosity_pa_s':(0.,1.)},{'source_ids':()},{'source_asset_sha256':(('a','bad'),)},
    {'model_id':''},{'version':''},{'saturation_knots':(0.5,0.5)}])
def test_invalid_relation_identity_or_domain(kw):
    with pytest.raises(LiquidTransportError):relation(**kw)


def test_real_zero_plateau_and_full_diagnostic_identity():
    table=relation(relation_kind='tabulated_saturation_relation',saturation_knots=(0.,.2,1.),
        permeability_m2=(2.,2.,2.),relative_permeability=(0.,0.,1.),viscosity_pa_s=(2.,2.,2.))
    out=face(left=state(saturation=.1),left_relation=table)
    assert out.status=='zero_mobility'
    assert out.left_mobility.saturation==.1
    assert out.left_mobility.source_asset_sha256==table.source_asset_sha256
    assert out.liquid_source_identity==state().identity
    assert out.connection.connection_id=='virtual:connected'
    assert out.pressure_interval_scope=='fixed_decoded_temperature'
    assert not out.full_inverse_direction_certified


def test_different_reference_or_asset_cannot_share_enthalpy_face():
    for modified in (replace(state(),metadata=replace(state().metadata,energy_reference_id='other')),
                     replace(state(),source_asset_sha256=(('fixture','c'*64),))):
        with pytest.raises(LiquidTransportError,match='identity'):face(right=modified)
