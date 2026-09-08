"""Free mechanics coupled to actual point energy/pressure, manufactured materials."""
from dataclasses import replace
import math
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from sludge_sandbox.free_solid_cell import ClosedFreeSolidCell
from sludge_sandbox.dynamic_solid_storage import DynamicSolidStorage,DynamicStorageErrorBounds
from sludge_sandbox.solid_fluid_heat import InventoryLayout
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.integration import integrate,ConservedState
from test_deforming_solid_storage import exact_volume_wet_model
from test_integration import policy
from test_rigid_storage import water,R


def host(water):
    original=exact_volume_wet_model(water)
    point=DynamicSolidStorage(template=original.template,
        skeleton=replace(original.skeleton,viscosity_pa_s=1e6),
        error_bounds=DynamicStorageErrorBounds((.5,2.),(.5,2.),0.,0.,('manufactured-error',),'manufactured'),
        model_id='free-cell-point',version='1',allow_manufactured=True)
    return ClosedFreeSolidCell(point=point,inventory_layout=InventoryLayout(
        species_order=('liquid','fixture','fixture_solid'),liquid_column_id='liquid',
        gas_species_order=('fixture',),solid_species_order=('fixture_solid',)),
        external_pressure_pa=101325.,body_power_w=0.,temperature_bracket_k=(295.,310.),
        inverse_policy=InversePolicy(1e-6,1e-6,100),source_ids=('manufactured-constant-boundary',),
        model_id='free-cell-test',version='1')


def test_dry_full_stage_coupling_against_independent_energy_pressure_ode(water,monkeypatch):
    op=host(water)
    monkeypatch.setattr(type(water),'state_tp',lambda *a,**k:pytest.fail('dry case called water EOS'))
    initial=op.state_from_temperature([[0.,.01,2.]],300.,normal_stretch=1.,tangential_stretch=1.)
    v=op.point.skeleton.reference_volume_m3
    heat_capacity=10+.01*(30-R)
    def oracle(_,state):
        n,t,energy=state
        theta=math.log(n)+2*math.log(t)
        elastic=v*(500*theta**2+400*((math.log(n)-theta/3)**2+2*(math.log(t)-theta/3)**2))
        temperature=(energy-elastic-.0015*t*t+200004.)/heat_capacity
        pressure=.01*R*temperature/(v*n*t*t-4e-5)
        normal=(n*n/1e6)*((pressure-101325)*t*t-(1000*theta+800*(math.log(n)-theta/3))/n)
        tangent=(t*t/1e6)*((pressure-101325)*n*t-(1000*theta+800*(math.log(t)-theta/3))/t-.0015*t/v)
        return [normal,tangent,-101325*v*(t*t*normal+2*n*t*tangent)]
    independent=solve_ivp(oracle,(0.,.1),[1.,1.,float(initial.internal_energy_j[0])],
                          method='DOP853',rtol=1e-12,atol=1e-13)
    assert independent.success
    numerical=policy(initial_step_s=.025,maximum_step_s=.025,
        relative_tolerance=1e-8,energy_absolute_tolerance_j=1e-6,stretch_absolute_tolerance=1e-9,stretch_scale=1.)
    result=integrate(initial,op,start_s=0.,end_s=.1,policy=numerical)
    assert result.status=='completed',result.reason
    final=result.states[-1];decoded=op.evaluate(final,.1).inverse.state
    assert np.max(np.abs(final.mechanical_stretches-independent.y[:2,-1]))<2e-7
    assert abs(final.internal_energy_j[0]-independent.y[2,-1])<2e-6
    volume=decoded.deformation.current.volumes_m3[0]
    assert abs(final.internal_energy_j[0]-initial.internal_energy_j[0]+101325*(volume-v))<2e-6
    assert decoded.thermal_state.mechanical.temperature_k<300.
    assert all(set(s.cell_work_components_j)=={'external_traction','body'} for s in result.steps)
    assert all(np.array_equal(s.amounts_mol,initial.amounts_mol) for s in result.states)
    from sludge_sandbox.checkpoint import audit_integration
    from sludge_sandbox.verification_case import encode
    audit_integration(encode(result),numerical,start_s=0.,end_s=.1)


def test_free_work_cannot_mix_with_stored_energy_components():
    from sludge_sandbox.integration import Rates
    with pytest.raises(ValueError,match='invalid_component_work_keys'):
        Rates([[0.],[0.]],[0.,0.],[[0.]],[0.],{'external_traction':[0.],'dissipation':[0.]})


def test_geometry_failure_returns_numerical_result_without_losing_initial_state(water,monkeypatch):
    from sludge_sandbox.geometry import GeometryError
    op=host(water)
    initial=op.state_from_temperature([[0.,.01,2.]],300.,normal_stretch=1.,tangential_stretch=1.)
    def fail(*args,**kwargs):raise GeometryError('unrepresentable_geometry')
    monkeypatch.setattr(type(op.point),'temperature_from_total_energy',fail)
    result=integrate(initial,op,start_s=0.,end_s=.1,policy=policy(stretch_absolute_tolerance=1e-9,stretch_scale=1.))
    assert result.status=='numerical_failure' and result.reason=='unrepresentable_geometry'
    assert len(result.states)==1 and result.states[0] is initial


def test_power_representation_failure_retains_an_accepted_prefix(water,monkeypatch):
    import sludge_sandbox.free_solid_cell as module
    op=host(water)
    initial=op.state_from_temperature([[0.,.01,2.]],300.,normal_stretch=1.,tangential_stretch=1.)
    original=module._out;calls=0
    def fail_after_prefix(value):
        nonlocal calls
        calls+=1
        if calls>=9:raise module.DeformingStorageError('unrepresentable_energy')
        return original(value)
    monkeypatch.setattr(module,'_out',fail_after_prefix)
    result=integrate(initial,op,start_s=0.,end_s=.1,
        policy=policy(initial_step_s=.001,maximum_step_s=.001,stretch_absolute_tolerance=1e-9,stretch_scale=1.))
    assert result.status=='numerical_failure' and result.reason=='unrepresentable_energy'
    assert len(result.steps)==1 and len(result.states)==2


def test_free_host_requires_matching_energy_and_explicit_geometry(water):
    op=host(water)
    with pytest.raises(ValueError,match='explicit_dynamic_stretches'):
        op.evaluate(ConservedState([[0.,.01,2.]],[0.]),0.)
    with pytest.raises(ValueError,match='matching_free_cell_energy'):
        op.evaluate(ConservedState([[0.,.01,2.]],[0.],mechanical_stretches=[1.,1.]),0.)
    assert replace(op,external_pressure_pa=100000.).energy_model_identity!=op.energy_model_identity
