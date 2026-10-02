"""Materialize the root-declared saved-face case and its initial geometry.

Run in the offline source checkout with its existing dependency environment. This entry reads saved H
geometry and calls initial_partition_from_faces once; it does not build a host.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sludge_vme.models.full_cycle import read_parameters, saved_reference_partition_case
from sludge_vme.models.initial_finite_volume import initial_partition_from_faces


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('--case-output', type=Path, required=True)
    parser.add_argument('--geometry-output', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    root = read_parameters(args.parameters)
    declaration = root['public_reference_cases']['saved_reference_partition']
    source_path = args.parameters.resolve().parent / declaration['source']
    saved = json.loads(source_path.read_text())[declaration['source_field']]
    case = saved_reference_partition_case(root)
    payload = json.dumps(case, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    args.case_output.write_text(payload)
    # Reuse the existing reader on the actual generated legal parameter file.
    case = read_parameters(args.case_output)
    parameters = case['parameters']
    contract = case['initial_partition']
    mode = parameters[contract['mode_parameter']]['value']
    if contract['profile_by_mode'][str(mode)] != 'saved_faces':
        raise ValueError('the named saved-reference case must select saved_faces')
    keys = {'faces': contract['faces_parameter'], 'cells': 'numerics.cells',
            'area': declaration['area_parameter'],
            'half_thickness': declaration['half_thickness_parameter'],
            'mode': contract['mode_parameter']}
    units = {'faces': 'm', 'cells': '1', 'area': 'm2', 'half_thickness': 'm', 'mode': '1'}
    for name, key in keys.items():
        if parameters[key]['unit'] != units[name]:
            raise ValueError(f'geometry unit mismatch: {key}')
    geometry = initial_partition_from_faces(
        faces_m=parameters[keys['faces']]['value'],
        cells=parameters[keys['cells']]['value'],
        half_thickness_m=parameters[keys['half_thickness']]['value'],
        area_m2=parameters[keys['area']]['value'])
    arrays = {k: v.tolist() if isinstance(v, np.ndarray) else float(v)
              for k, v in geometry.items()}
    old_bulk = np.asarray(saved['initial_reference_bulk_m3'])
    area = parameters[keys['area']]['value']
    length = parameters[keys['half_thickness']]['value']
    comparisons = {}
    for new_key, old_key in [('faces_m', 'initial_reference_faces_m'),
                             ('centers_m', 'initial_reference_centers_m'),
                             ('widths_m', 'initial_reference_widths_m')]:
        previous = np.asarray(saved[old_key])
        comparisons[new_key] = {
            'saved_values': saved[old_key],
            'each_raw_signed_new_minus_saved': (geometry[new_key] - previous).tolist(),
            'values_exactly_preserved': bool(np.array_equal(geometry[new_key], previous))}
    report = {
        'schema': 'saved_reference_partition_materialization_v1',
        'recorded_utc': datetime.now(timezone.utc).isoformat(),
        'input_parameter_path': str(args.parameters.resolve()),
        'case_parameter_path': str(args.case_output.resolve()),
        'source': {'path': str(source_path), 'field': declaration['source_field'],
                   'source_area_m2': saved['area_m2'],
                   'inserted_face_sources': saved['inserted_face_sources']},
        'case_declaration': declaration,
        'used_parameter_records': {name: {'key': key, 'record': parameters[key]}
                                   for name, key in keys.items()},
        'geometry': arrays,
        'coordinate_readback': comparisons,
        'volume_bases': {
            'new_basis': 'area * diff(explicit initial faces)',
            'saved_basis': saved['volume_basis'],
            'saved_fine_volume_sum_by_cell_m3': saved['initial_reference_bulk_m3'],
            'raw_signed_new_minus_saved_by_cell_m3': (geometry['initial_bulk_m3'] - old_bulk).tolist(),
            'raw_signed_new_sum_minus_area_half_thickness_m3': float(geometry['initial_bulk_m3'].sum() - area * length),
            'raw_signed_saved_sum_minus_area_half_thickness_m3': float(old_bulk.sum() - area * length),
            'raw_signed_new_sum_minus_saved_sum_m3': float(geometry['initial_bulk_m3'].sum() - old_bulk.sum()),
            'raw_signed_area_minus_source_area_m2': area - saved['area_m2']},
        'actual_primitive_evaluations': 1,
        'new_constructor_RHS_Jac_ODE_fit_UQ_C_G_H_selection_P38_calls': 0,
        'host_hookup_qualification': 'static source only; no FullCycle construction',
        'physical_numerical_or_grid_refinement_qualified': False,
        'new_mode3_dynamic_sampling_or_crossitems_qualified': False,
        'scope': 'Saved geometric input conversion, without a tolerance or physical acceptance decision',
        'elapsed_production_conversion_s': time.monotonic() - started}
    args.geometry_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'case_output': str(args.case_output),
                      'case_bytes': args.case_output.stat().st_size,
                      'geometry_output': str(args.geometry_output),
                      'geometry_bytes': args.geometry_output.stat().st_size,
                      'primitive_evaluations': 1,
                      'elapsed_production_conversion_s': report['elapsed_production_conversion_s']}))


if __name__ == '__main__':
    main()
