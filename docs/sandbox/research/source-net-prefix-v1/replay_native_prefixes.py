"""Fixed native source records, independent numerical prefixes, no EOS."""
from contextlib import ExitStack
from dataclasses import fields
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time
from unittest.mock import patch

from sludge_sandbox.integration import IntegrationPolicy
from sludge_sandbox.source_net_prefix import build_source_prefix, audit_source_prefixes


def run(root, output):
    started = time.monotonic()
    result = {'status': 'started', 'scope': 'independent_saved_numerical_prefixes_only',
              'trials': [], 'soft_budget_s': 30, 'outer_budget_s': 45}

    def save():
        Path(output).write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')

    def require(ok, reason):
        if not ok:
            raise ValueError(reason)

    def timeout(*_):
        raise TimeoutError('pure_prefix_replay_45s_budget_exceeded')

    save()
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, 45.)
    try:
        helper = Path(root)/'docs/sandbox/research/source-net-panel-v1/replay_native.py'
        helper_sha = hashlib.sha256(helper.read_bytes()).hexdigest()
        require(helper_sha == '0b7b12500a0ad2bcce7ae69c4d539efe86b839212072a28d9ff23b8d92e94df1',
                'reviewed_replay_helper_hash_mismatch')
        spec = importlib.util.spec_from_file_location('fixed_source_panel_replay', helper)
        replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(replay)
        folder = Path(root)/'docs/sandbox/research/exact-source-column-v1'
        raw, audit_raw = (folder/'native-result.json').read_bytes(), (folder/'native-audit.json').read_bytes()
        require(hashlib.sha256(raw).hexdigest() == replay.INPUT_SHA, 'native_hash_mismatch')
        require(hashlib.sha256(audit_raw).hexdigest() == replay.AUDIT_SHA, 'audit_hash_mismatch')
        data, old_audit = json.loads(raw), json.loads(audit_raw)
        require(old_audit['input_sha256'] == replay.INPUT_SHA and len(data['captures']) == 47
                and len(old_audit['trials']) == 7, 'fixed_native_trial_set')
        require(data['policy']['type'] == 'sludge_sandbox.integration.IntegrationPolicy', 'original_policy_type')
        policy = IntegrationPolicy(**data['policy']['fields'])
        require(replay.canonical(replay.encode(policy)) == replay.canonical(data['policy']),
                'complete_original_policy_roundtrip')
        result.update(input_sha256=replay.INPUT_SHA, audit_sha256=replay.AUDIT_SHA,
                      replay_helper_sha256=helper_sha, original_policy=replay.encode(policy))
        targets = ((replay.ExactSourceColumn, 'evaluate'), (replay.SourceWetStorage, 'invert'),
                   (replay.SourceWetStorage, 'evaluate'), (replay.RigidStorage, 'evaluate_at_temperature'),
                   (replay.WaterProperties, 'state_tp'), (replay.HEOSWaterProperties, 'state_tp'),
                   (replay.WaterChemicalPotential, 'equilibrium_at_liquid_tp'))
        with ExitStack() as stack:
            for cls, name in targets:
                stack.enter_context(patch.object(cls, name, replay.reject_physics))
            for trial in old_audit['trials']:
                require(time.monotonic()-started < 30, 'pure_prefix_replay_soft_budget_exceeded')
                indices = (trial['capture_start'], trial['capture_start']+3)
                captures = tuple(replay.decode(data['captures'][i]) for i in indices)
                for capture, i in zip(captures, indices):
                    require(replay.canonical(replay.encode(capture)) == replay.canonical(data['captures'][i]),
                            'full_capture_roundtrip_mismatch')
                first, interior = (replay.SavedSourceSample(c['packed_input'], c['evaluation'], role)
                                   for c, role in zip(captures, ('original_trial_full_start',
                                                                'first_half_euler_interior')))
                end = replay.ExactEventTime(F(trial['end']))
                require(first.evaluation.time.seconds == F(trial['start']) and
                        interior.evaluation.time.seconds == (F(trial['start'])+F(trial['end']))/2,
                        'original_trial_times')
                panel = replay.build_source_panel(first, interior, end,
                    operator_identity=first.evaluation.operator_identity,
                    energy_identity=first.state.energy_model_identity,
                    fixed_dry_mass_kg=tuple(s.solid_mass_kg[0] for s in first.evaluation.source_states))
                prefix = build_source_prefix(panel, end, policy=policy)
                prefix.check()
                # The original trial inputs are not a contiguous trajectory of
                # this new quadrature. Audit each singleton; do not concatenate.
                audit = audit_source_prefixes((prefix,))
                audit.check()
                require(prefix.status == 'strictly_positive_numerical_prefix'
                        and len(prefix.minima) == 12 and all(row[3] > 0 for row in prefix.minima),
                        'expected_positive_native_numerical_prefix')
                result['trials'].append(replay.encode(dict(
                    capture_indices=indices, original_trial=trial, sample_bindings=panel.sample_bindings,
                    operator_identity=panel.operator_identity, energy_identity=panel.energy_identity,
                    fixed_dry_mass_kg=panel.fixed_dry_mass_kg,
                    prefix={f.name: getattr(prefix, f.name) for f in fields(prefix) if f.name != 'panel'},
                    singleton_audit={f.name: getattr(audit, f.name) for f in fields(audit) if f.name != 'prefixes'},
                    material_qualified=False, physical_trajectory_or_event_admitted=False)))
                save()
        require(time.monotonic()-started < 30, 'pure_prefix_replay_soft_budget_exceeded')
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
