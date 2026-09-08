from dataclasses import replace
from fractions import Fraction as F
from decimal import Decimal as D,localcontext
import pytest
from test_dynamic_solid_storage import build as dynamic_build,water,forbid_water_eos,R
from sludge_sandbox.phase_storage import InversePolicy
import sludge_sandbox.current_solid_storage as m


def point(water):
    old=dynamic_build(water)
    reference=replace(old.skeleton.reference,cells=3)
    sk=replace(old.skeleton,reference=reference,cell_index=2,fixed_solid_inventory_mol=(('fixture_solid',.5),))
    template=replace(old.template,bulk_volume_m3=sk.reference_volume_m3)
    return m.CurrentSolidStorage(template=template,skeleton=sk,error_bounds=old.error_bounds,
        model_id='manufactured:current-point',version='1',allow_manufactured=True)


def inputs(**kw):return dict(normal_stretches=(.8,1.1,.97),tangential_stretch=.99,
    liquid_mol=0.,gas_mol={'fixture':.001},solid_mol={'fixture_solid':.5})|kw


def test_global_geometry_pressure_energy(water):
    p=point(water);out=p.forward(300.,**inputs());ref=p.skeleton.reference
    v0=F(ref.reference_area_m2)*F(ref.half_thickness_m)/3
    exact=v0*F(.97)*F(.99)**2
    assert abs(F(out.current_storage.bulk_volume_m3)-exact)<=F(out.current_bulk_error_bound_m3)
    expected_pressure=F(.001)*F(R)*F(300)/(exact-F(.5)*F(2e-5))
    assert abs(F(out.thermal_state.mechanical.pressure_pa)-expected_pressure)<=F(out.thermal_state.pressure_error_bound_pa)
    g=out.deformation.current
    assert tuple(g.widths_m)==tuple(v*(ref.half_thickness_m/3) for v in (.8,1.1,.97))
    assert g.faces_m[-1]==sum(g.widths_m)
    with localcontext() as c:
        c.prec=90
        n=D.from_float(.97);t=D.from_float(.99);ln=n.ln();lt=t.ln();theta=ln+2*lt
        sk=p.skeleton;v=D(v0.numerator)/D(v0.denominator)
        recover=v*(D(sk.bulk_modulus_pa)*theta**2/2+D(sk.shear_modulus_pa)*((ln-theta/3)**2+2*(lt-theta/3)**2))+D(sk.interface_energy_j_m2)*D(sk.reference_interface_area_m2)*t*t
        thermal=F(.5)*(F(-100000)+F(5)*300-F(1e5)*F(2e-5))+F(.001)*(F(30)-F(R))*300
        expected=recover+D(thermal.numerator)/D(thermal.denominator)
        assert abs(D(out.total_energy_j)-expected)<=D(out.energy_error_bound_j)


def test_inverse_target_and_bounds(water):
    p=point(water);state=p.forward(300.,**inputs())
    inv=p.temperature_from_total_energy(p.target(state.total_energy_j,0.),temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**inputs())
    assert inv.thermal_inverse.state is inv.state.thermal_state
    assert abs(inv.state.thermal_state.mechanical.temperature_k-300.)<=inv.temperature_error_bound_k
    with pytest.raises(ValueError,match='matching_explicit'):
        p.temperature_from_total_energy(replace(p.target(state.total_energy_j,0.),model_identity=('wrong',)),temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**inputs())


@pytest.mark.parametrize('kw',[{'solid_mol':{'fixture_solid':.4}},{'normal_stretches':(.9,)},{'normal_stretches':(.8,False,.97)},{'normal_stretches':(.4,1.1,.97)}])
def test_domains(water,kw):
    with pytest.raises(ValueError):point(water).forward(300.,**inputs(**kw))


def test_identity_immutability_and_source_guard(water):
    p=point(water);state=p.forward(300.,**inputs());identity=p.identity
    p.forward(300.,**inputs(normal_stretches=(.9,1.,1.)))
    assert p.identity==identity
    for array in vars(state.deformation.current).values():
        with pytest.raises(ValueError):array.flags.writeable=True
    changed=replace(p.template.solid_phases['fixture_solid'],molar_volume_m3_mol=2.1e-5)
    object.__setattr__(p.template,'solid_phases',{'fixture_solid':changed})
    with pytest.raises(ValueError,match='runtime_template'):
        p.forward(300.,**inputs())


def test_single_cell_storage_parity_without_free_closure(water,monkeypatch):
    old=dynamic_build(water)
    kw=dict(liquid_mol=0.,gas_mol={'fixture':.01},solid_mol={'fixture_solid':2.})
    prior=old.forward(300.,normal_stretch=.97,tangential_stretch=.99,external_pressure_pa=1e5,**kw)
    p=m.CurrentSolidStorage(template=old.template,skeleton=old.skeleton,error_bounds=old.error_bounds,
        model_id='current',version='1',allow_manufactured=True)
    import sludge_sandbox.free_skeleton_rates as free
    monkeypatch.setattr(free,'solve_free_rates',lambda *a,**k:pytest.fail('thermodynamic point called free closure'))
    import sludge_sandbox.dynamic_solid_storage as dynamic
    monkeypatch.setattr(dynamic,'solve_free_rates',lambda *a,**k:pytest.fail('imported free closure alias called'))
    out=p.forward(300.,normal_stretches=(.97,),tangential_stretch=.99,**kw)
    for field in ('total_energy_j','energy_error_bound_j','mechanical_energy_error_bound_j',
                  'total_addition_roundoff_j','current_bulk_error_bound_m3'):
        assert getattr(out,field)==getattr(prior,field)
    assert out.thermal_state.mechanical.pressure_pa==prior.thermal_state.mechanical.pressure_pa


def test_declared_geometry_uncertainty_preserved(water):
    p=point(water);out=p.forward(300.,**inputs())
    uncertain=replace(p,template=replace(p.template,bulk_volume_error_m3=1e-12))
    wide=uncertain.forward(300.,**inputs())
    assert F(wide.current_bulk_error_bound_m3)>=F(.97)*F(.99)**2*F(1e-12)
    assert wide.current_bulk_error_bound_m3>out.current_bulk_error_bound_m3
    assert wide.mechanical_energy_error_bound_j>out.mechanical_energy_error_bound_j
    assert wide.energy_error_bound_j>out.energy_error_bound_j
    with pytest.raises(ValueError):
        uncertain.temperature_from_total_energy(p.target(out.total_energy_j,0.),
            temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**inputs())
