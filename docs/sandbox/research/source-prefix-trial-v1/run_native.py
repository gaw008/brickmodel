"""One prepared actual-source trial; no physical evaluation at import."""
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


POLICY_VALUES = (1/1024, 1/1024, 1/16384, 1e-8, 1e-7, 1e-3, 1., 1e5, 4, 4, 180.)
DURATION = F(1, 16384)
MAXIMUM_CALLBACKS = 32
OUTER_SECONDS = 210.
HELPERS = {
    'exact-source-column-v1/run_native.py': 'b0b873960bdc8bc9f2299fc3d0d008fd5fa5a9d3f7a972eb0f080ec3a2d39ab5',
    'source-liquid-column-v1/run_native.py': '383832ab0c86a0a2c9c8a44799229e8775c0fb8f1744b8fcd64dada40aac12a0',
    'programmed-source-column-v1/run_native.py': 'd51367e36fb5234a27c5455a454766da4a00057fc17819516f8489bf1b36f543',
}


def run(root, output):
    root, output = Path(root), Path(output)
    started = time.monotonic()
    result = {'status': 'started', 'scope': 'single_actual_positive_source_numerical_trial',
              'material_qualified': False, 'outer_seconds': OUTER_SECONDS,
              'maximum_callbacks': MAXIMUM_CALLBACKS, 'policy_values': POLICY_VALUES,
              'duration_s': {'numerator': 1, 'denominator': 16384}, 'captures': []}

    def save():
        result['wall_seconds'] = time.monotonic()-started
        temporary = output.with_suffix('.pending')
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
        temporary.replace(output)

    def require(ok, reason):
        if not ok:
            raise AssertionError(reason)

    def timeout(*_):
        result['outer_timeout_requested'] = True
        raise TimeoutError('outer_210s_budget_exceeded')

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, OUTER_SECONDS)
    save()
    try:
        for name, expected in HELPERS.items():
            require(hashlib.sha256((root/'docs/sandbox/research'/name).read_bytes()).hexdigest()==expected,
                    'prepared_constructor_changed:'+name)
        helper = root/'docs/sandbox/research/exact-source-column-v1/run_native.py'
        spec = importlib.util.spec_from_file_location('frozen_source_constructor', helper)
        prior = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prior)
        encode = prior.serialize
        from sludge_sandbox.exact_source_column import ExactSourceColumn
        from sludge_sandbox.exact_event_clock import ExactEventTime as T
        from sludge_sandbox.integration import IntegrationPolicy
        from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
        adapter, initial, mobility_hash = prior.construct(root)
        policy = IntegrationPolicy(*POLICY_VALUES)
        result.update(status='constructed', constructor_hashes=HELPERS,
            initial=encode(initial), adapter_provenance=encode(adapter.provenance()),
            mobility_sha256=mobility_hash, policy=encode(policy), build_seconds=time.monotonic()-started)
        save()
        original = ExactSourceColumn.evaluate

        def observed(self, state, at):
            require(self is adapter, 'only_prepared_adapter_may_evaluate')
            item = {'ordinal': len(result['captures'])+1, 'packed_input': encode(state), 'time': encode(at)}
            result['captures'].append(item)
            result['pending_callback'] = item['ordinal']
            save()
            try:
                value = original(self, state, at)
                item['evaluation'] = encode(value)
                result.pop('pending_callback', None)
                save()
                return value
            except Exception as exc:
                item.update(exception_type=type(exc).__name__, exception=str(exc))
                result.pop('pending_callback', None)
                save()
                raise

        with patch.object(ExactSourceColumn, 'evaluate', observed):
            trial = evaluate_source_prefix_trial(adapter, initial, start=T(F()), end=T(DURATION),
                integration_policy=policy, maximum_callbacks=MAXIMUM_CALLBACKS)
        # Persist every returned field before auditing; the live adapter is
        # represented by its separately retained complete source provenance.
        result.update(status=trial.status, trial={f.name: encode(getattr(trial, f.name))
                      for f in fields(trial) if f.name!='adapter'})
        save()
        require(len(result['captures'])==len(trial.captures), 'every_actual_attempt_retained')
        trial.check()
        result['retained_evidence_check'] = 'passed'
        save()
        require(trial.status=='validated_positive_numerical_trial', 'positive_trial_not_validated')
        require(trial.reference.status=='completed' and trial.reference.times_s[-1]==T(DURATION),
                'complete_same_interval_reference_required')
        print(json.dumps({'status': trial.status, 'callbacks': len(trial.captures),
            'discrepancy': trial.discrepancy, 'reference_steps': len(trial.reference.steps),
            'reference_rejections': trial.reference.rejected_trials,
            'trial_seconds': trial.elapsed_seconds, 'wall_seconds': result['wall_seconds']}))
        return 0
    except Exception as exc:
        result.update(status='resource_limit' if result.get('outer_timeout_requested') else 'failed',
                      exception_type=type(exc).__name__, exception=str(exc))
        save()
        print(json.dumps({k: result.get(k) for k in ('status','exception_type','exception','wall_seconds')}))
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        signal.signal(signal.SIGALRM, previous)


if __name__=='__main__':
    sys.exit(run(*sys.argv[1:]))
