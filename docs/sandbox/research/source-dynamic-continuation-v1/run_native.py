"""One installed, globally bounded nonstationary source continuation comparison."""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_integration_checkpoint import _same
from sludge_sandbox.exact_integration_checkpoint_codec import encode_exact_checkpoint, decode_exact_checkpoint
from sludge_sandbox.run_service import read_run_with_source_record, runtime_identity
from sludge_sandbox.source_run_service import run_source_case
from sludge_sandbox.source_study_schema import reify
from sludge_sandbox.source_trajectory import SourceOrdinaryStepSizes, open_source_trajectory


def main(root, assets, out):
    root, assets, out = map(Path, (root, assets, out))
    out.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    parent, sessions, stop_reason = None, [], None
    case = root/'data/sandbox/cases/source-nonstationary-heos-v1.json'
    values = json.loads(case.read_bytes())
    limits = values['resources']
    before = runtime_identity()

    def counts():
        if parent is None:
            return {}
        return {key:value+sum(session.recorder.counts[key]-value for session in sessions)
                for key,value in parent['counts'].items()}

    def cancel():
        nonlocal stop_reason
        if time.monotonic()-began >= limits['outer_seconds']:
            stop_reason = 'combined_outer_seconds'
        actual = counts()
        for key,limit in (('rhs_started','total_callback_cap'), ('wet_started','wet_pressure_request_cap')):
            if actual.get(key,0) >= limits[limit]:
                stop_reason = 'combined_'+limit
        return stop_reason is not None

    try:
        import sludge_sandbox.source_trajectory as module
        assert 'site-packages' in module.__file__ and 'PYTHONPATH' not in os.environ
        original = json.loads((root/'data/sandbox/cases/source-multicell-heos-v1.json').read_bytes())
        original['grid']['conductivities_w_m_k'] = [[.5,.7],[.5,.7]]
        original['initial']['temperature_k'] = [325.,327.,329.]
        assert values == original
        parent = run_source_case(case, assets, out/'parent', cancel=cancel)
        assert parent['status'] == 'completed' and parent['numerical_event_accepted'], parent
        print(json.dumps({'phase':'parent_completed','counts':parent['counts'],
                          'elapsed_seconds':time.monotonic()-began}),flush=True)
        _, _, record = read_run_with_source_record(out/'parent')
        start = record.roots['transition'].candidates[1].end
        end = T(start.seconds+F(3,64))
        sizes = SourceOrdinaryStepSizes(1/64,1/64,
            'New post-event conduction segment: explicit 1/64 s initial/maximum steps; original tolerances and resources.')

        def open_segment(name):
            session = open_source_trajectory(out/'parent',out/name,end=end,step_sizes=sizes,cancel=cancel)
            sessions.append(session)
            assert session.recorder.counts['rhs_started'] == parent['counts']['rhs_started']
            for key in ('heos_started','heos_kernel_returned','heos_returned'):
                assert session.recorder.counts[key] == parent['counts'][key]+4
            assert session.recorder.counts['initial_energy_started'] == parent['counts']['initial_energy_started']
            return session

        uninterrupted = open_segment('continuous')
        baseline = uninterrupted.advance()
        assert baseline.status == 'completed', (baseline.status,baseline.reason)
        paused = open_segment('paused')
        prefix = paused.advance(pause_after_steps=1)
        assert prefix.status == 'paused' and len(prefix.execution.result.steps) == 1
        raw_checkpoint = encode_exact_checkpoint(prefix.execution.checkpoint)
        (out/'ordinary-checkpoint.json').write_bytes(raw_checkpoint)
        restored = decode_exact_checkpoint((out/'ordinary-checkpoint.json').read_bytes())
        assert _same(restored,prefix.execution.checkpoint)
        # Pure numeric decoding does not authorize replacement of this live
        # source session's checkpoint. It continues its original issued object.
        finished = paused.advance()
        assert finished.status == 'completed', (finished.status,finished.reason)
        numerical = finished.execution.result
        assert _same(replace(baseline.execution.result,elapsed_seconds=0.),replace(numerical,elapsed_seconds=0.))
        assert _same(baseline.execution.observations,finished.execution.observations)
        assert _same(prefix.execution.result.steps,numerical.steps[:1])
        assert baseline.balances == finished.balances
        assert numerical.times_s[0] == start and numerical.times_s[-1] == end
        assert len(numerical.steps) == 3 and numerical.evaluations == 22 and numerical.rejected_trials == 0
        assert any(np.any(step.face_energy_j[1:-1]) for step in numerical.steps)
        assert np.any(numerical.states[-1].internal_energy_j != numerical.states[0].internal_energy_j)
        assert all(np.array_equal(s.amounts_mol,numerical.states[0].amounts_mol) for s in numerical.states)
        first = paused.recorder.captures[0]['evaluation'].source_evaluation
        last = paused.recorder.captures[-1]['evaluation'].source_evaluation
        assert paused.recorder.captures[-1]['time'] == end
        assert _same(reify(paused.recorder.captures[-1]['packed_input']),numerical.states[-1])
        # The checkpoint's accepted-role observation is the same final state
        # and time captured by the real source operator.
        actual_last = finished.execution.observations[-1]
        assert actual_last.role == 'accepted' and actual_last.time == end
        assert _same(actual_last.state,numerical.states[-1])
        delta_t = [F(b.inverse.point.fluid.mechanical.temperature_k)-F(a.inverse.point.fluid.mechanical.temperature_k)
                   for a,b in zip(first.cells,last.cells)]
        bounds = [F(a.inverse.temperature_error_bound_k)+F(b.inverse.temperature_error_bound_k)
                  for a,b in zip(first.cells,last.cells)]
        assert any(abs(delta)>bound for delta,bound in zip(delta_t,bounds))
        assert any(face.shared_evaluation.conduction_w != 0 for face in first.faces[1:-1])
        total_energy_changes = []
        for old,new,step in zip(numerical.states,numerical.states[1:],numerical.steps):
            assert step.face_energy_j[0] == step.face_energy_j[-1] == 0
            change = sum(F(float(x)) for x in new.internal_energy_j)-sum(F(float(x)) for x in old.internal_energy_j)
            assert abs(change) <= F(paused.reference_policy.energy_absolute_tolerance_j)
            total_energy_changes.append(float(change))
        actual = counts()
        assert actual['rhs_started'] == actual['rhs_returned'] == parent['counts']['rhs_started']+44 <= 97
        assert actual['heos_started'] == actual['heos_kernel_returned'] == actual['heos_returned'] == 12
        assert actual['initial_energy_started'] == actual['initial_energy_returned'] == 3
        assert actual['wet_started'] == actual['wet_returned'] == parent['counts']['wet_started'] <= 16
        assert stop_reason is None and time.monotonic()-began < limits['outer_seconds']
        assert runtime_identity() == before
        assert all(not getattr(result,key) for result in (baseline,finished)
                   for key in ('material_qualified','full_firing_cycle','archived_resume_authorized'))
        result = dict(status='completed',case_sha256=hashlib.sha256(case.read_bytes()).hexdigest(),
            elapsed_seconds=time.monotonic()-began,parent_elapsed_seconds=parent['elapsed_wall_seconds'],
            total_actual_counts=actual,parent_counts=parent['counts'],branch_counts=[dict(x.counts) for x in (baseline,finished)],
            exact_start=start.to_record(),exact_end=end.to_record(),physical_end_seconds=float(end.seconds),
            accepted_steps=3,evaluations_per_branch=22,temperature_change_k=list(map(float,delta_t)),
            paired_inverse_temperature_bounds_k=list(map(float,bounds)),
            energy_change_j=(numerical.states[-1].internal_energy_j-numerical.states[0].internal_energy_j).tolist(),
            global_energy_changes_j=total_energy_changes,balance_rows=len(finished.balances),
            checkpoint_sha256=hashlib.sha256(raw_checkpoint).hexdigest(),checkpoint_bytes=len(raw_checkpoint),
            controller_roundtrip=True,paths_equal_except_elapsed=True,parent_study_sha256=record.sha256,
            runtime_before=before,runtime_after=runtime_identity(),material_qualified=False,
            full_firing_cycle=False,archived_source_resume_authorized=False)
        (out/'ACCEPTANCE.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(json.dumps({k:v for k,v in result.items() if not k.startswith('runtime_')},indent=2),flush=True)
    except BaseException as exc:
        failure = dict(status='failed',exception_type=type(exc).__name__,reason=str(exc),
            elapsed_seconds=time.monotonic()-began,total_known_actual_counts=counts(),stop_reason=stop_reason,
            material_qualified=False,full_firing_cycle=False)
        (out/'FAILURE.json').write_text(json.dumps(failure,indent=2,allow_nan=False)+'\n')
        raise


if __name__ == '__main__':
    main(*sys.argv[1:])
