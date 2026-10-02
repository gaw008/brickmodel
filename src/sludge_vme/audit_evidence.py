"""Retain native forward-report evidence without new physics or qualification.

Direct-file saved JSON export uses only the standard library and avoids the
sludge_vme package initializer. Optional ledger absence is an explicit source
state; ordinary required report budgets keep their existing required keys.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path


def json_native(value, *, array_type, scalar_type):
    """Use the existing ndarray/generic JSON representation with explicit types.

    The scientific host supplies its already imported NumPy type objects; this
    module imports no NumPy. Unsupported values reach json.dumps unchanged and
    fail there. No value, sign, null, boolean or qualification is inferred.
    """
    if isinstance(value, array_type):
        return value.tolist()
    if isinstance(value, scalar_type):
        return value.item()
    if isinstance(value, dict):
        return {key: json_native(item, array_type=array_type, scalar_type=scalar_type)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_native(item, array_type=array_type, scalar_type=scalar_type)
                for item in value]
    return value


def write_json(path: str | Path, data: dict, *, array_type, scalar_type) -> None:
    """Serialize supported actual host native types once through the shared layer."""
    native = json_native(data, array_type=array_type, scalar_type=scalar_type)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(native, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def retain_report_ledgers(report: dict, *, source_reference: dict) -> dict:
    """Copy complete native ledgers, including signed zeros/null/false/origins."""
    payload = {}
    states = {}
    for field in ('calcium_phase_ledger', 'entropy_ledger'):
        if field not in report:
            state = 'absent'
        else:
            state = 'explicit_null' if report[field] is None else 'present'
            payload[field] = deepcopy(report[field])
        states[field] = {'state': state, 'source_field': 'report.' + field,
            'field_path_relative_to_report': [field],
            'source_field_present': field in report}
    return {'ledger_retention': {
        'schema': 'native_forward_ledger_retention_v1',
        'source_reference': deepcopy(source_reference),
        'source_field_states': states,
        'declared_report_stages': list(report['stages']),
        'scope': 'Entire supplied report window only; no qualification for omitted stages.',
        'retention': 'Complete source ledger deepcopy; no residual, scale, potential or entropy recomputation.',
        'qualification_added': False,
        'absence_semantics': 'Absent field remains absent in payload; explicit source null remains null. No invented empty ledger or PASS.',
    }, **payload}


def forward_call_summary(report: dict, *, source_reference: dict) -> dict:
    """Keep existing ordinary metrics and complete optional ledger evidence."""
    gas_present = bool(report.get('gas_species_ledger'))
    return {'audit_schema': 'full_cycle_forward_call_summary_v2',
        'physical_consistency_passed': report['physical_consistency_passed'],
        'maximum_balance_relative_residual': max(
            value for budget in [report['whole_cycle'], *report['stages'].values()]
            for value in budget['relative_residuals'].values()),
        'forward_elapsed_s': report['elapsed_s'],
        'gas_ledger_present': gas_present,
        'gas_ledger_status': 'present' if gas_present else 'missing',
        'gas_ledger_source': 'report.gas_species_ledger',
        'gas_ledger_diagnostic': None if gas_present else
            'Missing or empty report.gas_species_ledger; no gas-ledger acceptance evidence is retained.',
        **retain_report_ledgers(report, source_reference=source_reference)}


def forward_audit(report: dict, *, source_reference: dict) -> dict:
    """Retain complete supplied budgets and native ledgers; add no verdict."""
    audit = forward_call_summary(report, source_reference=source_reference)
    audit['audit_schema'] = 'full_cycle_forward_audit_v2'
    audit.update({key: deepcopy(report[key]) for key in (
        'whole_cycle', 'stages', 'thermodynamics', 'state_domain', 'dimension_check')})
    audit['scope'] = {'stages': list(report['stages']),
        'whole_cycle_meaning': 'Entire declared process window; no claim for omitted stages.'}
    audit['gas_species_ledger'] = deepcopy(report['gas_species_ledger']) if audit['gas_ledger_present'] else None
    return audit


def export_saved_report_audits(sources: list[Path], *, report_path: list[str]) -> dict:
    """Export actual saved wrapper reports at the explicitly supplied path."""
    records = []
    for source in sources:
        wrapper = json.loads(source.read_text())
        report = wrapper
        for field in report_path:
            report = report[field]
        reference = {'kind': 'saved_JSON', 'source_file': str(source.resolve()),
            'report_path': list(report_path), 'source_schema': wrapper['schema'],
            'source_identity': wrapper['identity']}
        records.append({'source_reference': deepcopy(reference),
            'source_whole_project_complete': wrapper['whole_project_complete'],
            'audit': forward_audit(report, source_reference=reference)})
    return {'schema': 'saved_forward_audit_export_v1', 'records': records,
        'scope': 'Retention of existing saved native evidence, not a new forward/fit/UQ or independent physical acceptance.',
        'new_physical_or_material_qualification': False,
        'missing_history_backfilled': False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=Path, nargs='+')
    parser.add_argument('--report-path', nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    output = export_saved_report_audits(args.inputs, report_path=args.report_path)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(args.out), 'records': len(output['records']),
        'source_ledger_states': [record['audit']['ledger_retention']['source_field_states'] for record in output['records']],
        'new_physical_or_material_qualification': False}))


if __name__ == '__main__':
    main()
