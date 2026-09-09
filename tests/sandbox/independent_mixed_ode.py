"""Independent analytic-fixture reference; no tested host/flux/step in RHS."""
import math
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from test_mass_storage_bridge import MO,MN,R


def reference(pair,initial,end):
    st=pair.storages[0]
    masses=np.array([MO,MN,st.water.reference.molar_mass_kg_mol])
    hB=float(st.reference.particular_h0_j_kg[1])
    # Only independently shared declared ideal-water caloric source functions.
    vapor=st.fluid_template.gas_phases['H2O']._curve
    entropy0=pair.chemical._standard_entropy
    def hs(t):return np.array([30*t,29*t,vapor.enthalpy_j_mol(t)])
    def decode(y):
        rows=y.reshape(2,7);temperature=[];pressure=[];volumes=[]
        for mA,mB,nl,nO,nN,nW,U in rows:
            ng=np.array([nO,nN,nW]);vg=.001-mA*.001-mB*.0005-nl*1.8e-5
            def energy(t):return mA*(-100+1000*(t-300))+mB*(hB-50+1200*(t-300))+nl*(75*t-300000)+ng@(hs(t)-R*t)
            t=brentq(lambda t:energy(t)-U,294,350,xtol=1e-11)
            temperature.append(t);pressure.append(ng.sum()*R*t/vg);volumes.append(vg)
        return rows,np.array(temperature),np.array(pressure),np.array(volumes)
    wet=[True,True]
    def rhs(time,y):
        rows,T,P,V=decode(y);ng=rows[:,3:6];X=ng/ng.sum(axis=1)[:,None];Y=X*masses/(X@masses)[:,None]
        tf=T.mean();pf=P.mean();xf=X.mean(axis=0);mbar=xf@masses;rho=pf*mbar/(R*tf)
        velocity=1e-13/1.8e-5*(P[0]-P[1])/.1;donor=0 if velocity>0 else 1
        star=-rho*masses/mbar*np.array([1e-5,2e-5,1.5e-5])*(X[1]-X[0])/.1
        drift=0 if star.sum()<0 else 1
        diff=.01*(star-star.sum()*Y[drift])/masses;adv=.01*rho*Y[donor]*velocity/masses
        power=.01*(T[0]-T[1])/(.05/.5+.05/.7)+diff@hs(tf)+adv@hs(T[donor])
        out=np.zeros((2,7));extent=.2*rows[:,0]*ng[:,0]/.2
        out[:,0]=-extent;out[:,1]=2*extent;out[:,3]=-extent/MO
        for i in range(2):
            if wet[i]:
                hliq=75*T[i]-300000+P[i]*1.8e-5;sliq=75*math.log(T[i]/300)+75
                mu0=hs(T[i])[2]-T[i]*entropy0(T[i])
                peq=1e5*math.exp((hliq-T[i]*sliq-mu0)/(R*T[i]))
                phase=1e-8*(peq-ng[i,2]*R*T[i]/V[i])
                out[i,2]=-phase;out[i,5]=phase
        out[0,3:6]-=diff+adv;out[1,3:6]+=diff+adv;out[:,6]=(-power,power)
        return out.ravel()
    state=np.array([[*s.solid_mass_kg,s.liquid_water_mol,*s.gas_amounts_mol,s.internal_energy_j] for s in initial]).ravel()
    now=0.;segments=[];frames=[]
    while now<end:
        events=[];cells=[]
        for i in range(2):
            if wet[i]:
                def event(t,y,index=i):return y.reshape(2,7)[index,2]
                event.terminal=True;event.direction=-1;events.append(event);cells.append(i)
        answer=solve_ivp(rhs,(now,end),state,method='DOP853',rtol=1e-12,atol=np.array([[1e-15,1e-15,1e-22,1e-15,1e-15,1e-22,1e-12]]*2).ravel(),max_step=1e-5,dense_output=True,events=events or None)
        assert answer.success
        segments.append((now,answer.t[-1],answer.sol,tuple(wet)))
        now=float(answer.t[-1]);state=answer.y[:,-1].copy()
        if now>=end:break
        selected=next(cells[k] for k,values in enumerate(answer.t_events) if len(values))
        row=state.reshape(2,7)[selected]
        row[5]+=row[2];row[2]=0. # Reference root solver's own sub-1e-22 residue.
        wet[selected]=False;frames.append((selected,now,state.copy()))
    return state,tuple(frames),tuple(segments),decode
