"""One original final cooling_hold solve and stored-inventory product comparison.

This additive producer leaves the strict loader and all original53 files intact.
Its numerical execution requires a separately adopted bounded plan. No historical
trajectory, baseline potential, or initial reference is recomputed here.
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
from .full_cycle_endpoint_ledgers import endpoint_inventory, interval_ledger
from .full_cycle_gas import solve_ivp


def endpoint_products(point, reference, parameters):
    """Original product reductions on existing arrays; shrinkage is conditional.

    Original porosity uses final bulk-volume weights. Original carbon is global
    kg of elemental C in organic plus char, with signed inventories retained.
    The shared P78 initial bulk is a new declared reference, not recovered t0.
    """
    bulk = np.asarray(point['bulk_m3'])
    pore = np.asarray(point['native_pore_m3'])
    organic = np.asarray(point['condensed_inventory_mol']['organic'])
    char = np.asarray(point['condensed_inventory_mol']['char'])
    carbon = (organic+char)*parameters['atomic.C']['value']
    initial_bulk = np.asarray(reference['bulk_m3'])
    return {'porosity':float(np.average(pore/bulk, weights=bulk)),
            'residual_carbon_kg':float(sum(carbon.tolist())),
            'shrinkage':float(1-bulk.sum()/initial_bulk.sum())}


def product_comparison(coarse, refined, parameters, contract):
    """Preserve raw signs and use exactly the original convergence denominators."""
    threshold = parameters[contract['convergence_threshold_parameter']]['value']
    rows = {}
    for name, rule in contract['products'].items():
        floor = parameters[rule['denominator_floor_parameter']]
        denominator = max(abs(refined[name]), floor['value'])
        difference = refined[name]-coarse[name]
        relative = abs(difference)/denominator
        rows[name] = {'coarse_raw':coarse[name], 'refined_raw':refined[name],
            'signed_refined_minus_coarse':difference, 'unit':rule['unit'],
            'denominator':denominator, 'denominator_floor_record':floor,
            'denominator_source':rule['denominator_floor_parameter'],
            'denominator_rule':contract['denominator_rule'],
            'absolute_relative_difference':relative, 'threshold':threshold,
            'below_original_local_difference_threshold':bool(relative < threshold),
            'availability':rule['availability'], 'reference_basis':rule['reference_basis']}
    return rows


def compare_final_cooling_hold(parameters: Path, out: Path):
    """One strict53 load, original solve, one new decode/value/interval only."""
    started = time.monotonic()
    root = json.loads(parameters.read_text())
    contract = root['cooling_hold_comparison']
    project_root = parameters.resolve().parent
    checkpoint = project_root/contract['checkpoint_input']
    baseline_path = project_root/contract['baseline_ledger_input']
    baseline = json.loads(baseline_path.read_text())
    points = {point['stage']:point for point in baseline['points']}
    reference = points[root['endpoint_ledger_export']['initial_reference_label']]
    coarse_point = points[contract['output_stage']]
    coarse_ledger = {row['name']:row for row in baseline['intervals']}[contract['output_stage']]

    model, start_s, state, inherited = load_native_checkpoint(checkpoint, stage=contract['input_stage'])
    start_point = deepcopy(inherited['refined_endpoint_inventory'])
    start_point['native_y'] = np.asarray(start_point['native_y'], dtype=float)
    stage_index = inherited['config']['stages'].index(contract['output_stage'])
    end_s = float(model.times[stage_index+1])
    saved_case = deepcopy(inherited['config'])
    effective = deepcopy(saved_case)
    condition = root['conditional_numerical_conditions'][contract['condition_key']]
    effective['parameters'][condition['target_parameter']] = deepcopy(condition['record'])
    effective['conditional_numerical_conditions'][contract['condition_key']] = deepcopy(condition)
    effective['cooling_hold_comparison'] = deepcopy(contract)
    effective['native_checkpoint']['source_paths'] = list(contract['output_source_paths'])
    effective['native_checkpoint']['implementation_parent_revision'] = contract['implementation_parent_revision']
    model.config = effective
    max_step = model.p(condition['target_parameter'], 's')
    original_sixty_case = inherited['original_saved_case']['config']
    numerical_condition = {'condition_key':contract['condition_key'], 'target_parameter':condition['target_parameter'],
        'loaded_P80_record':saved_case['parameters'][condition['target_parameter']],
        'original_60s_record':original_sixty_case['parameters'][condition['target_parameter']],
        'effective_final_stage_record':effective['parameters'][condition['target_parameter']],
        'declaration_source':str(parameters.resolve())+'#conditional_numerical_conditions/'+contract['condition_key'],
        'solver_max_step_s':max_step,
        'changed_complete_records_from_loaded_P80':[key for key, value in effective['parameters'].items()
                                                   if value != saved_case['parameters'][key]],
        'changed_numeric_values_from_loaded_P80':[key for key, value in effective['parameters'].items()
                                                 if value['value'] != saved_case['parameters'][key]['value']],
        'changed_complete_records_from_original_60s':[key for key, value in effective['parameters'].items()
                                                     if value != original_sixty_case['parameters'][key]]}
    case_file = out/contract['case_output_filename']
    output_file = out/contract['output_filename']
    out.mkdir(parents=True, exist_ok=True)
    write_json(case_file, {
        'original_root_scientific_identity':{key:root[key] for key in contract['root_scientific_identity_keys']},
        'original_root_reference':{'path':str(parameters.resolve()),'full_bytes':parameters.stat().st_size},
        'P80_loaded_saved_case':saved_case,
        'P80_original_60s_case':inherited['original_saved_case'],
        'effective_final_stage_case':effective,
        'numerical_condition':numerical_condition})
    bundle = {'schema':effective['native_checkpoint']['schema'],
        'comparison_schema':contract['schema'], 'created_utc':datetime.now(timezone.utc).isoformat(),
        'case_reference':contract['effective_case_identity'], 'config':effective,
        'source_version':{'implementation_parent_revision':contract['implementation_parent_revision'],
            'identity_basis':contract['source_identity_rule'], 'source_text':_source_text(effective)},
        'input_source_identity':{
            'path':str(checkpoint.resolve()),'full_bytes':checkpoint.stat().st_size,
            'source_paths':inherited['config']['native_checkpoint']['source_paths'],
            'saved_source_identity_basis':inherited['source_version']['identity_basis'],
            'complete_input53_source_text_reference':contract['input_source_text_reference'],
            'strict_loader_changed':False},
        'baseline_reference':{'path':str(baseline_path.resolve()),'full_bytes':baseline_path.stat().st_size,
            'initial_reference_basis':baseline['initial_reference_basis'],
            'coarse_final_provenance':coarse_point['provenance'],
            'coarse_or_reference_decode_or_value_recomputed':False},
        'case_file_reference':str(case_file.resolve()), 'numerical_condition':numerical_condition,
        'context':inherited['context'], 'stop_stage':contract['output_stage'],
        'full_declared_stage_list':saved_case['stages'],
        'resume_origin':{'stage':contract['input_stage'],'time_s':start_s,'native_y':state.copy(),
            'basis':'Actual complete P80 refined cooling state and cumulative origins; no reset or coordinate mapping.'},
        'endpoints':[], 'continuation_completed':False, 'prefix_completed':False,
        'full_cycle_completed':False,'criterion':'criterion_not_applicable','whole_model_complete':False,
        'operation_scope':contract['scope_limits']}
    write_json(output_file,bundle)
    rhs_before, jac_before = model.rhs_calls, model.jacobian_calls
    solution = solve_ivp(model.rhs,(start_s,end_s),state,method=contract['solver_method'],jac=model.jacobian,
        t_eval=np.asarray([end_s]),max_step=max_step,
        rtol=model.p('numerics.rtol','1'),atol=model.p('numerics.atol','1'))
    if not solution.success:
        raise RuntimeError(f"{contract['output_stage']}: {solution.message}")
    endpoint = solution.y[:,-1].copy()
    temperature = endpoint[:model.n]*model.Tr
    solver = {'method':contract['solver_method'],'success':solution.success,'message':solution.message,
        'nfev':solution.nfev,'njev':solution.njev,'nlu':solution.nlu,'max_step_s':max_step,
        'actual_rhs_calls_including_jacobian':model.rhs_calls-rhs_before,
        'actual_jacobian_calls':model.jacobian_calls-jac_before,
        'elapsed_since_comparison_start_s':time.monotonic()-started,
        'history':'Fresh BDF history for original final cooling_hold; all native state, references and absolute clock retained.'}
    bundle['endpoints'].append({'stage':contract['output_stage'],'time_s':float(solution.t[-1]),
        'native_y':endpoint,'native_y_basis':'Exact complete sol.y[:,-1]; signed raw inventories preserved.',
        'temperature_k':temperature,'solver':solver,
        'branch_provenance':{'quartz_shomate_alpha':temperature.real < model.tc,
            'kinetic_liquid':model.kinetic_liquid,'direct_carbonation_enabled':model.direct_carbonation_enabled,
            'calcium_coordinate_mode':model.calcium_coordinate_mode,
            'caloric_source_domains':effective['caloric_background'],
            'viscosity_background':effective['viscosity_background'],
            'binary_diffusion_background':effective['binary_diffusion_background'],
            'scope':'Actual final endpoint only; no unsaved path or material qualification.'}})
    refined_point = endpoint_inventory(model,contract['output_stage'],float(solution.t[-1]),endpoint,
        provenance={'kind':'actual_refined_final_saved_solver_endpoint','numerical_condition':numerical_condition},
        contract=root['endpoint_ledger_export'])
    refined_ledger = interval_ledger(model,[start_point,refined_point],reference,root['endpoint_ledger_export'],
        name=contract['output_stage'],evidence_basis=contract['reference_qualification'])
    coarse_products = endpoint_products(coarse_point,reference,effective['parameters'])
    refined_products = endpoint_products(refined_point,reference,effective['parameters'])
    differences = product_comparison(coarse_products,refined_products,effective['parameters'],contract)
    bundle.update(continuation_completed=True,refined_endpoint_inventory=refined_point,
        coarse_saved_final_interval=coarse_ledger,refined_final_interval=refined_ledger,
        coarse_final_products=coarse_products,refined_final_products=refined_products,
        signed_final_product_comparisons=differences,
        local_three_product_difference_below_threshold=all(row['below_original_local_difference_threshold'] for row in differences.values()),
        original_saved_t0_shrinkage={'available':False,'coarse':None,'refined':None,
            'reason':contract['original_t0_qualification']},
        strict_nonnegative_inventories={'coarse':coarse_point['strict_nonnegative_inventories'],
            'refined':refined_point['strict_nonnegative_inventories'],
            'coarse_minimum_condensed_mol':coarse_point['minimum_condensed_inventory_mol'],
            'refined_minimum_condensed_mol':refined_point['minimum_condensed_inventory_mol'],
            'qualification':'Independent domain result; no clipping, seeding, floor or local difference pass repairs negative inventories.'},
        full_time_grid_peak_qualification='not_evaluated_by_this_two_cooling_stage_comparison',
        existing_potential_helper_counters=dict(model.potential_helper_calls),
        completed_production_calls={'saved_checkpoint_load':1,'make_cycle':1,'native_initial_state':0,
            'solve_ivp_completed':1,'native_refined_endpoint':1,'native_potential_state':1,
            'complete_potential_values':model.potential_value_calls,'endpoint_interval_ledger':1,
            'baseline_potential_reevaluations':0,'initial_reference_reevaluations':0,
            'stored_inventory_product_arithmetic':2,
            'native_RHS_counter':model.rhs_calls,'native_Jacobian_counter':model.jacobian_calls,
            'extra_public_rates':0,'state_dynamics':0,'instantaneous_projection':0,
            'potential_gradient_directions':0,'trajectory_summary':0,'predict':0,'fit':0,'UQ':0},
        counter_qualification=contract['counter_qualification'],
        uninstrumented_internal_calls=contract['source_only_forecast'])
    write_json(output_file,bundle)
    return {'output':str(output_file),'case_output':str(case_file),'start_time_s':start_s,'end_time_s':float(solution.t[-1]),
        'completed_production_calls':bundle['completed_production_calls'],
        'signed_final_product_comparisons':differences,
        'refined_interval_endpoint_balance_passed':refined_ledger['endpoint_balance_passed'],
        'criterion':'criterion_not_applicable','whole_model_complete':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(compare_final_cooling_hold(args.parameters,args.out),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
