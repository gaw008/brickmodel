"""Original manufactured closed-storage inverse, with separate Python EOS reference."""
from pathlib import Path
import json,traceback
from scipy.optimize import brentq
from sludge_sandbox.phase_storage import IdealGasPhase,InversePolicy
from sludge_sandbox.rigid_water_gas import RigidWaterGas,PressurePolicy
from sludge_sandbox.rigid_storage import RigidStorage,DeclaredNumericalEnvelope
from sludge_sandbox.thermochemistry import ShomateGas,ShomateSegment
from sludge_sandbox.water_properties import load_water_properties
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage5')
R=8.31446261815324
out={'passed':False}
try:
    water=load_water_properties(repo/'data/sandbox/water',backend='heos',backend_manifest=case/'expected.json')
    original=load_water_properties(repo/'data/sandbox/water')
    curve=ShomateGas('fixture',(ShomateSegment((100.,2000.),(30.,0.,0.,0.,0.,0.,0.,0.),0.,R,('manufactured-cp30',)),),'manufactured_test_fixture',('manufactured-cp30',))
    gas=IdealGasPhase(curve,.028,0,('nist-codata-2022',))
    mechanical=RigidWaterGas(water,('fixture',),1e-4,(1e4,1e6),'planar_interface_no_capillary_pressure',PressurePolicy(1e-13,1e-5,150))
    envelope=DeclaredNumericalEnvelope((295.,310.),(1e4,1e6),1e-8,1e-16,1e-4,{'fixture':1e-9},{'fixture':20.},'explicit_manufactured_numerical_verification_envelope_not_eos_certificate',('manufactured-error-envelope',))
    model=RigidStorage(mechanical=mechanical,gas_phases={'fixture':gas},envelope=envelope,allow_manufactured=True)
    mass=original.reference.molar_mass_kg_mol
    p=brentq(lambda p:2.*mass/original.state_tp(300.,p,phase='liquid').density_kg_m3+.01*R*300./p-1e-4,1e4,1e6,xtol=1e-7)
    state=original.state_tp(300.,p,phase='liquid')
    target=2.*state.internal_energy_j_mol+.01*(30.-R)*300.
    inverse=model.temperature_from_energy(target,2.,{'fixture':.01},(295.,310.),InversePolicy(1e-5,1e-4,100))
    actual=inverse.state.mechanical
    assert abs(actual.temperature_k-300.)<=1e-4 and abs(actual.pressure_pa-p)<=.2
    assert abs(inverse.energy_residual_j)<=1e-5 and inverse.temperature_error_bound_k<=1e-4
    assert inverse.final_temperature_bracket_k[0]<=300.<=inverse.final_temperature_bracket_k[1]
    assert actual.liquid_inventory_mol==2. and actual.gas_inventory_mol=={'fixture':.01}
    assert 'coolprop-8.0.0-heos-water' in actual.source_ids
    assert actual.source_asset_sha256['water_implementation_v1.json']==water.implementation.sha256
    out.update(passed=True,target_j=target,original_pressure_pa=p,temperature_k=actual.temperature_k,pressure_pa=actual.pressure_pa,energy_residual_j=inverse.energy_residual_j,temperature_error_bound_k=inverse.temperature_error_bound_k,final_temperature_bracket_k=inverse.final_temperature_bracket_k,source_ids=actual.source_ids,source_assets=dict(actual.source_asset_sha256),implementation=json.loads(water.implementation.canonical_json),scope='manufactured fixed-volume closed-storage one inverse, not full wet trajectory')
except BaseException as e:
    out.update(error=repr(e),traceback=traceback.format_exc())
    raise
finally:(case/'inverse-result.json').write_text(json.dumps(out,indent=2)+'\n')
print('closed-storage inverse passed original gates')
