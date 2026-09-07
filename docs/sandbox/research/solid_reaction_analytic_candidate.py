"""Actual SolidFluidHeat candidate against the pre-existing independent oracle.

All constitutive values are manufactured; never a real carbon/sludge model.
Each execution preserves a new numbered artifact pair, including failures.
"""
from dataclasses import replace
from hashlib import sha256
import csv
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests/sandbox')]
from solid_reaction_analytic_reference import reference
from test_solid_fluid_heat import solid_host
from test_water_phase_transfer import DATA
from test_reactions import kinetics
from sludge_sandbox.water_properties import load_water_properties
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.solid_fluid_heat import SolidFluidHeat,InventoryLayout
from sludge_sandbox.phase_storage import IdealGasPhase,InversePolicy
from sludge_sandbox.reactions import SpeciesDefinition,ReactionDefinition,ReactionNetwork
from sludge_sandbox.solid_reactions import ReactionSpeciesBinding,SolidReactionConfig
from sludge_sandbox.integration import integrate,IntegrationPolicy


def candidate():
    ingredients=(load_water_properties(DATA),IdealWaterVapor(DATA),WaterChemicalPotential(DATA))
    host=solid_host(ingredients)
    storage=host.storages[0];template=storage.fluid_template
    original=template.gas_phases['fixture'].caloric
    fn=-30.*298.15/1000.;fx=-1.-30.*298.15/1000.;fs=-50.*298.15/1000.
    nseg=replace(original.segments[0],temperature_range_k=(295.,450.),
        coefficients=(30.,0.,0.,0.,0.,fn,0.,0.),formation_enthalpy_298_j_mol=0.)
    xseg=replace(nseg,coefficients=(30.,0.,0.,0.,0.,fx,0.,-1.),formation_enthalpy_298_j_mol=-1000.)
    gases={'N2':IdealGasPhase(replace(original,species_id='N2',segments=(nseg,)),.028,0,('nist-codata-2022',)),
           'Xgas':IdealGasPhase(replace(original,species_id='Xgas',segments=(xseg,)),.012,0,('nist-codata-2022',))}
    template=replace(template,mechanical=replace(template.mechanical,gas_species_ids=('N2','Xgas')),
        gas_phases=gases,envelope=replace(template.envelope,temperature_range_k=(295.,450.),
        gas_u_error_j_mol={'N2':1e-9,'Xgas':1e-9},gas_cv_lower_j_mol_k={'N2':20.,'Xgas':20.}))
    solid=storage.solid_phases['fixture_solid']
    solid=replace(solid,molar_mass_kg_mol=.012,molar_volume_m3_mol=1e-5,
        caloric=replace(solid.caloric,species_id='Xsolid',temperature_range_k=(295.,450.),
        coefficients=(50.,0.,0.,0.,0.,fs,0.,0.),formation_enthalpy_298_j_mol=0.))
    storage=replace(storage,fluid_template=template,solid_phases={'Xsolid':solid})
    transport=replace(host.transport,storages=(template,),gas_species_order=('N2','Xgas'),
        effective_diffusivities_m2_s={'N2':(0.,),'Xgas':(0.,)},temperature_brackets_k=((295.,450.),),
        inverse_policy=InversePolicy(1e-8,1e-6,150))
    layout=InventoryLayout(species_order=('Xsolid','Xgas','N2','H2O_liquid'),liquid_column_id='H2O_liquid',
        gas_species_order=('N2','Xgas'),solid_species_order=('Xsolid',))
    sources=('manufactured:pre_registered_analytic',)
    species=(SpeciesDefinition('solid','solid',{'C':1},.012,sources,'manufactured'),
             SpeciesDefinition('gas','gas',{'C':1},.012,sources,'manufactured'))
    law=kinetics({'solid':1},candidate_id='manufactured:analytic-first-order',prefactor_mol_m3_s=1.,
        gas_constant_j_mol_k=template.mechanical.gas_constant_j_mol_k,temperature_range_k=(295.,450.))
    network=ReactionNetwork(species,(ReactionDefinition('solid-to-gas','1',{'solid':-1,'gas':1},law,
        'oxygen_free_pyrolysis',sources),),allow_manufactured=True)
    config=SolidReactionConfig(network=network,
        bindings=(ReactionSpeciesBinding('solid','Xsolid',solid),ReactionSpeciesBinding('gas','Xgas',gases['Xgas'])),
        storages=(storage,),inventory_layout=layout,allow_manufactured=True,
        binding_id='manufactured:analytic-binding',version='1',source_ids=sources)
    result=SolidFluidHeat(storages=(storage,),transport=transport,inventory_layout=layout,solid_reactions=config)
    return result,{'solid_F':fs,'product_F':fx,'carrier_F':fn,'R':template.mechanical.gas_constant_j_mol_k,
                   'bulk_m3':storage.bulk_volume_m3,'solid_v_m3_mol':solid.molar_volume_m3_mol,
                   'solid_p0_pa':solid.reference_pressure_pa,'solid_u_error_j_mol':solid.declared_u_error_j_mol,
                   'solid_v_error_m3_mol':solid.declared_v_error_m3_mol,
                   'bulk_error_m3':storage.bulk_volume_error_m3,'inverse_policy':vars(transport.inverse_policy)}


def run_level(host,dt,rows):
    initial=host.state_from_temperatures([[.01,0.,.01,0.]],[300.])
    # Deliberately permissive adaptive policy isolates uniform-step truncation;
    # the acceptance limits below remain the pre-registered physical-unit checks.
    policy=IntegrationPolicy(initial_step_s=dt,maximum_step_s=dt,minimum_step_s=1e-12,
        relative_tolerance=.1,amount_absolute_tolerance_mol=1e-3,energy_absolute_tolerance_j=1e-5,
        amount_scale_mol=.01,energy_scale_j=1.,maximum_steps=5000,maximum_rejections=100,maximum_wall_seconds=120)
    start=time.monotonic()
    run=integrate(initial,host,start_s=0,end_s=2.,policy=policy)
    maxima={k:0. for k in ('solid_mol','temperature_k','pressure_pa','energy_j','carbon_mol','nitrogen_mol','mass_kg','prefix_energy_j','step_energy_j')}
    times=run.times_s
    prefix=0.
    for i,(t,state) in enumerate(zip(times,run.states)):
        inverse=host.decode_inverse(state)[0];actual=inverse.state
        expected={k:float(v) for k,v in reference(float(t)).items()}
        ns,nx,nn,_=map(float,state.amounts_mol[0])
        if i:prefix+=float(run.steps[i-1].face_energy_j[0]-run.steps[i-1].face_energy_j[-1]+run.steps[i-1].cell_work_j[0])
        errors=dict(solid_mol=abs(ns-expected['solid_mol']),temperature_k=abs(actual.mechanical.temperature_k-expected['temperature_k']),
            pressure_pa=abs(actual.mechanical.pressure_pa-expected['pressure_pa']),energy_j=abs(float(state.internal_energy_j[0])-expected['internal_energy_j']),
            carbon_mol=abs(ns+nx-.01),nitrogen_mol=abs(2*nn-.02),mass_kg=abs(.012*(ns+nx)+.028*nn-(.012*.01+.028*.01)),
            prefix_energy_j=abs(float(state.internal_energy_j[0]-initial.internal_energy_j[0])-prefix),
            step_energy_j=(0. if not i else abs(float(state.internal_energy_j[0]-run.states[i-1].internal_energy_j[0])
                -float(run.steps[i-1].face_energy_j[0]-run.steps[i-1].face_energy_j[-1]+run.steps[i-1].cell_work_j[0]))))
        for k,v in errors.items():maxima[k]=max(maxima[k],v)
        rows.append(dict(dt_s=dt,time_s=float(t),solid_mol=ns,product_gas_mol=nx,carrier_mol=nn,
            temperature_k=actual.mechanical.temperature_k,pressure_pa=actual.mechanical.pressure_pa,
            internal_energy_j=float(state.internal_energy_j[0]),temperature_error_bound_k=inverse.temperature_error_bound_k,
            **{'error_'+k:v for k,v in errors.items()}))
    steps=[float(b-a) for a,b in zip(times,times[1:])]
    return dict(dt_s=dt,status=run.status,reason=run.reason,wall_seconds=time.monotonic()-start,
        accepted_steps=len(run.steps),rejected_trials=run.rejected_trials,evaluations=run.evaluations,
        breakpoints_s=[],actual_steps_s=steps,uniform=all(s==dt for s in steps),
        max_errors=maxima,minimum_inventory_mol=min(float(s.amounts_mol.min()) for s in run.states),
        integration_policy=vars(policy))


def main():
    folder=Path(__file__).parent;index=1
    while (folder/f'solid_reaction_analytic_candidate_attempt_{index:03d}.json').exists():index+=1
    stem=folder/f'solid_reaction_analytic_candidate_attempt_{index:03d}'
    rows=[];output={'classification':'manufactured_numerical_verification_not_material_admission','levels':[]}
    files=[Path(__file__).relative_to(ROOT),'docs/sandbox/research/SOLID_REACTION_ANALYTIC_PLAN.md',
        'docs/sandbox/research/solid_reaction_analytic_reference.py','src/sludge_sandbox/solid_fluid_heat.py',
        'src/sludge_sandbox/solid_reactions.py','src/sludge_sandbox/reactions.py','src/sludge_sandbox/solid_fluid_storage.py',
        'src/sludge_sandbox/integration.py','src/sludge_sandbox/incompressible_solid.py',
        'tests/sandbox/test_solid_fluid_heat.py','tests/sandbox/test_water_phase_transfer.py',
        'tests/sandbox/test_reactions.py','tests/sandbox/test_rigid_storage.py',
        'src/sludge_sandbox/rigid_storage.py','src/sludge_sandbox/rigid_water_gas.py',
        'src/sludge_sandbox/water_properties.py','src/sludge_sandbox/thermochemistry.py']
    output['source_hashes']={str(p):sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    try:
        host,inputs=candidate();output['inputs']=inputs
        output['independent_reference_checkpoints']=[reference(t) for t in (0.,.25,.5,1.,2.)]
        for dt in (1/16,1/32,1/64):output['levels'].append(run_level(host,dt,rows))
        levels=output['levels'];fine=levels[-1]['max_errors']
        errors=[level['max_errors']['solid_mol'] for level in levels]
        ratios=[a/b for a,b in zip(errors,errors[1:])]
        output['inventory_refinement_ratios']=ratios
        output['pass']=(all(l['status']=='completed' and l['uniform'] and l['minimum_inventory_mol']>=0 for l in levels)
            and all(r>=2.8 for r in ratios) and fine['solid_mol']<=1e-6 and fine['temperature_k']<=.02 and fine['pressure_pa']<=100
            and all(l['max_errors']['energy_j']<=1e-7 and l['max_errors']['prefix_energy_j']<=1e-7 and l['max_errors']['step_energy_j']<=1e-7
                and l['max_errors']['carbon_mol']<=1e-12 and l['max_errors']['nitrogen_mol']<=1e-12
                and l['max_errors']['mass_kg']<=1e-14 for l in levels))
    except Exception as exc:
        output['pass']=False;output['failure']={'type':type(exc).__name__,'message':str(exc)}
    finally:
        if rows:
            with stem.with_suffix('.csv').open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
            output['trajectory_csv_sha256']=sha256(stem.with_suffix('.csv').read_bytes()).hexdigest()
        stem.with_suffix('.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
        print(json.dumps(output,indent=2,allow_nan=False))
    if not output['pass']:raise SystemExit(1)


if __name__=='__main__':main()
