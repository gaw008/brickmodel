"""Replay frozen native sample pairs through source root ordering, without EOS."""
from contextlib import ExitStack
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time
from unittest.mock import patch

from sludge_sandbox.source_net_roots import order_source_panel_roots


def run(root, output):
    started = time.monotonic()
    result = {'status': 'started', 'scope': 'saved_numerical_first_zero_order_only',
              'trials': [], 'soft_budget_s': 30, 'outer_budget_s': 45}

    def save():
        Path(output).write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')

    def require(ok, reason):
        if not ok:
            raise ValueError(reason)

    def timeout(*_):
        raise TimeoutError('pure_root_replay_45s_budget_exceeded')

    save()
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, 45.)
    try:
        # Reuse the reviewed, fixed 35-class passive decoder. No class or
        # module name from the saved input is imported dynamically.
        helper = Path(root)/'docs/sandbox/research/source-net-panel-v1/replay_native.py'
        helper_sha = hashlib.sha256(helper.read_bytes()).hexdigest()
        require(helper_sha == '0b7b12500a0ad2bcce7ae69c4d539efe86b839212072a28d9ff23b8d92e94df1',
                'reviewed_replay_helper_hash_mismatch')
        spec = importlib.util.spec_from_file_location('fixed_source_panel_replay', helper)
        replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(replay)
        folder = Path(root)/'docs/sandbox/research/exact-source-column-v1'
        raw = (folder/'native-result.json').read_bytes()
        audit_raw = (folder/'native-audit.json').read_bytes()
        require(hashlib.sha256(raw).hexdigest() == replay.INPUT_SHA, 'native_hash_mismatch')
        require(hashlib.sha256(audit_raw).hexdigest() == replay.AUDIT_SHA, 'audit_hash_mismatch')
        data, audit = json.loads(raw), json.loads(audit_raw)
        require(audit['input_sha256'] == replay.INPUT_SHA and len(data['captures']) == 47
                and len(audit['trials']) == 7, 'fixed_native_trial_set')
        result.update(input_sha256=replay.INPUT_SHA, audit_sha256=replay.AUDIT_SHA,
                      replay_helper_sha256=helper_sha)
        targets = ((replay.ExactSourceColumn, 'evaluate'), (replay.SourceWetStorage, 'invert'),
                   (replay.SourceWetStorage, 'evaluate'), (replay.RigidStorage, 'evaluate_at_temperature'),
                   (replay.WaterProperties, 'state_tp'), (replay.HEOSWaterProperties, 'state_tp'),
                   (replay.WaterChemicalPotential, 'equilibrium_at_liquid_tp'))
        with ExitStack() as stack:
            for cls, name in targets:
                stack.enter_context(patch.object(cls, name, replay.reject_physics))
            for trial in audit['trials']:
                require(time.monotonic()-started < 30, 'pure_root_replay_soft_budget_exceeded')
                indices = (trial['capture_start'], trial['capture_start']+3)
                captures = tuple(replay.decode(data['captures'][i]) for i in indices)
                for capture, i in zip(captures, indices):
                    require(replay.canonical(replay.encode(capture)) ==
                            replay.canonical(data['captures'][i]), 'capture_roundtrip_mismatch')
                first, interior = (replay.SavedSourceSample(c['packed_input'], c['evaluation'], role)
                                   for c, role in zip(captures, ('original_trial_full_start',
                                                                'first_half_euler_interior')))
                upper = replay.ExactEventTime(F(trial['end']))
                require(first.evaluation.time.seconds == F(trial['start']) and
                        interior.evaluation.time.seconds == (F(trial['start'])+F(trial['end']))/2,
                        'original_trial_times')
                panel = replay.build_source_panel(first, interior, upper,
                    operator_identity=first.evaluation.operator_identity,
                    energy_identity=first.state.energy_model_identity,
                    fixed_dry_mass_kg=tuple(s.solid_mass_kg[0] for s in first.evaluation.source_states))
                roots = order_source_panel_roots(panel)
                roots.check()
                require(roots.order.status == 'no_roots' and roots.order.complete is True
                        and len(roots.order.exclusions) == 12 and not roots.order.roots
                        and not roots.order.zero_initial_labels, 'expected_native_panel_positive')
                result['trials'].append(replay.encode(dict(
                    capture_indices=indices, original_trial=trial, start=roots.start, upper=roots.upper,
                    operator_identity=roots.operator_identity, sample_bindings=roots.sample_bindings,
                    order=roots.order, qualification=roots.qualification,
                    material_qualified=False, physical_trajectory_or_event_admitted=False)))
                save()
        require(time.monotonic()-started < 30, 'pure_root_replay_soft_budget_exceeded')
        result.update(status='completed', elapsed_s=time.monotonic()-started)
        save()
        return 0
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, reason=str(exc),
                      elapsed_s=time.monotonic()-started)
        save()
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        signal.signal(signal.SIGALRM, previous)


if __name__ == '__main__':
    sys.exit(run(*sys.argv[1:]))
