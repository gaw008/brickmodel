"""Pure analytic-liquid framework; never invokes native water EOS."""
from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_mass_wet_transport import setup as base_setup,totals
from sludge_sandbox.mass_wet_exact_stage import MixedStagePolicy,InventoryPolynomial,try_step_doubling,exact
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.mass_wet_transport import WetPair


def setup(monkeypatch):
    pair,states=base_setup(monkeypatch)
    for st in pair.storages:
        for function in (st.water.state_tp.__func__,st.water.state_tp_response.__func__):
            function.manufactured_test_fixture=True
            function.constant_volume_m3_mol=F(1.8e-5)
            function.constant_volume_temperature_domain_k=st.temperature_domain_k
            function.constant_volume_pressure_domain_pa=st.fluid_template.envelope.pressure_range_pa
    return pair,states


def fixture(pair):
    from sludge_sandbox.mass_wet_exact_stage import ManufacturedConstantLiquidFixture
    return ManufacturedConstantLiquidFixture.capture(pair,volume_m3_mol=F(1.8e-5))


def policy(**kw):
    return replace(MixedStagePolicy(1e-8,4e-7,1e-3,1e-3,1.,1e-8,1e-12,.01),**kw)


def run(pair,states,**kw):
    return try_step_doubling(pair,states,start=T(F()),end=T(F(1,1000)),policy=policy(),constant_liquid_fixture=fixture(pair),**kw)


def test_actual_coupled_trial_and_all_local_ledgers(monkeypatch):
    pair,initial=setup(monkeypatch);r=run(pair,initial)
    assert r.status=='accepted',r.reason
    assert r.evaluations_attempted==r.evaluations_completed==9
    assert len(r.steps)==len(r.panels)==3 and r.candidate_state==r.steps[-1].endpoint_state
    assert r.initial_state is initial and initial!=r.candidate_state
    for step in r.steps:
        d=dict(step.ledger.represented_integrals)
        for i,(a,b) in enumerate(zip(step.initial_state,step.endpoint_state)):
            sign=(-1,1)[i]
            assert abs(F(b.internal_energy_j)-F(a.internal_energy_j)-sign*F(d['face_energy',]))<F(1e-10)
            assert abs(F(b.liquid_water_mol)-F(a.liquid_water_mol)+F(d['phase_water',i]))<F(1e-16)
            for j in range(2):assert abs(F(b.solid_mass_kg[j])-F(a.solid_mass_kg[j])-F(d['solid',i,j]))<F(1e-17)
            for j in range(3):
                delta=F(d['chemical_gas',i,j])+sign*F(d['face_species',j])+(F(d['phase_water',i]) if j==2 else 0)
                assert abs(F(b.gas_amounts_mol[j])-F(a.gas_amounts_mol[j])-delta)<F(1e-16)
        for (k,e),(_,v),(_,q) in zip(step.ledger.exact_integrals,step.ledger.represented_integrals,step.ledger.integral_roundoff):assert F(v)-e==q
    before=totals(pair,initial);after=totals(pair,r.candidate_state)
    assert abs(after[2]-before[2])<F(1e-15) and abs(after[3]-before[3])<F(2e-10)
    assert dict(r.comparisons)['temperature_k']>0 and dict(r.comparisons)['pressure_pa']>0


def test_large_origin_exact_schedule(monkeypatch):
    pair,initial=setup(monkeypatch);h=F(1,10**8);origin=F(10**12)
    a=try_step_doubling(pair,initial,start=T(F()),end=T(h),policy=policy(),constant_liquid_fixture=fixture(pair))
    b=try_step_doubling(pair,initial,start=T(origin),end=T(origin+h),policy=policy(),constant_liquid_fixture=fixture(pair))
    assert a.status==b.status=='accepted'
    assert a.candidate_state==b.candidate_state
    assert float(origin)==float(origin+h)
    assert all(y.time.seconds-x.time.seconds==origin for x,y in zip(a.samples,b.samples))
    assert a.steps[0].ledger.exact_integrals==b.steps[0].ledger.exact_integrals


def test_rejection_is_not_commit(monkeypatch):
    pair,initial=setup(monkeypatch)
    r=try_step_doubling(pair,initial,start=T(F()),end=T(F(1,1000)),policy=policy(solid_mass_absolute_kg=1e-30),constant_liquid_fixture=fixture(pair))
    assert r.status=='rejected' and r.candidate_state is None and len(r.steps)==3
    assert r.initial_state is initial


@pytest.mark.parametrize('changes',[{'minimum_step_s':.001},{'maximum_step_s':.0001}])
def test_declared_step_domain_no_callback(monkeypatch,changes):
    pair,initial=setup(monkeypatch)
    r=try_step_doubling(pair,initial,start=T(F()),end=T(F(1,1000)),policy=policy(**changes))
    assert r.status=='failed' and r.evaluations_attempted==0


def test_budget_and_cancel_retain_uncommitted_diagnostics(monkeypatch):
    pair,initial=setup(monkeypatch)
    r=try_step_doubling(pair,initial,start=T(F()),end=T(F(1,1000)),policy=policy(maximum_evaluations=4))
    assert r.status=='resource_limit' and r.evaluations_attempted==4 and len(r.steps)==1 and r.candidate_state is None
    calls=0
    old=WetPair.evaluate
    def wrapped(self,state):
        nonlocal calls
        result=old(self,state);calls+=1;return result
    monkeypatch.setattr(WetPair,'evaluate',wrapped)
    r=run(pair,initial,cancel=lambda:calls>=3)
    assert r.status=='cancelled' and r.evaluations_completed==3 and len(r.samples)==3 and r.candidate_state is None


def test_source_change_after_actual_callback(monkeypatch):
    pair,initial=setup(monkeypatch);old=WetPair.evaluate
    def changed(self,state):
        result=old(self,state)
        object.__setattr__(self,'rate_constants_per_s',(1.,1.))
        return result
    monkeypatch.setattr(WetPair,'evaluate',changed)
    r=run(pair,initial)
    assert r.status=='failed' and 'source' in r.reason and r.evaluations_completed==1 and r.candidate_state is None


def test_exact_quadratic_interior_extremum():
    p=InventoryPolynomial('gas',0,0,F(1,100),F(-8,100),F(12,100))
    assert p.initial>0 and p.initial+p.linear+p.quadratic>0
    assert p.minimum(F(1))==(F(-1,300),F(1,3))
    assert InventoryPolynomial('liquid',0,0,F(1),F(-4),F(4)).minimum(F(1))==(F(0),F(1,2))


@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),'1'])
def test_invalid_inputs(value):
    with pytest.raises(ValueError):exact(value)

from test_mass_storage_bridge import MO,MN,R
import math

def test_independent_full_coupled_ode(monkeypatch):
    import numpy as np
    from scipy.integrate import solve_ivp
    from scipy.optimize import brentq
    pair,initial=setup(monkeypatch);st=pair.storages[0]
    masses=np.array([MO,MN,st.water.reference.molar_mass_kg_mol]);hB=float(st.reference.particular_h0_j_kg[1])
    # Shared source ideal functions, but no tested storage/phase-transfer/face/
    # conduction/integration methods in the reference RHS.
    vapor=st.fluid_template.gas_phases['H2O']._curve
    entropy0=pair.chemical._standard_entropy
    def hs(t):return np.array([30*t,29*t,vapor.enthalpy_j_mol(t)])
    def decode(y):
        rows=y.reshape(2,7);temp=[];pressure=[];volumes=[]
        for mA,mB,nl,nO,nN,nW,U in rows:
            ng=np.array([nO,nN,nW]);vg=.001-mA*.001-mB*.0005-nl*1.8e-5
            def energy(t):return mA*(-100+1000*(t-300))+mB*(hB-50+1200*(t-300))+nl*(75*t-300000)+ng@(hs(t)-R*t)
            t=brentq(lambda t:energy(t)-U,294,350,xtol=1e-11)
            temp.append(t);pressure.append(ng.sum()*R*t/vg);volumes.append(vg)
        return rows,np.array(temp),np.array(pressure),np.array(volumes)
    def rhs(t,y):
        rows,T,P,V=decode(y);ng=rows[:,3:6];X=ng/ng.sum(axis=1)[:,None];Y=X*masses/(X@masses)[:,None]
        tf=T.mean();pf=P.mean();xf=X.mean(axis=0);mbar=xf@masses;rho=pf*mbar/(R*tf)
        velocity=1e-13/1.8e-5*(P[0]-P[1])/.1;donor=0 if velocity>0 else 1
        star=-rho*masses/mbar*np.array([1e-5,2e-5,1.5e-5])*(X[1]-X[0])/.1
        drift=0 if star.sum()<0 else 1
        diff=.01*(star-star.sum()*Y[drift])/masses;adv=.01*rho*Y[donor]*velocity/masses;flux=diff+adv
        power=.01*(T[0]-T[1])/(.05/.5+.05/.7)+diff@hs(tf)+adv@hs(T[donor])
        out=np.zeros((2,7));extent=.2*rows[:,0]*ng[:,0]/.2
        out[:,0]=-extent;out[:,1]=2*extent;out[:,3]=-extent/MO
        for i in range(2):
            hliq=75*T[i]-300000+P[i]*1.8e-5;sliq=75*math.log(T[i]/300)+75
            mu0=hs(T[i])[2]-T[i]*entropy0(T[i])
            peq=1e5*math.exp((hliq-T[i]*sliq-mu0)/(R*T[i]))
            phase=1e-8*(peq-ng[i,2]*R*T[i]/V[i])
            out[i,2]=-phase;out[i,5]=phase
        out[0,3:6]-=flux;out[1,3:6]+=flux;out[:,6]=(-power,power)
        return out.ravel()
    y0=np.array([[*s.solid_mass_kg,s.liquid_water_mol,*s.gas_amounts_mol,s.internal_energy_j] for s in initial]).ravel()
    ref=solve_ivp(rhs,(0,.01),y0,method='DOP853',rtol=1e-12,atol=1e-13,dense_output=True)
    assert ref.success
    result=run(pair,initial)
    assert result.status=='accepted',result.reason
    for step in result.steps:
        rows,T,P,V=decode(ref.sol(float(step.end.seconds)))
        for i,s in enumerate(step.endpoint_state):
            assert max(abs(np.array(s.solid_mass_kg)-rows[i,:2]))<1e-8
            assert abs(s.liquid_water_mol-rows[i,2])<4e-7
            assert max(abs(np.array(s.gas_amounts_mol)-rows[i,3:6]))<4e-7
            assert abs(s.internal_energy_j-rows[i,6])<1e-3
            assert abs(step.endpoint_sample.rates.cells[i].inverse.point.temperature_k-T[i])<1e-3
            assert abs(step.endpoint_sample.rates.cells[i].inverse.point.pressure_pa-P[i])<1.


def test_near_zero_predictor_rejects_without_switch(monkeypatch):
    pair,initial=setup(monkeypatch)
    tiny=replace(initial[0],liquid_water_mol=1e-15)
    tiny=replace(tiny,internal_energy_j=pair.storages[0].evaluate(tiny,305.).total_internal_energy_j)
    r=run(pair,(tiny,initial[1]))
    assert r.status=='failed' and r.reason=='negative_trial_inventory'
    assert r.evaluations_attempted==r.evaluations_completed==1 and r.candidate_state is None
    assert pair.interfaces==('existing_liquid',)*2


def test_wall_failure_and_dry_liquid_identically_zero(monkeypatch):
    import sludge_sandbox.mass_wet_exact_stage as module
    pair,initial=setup(monkeypatch);zeros=[]
    for i,s in enumerate(initial):
        z=pair.storages[i].state(s.solid_mass_kg,0.,(.2,.2,1e-8),0.)
        zeros.append(replace(z,internal_energy_j=pair.storages[i].evaluate(z,305.+5*i).total_internal_energy_j))
    dry=pair.with_depleted_cells(tuple(zeros),(0,1))
    r=run(dry,tuple(zeros))
    assert r.status=='accepted',r.reason
    assert all(p.initial==p.linear==p.quadratic==0 for panel in r.panels for p in panel.inventories if p.family=='liquid')
    counter=[0]
    def clock():counter[0]+=1;return counter[0]*.1
    monkeypatch.setattr(module.time,'monotonic',clock)
    r=try_step_doubling(pair,initial,start=T(F()),end=T(F(1,1000)),policy=policy(maximum_wall_seconds=.25))
    assert r.status=='resource_limit' and r.evaluations_completed==1 and r.candidate_state is None


def test_midpoint_failure_keeps_actual_predictor_and_cost(monkeypatch):
    pair,initial=setup(monkeypatch);old=WetPair.evaluate;counter=[0]
    def fail(self,state):
        counter[0]+=1
        if counter[0]==2:raise ValueError('synthetic_midpoint_failure')
        return old(self,state)
    monkeypatch.setattr(WetPair,'evaluate',fail)
    r=run(pair,initial)
    assert r.status=='failed' and r.reason=='synthetic_midpoint_failure'
    assert (r.evaluations_attempted,r.evaluations_completed)==(2,1)
    assert len(r.predictor_states)==1 and r.predictor_states[0][1]==T(F(1,2000))
    assert not r.steps and r.candidate_state is None and r.initial_state is initial


def test_whole_panel_touch_zero_is_not_ordinary_wet_permission(monkeypatch):
    from sludge_sandbox.mass_wet_exact_stage import Sample,build_panel,validate_positive_panel
    pair,states=setup(monkeypatch);rates=pair.evaluate(states)
    # Exact binary rational manufactured panel has positive endpoints but
    # touches zero internally: L=1/4 - t + t². No host evolution is asserted.
    states=(replace(states[0],liquid_water_mol=.25),states[1])
    start_rates=replace(rates,cells=(replace(rates.cells[0],phase_water_mol_s=1.),rates.cells[1]))
    mid_rates=replace(rates,cells=(replace(rates.cells[0],phase_water_mol_s=0.),rates.cells[1]))
    a=Sample('symbolic',T(F()),states,start_rates,pair.binding(),pair.interfaces)
    b=Sample('symbolic',T(F(1,2)),states,mid_rates,pair.binding(),pair.interfaces)
    panel=build_panel(a,b,T(F(1)))
    with pytest.raises(ValueError,match='strict_positive_liquid'):validate_positive_panel(panel)
