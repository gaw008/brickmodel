"""One declared cooling timestep comparison from an actual saved hold endpoint.

The original strict loader restores the saved physical case and context first.
Only the root-declared conditional numerical record changes the effective
max_step. Baseline inventories and potentials remain previously saved data.
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


def residual_comparison(coarse, refined):
    """Preserve each original denominator and every signed comparison."""
    a = coarse['absolute_relative_residual']
    b = refined['absolute_relative_residual']
    change = b-a if a is not None and b is not None else None
    relation = ('lower' if change < 0 else 'higher' if change > 0 else 'unchanged') if change is not None else 'undefined_relative_comparison'
    return {'coarse':coarse, 'refined':refined,
            'signed_residual_change':refined['signed_residual']-coarse['signed_residual'],
            'absolute_residual_change':abs(refined['signed_residual'])-abs(coarse['signed_residual']),
            'absolute_relative_residual_change':change, 'relative_relation':relation,
            'criterion':'criterion_not_applicable',
            'qualification':'No required monotonic improvement; local existing ledger verdicts remain separate from timestep convergence and full-cycle acceptance.'}


def refine_cooling_endpoint(parameters: Path, checkpoint: Path, baseline_ledgers: Path, out: Path):
    """One strict load, one original cooling solve, one new decode/value/ledger."""
    started = time.monotonic()
    root = json.loads(parameters.read_text())
    contract = root['cooling_time_refinement']
    condition = root['conditional_numerical_conditions'][contract['condition_key']]
    baseline = json.loads(baseline_ledgers.read_text())
    points = {point['stage']:point for point in baseline['points']}
    hold = deepcopy(points[contract['input_stage']])
    # JSON stores ordinary lists. Only this array boundary is restored; the
    # saved hold inventory, complete potential and context are not reevaluated.
    hold['native_y'] = np.asarray(hold['native_y'], dtype=float)
    initial_reference = points[root['endpoint_ledger_export']['initial_reference_label']]
    coarse_point = points[contract['output_stage']]
    coarse_ledger = {row['name']:row for row in baseline['intervals']}[contract['output_stage']]

    model, start_s, state, inherited = load_native_checkpoint(checkpoint, stage=contract['input_stage'])
    stage_index = inherited['config']['stages'].index(contract['output_stage'])
    end_s = float(model.times[stage_index+1])
    saved_case = deepcopy(inherited['config'])
    effective = deepcopy(saved_case)
    effective['parameters'][condition['target_parameter']] = deepcopy(condition['record'])
    effective['cooling_time_refinement'] = deepcopy(contract)
    effective['conditional_numerical_conditions'] = {contract['condition_key']:deepcopy(condition)}
    effective['native_checkpoint']['source_paths'] = list(dict.fromkeys([
        *saved_case['native_checkpoint']['source_paths'],
        root['endpoint_ledger_export']['producer_source_path'], contract['producer_source_path']]))
    effective['native_checkpoint']['implementation_parent_revision'] = contract['implementation_parent_revision']
    # p() reads model.config. Solver and complete saved computation config now
    # share the exact same conditional record; constructor/context stay saved.
    model.config = effective
    max_step_s = model.p(condition['target_parameter'], 's')
    ledger_contract = root['endpoint_ledger_export']
    path = out/contract['output_filename']
    numerical_difference = {
        'parameter':condition['target_parameter'],
        'original_saved_record':saved_case['parameters'][condition['target_parameter']],
        'effective_conditional_record':effective['parameters'][condition['target_parameter']],
        'conditional_record_source':str(parameters.resolve())+'#conditional_numerical_conditions/'+contract['condition_key'],
        'solver_max_step_s':max_step_s,
        'changed_parameter_records':[name for name,item in effective['parameters'].items()
            if item != saved_case['parameters'][name]],
        'effective_config_basis':'Exact saved P75 physical case with only the explicit conditional numerical record applied after strict restoration. Administrative/source provenance is added separately.'}
    bundle = {
        'schema':effective['native_checkpoint']['schema'],
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'case_reference':contract['effective_case_identity'], 'config':effective,
        'original_saved_case':{'checkpoint_reference':str(checkpoint.resolve()),
            'full_input_bytes':checkpoint.stat().st_size, 'case_reference':inherited['case_reference'],
            'config':saved_case, 'source_identity':inherited['inherited_source_identity'],
            'source_version':{'implementation_parent_revision':inherited['source_version']['implementation_parent_revision'],
                'identity_basis':inherited['source_version']['identity_basis'],
                'source_paths':saved_case['native_checkpoint']['source_paths']}},
        'source_version':{
            'implementation_parent_revision':contract['implementation_parent_revision'],
            'identity_basis':'All unchanged historical51 model/loader source texts plus the independent ledger52 and refinement53 producers; original input identity remains separate and strict.',
            'source_text':_source_text(effective)},
        'numerical_condition':numerical_difference,
        'context':inherited['context'], 'stop_stage':contract['output_stage'],
        'full_declared_stage_list':saved_case['stages'],
        'resume_origin':{'stage':contract['input_stage'],'time_s':start_s,'native_y':state.copy(),
            'basis':'Exact saved actual hold y and original cumulative/context references; no initial reset or prefix replay.'},
        'baseline_reference':{'path':str(baseline_ledgers.resolve()),'full_input_bytes':baseline_ledgers.stat().st_size,
            'initial_reference_basis':baseline['initial_reference_basis'],
            'hold_provenance':hold['provenance'],'coarse_cooling_provenance':coarse_point['provenance'],
            'qualification':contract['reference_qualification']},
        'endpoints':[], 'continuation_completed':False, 'prefix_completed':False,
        'full_cycle_completed':False, 'criterion':'criterion_not_applicable', 'whole_model_complete':False,
        'operation_scope':contract['scope_limits']}
    out.mkdir(parents=True, exist_ok=True)
    write_json(out/'case-parameters.json', effective)
    write_json(path, bundle)

    rhs_before, jac_before = model.rhs_calls, model.jacobian_calls
    solution = solve_ivp(model.rhs, (start_s, end_s), state,
        method=contract['solver_method'], jac=model.jacobian, t_eval=np.asarray([end_s]),
        max_step=max_step_s, rtol=model.p('numerics.rtol','1'), atol=model.p('numerics.atol','1'))
    if not solution.success:
        raise RuntimeError(f"{contract['output_stage']}: {solution.message}")
    endpoint = solution.y[:,-1].copy()
    temperature = endpoint[:model.n]*model.Tr
    solver = {'method':contract['solver_method'],'success':solution.success,'message':solution.message,
        'nfev':solution.nfev,'njev':solution.njev,'nlu':solution.nlu,'max_step_s':max_step_s,
        'actual_rhs_calls_including_jacobian':model.rhs_calls-rhs_before,
        'actual_jacobian_calls':model.jacobian_calls-jac_before,
        'elapsed_since_refinement_start_s':time.monotonic()-started,
        'history':'Fresh BDF history only for the original cooling interval; existing native equations and absolute-time boundary/gas programs remain unchanged.'}
    bundle['endpoints'].append({'stage':contract['output_stage'],'time_s':float(solution.t[-1]),
        'native_y':endpoint,'native_y_basis':'Exact complete sol.y[:,-1]; no clipping, seed or coordinate remapping.',
        'temperature_k':temperature,'solver':solver,
        'branch_provenance':{'quartz_shomate_alpha':temperature.real < model.tc,
            'kinetic_liquid':model.kinetic_liquid,'direct_carbonation_enabled':model.direct_carbonation_enabled,
            'calcium_coordinate_mode':model.calcium_coordinate_mode,
            'caloric_source_domains':effective['caloric_background'],
            'viscosity_background':effective['viscosity_background'],
            'binary_diffusion_background':effective['binary_diffusion_background'],
            'scope':'One actual refined endpoint, not continuous-path/source-domain or material qualification.'}})
    refined_point = endpoint_inventory(model,contract['output_stage'],float(solution.t[-1]),endpoint,
        provenance={'kind':'actual_refined_saved_solver_endpoint','numerical_condition':numerical_difference},
        contract=ledger_contract)
    refined_ledger = interval_ledger(model,[hold,refined_point],initial_reference,ledger_contract,
        name=contract['output_stage'],evidence_basis=contract['reference_qualification'])
    comparisons = {
        'mass':residual_comparison(coarse_ledger['mass'],refined_ledger['mass']),
        'elements':{name:residual_comparison(coarse_ledger['elements'][name],refined_ledger['elements'][name]) for name in model.elements},
        'complete_energy':residual_comparison(coarse_ledger['complete_energy'],refined_ledger['complete_energy']),
        'entropy':residual_comparison(coarse_ledger['entropy'],refined_ledger['entropy']),
        'gas_species':{name:{key:residual_comparison(coarse_ledger['gas_species'][name][key],refined_ledger['gas_species'][name][key])
            for key in ['budget_normalization','initial_reference_normalization']} for name in model.ng}}
    bundle.update(continuation_completed=True,refined_endpoint_inventory=refined_point,
        coarse_saved_cooling_interval=coarse_ledger,refined_cooling_interval=refined_ledger,
        signed_residual_comparisons=comparisons,
        refined_minus_coarse_endpoint_temperature_k=temperature-np.asarray(coarse_point['temperature_k']),
        endpoint_temperature_comparison_scope='Cooling endpoint only; no final cooling_hold product differences, continuous peak temperature or grid convergence.',
        existing_potential_helper_counters=dict(model.potential_helper_calls),
        completed_production_calls={'saved_checkpoint_load':1,'make_cycle':1,'native_initial_state':0,
            'solve_ivp_completed':1,'native_refined_endpoint':1,'native_potential_state':1,
            'complete_potential_values':model.potential_value_calls,'endpoint_interval_ledger':1,
            'baseline_potential_reevaluations':0,'initial_reference_reevaluations':0,
            'native_RHS_counter':model.rhs_calls,'native_Jacobian_counter':model.jacobian_calls,
            'extra_public_rates':0,'state_dynamics':0,'instantaneous_projection':0,
            'potential_gradient_directions':0,'trajectory_summary':0,'predict':0,'fit':0,'UQ':0},
        counter_qualification='Completed production path declarations and existing counters only; future RHS/Jac/native rates and inherited solver primitives are unknown until the actual solve, and no low-level probe is added.',
        uninstrumented_internal_calls=contract['source_only_forecast'])
    write_json(path, bundle)
    return {'output':str(path),'start_time_s':start_s,'end_time_s':float(solution.t[-1]),
        'numerical_condition':numerical_difference,'completed_production_calls':bundle['completed_production_calls'],
        'refined_interval_endpoint_balance_passed':refined_ledger['endpoint_balance_passed'],
        'criterion':'criterion_not_applicable','whole_model_complete':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters',type=Path)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--baseline-ledgers',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(refine_cooling_endpoint(args.parameters,args.checkpoint,args.baseline_ledgers,args.out),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
