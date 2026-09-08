from dataclasses import replace
from fractions import Fraction as F
import importlib.util,sys
from pathlib import Path
import pytest
from test_dynamic_solid_storage import build,water,forbid_water_eos,R
from sludge_sandbox.reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.current_solid_storage import CurrentSolidStorage as Original
spec=importlib.util.spec_from_file_location('sludge_sandbox._reacting_point_candidate',Path(__file__).with_name('current_solid_storage.py'))
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)


def fixture(water,reacting=True):
    old=build(water)
    skeleton=old.skeleton
    if reacting:
        skeleton=ManufacturedReactingSkeletonEnergy(reference_model=skeleton,composition_offset=.5,
            composition_weights_per_mol=(('fixture_solid',.25),),model_id='manufactured-q',version='1',
            classification='manufactured_test_fixture',allow_manufactured=True)
    return m.CurrentSolidStorage(template=old.template,skeleton=skeleton,error_bounds=old.error_bounds,
        model_id='current',version='1',allow_manufactured=True,solid_inventory_regime='reacting_manufactured' if reacting else 'fixed_solid')


def args(amount=2.):return dict(normal_stretches=(.97,),tangential_stretch=.99,liquid_mol=0.,gas_mol={'fixture':.01},solid_mol={'fixture_solid':amount})


def test_changed_composition_energy_pore_pressure_and_temperature(water):
    point=fixture(water);identity=point.identity
    initial=point.forward(300.,**args());changed=point.forward(300.,**args(1.))
    assert point.identity==identity and changed.qualification.startswith('manufactured_reacting')
    sk=point.skeleton.reference_model
    base=sk.evaluate(normal_stretch=.97,tangential_stretch=.99,normal_rate_per_s=0.,tangential_rate_per_s=0.,solid_inventory_mol={'fixture_solid':2.})
    reference=F(base.elastic_energy_j)+F(base.interface_energy_j)
    # q1=.75, thermal solid per mole u=-98502 at300K; gas stays unchanged.
    expected_delta= -F(-100000+5*300-1e5*2e-5)-F(1,4)*reference
    bound=F(initial.energy_error_bound_j)+F(changed.energy_error_bound_j)
    assert abs(F(changed.total_energy_j)-F(initial.total_energy_j)-expected_delta)<=bound
    assert changed.thermal_state.available_pore_volume_m3>initial.thermal_state.available_pore_volume_m3
    volume=F(point.skeleton.reference_volume_m3)*F(.97)*F(.99)**2-F(2e-5)
    expected_pressure=F(.01)*F(R)*300/volume
    assert abs(F(changed.thermal_state.mechanical.pressure_pa)-expected_pressure)<=F(changed.thermal_state.pressure_error_bound_pa)
    # Small current-composition change keeps the strict original T bracket.
    amount=2.-1e-8
    inv=point.temperature_from_total_energy(point.target(initial.total_energy_j,0.),temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args(amount))
    q=F(.5)+F(.25)*F(amount)
    cv=F(amount)*5+F(.01)*(F(30)-F(R))
    expected_t=(F(initial.total_energy_j)-F(amount)*F(-100002)-q*reference)/cv
    assert abs(F(inv.state.thermal_state.mechanical.temperature_k)-expected_t)<=F(inv.temperature_error_bound_k)
    assert inv.thermal_inverse.state is inv.state.thermal_state


def test_fixed_default_identity_numeric_parity(water):
    p=fixture(water,False)
    old=Original(template=p.template,skeleton=p.skeleton,error_bounds=p.error_bounds,model_id=p.model_id,version=p.version,allow_manufactured=True)
    assert p.identity==old.identity
    a=p.forward(300.,**args());b=old.forward(300.,**args())
    for field in ('total_energy_j','energy_error_bound_j','mechanical_energy_error_bound_j','current_bulk_error_bound_m3'):
        assert getattr(a,field)==getattr(b,field)
    with pytest.raises(ValueError):p.forward(300.,**args(1.))


def test_regime_allzero_and_target_guards(water):
    p=fixture(water)
    with pytest.raises(ValueError):p.forward(300.,**args(0.))
    with pytest.raises(ValueError):replace(p,solid_inventory_regime='fixed_solid')
    with pytest.raises(ValueError):replace(p,solid_inventory_regime='unknown')
    with pytest.raises(ValueError):replace(p,allow_manufactured=False)
    fixed=fixture(water,False)
    with pytest.raises(ValueError):p.temperature_from_total_energy(fixed.target(-197000.,0.),temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())


def test_independent_interface_q_derivative_and_source_mutation(water):
    p=fixture(water);sk=p.skeleton.reference_model
    state=p.forward(300.,**(args(1.)|{'normal_stretches':(1.,),'tangential_stretch':1.}))
    interface=F(sk.interface_energy_j_m2)*F(sk.reference_interface_area_m2)
    assert abs(F(state.skeleton_state.interface_energy_j)-F(3,4)*interface)<=F(state.skeleton_state.numerical_error_bounds['interface_energy_j'])
    derivative=state.skeleton_state.interface_composition_derivative_j_mol['fixture_solid']
    assert abs(F(derivative)-interface/4)<=F(state.skeleton_state.numerical_error_bounds['interface_composition_derivative_j_mol']['fixture_solid'])
    changed=replace(p.template.solid_phases['fixture_solid'],molar_volume_m3_mol=2.1e-5)
    object.__setattr__(p.template,'solid_phases',{'fixture_solid':changed})
    with pytest.raises(ValueError,match='runtime_template'):
        p.forward(300.,**args())
