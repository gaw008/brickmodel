from dataclasses import replace
from fractions import Fraction
import math

import numpy as np
import pytest
from scipy.optimize import brentq

from sludge_sandbox.solid_fluid_storage import SolidFluidStorage,SolidFluidStorageError
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.integration import ConservedState,Rates,IntegrationPolicy,integrate
from test_rigid_storage import model as fluid_model,water,R
from test_incompressible_solid import phase


def model(water,**changes):
    values=dict(fluid_template=fluid_model(water),solid_phases={'fixture_solid':phase()},bulk_volume_m3=1.4e-4,
        bulk_volume_error_m3=1e-15,geometry_source_ids=('manufactured:bulk',),geometry_id='manufactured:bulk',geometry_version='1',
        geometry_classification='manufactured_test_fixture',allow_manufactured=True)
    values.update(changes)
    return SolidFluidStorage(**values)


def test_pure_gas_solid_actual_forward_and_inverse(water):
    m=model(water)
    state=m.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':2.})
    assert state.available_pore_volume_m3==float(Fraction(1.4e-4)-2*Fraction(2e-5))
    assert state.mechanical.pressure_pa==pytest.approx(.01*R*300/1e-4,rel=0,abs=1e-9)
    assert state.internal_energy_j==pytest.approx(2*(-100000+5*300-2)+.01*(30-R)*300,rel=0,abs=1e-9)
    assert state.closed_heat_capacity_j_k==pytest.approx(10+.01*(30-R),rel=0,abs=1e-12)
    inverse=m.temperature_from_energy(state.internal_energy_j,0.,{'fixture':.01},{'fixture_solid':2.},(295.,310.),InversePolicy(1e-6,1e-6,100))
    assert inverse.state.mechanical.temperature_k==pytest.approx(300.,rel=0,abs=1e-6)
    assert inverse.final_temperature_bracket_k[0]<=300<=inverse.final_temperature_bracket_k[1]
    assert state.enthalpy_j-state.internal_energy_j==pytest.approx(state.mechanical.pressure_pa*1.4e-4,rel=0,abs=1e-8)


def test_actual_constant_power_integration_uses_full_inventory_inverse(water):
    m=model(water)
    start=m.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':2.})
    initial=ConservedState([[0.,.01,2.]],[start.internal_energy_j])
    trials=[]
    def operator(state,time):
        row=state.amounts_mol[0]
        inverse=m.temperature_from_energy(float(state.internal_energy_j[0]),float(row[0]),{'fixture':float(row[1])},
            {'fixture_solid':float(row[2])},(295.,310.),InversePolicy(1e-6,1e-6,100))
        trials.append(inverse.state.mechanical.temperature_k)
        return Rates(np.zeros((2,3)),np.zeros(2),np.zeros((1,3)),np.array([2.]))
    out=integrate(initial,operator,start_s=0,end_s=.1,policy=IntegrationPolicy(initial_step_s=.1,
        maximum_step_s=.1,minimum_step_s=1e-10,relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-10,
        energy_absolute_tolerance_j=1e-6,amount_scale_mol=1.,energy_scale_j=1.,maximum_steps=10,
        maximum_rejections=10,maximum_wall_seconds=90))
    assert out.status=='completed',(out.status,out.reason)
    for t,s in zip(out.times_s,out.states):
        assert s.internal_energy_j[0]==pytest.approx(start.internal_energy_j+2*t,rel=0,abs=1e-8)
        assert np.array_equal(s.amounts_mol,initial.amounts_mol)
    end=m.temperature_from_energy(float(out.states[-1].internal_energy_j[0]),0.,{'fixture':.01},{'fixture_solid':2.},
        (295.,310.),InversePolicy(1e-6,1e-6,100))
    assert end.state.mechanical.temperature_k==pytest.approx(300+.2/(10+.01*(30-R)),rel=0,abs=1e-6)
    assert len(set(trials))>1


@pytest.mark.parametrize('nl',[0.,2.])
def test_declared_solid_volume_error_covers_independent_perturbed_pressure_and_energy(water,nl):
    m=model(water,solid_phases={'fixture_solid':phase(declared_v_error_m3_mol=1e-10,declared_u_error_j_mol=2e-5)})
    out=m.evaluate_at_temperature(300.,nl,{'fixture':.01},{'fixture_solid':2.})
    for sign in (-1,1):
        v=2e-5+sign*1e-10
        available=1.4e-4-2*v
        def residual(p):
            vl=0 if not nl else nl*water.reference.molar_mass_kg_mol/water.state_tp(300,p,phase='liquid').density_kg_m3
            return vl+.01*R*300/p-available
        p=brentq(residual,1e4,1e6,xtol=1e-7)
        u=2*(-98500-1e5*v)+.01*(30-R)*300
        if nl:u+=nl*water.state_tp(300,p,phase='liquid').internal_energy_j_mol
        assert abs(p-out.mechanical.pressure_pa)<=out.pressure_error_bound_pa
        assert abs(u-out.internal_energy_j)<=out.energy_error_bound_j


@pytest.mark.parametrize('solids',[{}, {'other':1.},{'fixture_solid':-1.},{'fixture_solid':10.}])
def test_bad_inventory(water,solids):
    with pytest.raises(SolidFluidStorageError):model(water).evaluate_at_temperature(300.,0.,{'fixture':.01},solids)


def test_zero_solid_preserves_fluid_forward(water):
    m=model(water,bulk_volume_m3=1e-4)
    state=m.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':0.})
    fluid=m.fluid_template.evaluate_at_temperature(300.,0.,{'fixture':.01})
    assert state.internal_energy_j==fluid.internal_energy_j
    assert state.mechanical.gas_volume_m3==fluid.mechanical.gas_volume_m3


def test_zero_gas_not_patched_and_manufactured_gate(water):
    with pytest.raises(ValueError):model(water).evaluate_at_temperature(300.,0.,{'fixture':0.},{'fixture_solid':2.})
    with pytest.raises(SolidFluidStorageError):model(water,allow_manufactured=False)


def test_declared_budget_cannot_claim_tighter_inverse(water):
    m=model(water)
    u=m.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':2.}).internal_energy_j
    with pytest.raises(SolidFluidStorageError,match='exceeds_inverse'):
        m.temperature_from_energy(u,0.,{'fixture':.01},{'fixture_solid':2.},(295.,310.),InversePolicy(1e-9,1e-9,100))


def test_inventory_change_recomputes_solid_volume_and_temperature_storage(water):
    m=model(water)
    a=m.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':2.})
    b=m.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':1.})
    assert a.solid_volume_m3==2*b.solid_volume_m3
    assert b.mechanical.pressure_pa<a.mechanical.pressure_pa
    assert b.internal_energy_j-a.internal_energy_j==pytest.approx(98502.,rel=0,abs=1e-9)


def test_nominal_valid_pressure_with_volume_uncertainty_outside_domain_rejects(water):
    m=model(water,bulk_volume_error_m3=1e-5)
    with pytest.raises(SolidFluidStorageError,match='pressure_uncertainty'):
        m.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':2.})


def test_complete_zero_solid_has_no_active_point_and_cannot_mutate_diagnostics(water):
    m=model(water)
    out=m.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':0.})
    assert out.solid_points=={}
    assert out.solid_inventory_mol=={'fixture_solid':0.}
    with pytest.raises(TypeError):out.solid_inventory_mol['fixture_solid']=1.


@pytest.mark.parametrize('changes',[dict(geometry_source_ids=()),dict(geometry_id=''),dict(geometry_version=''),
    dict(geometry_classification='unknown'),dict(bulk_volume_error_m3=-1.),dict(bulk_volume_m3=0.)])
def test_bad_geometry_identity(water,changes):
    with pytest.raises(SolidFluidStorageError):model(water,**changes)


def test_same_species_across_solid_gas_requires_same_molar_mass(water):
    p=phase()
    p=replace(p,caloric=replace(p.caloric,species_id='fixture'))
    with pytest.raises(SolidFluidStorageError,match='molar_mass_mismatch'):
        model(water,solid_phases={'fixture':p})


def test_solid_temperature_domain_is_not_silently_skipped_when_active(water):
    p=phase()
    p=replace(p,caloric=replace(p.caloric,temperature_range_k=(301.,500.)))
    with pytest.raises(ValueError,match='solid_temperature_out_of_domain'):
        model(water,solid_phases={'fixture_solid':p}).evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':1.})


def test_virtual_geometry_is_explicit_design_not_material_qualification(water):
    m=model(water,geometry_classification='virtual_design_choice',geometry_id='virtual:cell-box',
        geometry_source_ids=('virtual-design:cell-box-v1',))
    assert m.geometry_classification=='virtual_design_choice'
    assert m.geometry_id=='virtual:cell-box'
    assert 'virtual-design:cell-box-v1' in m.source_ids
    assert not m.material_qualified
    # A virtual geometry does not remove manufactured material opt-in.
    with pytest.raises(SolidFluidStorageError,match='manufactured'):
        replace(m,allow_manufactured=False)
    for changes in ({'geometry_source_ids':()}, {'geometry_id':''}, {'geometry_version':''}):
        with pytest.raises(SolidFluidStorageError):replace(m,**changes)
    # The design category is deliberately unavailable to a material provider.
    with pytest.raises(ValueError,match='classification'):
        replace(m.solid_phases['fixture_solid'],volume_classification='virtual_design_choice')
