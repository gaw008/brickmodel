"""Actual shared spherical host boundary; all material coefficients are fixtures."""
from dataclasses import replace
import math

import numpy as np
import pytest
from scipy.optimize import brentq

from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.integration import IntegrationPolicy, integrate
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeat, ProgrammedSolidFluidHeatError
from sludge_sandbox.solid_fluid_heat import SolidFluidHeat, InventoryLayout
from sludge_sandbox.solid_fluid_storage import SolidFluidStorage
from sludge_sandbox.water_properties import load_water_properties
from test_spherical_fluid_heat import sphere, DATA, R
from test_incompressible_solid import phase, caloric


@pytest.fixture(scope='module')
def water():
    return load_water_properties(DATA)


def programmed_sphere(water, *, conductivity=.5, h=20., emissivity=0., radiation=300.,
                      knots=(0.,.1), gas_temperatures=(310.,310.), policy=None, cells=1):
    transport=replace(sphere(water,cells),conductivities_w_m_k=(conductivity,)*cells)
    solid=phase(caloric=caloric(coefficients=(50.,0.,0.,0.,0.,-100.,0.,-100.)),
                molar_volume_m3_mol=1e-6,declared_v_error_m3_mol=1e-18)
    storages=tuple(SolidFluidStorage(fluid_template=fluid,solid_phases={'fixture_solid':solid},
        bulk_volume_m3=transport.cell_bulk_volume_m3(i),bulk_volume_error_m3=1e-18,geometry_id='manufactured:sphere',
        geometry_version='1',geometry_classification='manufactured_test_fixture',
        geometry_source_ids=('manufactured:radial-mesh',),allow_manufactured=True)
        for i,fluid in enumerate(transport.storages))
    host=SolidFluidHeat(storages=storages,transport=transport,inventory_layout=InventoryLayout(
        species_order=('liquid','fixture','fixture_solid'),liquid_column_id='liquid',
        gas_species_order=('fixture',),solid_species_order=('fixture_solid',)))
    program=BoundaryProgram(identity=ProgramIdentity(program_id='manufactured:spherical-oven',version='1',
        classification='virtual_design_choice',source_ids=('manufactured:spherical-oven',)),
        knot_times_s=knots,gas_temperature_k=gas_temperatures,
        radiation_temperature_k=(radiation,)*len(knots),total_pressure_pa=(3e5,)*len(knots),
        species_order=('fixture',),mole_fractions=((1.,),)*len(knots))
    return ProgrammedSolidFluidHeat(base_model=host,program=program,convection_w_m2_k=h,emissivity=emissivity,
        stefan_boltzmann_w_m2_k4=5.670374419e-8,coefficient_set_id='manufactured:spherical-film',
        coefficient_version='1',coefficient_classification='manufactured',
        coefficient_source_ids=('manufactured:spherical-film',),allow_manufactured=True,
        surface_policy=policy or SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=100))


def initial(op, temperature=300.):
    volume=op.base_model.transport.cell_bulk_volume_m3(0)
    return op.base_model.state_from_temperatures([[0.,100*volume,10*volume]],[temperature])


def independent_conductance(op):
    geometry=op.base_model.transport.spherical_geometry
    radius=geometry.faces_m[-1];center=geometry.centers_m[-1]
    return 4*math.pi*op.base_model.transport.conductivities_w_m_k[-1]/(1/center-1/radius)


def test_actual_spherical_film_surface_and_single_host_evaluation(water,monkeypatch):
    op=programmed_sphere(water)
    state=initial(op)
    calls=[];original=SolidFluidHeat.decode_inverse
    def count(self,s):
        calls.append(s)
        return original(self,s)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',count)
    result=op.evaluate(state,0.)
    g=independent_conductance(op);area=4*math.pi*.02**2;film=area*20
    expected=(g*300+film*310)/(g+film)
    assert expected==pytest.approx(304.4444444444444,abs=1e-12)
    assert result.surface_temperature_k==pytest.approx(expected,abs=2e-8,rel=0)
    assert result.conductive_into_cell_w==pytest.approx(10/(1/g+1/film),abs=1e-9,rel=0)
    assert result.heat.convective_in_w==pytest.approx(area*20*(310-result.surface_temperature_k),abs=1e-14)
    assert result.rates.face_energy_w[-1]==-result.conductive_into_cell_w
    assert len(calls)==1
    assert result.storage_inverses is result.base_evaluation.storage_inverses
    assert 'manufactured:radial-mesh' in result.source_ids
    assert not op.material_qualified


def test_radiation_independent_nonlinear_spherical_root(water):
    op=programmed_sphere(water,emissivity=.8,radiation=400.)
    result=op.evaluate(initial(op),0.)
    g=independent_conductance(op);area=4*math.pi*.02**2
    h=area*op.convection_w_m2_k;b=area*op.emissivity*op.stefan_boltzmann_w_m2_k4
    reference=brentq(lambda ts:b*ts**4+(g+h)*ts-(g*300+h*310+b*400**4),300.,400.,xtol=1e-12)
    assert result.surface_temperature_k==pytest.approx(reference,abs=2e-8,rel=0)
    assert abs(result.surface_balance_residual_w)<=result.surface_balance_limit_w
    assert result.rates.face_energy_w[-1]==-result.conductive_into_cell_w


def integration_policy(dt=.001):
    return IntegrationPolicy(initial_step_s=dt,maximum_step_s=dt,minimum_step_s=1e-9,
        relative_tolerance=1e-5,amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-9,
        amount_scale_mol=.001,energy_scale_j=.1,maximum_steps=2000,maximum_rejections=100,
        maximum_wall_seconds=30.)


def test_same_integrator_heating_then_cooling_and_energy_ledger(water):
    op=programmed_sphere(water,knots=(0.,.1,.2,.4),gas_temperatures=(310.,310.,295.,295.))
    state=initial(op)
    result=integrate(state,op,start_s=0.,end_s=.4,policy=integration_policy(),
                     breakpoints_s=op.breakpoints_s(0.,.4))
    assert result.status=='completed',(result.status,result.reason)
    g=independent_conductance(op);film=4*math.pi*.02**2*op.convection_w_m2_k
    capacity=state.amounts_mol[0,1]*(30-R)+state.amounts_mol[0,2]*50
    lam=(g*film/(g+film))/capacity
    reference=300.
    observed=[]
    for a,b,ta,tb in zip((0.,.1,.2),(.1,.2,.4),(310.,310.,295.),(310.,295.,295.)):
        dt=b-a;slope=(tb-ta)/dt
        reference=reference*math.exp(-lam*dt)+ta*(-math.expm1(-lam*dt))+slope*(dt+math.expm1(-lam*dt)/lam)
        index=result.times_s.index(b)
        temperature=op.base_model.decode(result.states[index])[0].mechanical.temperature_k
        observed.append(temperature)
        assert temperature==pytest.approx(reference,abs=2e-5,rel=0)
    assert observed[0]>300 and observed[-1]<observed[1]
    assert np.array_equal(result.states[-1].amounts_mol,state.amounts_mol)
    for before,after,step in zip(result.states,result.states[1:],result.steps):
        assert after.internal_energy_j[0]-before.internal_energy_j[0]==pytest.approx(-step.face_energy_j[-1],abs=1e-12)


@pytest.mark.parametrize('h,emissivity,radiation,expected',[(0.,0.,300.,300.),(20.,0.,300.,310.),(0.,.8,350.,350.)])
def test_zero_conductivity_surface_limits(water,h,emissivity,radiation,expected):
    op=programmed_sphere(water,conductivity=0.,h=h,emissivity=emissivity,radiation=radiation)
    result=op.evaluate(initial(op),0.)
    assert result.surface_temperature_k==pytest.approx(expected,abs=2e-8,rel=0)
    assert result.conductive_into_cell_w==0
    assert result.rates.face_energy_w[-1]==0
    if h==emissivity==0:assert result.surface_status=='insulated_surface_undetermined'


def test_zero_conductivity_does_not_remove_gas_enthalpy(water):
    op=programmed_sphere(water,conductivity=0.)
    host=op.base_model
    op=replace(op,base_model=replace(host,transport=replace(host.transport,permeability_m2=(1e-15,))))
    result=op.evaluate(initial(op),0.)
    assert result.conductive_into_cell_w==0
    assert result.rates.face_species_mol_s[-1,1]<0
    assert result.rates.face_energy_w[-1]<0


def test_surface_failure_propagates_without_accepted_steps(water):
    op=programmed_sphere(water,emissivity=.8,radiation=400.,
        policy=SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=1))
    state=initial(op)
    with pytest.raises(ProgrammedSolidFluidHeatError,match='surface_iteration_limit'):op.evaluate(state,0.)
    result=integrate(state,op,start_s=0.,end_s=.01,policy=integration_policy())
    assert result.status=='numerical_failure' and result.reason=='surface_iteration_limit'
    assert not result.steps and len(result.states)==1


def test_multicell_sphere_robin_mode_spatial_and_temporal_convergence(water):
    # Preregistered numerical criteria: 4/8/16cells, factor>3 reduction,
    # finest midpoint RMS<.005K; timestep-halving maxdelta<finesterror/20.
    # Bi=hR/k=1 gives mu=pi/2 exactly (mu*cot(mu)=1-Bi).
    radius=.02;conductivity=.5;capacity_per_volume=100*(30-R)+10*50
    alpha=conductivity/capacity_per_volume;end=.05*radius**2/alpha
    mu=math.pi/2;errors=[];fine=[]
    for cells,dt in ((4,.001),(8,.001),(16,.001),(16,.0005)):
        op=programmed_sphere(water,cells=cells,conductivity=conductivity,h=conductivity/radius,
                             knots=(0.,end),gas_temperatures=(300.,300.))
        geom=op.base_model.transport.spherical_geometry
        shape=np.sinc(mu*np.asarray(geom.centers_m)/(math.pi*radius))
        amounts=[[0.,100*v,10*v] for v in geom.volumes_m3]
        state=op.base_model.state_from_temperatures(amounts,(300+4*shape).tolist())
        run=integrate(state,op,start_s=0.,end_s=end,policy=integration_policy(dt),
                      breakpoints_s=op.breakpoints_s(0.,end))
        assert run.status=='completed',(run.status,run.reason)
        observed=np.array([v.mechanical.temperature_k for v in op.base_model.decode(run.states[-1])])
        reference=300+4*shape*math.exp(-mu**2*.05)
        error=math.sqrt(sum(v*(a-b)**2 for v,a,b in zip(geom.volumes_m3,observed,reference))/sum(geom.volumes_m3))
        errors.append(error)
        if cells==16:fine.append(observed)
        assert np.array_equal(run.states[-1].amounts_mol,state.amounts_mol)
        assert sum(run.states[-1].internal_energy_j)-sum(state.internal_energy_j)==pytest.approx(
            -sum(step.face_energy_j[-1] for step in run.steps),abs=1e-11)
    assert errors[1]<errors[0]/3 and errors[2]<errors[1]/3
    assert errors[2]<.005
    temporal_delta=float(np.max(np.abs(fine[1]-fine[0])))
    assert temporal_delta<errors[2]/20
    print({'sphere_Robin_midpoint_RMS_K':errors,'finest_temporal_halving_max_delta_K':temporal_delta})
