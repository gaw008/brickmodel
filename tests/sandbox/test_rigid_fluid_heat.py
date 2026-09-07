"""Manufactured transport coupled to actual liquid/ideal-gas storage closure."""
from dataclasses import replace
import math

import numpy as np
import pytest

from sludge_sandbox.gas_transport import ideal_gas_reservoir
from sludge_sandbox.integration import DomainExit, IntegrationPolicy, integrate
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.rigid_fluid_heat import RigidFluidHeat, RigidFluidHeatError
from test_rigid_storage import model as storage_model, DATA, R
from sludge_sandbox.water_properties import load_water_properties

pytest.importorskip('iapws')


@pytest.fixture(scope='module')
def water():
    return load_water_properties(DATA)


def operator(water, **changes):
    first=storage_model(water)
    second=replace(first,mechanical=replace(first.mechanical,available_pore_volume_m3=8e-5))
    fields=dict(storages=(first,second),gas_species_order=('fixture',), liquid_column_id='H2O_liquid',
                face_area_m2=.01,cell_widths_m=(.01,.01),conductivities_w_m_k=(.2,.3),
                effective_diffusivities_m2_s={'fixture':(1e-6,2e-6)},permeability_m2=(1e-15,2e-15),
                relative_permeability=(1.,1.),viscosity_pa_s=(1e-5,1e-5),
                temperature_brackets_k=((295.,310.),(295.,310.)),
                inverse_policy=InversePolicy(1e-5,1e-4,100),
                coefficient_set_id='manufactured-rigid-fluid',coefficient_version='1',
                coefficient_classification='manufactured',coefficient_source_ids=('manufactured:rigid-fluid',),
                allow_manufactured=True)
    fields.update(changes)
    return RigidFluidHeat(**fields)


def test_two_cells_decode_real_storage_and_share_conduction_pressure_flux(water):
    op=operator(water)
    state=op.state_from_temperatures([[2,.01],[1,.008]],[300,301])
    out=op.evaluate(state,0)
    assert len(out.storage_states)==2
    assert not op.material_qualified
    assert len(out.storage_inverses)==2
    for inverse,decoded in zip(out.storage_inverses,out.storage_states):
        assert inverse.state is decoded
        assert abs(inverse.energy_residual_j)<=op.inverse_policy.energy_tolerance_j
        assert inverse.temperature_error_bound_k<=op.inverse_policy.temperature_tolerance_k
    assert out.rates.face_species_mol_s.shape==(3,2)
    assert np.all(out.rates.face_species_mol_s[:,0]==0)
    assert out.rates.face_species_mol_s[1,1]!=0
    assert out.storage_states[0].mechanical.gas_volume_m3<1e-4
    assert out.storage_states[1].mechanical.gas_volume_m3<8e-5
    dn,du=out.rates.derivatives(state)
    assert math.fsum(dn[:,1])==0
    assert math.fsum(du)==0
    assert all(s.qualification.startswith('conditional') for s in out.storage_states)
    off=replace(op,permeability_m2=(0.,0.),effective_diffusivities_m2_s={'fixture':(0.,0.)})
    no_flow=off.evaluate(state,0)
    assert no_flow.rates.face_species_mol_s[1,1]==0
    expected=.01*(300-301)/(.005/.2+.005/.3)
    assert no_flow.rates.face_energy_w[1]==pytest.approx(expected,abs=1e-8,rel=0)
    changed=op.state_from_temperatures([[2,.011],[1,.008]],[300,301])
    assert op.evaluate(changed,0).rates.face_species_mol_s[1,1]!=out.rates.face_species_mol_s[1,1]


def test_actual_two_cell_integrator_preserves_liquid_species_and_total_energy(water):
    op=operator(water)
    initial=op.state_from_temperatures([[2,.01],[1,.008]],[300,301])
    initial_decode=op.decode(initial)
    result=integrate(initial,op,start_s=0,end_s=.001,
        policy=IntegrationPolicy(initial_step_s=.001,maximum_step_s=.001,minimum_step_s=1e-10,
            relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-11,energy_absolute_tolerance_j=1e-5,
            amount_scale_mol=.01,energy_scale_j=1,maximum_steps=10,maximum_rejections=10,
            maximum_wall_seconds=90))
    assert result.status=='completed',(result.status,result.reason)
    assert result.evaluations>1
    for state in result.states:
        assert np.array_equal(state.amounts_mol[:,0],initial.amounts_mol[:,0])
        assert math.fsum(state.amounts_mol[:,1])==pytest.approx(.018,abs=1e-11,rel=0)
        assert math.fsum(state.internal_energy_j)==pytest.approx(math.fsum(initial.internal_energy_j),abs=1e-7,rel=0)
    assert result.states[-1].amounts_mol[0,1]!=initial.amounts_mol[0,1]
    final_decode=op.decode(result.states[-1])
    assert final_decode[0].mechanical.pressure_pa!=initial_decode[0].mechanical.pressure_pa
    for before,after,step in zip(result.states,result.states[1:],result.steps):
        assert after.internal_energy_j-before.internal_energy_j==pytest.approx(
            step.face_energy_j[:-1]-step.face_energy_j[1:],abs=1e-7,rel=0)


def test_open_pure_gas_outflow_uses_donor_enthalpy_and_cools_adiabatically(water):
    op=operator(water)
    storage=op.storages[0]
    gas=ideal_gas_reservoir(pressure_pa=1e4,temperature_k=305,mole_fractions={'fixture':1},
                          molar_masses_kg_mol={'fixture':.028},gas_constant_j_mol_k=R)
    op=replace(op,storages=(storage,),cell_widths_m=(.01,),conductivities_w_m_k=(0.,),
        effective_diffusivities_m2_s={'fixture':(0.,)},permeability_m2=(1e-15,),relative_permeability=(1.,),
        viscosity_pa_s=(1e-5,),temperature_brackets_k=((295.,310.),),
        outer_reservoir=gas,outer_reservoir_source_ids=('manufactured:open-reservoir',))
    state=op.state_from_temperatures([[0,.01]],[300])
    out=op.evaluate(state,0)
    dn,du=out.rates.derivatives(state)
    assert dn[0,1]<0
    h=30*300
    u=(30-R)*300
    assert du[0]==pytest.approx(h*dn[0,1],abs=1e-8,rel=0)
    assert du[0]-u*dn[0,1]==pytest.approx(R*300*dn[0,1],abs=1e-8,rel=0)
    assert du[0]-u*dn[0,1]<0
    assert op.scientific_status=='conditional_fixed_liquid_rigid_fluid_transport_not_brick'


@pytest.mark.parametrize('changes',[dict(face_area_m2=-1),dict(cell_widths_m=(1e-5,1e-5)),
    dict(relative_permeability=(1.,2.)),dict(coefficient_source_ids=()),dict(allow_manufactured=False),
    dict(gas_species_order=('missing',)),dict(liquid_column_id='fixture')])
def test_invalid_geometry_identity_and_coefficients(water,changes):
    with pytest.raises(RigidFluidHeatError):operator(water,**changes)


def test_cross_cell_caloric_curve_and_mass_must_match(water):
    op=operator(water)
    second=op.storages[1]
    phase=second.gas_phases['fixture']
    curve=phase.caloric
    shifted=replace(curve,segments=(replace(curve.segments[0],coefficients=(30,0,0,0,0,1,0,0)),))
    bad=replace(second,gas_phases={'fixture':replace(phase,caloric=shifted)})
    with pytest.raises(RigidFluidHeatError,match='caloric'):
        replace(op,storages=(op.storages[0],bad))
    bad=replace(second,gas_phases={'fixture':replace(phase,molar_mass_kg_mol=.03)})
    with pytest.raises(RigidFluidHeatError,match='caloric'):
        replace(op,storages=(op.storages[0],bad))


def test_bad_state_shape_and_numerical_contract_failure_are_distinct(water):
    from sludge_sandbox.integration import ConservedState
    op=operator(water)
    with pytest.raises(RigidFluidHeatError,match='shape'):
        op(ConservedState([[1]],[0]),0)
    state=op.state_from_temperatures([[2,.01],[1,.008]],[300,301])
    bad=replace(op,inverse_policy=InversePolicy(1e-15,1e-15,100))
    with pytest.raises(RigidFluidHeatError):bad(state,0)
    with pytest.raises(DomainExit):
        op.state_from_temperatures([[2,.01],[1,.008]],[320,301])


def test_two_gas_diffusion_preserves_mass_and_maps_each_species_enthalpy(water):
    from sludge_sandbox.phase_storage import IdealGasPhase
    from sludge_sandbox.thermochemistry import ShomateGas,ShomateSegment
    base=storage_model(water)
    names=('B','A')  # Deliberately not alphabetical: arrays obey this declared order.
    phases={}
    for name,mass,cp,f in [('B',.044,35.,1.),('A',.028,30.,0.)]:
        curve=ShomateGas(name,(ShomateSegment((100.,2000.),(cp,0,0,0,0,f,0,0),0,R,
            ('manufactured:binary-caloric',)),),'manufactured_test_fixture',('manufactured:binary-caloric',))
        phases[name]=IdealGasPhase(curve,mass,0,('nist-codata-2022',))
    storage=replace(base,mechanical=replace(base.mechanical,gas_species_ids=names),gas_phases=phases,
        envelope=replace(base.envelope,gas_u_error_j_mol={n:1e-9 for n in names},
                         gas_cv_lower_j_mol_k={n:20. for n in names}))
    op=operator(water,storages=(storage,storage),gas_species_order=names,
        conductivities_w_m_k=(0.,0.),permeability_m2=(0.,0.),
        effective_diffusivities_m2_s={'B':(2e-6,2e-6),'A':(1e-6,1e-6)})
    state=op.state_from_temperatures([[2,.002,.008],[2,.008,.002]],[300,300])
    result=op.evaluate(state,0)
    liquid,b,a=result.rates.face_species_mol_s[1]
    assert liquid==0 and b<0 and a>0
    assert .044*b+.028*a==pytest.approx(0,abs=1e-15,rel=0)
    temperature=(result.gas_states[0].temperature_k+result.gas_states[1].temperature_k)/2
    expected=b*(35*temperature+1000)+a*(30*temperature)
    assert result.rates.face_energy_w[1]==pytest.approx(expected,abs=1e-8,rel=0)
    assert op.species_order==('H2O_liquid','B','A')


def test_real_surface_temperature_boundary_uses_last_half_cell(water):
    op=operator(water)
    op=replace(op,storages=(op.storages[0],),cell_widths_m=(.01,),conductivities_w_m_k=(.2,),
        effective_diffusivities_m2_s={'fixture':(0.,)},permeability_m2=(0.,),relative_permeability=(1.,),
        viscosity_pa_s=(1e-5,),temperature_brackets_k=((295.,310.),),
        outer_surface_temperature_k=310,outer_heat_source_ids=('manufactured:actual-surface',))
    state=op.state_from_temperatures([[0,.01]],[300])
    out=op.evaluate(state,0)
    assert out.rates.face_energy_w[-1]==pytest.approx(-.01*.2*(310-300)/.005,abs=1e-8,rel=0)
    assert np.all(out.rates.face_species_mol_s==0)


def test_continuous_caloric_reservoir_outside_domain_is_domain_exit(water):
    from sludge_sandbox.continuous_caloric import ContinuousShomateGas
    op=operator(water)
    storage=op.storages[0]
    phase=storage.gas_phases['fixture']
    derived=ContinuousShomateGas(source_gas=phase.caloric,model_id='derived-fluid-fixture',version='1',
        anchor_temperature_k=300,method_source_ids=('manufactured:cp-integration',),
        gas_constant_source_ids=('nist-codata-2022',),allow_manufactured=True)
    storage=replace(storage,gas_phases={'fixture':replace(phase,caloric=derived,segment_index=None)})
    reservoir=ideal_gas_reservoir(pressure_pa=1e6,temperature_k=3000,mole_fractions={'fixture':1},
                                 molar_masses_kg_mol={'fixture':.028},gas_constant_j_mol_k=R)
    op=replace(op,storages=(storage,),cell_widths_m=(.01,),conductivities_w_m_k=(0.,),
        effective_diffusivities_m2_s={'fixture':(0.,)},permeability_m2=(1e-15,),relative_permeability=(1.,),
        viscosity_pa_s=(1e-5,),temperature_brackets_k=((295.,310.),),
        outer_reservoir=reservoir,outer_reservoir_source_ids=('manufactured:outside-caloric-domain',))
    state=op.state_from_temperatures([[0,.01]],[300])
    with pytest.raises(DomainExit,match='temperature_out_of_domain'):
        op(state,0)


def test_independently_loaded_identical_water_bridges_share_semantic_identity(water):
    from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
    from sludge_sandbox.phase_storage import IdealGasPhase
    first=storage_model(water)
    storages=[]
    for _ in range(2):
        bridge=IdealWaterVapor(DATA)
        phase=IdealGasPhase(bridge,bridge.molar_mass_kg_mol)
        storages.append(replace(first,mechanical=replace(first.mechanical,gas_species_ids=('H2O',)),
            gas_phases={'H2O':phase},envelope=replace(first.envelope,
            gas_u_error_j_mol={'H2O':1e-9},gas_cv_lower_j_mol_k={'H2O':20.})))
    assert storages[0].gas_phases['H2O'].caloric is not storages[1].gas_phases['H2O'].caloric
    op=operator(water,storages=tuple(storages),gas_species_order=('H2O',),
                effective_diffusivities_m2_s={'H2O':(1e-6,1e-6)})
    assert op.gas_species_order==('H2O',)
