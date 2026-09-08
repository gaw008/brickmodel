"""Independent manufactured A->B/current-pore/free mechanics/heat ODE."""
from fractions import Fraction as F
import json
import math
import os
from pathlib import Path
import traceback
import numpy as np
from scipy.integrate import solve_ivp
from sludge_sandbox.integration import integrate
from sludge_sandbox.checkpoint import audit_integration
from sludge_sandbox.verification_case import encode
from test_dynamic_solid_storage import water,forbid_water_eos
from test_integration import policy
from test_rigid_storage import R


def independent_rhs(*,with_constraint=True,current_viscosity=True):
    """No production state/energy/mechanics/reaction helper is called here."""
    def rhs(time,y):
        normals=y[:2];t=y[2];energies=y[3:]
        a=2*math.exp(-.1*time);b=2-a;q=1+10*b
        v0=.00014;eta=q*1e6 if current_viscosity else 1e6;pe=101325.;ng=(.01,.008)
        temperatures=[];pressures=[];sn=[];st=[]
        for i,n in enumerate(normals):
            ln,lt=math.log(n),math.log(t);theta=ln+2*lt
            reference=v0*(500*theta*theta+400*((ln-theta/3)**2+2*(lt-theta/3)**2))+.3*t*t
            temperature=(energies[i]-q*reference+100002*a+100006*b)/(5*(a+b)+ng[i]*(30-R))
            temperatures.append(temperature)
            pressures.append(ng[i]*R*temperature/(v0*n*t*t-a*2e-5-b*1e-5))
            sn.append(q*(1000*theta+800*(ln-theta/3))/n)
            st.append(q*((1000*theta+800*(lt-theta/3))/t+.3*t/v0))
        nd=[n*n/eta*((p-pe)*t*t-force) for n,p,force in zip(normals,pressures,sn,strict=True)]
        td=t*t*sum(v0*((p-pe)*n*t-force) for n,p,force in zip(normals,pressures,st,strict=True))/(2*v0*eta)
        flux=.2*(.014*t*t)*(temperatures[0]-temperatures[1])/(.005*(normals[0]+normals[1]))
        work=[]
        for i,n in enumerate(normals):
            volume_rate=v0*(t*t*nd[i]+2*n*t*td)
            reaction=st[i]+eta*td/(t*t)-(pressures[i]-pe)*n*t
            constraint=2*v0*reaction*td if with_constraint else 0.
            work.append((-flux if i==0 else flux)-pe*volume_rate+constraint)
        return nd+[td]+work
    return rhs


def initial_oracle():
    return np.array([1.,1.,1.,2*(5*305-100002)+.01*(30-R)*305+.3,
        2*(5*306-100002)+.008*(30-R)*306+.3])


def test_reacting_free_trajectory_explicit_in_domain(water,tmp_path):
    # Helper import delayed so the independent oracle can run before host exists.
    from test_reacting_free_solid_slab import reacting_host
    artifact=Path(os.environ.get('BRICK_REACTING_FREE_TRAJECTORY_ARTIFACT',str(tmp_path/'trajectory.json')))
    if artifact.exists():raise RuntimeError('fresh_trajectory_artifact_required')
    payload={'status':'started','qualification':'manufactured_dry_reacting_reduced_free_slab_not_material_validation','runs':[]}
    def save():artifact.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    save()
    try:
        op=reacting_host(water,order=1.,weights=10.,equal_volume=False)
        initial=op.state_from_temperatures([[0.,.01,0.,2.],[0.,.008,0.,2.]],[305.,306.],normal_stretches=(1.,1.),tangential_stretch=1.)
        y0=initial_oracle()
        assert np.max(np.abs(initial.internal_energy_j-y0[3:]))<1e-9
        ref=solve_ivp(independent_rhs(),(0.,.1),y0,method='DOP853',rtol=1e-12,atol=1e-13,dense_output=True)
        wrong=solve_ivp(independent_rhs(with_constraint=False),(0.,.1),y0,method='DOP853',rtol=1e-12,atol=1e-13)
        wrong_eta=solve_ivp(independent_rhs(current_viscosity=False),(0.,.1),y0,method='DOP853',rtol=1e-12,atol=1e-13)
        assert ref.success and wrong.success and wrong_eta.success
        payload['oracle']={'final':ref.y[:,-1].tolist(),'omitted_constraint_final':wrong.y[:,-1].tolist(),
            'reference_eta_final':wrong_eta.y[:,-1].tolist(),'nfev':ref.nfev}
        save()
        assert np.max(np.abs(ref.y[3:,-1]-wrong.y[3:,-1]))>1e-4
        assert np.max(np.abs(ref.y[:3,-1]-wrong_eta.y[:3,-1]))>2e-7
        runs=[]
        for cap in (.025,.0125):
            numerical=policy(initial_step_s=cap,maximum_step_s=cap,relative_tolerance=1e-8,
                amount_absolute_tolerance_mol=1e-11,energy_absolute_tolerance_j=1e-6,
                stretch_absolute_tolerance=1e-9,stretch_scale=1.)
            out=integrate(initial,op,start_s=0.,end_s=.1,policy=numerical)
            payload['runs'].append({'policy':encode(numerical),'result':encode(out)})
            save()
            assert out.status=='completed',out.reason
            assert out.steps and len(out.states)==len(out.steps)+1 and out.times_s[-1]==.1
            assert np.max(np.abs(out.states[-1].mechanical_stretches-ref.y[:3,-1]))<2e-7
            assert np.max(np.abs(out.states[-1].internal_energy_j-ref.y[3:,-1]))<2e-6
            max_global=0.
            for step,time,state in zip(out.steps,out.times_s[1:],out.states[1:],strict=True):
                a=2*math.exp(-.1*time);b=2-a
                assert np.max(np.abs(state.amounts_mol[:,3]-a))<1e-9
                assert np.max(np.abs(state.amounts_mol[:,0]-b))<1e-9
                assert np.array_equal(state.amounts_mol[:,1:3],initial.amounts_mol[:,1:3])
                assert set(step.cell_work_components_j)=={'external_traction','mechanical_constraint','body'}
                assert np.all(step.face_species_mol==0.)
                assert step.face_energy_j[0]==step.face_energy_j[-1]==0.
                n0,n1,t=map(F,map(float,state.mechanical_stretches))
                delta=sum((F(float(u))-F(float(u0)) for u,u0 in zip(state.internal_energy_j,initial.internal_energy_j,strict=True)),F())
                residual=abs(delta+F(101325.)*F(.00014)*((n0+n1)*t*t-2))
                assert residual<F(4e-6)
                max_global=max(max_global,float(residual))
            audit_integration(encode(out),numerical,start_s=0.,end_s=.1)
            payload['runs'][-1]['max_global_prefix_residual_j']=max_global
            runs.append(out);save()
        assert np.max(np.abs(runs[0].states[-1].internal_energy_j-runs[1].states[-1].internal_energy_j))<2e-6
        payload['status']='passed';save()
    except BaseException as exc:
        payload.update(status='failed',reason=str(exc),traceback=traceback.format_exc());save();raise
