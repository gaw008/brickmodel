"""Independent two-cell heat/mechanics ODE with local constraint work."""
from dataclasses import replace
from fractions import Fraction as F
import json
import math
import numpy as np
from scipy.integrate import solve_ivp
from sludge_sandbox.integration import integrate
from sludge_sandbox.checkpoint import audit_integration
from sludge_sandbox.verification_case import encode
from test_integration import policy
from test_dynamic_solid_storage import water,forbid_water_eos
from test_free_solid_slab import host
from test_rigid_storage import R


def independent_rhs(with_constraint=True):
    def rhs(_,y):
        normal=y[:2];t=y[2];energies=y[3:]
        v0=.00014;eta=1e6;pe=101325.;ng=(.01,.008)
        temperatures=[];pressures=[];sn=[];st=[]
        for i,n in enumerate(normal):
            ln,lt=math.log(n),math.log(t);theta=ln+2*lt
            elastic=v0*(500*theta**2+400*((ln-theta/3)**2+2*(lt-theta/3)**2))
            interface=.0015*t*t
            temperature=(energies[i]-elastic-interface+200004.)/(10+ng[i]*(30-R))
            temperatures.append(temperature)
            pressures.append(ng[i]*R*temperature/(v0*n*t*t-4e-5))
            sn.append((1000*theta+800*(ln-theta/3))/n)
            st.append((1000*theta+800*(lt-theta/3))/t+.0015*t/v0)
        nd=[n*n/eta*((p-pe)*t*t-force) for n,p,force in zip(normal,pressures,sn,strict=True)]
        td=t*t*sum(v0*((p-pe)*n*t-force) for n,p,force in zip(normal,pressures,st,strict=True))/(2*v0*eta)
        flux=.2*(.014*t*t)*(temperatures[0]-temperatures[1])/(.005*(normal[0]+normal[1]))
        energy_rates=[]
        for i,n in enumerate(normal):
            vdot=v0*(t*t*nd[i]+2*n*t*td)
            reaction=st[i]+eta*td/(t*t)-(pressures[i]-pe)*n*t
            constraint=2*v0*reaction*td if with_constraint else 0.
            energy_rates.append((-flux if i==0 else flux)-pe*vdot+constraint)
        return nd+[td]+energy_rates
    return rhs


def test_coupled_dry_trajectory_and_negative_local_energy_control(water):
    op=replace(host(water),external_pressure_pa=101325.)
    initial=op.state_from_temperatures([[0.,.01,2.],[0.,.008,2.]],[300.,301.],
                                      normal_stretches=(1.,1.),tangential_stretch=1.)
    y0=np.r_[initial.mechanical_stretches,initial.internal_energy_j]
    reference=solve_ivp(independent_rhs(),(0.,.1),y0,method='DOP853',rtol=1e-12,atol=1e-13)
    wrong=solve_ivp(independent_rhs(False),(0.,.1),y0,method='DOP853',rtol=1e-12,atol=1e-13)
    assert reference.success and wrong.success
    assert np.max(np.abs(reference.y[3:,-1]-wrong.y[3:,-1]))>1e-4
    # Global balance alone cannot detect the omitted opposite local powers.
    bad=wrong.y[:,-1]
    assert abs(sum(bad[3:]-y0[3:])+101325.*.00014*(sum(bad[:2])*bad[2]**2-2))<4e-6
    runs=[];max_global=0.
    for cap in (.025,.0125):
        numerical=policy(initial_step_s=cap,maximum_step_s=cap,relative_tolerance=1e-8,
            energy_absolute_tolerance_j=1e-6,stretch_absolute_tolerance=1e-9,stretch_scale=1.)
        result=integrate(initial,op,start_s=0.,end_s=.1,policy=numerical)
        assert result.status=='completed',result.reason
        final=result.states[-1];runs.append(result)
        assert np.max(np.abs(final.mechanical_stretches-reference.y[:3,-1]))<2e-7
        assert np.max(np.abs(final.internal_energy_j-reference.y[3:,-1]))<2e-6
        constraint_sum_abs=F();constraint_exact_abs=F()
        for step,state in zip(result.steps,result.states[1:],strict=True):
            assert np.array_equal(state.amounts_mol,initial.amounts_mol)
            assert set(step.cell_work_components_j)=={'external_traction','mechanical_constraint','body'}
            constraint=tuple(map(F,map(float,step.cell_work_components_j['mechanical_constraint'])))
            rounding=step.component_quadrature_roundoff_j['mechanical_constraint']
            constraint_sum_abs+=abs(sum(constraint,F()))
            constraint_exact_abs+=abs(sum((v-q for v,q in zip(constraint,rounding,strict=True)),F()))
            assert constraint_sum_abs<=F(numerical.energy_absolute_tolerance_j)
            assert constraint_exact_abs<=F(numerical.energy_absolute_tolerance_j)
            assert np.all(step.face_species_mol==0.)
            assert step.face_energy_j[0]==step.face_energy_j[-1]==0.
            n0,n1,t=map(float,state.mechanical_stretches)
            delta=sum((F(float(a))-F(float(b)) for a,b in zip(state.internal_energy_j,initial.internal_energy_j,strict=True)),F())
            volume=F(.00014)*((F(n0)+F(n1))*F(t)**2-2)
            residual=abs(delta+F(101325.)*volume)
            assert residual<F(4e-6)
            max_global=max(max_global,float(residual))
        audit_integration(encode(result),numerical,start_s=0.,end_s=.1)
    assert np.max(np.abs(runs[0].states[-1].internal_energy_j-runs[1].states[-1].internal_energy_j))<2e-6
    print(json.dumps(dict(qualification='manufactured_two_cell_dry_thermal_mechanical_trajectory_not_material_validation',
        steps=[len(r.steps) for r in runs],rejected=[r.rejected_trials for r in runs],
        maximum_prefix_global_energy_residual_j=max_global,
        max_final_energy_error_j=[float(np.max(np.abs(r.states[-1].internal_energy_j-reference.y[3:,-1]))) for r in runs],
        max_final_stretch_error=[float(np.max(np.abs(r.states[-1].mechanical_stretches-reference.y[:3,-1]))) for r in runs],
        omitted_constraint_local_energy_error_j=float(np.max(np.abs(reference.y[3:,-1]-wrong.y[3:,-1]))))))
