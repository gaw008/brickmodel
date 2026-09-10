"""One installed real-source study, reconstruction, pause and continuation."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
import time

from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.run_service import runtime_identity
from sludge_sandbox.source_run_service import run_source_case
from sludge_sandbox.source_study_record import decode_source_study
from sludge_sandbox.source_trajectory import open_source_trajectory


def main():
    root, old_assets, out = map(Path, sys.argv[1:])
    out.mkdir(parents=True, exist_ok=False)
    import sludge_sandbox.source_trajectory as module
    assert 'site-packages' in module.__file__, module.__file__
    assert 'PYTHONPATH' not in __import__('os').environ
    before = runtime_identity()
    began = time.monotonic()
    case = root / 'data/sandbox/cases/source-multicell-heos-v1.json'
    assert hashlib.sha256(case.read_bytes()).hexdigest() == '323cdc6ebbd866c81e87ac1227155357253f0b05f2384c55fadead85218c2dc5'
    parent = run_source_case(case, old_assets, out / 'parent')
    assert parent['status'] == 'completed' and parent['numerical_event_accepted'], parent
    for key in ('heos_started', 'heos_kernel_returned', 'heos_returned'):
        assert parent['counts'][key] == 4
    record = decode_source_study((out / 'parent/source-study-record.json').read_bytes())
    endpoint = record.roots['transition'].candidates[1].end
    horizon = record.metadata['effective_inputs']['horizon']
    session = open_source_trajectory(out / 'parent', out / 'continuation', end=T(endpoint.seconds + 3*horizon))
    for key in ('heos_started', 'heos_kernel_returned', 'heos_returned'):
        assert session.recorder.counts[key] == parent['counts'][key] + 4
    assert session.recorder.counts['rhs_started'] == parent['counts']['rhs_started']
    assert session.recorder.counts['initial_energy_started'] == parent['counts']['initial_energy_started']
    paused = session.advance(pause_after_steps=1)
    assert paused.status == 'paused', (paused.status, paused.reason)
    assert len(paused.execution.result.steps) == 1
    finished = session.advance()
    assert finished.status == 'completed', (finished.status, finished.reason)
    numerical = finished.execution.result
    assert numerical.times_s[0] == endpoint and numerical.times_s[-1] == session.end
    assert dict(finished.counts)['rhs_started'] == parent['counts']['rhs_started'] + numerical.evaluations
    assert len(finished.execution.observations) == numerical.evaluations
    assert len(finished.balances) == len(record.roots['transition'].balance_paths[1]) + len(numerical.steps)
    assert numerical.states[-1].amounts_mol[1, 0] == 0
    assert all(not getattr(finished, k) for k in ('material_qualified', 'full_firing_cycle', 'archived_resume_authorized'))
    assert runtime_identity() == before
    result = dict(status='completed', python=sys.executable, installed_module=module.__file__,
        elapsed_seconds=time.monotonic()-began, parent_elapsed_seconds=parent['elapsed_wall_seconds'],
        parent_counts=parent['counts'], final_counts=dict(finished.counts),
        exact_start=endpoint.to_record(), exact_end=session.end.to_record(),
        physical_end_seconds=float(session.end.seconds),
        accepted_steps=len(numerical.steps), evaluations=numerical.evaluations,
        rejected_trials=numerical.rejected_trials, attempted_trials=numerical.attempted_trials,
        segment_elapsed_seconds=numerical.elapsed_seconds,
        original_policy={k: getattr(session.policy, k) for k in (
            'maximum_steps', 'maximum_rejections', 'maximum_wall_seconds',
            'amount_absolute_tolerance_mol', 'energy_absolute_tolerance_j')},
        balance_rows=len(finished.balances), journal_events=session.recorder.journal.count,
        journal_bytes=session.recorder.journal.total_bytes,
        maximum_inventory_residual_mol=float(max(abs(x) for row in finished.balances
            for cell in row.cell_balances for x in (*cell.inventory_residual_mol, *cell.full_inventory_residual_mol))),
        maximum_energy_residual_j=float(max(abs(x) for row in finished.balances
            for cell in row.cell_balances for x in (cell.energy_residual_j,cell.full_energy_residual_j))),
        parent_study_sha256=record.sha256, runtime_before=before, runtime_after=runtime_identity(),
        material_qualified=False, full_firing_cycle=False, archived_resume_authorized=False)
    (out / 'ACCEPTANCE.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k:v for k,v in result.items() if not k.startswith('runtime_')}, indent=2))


if __name__ == '__main__':
    main()
