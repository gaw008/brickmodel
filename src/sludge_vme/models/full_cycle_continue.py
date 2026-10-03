"""Continue one declared stage from a strictly loaded native checkpoint.

The saved complete case and mechanical references remain authoritative. The
additional producer travels with the endpoint source identity, so the existing
strict loader can consume it without changing its source comparison.
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
from .full_cycle_gas import solve_ivp


def continue_native_endpoint(parameters: Path, checkpoint: Path, out: Path):
    """Use the existing BDF callable and native rhs/jac on the saved full y."""
    started = time.monotonic()
    contract = json.loads(parameters.read_text())['native_continuation']
    model, start_s, state, inherited = load_native_checkpoint(checkpoint, stage=None)
    stage_index = model.config['stages'].index(inherited['stop_stage']) + 1
    stage = model.config['stages'][stage_index]
    end_s = float(model.times[stage_index+1])

    config = deepcopy(inherited['config'])
    config['native_continuation'] = contract
    config['native_checkpoint']['source_paths'] = list(dict.fromkeys([
        *config['native_checkpoint']['source_paths'], contract['producer_source_path']]))
    config['native_checkpoint']['implementation_parent_revision'] = contract['implementation_parent_revision']
    path = out/contract['output_filename']
    bundle = {
        'schema': config['native_checkpoint']['schema'],
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'case_reference': inherited['case_reference'], 'config': config,
        'source_version': {
            'implementation_parent_revision': contract['implementation_parent_revision'],
            'identity_basis': 'Complete unchanged inherited production source plus this additive producer; parent revision is ancestry, not an execution commit claim.',
            'source_text': _source_text(config)},
        'inherited_checkpoint_reference': str(checkpoint.resolve()),
        'inherited_source_identity': {
            'implementation_parent_revision': inherited['source_version']['implementation_parent_revision'],
            'identity_basis': inherited['source_version']['identity_basis'],
            'source_paths': inherited['config']['native_checkpoint']['source_paths']},
        'resume_origin': {'stage': inherited['stop_stage'], 'time_s': start_s,
                          'native_y': state.copy(),
                          'basis': 'Exact saved complete native y supplied to BDF; all cumulative origins and references retained.'},
        'context': inherited['context'], 'stop_stage': stage,
        'full_declared_stage_list': config['stages'], 'endpoints': [],
        'continuation_completed': False, 'prefix_completed': False,
        'full_cycle_completed': False, 'criterion': 'criterion_not_applicable',
        'whole_model_complete': False,
        'operation_scope': 'One next original stage, endpoint only; native equations and absolute-time furnace/gas interpolation unchanged.'}
    out.mkdir(parents=True, exist_ok=True)
    write_json(out/'case-parameters.json', config)
    write_json(path, bundle)

    rhs_before, jac_before = model.rhs_calls, model.jacobian_calls
    sol = solve_ivp(model.rhs, (start_s, end_s), state,
                    method=contract['solver_method'], jac=model.jacobian,
                    t_eval=np.asarray([end_s]),
                    max_step=model.p('numerics.max_step', 's'),
                    rtol=model.p('numerics.rtol', '1'),
                    atol=model.p('numerics.atol', '1'))
    if not sol.success:
        raise RuntimeError(f'{stage}: {sol.message}')
    endpoint = sol.y[:, -1].copy()
    temperature = endpoint[:model.n]*model.Tr
    solver = {'method': contract['solver_method'], 'success': sol.success,
              'message': sol.message, 'nfev': sol.nfev, 'njev': sol.njev, 'nlu': sol.nlu,
              'actual_rhs_calls_including_jacobian': model.rhs_calls-rhs_before,
              'actual_jacobian_calls': model.jacobian_calls-jac_before,
              'elapsed_since_continuation_start_s': time.monotonic()-started,
              'history': 'Fresh BDF history at the saved stage boundary; complete native y and all ledgers carried unchanged.'}
    bundle['endpoints'].append({
        'stage': stage, 'time_s': float(sol.t[-1]), 'native_y': endpoint,
        'native_y_basis': 'Exact complete sol.y[:, -1] at sol.t[-1]; no reconstruction, clipping or reseeding.',
        'temperature_k': temperature,
        'branch_provenance': {
            'quartz_shomate_alpha': temperature.real < model.tc,
            'kinetic_liquid': model.kinetic_liquid,
            'direct_carbonation_enabled': model.direct_carbonation_enabled,
            'calcium_coordinate_mode': model.calcium_coordinate_mode,
            'caloric_source_domains': config['caloric_background'],
            'viscosity_background': config['viscosity_background'],
            'binary_diffusion_background': config['binary_diffusion_background'],
            'scope': 'Actual endpoint only; no continuous-source-domain or material admission. Original assumed analytic continuation remains explicit.'},
        'solver': solver})
    bundle['continuation_completed'] = True
    bundle['completed_production_calls'] = {
        'saved_checkpoint_load': 1, 'make_cycle': 1, 'native_initial_state': 0,
        'solve_ivp_completed': 1, 'native_RHS_counter': model.rhs_calls,
        'native_Jacobian_counter': model.jacobian_calls,
        'potential_values': 0, 'state_dynamics': 0, 'trajectory_summary': 0,
        'predict': 0, 'fit': 0, 'UQ': 0}
    bundle['counter_qualification'] = 'Completed production path counts and actual native RHS/Jac counters; uninstrumented primitives remain source forecasts.'
    write_json(path, bundle)
    return {'checkpoint': str(path), 'continued_stage': stage,
            'start_time_s': start_s, 'end_time_s': float(sol.t[-1]),
            'continuation_completed': True, 'full_cycle_completed': False,
            'completed_production_calls': bundle['completed_production_calls'],
            'criterion': 'criterion_not_applicable', 'whole_model_complete': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = continue_native_endpoint(args.parameters, args.checkpoint, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
