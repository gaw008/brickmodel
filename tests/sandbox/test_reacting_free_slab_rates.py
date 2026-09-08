from dataclasses import replace,fields
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
import pytest
from test_free_slab_rates import skeletons
from sludge_sandbox.reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy as Reacting
import sludge_sandbox.free_slab_rates as m


def wrap(base,weight=.5):return Reacting(reference_model=base,composition_offset=1.,composition_weights_per_mol=(('solid',weight),),
    model_id='q-law',version='1',classification='manufactured_test_fixture',allow_manufactured=True)

def inputs():return dict(normal_stretches=(1.1,.9),tangential_stretch=.9,pore_pressures_pa=(100.,150.),external_pressure_pa=101.,solid_inventories_mol=({'solid':.5},{'solid':2.}))


def test_unequal_q_current_viscosity_decimal_oracle():
    bases=skeletons(2);models=tuple(wrap(s) for s in bases);kw=inputs()
    out=m.solve_free_slab_rates(models,solid_inventory_regime='reacting_manufactured',**kw)
    with localcontext() as c:
        c.prec=120;t=D(.9);pe=D(101.);num=D();den=D();normal=[]
        for s,n,p,amount in zip(bases,kw['normal_stretches'],kw['pore_pressures_pa'],(.5,2.),strict=True):
            n=D(n);p=D(p);q=1+D(.5)*D(amount);v=D(s.reference_volume_m3);eta=q*D(s.viscosity_pa_s)
            theta=n.ln()+2*t.ln()
            pn=q*(D(s.bulk_modulus_pa)*theta+2*D(s.shear_modulus_pa)*(n.ln()-theta/3))/n
            pt=q*((D(s.bulk_modulus_pa)*theta+2*D(s.shear_modulus_pa)*(t.ln()-theta/3))/t+D(s.interface_energy_j_m2)*D(s.reference_interface_area_m2)*t/v)
            normal.append(n*n*((p-pe)*t*t-pn)/eta);num+=v*((p-pe)*n*t-pt);den+=v*eta
        expected=tuple(normal)+(t*t*num/den,)
        for got,bound,want in zip(out.rates,out.rate_error_bounds,expected,strict=True):assert abs(D(got)-want)<=D(bound)
    assert out.zero_balance_enclosed
    assert out.qualification.startswith('manufactured_reacting')
    assert all('solid' in s.elastic_composition_derivative_j_mol for s in out.states)


def test_q_one_and_fixed_identity_parity():
    base=skeletons(2);kw=inputs()|{'solid_inventories_mol':({'solid':1.},{'solid':1.})}
    old=m.solve_free_slab_rates(base,**kw);fixed=m.solve_free_slab_rates(base,solid_inventory_regime='fixed_solid',**kw)
    for f in fields(old):assert getattr(fixed,f.name)==getattr(old,f.name)
    result=m.solve_free_slab_rates(tuple(wrap(s,0.) for s in base),solid_inventory_regime='reacting_manufactured',**kw)
    for name in ('rates','rate_error_bounds','external_powers_w','constraint_powers_w','cell_power_residuals_w','cell_power_residual_errors_w'):
        assert getattr(result,name)==getattr(old,name)


@pytest.mark.parametrize('changes',[{'solid_inventories_mol':({'solid':0.},{'solid':2.})},{'solid_inventories_mol':({}, {'solid':2.})},{'normal_stretches':(.01,.9)}])
def test_invalid_current_inputs(changes):
    with pytest.raises(ValueError):m.solve_free_slab_rates(tuple(wrap(s) for s in skeletons(2)),solid_inventory_regime='reacting_manufactured',**(inputs()|changes))


def test_regime_mixed_and_eta_guards():
    base=skeletons(2);wrapped=tuple(wrap(s) for s in base)
    with pytest.raises(ValueError):m.solve_free_slab_rates(wrapped,**inputs())
    with pytest.raises(ValueError):m.solve_free_slab_rates((wrapped[0],base[1]),solid_inventory_regime='reacting_manufactured',**inputs())
    with pytest.raises(ValueError):m.solve_free_slab_rates(tuple(wrap(replace(s,viscosity_pa_s=0.)) for s in base),solid_inventory_regime='reacting_manufactured',**inputs())


def test_exact_weighted_viscosity_denominator_and_stable_identity():
    bases=skeletons(2)
    models=tuple(wrap(s) for s in bases)
    kw=inputs()|{'normal_stretches':(1.,1.),'tangential_stretch':1.}
    out=m.solve_free_slab_rates(models,solid_inventory_regime='reacting_manufactured',**kw)
    volumes=tuple(F(s.reference_volume_m3) for s in bases)
    denominator=sum((v*q*F(s.viscosity_pa_s) for v,q,s in zip(volumes,(F(5,4),F(2)),bases,strict=True)),F())
    numerator=sum((v*(F(p)-F(101))-q*F(s.interface_energy_j_m2)*F(s.reference_interface_area_m2)
        for v,p,q,s in zip(volumes,(100.,150.),(F(5,4),F(2)),bases,strict=True)),F())
    assert abs(F(out.rates[-1])-numerator/denominator)<=F(out.rate_error_bounds[-1])
    changed=m.solve_free_slab_rates(models,solid_inventory_regime='reacting_manufactured',**(kw|{'solid_inventories_mol':({'solid':1.},{'solid':1.})}))
    assert changed.model_identity==out.model_identity and changed.rates!=out.rates
    assert set(out.source_ids)=={v for s in models for v in s.source_ids}
