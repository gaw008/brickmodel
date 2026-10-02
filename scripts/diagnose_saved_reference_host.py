"""Run the declared single initial-state host/RHS production diagnostic.

Source-checkout offline entry; parameter values and operation scope are in root.
The calling existing supervisor supplies the unique time/output allocation.
"""
from __future__ import annotations
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sludge_vme.models.full_cycle import read_parameters
from sludge_vme.models.instantaneous_diagnostics import saved_reference_host_case, observe_initial_rhs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    args = parser.parse_args()
    root = read_parameters(args.parameters)
    declaration = root['public_reference_cases']['saved_reference_host']
    project = args.parameters.resolve().parent
    case_path = project / declaration['case_output']
    result_path = project / declaration['diagnostic_output']
    events_path = project / declaration['events_output']
    case = saved_reference_host_case(root)
    case_path.write_text(json.dumps(case, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    case = read_parameters(case_path)
    try:
        retained = json.loads((project / declaration['retained_failure_report']).read_text())['retained_failures']
        report = observe_initial_rhs(case, events_path=events_path, retained_failures=retained)
    except BaseException as error:
        failure = {'recorded_utc': datetime.now(timezone.utc).isoformat(),
                   'exception_type': type(error).__name__, 'exception': str(error),
                   'scope': 'Original sole operation failure; no retry or alternate context',
                   'whole_project_complete': False}
        result_path.with_name('failure.json').write_text(json.dumps(failure, ensure_ascii=False, indent=2) + '\n')
        raise
    result_path.write_text(json.dumps(report, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    print(json.dumps({'diagnostic': str(result_path), 'diagnostic_bytes': result_path.stat().st_size,
                      'case_bytes': case_path.stat().st_size, 'host_instances': report['make_cycle_instance_calls'],
                      'RHS_calls': report['RHS_calls'], 'whole_project_complete': False}))


if __name__ == '__main__':
    main()
