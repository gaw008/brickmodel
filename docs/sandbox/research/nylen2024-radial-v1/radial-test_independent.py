from pathlib import Path
from dataclasses import replace,fields
import importlib.util,math
import numpy as np
import pytest
from sludge_sandbox.rigid_fluid_heat import RigidFluidHeat
from test_rigid_fluid_heat import operator
from test_rigid_storage import DATA,R
from test_spherical_fluid_heat import sphere
from sludge_sandbox.water_properties import load_water_properties
@pytest.fixture(scope='module')
def water():return load_water_properties(DATA)
def test_prior_slab_full_rate_bit_parity(water):
    spec=importlib.util.spec_from_file_location('sludge_sandbox._review_prior_rigid','/private/tmp/brick-radial-host-review/prior_rigid.py')
    module=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name]=module;spec.loader.exec_module(module)
    op=operator(water)
    prior=module.RigidFluidHeat(**{f.name:getattr(op,f.name) for f in fields(module.RigidFluidHeat)})
    for temp in ([300.,305.],[306.,299.],[303.,303.]):
        state=op.state_from_temperatures([[0.,.01],[0.,.008]],temp)
        a=op.evaluate(state,0.);b=prior.evaluate(state,0.)
        assert np.array_equal(a.rates.face_species_mol_s,b.rates.face_species_mol_s)
        assert np.array_equal(a.rates.face_energy_w,b.rates.face_energy_w)
        assert [g.pressure_pa.hex() for g in a.gas_states]==[g.pressure_pa.hex() for g in b.gas_states]
def test_zero_conductivity_internal_and_boundary(water):
    op=sphere(water,2,surface=300.)
    for k in [(0.,.7),(.7,0.),(0.,0.)]:
        modified=replace(op,conductivities_w_m_k=k)
        assert modified._conduction(305.,300.,0,1)==0
        if k[-1]==0:assert modified._conduction(305.,300.,1,None)==0

def test_nonuniform_shell_flux_constant_analytic_profile(water):
    from sludge_sandbox.spherical_geometry import FixedSphericalShells
    g=FixedSphericalShells((0.,.002,.007,.02),'review:sphere',('review:geometry',))
    template=sphere(water,3)
    stores=tuple(replace(s,mechanical=replace(s.mechanical,available_pore_volume_m3=v)) for s,v in zip(template.storages,g.volumes_m3))
    op=replace(template,storages=stores,spherical_geometry=g,face_area_m2=g.areas_m2[-1],cell_widths_m=g.widths_m,conductivities_w_m_k=(.5,)*3)
    # Steady radial harmonic profile only away from origin: T=C+B/r.
    b=.001
    for li,ri in [(0,1),(1,2),(2,None)]:
        left=g.centers_m[li];right=g.centers_m[ri] if ri is not None else g.faces_m[-1]
        q=op._conduction(300+b/left,300+b/right,li,ri)
        assert q==pytest.approx(4*math.pi*.5*b,rel=1e-11)

def test_motion_wrappers_stop_before_planar_consumption(water):
    from sludge_sandbox.solid_fluid_heat import SolidFluidHeat,InventoryLayout
    from sludge_sandbox.solid_fluid_storage import SolidFluidStorage
    from sludge_sandbox.deforming_solid_heat import DeformingSolidHeat,DeformingSolidHeatError
    from sludge_sandbox.free_solid_slab import FreeSolidSlab
    from sludge_sandbox.current_solid_storage import CurrentSolidStorage
    from sludge_sandbox.integration import IntegrationError
    from test_incompressible_solid import phase
    op=sphere(water,1)
    storage=SolidFluidStorage(fluid_template=op.storages[0],solid_phases={'fixture_solid':phase()},bulk_volume_m3=op.cell_bulk_volume_m3(0),bulk_volume_error_m3=1e-18,geometry_id='review:sphere',geometry_version='1',geometry_classification='manufactured_test_fixture',geometry_source_ids=('review:geometry',),allow_manufactured=True)
    host=SolidFluidHeat(storages=(storage,),transport=op,inventory_layout=InventoryLayout(species_order=('liquid','fixture','fixture_solid'),liquid_column_id='liquid',gas_species_order=('fixture',),solid_species_order=('fixture_solid',)))
    # Deliberately unreadable mechanical points prove shape rejection precedes planar access.
    with pytest.raises(DeformingSolidHeatError,match='spherical_slab_motion'):
        DeformingSolidHeat(base_model=host,point_storages=(object(),),mechanical_regime='unused',transport_regime='unused',model_id='review',version='1',source_ids=('review',))
    point=object.__new__(CurrentSolidStorage)
    with pytest.raises(IntegrationError,match='spherical_slab_motion'):
        FreeSolidSlab(base_model=host,point_storages=(point,),external_pressure_pa=1e5,model_id='review',version='1',source_ids=('review',),allow_manufactured=True)
