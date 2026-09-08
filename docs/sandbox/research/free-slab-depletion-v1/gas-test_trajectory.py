from dataclasses import replace
import math,json
from pathlib import Path
import numpy as np
from fractions import Fraction as F
from scipy.integrate import solve_ivp
from sludge_sandbox.integration import integrate
from sludge_sandbox.checkpoint import audit_integration
from sludge_sandbox.verification_case import encode
from test_dynamic_solid_storage import water,forbid_water_eos
from test_free_solid_slab import host
from test_integration import policy
from test_rigid_storage import R


def rhs(stale=False):
    def evaluate(_,y):
        ns=y[:2];t=y[2];es=y[3:5];ng=y[5:7];v0=.00014;pe=101325.;eta=1e6
        ts=[];ps=[];sn=[];st=[]
        for i,n in enumerate(ns):
            ln,lt=math.log(n),math.log(t);theta=ln+2*lt
            rec=v0*(500*theta**2+400*((ln-theta/3)**2+2*(lt-theta/3)**2))+.0015*t*t
            temp=(es[i]-rec+200004.)/(10+ng[i]*(30-R));ts.append(temp)
            ps.append(ng[i]*R*temp/(v0*n*t*t-4e-5))
            sn.append((1000*theta+800*(ln-theta/3))/n)
            st.append((1000*theta+800*(lt-theta/3))/t+.0015*t/v0)
        nd=[n*n/eta*((p-pe)*t*t-s) for n,p,s in zip(ns,ps,sn)]
        td=t*t*sum(v0*((p-pe)*n*t-s) for n,p,s in zip(ns,ps,st))/(2*v0*eta)
        widths=[.01*n for n in ns];area=.014*t*t
        # Negative control only stales gas transport geometry, leaving mechanics and heat correct.
        dl,dr=(.005,.005) if stale else (widths[0]/2,widths[1]/2)
        ga=.014 if stale else area
        gp=[ng[i]*R*ts[i]/(.00014-4e-5) for i in range(2)] if stale else ps
        w=dr/(dl+dr);pf=w*gp[0]+(1-w)*gp[1];tf=w*ts[0]+(1-w)*ts[1]
        mobility=(dl+dr)/(dl/(1e-15/1e-5)+dr/(3e-15/2e-5))
        velocity=mobility*(gp[0]-gp[1])/(dl+dr)
        gas=ga*pf/(R*tf)*velocity
        carried=gas*30*ts[0 if gas>0 else 1]
        heat=.2*area*(ts[0]-ts[1])/(.5*sum(widths))
        ed=[]
        for i,n in enumerate(ns):
            vd=v0*(t*t*nd[i]+2*n*t*td)
            reaction=st[i]+eta*td/(t*t)-(ps[i]-pe)*n*t
            ed.append((-1 if i==0 else 1)*(heat+carried)-pe*vd+2*v0*reaction*td)
        return nd+[td]+ed+[-gas,gas]
    return evaluate


def test_dry_gas_trajectory(water):
    old=host(water);tr=replace(old.base_model.transport,permeability_m2=(1e-15,3e-15),viscosity_pa_s=(1e-5,2e-5))
    op=replace(old,base_model=replace(old.base_model,transport=tr),external_pressure_pa=101325.)
    initial=op.state_from_temperatures([[0.,.01,2.],[0.,.008,2.]],[300.,301.],normal_stretches=(1.,1.),tangential_stretch=1.)
    y0=np.r_[initial.mechanical_stretches,initial.internal_energy_j,initial.amounts_mol[:,1]]
    good=solve_ivp(rhs(),(0.,.1),y0,method='DOP853',rtol=1e-12,atol=1e-13)
    bad=solve_ivp(rhs(True),(0.,.1),y0,method='DOP853',rtol=1e-12,atol=1e-13)
    assert good.success and bad.success
    negative=float(np.max(np.abs(good.y[5:,-1]-bad.y[5:,-1])));assert negative>1e-9
    runs=[];errors=[];maxwork=F()
    for cap in (.00625,.003125):
        p=policy(initial_step_s=cap,maximum_step_s=cap,relative_tolerance=1e-9,amount_absolute_tolerance_mol=1e-11,
            energy_absolute_tolerance_j=1e-6,stretch_absolute_tolerance=1e-9,stretch_scale=1.)
        out=integrate(initial,op,start_s=0.,end_s=.1,policy=p);runs.append(encode(out))
        Path(__file__).with_name('results.json').write_text(json.dumps(runs,indent=2))
        assert out.status=='completed',out.reason
        end=out.states[-1];ev=[float(np.max(np.abs(end.mechanical_stretches-good.y[:3,-1]))),float(np.max(np.abs(end.internal_energy_j-good.y[3:5,-1]))),float(np.max(np.abs(end.amounts_mol[:,1]-good.y[5:,-1])))]
        assert ev[0]<2e-7 and ev[1]<2e-6 and ev[2]<1e-9;errors.append(ev)
        for state in out.states:
            assert np.array_equal(state.amounts_mol[:,[0,2]],initial.amounts_mol[:,[0,2]])
            assert abs(sum(map(F,map(float,state.amounts_mol[:,1])),F())-F(.01)-F(.008))<F(1e-11)
            n0,n1,t=map(F,map(float,state.mechanical_stretches));de=sum((F(float(a))-F(float(b)) for a,b in zip(state.internal_energy_j,initial.internal_energy_j)),F())
            residual=abs(de+101325*F(.00014)*((n0+n1)*t*t-2));assert residual<F(4e-6);maxwork=max(maxwork,residual)
        audit_integration(encode(out),p,start_s=0.,end_s=.1)
    assert len(runs[1]['steps'])>len(runs[0]['steps'])
    for key,tol in [('mechanical_stretches',2e-7),('internal_energy_j',2e-6),('amounts_mol',1e-9)]:
        assert np.max(np.abs(np.array(runs[0]['states'][-1][key])-np.array(runs[1]['states'][-1][key])))<tol
    print(json.dumps({'errors_stretch_energy_gas':errors,'stale_geometry_gas_error':negative,'max_global_work':float(maxwork),'steps':[len(r['steps']) for r in runs]}))
