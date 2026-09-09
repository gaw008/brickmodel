"""Analytic-liquid seam only; actual storage/pressure/gas/chemical framework."""
from dataclasses import replace
from fractions import Fraction as F
import math
import pytest
from test_mass_wet_storage import setup as storage_setup
from test_mass_storage_bridge import REPOSITORY,MO,MN,R
from sludge_sandbox.mass_wet_transport import WetPair,WetFace,integrate_wet_pair
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.water_properties import WaterProperties
from sludge_sandbox.phase_storage import InversePolicy


def setup(monkeypatch):
    st,initial,calls=storage_setup(monkeypatch)
    old=WaterProperties.state_tp
    def manufactured_liquid(w,t,p,*,phase):
        raw=old(w,t,p,phase=phase)
        # Test-only adapter supplies a declared analytic liquid to the strict
        # chemical framework. No real-fluid thermodynamic evidence is claimed.
        entropy=(75*math.log(t/300)+75)/w.reference.molar_mass_kg_mol
        return replace(raw,native_entropy_j_kg_k=entropy,method_id='iapws95_real_fluid_helmholtz')
    monkeypatch.setattr(WaterProperties,'state_tp',manufactured_liquid)
    chemical=WaterChemicalPotential(REPOSITORY/'data/sandbox/water')
    face=WetFace(.01,(.05,.05),(.5,.7),(1e-5,2e-5,1.5e-5),1e-13,1.8e-5,('manufactured-wet-face',))
    pair=WetPair((st,st),(InversePolicy(1e-6,1e-6,100),)*2,chemical,(.2,.2),(.2,.2),(1e-8,1e-8),('manufactured-reaction-phase-coefficients',),face)
    initial=replace(initial,gas_amounts_mol=(.2,.2,1e-8))
    a=replace(initial,internal_energy_j=st.evaluate(initial,305.).total_internal_energy_j)
    b=st.state((.007,.002),.18,(.08,.25,.07),0.)
    b=replace(b,internal_energy_j=st.evaluate(b,310.).total_internal_energy_j)
    return pair,(a,b)


def totals(pair,states):
    st=pair.storages[0];net=st.reference.network;out=[F() for _ in net.elements];mass=F();water=F()
    mw=F(st.water.reference.molar_mass_kg_mol)
    for s in states:
        values=[*map(F,s.solid_mass_kg),*(F(n)*F(st.fluid_template.gas_phases[k].molar_mass_kg_mol) for k,n in zip(st.gas_ids,s.gas_amounts_mol))]
        values[-1]+=F(s.liquid_water_mol)*mw;mass+=sum(values)
        for v,c in zip(values,net.components):
            for i,w in enumerate(c.element_mass_fractions):out[i]+=v*w
        water+=F(s.liquid_water_mol)+F(s.gas_amounts_mol[2])
    return tuple(out),mass,water,sum(F(s.internal_energy_j) for s in states)


def test_positive_liquid_coupled_prefixes(monkeypatch):
    pair,initial=setup(monkeypatch);original=totals(pair,initial)
    observation=pair.evaluate(initial)
    assert observation.cells[0].phase_water_mol_s>0 and observation.cells[1].phase_water_mol_s<0
    for count in (4,8):
        run=integrate_wet_pair(pair,initial,duration_s=.01,steps=count)
        assert run.status=='completed',run.reason
        cs=[[F(),F()] for _ in range(2)];cg=[[F(),F(),F()] for _ in range(2)];cl=[F(),F()];ce=[F(),F()]
        for states,obs,l in zip(run.states[1:],run.observations,run.ledgers):
            el,m,w,e=totals(pair,states)
            assert max(abs(a-b) for a,b in zip(el,original[0]))<F(2e-15)
            assert abs(m-original[1])<F(2e-15) and abs(w-original[2])<F(2e-15)
            assert abs(e-original[3])<F(2e-10)
            assert obs.conduction_w!=0 and any(v!=0 for v in obs.exchange.advective_mol_s.values())
            assert any(v!=0 for v in obs.exchange.diffusive_mol_s.values())
            assert all(c.entropy_production_w_k>=0 for c in obs.cells)
            for i,sign in enumerate((-1,1)):
                cl[i]-=F(l.phase_water_mol[i]);ce[i]+=sign*F(l.face_energy_j)
                assert abs(F(states[i].liquid_water_mol)-F(initial[i].liquid_water_mol)-cl[i])<F(1e-15)
                assert abs(F(states[i].internal_energy_j)-F(initial[i].internal_energy_j)-ce[i])<F(1e-10)
                for j in range(2):
                    cs[i][j]+=F(l.solid_kg[i][j])
                    assert abs(F(states[i].solid_mass_kg[j])-F(initial[i].solid_mass_kg[j])-cs[i][j])<F(1e-16)
                for j in range(3):
                    cg[i][j]+=F(l.chemical_gas_mol[i][j])+sign*F(l.face_mol[j])+(F(l.phase_water_mol[i]) if j==2 else 0)
                    assert abs(F(states[i].gas_amounts_mol[j])-F(initial[i].gas_amounts_mol[j])-cg[i][j])<F(1e-15)
                assert l.chemical_gas_mol[i][2]==0 and states[i].liquid_water_mol>0
            assert abs(F(l.face_energy_j)-F(l.conduction_j)-sum(map(F,l.diffusive_enthalpy_j))-sum(map(F,l.advective_enthalpy_j)))<F(1e-12)
        assert run.evaluations_attempted==run.evaluations_completed==3*count
        assert run.times_s[-1]==F(.01)


def test_zero_oxygen_and_failure_prefix(monkeypatch):
    pair,initial=setup(monkeypatch);st=pair.storages[0]
    states=[]
    for s in initial:
        p=replace(s,gas_amounts_mol=(0.,s.gas_amounts_mol[1],s.gas_amounts_mol[2]))
        states.append(replace(p,internal_energy_j=st.evaluate(p,305.).total_internal_energy_j))
    obs=pair.evaluate(tuple(states));assert all(c.extent_kg_s==0 for c in obs.cells)
    run=integrate_wet_pair(pair,initial,duration_s=10000.,steps=1)
    assert run.status=='failed' and run.states==(initial,) and not run.ledgers
    stopped=integrate_wet_pair(pair,initial,duration_s=.01,steps=4,cancel=lambda:True)
    assert stopped.status=='cancelled' and stopped.evaluations_attempted==0 and stopped.states==(initial,)


def test_source_change_and_undeclared_dry_refused(monkeypatch):
    pair,states=setup(monkeypatch)
    with pytest.raises(ValueError,match='positive_liquid_segment_only'):pair.evaluate((replace(states[0],liquid_water_mol=0.),states[1]))
    object.__setattr__(pair,'transfer_coefficients_mol_s_pa',(2e-8,1e-8))
    with pytest.raises(ValueError,match='wet_pair_source_changed'):pair.evaluate(states)


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
    for count in (4,8):
        run=integrate_wet_pair(pair,initial,duration_s=.01,steps=count);assert run.status=='completed',run.reason
        for time,states,obs in zip(run.times_s[1:],run.states[1:],run.observations):
            rows,T,P,V=decode(ref.sol(float(time)))
            for i,s in enumerate(states):
                assert max(abs(np.array(s.solid_mass_kg)-rows[i,:2]))<1e-8
                assert abs(s.liquid_water_mol-rows[i,2])<4e-7
                assert max(abs(np.array(s.gas_amounts_mol)-rows[i,3:6]))<4e-7
                assert abs(s.internal_energy_j-rows[i,6])<1e-3
                assert abs(obs.cells[i].inverse.point.temperature_k-T[i])<1e-3
                assert abs(obs.cells[i].inverse.point.pressure_pa-P[i])<1.


def test_partial_cancel_and_wall_costs(monkeypatch):
    import sludge_sandbox.mass_wet_transport as module
    pair,states=setup(monkeypatch);checks=[0]
    def cancel():
        checks[0]+=1;return checks[0]>3
    run=integrate_wet_pair(pair,states,duration_s=.01,steps=4,cancel=cancel)
    assert run.status=='cancelled' and len(run.ledgers)==1 and len(run.states)==2
    assert run.evaluations_attempted==run.evaluations_completed==3
    clock=iter((0.,.1,.2,.3,.4))
    monkeypatch.setattr(module.time,'monotonic',lambda:next(clock))
    bounded=integrate_wet_pair(pair,states,duration_s=.01,steps=4,maximum_wall_seconds=.25)
    assert bounded.status=='resource_limit' and not bounded.ledgers and bounded.states==(states,)
    assert bounded.evaluations_attempted==bounded.evaluations_completed==1


def test_nonzero_coefficients_cannot_silently_underflow(monkeypatch):
    pair,_=setup(monkeypatch)
    with pytest.raises(ValueError):replace(pair.face,diffusivities_m2_s=(F(1,10**400),2e-5,1.5e-5))
    with pytest.raises(ValueError):replace(pair,transfer_coefficients_mol_s_pa=(F(1,10**400),1e-8))


def test_chemical_class_constants_are_bound(monkeypatch):
    pair,states=setup(monkeypatch)
    monkeypatch.setattr(WaterChemicalPotential,'reference_pressure_pa',2e5)
    with pytest.raises(ValueError,match='wet_pair_source_changed'):pair.evaluate(states)
