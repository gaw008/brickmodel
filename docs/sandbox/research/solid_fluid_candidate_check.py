"""Compare actual storage/integration to the separately generated analytic JSON."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from sludge_sandbox.incompressible_solid import SolidShomateCaloric, IncompressibleSolidPhase
from sludge_sandbox.integration import ConservedState, IntegrationPolicy, Rates, integrate
from sludge_sandbox.phase_storage import IdealGasPhase, InversePolicy
from sludge_sandbox.rigid_storage import RigidStorage, DeclaredNumericalEnvelope
from sludge_sandbox.rigid_water_gas import RigidWaterGas, PressurePolicy
from sludge_sandbox.solid_fluid_storage import SolidFluidStorage
from sludge_sandbox.thermochemistry import ShomateGas, ShomateSegment
from sludge_sandbox.water_properties import load_water_properties


def build(root):
    r=8.31446261815324
    source=('manufactured:two-solid-two-gas-oracle',)
    water=load_water_properties(root/'data/sandbox/water')
    gases={}
    for name,cp,h,mass in (('g1',30.,-1000.,.028),('g2',40.,-2000.,.032)):
        segment=ShomateSegment((295.,400.),(cp,0.,0.,0.,0.,h/1000,0.,h/1000),h,r,source)
        curve=ShomateGas(name,(segment,),'manufactured_test_fixture',source)
        gases[name]=IdealGasPhase(curve,mass,0,source)
    mechanical=RigidWaterGas(water,tuple(gases),1e-4,(1e4,1e6),
                             'planar_interface_no_capillary_pressure',PressurePolicy(1e-13,1e-5,150))
    envelope=DeclaredNumericalEnvelope((295.,400.),(1e4,1e6),1e-8,1e-16,1e-4,
                                      {'g1':1e-10,'g2':1e-10},{'g1':20.,'g2':30.},
                                      'manufactured_error_envelope_not_physical_certificate',source)
    fluid=RigidStorage(mechanical,gases,envelope,True)
    solids={}
    for name,cp,h,volume,mass in (('a',30.,-100000.,1e-5,.05),('b',50.,-200000.,2e-5,.06)):
        caloric=SolidShomateCaloric(species_id=name,crystal_phase_id='manufactured_single_branch',
            temperature_range_k=(295.,400.),coefficients=(cp,0.,0.,0.,0.,h/1000,0.,h/1000),
            formation_enthalpy_298_j_mol=h,dataset_id='manufactured:analytic',version='1',
            classification='manufactured_test_fixture',source_ids=source,
            source_asset_sha256=(('manufactured:coefficient_fixture','a'*64),))
        solids[name]=IncompressibleSolidPhase(caloric=caloric,molar_mass_kg_mol=mass,
            molar_volume_m3_mol=volume,reference_pressure_pa=1e5,pressure_range_pa=(1e4,1e6),
            volume_model_id='manufactured:fixed',volume_version='1',volume_classification='manufactured_test_fixture',
            volume_source_ids=source,volume_source_asset_sha256=(('manufactured:volume_fixture','b'*64),),
            declared_u_error_j_mol=1e-10,declared_v_error_m3_mol=0.,
            error_method_id='manufactured:declared',error_classification='manufactured_test_fixture',
            error_source_ids=source,allow_manufactured=True)
    return SolidFluidStorage(fluid_template=fluid,solid_phases=solids,bulk_volume_m3=1e-4,
        bulk_volume_error_m3=1e-16,geometry_source_ids=source,
        geometry_id='manufactured:bulk',geometry_version='1',
        geometry_classification='manufactured_test_fixture',allow_manufactured=True)


def main():
    root=Path(__file__).resolve().parents[3]
    reference_path=Path(__file__).with_name('solid_fluid_analytic_oracle.json')
    refs=json.loads(reference_path.read_text())['cases']
    model=build(root)
    gas={'g1':.001,'g2':.002};solid={'a':2.,'b':1.}
    rows=[]
    for name,t,n in (('initial_300k',300.,solid),('higher_350k',350.,solid),
                     ('half_solid_300k',300.,{'a':1.,'b':.5})):
        state=model.evaluate_at_temperature(t,0.,gas,n)
        actual=dict(solid_volume_m3=state.solid_volume_m3,gas_volume_m3=state.mechanical.gas_volume_m3,
                    pressure_pa=state.mechanical.pressure_pa,internal_energy_j=state.internal_energy_j,
                    enthalpy_j=state.enthalpy_j,heat_capacity_j_k=state.closed_heat_capacity_j_k)
        tolerances=dict(solid_volume_m3=1e-15,gas_volume_m3=1e-15,pressure_pa=1e-5,
                        internal_energy_j=1e-7,enthalpy_j=1e-7,heat_capacity_j_k=1e-9)
        errors={key:actual[key]-float(refs[name][key]) for key in actual}
        rows.append(dict(case=name,errors=errors,passed=all(abs(errors[k])<=tolerances[k] for k in errors)))
    policy=InversePolicy(1e-6,1e-5,100)
    inverse=model.temperature_from_energy(float(refs['after_250j']['internal_energy_j']),0.,gas,solid,(295.,400.),policy)
    inverse_error=inverse.state.mechanical.temperature_k-float(refs['after_250j']['temperature_k'])
    initial_u=model.evaluate_at_temperature(300.,0.,gas,solid).internal_energy_j
    initial=ConservedState([[0.,.001,.002,2.,1.]],[initial_u])
    calls=[]
    def operator(state,time):
        row=state.amounts_mol[0]
        result=model.temperature_from_energy(float(state.internal_energy_j[0]),float(row[0]),
            {'g1':float(row[1]),'g2':float(row[2])},{'a':float(row[3]),'b':float(row[4])},(295.,400.),policy)
        calls.append(result.state.mechanical.temperature_k)
        return Rates(np.zeros((2,5)),np.zeros(2),np.zeros((1,5)),np.array([25.]))
    trajectory=integrate(initial,operator,start_s=0,end_s=10.,policy=IntegrationPolicy(
        initial_step_s=1.,maximum_step_s=1.,minimum_step_s=1e-8,relative_tolerance=1e-7,
        amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-6,amount_scale_mol=1.,
        energy_scale_j=1.,maximum_steps=50,maximum_rejections=10,maximum_wall_seconds=60))
    last=model.temperature_from_energy(float(trajectory.states[-1].internal_energy_j[0]),0.,gas,solid,(295.,400.),policy)
    final_error=last.state.mechanical.temperature_k-float(refs['after_250j']['temperature_k'])
    inventory_equal=all(np.array_equal(s.amounts_mol,initial.amounts_mol) for s in trajectory.states)
    energy_errors=[float(s.internal_energy_j[0])-initial_u-25.*t for s,t in zip(trajectory.states,trajectory.times_s)]
    passed=(all(row['passed'] for row in rows) and abs(inverse_error)<=1e-4 and abs(final_error)<=1e-4
            and trajectory.status=='completed' and inventory_equal and max(map(abs,energy_errors))<=1e-7)
    paths=[Path(__file__),reference_path,root/'src/sludge_sandbox/solid_fluid_storage.py',
           root/'src/sludge_sandbox/incompressible_solid.py',root/'src/sludge_sandbox/integration.py']
    out=dict(classification='manufactured_test_fixture',passed=passed,forward_comparisons=rows,
        inverse_error_k=inverse_error,integrated_final_error_k=final_error,
        integration_status=trajectory.status,operator_calls=len(calls),inventory_equal=inventory_equal,
        saved_state_energy_errors_j=energy_errors,
        hashes={str(p.resolve().relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in paths})
    Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps(out,indent=2))
    if not passed:raise SystemExit('preregistered analytic/integration comparison failed')


if __name__=='__main__':main()
