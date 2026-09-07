"""Point-storage tests; dry branch explicitly forbids real water EOS."""
from dataclasses import replace
from fractions import Fraction
import pytest
from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.deformation_program import PrescribedSlabMotion
from sludge_sandbox.skeleton_energy import DiagonalSkeletonEnergy
from sludge_sandbox.phase_storage import InversePolicy
from test_rigid_storage import water
from test_solid_fluid_storage import model as base_storage

import sludge_sandbox.deforming_solid_storage as m


def build(water):
    base=base_storage(water,bulk_volume_error_m3=1e-18)
    reference=ReferenceSlab(.01,.014,1)
    motion=PrescribedSlabMotion(reference=reference,knot_times_s=(0.,1.),normal_stretches_at_knots=((1.,),(.9,)),
        tangential_stretches_at_knots=(1.,1.),motion_id='motion-fixture',version='1',classification='manufactured_test_fixture',source_ids=('fixture-motion',),source_asset_sha256=())
    skeleton=DiagonalSkeletonEnergy(reference=reference,cell_index=0,fixed_solid_inventory_mol=(('fixture_solid',2.),),
        solid_provider_identity=m.solid_provider_identity(base.solid_phases),bulk_modulus_pa=1000.,shear_modulus_pa=400.,viscosity_pa_s=3.,
        interface_energy_j_m2=.5,reference_interface_area_m2=.003,stretch_range=(.5,2.),maximum_absolute_log_rate_per_s=2.,
        model_id='fixture-skeleton',version='1',source_ids=('fixture-skeleton',),classification='manufactured_test_fixture',allow_manufactured=True)
    bounds=m.DeformationErrorBounds((0.,1.),0.,0.,('fixture-exact-motion-inputs',),'conditional_declared_not_material_admission')
    return m.DeformingSolidStorage(template=base,motion=motion,skeleton=skeleton,error_bounds=bounds,model_id='fixture-storage',version='1',allow_manufactured=True)


def args():return dict(liquid_mol=0.,gas_mol={'fixture':.01},solid_mol={'fixture_solid':2.},time_s=.5)


def test_dry_forward_total_energy_and_true_current_pressure_without_water_eos(water,monkeypatch):
    p=build(water)
    def forbidden(*a,**k):raise AssertionError('dry branch called water EOS')
    monkeypatch.setattr(type(water),'state_tp',forbidden)
    s=p.forward(300.,**args())
    assert s.total_energy_j==pytest.approx(s.thermal_state.internal_energy_j+s.skeleton_state.elastic_energy_j+s.skeleton_state.interface_energy_j,abs=1e-9,rel=0)
    assert s.thermal_state.available_pore_volume_m3==pytest.approx(s.motion.current.volumes_m3[0]-4e-5,abs=1e-18,rel=0)
    assert s.thermal_state.mechanical.pressure_pa>p.template.evaluate_at_temperature(300.,0.,{'fixture':.01},{'fixture_solid':2.}).mechanical.pressure_pa
    assert s.energy_error_bound_j>=s.thermal_state.energy_error_bound_j


def test_total_target_roundtrip_and_scope(water):
    p=build(water);s=p.forward(300.,**args());target=p.target(s.total_energy_j,s.energy_error_bound_j)
    inverse=p.temperature_from_total_energy(target,temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())
    assert abs(inverse.state.thermal_state.mechanical.temperature_k-300.)<=inverse.temperature_error_bound_k
    assert inverse.thermal_inverse.target_energy_error_bound_j>=target.error_bound_j
    with pytest.raises(m.DeformingStorageError):p.temperature_from_total_energy(s.total_energy_j,temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())
    with pytest.raises(m.DeformingStorageError):p.temperature_from_total_energy(replace(target,energy_scope='thermal'),temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())


def test_actual_solid_identity_cannot_be_relabelled(water):
    p=build(water)
    with pytest.raises(m.DeformingStorageError):replace(p,skeleton=replace(p.skeleton,solid_provider_identity=('arbitrary',)))
    phase=p.template.solid_phases['fixture_solid'];altered=replace(phase,molar_volume_m3_mol=phase.molar_volume_m3_mol*1.01)
    assert m.solid_provider_identity({'fixture_solid':altered})!=m.solid_provider_identity(p.template.solid_phases)
    with pytest.raises(m.DeformingStorageError):replace(p,template=replace(p.template,solid_phases={'fixture_solid':altered}))


def test_inventory_geometry_and_manufactured_boundaries(water):
    p=build(water)
    with pytest.raises(m.DeformingStorageError):replace(p,allow_manufactured=False)
    with pytest.raises(m.DeformingStorageError):replace(p,template=replace(p.template,bulk_volume_m3=2*p.template.bulk_volume_m3))
    with pytest.raises(ValueError):p.forward(300.,**(args()|{'solid_mol':{'fixture_solid':1.}}))
    with pytest.raises(ValueError):p.forward(300.,**(args()|{'time_s':2.}))


def test_large_explicit_additional_energy_bound_cannot_claim_precision(water):
    p=build(water);p=replace(p,error_bounds=replace(p.error_bounds,additional_mechanical_energy_error_j=.1))
    s=p.forward(300.,**args())
    with pytest.raises(ValueError):p.temperature_from_total_energy(p.target(s.total_energy_j,0.),temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())


def test_addition_subtraction_error_and_reference_volume_propagation(water):
    p=build(water);s=p.forward(300.,**args())
    exact=sum((Fraction(s.thermal_state.internal_energy_j),Fraction(s.skeleton_state.elastic_energy_j),Fraction(s.skeleton_state.interface_energy_j)),Fraction())
    assert Fraction(s.total_addition_roundoff_j)>=abs(Fraction(s.total_energy_j)-exact)
    assert Fraction(s.energy_error_bound_j)>=Fraction(s.thermal_state.energy_error_bound_j)+Fraction(s.mechanical_energy_error_bound_j)+abs(Fraction(s.total_energy_j)-exact)
    altered=replace(p,template=replace(p.template,bulk_volume_error_m3=1e-12))
    changed=altered.forward(300.,**args())
    assert changed.current_bulk_error_bound_m3>s.current_bulk_error_bound_m3
    assert changed.mechanical_energy_error_bound_j>s.mechanical_energy_error_bound_j
    target=p.target(s.total_energy_j,1e-8)
    inv=p.temperature_from_total_energy(target,temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())
    exact_sub=Fraction(target.value_j)-Fraction(s.skeleton_state.elastic_energy_j)-Fraction(s.skeleton_state.interface_energy_j)
    assert Fraction(inv.subtraction_roundoff_j)>=abs(Fraction(inv.thermal_inverse.target_energy_j)-exact_sub)
    assert inv.thermal_inverse.target_energy_error_bound_j>=target.error_bound_j+s.mechanical_energy_error_bound_j


def test_total_fraction_target_rounding_explicit_and_invalid_tiny_reject(water):
    p=build(water);x=Fraction(1,3);target=p.target(x,0.)
    assert Fraction(target.error_bound_j)>=abs(Fraction(target.value_j)-x)
    tiny=Fraction(1,10**400)
    for value,error in ((-tiny,0.),(0.,-tiny),(0.,tiny)):
        with pytest.raises(m.DeformingStorageError):p.target(value,error)
    with pytest.raises(m.DeformingStorageError):replace(p.error_bounds,additional_bulk_volume_error_m3=-tiny)


def test_wrong_model_target_and_lost_pore_guarantee_reject(water):
    p=build(water);s=p.forward(300.,**args())
    other=replace(p,version='2')
    with pytest.raises(m.DeformingStorageError):other.temperature_from_total_energy(p.target(s.total_energy_j,0.),temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())
    with pytest.raises(ValueError):replace(p,error_bounds=replace(p.error_bounds,additional_bulk_volume_error_m3=1e-3)).forward(300.,**args())


def test_identity_same_for_equivalent_source_load_and_diff_for_caloric_change(water):
    p=build(water);assert p.identity==build(water).identity
    phase=p.template.solid_phases['fixture_solid']
    c=phase.caloric;coefficients=list(c.coefficients);coefficients[0]+=1
    other=replace(phase,caloric=replace(c,coefficients=tuple(coefficients)))
    assert m.solid_provider_identity({'fixture_solid':other})!=m.solid_provider_identity(p.template.solid_phases)


def test_actual_wet_deformed_point_inverse_and_pressure(water):
    """Registered wet gate: <=90 s wall; original policy 1e-6 J/1e-6 K.

    Actual water, manufactured solids; no material qualification. Temperature
    error interval must contain 300 K. Pressure change must exceed combined
    fixed-T pressure bounds; total-minus-mechanical agrees with thermal target.
    """
    import time
    start=time.monotonic();p=exact_volume_wet_model(water)
    wet=args()|{'liquid_mol':1.}
    before=p.forward(300.,**(wet|{'time_s':0.}))
    after=p.forward(300.,**wet)
    assert after.thermal_state.mechanical.liquid_inventory_mol==1.
    assert after.thermal_state.available_pore_volume_m3<before.thermal_state.available_pore_volume_m3
    pa,pb=after.thermal_state,before.thermal_state
    assert pa.mechanical.pressure_pa-pa.pressure_error_bound_pa>pb.mechanical.pressure_pa+pb.pressure_error_bound_pa
    target=p.target(after.total_energy_j,after.energy_error_bound_j)
    out=p.temperature_from_total_energy(target,temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**wet)
    t=out.state.thermal_state.mechanical.temperature_k
    assert abs(t-300.)<=out.temperature_error_bound_k<=1e-6
    assert out.thermal_inverse.final_temperature_bracket_k[0]<=300.<=out.thermal_inverse.final_temperature_bracket_k[1]
    assert abs(out.total_energy_residual_j)<=1e-6
    exact=Fraction(target.value_j)-Fraction(after.skeleton_state.elastic_energy_j)-Fraction(after.skeleton_state.interface_energy_j)
    assert abs(Fraction(out.thermal_inverse.target_energy_j)-exact)<=Fraction(out.subtraction_roundoff_j)
    assert out.thermal_inverse.target_energy_error_bound_j>=target.error_bound_j
    assert time.monotonic()-start<=90.


def exact_volume_wet_model(water):
    # Distinct exact-binary-input constant-volume numerical fixture; the
    # original broad declared-volume-uncertainty fixture remains unchanged.
    import math
    p=build(water);phase=p.template.solid_phases['fixture_solid']
    exact_manufactured_volume=Fraction(1,50000)  # m3/mol, independent rational definition
    assert abs(Fraction(phase.molar_volume_m3_mol)-exact_manufactured_volume)<=Fraction(math.ulp(phase.molar_volume_m3_mol))
    phase=replace(phase,declared_v_error_m3_mol=math.ulp(phase.molar_volume_m3_mol),
        error_method_id='manufactured_exact_constant_volume_one_ulp_v1',
        error_source_ids=('manufactured:binary64-constant-volume-ulp',))
    template=replace(p.template,solid_phases={'fixture_solid':phase})
    skeleton=replace(p.skeleton,solid_provider_identity=m.solid_provider_identity(template.solid_phases))
    return replace(p,template=template,skeleton=skeleton)


def test_original_wet_volume_uncertainty_correctly_refuses_original_precision(water):
    p=build(water);wet=args()|{'liquid_mol':1.};s=p.forward(300.,**wet)
    assert s.energy_error_bound_j>1e-6
    with pytest.raises(ValueError,match='exceeds_inverse_tolerance'):
        p.temperature_from_total_energy(p.target(s.total_energy_j,s.energy_error_bound_j),temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**wet)
