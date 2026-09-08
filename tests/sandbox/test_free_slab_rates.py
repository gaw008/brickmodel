"""Independent reduced-slab virtual-work checks; manufactured, no EOS."""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import pytest
from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.free_slab_rates import solve_free_slab_rates
from test_free_skeleton_rates import model,solve as solve_single


def skeletons(cells=3,heterogeneous=True):
    ref=ReferenceSlab(.02,.04,cells)
    return tuple(model(reference=ref,cell_index=i,reference_interface_area_m2=.003/cells,
        fixed_solid_inventory_mol=(('solid',2./cells),),
        viscosity_pa_s=1000.*(i+1 if heterogeneous else 1)) for i in range(cells))


def solve(models=None,**changes):
    models=skeletons() if models is None else models
    values=dict(normal_stretches=(1.1,.9,1.),tangential_stretch=.9,
        pore_pressures_pa=(100.,150.,75.),external_pressure_pa=101.,
        solid_inventories_mol=tuple({'solid':2./len(models)} for _ in models))
    return solve_free_slab_rates(models,**(values|changes))


def oracle(models,normal,t,p,pe):
    with localcontext() as ctx:
        ctx.prec=160
        t=D.from_float(t);pe=D.from_float(pe)
        drives=[];normals=[];den=D(0)
        for s,n,p in zip(models,normal,p,strict=True):
            n=D.from_float(n);p=D.from_float(p);v=D.from_float(s.reference_volume_m3)
            k=D.from_float(s.bulk_modulus_pa);g=D.from_float(s.shear_modulus_pa)
            eta=D.from_float(s.viscosity_pa_s)
            theta=n.ln()+2*t.ln()
            pn=(k*theta+2*g*(n.ln()-theta/3))/n
            pt=(k*theta+2*g*(t.ln()-theta/3))/t+D.from_float(s.interface_energy_j_m2)*D.from_float(s.reference_interface_area_m2)*t/v
            normals.append(n*n*((p-pe)*t*t-pn)/eta)
            drives.append(v*((p-pe)*n*t-pt));den+=v*eta
        return tuple(normals)+(t*t*sum(drives)/den,)


def test_global_common_rate_matches_independent_decimal_energy_gradient():
    models=skeletons();out=solve(models)
    expected=oracle(models,(1.1,.9,1.),.9,(100.,150.,75.),101.)
    for actual,bound,want in zip(out.rates,out.rate_error_bounds,expected,strict=True):
        assert abs(D.from_float(actual)-want)<=D.from_float(bound)
    assert out.zero_balance_enclosed
    assert len({s.tangential_rate_per_s for s in out.states})==1
    assert all(s.tangential_rate_per_s==out.rates[-1] for s in out.states)


def test_local_constraint_work_is_nonzero_but_global_sum_is_zero_enclosed():
    models=skeletons();out=solve(models)
    assert min(out.constraint_powers_w)<0<max(out.constraint_powers_w)
    assert max(map(abs,out.constraint_powers_w))>1e-6
    total=sum(map(F,out.constraint_powers_w),F())
    assert abs(total-F(out.constraint_power_sum_w))<=F(out.constraint_power_sum_error_w)
    assert abs(F(out.constraint_power_sum_w))<=F(out.constraint_power_sum_error_w)
    for i,s in enumerate(out.states):
        actual=F(s.elastic_rate_w)+F(s.interface_rate_w)+F(s.dissipation_w)-F(out.pore_pressures_pa[i])*F(out.volume_rates_m3_s[i])-F(out.external_powers_w[i])-F(out.constraint_powers_w[i])
        assert abs(actual-F(out.cell_power_residuals_w[i]))<=F(out.cell_power_residual_errors_w[i])
        assert abs(F(out.cell_power_residuals_w[i]))<=F(out.cell_power_residual_errors_w[i])
        # Omitting cell constraint power is observably wrong despite global cancellation.
        wrong=actual+F(out.constraint_powers_w[i])
        assert abs(wrong)>F(1e-6)
    assert abs(F(out.global_power_residual_w))<=F(out.global_power_residual_error_w)


def test_independent_final_traction_and_local_constraint_power():
    models=skeletons();out=solve(models);t=F(.9);tdot=F(out.rates[-1])
    weighted=F()
    for i,(model,state,n,p) in enumerate(zip(models,out.states,(1.1,.9,1.),(100.,150.,75.),strict=True)):
        n=F(n);v=F(model.reference_volume_m3)
        r=sum(F(getattr(state,key)[1]) for key in ('elastic_piola_pa','interface_piola_pa','viscous_piola_pa'))-(F(p)-F(101.))*n*t
        weighted+=v*r
        assert abs(r-F(out.tangential_constraint_piola_pa[i]))<=F(out.tangential_constraint_errors_pa[i])
        want=2*v*r*tdot
        assert abs(want-F(out.constraint_powers_w[i]))<=F(out.constraint_power_errors_w[i])
    assert abs(weighted-F(out.weighted_tangential_residual_j))<=F(out.weighted_tangential_residual_error_j)
    assert abs(weighted)<=F(out.weighted_tangential_residual_error_j)


@pytest.mark.parametrize('cells',[1,2,4])
def test_homogeneous_partition_reduces_to_original_single_cell(cells):
    models=skeletons(cells,False)
    out=solve(models,normal_stretches=(1.1,)*cells,pore_pressures_pa=(100.,)*cells)
    old=solve_single()
    assert out.rates[:-1]==pytest.approx((old.rates[0],)*cells,rel=0,abs=1e-14)
    assert out.rates[-1]==pytest.approx(old.rates[1],rel=0,abs=1e-14)
    assert sum(out.external_powers_w)==pytest.approx(old.external_power_w,rel=0,abs=1e-13)
    assert max(map(abs,out.constraint_powers_w))<1e-12


def test_common_tangent_cannot_be_replaced_by_each_cells_free_rate():
    models=skeletons();out=solve(models)
    independently_free=[]
    for i,m in enumerate(models):
        ref=ReferenceSlab(m.reference.half_thickness_m/3,m.reference.reference_area_m2,1)
        local=replace(m,reference=ref,cell_index=0)
        independently_free.append(solve_single(local,normal_stretch=(1.1,.9,1.)[i],
            tangential_stretch=.9,pore_pressure_pa=(100.,150.,75.)[i],
            solid_inventory_mol={'solid':2./3}).rates[1])
    assert max(independently_free)-min(independently_free)>1e-3
    assert min(independently_free)<out.rates[-1]<max(independently_free)


@pytest.mark.parametrize('changes',[
    {'normal_stretches':(1.,1.)},{'normal_stretches':(True,1.,1.)},
    {'pore_pressures_pa':(0.,-1.,0.)},{'external_pressure_pa':True},
    {'solid_inventories_mol':({'solid':1.},)*3},{'tangential_stretch':.1}])
def test_invalid_state_refused(changes):
    with pytest.raises(ValueError):solve(**changes)


@pytest.mark.parametrize('change',['order','reference','zero_viscosity','rate_domain'])
def test_invalid_model_and_rate_domain_refused(change):
    m=skeletons()
    if change=='order':m=(m[1],m[0],m[2])
    if change=='reference':m=(replace(m[0],reference=ReferenceSlab(.03,.04,3)),)+m[1:]
    if change=='zero_viscosity':m=(replace(m[0],viscosity_pa_s=0.),)+m[1:]
    if change=='rate_domain':m=(replace(m[0],maximum_absolute_log_rate_per_s=1e-12),)+m[1:]
    with pytest.raises(ValueError):solve(m)


def test_constraint_exchange_has_a_separate_total_energy_component():
    from sludge_sandbox.integration import Rates
    rates=Rates([[0.],[0.],[0.]],[0.,0.,0.],[[0.],[0.]],[3.,-1.],
        {'external_traction':[1.,1.],'mechanical_constraint':[2.,-2.],'body':[0.,0.]},
        mechanical_rates_per_s=[.1,.2,.3])
    assert list(rates.cell_power_w)==[3.,-1.]
    assert sum(rates.cell_power_components_w['mechanical_constraint'])==0
    with pytest.raises(ValueError,match='invalid_component_work_keys'):
        Rates([[0.],[0.]],[0.,0.],[[0.]],[0.],
              {'mechanical_constraint':[0.],'dissipation':[0.]})


def test_reactions_exist_when_common_tangent_power_is_exactly_zero():
    reference=ReferenceSlab(.125,.125,2)
    models=tuple(replace(s,reference=reference,reference_interface_area_m2=.03125)
                 for s in skeletons(2,False))
    out=solve(models,normal_stretches=(1.,1.),tangential_stretch=1.,
              pore_pressures_pa=(1.,3.),external_pressure_pa=0.)
    assert out.rates[-1]==0.
    assert out.tangential_constraint_piola_pa==(1.,-1.)
    assert out.constraint_powers_w==(0.,0.) and out.zero_balance_enclosed


def test_reindexed_permutation_preserves_physical_solution():
    original=skeletons();first=solve(original);order=(2,0,1)
    moved=tuple(replace(original[j],cell_index=i) for i,j in enumerate(order))
    second=solve(moved,normal_stretches=tuple((1.1,.9,1.)[j] for j in order),
                 pore_pressures_pa=tuple((100.,150.,75.)[j] for j in order))
    assert second.rates[:-1]==tuple(first.rates[j] for j in order)
    assert second.rates[-1]==first.rates[-1]
    assert second.constraint_powers_w==tuple(first.constraint_powers_w[j] for j in order)
