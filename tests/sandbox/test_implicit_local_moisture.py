"""Pure manufactured frozen ODEs; no EOS, material or long-run validation."""
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction as F
import json
import math
from pathlib import Path

import pytest

from sludge_sandbox import implicit_local_moisture as local


def coefficients(a=2,b=1,c=3,f=0,hv=-200000):
    return local.FrozenLocalMoistureCoefficients(a,b,c,f,hv,
        'manufactured:common_water_reference',('manufactured:local_coefficients',),
        'manufactured_test_fixture')


def test_independent_elimination_solution_and_shared_integrals():
    # At h=1/2, a=2,b=1,c=3,f=5, Nc0=3,Nv0=1, the independent
    # equations are 2*Nc1-Nv1/2=3, -Nc1+3*Nv1=7/2.
    x=local.backward_euler_local_moisture(3,1,F(1,2),coefficients(f=5))
    assert x.nc1_mol==F(43,22) and x.nv1_mol==F(20,11)
    assert x.phase_transfer_mol==F(23,22)
    assert x.outlet_transfer_mol==F(5,22)
    assert x.nc1_mol==x.nc0_mol-x.phase_transfer_mol
    assert x.nv1_mol==x.nv0_mol+x.phase_transfer_mol-x.outlet_transfer_mol
    assert x.outlet_enthalpy_j==x.coefficients.vapor_enthalpy_j_mol*x.outlet_transfer_mol
    assert x.energy_change_j==-x.outlet_enthalpy_j
    assert x.additional_latent_energy_j==0


@pytest.mark.parametrize('nc,nv,dt', [(0,0,0),(0,0,100),(3,1,0),(3,1,10**50)])
def test_zero_coefficients_and_zero_time_are_true_identity(nc,nv,dt):
    x=local.backward_euler_local_moisture(nc,nv,dt,coefficients(0,0,0,0))
    assert (x.nc1_mol,x.nv1_mol)==(F(nc),F(nv))
    assert x.phase_transfer_mol==x.outlet_transfer_mol==x.outlet_enthalpy_j==0


@pytest.mark.parametrize('nc,nv', [(3,1),(0,2),(2,0),(0,0)])
def test_closed_cell_reversible_exchange_preserves_total_water(nc,nv):
    x=local.backward_euler_local_moisture(nc,nv,10,coefficients(c=0))
    assert x.nc1_mol>=0 and x.nv1_mol>=0
    assert x.nc1_mol+x.nv1_mol==nc+nv
    assert x.outlet_transfer_mol==x.outlet_enthalpy_j==0
    if nc==0 and nv:
        assert x.phase_transfer_mol<0 and x.nc1_mol>0
    if nv==0 and nc:
        assert x.phase_transfer_mol>0 and x.nv1_mol>0


def test_humid_reservoir_allows_signed_inflow_and_rewetting():
    x=local.backward_euler_local_moisture(0,0,F(1,2),coefficients(f=5,hv=100000))
    assert x.nc1_mol>0 and x.nv1_mol>0
    assert x.phase_transfer_mol<0 and x.outlet_transfer_mol<0
    assert x.outlet_enthalpy_j<0 and x.energy_change_j>0
    assert x.nc1_mol+x.nv1_mol==-x.outlet_transfer_mol


def test_degenerate_one_way_and_forcing_systems_do_not_invert_A():
    x=local.backward_euler_local_moisture(3,1,2,coefficients(0,0,4,5))
    assert x.nc1_mol==3 and x.nv1_mol==F(11,9)
    assert x.phase_transfer_mol==0 and x.outlet_transfer_mol==F(-2,9)
    y=local.backward_euler_local_moisture(3,1,2,coefficients(0,0,0,5))
    assert y.nc1_mol==3 and y.nv1_mol==11
    assert y.outlet_transfer_mol==-10


@pytest.mark.parametrize('dt', [F(1,10**20),F(1,100),F(100),F(10**200)])
def test_vacuum_monotonicity_and_strict_finite_time_positive_remainder(dt):
    x=local.backward_euler_local_moisture(3,1,dt,coefficients())
    assert x.nc1_mol>0 and x.nv1_mol>0
    assert 0<x.outlet_transfer_mol<4
    assert x.nc1_mol+x.nv1_mol==4-x.outlet_transfer_mol


def test_common_enthalpy_reference_shift_preserves_water_and_energy_bookkeeping():
    initial_u=F(12345)
    coeff=coefficients(f=5)
    shift=F(987654321,17)
    x=local.backward_euler_local_moisture(F(1,3),F(2,7),F(3,11),coeff)
    y=local.backward_euler_local_moisture(F(1,3),F(2,7),F(3,11),
        replace(coeff,vapor_enthalpy_j_mol=coeff.vapor_enthalpy_j_mol+shift,
                energy_reference_id='manufactured:shifted_common_water_reference'))
    assert (x.nc1_mol,x.nv1_mol,x.phase_transfer_mol,x.outlet_transfer_mol)==(
            y.nc1_mol,y.nv1_mol,y.phase_transfer_mol,y.outlet_transfer_mol)
    assert y.outlet_enthalpy_j==x.outlet_enthalpy_j+shift*x.outlet_transfer_mol
    shifted_u0=initial_u+shift*(x.nc0_mol+x.nv0_mol)
    assert shifted_u0+y.energy_change_j==initial_u+x.energy_change_j+shift*(x.nc1_mol+x.nv1_mol)


def test_projection_preserves_independent_stock_and_shared_transfer_roundoff():
    x=local.backward_euler_local_moisture(F(1,3),F(2,7),F(3,11),coefficients(f=5))
    p=x.project()
    q={v.name:v for v in p.projections}
    assert p.step_identity==x.identity
    for name,v in q.items():
        assert v.binary64==float(v.exact)
        assert v.signed_roundoff==F(v.binary64)-v.exact
        assert v.absolute_error==abs(v.signed_roundoff)
    assert p.condensed_balance_roundoff_mol==q['nc1_mol'].signed_roundoff+q['phase_transfer_mol'].signed_roundoff
    assert p.vapor_balance_roundoff_mol==q['nv1_mol'].signed_roundoff-q['phase_transfer_mol'].signed_roundoff+q['outlet_transfer_mol'].signed_roundoff
    assert p.carried_enthalpy_roundoff_j==q['outlet_enthalpy_j'].signed_roundoff-x.coefficients.vapor_enthalpy_j_mol*q['outlet_transfer_mol'].signed_roundoff
    assert not p.full_host_budget_verified and not p.source_state_binding_verified
    json.dumps(p.to_record(),allow_nan=False)


def test_exact_extreme_step_survives_rejected_float_projection():
    x=local.backward_euler_local_moisture(3,1,F(10**200),coefficients(10**200,10**200,10**200))
    assert x.nc1_mol>0 and x.nv1_mol>0 and x.outlet_transfer_mol<4
    with pytest.raises(local.ImplicitMoistureError,match='underflow'):
        x.project()
    # Exact result and complete shared integrals remain available after failure.
    assert x.nc1_mol+x.nv1_mol==4-x.outlet_transfer_mol
    json.dumps(x.to_record(),allow_nan=False)
    y=local.backward_euler_local_moisture(0,0,F(10**200),coefficients(0,0,0,10**200))
    with pytest.raises(local.ImplicitMoistureError,match='overflow'):
        y.project()


@pytest.mark.parametrize('field,value', [('a_s_inv',-1),('b_s_inv',None),('c_s_inv',math.nan),
    ('forcing_mol_s',math.inf),('vapor_enthalpy_j_mol',None),('a_s_inv',True),
    ('energy_reference_id',''),('source_ids',()),('input_classification','measured_public_data')])
def test_bad_frozen_input_is_rejected(field,value):
    with pytest.raises(local.ImplicitMoistureError):
        replace(coefficients(),**{field:value})


@pytest.mark.parametrize('nc,nv,dt', [(-1,1,1),(1,-1,1),(1,1,-1),
                                    (True,1,1),(1,math.nan,1),(1,1,None)])
def test_bad_state_or_duration_has_no_silent_default(nc,nv,dt):
    with pytest.raises(local.ImplicitMoistureError):
        local.backward_euler_local_moisture(nc,nv,dt,coefficients())


def test_fraction_and_decimal_inputs_are_not_first_projected_to_float():
    n=F(1,3)+F(1,10**80)
    x=local.backward_euler_local_moisture(n,Decimal('.1'),Decimal('.2'),coefficients())
    assert x.nc0_mol==n and x.nv0_mol==F(1,10) and x.duration_s==F(1,5)
    assert x.nc0_mol!=F(float(n))


def analytic_solution(t):
    # Independent matrix exponential for A=[[-2,1],[2,-4]], eigenvalues
    # -3+-sqrt(3), forced equilibrium (5/6,5/3). No BE formulas are reused.
    steady=(5/6,5/3)
    y=(3-steady[0],1-steady[1])
    z=(y[0]+y[1],2*y[0]-y[1])  # (A+3I)y
    e,c,s=math.exp(-3*t),math.cosh(math.sqrt(3)*t),math.sinh(math.sqrt(3)*t)/math.sqrt(3)
    return tuple(steady[i]+e*(c*y[i]+s*z[i]) for i in (0,1))


def test_first_order_against_independent_forced_matrix_exponential(tmp_path):
    exact=analytic_solution(1.)
    records=[]
    for n in (8,16,32,64):
        nc,nv=F(3),F(1)
        phase=outlet=energy=F(0)
        for _ in range(n):
            x=local.backward_euler_local_moisture(nc,nv,F(1,n),coefficients(f=5))
            nc,nv=x.nc1_mol,x.nv1_mol
            phase+=x.phase_transfer_mol
            outlet+=x.outlet_transfer_mol
            energy+=x.outlet_enthalpy_j
        assert nc==3-phase and nv==1+phase-outlet
        assert energy==coefficients().vapor_enthalpy_j_mol*outlet
        error=max(abs(float(nc)-exact[0]),abs(float(nv)-exact[1]))
        records.append({'steps':n,'duration_s':1.,'nc1':float(nc),'nv1':float(nv),'max_inventory_error':error,
                        'analytic_nc1':exact[0],'analytic_nv1':exact[1]})
    ratios=[a['max_inventory_error']/b['max_inventory_error'] for a,b in zip(records,records[1:])]
    assert all(1.7<ratio<2.1 for ratio in ratios)
    assert records[-1]['max_inventory_error']>1e-8  # Not an exact exponential method.
    (tmp_path/'FIRST_ORDER.json').write_text(json.dumps({'cases':records,'refinement_ratios':ratios},indent=2)+'\n')


def test_provenance_separates_frozen_step_exactness_from_real_ode_and_source_truth():
    x=local.backward_euler_local_moisture(3,1,F(1,10),coefficients())
    r=x.to_record()
    assert r['numerical_policy']['formal_order']==1
    assert r['numerical_policy']['exact_frozen_ode_solution'] is False
    assert r['source_state_binding_verified'] is False and r['material_qualified'] is False
    assert r['frozen_coefficient_model_error'] is None and r['time_discretization_error'] is None
    r['coefficients']['source_ids'].clear()
    assert x.to_record()['coefficients']['source_ids']
    assert x.identity!=local.backward_euler_local_moisture(3,1,F(1,11),coefficients()).identity
