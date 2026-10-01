"""One fixed scientific data job for initial-partition algebra; no host calls."""
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
import sys
import time
import numpy as np


def analyze(root_file: Path) -> dict:
    started=time.monotonic(); root=json.loads(root_file.read_text()); project=root_file.parent
    case=root['public_reference_cases']['fixed_initial_partition']; p=lambda key:root['parameters'][key]['value']
    source=json.loads((project/case['saved_reference']).read_text()); before=json.loads((project/case['physical_input_root']).read_text())
    bp=lambda key:before['parameters'][key]['value']; saved=source['actual_initial_state']; initial=source['saved_numerical_samples'][0]; final=source['saved_numerical_samples'][-1]
    spec=importlib.util.spec_from_file_location('initial_partition_primitive',project/case['primitive']); primitive=importlib.util.module_from_spec(spec); spec.loader.exec_module(primitive)
    area=bp('geometry.area'); length=bp('geometry.half_thickness'); total_bulk=area*length; factor=p(case['arithmetic_factor_parameter']); eps=np.finfo(float).eps
    masses={'char':bp('atomic.C'),'water':2*bp('atomic.H')+bp('atomic.O')}
    initial_inventory={name:sum(values)/total_bulk for name,values in saved['actual_condensed_mol_by_cell'].items()}
    gas_density={name:sum(values)/total_bulk for name,values in saved['actual_gas_mol_by_cell'].items()}
    ext_names=list(final['reaction_extent_mol']); extent_density=np.array([sum(final['reaction_extent_mol'][name])/total_bulk for name in ext_names])
    elapsed_saved_s=final['time_s']-initial['time_s']; rate_density=extent_density/elapsed_saved_s
    phi=initial['porosity'][0]; temperature=initial['temperature_k'][0]; R=bp('reference.R')
    rows=[]; fixtures={}; numerical={}

    def record(name,actual,expected,scale,unit):
        a=np.asarray(actual); e=np.asarray(expected); residual=a-e; bound=factor*eps*np.asarray(scale)
        rows.append({'name':name,'unit':unit,'signed_residual':residual.tolist(),'arithmetic_bound':np.broadcast_to(bound,residual.shape).tolist(),'passed':bool(np.all(np.abs(residual)<=bound))})

    for fixture in case['fixtures']:
        name=fixture['id']
        if name=='invalid_composite':
            try:
                primitive.initial_partition(cells=fixture['invalid_cells'],half_thickness_m=fixture['invalid_half_thickness_m'],area_m2=fixture['invalid_area_m2'],profile=fixture['profile'],exterior_exponent=fixture['invalid_exponent'])
            except ValueError as error:
                fixtures[name]={'rejected':True,'exception':'ValueError','message':str(error),'scope':'One compound input rejected at the first violated precondition; individual invalid branches not separately exercised.'}
            else:
                fixtures[name]={'rejected':False}
            continue
        n=int(p(fixture['cells_parameter'])); geometry=primitive.initial_partition(cells=n,half_thickness_m=length,area_m2=area,profile=fixture['profile'],exterior_exponent=p(case['exponent_parameter']))
        volume=geometry['initial_bulk_m3']; widths=geometry['widths_m']; centers=geometry['centers_m']; faces=geometry['faces_m']
        scales=primitive.initial_cell_scales(volume,dry_density_kg_m3=bp('material.dry_density'),char_molar_mass_kg_mol=masses['char'],retention_kg_kg=bp('water.retention_scale'),water_molar_mass_kg_mol=masses['water'])
        inventory=np.column_stack([volume*d for d in initial_inventory.values()]); gas=np.column_stack([volume*d for d in gas_density.values()]); extent=volume[:,None]*extent_density; rates=volume[:,None]*rate_density
        encoded=primitive.extent_coordinates(extent,scales['chemical_scale_mol']); decoded=primitive.extent_inventory(encoded,scales['chemical_scale_mol'],reactions=len(ext_names))
        encoded_rate=primitive.extent_coordinates(rates,scales['chemical_scale_mol']); decoded_rate=primitive.extent_inventory(encoded_rate,scales['chemical_scale_mol'],reactions=len(ext_names))
        start=len(rows)
        record(name+'.face_coverage',faces[[0,-1]],[0,length],length,'m')
        record(name+'.width_sum',widths.sum(),length,length,'m')
        record(name+'.volume_sum',volume.sum(),total_bulk,total_bulk,'m3')
        record(name+'.half_width_center_distance',geometry['internal_center_distance_m'],(widths[:-1]+widths[1:])/2,length,'m')
        record(name+'.outer_half_width',length-centers[-1],widths[-1]/2,length,'m')
        record(name+'.dry_mass_density',scales['dry_mass_kg']/volume,bp('material.dry_density'),bp('material.dry_density'),'kg/m3')
        record(name+'.chemical_scale_density',scales['chemical_scale_mol']/volume,bp('material.dry_density')/masses['char'],bp('material.dry_density')/masses['char'],'mol/m3')
        rd=bp('water.retention_scale')*bp('material.dry_density')/masses['water']; record(name+'.retention_density',scales['retention_scale_mol']/volume,rd,rd,'mol/m3')
        record(name+'.species_density',inventory/volume[:,None],np.array(list(initial_inventory.values())),np.abs(np.array(list(initial_inventory.values()))),'mol/m3')
        pore=phi*volume; pressure=gas*R*temperature/pore[:,None]; pressure_ref=np.array(list(gas_density.values()))*R*temperature/phi
        record(name+'.ideal_partial_pressure_scaling',pressure,pressure_ref,np.abs(pressure_ref),'Pa')
        concentration_ratio=(gas/pore[:,None])/(np.array(list(gas_density.values()))/phi)
        record(name+'.same_density_mu_argument_only',concentration_ratio,1,np.ones_like(concentration_ratio),'1')
        record(name+'.independent_extent_roundtrip',decoded,extent,np.abs(extent),'mol')
        record(name+'.given_rate_axis_roundtrip',decoded_rate,rates,np.abs(rates),'mol/s')
        record(name+'.given_rate_per_chemical_scale',encoded_rate.reshape(len(ext_names),n).T,rate_density[None,:]/(bp('material.dry_density')/masses['char']),np.abs(rate_density)/(bp('material.dry_density')/masses['char']),'1/s')
        record(name+'.inventory_totals',inventory.sum(axis=0),total_bulk*np.array(list(initial_inventory.values())),np.abs(total_bulk*np.array(list(initial_inventory.values()))),'mol')
        record(name+'.dry_mass_total',scales['total_initial_dry_mass_kg'],total_bulk*bp('material.dry_density'),total_bulk*bp('material.dry_density'),'kg')

        # Artificial chemical-potential gradients with a positive diagonal
        # face mobility; this is not a reevaluation of actual MS/Darcy fluxes.
        mobility=p(case['synthetic_face_mobility_parameter']); amplitude=np.array(initial['direct_carbonation_affinity_j_mol'])[0]
        weights=np.array(list(gas_density.values())); weights=weights/weights.sum()
        mu=(1-centers[:,None]/length)*amplitude*weights[None,:]
        face=np.zeros((n+1,len(gas_density))); delta=mu[:-1]-mu[1:]
        face[1:-1]=mobility*area*delta/geometry['internal_center_distance_m'][:,None]
        face[-1]=mobility*area*mu[-1]/geometry['exterior_half_width_m']
        given_source=gas/elapsed_saved_s; storage=primitive.shared_face_balance(given_source,face)
        terms=np.abs(given_source).sum(axis=0)+np.abs(face).sum(axis=0)*2
        record(name+'.shared_molar_faces_telescope',storage.sum(axis=0),given_source.sum(axis=0)+face[0]-face[-1],terms,'mol/s')
        dissipation=float(np.sum(face[1:-1]*delta)/temperature)
        prescribed_T=temperature+(final['temperature_k'][-1]-temperature)*centers/length
        heat=np.zeros(n+1); conductivity=bp('thermal.conductivity')
        heat[1:-1]=area*conductivity*(prescribed_T[:-1]-prescribed_T[1:])/geometry['internal_center_distance_m']
        heat[-1]=area*conductivity*(prescribed_T[-1]-final['temperature_k'][-1])/geometry['exterior_half_width_m']
        energy_rate=primitive.shared_face_balance(np.zeros(n),heat)
        record(name+'.shared_heat_faces_telescope',energy_rate.sum(),heat[0]-heat[-1],2*np.abs(heat).sum(),'W')
        heat_entropy=float(np.sum(heat[1:-1]*(1/prescribed_T[1:]-1/prescribed_T[:-1])))
        fixtures[name]={'cells':n,'profile':fixture['profile'],'faces_m':faces.tolist(),'widths_m':widths.tolist(),'centers_m':centers.tolist(),'volume_m3':volume.tolist(),'minimum_width_m':float(widths.min()),'maximum_width_m':float(widths.max()),'signed_volume_residual_m3':float(volume.sum()-total_bulk),'positive_widths':bool(np.all(widths>0)),'given_positive_diagonal_face_mobility_mol2_J_m_s':mobility,'synthetic_internal_mu_face_entropy_W_K':dissipation,'synthetic_internal_heat_face_entropy_W_K':heat_entropy,'positive_synthetic_internal_face_dissipation':dissipation>=0 and heat_entropy>=0,'all_arithmetic_rows_passed':all(row['passed'] for row in rows[start:]),'array_axis':'cells first; encoded extent is reaction-first flat','full_host_thermodynamics_evaluated':False}
        numerical[name]={'geometry':geometry,'scales':scales,'inventory':inventory,'gas':gas,'extent':extent}
        if fixture['profile']=='uniform':
            oldV=area*length/n; record(name+'.old_scalar_volume_broadcast',volume,oldV,total_bulk,'m3')
            record(name+'.old_scalar_extent_encoding',encoded,(extent/(bp('material.dry_density')*oldV/masses['char'])).T.ravel(),np.abs(encoded),'1')
        fixtures[name]['all_arithmetic_rows_passed']=all(row['passed'] for row in rows[start:])
        fixtures[name]['synthetic_entropy_scope']='Internal faces only; the supplied outer boundary is included in storage telescoping but its reservoir entropy is not verified here.'

    coarse=numerical['quadratic12']; fine=numerical['quadratic24']; parents=fixtures['quadratic12']['cells']; ratio=fixtures['quadratic24']['cells']//parents
    record('nested.parent_faces',fine['geometry']['faces_m'][::ratio],coarse['geometry']['faces_m'],length,'m')
    for key,unit in [('inventory','mol'),('gas','mol'),('extent','mol')]:
        grouped=primitive.nested_extensive_sum(fine[key],parent_cells=parents); record('nested.'+key,grouped,coarse[key],np.abs(coarse[key]),unit)
    for key,unit in [('initial_bulk_m3','m3')]:
        grouped=primitive.nested_extensive_sum(fine['geometry'][key],parent_cells=parents); record('nested.'+key,grouped,coarse['geometry'][key],total_bulk,unit)
    for key,unit in [('dry_mass_kg','kg'),('chemical_scale_mol','mol'),('retention_scale_mol','mol')]:
        grouped=primitive.nested_extensive_sum(fine['scales'][key],parent_cells=parents); record('nested.'+key,grouped,coarse['scales'][key],np.abs(coarse['scales'][key]),unit)
    return {'schema':'P42_fixed_initial_partition_actual_invariants_v1','recorded_utc':datetime.now(timezone.utc).isoformat(),'identity':'Three given homogeneous synthetic algebra fixtures plus one compound invalid input; no resimulated P40 trajectory','fixture_count':len(fixtures),'fixtures':fixtures,'arithmetic_rows':rows,'arithmetic_factor_root_parameter':case['arithmetic_factor_parameter'],'all_arithmetic_rows_passed':all(row['passed'] for row in rows),'invalid_fixture_rejected':fixtures['invalid_composite']['rejected'],'synthetic_internal_face_dissipation_passed':all(v['positive_synthetic_internal_face_dissipation'] for k,v in fixtures.items() if k!='invalid_composite'),'input_species_names':list(initial_inventory),'input_gas_names':list(gas_density),'independent_extent_names':ext_names,'independent_extent_input':'Saved independently integrated final totals, homogenized as given synthetic extensive density. Not derived from inventories.','root_parameter_count':len(root['parameters']),'nominal_uniform_and_direct_configuration_changed':False,'original44_host_sources_changed':False,'new_model_instances_constitutive_transport_thermo_RHS_Jac_ODE_fit_UQ_recovery':0,'full_host_thermodynamics_admitted':False,'current_host_nonuniform_connected':False,'P40_mesh_or_phase_failure_reclassified':False,'whole_project_complete':False,'elapsed_analysis_s':time.monotonic()-started,'limitations':['Only declared algebra; complete chemical potentials/energy/surface/elastic/mechanical operators were not evaluated','Positive diagonal synthetic flux quadratic form is not actual MS/Darcy coupled qualification','No interpolation of T replaces energy or original peak contrast','No trajectory, source rate, direct mobility, process or real brick qualification']}


def analyze_uniform(root_file: Path) -> dict:
    """Only the failed encoding and four corrected uniform input checks."""
    started=time.monotonic(); root=json.loads(root_file.read_text()); project=root_file.parent
    addition=root['public_reference_cases']['fixed_initial_partition_uniform_appendix']; case=root['public_reference_cases'][addition['original_contract']]
    p=lambda key:root['parameters'][key]['value']; before=json.loads((project/case['physical_input_root']).read_text()); bp=lambda key:before['parameters'][key]['value']
    fixture=next(item for item in case['fixtures'] if item['id']==addition['original_fixture_id'])
    source=json.loads((project/case['saved_reference']).read_text()); final=source['saved_numerical_samples'][-1]
    spec=importlib.util.spec_from_file_location('initial_partition_primitive',project/case['primitive']); primitive=importlib.util.module_from_spec(spec); spec.loader.exec_module(primitive)
    n=int(p(fixture['cells_parameter'])); area=bp('geometry.area'); length=bp('geometry.half_thickness'); total_bulk=area*length; oldV=area*length/n; old_md=bp('material.dry_density')*oldV; old_scale=old_md/bp('atomic.C')
    geometry=primitive.initial_partition(cells=n,half_thickness_m=length,area_m2=area,profile=fixture['profile'],exterior_exponent=p(case['exponent_parameter']))
    scales=primitive.initial_cell_scales(geometry['initial_bulk_m3'],dry_density_kg_m3=bp('material.dry_density'),char_molar_mass_kg_mol=bp('atomic.C'),retention_kg_kg=bp('water.retention_scale'),water_molar_mass_kg_mol=2*bp('atomic.H')+bp('atomic.O'))
    ext_names=list(final['reaction_extent_mol']); extent_density=np.array([sum(final['reaction_extent_mol'][name])/total_bulk for name in ext_names]); extent=geometry['initial_bulk_m3'][:,None]*extent_density
    encoded=primitive.extent_coordinates(extent,scales['chemical_scale_mol']); factor=p(case['arithmetic_factor_parameter']); eps=np.finfo(float).eps; rows=[]

    def record(name,actual,expected,scale,unit):
        a=np.asarray(actual); e=np.asarray(expected); residual=a-e; bound=factor*eps*np.asarray(scale)
        rows.append({'name':name,'unit':unit,'signed_residual':residual.tolist(),'arithmetic_bound':np.broadcast_to(bound,residual.shape).tolist(),'passed':bool(np.all(np.abs(residual)<=bound))})

    name=fixture['id']
    record(name+'.old_scalar_width_broadcast',geometry['widths_m'],length/n,length,'m')
    record(name+'.old_scalar_volume_broadcast',geometry['initial_bulk_m3'],oldV,total_bulk,'m3')
    record(name+'.old_scalar_md_broadcast',scales['dry_mass_kg'],old_md,old_md,'kg')
    record(name+'.old_scalar_chemical_scale_broadcast',scales['chemical_scale_mol'],old_scale,old_scale,'mol')
    record(name+'.old_scalar_extent_encoding',encoded,(extent/(bp('material.dry_density')*oldV/bp('atomic.C'))).T.ravel(),np.abs(encoded),'1')
    return {'schema':'P42_explicit_affected_uniform_actual_rows_v1','recorded_utc':datetime.now(timezone.utc).isoformat(),'identity':'Explicit second science job in new added window; corrected uniform inputs and original failed encoding only','fixture_ids_evaluated':[name],'arithmetic_rows':rows,'all_arithmetic_rows_passed':all(row['passed'] for row in rows),'arithmetic_factor_root_parameter':case['arithmetic_factor_parameter'],'original_failed_row_definition_unchanged':True,'original_physical_input_and_old_scalar_definition_unchanged':True,'rows_not_repeated':'Original63 passed rows retained separately except old volume compatibility rechecked because affected input changed. No quadratic/invalid/nesting/roundtrip/pressure/shared-face/dissipation validation repeated.','independent_extent_names':ext_names,'independent_extent_input':'Given homogeneous density from saved independently integrated final extent totals, not reconstructed from inventory','current_uniform_input_volume_m3':geometry['initial_bulk_m3'].tolist(),'current_uniform_width_m':geometry['widths_m'].tolist(),'old_scalar_volume_m3':oldV,'old_scalar_width_m':length/n,'old_scalar_dry_mass_kg':old_md,'old_scalar_chemical_scale_mol':old_scale,'root_parameter_count':len(root['parameters']),'new_model_instances_constitutive_transport_thermo_RHS_Jac_ODE_fit_UQ_recovery':0,'full_host_thermodynamics_admitted':False,'host_nonuniform_connected':False,'original_closed_window_failure_reclassified':False,'whole_project_complete':False,'elapsed_analysis_s':time.monotonic()-started}


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[3]=='--uniform-only':
        result=analyze_uniform(Path(sys.argv[1])); passed=result['all_arithmetic_rows_passed']
    elif len(sys.argv)==3:
        result=analyze(Path(sys.argv[1])); passed=result['all_arithmetic_rows_passed'] and result['invalid_fixture_rejected'] and result['synthetic_internal_face_dissipation_passed']
    else:
        raise ValueError('Arguments: ROOT OUTPUT [--uniform-only]')
    Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    if not passed:raise SystemExit(1)
