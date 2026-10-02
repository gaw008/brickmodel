"""One initial-state production RHS observation on the declared saved-face case.

This fixed-context diagnostic reports signed physical budgets. It neither
changes the physics nor supplies a second operator/trajectory for comparison.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import numpy as np

from .full_cycle import make_cycle, saved_reference_partition_case


def saved_reference_host_case(root: dict) -> dict:
    declaration = root['public_reference_cases']['saved_reference_host']
    physical = root['public_reference_cases'][declaration['physical_case']]
    case = deepcopy(root)
    for target, source in physical['common_override_parameters'].items():
        case['parameters'][target] = deepcopy(root['parameters'][source])
    case['stages'] = deepcopy(physical['stages'])
    case['direct_carbonation'] = deepcopy(physical['channel'])
    case['parameters']['numerics.calcium_inventory_coordinate'] = deepcopy(
        root['parameters'][physical['calcium_coordinate_mode_parameter']])
    return saved_reference_partition_case(case)


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


def balance_record(residual, scale, *, unit, limit, definition):
    raw = np.asarray(residual)
    magnitude = float(np.max(np.abs(raw)))
    relative = None if scale == 0 else magnitude / scale
    return {'raw_signed_residual': plain(raw), 'unit': unit,
            'maximum_absolute': magnitude, 'normalization_scale': float(scale),
            'scale_definition': definition, 'relative': relative,
            'limit': limit, 'passed': relative is not None and relative < limit,
            'classification': 'undefined_zero_budget' if relative is None
            else 'passed' if relative < limit else 'failed'}


def face_record(values, unit):
    values = np.asarray(values)
    return {'native_internal_face_values': plain(values), 'unit': unit,
            'left_cell_contribution': plain(-values),
            'right_cell_contribution': plain(values),
            'raw_signed_adjacent_sum': plain(-values + values),
            'raw_signed_global_internal_sum': plain((-values + values).sum(axis=0)),
            'nonzero_observed_at_this_instant': bool(np.any(values != 0)),
            'scope': 'Same production face value with its two signed cell contributions; no second face operator or cross-context qualification'}


def observe_initial_rhs(case: dict, *, events_path: Path, retained_failures: dict) -> dict:
    declaration = case['public_reference_cases']['saved_reference_host']
    criteria = declaration['criteria']
    limit_key = criteria['instantaneous_identity']['limit_parameter']
    limit = case['parameters'][limit_key]['value']
    if case['parameters'][limit_key]['unit'] != '1':
        raise ValueError('instantaneous identity limit must be dimensionless')
    phase = 'construction'
    counts = {}
    captured = {}
    model = None
    started = time.monotonic()
    event_rows = []
    module_names = {'full_cycle.py', 'full_cycle_gas.py', 'full_cycle_solid.py',
                    'initial_finite_volume.py', 'direct_carbonation.py', 'face_energy_sampling.py'}
    def save_events():
        payload = {'recorded_utc': datetime.now(timezone.utc).isoformat(),
                   'production_function_entries_by_phase': counts,
                   'actual_entry_events': event_rows,
                   'physical_core_RHS_calls': None if model is None else model.rhs_calls,
                   'scope': 'Observed original call entries; inheritance entries are not extra instances'}
        events_path.write_text(json.dumps(payload, indent=2) + '\n')
    def observer(frame, event, value):
        file = Path(frame.f_code.co_filename).name
        if file not in module_names:
            return
        name = frame.f_code.co_qualname
        key = file + ':' + name
        if event == 'call':
            counts.setdefault(phase, {})[key] = counts.setdefault(phase, {}).get(key, 0) + 1
            if name in ('make_cycle', 'ThermoelasticFullCycle.rhs'):
                event_rows.append({'entry': key, 'phase': phase,
                                   'UTC': datetime.now(timezone.utc).isoformat()})
                save_events()
        if event == 'return' and phase == 'RHS':
            if name == 'FiniteGasFullCycle.rates':
                captured['rates'] = value
                captured['rate_locals'] = dict(frame.f_locals)
            if name == 'FiniteGasFullCycle.transport':
                captured['transport'] = dict(frame.f_locals)
            if name == 'ThermoelasticFullCycle.porous_mechanical_rates':
                captured['mechanical'] = dict(frame.f_locals)
    sys.setprofile(observer)
    try:
        model = make_cycle(case)
        phase = 'initialization'
        initial_state = model.initial_state()
        phase = 'RHS'
        model._summary_face_capture = {}
        derivative = model.rhs(model.times[0], initial_state)
        captured['native_faces'] = model._summary_face_capture
    finally:
        sys.setprofile(None)
        if model is not None:
            model._summary_face_capture = None
        save_events()
    rr = captured['rates']
    local = captured['rate_locals']
    mechanical = captured['mechanical']
    f, T, ns, ng = local['fields'], local['T'], local['ns'], local['ng']
    dns, dng = rr['dns'], rr['dng']
    cells = model.n
    df = derivative[:model.gas_offset].reshape(-1, cells)
    extent_dot = derivative[model.extent_offset:model.last].reshape(model.nr, cells).T * model.cell_chemical_scale[:, None]
    gas_coordinate_dot = derivative[model.gas_offset:model.extent_offset].reshape(model.g, cells).T * ng
    decoded_Ca = np.column_stack((
        -model.calcium_pool * df[3] - model.cell_chemical_scale * df[model.hydroxide_coordinate],
        model.calcium_pool * df[3],
        model.cell_chemical_scale * df[model.hydroxide_coordinate]))
    ca_indices = [model.calcite, model.lime, model.portlandite]
    boundary = rr['gas_flux'][-1]
    solid_massdot = dns @ model.mw[:len(model.ns)]
    gas_massdot = dng @ model.mw[len(model.ns):]
    boundary_mass = boundary @ model.mw[len(model.ns):]
    element_s = dns @ model.atom[:len(model.ns)]
    element_g = dng @ model.atom[len(model.ns):]
    element_out = boundary @ model.atom[len(model.ns):]
    mass_scale = np.abs(solid_massdot).sum() + np.abs(gas_massdot).sum() + np.abs(boundary * model.mw[len(model.ns):]).sum()
    element_scale = np.abs(element_s).sum() + np.abs(element_g).sum()
    mass_residual = solid_massdot.sum() + gas_massdot.sum() + boundary_mass
    element_residual = element_s.sum(axis=0) + element_g.sum(axis=0) + element_out
    elastic = mechanical['elastic']
    K, eps = elastic['modulus'], elastic['eps']
    bp, bpp = mechanical['beta_prime'], mechanical['beta_second']
    Kdot = elastic['kv'] * rr['db'] + elastic['kd'] * mechanical['ddry'] + mechanical['phase_modulus_rate']
    epsdot = rr['db'] / model.b0 - bp * rr['dT'] - mechanical['inelastic_rate']
    elastic_Udot = model.b0 * (Kdot * (eps**2 / 2 + T * bp * eps) + K * eps * epsdot
        + K * (rr['dT'] * bp * eps + T * bpp * rr['dT'] * eps + T * bp * epsdot))
    phase_Udot = -np.asarray(mechanical['phase_power'])
    Ucomponents = {'thermal_capacity': rr['capacity'] * rr['dT'],
                   'condensed_composition_including_binding': np.sum(local['us'] * dns, axis=1),
                   'gas_composition': np.sum(local['ug'] * dng, axis=1),
                   'pore_surface': local['cap'] * rr['dpore'],
                   'skeleton': elastic_Udot, 'phase_internal': phase_Udot}
    Udot = sum(Ucomponents.values())
    pressure_work = -model.P * rr['db'].sum()
    Uboundary = local['qext'] - rr['energy_flux'][-1] + pressure_work
    Uscale = (np.abs(rr['capacity'] * rr['dT']).sum()
              + np.abs(local['us'] * dns).sum() + np.abs(local['ug'] * dng).sum()
              + np.abs(local['cap'] * rr['dpore']).sum()
              + np.abs(elastic_Udot).sum() + np.abs(phase_Udot).sum() + abs(Uboundary))
    Scomponents = {
        'thermal_capacity': float(np.sum(rr['capacity'] * rr['dT'] / T)),
        'condensed_composition': float(np.sum(local['s'][:, :len(model.ns)] * dns)),
        'gas_composition': float(np.sum((local['sg'] - model.R) * dng)),
        'gas_pore_volume': float(np.sum(ng.sum(axis=1) * model.R * rr['dpore'] / local['pore'])),
        'skeleton_and_phase': float(local['extra_sdot']),
        'retention_mixing': float(-model.R * np.sum(local['log_activity'] * dns[:, model.water_index])),
        'binding_water': float(np.sum(local['binding']['partial_s'] * dns[:, model.water_index])),
        'binding_kaolin': float(np.sum(local['binding']['kaolin_s'] * dns[:, model.kaolin]))}
    Sdot = sum(Scomponents.values())
    Sscale = abs(Sdot) + abs(rr['production']) + abs(rr['exchange'])
    balances = {
        'mass': balance_record(mass_residual, mass_scale, unit='kg/s', limit=limit, definition=criteria['mass']['denominator']),
        'elements': balance_record(element_residual, element_scale, unit='mol/s', limit=limit, definition=criteria['elements']['denominator']),
        'complete_U_same_RHS_components': balance_record(Udot.sum() - Uboundary, Uscale, unit='W', limit=limit, definition=criteria['complete_U_components']['denominator']),
        'complete_S_same_RHS_components': balance_record(Sdot - rr['production'] - rr['exchange'], Sscale, unit='W/K', limit=limit, definition=criteria['complete_S_components']['denominator'])}
    source_scale = float(np.max(np.abs(rr['rate'])))
    coordinate_budgets = {
        'independent_extents': balance_record(extent_dot - rr['rate'], source_scale, unit='mol/s', limit=limit, definition='P43/P45 max abs(same rate)'),
        'gas_log_coordinates': balance_record(gas_coordinate_dot - dng, float(np.max(np.abs(dng))), unit='mol/s', limit=limit, definition='P45 max abs(same dng)'),
        'Ca_coordinates': balance_record(decoded_Ca - dns[:, ca_indices], source_scale, unit='mol/s', limit=limit, definition='P45 max abs(same rate)')}
    phases = {}
    for name, index in zip(('calcite', 'lime', 'portlandite'), ca_indices):
        delta = ns[:, index] - model.initial[:, index]
        scale = float(np.abs(model.initial[:, index]).sum() + np.abs(ns[:, index]).sum())
        phases[name] = {'declared_initial_mol': model.initial[:, index], 'actual_initial_mol': ns[:, index],
                        'raw_signed_initial_minus_declared_mol': delta,
                        'readback_budget': {
                            'raw_signed_residual': delta, 'unit': 'mol',
                            'maximum_absolute': float(np.max(np.abs(delta))),
                            'normalization_scale': scale,
                            'scale_definition': criteria['Ca_inventory_readback']['denominator'],
                            'relative': None if scale == 0 else float(np.max(np.abs(delta))) / scale,
                            'passed': False, 'criterion_applicable': False,
                            'classification': 'undefined_zero_budget' if scale == 0 else 'notqualified_descriptive_readback',
                            'scope': 'Descriptive ratio only; no existing initial inventory readback criterion'},
                        'interval_phase_ledger_qualified': False}
    baseline_h = local['h'][:, :len(model.ns)] - model.P * model.v
    initial_energy = {'condensed': np.sum(ns * baseline_h, axis=1),
                      'gas': np.sum(ng * local['ug'], axis=1),
                      'surface': local['surface'], 'binding': local['binding']['energy'],
                      'skeleton': model.b0 * K * (eps**2 / 2 + T * bp * eps)}
    initial_entropy = {'condensed': np.sum(ns * local['s'][:, :len(model.ns)], axis=1),
                       'gas': np.sum(ng * local['sg'], axis=1),
                       'retention_mixing': local['retention_entropy'],
                       'binding': local['binding']['entropy'],
                       'skeleton': model.b0 * K * bp * eps}
    strict = {'condensed_inventory_mol': ns, 'gas_inventory_mol': ng,
              'condensed_minimum_mol': float(ns.min()), 'gas_minimum_mol': float(ng.min()),
              'condensed_nonnegative': bool(np.all(ns >= 0)), 'gas_nonnegative': bool(np.all(ng >= 0)),
              'hydroxide_entropy_W_K': rr['hydroxide_entropy'], 'carbonate_entropy_W_K': rr['carbonate_entropy'],
              'direct_entropy_W_K': rr['direct_carbonation']['entropy_production_w_k'],
              'gas_face_entropy_W_K': local['face_entropy'], 'water_face_entropy_W_K': rr['water_entropy'],
              'thermal_entropy_W_K': local['thermal_entropy'], 'mechanical_entropy_W_K': local['mechanical_entropy'],
              'phase_entropy_W_K': mechanical['phase_production'],
              'sampled_reaction_entropy_by_cell_channel_W_K': -rr['rate'] * local['dg'] / T[:, None],
              'scope': 'Strict signs at this actual initial instant; no floor or dynamic positivity claim'}
    strict['all_observed_entropy_terms_nonnegative'] = all(bool(np.all(np.asarray(value) >= 0)) for key, value in strict.items() if 'entropy_' in key and key != 'scope')
    native = captured['native_faces']
    faces = {'positive_orientation': 'symmetry toward exterior',
             'gas_native_faces_mol_s': rr['gas_flux'],
             'gas_native_faces_count_excludes_symmetry': model.n,
             'gas_internal': face_record(rr['gas_flux'][:-1], 'mol/s'),
             'gas_boundary_mol_s': boundary,
             'gas_energy_internal': face_record(rr['energy_flux'][:-1], 'W'),
             'gas_energy_boundary_W': rr['energy_flux'][-1],
             'gas_molecular_energy_W': native['gas_molecular_energy_w'],
             'gas_Darcy_energy_W': native['gas_darcy_energy_w'],
             'heat_native_all_faces_W': native['thermal_energy_native_w'],
             'heat_internal': face_record(native['thermal_energy_native_w'][1:-1], 'W'),
             'heat_external_into_system_W': local['qext'],
             'water_internal': face_record(rr['water_flux'], 'mol/s'),
             'water_energy_internal': face_record(rr['water_energy_flux'], 'W'),
             'water_boundary': 'Closed symmetry and exterior; native water arrays contain internal faces only',
             'cell_heat_W': rr['heat'], 'cell_carried_flow_W': rr['flow'],
             'energy_accounting': 'Original total energy_flux counted once; molecular/Darcy decomposition is diagnostic only'}
    declared_sites = model.retention_matrix * model.site_survival + model.site_slope * ns[:, model.kaolin]
    physical = case['public_reference_cases'][declaration['physical_case']]
    changed_targets = {**physical['common_override_parameters'],
        'numerics.calcium_inventory_coordinate': physical['calcium_coordinate_mode_parameter'],
        **case['public_reference_cases']['saved_reference_partition']['parameter_records']}
    event_data = json.loads(events_path.read_text())
    report = {
        'schema': 'saved_reference_host_initial_instantaneous_diagnostics_v1',
        'recorded_utc': datetime.now(timezone.utc).isoformat(), 'physical_context': declaration,
        'derived_case_replaced_records': {key: {'source_parameter': source, 'actual_record': case['parameters'][key]} for key, source in changed_targets.items()},
        'actual_class': type(model).__name__, 'time_s': float(model.times[0]),
        'make_cycle_instance_calls': counts['construction']['full_cycle.py:make_cycle'], 'RHS_calls': model.rhs_calls,
        'normal_production_call_entries': event_data, 'sampler_dynamic_enabled': False,
        'initial_state': initial_state, 'RHS_derivative': derivative,
        'geometry': model.initial_partition,
        'actual_same_RHS_geometry': {'bulk_m3': local['bulk'], 'pore_m3': local['pore'],
            'transport_widths_m': captured['transport']['widths'],
            'transport_face_distance_m': captured['transport']['distance'],
            'raw_signed_bulk_minus_initial_b0_m3': local['bulk'] - model.b0},
        'scales': {'b0_m3': model.b0, 'md_kg': model.md, 'chemical_mol': model.cell_chemical_scale,
                   'conversion_mol': model.conversion_scale, 'independent_extent_reference_mol': model.cell_chemical_scale,
                   'extent_scale_mol': model.extent_scale, 'retention_sites_mol': declared_sites,
                   'calcium_pool_mol': model.calcium_pool, 'total_initial_dry_mass_kg': model.total_initial_dry_mass},
        'initial_inventory': {'condensed_species': model.ns, 'gas_species': model.ng,
            'declared_condensed_mol': model.initial, 'actual_condensed_mol': ns,
            'raw_signed_condensed_minus_declared_mol': ns - model.initial,
            'declared_gas_mol': model.initial_gas, 'actual_gas_mol': ng,
            'raw_signed_gas_minus_declared_mol': ng - model.initial_gas,
            'calcium_phases': phases,
            'independent_extent_initial_mol': initial_state[model.extent_offset:model.last].reshape(model.nr, model.n).T * model.cell_chemical_scale[:, None],
            'initial_U_components_J': initial_energy, 'initial_S_components_J_K': initial_entropy},
        'same_RHS_faces': faces,
        'same_RHS_sources': {'reaction_ids': [item['id'] for item in model.reactions],
            'rate_mol_s': rr['rate'], 'condensed_mol_s': dns, 'gas_mol_s': dng,
            'dT_K_s': rr['dT'], 'db_m3_s': rr['db'], 'dpore_m3_s': rr['dpore']},
        'mass_element_ledger': {'mass_storage_kg_s': float(solid_massdot.sum() + gas_massdot.sum()),
            'mass_boundary_out_kg_s': float(boundary_mass), 'element_names': model.elements,
            'element_storage_mol_s': element_s.sum(axis=0) + element_g.sum(axis=0), 'element_boundary_out_mol_s': element_out},
        'complete_U_ledger': {'cell_storage_components_W': Ucomponents, 'cell_storage_total_W': Udot,
            'boundary_heat_in_W': local['qext'], 'boundary_carried_energy_out_W': rr['energy_flux'][-1],
            'external_pressure_work_W': pressure_work, 'boundary_net_W': Uboundary,
            'reaction_or_phase_heat_added_as_extra_source': False,
            'scope': 'Analytic derivative from same mechanical coefficients; phase heat counted through original storage once'},
        'complete_S_ledger': {'storage_components_W_K': Scomponents, 'storage_W_K': Sdot,
            'production_W_K': rr['production'], 'exchange_W_K': rr['exchange'],
            'raw_producer_storage_W_K': local['sdot'], 'raw_producer_residual_W_K': rr['entropy_identity_residual'],
            'scope': 'Same production mechanical derivatives; not independent potential differentiation'},
        'instantaneous_balances': balances, 'coordinate_readback_budgets': coordinate_budgets,
        'strict_initial_inventory_and_entropy': strict,
        'P45_old_new_netU': {'qualified': False, 'reason': 'Matched old host unavailable under one instance allocation',
            'original_retained_failure_relative': retained_failures['P45_netU_relative'], 'original_limit_parameter': limit_key,
            'component_U_ledger_does_not_replace_original_comparison': True},
        'units_used_by_host': model.used_units,
        'new_Jac_ODE_fit_UQ_extra_rates_thermo_constitutive_scans': 0,
        'all8stage_dynamics_time_grid_Csampling_comparison_inverse_modelCLI_qualified': False,
        'whole_project_complete': False, 'elapsed_observation_and_report_s': time.monotonic() - started}
    return plain(report)
