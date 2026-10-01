"""Compare stored finite-volume profiles; never import or evaluate a model.

Usage: python scripts/analyze_saved_direct_transient.py ROOT_PARAMETERS OUTPUT
All case paths and field selections are the root's explicit P41 contract.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time


def grouped_sum(values, ratio):
    return [sum(values[i:i+ratio]) for i in range(0, len(values), ratio)]


def difference(left, right):
    return [b-a for a, b in zip(left, right)]


def centers(widths):
    positions, edge = [], 0.0
    for width in widths:
        positions.append(edge+width/2)
        edge += width
    return positions


def interpolate_inside(positions, values, targets):
    result, i = [], 0
    for target in targets:
        while positions[i+1] < target:
            i += 1
        weight = (target-positions[i])/(positions[i+1]-positions[i])
        result.append(values[i]+weight*(values[i+1]-values[i]))
    return result


def flatten_scalars(value, prefix=''):
    if isinstance(value, dict):
        return {k: v for key, child in value.items()
                for k, v in flatten_scalars(child, prefix+key+'.').items()}
    if isinstance(value, list):
        return {k: v for i, child in enumerate(value)
                for k, v in flatten_scalars(child, prefix+str(i)+'.').items()}
    return {prefix.rstrip('.'): value}


def analyze(parameter_path: Path):
    started = time.monotonic()
    project = parameter_path.parent
    current = json.loads(parameter_path.read_text())
    contract = current['public_reference_cases']['saved_direct_spatial_diagnosis']
    directory = project/contract['input_directory']
    frozen = json.loads((directory/contract['physical_input_root']).read_text())
    old_case = frozen['public_reference_cases']['direct_carbonation_transient']
    records = {name: json.loads((directory/(name+'.json')).read_text())
               for name in contract['case_ids']}
    original_acceptance = json.loads((directory/contract['prior_acceptance']).read_text())
    coarse = records[contract['coarse_case']]
    fine = records[contract['fine_case']]
    temporal = records[contract['temporal_case']]
    coarse_rows = coarse['saved_numerical_samples']
    fine_rows = fine['saved_numerical_samples']
    nc, nf = len(coarse_rows[0]['temperature_k']), len(fine_rows[0]['temperature_k'])
    ratio = nf//nc
    if nf != ratio*nc:
        raise ValueError('Stored fine cells do not partition coarse reference intervals.')
    coarse_times = [row['time_s'] for row in coarse_rows]
    if coarse_times != [row['time_s'] for row in fine_rows]:
        raise ValueError('Stored physical sampling times differ; no implicit time interpolation.')
    area = frozen['parameters']['geometry.area']['value']
    length = frozen['parameters']['geometry.half_thickness']['value']
    geometry = {}
    configurations, initial_comparisons = {}, {}
    for name, record in records.items():
        job = record['frozen_job']
        effective = deepcopy(frozen['parameters'])
        for target, source in old_case['common_override_parameters'].items():
            effective[target] = deepcopy(frozen['parameters'][source])
        for target, source in [('numerics.cells', job['cells_parameter']),
                               ('numerics.max_step', job['max_step_parameter']),
                               ('numerics.rtol', job['rtol_parameter']),
                               ('numerics.atol', job['atol_parameter'])]:
            effective[target] = deepcopy(frozen['parameters'][source])
        configurations[name] = effective
        n = len(record['saved_numerical_samples'][0]['temperature_k'])
        b0 = area*length/n
        initial = record['actual_initial_state']
        ref = initial['references']
        geometry[name] = {
            'cells': n, 'area_m2': area, 'half_thickness_m': length,
            'declared_initial_cell_volume_m3': b0,
            'actual_initial_total_bulk_m3': ref['bulk_volume_m3'],
            'actual_minus_declared_total_bulk_m3': ref['bulk_volume_m3']-area*length,
            'reference_cell_width_m': length/n,
            'reference_cell_centers_m': centers([length/n]*n),
            'initial_condensed_mol_by_cell': initial['actual_condensed_mol_by_cell'],
            'initial_gas_mol_by_cell': initial['actual_gas_mol_by_cell'],
            'initial_portlandite_bulk_concentration_mol_m3':
                [v/b0 for v in initial['actual_condensed_mol_by_cell']['portlandite']],
            'initial_direct_rate_mol_s_by_cell': record['saved_numerical_samples'][0]['direct_carbonation_rate_mol_s'],
            'initial_direct_rate_total_mol_s': sum(record['saved_numerical_samples'][0]['direct_carbonation_rate_mol_s']),
            'initial_rate_per_OH_per_s': [v/n0 for v, n0 in zip(
                record['saved_numerical_samples'][0]['direct_carbonation_rate_mol_s'],
                initial['actual_condensed_mol_by_cell']['portlandite'])],
            'saved_boundary_program': {s: effective['gas.inlet.'+s]
                                       for s in initial['actual_gas_mol_by_cell']},
            'channel_identity': old_case['channel'],
            'mobility': effective[old_case['channel']['mobility_parameter']],
            'initial_output_raw_difference': record['report']['initial_output_provenance'],
        }
    reference_parameters = configurations[contract['coarse_case']]
    reference_scalars = flatten_scalars(coarse['actual_initial_state']['references'])
    for name, record in records.items():
        diffs = {k: {'baseline': reference_parameters[k], 'case': value}
                 for k, value in configurations[name].items()
                 if value != reference_parameters[k]}
        got = flatten_scalars(record['actual_initial_state']['references'])
        initial_comparisons[name] = {
            'effective_parameter_differences': diffs,
            'only_declared_numeric_case_parameters_differ':
                set(diffs) <= {'numerics.cells', 'numerics.max_step', 'numerics.rtol', 'numerics.atol'},
            'actual_initial_reference_signed_differences':
                {k: got[k]-v for k, v in reference_scalars.items()
                 if isinstance(v, (int, float)) and k in got},
            'same_reference_scope': record['actual_initial_state']['references']['reference_basis'],
            'percell_vs_total_note': 'Per-cell quantities are explicitly grouped before spatial comparison. Zero independent extents/cumulative references retain signed differences; no bitwise trajectory-origin requirement.',
        }
    comparisons = []
    for left, right in zip(coarse_rows, fine_rows):
        fields = {name: left[name] for name in contract['extensive_profile_fields']}
        fine_fields = {name: right[name] for name in contract['extensive_profile_fields']}
        for dictionary in contract['extensive_dictionary_fields']:
            fields.update({dictionary+'.'+name: values for name, values in left[dictionary].items()})
            fine_fields.update({dictionary+'.'+name: values for name, values in right[dictionary].items()})
        extensive = {}
        for name, values in fields.items():
            mapped = grouped_sum(fine_fields[name], ratio)
            delta = difference(values, mapped)
            extensive[name] = {'coarse_raw': values, 'fine_conservative_sum': mapped,
                               'signed_difference': delta, 'global_signed_difference': sum(delta),
                               'fine_total_minus_mapped_total_roundoff': sum(fine_fields[name])-sum(mapped)}
        cb = [area*length/nc*(1-v) for v in left['thickness_shrinkage']]
        fb = [area*length/nf*(1-v) for v in right['thickness_shrinkage']]
        grouped_bulk = grouped_sum(fb, ratio)
        ct, ft = left['temperature_k'], right['temperature_k']
        weighted_t = [sum(t*v for t, v in zip(ft[i:i+ratio], fb[i:i+ratio]))/sum(fb[i:i+ratio])
                      for i in range(0, nf, ratio)]
        interpolated = interpolate_inside(geometry[contract['fine_case']]['reference_cell_centers_m'],
                                         ft, geometry[contract['coarse_case']]['reference_cell_centers_m'])
        coarse_ca = [sum(z) for z in zip(left['calcite_inventory_mol'], left['lime_inventory_mol'], left['portlandite_inventory_mol'])]
        fine_ca = grouped_sum([sum(z) for z in zip(right['calcite_inventory_mol'], right['lime_inventory_mol'], right['portlandite_inventory_mol'])], ratio)
        phase = {name: {'coarse_mol_per_current_bulk_m3': [v/vol for v, vol in zip(left[name+'_inventory_mol'], cb)],
                        'fine_group_mol_per_group_current_bulk_m3': [v/vol for v, vol in zip(grouped_sum(right[name+'_inventory_mol'], ratio), grouped_bulk)],
                        'coarse_fraction_of_current_Ca': [v/ca for v, ca in zip(left[name+'_inventory_mol'], coarse_ca)],
                        'fine_group_fraction_of_current_Ca': [v/ca for v, ca in zip(grouped_sum(right[name+'_inventory_mol'], ratio), fine_ca)]}
                 for name in coarse['calcium_phase_ledgers'][0]['species']}
        partials = {}
        for name in left['gas_inventory_mol']:
            lp = [p*v/nt for p, v, nt in zip(left['pressure_pa'], left['gas_inventory_mol'][name], [sum(z) for z in zip(*left['gas_inventory_mol'].values())])]
            rp = [p*v/nt for p, v, nt in zip(right['pressure_pa'], right['gas_inventory_mol'][name], [sum(z) for z in zip(*right['gas_inventory_mol'].values())])]
            partials[name] = {'coarse_raw_Pa': lp, 'fine_raw_Pa': rp,
                              'basis': 'Saved totalpressure times saved molefraction; no gas_state/constitutive reevaluation.'}
        comparisons.append({'time_s': left['time_s'], 'extensive_profiles': extensive,
                            'current_bulk_reconstructed_m3': {'coarse': cb, 'fine_group_sum': grouped_bulk},
                            'bulk_basis': 'Exact algebraic inverse of saved shrinkage=1-bulk/b0, with rootarea*length/n; no model instance.',
                            'current_cell_centers_m': {'coarse': centers([v/area for v in cb]), 'fine': centers([v/area for v in fb])},
                            'temperature': {'coarse_raw_K': ct, 'fine_raw_K': ft,
                                            'fine_bulk_volume_weighted_group_K': weighted_t,
                                            'signed_group_temperature_difference_K': difference(ct, weighted_t),
                                            'fine_linear_interpolation_on_coarse_reference_centers_K': interpolated,
                                            'signed_reference_center_temperature_difference_K': difference(ct, interpolated),
                                            'original_coarse_peakcontrast_K': left['temperature_difference_k'],
                                            'original_fine_peakcontrast_K': right['temperature_difference_k'],
                                            'limitation': 'Volume-weighted temperature is not heat-energy averaging; interpolation is on material reference positions. Neither replaces finepeak or originalfailedacceptance.'},
                            'phase_ratios': phase, 'gas_partial_profiles': partials,
                            'direct_saved_rates_mol_s': {'coarse_raw': left['direct_carbonation_rate_mol_s'],
                                                         'fine_group_sum': grouped_sum(right['direct_carbonation_rate_mol_s'], ratio)},
                            'direct_saved_affinity_J_mol': {'coarse_raw': left['direct_carbonation_affinity_j_mol'], 'fine_raw': right['direct_carbonation_affinity_j_mol']}})
    ledger = {}
    for name in records:
        species = records[name]['report']['gas_species_ledger']['whole_cycle']['species']['CO2']
        ext = records[name]['report']['summary']['reaction_totals_mol']['direct_carbonation']
        other = sum(v for reaction, v in species['reaction_sources_mol'].items() if reaction != 'direct_carbonation')
        predicted = species['initial_inventory_mol']-species['final_inventory_mol']+species['boundary_in_mol']-species['boundary_out_mol']+other+species['residual_mol']
        ledger[name] = {'independent_integrated_direct_extent_mol': ext,
                        'CO2_initial_mol': species['initial_inventory_mol'], 'CO2_final_mol': species['final_inventory_mol'],
                        'CO2_boundary_in_mol': species['boundary_in_mol'], 'CO2_boundary_out_mol': species['boundary_out_mol'],
                        'other_signed_CO2_reaction_sources_mol': other, 'signed_original_CO2_budget_residual_mol': species['residual_mol'],
                        'algebraic_CO2_account_prediction_mol': predicted, 'independent_extent_minus_account_prediction_mol': ext-predicted,
                        'qualification': 'Cross-read independently integratedextent andboundary endpoints; retained residual is itself their signed mismatch. This rearranged identity is explanatory, not a new independent conservation proof or extent recovery.'}
    base_ledger = ledger[contract['coarse_case']]
    signed_ledger_difference = {name: {k: value-base_ledger[k] for k, value in row.items() if isinstance(value, (int, float))}
                               for name, row in ledger.items()}
    final_difference = comparisons[-1]['extensive_profiles']['reaction_extent_mol.direct_carbonation']['signed_difference']
    static = []
    desired = {'full_cycle.py': ['__init__', 'reaction_fields', 'heat_transfer_from_conductivity'],
               'full_cycle_gas.py': ['__init__', 'gas_state', 'transport', 'wall_friction_molecular_flux', 'rates', 'rhs', 'condensed_state', 'caloric_capacity', 'mechanical_rates'],
               'full_cycle_solid.py': ['mechanical_rates', 'caloric_capacity', 'skeleton_chemical_potential'],
               'direct_carbonation.py': ['direct_carbonation_sources'],
               'full_cycle_diagnostics.py': ['gas_species_ledger']}
    for name in contract['source_files']:
        source = (project/name).read_text()
        saved = (directory/'frozen-src'/Path(name).relative_to('src')).read_text()
        tree = ast.parse(saved)
        anchors = [{'function': node.name, 'start': node.lineno, 'end': node.end_lineno}
                   for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name in desired[Path(name).name]]
        static.append({'path': name, 'live_equals_executed_frozen_source': source == saved, 'functions': anchors})
    output = {'schema': 'P41_saved_spatial_diagnosis_v1', 'recorded_utc': datetime.now(timezone.utc).isoformat(),
              'identity': 'Pure saved synthetic-data analysis; not material or new model evaluation',
              'input_records': [str(Path(contract['input_directory'])/(name+'.json')) for name in records],
              'configuration_and_initial_state': initial_comparisons, 'geometry_and_initial_scaling': geometry,
              'shared_reference_pairing': {'fine_per_coarse': ratio, 'coarse_cells': nc, 'fine_cells': nf,
                                          'reference_centers_coarse_m': geometry[contract['coarse_case']]['reference_cell_centers_m'],
                                          'same_initial_material_interval_not_exact_currentspatial_overlay': True},
              'samples': comparisons, 'CO2_extent_account_crossread': ledger,
              'signed_account_differences_from_baseline': signed_ledger_difference,
              'final_outer_reference_bin': {'signed_extra_extent_mol': final_difference[-1],
                                             'fraction_of_global_extra_extent': final_difference[-1]/sum(final_difference)},
              'source_static_anchors': static, 'original_required_acceptance': original_acceptance['required_four_metric_checks'],
              'original_P40_starts_and_deadline': {'starts_including_failure': original_acceptance['actual_integration_starts_including_failure'],
                                                  'original_allowance': original_acceptance['original_start_allowance'],
                                                  'explicit_additional_mesh': original_acceptance['explicit_additional_mesh_allowance'],
                                                  'deadline_extended': False},
              'saved_fine_original_peakcontrast_retained': True, 'whole_project_complete': False,
              'new_model_instances_constitutive_RHS_Jac_ODE_fit_UQ_calls': 0,
              'elapsed_analysis_s': time.monotonic()-started,
              'limits': ['Finite21saved samples are not continuousdomain/entropy proof.',
                         'Missing molecular/Darcy boundary separation and local energycomponent histories cannot be fabricated.',
                         'No confirmed source/area/units/index bug; spatially changed boundaryreaction solution is observed, unique cause/asymptoticorder unproved.',
                         'CaOphasebudget/strictOH+carbonate/P34old30of81/nominaldrying remain failed.',
                         'Grouped intensiveprofiles do not replace original mesh acceptance.']}
    return output


if __name__ == '__main__':
    result = analyze(Path(sys.argv[1]).resolve())
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'elapsed_analysis_s': result['elapsed_analysis_s'],
                      'saved_samples': len(result['samples']),
                      'outer_bin': result['final_outer_reference_bin'],
                      'new_model_calls': result['new_model_instances_constitutive_RHS_Jac_ODE_fit_UQ_calls']}, indent=2))
