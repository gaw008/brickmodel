from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from test_dynamic_solid_storage import water,forbid_water_eos
from test_deforming_solid_heat import host as old_host
from test_rigid_fluid_heat import operator
from sludge_sandbox.current_solid_storage import CurrentSolidStorage
from sludge_sandbox.dynamic_solid_storage import DynamicStorageErrorBounds
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.solid_fluid_heat import SolidFluidHeat
import sludge_sandbox.free_solid_slab as m


def host(water):
    old=old_host(water);point=old.point_storages[0]
    reference=replace(point.skeleton.reference,half_thickness_m=.02,cells=2)
    bounds=DynamicStorageErrorBounds((.5,2.),(.5,2.),0.,0.,('manufactured:current-bounds',),'conditional_manufactured')
    points=tuple(CurrentSolidStorage(template=point.template,skeleton=replace(point.skeleton,reference=reference,cell_index=i,viscosity_pa_s=1e6),
        error_bounds=bounds,model_id=f'point-{i}',version='1',allow_manufactured=True) for i in range(2))
    transport=operator(water,liquid_column_id='liquid',storages=tuple(p.template.fluid_template for p in points),
        face_area_m2=.014,cell_widths_m=(.01,.01),conductivities_w_m_k=(.2,.2),effective_diffusivities_m2_s={'fixture':(0.,0.)},
        permeability_m2=(0.,0.),inverse_policy=InversePolicy(1e-6,1e-6,100))
    base=replace(old.base_model,storages=tuple(p.template for p in points),transport=transport)
    return m.FreeSolidSlab(base_model=base,point_storages=points,external_pressure_pa=100000.,
        model_id='manufactured-free-slab',version='1',source_ids=('manufactured:closed-boundary',),allow_manufactured=True)


def initial(op):return op.state_from_temperatures([[0.,.01,2.],[0.,.008,2.]],[300.,301.],normal_stretches=(.95,1.03),tangential_stretch=.99)


def test_actual_geometry_shared_faces_and_single_inverse(water,monkeypatch):
    op=host(water);state=initial(op);calls=[];original=CurrentSolidStorage.temperature_from_total_energy
    def counted(self,*args,**kw):calls.append(self.skeleton.cell_index);return original(self,*args,**kw)
    monkeypatch.setattr(CurrentSolidStorage,'temperature_from_total_energy',counted)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',lambda *a:pytest.fail('second inverse'))
    out=op.evaluate(state,0.)
    assert calls==[0,1]
    np.testing.assert_array_equal(out.geometry.widths_m,[.95*.01,1.03*.01])
    assert out.current_host.transport.face_area_m2==.014*.99**2
    temps=[v.mechanical.temperature_k for v in out.storage_states]
    expected=(F(temps[0])-F(temps[1]))*F(out.current_host.transport.face_area_m2)/(F(.95*.01)/2/F(.2)+F(1.03*.01)/2/F(.2))
    assert abs(F(float(out.rates.face_energy_w[1]))-expected)<F(1e-12)
    assert np.all(out.rates.face_species_mol_s==0.)
    for i,inv in enumerate(out.total_inverses):
        assert inv.thermal_inverse is out.storage_inverses[i]
        assert inv.thermal_inverse.state is out.storage_states[i]
        assert out.current_host.storages[i] is inv.state.current_storage
        assert out.current_host.storages[i].fluid_template is out.current_host.transport.storages[i]
    for a in (state.mechanical_stretches,out.geometry.widths_m):
        with pytest.raises(ValueError):a.flags.writeable=True


def test_local_constraint_work_and_conservation(water):
    op=host(water);state=initial(op);out=op.evaluate(state,0.)
    assert out.free.zero_balance_enclosed
    assert set(out.rates.cell_power_components_w)=={'external_traction','mechanical_constraint','body'}
    assert any(abs(v)>0 for v in out.free.constraint_powers_w)
    for i in range(2):
        expected=F(out.free.external_powers_w[i])+F(out.free.constraint_powers_w[i])
        assert out.rates.cell_power_w[i]==float(expected)
    np.testing.assert_array_equal(out.rates.mechanical_rates_per_s,out.free.rates)
    dn,du=out.rates.derivatives(state)
    assert np.all(dn==0.)
    assert abs(sum(map(F,map(float,du)))-sum(map(F,map(float,out.rates.cell_power_w))))<F(1e-12)


def test_source_and_state_guards(water):
    op=host(water);state=initial(op)
    with pytest.raises(ValueError):op.evaluate(replace(state,energy_model_identity=('wrong',)),0.)
    bad=np.array(state.amounts_mol);bad[0,2]=1.9
    with pytest.raises(ValueError,match='fixed_solid'):op.evaluate(replace(state,amounts_mol=bad),0.)
    with pytest.raises(ValueError):replace(op,point_storages=tuple(reversed(op.point_storages)))
    with pytest.raises(ValueError):replace(op,allow_manufactured=False)
    with pytest.raises(ValueError):op.state_from_temperatures(state.amounts_mol,[300.],normal_stretches=(1.,1.),tangential_stretch=1.)
    object.__setattr__(op.base_model.transport,'conductivities_w_m_k',(.3,.3))
    with pytest.raises(ValueError,match='runtime_base'):op.evaluate(state,0.)


def test_second_cell_decode_failure_preserves_complete_previous_prefix(water,monkeypatch):
    from sludge_sandbox.integration import integrate
    from sludge_sandbox.deforming_solid_storage import DeformingStorageError
    from test_integration import policy
    op=host(water);state=initial(op)
    original=CurrentSolidStorage.temperature_from_total_energy;calls=0
    def fail_after_prefix(self,*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==18:
            assert self.skeleton.cell_index==1
            raise DeformingStorageError('manufactured_second_cell_decode_failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(CurrentSolidStorage,'temperature_from_total_energy',fail_after_prefix)
    out=integrate(state,op,start_s=0.,end_s=.01,
        policy=policy(initial_step_s=.001,maximum_step_s=.001,stretch_absolute_tolerance=1e-9,stretch_scale=1.))
    assert out.status=='numerical_failure' and out.reason=='manufactured_second_cell_decode_failure'
    assert len(out.steps)==1 and out.times_s==(0.,.001)
    assert len(out.states)==2 and out.states[-1].mechanical_stretches.shape==(3,)
    assert out.states[-1].energy_model_identity==op.energy_model_identity
    assert np.array_equal(out.states[-1].amounts_mol,state.amounts_mol)
