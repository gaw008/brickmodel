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
ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github');OUT=Path(__file__).with_name('profile-result.json')
start=time.monotonic(); result={'status':'running','qualification':'HEOS_fixed_inventory_1_over_64_second_prefix_against_independent_Python_entropy_not_active_phase_transfer','stages':[]};calls=[0]
def enc(x):
    if isinstance(x,F):return {'numerator':x.numerator,'denominator':x.denominator}
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    if is_dataclass(x):return {f.name:enc(getattr(x,f.name)) for f in fields(x)}
    if isinstance(x,Mapping):return {str(k):enc(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [enc(v) for v in x]
    return x
def save():
    result['elapsed_seconds']=time.monotonic()-start;result['python_oracle_state_tp_calls']=calls[0]
    OUT.write_text(json.dumps(enc(result),indent=2)+'\n')
def stage(name,value):result['stages'].append({'name':name,'value':value,'elapsed_seconds':time.monotonic()-start});save()
try:
    old=WaterProperties.state_tp
    def counted(self,*a,**k):calls[0]+=1;return old(self,*a,**k)
    WaterProperties.state_tp=counted
    w=load_water_properties(ROOT/'data/sandbox/water',backend='heos',backend_manifest=ROOT/'data/sandbox/water/heos-8.0.0-approved-manifest.json')
    reference_water=load_water_properties(ROOT/'data/sandbox/water')
    result['implementation']=json.loads(w.implementation.canonical_json)
    assert type(reference_water) is WaterProperties and reference_water.implementation is None
    result['reference_provider']={'class':type(reference_water).__name__,'implementation':reference_water.implementation,'reference':reference_water.reference,'assets':dict(reference_water.source_asset_sha256)}
    import sys
    result['loaded_modules']={name:module.__file__ for name,module in sys.modules.items() if name.startswith('sludge_sandbox') and getattr(module,'__file__',None)}
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
    assert enc(initial.amounts_mol)==previous['amounts_mol']
    initial_energy_delta=float(initial.internal_energy_j[0])-previous['internal_energy_j'][0]
    assert abs(initial_energy_delta)<=1e-6, 'same T/inventory initial energy differs beyond original energy gate'
    assert initial.energy_model_identity==op.energy_model_identity
    assert enc(initial.energy_model_identity)!=previous['energy_model_identity'], 'backend identity must differ'
    stage('initial_backend_comparison',{'energy_delta_j':initial_energy_delta,'inventory_exact':True,'identity_intentionally_distinct':True,'temperature_k':300.})
    import cProfile,pstats,io
    profiler=cProfile.Profile()
    profiler.enable()
    out=op.evaluate(initial,0.)
    profiler.disable()
    profiler.dump_stats(str(Path(__file__).with_name('evaluate.prof')))
    report=io.StringIO()
    stats=pstats.Stats(profiler,stream=report).strip_dirs().sort_stats('cumulative')
    stats.print_stats(45)
    Path(__file__).with_name('profile.txt').write_text(report.getvalue())
    result.update(status='profile_completed',qualification='one_actual_host_evaluation_cost_diagnostic_not_trajectory_validation',temperature_error_bound_k=out.total_inverses[0].temperature_error_bound_k)
    save()
except BaseException as exc:
    result.update(status='failed',exception_type=type(exc).__name__,exception=str(exc),traceback=traceback.format_exc());save();raise
