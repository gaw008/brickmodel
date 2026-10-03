"""Paired explicitly selected original interval and saved-reference sampled peak comparison.

This independent producer preserves the original loader and constitutive code.
Its bounded numerical run is separately adopted. No prefix, initial state or
historical baseline peak is reconstructed. The output is a comparison bundle
with shared case references, not the unchanged loader's checkpoint schema.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import numpy as np

from .full_cycle import write_json
from .full_cycle_checkpoint import load_native_checkpoint, _source_text
from .full_cycle_cooling_hold_comparison import endpoint_products, product_comparison
from .full_cycle_endpoint_ledgers import endpoint_inventory, interval_ledger
from .full_cycle_gas import solve_ivp


def compare_sintering_time(parameters: Path, out: Path, *, contract_key: str):
    """Two strict loads, original BDF solves, sampled spans and endpoint ledgers."""
    started = time.monotonic()
    root = json.loads(parameters.read_text())
    contract = root[contract_key]
    project_root = parameters.resolve().parent
    checkpoint = project_root/contract['checkpoint_input']
    inventory_path = project_root/contract['inventory_input']
    saved_inventory = json.loads(inventory_path.read_text())
    points = {point['stage']:point for point in saved_inventory['points']}
    start_point = deepcopy(points[contract['input_stage']])
    start_point['native_y'] = np.asarray(start_point['native_y'], dtype=float)
    reference = points[root['endpoint_ledger_export']['initial_reference_label']]
    out.mkdir(parents=True, exist_ok=True)
    case_file = out/contract['case_output_filename']
    output_file = out/contract['output_filename']
    cases = {'original_root_scientific_identity':{key:root[key] for key in contract['root_scientific_identity_keys']},
        'root_reference':{'path':str(parameters.resolve()),'full_bytes':parameters.stat().st_size},
        'original_saved_config':None,'effective_cases':{},'numerical_conditions':{}}
    bundle = {'schema':contract['schema'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'selected_contract_key':contract_key,'contract_reference':str(parameters.resolve())+'#/'+contract_key,
        'case_file_reference':str(case_file.resolve()),'source_version':None,'context':None,
        'input_source_identity':None,'resume_origin':None,'sample_times_s':None,
        'inventory_reference':{'path':str(inventory_path.resolve()),'full_bytes':inventory_path.stat().st_size,
            'initial_reference_basis':saved_inventory['initial_reference_basis'],
            'start_inventory_provenance':start_point['provenance'],
            'start_and_reference_decode_or_value_recomputed':False},
        'cases':[],'paired_comparison_completed':False,'prefix_completed':False,'full_cycle_completed':False,
        'criterion':'criterion_not_applicable','whole_model_complete':False,
        'operation_scope':contract['scope_limits'],'units':contract['units']}
    write_json(case_file,cases)
    write_json(output_file,bundle)
    for case_name, case_rule in contract['cases'].items():
        model, start_s, state, inherited = load_native_checkpoint(checkpoint,stage=contract['input_stage'])
        saved_config = deepcopy(inherited['config'])
        effective = deepcopy(saved_config)
        condition = None
        if case_rule['condition_key'] is not None:
            condition = root['conditional_numerical_conditions'][case_rule['condition_key']]
            effective['parameters'][condition['target_parameter']] = deepcopy(condition['record'])
            effective['conditional_numerical_conditions'] = {case_rule['condition_key']:deepcopy(condition)}
        effective[contract_key] = deepcopy(contract)
        effective['native_checkpoint']['source_paths'] = list(contract['output_source_paths'])
        effective['native_checkpoint']['implementation_parent_revision'] = contract['implementation_parent_revision']
        model.config = effective
        stage_index = saved_config['stages'].index(contract['output_stage'])
        end_s = float(model.times[stage_index+1])
        global_times = np.unique(np.r_[np.arange(model.times[0],model.times[-1],
            model.p('numerics.output_step','s')),model.times])
        sample_times = global_times[(global_times >= start_s) & (global_times <= end_s)]
        numerical = {'original_record':saved_config['parameters']['numerics.max_step'],
            'effective_record':effective['parameters']['numerics.max_step'],
            'condition_key':case_rule['condition_key'],
            'condition_declaration_reference':None if condition is None else
                str(parameters.resolve())+'#conditional_numerical_conditions/'+case_rule['condition_key'],
            'changed_complete_records':[key for key,value in effective['parameters'].items()
                if value != saved_config['parameters'][key]],
            'max_step_s':model.p('numerics.max_step','s'),
            'rtol_record':effective['parameters']['numerics.rtol'],
            'atol_record':effective['parameters']['numerics.atol']}
        if cases['original_saved_config'] is None:
            cases['original_saved_config'] = saved_config
            bundle.update(source_version={'implementation_parent_revision':contract['implementation_parent_revision'],
                    'identity_basis':contract['source_identity_rule'],'source_text':_source_text(effective)},
                context=inherited['context'],
                input_source_identity={'path':str(checkpoint.resolve()),'full_bytes':checkpoint.stat().st_size,
                    'source_paths':saved_config['native_checkpoint']['source_paths'],
                    'saved_identity_basis':inherited['source_version']['identity_basis'],
                    'complete_input_source_text_reference':contract['input_source_text_reference'],
                    'strict_loader_changed':False},
                resume_origin={'stage':contract['input_stage'],'time_s':start_s,'native_y':state.copy(),
                    'basis':'Exact actual saved '+contract['checkpoint_input']+' '+contract['input_stage']+' checkpoint; references and cumulative origins retained.'},
                sample_times_s=sample_times)
        cases['effective_cases'][case_name] = effective
        cases['numerical_conditions'][case_name] = numerical
        write_json(case_file,cases)
        write_json(output_file,bundle)
        rhs_before,jac_before = model.rhs_calls,model.jacobian_calls
        solve_started = time.monotonic()
        solution = solve_ivp(model.rhs,(start_s,end_s),state,method=contract['solver_method'],
            jac=model.jacobian,t_eval=sample_times,max_step=model.p('numerics.max_step','s'),
            rtol=model.p('numerics.rtol','1'),atol=model.p('numerics.atol','1'))
        if not solution.success:
            raise RuntimeError(f"{case_name} {contract['output_stage']}: {solution.message}")
        solver_wall = time.monotonic()-solve_started
        sampled_native = solution.y.T.copy()
        solver_t0_native = sampled_native[0].copy()
        solver_t0_minus_actual_input = sampled_native[0]-state
        sampled_native[0] = state
        cell_temperatures = sampled_native[:,:model.n]*model.Tr
        surface_temperatures,center_temperatures,spans = [],[],[]
        for time_s,row,temperature in zip(sample_times,sampled_native,cell_temperatures):
            event = model.rates(float(time_s),row)
            surface = float(event['surface_T'])
            center = model.center_temperature(temperature)
            span = max(float(temperature.max()),surface,center)-min(float(temperature.min()),surface,center)
            surface_temperatures.append(surface)
            center_temperatures.append(center)
            spans.append(span)
        endpoint = solution.y[:,-1].copy()
        point = endpoint_inventory(model,contract['output_stage'],float(solution.t[-1]),endpoint,
            provenance={'kind':'actual_paired_'+contract['output_stage']+'_saved_solver_endpoint','case':case_name,
                'numerical_condition_reference':'case-parameters.json#/numerical_conditions/'+case_name},
            contract=root['endpoint_ledger_export'])
        ledger = interval_ledger(model,[start_point,point],reference,root['endpoint_ledger_export'],
            name=contract['output_stage'],evidence_basis=contract['reference_qualification'])
        products = endpoint_products(point,reference,effective['parameters'])
        products[contract['peak_product_key']] = max(spans)
        peak_index = int(np.argmax(spans))
        case = {'case':case_name,'effective_config_reference':'case-parameters.json#/effective_cases/'+case_name,
            'numerical_condition_reference':'case-parameters.json#/numerical_conditions/'+case_name,
            'start_time_s':start_s,'end_time_s':float(solution.t[-1]),
            'sample_times_reference':'#/sample_times_s','cell_temperature_k':cell_temperatures,
            'surface_temperature_k':surface_temperatures,'center_temperature_k':center_temperatures,
            'temperature_span_k':spans,'sampled_peak':{'span_k':max(spans),
                'sample_index':peak_index,'time_s':float(sample_times[peak_index]),'definition':contract['peak_definition']},
            'actual_solver_t0_native_y':solver_t0_native,
            'actual_solver_t0_basis':'Exact complete sol.y[:,0], separately retained; not reconstructed from input plus delta.',
            'solver_t0_minus_actual_input_native':solver_t0_minus_actual_input,
            'sample_zero_basis':'Exact supplied native checkpoint; signed solver t0 roundtrip retained separately.',
            'endpoint_inventory':point,'interval_ledger':ledger,'products':products,
            'solver':{'method':contract['solver_method'],'success':solution.success,'message':solution.message,
                'nfev':solution.nfev,'njev':solution.njev,'nlu':solution.nlu,'solver_wall_seconds':solver_wall,
                'actual_rhs_calls_including_jacobian':model.rhs_calls-rhs_before,
                'actual_jacobian_calls':model.jacobian_calls-jac_before},
            'completed_production_calls':{'strict_checkpoint_load':1,'logical_constructor':1,'native_initial_state':0,
                'original_BDF_solve':1,'endpoint_decode':1,'complete_potential_values':model.potential_value_calls,
                'endpoint_interval_ledger':1,'public_sample_rates':len(spans),
                'center_temperature_helper':len(center_temperatures),'baseline_reference_decode_value_summary':0},
            'existing_potential_helper_counters':dict(model.potential_helper_calls)}
        bundle['cases'].append(case)
        write_json(output_file,bundle)
    indexed = {case['case']:case for case in bundle['cases']}
    coarse = indexed[contract['coarse_case_key']]
    refined = indexed[contract['refined_case_key']]
    differences = product_comparison(coarse['products'],refined['products'],root['parameters'],contract)
    bundle.update(paired_comparison_completed=True,signed_product_comparisons=differences,
        local_four_product_difference_below_threshold=all(row['below_original_local_difference_threshold']
            for row in differences.values()),
        strict_nonnegative_inventories={case['case']:{key:case['endpoint_inventory'][key]
            for key in ['strict_nonnegative_inventories','minimum_condensed_inventory_mol','minimum_gas_inventory_mol']}
            for case in bundle['cases']},
        original_saved_t0_shrinkage={'available':False,'coarse':None,'refined':None,
            'reason':contract['original_t0_qualification']},
        counter_qualification=contract['counter_qualification'],
        uninstrumented_internal_calls=contract['source_only_forecast'],
        elapsed_since_comparison_start_s=time.monotonic()-started)
    write_json(output_file,bundle)
    return {'output':str(output_file),'case_output':str(case_file),'paired_comparison_completed':True,
        'completed_production_calls':[case['completed_production_calls'] for case in bundle['cases']],
        'signed_product_comparisons':differences,'criterion':'criterion_not_applicable','whole_model_complete':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract',required=True,help='Explicit root comparison contract key')
    args = parser.parse_args()
    print(json.dumps(compare_sintering_time(args.parameters,args.out,contract_key=args.contract),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
