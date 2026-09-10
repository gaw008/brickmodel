"""Shared existing host/integrator spherical geometry, manufactured caloric data."""
from dataclasses import replace, FrozenInstanceError
from fractions import Fraction as F
import math

import numpy as np
import pytest

from sludge_sandbox.spherical_geometry import FixedSphericalShells, SphericalGeometryError
from sludge_sandbox.rigid_fluid_heat import RigidFluidHeat, RigidFluidHeatError
from sludge_sandbox.integration import IntegrationPolicy, integrate
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.deforming_solid_storage import _digest, _canonical
from sludge_sandbox.exchanges import conduction_rate_w
from test_rigid_fluid_heat import operator
from test_rigid_storage import model as storage_model, DATA, R
from sludge_sandbox.water_properties import load_water_properties


@pytest.fixture(scope='module')
def water():
    return load_water_properties(DATA)


def metric(cells=4, radius=.02):
    return FixedSphericalShells(tuple(radius*i/cells for i in range(cells+1)),
                               'manufactured:sphere', ('manufactured:radial-mesh',))


def sphere(water, cells=4, surface=None):
    g=metric(cells)
    template=storage_model(water)
    storages=tuple(replace(template,mechanical=replace(template.mechanical,available_pore_volume_m3=v))
                   for v in g.volumes_m3)
    return RigidFluidHeat(storages=storages,gas_species_order=('fixture',),liquid_column_id='liquid',
        face_area_m2=g.areas_m2[-1],cell_widths_m=g.widths_m,
        conductivities_w_m_k=((30-R)*100*.02**2,)*cells,
        effective_diffusivities_m2_s={'fixture':(0.,)*cells},permeability_m2=(0.,)*cells,
        relative_permeability=(1.,)*cells,viscosity_pa_s=(1e-5,)*cells,
        temperature_brackets_k=((295.,310.),)*cells,inverse_policy=InversePolicy(1e-10,1e-7,100),
        coefficient_set_id='manufactured:radial',coefficient_version='1',coefficient_classification='manufactured',
        coefficient_source_ids=('manufactured:radial-coefficients',),allow_manufactured=True,
        outer_surface_temperature_k=surface,outer_heat_source_ids=(() if surface is None else ('manufactured:surface',)),
        spherical_geometry=g)


def test_geometry_analytic_volume_resistance_and_center():
    g=FixedSphericalShells((0.,.1,.3,.7),'test:sphere',('test:geometry',))
    assert sum(g.volumes_m3)==pytest.approx(4*math.pi*.7**3/3,rel=3e-16)
    for face in (1,2,3):
        area,dl,dr=g.face_metric(face)
        a=F(g.centers_m[face-1]);r=F(g.faces_m[face])
        # Independent rational evaluation with the same declared binary64 pi.
        expected=(1/a-1/r)/(4*F(math.pi))
        assert dl/area==pytest.approx(float(expected),rel=5e-16)
        if face<g.cells:
            b=F(g.centers_m[face])
            assert dr/area==pytest.approx(float((1/r-1/b)/(4*F(math.pi))),rel=5e-16)
        else:
            assert dr==0
    with pytest.raises(SphericalGeometryError):g.face_metric(0)
    with pytest.raises(FrozenInstanceError):g.faces_m=(0.,1.)


@pytest.mark.parametrize('faces',[(True,1.),(0.,True),(0.,0.),(0.,1.,.5),(0.,float('inf')),
                                   (0.,float('nan')),(0.,1e-200),(0.,1e200),(0.,),[0.,1.]])
def test_invalid_mesh(faces):
    with pytest.raises(SphericalGeometryError):FixedSphericalShells(faces,'test:sphere',('test:geometry',))


def test_piecewise_conduction_outer_and_default_slab_arithmetic(water):
    op=sphere(water,3,surface=305.)
    op=replace(op,conductivities_w_m_k=(.3,.7,1.1))
    g=op.spherical_geometry
    for left,right in ((0,1),(1,2),(2,None)):
        r=g.faces_m[left+1];a=g.centers_m[left]
        resistance=(1/a-1/r)/(4*math.pi*op.conductivities_w_m_k[left])
        if right is not None:
            resistance+=(1/r-1/g.centers_m[right])/(4*math.pi*op.conductivities_w_m_k[right])
        assert op._conduction(303.,300.,left,right)==pytest.approx(3/resistance,rel=5e-16)
    slab=operator(water)
    for left,right in ((0,1),(1,None)):
        expected=conduction_rate_w(303.,300.,area_m2=slab.face_area_m2,
            left_distance_m=slab.cell_widths_m[left]/(2 if right is not None else 4),
            right_distance_m=slab.cell_widths_m[right]/2 if right is not None else slab.cell_widths_m[left]/4,
            left_conductivity_w_m_k=slab.conductivities_w_m_k[left],
            right_conductivity_w_m_k=slab.conductivities_w_m_k[right if right is not None else left])
        assert slab._conduction(303.,300.,left,right).hex()==expected.hex()


@pytest.mark.parametrize('cells',[1,3,7])
def test_same_host_global_energy_and_shared_faces(water,cells):
    op=sphere(water,cells,surface=300.)
    quantities=[[0.,100*v] for v in op.spherical_geometry.volumes_m3]
    temperatures=np.linspace(301.,304.,cells)
    state=op.state_from_temperatures(quantities,temperatures.tolist())
    out=op.evaluate(state,0.)
    assert out.rates.face_energy_w[0]==0
    assert np.all(out.rates.face_species_mol_s==0)
    dn,du=out.rates.derivatives(state)
    assert math.fsum(du)==pytest.approx(-out.rates.face_energy_w[-1],rel=1e-14,abs=1e-14)
    assert np.all(dn==0)
    assert np.array_equal(du,out.rates.face_energy_w[:-1]-out.rates.face_energy_w[1:])
    assert 'manufactured:radial-mesh' in op.source_ids
    assert not op.material_qualified


def test_geometry_identity_and_mismatches(water):
    op=sphere(water)
    other=replace(op,spherical_geometry=replace(op.spherical_geometry,geometry_id='other'))
    assert _digest(op)!=_digest(other)
    canonical=_canonical(op)
    assert any(name=='spherical_geometry' and value is not None for name,value in canonical[2])
    with pytest.raises(RigidFluidHeatError,match='area_mismatch'):replace(op,face_area_m2=.5)
    with pytest.raises(RigidFluidHeatError,match='widths_mismatch'):replace(op,cell_widths_m=(.01,)*4)
    with pytest.raises(RigidFluidHeatError,match='matching_spherical'):replace(op,spherical_geometry=metric(3))
    with pytest.raises(RigidFluidHeatError,match='exceeds_bulk'):
        replace(op,storages=(replace(op.storages[0],mechanical=replace(op.storages[0].mechanical,available_pore_volume_m3=1.)),)+op.storages[1:])


def test_spatial_convergence_through_existing_host_and_integrator(water):
    errors=[]
    fine_solutions=[]
    for cells,dt in ((4,.001),(8,.001),(16,.001),(16,.0005)):
        op=sphere(water,cells,surface=300.)
        g=op.spherical_geometry
        # Single exact regular spherical Laplacian eigenfunction; Tsurface=300.
        shape=np.sinc(np.asarray(g.centers_m)/g.faces_m[-1])
        quantities=[[0.,100*v] for v in g.volumes_m3]
        initial=op.state_from_temperatures(quantities,(300.+4*shape).tolist())
        result=integrate(initial,op,start_s=0.,end_s=.05,policy=IntegrationPolicy(
            initial_step_s=dt,maximum_step_s=dt,minimum_step_s=1e-9,
            relative_tolerance=1e-5,amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-9,
            amount_scale_mol=.001,energy_scale_j=.1,maximum_steps=1000,maximum_rejections=100,
            maximum_wall_seconds=30.))
        assert result.status=='completed',(result.status,result.reason)
        observed=np.array([v.mechanical.temperature_k for v in op.decode(result.states[-1])])
        reference=300.+4*shape*math.exp(-math.pi**2*.05)
        error=math.sqrt(sum(v*(a-b)**2 for v,a,b in zip(g.volumes_m3,observed,reference))/sum(g.volumes_m3))
        errors.append(error)
        if cells==16:fine_solutions.append(observed)
        assert np.array_equal(result.states[-1].amounts_mol,initial.amounts_mol)
        assert sum(result.states[-1].internal_energy_j)-sum(initial.internal_energy_j)==pytest.approx(
            -sum(step.face_energy_j[-1] for step in result.steps),abs=1e-11)
    assert errors[1]<errors[0]/3
    assert errors[2]<errors[1]/3
    assert errors[2]<.005
    temporal_delta=float(np.max(np.abs(fine_solutions[1]-fine_solutions[0])))
    assert temporal_delta<errors[2]/20
    print({'spherical_midpoint_RMS_errors_K':errors,'finest_temporal_halving_max_delta_K':temporal_delta})


def test_solid_host_uses_same_shell_volumes_faces_and_energy(water):
    from sludge_sandbox.solid_fluid_heat import SolidFluidHeat, InventoryLayout, SolidFluidHeatError
    from sludge_sandbox.solid_fluid_storage import SolidFluidStorage
    from test_incompressible_solid import phase, caloric
    transport=sphere(water,3,surface=300.)
    solid=phase(caloric=caloric(coefficients=(50.,0.,0.,0.,0.,-100.,0.,-100.)),
                molar_volume_m3_mol=1e-6,declared_v_error_m3_mol=1e-18)
    storages=tuple(SolidFluidStorage(fluid_template=s,solid_phases={'fixture_solid':solid},
        bulk_volume_m3=v,bulk_volume_error_m3=1e-18,geometry_id='manufactured:sphere',
        geometry_version='1',geometry_classification='manufactured_test_fixture',
        geometry_source_ids=('manufactured:radial-mesh',),allow_manufactured=True)
        for s,v in zip(transport.storages,transport.spherical_geometry.volumes_m3))
    layout=InventoryLayout(species_order=('liquid','fixture','fixture_solid'),
        liquid_column_id='liquid',gas_species_order=('fixture',),solid_species_order=('fixture_solid',))
    host=SolidFluidHeat(storages=storages,inventory_layout=layout,transport=transport)
    amounts=[[0.,100*v,v] for v in transport.spherical_geometry.volumes_m3]
    state=host.state_from_temperatures(amounts,[301.,302.,303.])
    result=host.evaluate(state,0.)
    assert np.all(result.rates.face_species_mol_s==0)
    for face in range(1,4):
        left=face-1;right=face if face<3 else None
        tr=result.gas_states[right].temperature_k if right is not None else 300.
        expected=transport._conduction(result.gas_states[left].temperature_k,tr,left,right)
        assert result.rates.face_energy_w[face]==expected
    dn,du=result.rates.derivatives(state)
    assert np.all(dn==0)
    assert math.fsum(du)==pytest.approx(-result.rates.face_energy_w[-1],abs=1e-14)
    with pytest.raises(SolidFluidHeatError,match='bulk_geometry'):
        replace(host,storages=(replace(storages[0],bulk_volume_m3=storages[0].bulk_volume_m3*1.1),)+storages[1:])
    with pytest.raises(SolidFluidHeatError,match='spherical_liquid_transport'):
        replace(host,liquid_transport=object())


def test_radial_gas_face_uses_integrated_resistance_and_physical_area(water):
    from sludge_sandbox.gas_transport import ideal_gas_reservoir
    op=replace(sphere(water,2),permeability_m2=(2e-15,5e-15))
    left=ideal_gas_reservoir(pressure_pa=3e5,temperature_k=300.,mole_fractions={'fixture':1.},
                           molar_masses_kg_mol={'fixture':.028},gas_constant_j_mol_k=R)
    right=ideal_gas_reservoir(pressure_pa=2e5,temperature_k=300.,mole_fractions={'fixture':1.},
                            molar_masses_kg_mol={'fixture':.028},gas_constant_j_mol_k=R)
    for li,ri in ((0,1),(1,None)):
        ex=op._face(left,right,li,ri)
        g=op.spherical_geometry;r=g.faces_m[li+1];a=g.centers_m[li]
        resistance=(1/a-1/r)/(4*math.pi*(op.permeability_m2[li]/op.viscosity_pa_s[li]))
        if ri is not None:
            resistance+=(1/r-1/g.centers_m[ri])/(4*math.pi*(op.permeability_m2[ri]/op.viscosity_pa_s[ri]))
        volume_flow=(left.pressure_pa-right.pressure_pa)/resistance
        assert g.areas_m2[li+1]*ex.darcy_velocity_m_s==pytest.approx(volume_flow,rel=1e-15)
        assert ex.advective_mol_s['fixture']==pytest.approx(ex.face_density_kg_m3/.028*volume_flow,rel=1e-15)
    with pytest.raises(RigidFluidHeatError,match='outer_spherical'):
        op._face(left,right,0,None)


def test_unregistered_radial_operator_not_silently_captured_by_old_codecs(water):
    from sludge_sandbox.exact_record import pack as pack_exact, ExactRecordError
    from sludge_sandbox.mass_wet_exact_record import pack as pack_mixed, MixedRecordError
    from sludge_sandbox.verification_case import encode, CaseError
    op=sphere(water,2)
    for pack,error in ((pack_exact,ExactRecordError),(pack_mixed,MixedRecordError)):
        with pytest.raises(error):pack(op)
        with pytest.raises(error):pack(op.spherical_geometry)
    # Geometry can be presented; entire native-provider operators have no generic presentation/replay codec.
    assert encode(op.spherical_geometry)['faces_m']==list(op.spherical_geometry.faces_m)
    with pytest.raises(CaseError,match='unsupported output type'):encode(op)
