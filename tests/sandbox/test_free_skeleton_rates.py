"""Independent traction/power checks for manufactured mechanical closure; no EOS."""
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import pytest
from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.skeleton_energy import DiagonalSkeletonEnergy
from sludge_sandbox.free_skeleton_rates import solve_free_rates


def model(**changes):
    values = dict(reference=ReferenceSlab(.02,.04,1), cell_index=0,
        fixed_solid_inventory_mol=(('solid',2.),), solid_provider_identity=('fixture','v1'),
        bulk_modulus_pa=1000., shear_modulus_pa=400., viscosity_pa_s=1000.,
        interface_energy_j_m2=.5, reference_interface_area_m2=.003,
        stretch_range=(.5,2.), maximum_absolute_log_rate_per_s=2.,
        model_id='free-rate-test', version='1', source_ids=('manufactured-fixture',),
        classification='manufactured_test_fixture', allow_manufactured=True)
    return DiagonalSkeletonEnergy(**(values | changes))


def solve(skeleton=None, **changes):
    return solve_free_rates(skeleton or model(), **(dict(normal_stretch=1.1,
        tangential_stretch=.9,pore_pressure_pa=100.,external_pressure_pa=101.,
        solid_inventory_mol={'solid':2.}) | changes))


def test_independent_energy_gradient_determines_both_rates():
    p=model(); answer=solve(p)
    with localcontext() as ctx:
        ctx.prec=160
        n,t=D.from_float(1.1),D.from_float(.9)
        v=D.from_float(p.reference_volume_m3)
        gamma_area=D.from_float(.5)*D.from_float(.003)
        logs=(n.ln(),t.ln(),t.ln()); theta=sum(logs)
        expected=[]
        for i,lam in enumerate((n,t)):
            elastic=(D(1000)*theta+800*(logs[i]-theta/3))/lam
            surface=D(0) if i==0 else gamma_area*t/v
            force=-n*t*t/lam-elastic-surface
            expected.append(lam*lam*force/1000)
        for actual,bound,want in zip(answer.rates,answer.rate_error_bounds,expected):
            assert abs(D.from_float(actual)-want)<=D.from_float(bound)


def test_oriented_interface_cannot_be_solved_as_isotropic_rate():
    answer=solve(normal_stretch=1.,tangential_stretch=1.,pore_pressure_pa=0.,external_pressure_pa=0.)
    assert answer.rates[0]==0
    assert answer.rates[1]<0
    assert answer.state.interface_rate_w<0 and answer.state.dissipation_w>0
    assert answer.external_power_w==0


def test_exact_fraction_certificate_for_unrepresentable_free_rate():
    p=model(viscosity_pa_s=3.)
    answer=solve(p, normal_stretch=1., tangential_stretch=1.,
                 pore_pressure_pa=0., external_pressure_pa=0.)
    volume=F(p.reference_volume_m3)
    exact_t=-F(.5)*F(.003)/(volume*3)
    expected=(F(0),exact_t,exact_t)
    rates=tuple(map(F,(answer.rates[0],answer.rates[1],answer.rates[1])))
    errors=tuple(map(F,(answer.rate_error_bounds[0],answer.rate_error_bounds[1],answer.rate_error_bounds[1])))
    assert rates[1]!=exact_t
    for i,(rate,want,error) in enumerate(zip(rates,expected,errors)):
        assert abs(rate-want)<=error
        exact_residual=3*(rate-want)
        assert abs(F(answer.traction_residual_pa[i])-exact_residual)<=F(answer.traction_evaluation_error_pa[i])
        assert 3*error<=F(answer.traction_rate_roundoff_bound_pa[i])
        assert F(answer.traction_evaluation_error_pa[i])+3*error<=F(answer.traction_residual_error_pa[i])
    exact_power=volume*sum(3*rate*(rate-want) for rate,want in zip(rates,expected))
    roundoff_bound=volume*sum(abs(rate)*3*error for rate,error in zip(rates,errors))
    assert abs(F(answer.power_residual_w)-exact_power)<=F(answer.power_evaluation_error_w)
    assert roundoff_bound<=F(answer.power_rate_roundoff_bound_w)
    assert F(answer.power_evaluation_error_w)+roundoff_bound<=F(answer.power_residual_error_w)
    assert answer.zero_balance_enclosed


@pytest.mark.parametrize('external', [0.,50.,101.,300.])
def test_power_identity_and_residual_are_not_hidden(external):
    answer=solve(external_pressure_pa=external)
    s=answer.state
    exact=F(s.elastic_rate_w)+F(s.interface_rate_w)+F(s.dissipation_w)-F(100)*F(answer.volume_rate_m3_s)-F(answer.external_power_w)
    assert abs(exact-F(answer.power_residual_w))<=F(answer.power_residual_error_w)
    assert answer.external_power_w == pytest.approx(-external*answer.volume_rate_m3_s, rel=1e-14, abs=1e-14)
    assert s.dissipation_w>=0
    # Independent scale gate from the existing manufactured power tests.
    assert abs(answer.power_residual_w)<=1e-10
    assert max(map(abs,answer.traction_residual_pa))<=1e-10


def test_pore_pressure_opposes_compression_and_viscosity_scales_rate():
    base=solve(); pressure=solve(pore_pressure_pa=200.)
    assert all(a>b for a,b in zip(pressure.rates,base.rates))
    slower=solve(model(viscosity_pa_s=2000.))
    assert slower.rates==pytest.approx(tuple(v/2 for v in base.rates),abs=1e-15)


@pytest.mark.parametrize('changes', [dict(viscosity_pa_s=0.),dict(reference=ReferenceSlab(.02,.04,2)),dict(maximum_absolute_log_rate_per_s=1e-12)])
def test_unsupported_or_outside_rate_domain_is_rejected(changes):
    with pytest.raises(ValueError): solve(model(**changes))


@pytest.mark.parametrize('changes', [dict(pore_pressure_pa=-1),dict(external_pressure_pa=True),dict(pore_pressure_pa=float('nan')),dict(normal_stretch=.1),dict(solid_inventory_mol={'solid':1.})])
def test_invalid_state_is_rejected(changes):
    with pytest.raises(ValueError): solve(**changes)
