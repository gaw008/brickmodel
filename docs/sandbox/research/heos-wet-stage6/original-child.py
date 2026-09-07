from pathlib import Path
from dataclasses import fields,is_dataclass,asdict,replace
from fractions import Fraction as F
from collections.abc import Mapping
import json,time,traceback,math,hashlib
import numpy as np
from entropy_reference import OracleInputs,OraclePolicy,FixedInventoryEntropyReference
from sludge_sandbox.water_properties import load_water_properties,WaterProperties
from sludge_sandbox.integration import integrate
from test_deforming_solid_heat import host
from test_deforming_solid_storage import exact_volume_wet_model
from test_integration import policy
ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github');OUT=Path(__file__).with_name('result.json')
start=time.monotonic(); result={'status':'running','qualification':'partial_1_over_64_second_refinement_not_full_10_percent_validation','stages':[]};calls=[0]
def enc(x):
    if isinstance(x,F):return {'numerator':x.numerator,'denominator':x.denominator}
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    if is_dataclass(x):return {f.name:enc(getattr(x,f.name)) for f in fields(x)}
    if isinstance(x,Mapping):return {str(k):enc(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [enc(v) for v in x]
    return x
def save():
    result['elapsed_seconds']=time.monotonic()-start;result['public_water_state_tp_calls']=calls[0]
    OUT.write_text(json.dumps(enc(result),indent=2)+'\n')
def stage(name,value):result['stages'].append({'name':name,'value':value,'elapsed_seconds':time.monotonic()-start});save()
try:
    old=WaterProperties.state_tp
    def counted(self,*a,**k):calls[0]+=1;return old(self,*a,**k)
    WaterProperties.state_tp=counted
    w=load_water_properties(ROOT/'data/sandbox/water')
    result.update(water_reference=w.reference,water_assets=dict(w.source_asset_sha256),water_limits=w.numerical_limits,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/sludge_sandbox').glob('*.py')})
    op0=host(w,isotropic=True);p=exact_volume_wet_model(w)
    p=replace(p,motion=replace(p.motion,tangential_stretches_at_knots=(1.,.9)),skeleton=replace(p.skeleton,viscosity_pa_s=0.))
    base=replace(op0.base_model,storages=(p.template,),transport=replace(op0.base_model.transport,storages=(p.template.fluid_template,)))
    op=replace(op0,base_model=base,point_storages=(p,))
    pol=policy(initial_step_s=1/256,maximum_step_s=1/256,relative_tolerance=1e-6,energy_absolute_tolerance_j=1e-6,maximum_steps=4,maximum_rejections=4,maximum_wall_seconds=25)
    result.update(integration_policy=pol,inverse_policy=op.base_model.transport.inverse_policy,energy_model_identity=op.energy_model_identity)
    initial=op.state_from_temperatures([[1.,.01,2.]],[300.],time_s=0.);stage('initial',initial)
    previous=json.loads(Path(__file__).with_name('previous-result.json').read_text())['stages'][0]['value']
    assert enc(initial)==previous, 'initial state changed from previous partial case'
    run=integrate(initial,op,start_s=0.,end_s=1/64,policy=pol);stage('actual_integration',run)
    assert run.status=='completed',run.reason
    sums={k:F() for k in ('elastic','interface','pore','body','dissipation')};energy=F();dn=[F(),F(),F()];prefix=[]
    for t,s,l in zip(run.times_s[1:],run.states[1:],run.steps):
        for k in sums:sums[k]+=F(float(l.cell_work_components_j[k][0]))
        energy+=F(float(l.cell_work_j[0]))+F(float(l.face_energy_j[0]))-F(float(l.face_energy_j[1]))
        for j in range(3):dn[j]+=F(float(l.face_species_mol[0,j]))-F(float(l.face_species_mol[1,j]))+F(float(l.reaction_species_mol[0,j]))
        residual=F(float(s.internal_energy_j[0]))-F(float(initial.internal_energy_j[0]))-energy
        nres=[F(float(s.amounts_mol[0,j]))-F(float(initial.amounts_mol[0,j]))-dn[j] for j in range(3)]
        prefix.append({'time_s':t,'energy_residual_j':residual,'amount_residual_mol':nres,'component_prefix_j':dict(sums)})
        assert abs(residual)<=F(1e-6) and all(abs(v)<=F(pol.amount_absolute_tolerance_mol) for v in nres)
        assert np.array_equal(s.amounts_mol,initial.amounts_mol)
        assert l.cell_work_components_j['body'][0]==0 and l.cell_work_components_j['dissipation'][0]==0
    stage('independent_accepted_prefix_reconstruction',prefix)
    inputs=OracleInputs(1.,.01,2.,30.,5.,2e-5,300.,1.4e-4,8.31446261815324)
    rp=OraclePolicy((295.,310.),(1e4,1e6),1e-9,1e-6,1e-8,1e-14,100)
    ref=FixedInventoryEntropyReference(inputs,rp,w)
    # The motion program alone supplies geometry; no tested storage supplies truth.
    lam=float(p.motion.sample(1/64).normal_stretches[0]);point=ref.solve(1.4e-4*lam**3)
    stage('independent_entropy_endpoint',{'point':point,'inputs':inputs,'policy':rp,'lambda':lam})
    out=op.evaluate(run.states[-1],run.times_s[-1]);actual=out.thermal_evaluation.storage_states[0].mechanical
    wi=w.state_tp(300.,ref.initial_pressure_pa,phase='liquid');wf=w.state_tp(point.temperature_k,point.pressure_pa,phase='liquid')
    refs={'elastic':.5*1000*1.4e-4*(3*math.log(lam))**2,'interface':.0015*(lam**2-1),'pore':w.reference.molar_mass_kg_mol*(wf.native_internal_energy_j_kg-wi.native_internal_energy_j_kg)+(.01*(30-inputs.gas_constant_j_mol_k)+10)*(point.temperature_k-300),'body':0.,'dissipation':0.}
    errors={k:abs(float(sums[k])-refs[k]) for k in sums}
    errors.update(temperature_k=abs(actual.temperature_k-point.temperature_k),pressure_pa=abs(actual.pressure_pa-point.pressure_pa))
    stage('comparison',{'native_water_operands':{'initial_u_j_kg':wi.native_internal_energy_j_kg,'final_u_j_kg':wf.native_internal_energy_j_kg,'initial_s_j_kg_k':wi.native_entropy_j_kg_k,'final_s_j_kg_k':wf.native_entropy_j_kg_k,'initial_pressure_pa':ref.initial_pressure_pa},'actual_mechanical':actual,'temperature_error_bound_k':out.total_inverses[0].temperature_error_bound_k,'reference_work_j':refs,'errors':errors})
    assert errors['temperature_k']<=2e-5 and errors['pressure_pa']<=.2
    assert all(errors[k]<=1e-6 for k in sums)
    result['status']='completed_partial_smoke';save()
except BaseException as exc:
    result.update(status='failed',exception_type=type(exc).__name__,exception=str(exc),traceback=traceback.format_exc());save();raise
