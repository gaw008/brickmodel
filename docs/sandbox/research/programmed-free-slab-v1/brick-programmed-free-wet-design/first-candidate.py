"""Prepared native-water test; requires explicit future wrapper admission."""
from dataclasses import replace
from fractions import Fraction as F
import json,os,traceback
from pathlib import Path
import numpy as np
from sludge_sandbox.boundary_program import BoundaryProgram,ProgramIdentity
from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeat
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.integration import integrate
from sludge_sandbox.checkpoint import audit_integration
from sludge_sandbox.verification_case import encode
from test_free_slab_phase_transfer import slab_transfer,ingredients
from test_integration import policy


def test_programmed_free_wet(ingredients,tmp_path):
    artifact=Path(os.environ.get('BRICK_PROGRAMMED_FREE_WET_ARTIFACT',str(tmp_path/'trajectory.json')))
    if artifact.exists():raise RuntimeError('fresh_artifact_required')
    payload={'status':'started','qualification':'virtual_program_actual_water_manufactured_free_slab_sparse_coupling','runs':[]}
    def save():artifact.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    save()
    try:
        phase=slab_transfer(ingredients);base=phase.base_model
        program=BoundaryProgram(identity=ProgramIdentity(program_id='virtual:short-free-wet',version='1',classification='virtual_design_choice',source_ids=('virtual:short-free-wet',)),
            knot_times_s=(0.,3e-5,7e-5,1e-4),gas_temperature_k=(305.,310.,308.,304.),radiation_temperature_k=(307.,312.,309.,306.),
            total_pressure_pa=(101325.,)*4,species_order=('fixture','H2O'),mole_fractions=((1.,0.),)*4)
        wrapped=ProgrammedSolidFluidHeat(base_model=base,program=program,convection_w_m2_k=20.,emissivity=.5,
            stefan_boltzmann_w_m2_k4=5.670374419e-8,coefficient_set_id='manufactured:film',coefficient_version='1',
            coefficient_classification='manufactured',coefficient_source_ids=('manufactured:film',),allow_manufactured=True,
            surface_policy=SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=200))
        op=replace(phase,base_model=wrapped)
        initial=base.state_from_temperatures([[1.,.01,1e-5,2.],[.5,.008,.001,2.]],[300.,301.],normal_stretches=(1.,1.),tangential_stretch=1.)
        payload['initial']=encode(initial);payload['program']=encode(program);save();outputs=[];temps=[]
        for cap in (1e-4,2.5e-5):
            numerical=policy(initial_step_s=cap,maximum_step_s=cap,minimum_step_s=1e-10,relative_tolerance=1e-7,
                amount_absolute_tolerance_mol=1e-11,energy_absolute_tolerance_j=1e-6,stretch_absolute_tolerance=1e-9,
                stretch_scale=1.,maximum_steps=12,maximum_rejections=8,maximum_wall_seconds=90.)
            out=integrate(initial,op,start_s=0.,end_s=1e-4,policy=numerical,breakpoints_s=wrapped.breakpoints_s(0.,1e-4))
            payload['runs'].append({'policy':encode(numerical),'result':encode(out)});save()
            assert out.status=='completed',out.reason
            assert out.times_s[-1]==1e-4 and all(k in out.times_s for k in (3e-5,7e-5))
            sums=[F()]*3;exact=[F()]*3;roundoff=[F()]*3;energy=[F()]*2;boundary=F();cr=ce=F()
            for ledger,state in zip(out.steps,out.states[1:],strict=True):
                assert not any(ledger.start_s<k<ledger.end_s for k in (3e-5,7e-5))
                assert np.all(ledger.face_species_mol==0.) and np.all(state.mechanical_stretches>0)
                assert set(ledger.cell_work_components_j)=={'external_traction','mechanical_constraint','body'}
                for i in range(2):
                    row=state.amounts_mol[i];start=initial.amounts_mol[i]
                    assert row[1]==start[1] and row[3]==start[3]
                    assert abs(F(float(row[0]))+F(float(row[2]))-F(float(start[0]))-F(float(start[2])))<F(1e-11)
                    energy[i]+=F(float(ledger.face_energy_j[i]))-F(float(ledger.face_energy_j[i+1]))+F(float(ledger.cell_work_j[i]))
                    assert abs(F(float(state.internal_energy_j[i]))-F(float(initial.internal_energy_j[i]))-energy[i])<F(1e-6)
                for i in range(3):
                    v=F(float(ledger.stretch_increment[i]));q=ledger.stretch_quadrature_roundoff[i]
                    sums[i]+=v;exact[i]+=v-q;roundoff[i]+=abs(q);change=F(float(state.mechanical_stretches[i]))-1
                    assert abs(change-sums[i])<=F(1e-9) and abs(change-exact[i])<=F(1e-9) and roundoff[i]<=F(1e-9)
                c=list(map(F,map(float,ledger.cell_work_components_j['mechanical_constraint'])));q=ledger.component_quadrature_roundoff_j['mechanical_constraint']
                cr+=abs(sum(c,F()));ce+=abs(sum((v-z for v,z in zip(c,q,strict=True)),F()));assert max(cr,ce)<=F(1e-6)
                boundary+=F(float(ledger.face_energy_j[0]))-F(float(ledger.face_energy_j[-1]))
                n0,n1,t=map(F,map(float,state.mechanical_stretches));de=sum((F(float(v))-F(float(z)) for v,z in zip(state.internal_energy_j,initial.internal_energy_j,strict=True)),F())
                assert abs(de+101325*F(.00014)*((n0+n1)*t*t-2)-boundary)<F(4e-6)
            assert boundary>0
            audit_integration(encode(out),numerical,start_s=0.,end_s=1e-4)
            last=out.states[-1];assert last.amounts_mol[0,0]<1. and last.amounts_mol[1,0]>.5
            final=wrapped.evaluate(last,1e-4);current=final.base_evaluation
            values=[s.mechanical.temperature_k for s in current.storage_states];temps.append(values)
            n0,n1,t=map(float,last.mechanical_stretches);area=.014*t*t;width=.01*n1
            expected=.2*area*(final.surface_temperature_k-values[-1])/(width/2)
            assert abs(expected-final.conductive_into_cell_w)<1e-8
            assert abs(final.surface_balance_residual_w)<=final.surface_balance_limit_w
            payload['runs'][-1]['final_callback']=encode(final);save();outputs.append(out)
        assert outputs[0].times_s!=outputs[1].times_s and len(outputs[1].steps)>len(outputs[0].steps)
        a,b=[x.states[-1] for x in outputs]
        for name,tol in [('amounts_mol',1e-11),('internal_energy_j',2e-6),('mechanical_stretches',2e-7)]:assert np.max(np.abs(getattr(a,name)-getattr(b,name)))<tol
        assert np.max(np.abs(np.array(temps[0])-np.array(temps[1])))<2e-6
        payload['status']='passed';save()
    except BaseException as exc:
        payload.update(status='failed',reason=str(exc),traceback=traceback.format_exc());save();raise
