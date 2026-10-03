"""Production native endpoint persistence with the original constitutive context.

Only solver-returned endpoint vectors are saved. Prefix acquisition never calls
the full-cycle summary, and loading never substitutes an initial state. The
source text and complete case travel with the vector; no checksum is used.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from .full_cycle import make_cycle, write_json


def _source_text(config):
    root = Path(__file__).resolve().parents[3]
    return {name: (root/name).read_text()
            for name in config['native_checkpoint']['source_paths']}


def _native_context(model):
    """Copy constructor references and scales without decoding any state."""
    names = model.config['native_checkpoint']['context_numeric_attributes']
    numeric = {}
    for name in names:
        value = getattr(model, name)
        numeric[name] = {'kind': 'array' if isinstance(value, np.ndarray) else 'scalar',
                         'value': value}
    return {'numeric': numeric, 'initial_partition': model.initial_partition,
            'phase0': model.phase0, 'liquid_reference': model.liquid_reference,
            'species': {'condensed': model.ns, 'gas': model.ng},
            'reactions': model.reactions,
            'branch_selectors': {
                'kinetic_liquid': model.kinetic_liquid,
                'direct_carbonation_enabled': model.direct_carbonation_enabled,
                'cellwise_partition': model.cellwise_partition,
                'calcium_coordinate_mode': model.calcium_coordinate_mode,
                'calcium_fraction_coordinate': model.calcium_fraction_coordinate},
            'layout': {'cells': model.n, 'gas_species': model.g,
                       'reactions': model.nr, 'hydroxide_field': model.hydroxide_coordinate,
                       'liquid_field': model.liquid_coordinate,
                       'gas_offset': model.gas_offset, 'extent_offset': model.extent_offset,
                       'reaction_end': model.last, 'length': model.last+2*model.g+3},
            'physical_units': {'time': 's', 'temperature': 'K', 'inventory': 'mol',
                               'energy_scale': 'J', 'entropy_scale': 'J/K'},
            'native_layout_contract': model.config['native_checkpoint']['native_layout']}


def export_native_checkpoints(config, out: Path, *, case_reference: str, stop_stage: str):
    """Acquire the declared stage prefix using the complete unchanged case."""
    out.mkdir(parents=True, exist_ok=True)
    model = make_cycle(config)
    contract = config['native_checkpoint']
    path = out/contract['output_filename']
    bundle = {'schema': contract['schema'], 'created_utc': datetime.now(timezone.utc).isoformat(),
              'case_reference': case_reference, 'config': config,
              'source_version': {
                  'implementation_parent_revision': contract['implementation_parent_revision'],
                  'identity_basis': 'Complete ordinary production source text; parent revision is ancestry, not an execution commit claim.',
                  'source_text': _source_text(config)},
              'context': _native_context(model), 'stop_stage': stop_stage,
              'full_declared_stage_list': config['stages'], 'endpoints': [],
              'prefix_completed': False, 'full_cycle_completed': False,
              'criterion': 'criterion_not_applicable', 'whole_model_complete': False,
              'operation_scope': 'Solver-returned native endpoints only; no summary or new constitutive evaluation.'}
    write_json(path, bundle)
    write_json(out/'case-parameters.json', config)

    def save_endpoint(stage, time_s, y, solver):
        temperature = y[:model.n]*model.Tr
        bundle['endpoints'].append({
            'stage': stage, 'time_s': time_s, 'native_y': y,
            'native_y_basis': 'Exact complete sol.y[:, -1] at sol.t[-1]; no reconstruction or reseeding.',
            'temperature_k': temperature,
            'branch_provenance': {
                'quartz_shomate_alpha': temperature.real < model.tc,
                'kinetic_liquid': model.kinetic_liquid,
                'direct_carbonation_enabled': model.direct_carbonation_enabled,
                'calcium_coordinate_mode': model.calcium_coordinate_mode,
                'caloric_source_domains': config['caloric_background'],
                'viscosity_background': config['viscosity_background'],
                'binary_diffusion_background': config['binary_diffusion_background'],
                'scope': 'Actual endpoint temperature and selectors; not extrema or source admission between saved endpoints.'},
            'solver': solver})
        write_json(path, bundle)

    execution = model.integrate_until(stop_stage, endpoint_sink=save_endpoint)
    bundle['prefix_completed'] = True
    bundle['completed_production_calls'] = {
        'make_cycle': 1, 'native_initial_state': 1,
        'solve_ivp_completed': len(bundle['endpoints']),
        'native_RHS_counter': model.rhs_calls, 'native_Jacobian_counter': model.jacobian_calls,
        'potential_values': 0, 'state_dynamics': 0, 'trajectory_summary': 0,
        'predict': 0, 'fit': 0, 'UQ': 0}
    bundle['execution'] = execution
    write_json(path, bundle)
    return {'checkpoint': str(path), 'stop_stage': stop_stage,
            'prefix_completed': True, 'full_cycle_completed': False,
            'completed_production_calls': bundle['completed_production_calls'],
            'criterion': 'criterion_not_applicable', 'whole_model_complete': False}


def load_native_checkpoint(path: Path, *, stage: str | None):
    """Read the saved complete case, source context and actual native endpoint."""
    bundle = json.loads(Path(path).read_text())
    config = bundle['config']
    if _source_text(config) != bundle['source_version']['source_text']:
        raise ValueError('Saved native checkpoint production source differs from the current source')
    model = make_cycle(config)
    context = bundle['context']
    for name, item in context['numeric'].items():
        value = np.asarray(item['value']) if item['kind'] == 'array' else item['value']
        setattr(model, name, value)
    model.initial_partition = {name: np.asarray(value)
                               for name, value in context['initial_partition'].items()}
    model.phase0 = tuple(context['phase0'])
    model.liquid_reference = tuple(context['liquid_reference'])
    selected_stage = bundle['stop_stage'] if stage is None else stage
    endpoint = {record['stage']: record for record in bundle['endpoints']}[selected_stage]
    y = np.asarray(endpoint['native_y'], dtype=float)
    return model, endpoint['time_s'], y, bundle


def export_checkpoint_state_dynamics(checkpoint: Path, out: Path):
    """Use one saved-state native event and its existing explicit projection."""
    model, time_s, y, bundle = load_native_checkpoint(checkpoint, stage=None)
    dynamics = model.state_dynamics(time_s, y)
    projection = model.instantaneous_potential_power(dynamics)
    payload = {'schema': 'full_cycle_saved_native_state_dynamics_v1',
               'checkpoint_reference': str(checkpoint.resolve()),
               'saved_stage': bundle['stop_stage'], 'saved_time_s': time_s,
               'saved_source_version': bundle['source_version'],
               'dynamics': dynamics, 'projection': projection,
               'source_domain_contract': model.config['caloric_background'],
               'direct_channel': {'enabled': model.direct_carbonation_enabled},
               'completed_production_calls': {
                   'make_cycle': 1, 'native_initial_state': 0,
                   **dynamics['completed_production_calls'],
                   'complete_vector_potential_values': model.potential_value_calls,
                   'own_value_helper_call_sites': model.potential_helper_calls,
                   'native_RHS_counter': model.rhs_calls,
                   'native_Jacobian_counter': model.jacobian_calls,
                   'ODE': 0, 'trajectory_summary': 0, 'predict': 0, 'fit': 0, 'UQ': 0},
               'counter_qualification': 'Only public production counters are observed; inherited and uninstrumented primitives are source forecasts.',
               'criterion': 'criterion_not_applicable', 'whole_model_complete': False,
               'material_applicability': 'Pending target material measurements; evolved-state activation must be interpreted from actual output.'}
    write_json(out/'case-parameters.json', model.config)
    write_json(out/'state-dynamics.json', payload)
    return payload
