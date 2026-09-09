from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_mass_storage_bridge import fixture,MO,MN,R
from sludge_sandbox.mass_transport_bridge import MixedPair,SharedFace,integrate_pair


def setup(monkeypatch):
    cell,a=fixture(monkeypatch)
    proto=cell.storage.state((.007,.002),(.08,.25),0.)
    b=replace(proto,internal_energy_j=cell.storage.evaluate(proto,320.).internal_energy_j)
    face=SharedFace(.01,(.05,.05),(.5,.7),(1e-5,2e-5),1e-13,1.8e-5,('manufactured-face-coefficients',))
    return MixedPair((cell,cell),face),(a,b)


def elements(states):
    return tuple(sum((F(s.solid_mass_kg[0])+F(s.solid_mass_kg[1])/2 if j==0 else F(s.solid_mass_kg[1])/2+F(s.fluid_amounts_mol[0])*F(MO) if j==1 else F(s.fluid_amounts_mol[1])*F(MN) for s in states),F()) for j in range(3))


def test_actual_two_cell_prefix_conservation(monkeypatch):
    pair,initial=setup(monkeypatch)
    runs=[integrate_pair(pair,initial,duration_s=.02,steps=n) for n in (4,8)]
    for run in runs:
        assert run.status=='completed',run.reason
        totals=elements(initial); energy=sum(F(s.internal_energy_j) for s in initial)
        cum_s=[[F(),F()],[F(),F()]];cum_n=[[F(),F()],[F(),F()]];cum_e=[F(),F()]
        for states,obs,l in zip(run.states[1:],run.observations,run.ledgers):
            assert any(abs(x)>0 for x in obs.exchange.diffusive_mol_s.values())
            assert any(abs(x)>0 for x in obs.exchange.advective_mol_s.values())
            assert obs.conduction_w!=0 and all(r.extent_kg_s>0 for r in obs.reactions)
            assert max(abs(a-b) for a,b in zip(elements(states),totals))<F(2e-16)
            assert abs(sum(F(s.internal_energy_j) for s in states)-energy)<F(2e-11)
            assert abs(F(l.face_energy_j)-F(l.conduction_j)-sum(map(F,l.diffusive_enthalpy_j))-sum(map(F,l.advective_enthalpy_j)))<F(1e-12)
            for i,sign in enumerate((-1,1)):
                cum_e[i]+=sign*F(l.face_energy_j)
                assert abs(F(states[i].internal_energy_j)-F(initial[i].internal_energy_j)-cum_e[i])<F(1e-11)
                for j in range(2):
                    cum_s[i][j]+=F(l.solid_kg[i][j]);cum_n[i][j]+=F(l.reaction_gas_mol[i][j])+sign*F(l.face_mol[j])
                    assert abs(F(states[i].solid_mass_kg[j])-F(initial[i].solid_mass_kg[j])-cum_s[i][j])<F(1e-16)
                    assert abs(F(states[i].fluid_amounts_mol[j])-F(initial[i].fluid_amounts_mol[j])-cum_n[i][j])<F(1e-15)
        assert run.times_s[-1]==F(.02)
        assert run.states[-1][0].internal_energy_j!=initial[0].internal_energy_j
    assert max(abs(a.internal_energy_j-b.internal_energy_j) for a,b in zip(runs[0].states[-1],runs[1].states[-1]))<1e-4


def test_independent_face_algebra_and_reversal(monkeypatch):
    pair,states=setup(monkeypatch);o=pair.evaluate(states)
    left,right=o.gas_states;f=pair.face
    # Independent Darcy pressure-gradient and Fourier resistance oracle.
    assert o.exchange.darcy_velocity_m_s==pytest.approx(f.permeability_m2/f.viscosity_pa_s*(left.pressure_pa-right.pressure_pa)/.1,rel=1e-14)
    assert o.conduction_w==pytest.approx(.01*(left.temperature_k-right.temperature_k)/(.05/.5+.05/.7),rel=1e-14)
    for i,k in enumerate(('O2','N2')):
        cp=(30,29)[i]
        assert o.diffusive_enthalpy_w[i]==pytest.approx(o.exchange.diffusive_mol_s[k]*cp*o.exchange.face_temperature_k,rel=1e-14)
        assert o.advective_enthalpy_w[i]==pytest.approx(o.exchange.advective_mol_s[k]*cp*left.temperature_k,rel=1e-14)
    reverse=replace(pair,face=replace(f,conductivities_w_m_k=f.conductivities_w_m_k[::-1])).evaluate(states[::-1])
    assert reverse.face_energy_w==pytest.approx(-o.face_energy_w,rel=1e-12)
    for k in ('O2','N2'):assert reverse.exchange.net_mol_s[k]==pytest.approx(-o.exchange.net_mol_s[k],rel=1e-12)


def shifted(pair,states):
    cell=pair.cells[0];st=cell.storage;phases=dict(st.fluid_template.gas_phases)
    p=phases['O2'];curve=p.caloric;seg=curve.segments[0];coef=list(seg.coefficients);coef[5]+=1.
    phases['O2']=replace(p,caloric=replace(curve,segments=(replace(seg,coefficients=tuple(coef)),)))
    net=st.reference.network
    anchors=tuple(replace(a,h0_j_kg=F(phases['O2'].evaluate(300.,100000.).enthalpy_j_mol)/F(MO)) if a.component_id=='O2' else a for a in net.anchors)
    newst=replace(st,fluid_template=replace(st.fluid_template,gas_phases=phases),reference=replace(net,anchors=anchors).solve())
    newcell=replace(cell,storage=newst)
    newstates=[]
    for state in states:
        t=st.invert(state,cell.inverse_policy).point.temperature_k
        proto=newst.state(state.solid_mass_kg,state.fluid_amounts_mol,0.)
        newstates.append(replace(proto,internal_energy_j=newst.evaluate(proto,t).internal_energy_j))
    return replace(pair,cells=(newcell,newcell)),tuple(newstates)


def test_shared_oxygen_gauge_transports_reference_energy(monkeypatch):
    pair,states=setup(monkeypatch);gp,gs=shifted(pair,states)
    a=integrate_pair(pair,states,duration_s=.02,steps=4);b=integrate_pair(gp,gs,duration_s=.02,steps=4)
    assert a.status==b.status=='completed',(a.reason,b.reason)
    for aa,bb,oa,ob in zip(a.states[1:],b.states[1:],a.observations,b.observations):
        for x,y,rx,ry in zip(aa,bb,oa.reactions,ob.reactions):
            assert x.solid_mass_kg==pytest.approx(y.solid_mass_kg,abs=2e-12)
            assert x.fluid_amounts_mol==pytest.approx(y.fluid_amounts_mol,abs=2e-11)
            assert abs(rx.inverse.point.temperature_k-ry.inverse.point.temperature_k)<1e-6
            assert abs(rx.inverse.point.pressure_pa-ry.inverse.point.pressure_pa)<1e-3
            oxygen=F(x.solid_mass_kg[1])/2+F(x.fluid_amounts_mol[0])*F(MO)
            assert abs(F(y.internal_energy_j)-F(x.internal_energy_j)-oxygen*F(1000)/F(MO))<F(1e-6)
        assert ob.face_energy_w-oa.face_energy_w==pytest.approx(1000*oa.exchange.net_mol_s['O2'],abs=1e-6)
    with pytest.raises(ValueError,match='shared_material_reference'):MixedPair((pair.cells[0],gp.cells[0]),pair.face)


def test_equilibrium_zero_oxygen_and_failure_rollback(monkeypatch):
    pair,(a,b)=setup(monkeypatch);st=pair.cells[0].storage
    proto=st.state((.01,0.),(0.,.2),0.);zero=replace(proto,internal_energy_j=st.evaluate(proto,310.).internal_energy_j)
    run=integrate_pair(pair,(zero,zero),duration_s=.01,steps=2)
    assert run.status=='completed' and run.states[-1]==(zero,zero)
    assert all(o.face_energy_w==0 and o.exchange.net_mol_s=={'O2':0.,'N2':0.} for o in run.observations)
    failed=integrate_pair(pair,(a,b),duration_s=10000.,steps=1)
    assert failed.status=='failed' and failed.states==((a,b),) and not failed.ledgers


def test_independent_coupled_ode(monkeypatch):
    import numpy as np
    from scipy.integrate import solve_ivp
    pair,initial=setup(monkeypatch)
    masses=np.array([MO,MN]);cp=np.array([30.,29.]);cv=cp-R
    hB=(-200000+30*300/MO)/2
    def decoded(y):
        rows=y.reshape(2,5);m=rows[:,:2];n=rows[:,2:4]
        capacity=m[:,0]*1000+m[:,1]*1200+n@cv
        T=(rows[:,4]-m[:,0]*(-100-300000)-m[:,1]*(hB-50-360000))/capacity
        volume=.001-m[:,0]*.001-m[:,1]*.0005
        P=n.sum(axis=1)*R*T/volume
        return rows,T,P
    def rhs(t,y):
        rows,T,P=decoded(y);n=rows[:,2:4];X=n/n.sum(axis=1)[:,None]
        Y=X*masses/(X@masses)[:,None]
        tf=T.mean();pf=P.mean();xf=X.mean(axis=0);mean=xf@masses;rho=pf/(R*tf)*mean
        velocity=1e-13/1.8e-5*(P[0]-P[1])/.1
        donor=0 if velocity>0 else 1
        star=-rho*masses/mean*np.array([1e-5,2e-5])*(X[1]-X[0])/.1
        drift=0 if star.sum()<0 else 1
        diff=.01*(star-star.sum()*Y[drift])/masses
        adv=.01*rho*Y[donor]*velocity/masses
        flux=diff+adv
        heat=.01*(T[0]-T[1])/(.05/.5+.05/.7)
        energy=heat+np.sum(diff*cp*tf)+np.sum(adv*cp*T[donor])
        rate=.2*rows[:,0]*n[:,0]/.2
        out=np.zeros((2,5));out[:,0]=-rate;out[:,1]=2*rate;out[:,2]=-rate/MO
        out[0,2:4]-=flux;out[1,2:4]+=flux;out[:,4]=(-energy,energy)
        return out.ravel()
    y0=np.array([[*s.solid_mass_kg,*s.fluid_amounts_mol,s.internal_energy_j] for s in initial]).ravel()
    ref=solve_ivp(rhs,(0,.02),y0,method='DOP853',rtol=1e-12,atol=1e-13,dense_output=True)
    assert ref.success
    errors=[]
    for count in (4,8):
        run=integrate_pair(pair,initial,duration_s=.02,steps=count);assert run.status=='completed',run.reason
        for time,states,obs in zip(run.times_s[1:],run.states[1:],run.observations):
            rows,T,P=decoded(ref.sol(float(time)))
            for i,s in enumerate(states):
                assert max(abs(np.array(s.solid_mass_kg)-rows[i,:2]))<1e-8
                assert max(abs(np.array(s.fluid_amounts_mol)-rows[i,2:4]))<4e-7
                assert abs(s.internal_energy_j-rows[i,4])<1e-3
                assert abs(obs.reactions[i].inverse.point.temperature_k-T[i])<1e-3
                assert abs(obs.reactions[i].inverse.point.pressure_pa-P[i])<1.
        errors.append(max(abs(np.array([s.internal_energy_j for s in run.states[-1]])-ref.y[:,-1].reshape(2,5)[:,4])))
    assert errors[1]<errors[0]/3


def test_invalid_and_mutated_source_refused(monkeypatch):
    pair,initial=setup(monkeypatch)
    for bad in (True,float('nan'),-1.):
        with pytest.raises(ValueError):replace(pair.face,permeability_m2=bad)
    with pytest.raises(ValueError):integrate_pair(pair,initial,duration_s=.01,steps=True)
    object.__setattr__(pair.cells[0],'rate_constant_per_s',.3)
    with pytest.raises(ValueError,match='pair_source_changed'):pair.evaluate(initial)
