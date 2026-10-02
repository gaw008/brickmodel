"""Project effective declared physical conditions; no model or source inference."""
from __future__ import annotations

from copy import deepcopy
import argparse
import json
from pathlib import Path


def project_declared_case_conditions(config: dict, case_reference: str) -> dict:
    """Preserve legacy65 while using only this case's actual stages and gases.

    Complete records keep their original sources/statuses. This projection
    describes supplied configuration, never measured protocol or compatibility.
    """
    parameters = config['parameters']
    legacy_keys = config['observation_contract']['condition_parameter_keys']
    legacy_configuration = {'stages': list(config['stages']), 'parameters': {
        key: {field: deepcopy(parameters[key][field]) for field in ('value', 'unit')}
        for key in legacy_keys}}
    stage_keys = []
    gas_species = [species['id'] for species in config['species'] if species['phase'] == 'gas']
    for stage in config['stages']:
        stage_keys.extend(f'process.{stage}.{field}' for field in ('end', 'temperature'))
        stage_keys.extend(f'gas.stage.{stage}.{species}' for species in gas_species)
    # Historical stage conditions remain in legacy; active conditions are
    # enumerated from the supplied case, never from a permanent synthetic list.
    effective_keys = [key for key in legacy_keys
        if not key.startswith('gas.stage.') and not (
            key.startswith('process.') and len(key.split('.')) == 3
            and key.split('.')[-1] in ('end', 'temperature'))]
    candidates = [key for key in parameters if key.startswith('recipe.')] + stage_keys
    unavailable = []
    for key in candidates:
        if key in effective_keys:
            continue
        if key not in parameters:
            unavailable.append({'parameter_key': key, 'reason': 'missing_from_case'})
            continue
        effective_keys.append(key)
    configuration = {'stages': list(config['stages']), 'parameters': {
        key: {field: deepcopy(parameters[key][field]) for field in ('value', 'unit')}
        for key in effective_keys}}
    return {'schema': 'declared_case_condition_projection_v2',
        'case_reference': case_reference,
        'legacy_configuration': legacy_configuration,
        'legacy_records': {key: deepcopy(parameters[key]) for key in legacy_keys},
        'configuration': configuration,
        'records': {key: deepcopy(parameters[key]) for key in effective_keys},
        'added_parameter_keys': [key for key in effective_keys if key not in legacy_keys],
        'inactive_legacy_condition_keys': [key for key in legacy_keys if key not in effective_keys],
        'unavailable_conditions': unavailable,
        'qualification': {'declared_case_only': True, 'measured_protocol': False,
            'observation_mapping_executed': False, 'model_calls': 0,
            'physical_or_material_acceptance': False}}


def describe_case_transformation(source: dict, derived: dict, *, operation: str) -> dict:
    """Record actual in-memory changes without inventing a saved case file."""
    return {'operation': operation, 'source_stages': deepcopy(source['stages']),
        'derived_stages': deepcopy(derived['stages']), 'saved_derived_file': None,
        'changed_parameter_records': {
            key: {'source_record': deepcopy(source['parameters'][key]),
                'derived_record': deepcopy(value)}
            for key, value in derived['parameters'].items()
            if value != source['parameters'][key]}}


def declared_case_condition_bundle(config: dict, case_reference: str, *,
                                   case_transformations: list[dict]) -> dict:
    """Create v2 source-complete declaration with explicit caller provenance."""
    return {'schema': 'declared_case_condition_bundle_v2',
        'case_reference': case_reference,
        'case_provenance': {'original_case_reference': case_reference,
            'transformations': deepcopy(case_transformations),
            'derived_saved_file': None},
        'projection': project_declared_case_conditions(config, case_reference),
        'sources': deepcopy(config['sources']),
        'identity': 'declared_configuration_not_measured_protocol',
        'physical_or_material_acceptance': False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.parameters.read_text())
    bundle = declared_case_condition_bundle(config, str(args.parameters.resolve()),
        case_transformations=[])
    args.out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(args.out), 'case_reference': bundle['case_reference'],
        'legacy_conditions': len(bundle['projection']['legacy_configuration']['parameters']),
        'effective_conditions': len(bundle['projection']['configuration']['parameters']),
        'model_calls': 0}))


if __name__ == '__main__':
    main()
