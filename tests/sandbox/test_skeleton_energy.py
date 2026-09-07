"""Pre-implementation gates: gradient abs 2e-5 Pa, powers 1e-10 W; no EOS."""
import sys
from dataclasses import replace, FrozenInstanceError
from decimal import Decimal, localcontext
import math
import pytest
from sludge_sandbox.geometry import ReferenceSlab

from sludge_sandbox import skeleton_energy as m


def model(**changes):
    args=dict(reference=ReferenceSlab(.02,.04,2),cell_index=0,
        fixed_solid_inventory_mol=(('fixture_solid',2.),),solid_provider_identity=('fixture-solid','v1','a'*64),
        bulk_modulus_pa=1000.,shear_modulus_pa=400.,viscosity_pa_s=3.,
        interface_energy_j_m2=.5,reference_interface_area_m2=.003,
        stretch_range=(.5,2.),maximum_absolute_log_rate_per_s=2.,
        model_id='manufactured-log-skeleton',version='1',source_ids=('manufactured-oracle',),
        classification='manufactured_test_fixture',allow_manufactured=True)
    return m.DiagonalSkeletonEnergy(**(args|changes))


def evaluate(p=None,n=1.1,t=.9,nr=.03,tr=-.02):
    return (p or model()).evaluate(normal_stretch=n,tangential_stretch=t,
        normal_rate_per_s=nr,tangential_rate_per_s=tr,solid_inventory_mol={'fixture_solid':2.})


def test_independent_potential_gradient_and_power():
    p=model();s=evaluate(p);v=p.reference_volume_m3
    d=1e-6
    for i in (0,1):
        plus=evaluate(p,n=1.1+(d if i==0 else 0),t=.9+(d if i==1 else 0))
        minus=evaluate(p,n=1.1-(d if i==0 else 0),t=.9-(d if i==1 else 0))
        factor=1 if i==0 else 2
        assert (plus.elastic_energy_j-minus.elastic_energy_j)/(2*d*v*factor)==pytest.approx(s.elastic_piola_pa[i],abs=2e-5,rel=0)
        assert (plus.interface_energy_j-minus.interface_energy_j)/(2*d*v*factor)==pytest.approx(s.interface_piola_pa[i],abs=2e-5,rel=0)
    rates=(.03,-.02,-.02)
    for name,rate in [('elastic',s.elastic_rate_w),('interface',s.interface_rate_w),('viscous',s.dissipation_w)]:
        assert v*sum(a*b for a,b in zip(getattr(s,name+'_piola_pa'),rates))==pytest.approx(rate,abs=1e-10,rel=0)
    assert s.dissipation_w>=0
    assert 2*s.rayleigh_potential_w==pytest.approx(s.dissipation_w,abs=1e-14,rel=0)


def test_isochoric_independent_analytic_values():
    a=.12;adot=.04;p=model();s=evaluate(p,n=math.exp(a),t=math.exp(-a/2),nr=adot*math.exp(a),tr=-adot/2*math.exp(-a/2))
    assert s.elastic_energy_j==pytest.approx(1.5*400*p.reference_volume_m3*a*a,abs=1e-14,rel=0)
    assert s.interface_energy_j==pytest.approx(.5*.003*math.exp(-a),abs=1e-14,rel=0)
    assert s.dissipation_w==pytest.approx(1.5*3*p.reference_volume_m3*adot*adot,abs=1e-14,rel=0)


def test_rest_and_identity_immutability():
    p=model();s=evaluate(p,n=1,t=1,nr=0,tr=0)
    assert s.elastic_energy_j==s.elastic_rate_w==s.interface_rate_w==s.dissipation_w==0
    assert p.identity!=replace(p,version='2').identity
    with pytest.raises(FrozenInstanceError):s.elastic_energy_j=1
    with pytest.raises(TypeError):s.numerical_error_bounds['elastic_energy_j']=1
    with pytest.raises(m.SkeletonEnergyError):p.evaluate(normal_stretch=1,tangential_stretch=1,normal_rate_per_s=0,tangential_rate_per_s=0,solid_inventory_mol={'fixture_solid':1.})


@pytest.mark.parametrize('field,value',[('bulk_modulus_pa',0),('shear_modulus_pa',True),('viscosity_pa_s',-1),('interface_energy_j_m2',float('nan')),('reference_interface_area_m2',0),('allow_manufactured',False),('solid_provider_identity',()),('stretch_range',(0,2)),('classification','derived_from_evidence')])
def test_invalid_configuration(field,value):
    with pytest.raises(m.SkeletonEnergyError):model(**{field:value})


@pytest.mark.parametrize('kw',[{'n':0},{'n':float('inf')},{'tr':float('nan')},{'nr':5},{'t':.49}])
def test_domain(kw):
    with pytest.raises(m.SkeletonEnergyError):evaluate(**kw)


def test_numerical_enclosure_against_independent_high_precision_formula():
    p=model();s=evaluate(p)
    with localcontext() as ctx:
        ctx.prec=160
        n,t=Decimal.from_float(1.1),Decimal.from_float(.9)
        x,y=n.ln(),t.ln();theta=x+2*y;dev=(x-theta/3,y-theta/3,y-theta/3)
        v=Decimal.from_float(p.reference_volume_m3)
        expected=v*(Decimal(1000)*theta*theta/2+Decimal(400)*sum(z*z for z in dev))
        error=abs(Decimal.from_float(s.elastic_energy_j)-expected)
        assert error<=Decimal.from_float(s.numerical_error_bounds['elastic_energy_j'])


def test_extreme_output_is_explicit_failure():
    p=model(bulk_modulus_pa=sys.float_info.max,shear_modulus_pa=sys.float_info.max)
    with pytest.raises(m.SkeletonEnergyError):evaluate(p,n=2,t=2)


def test_all_fields_enclosed_and_decimal_global_context_cannot_change_results():
    p=model();original=evaluate(p)
    with localcontext() as ctx:
        ctx.prec=3
        assert evaluate(p)==original
    with localcontext() as ctx:
        ctx.prec=160
        d=Decimal.from_float
        for n,t,nr,tr in ((.51,1.99,.01,-.1),(1.00001,.99999,-.03,.02),(.8,.7,0.,0.)):
            s=evaluate(p,n,t,nr,tr)
            v=d(p.reference_volume_m3);ls=(d(n),d(t),d(t));rs=(d(nr),d(tr),d(tr))
            ell=tuple(x.ln() for x in ls);theta=sum(ell);dev=tuple(x-theta/3 for x in ell)
            pe=tuple((1000*theta+800*x)/l for x,l in zip(dev,ls))
            ga=d(.5)*d(.003)
            ps=(Decimal(0),ga*ls[2]/v,ga*ls[1]/v)
            pv=tuple(3*r/l/l for r,l in zip(rs,ls))
            diss=3*v*sum((r/l)**2 for r,l in zip(rs,ls))
            expected=dict(elastic_energy_j=v*(500*theta**2+400*sum(x*x for x in dev)),interface_energy_j=ga*ls[1]*ls[2],elastic_piola_pa=pe,interface_piola_pa=ps,viscous_piola_pa=pv,elastic_rate_w=v*sum(x*r for x,r in zip(pe,rs)),interface_rate_w=v*sum(x*r for x,r in zip(ps,rs)),dissipation_w=diss,rayleigh_potential_w=diss/2)
            for key,target in expected.items():
                targets=target if isinstance(target,tuple) else (target,)
                actual=getattr(s,key);actual=actual if isinstance(actual,tuple) else (actual,)
                err=s.numerical_error_bounds[key];err=err if isinstance(err,tuple) else (err,)
                for x,y,e in zip(actual,targets,err):
                    assert abs(d(x)-y)<=d(e),key


def test_identity_includes_parameters_geometry_inventory_and_interval_policy():
    p=model()
    for other in (replace(p,bulk_modulus_pa=1001),replace(p,reference=ReferenceSlab(.021,.04,2)),replace(p,fixed_solid_inventory_mol=(('fixture_solid',3.),)),replace(p,solid_provider_identity=('other',))):
        assert other.identity!=p.identity
    assert 'decimal80' in str(p.identity)


def test_missing_parameters_no_defaults_and_fraction_or_boolean_rejected():
    from fractions import Fraction
    with pytest.raises(TypeError):m.DiagonalSkeletonEnergy()
    with pytest.raises(m.SkeletonEnergyError):evaluate(n=Fraction(1,10**400))
    with pytest.raises(m.SkeletonEnergyError):evaluate(nr=True)


def test_unrepresentable_subnormal_formula_output_rejected():
    p=model(interface_energy_j_m2=math.nextafter(0.,1.))
    with pytest.raises(m.SkeletonEnergyError):evaluate(p)
