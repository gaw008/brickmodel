"""Reconstruct actual storage, then enclose six frozen source inverse records.

Two backend constructors perform reference-anchor checks. New endpoint EOS and
source evaluations are forbidden; this is conditional accounting, not a run of
the source integrator or an independent material/EOS certification.
"""
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

INPUT_SHA = '7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505'
AUDIT_SHA = '477744e6e77122ed8a9148bd49d5c86f931b45f95dc293440167414ea66c4f59'
DECODER_SHA = '0b7b12500a0ad2bcce7ae69c4d539efe86b839212072a28d9ff23b8d92e94df1'
CONSTRUCTOR_SHA = '9a8bbf40651c7dfc31e81c85e8367904e441e210f1c7b1666c9080dbc81b93a6'
INDEPENDENT_SHA = '711d7716bf247b693c4c92b6d0a65150e5abffc94a2b3f1d112d8f3c57d0f7ab'


def run(root, output):
    root, output = Path(root), Path(output)
    start = time.monotonic()
    result = dict(status='started', scope='actual_storage_saved_inverse_conditional_pressure',
                  input_sha256=INPUT_SHA, event_policy=None, conditional_gate=None,
                  event_admitted=False, material_qualified=False, source_certified=False,
                  soft_budget_s=20, outer_budget_s=30, backend_constructors_started=0,
                  backend_constructors_completed=0, constructor_reference_anchor_checks=0,
                  new_endpoint_evaluations_attempted=0, checks=0, cells=[])

    def store():
        result['wall_seconds'] = time.monotonic()-start
        output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')

    def require(ok, reason):
        if not ok:
            raise AssertionError(reason)
        result['checks'] += 1

    def saved(path, sha):
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == sha, 'frozen_file_changed:'+str(path))
        return raw

    def module(path, sha, name):
        saved(path, sha)
        spec = importlib.util.spec_from_file_location(name, path)
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        return value

    def forbidden(*args, **kwargs):
        result['new_endpoint_evaluations_attempted'] += 1
        raise AssertionError('new_endpoint_physics_forbidden')

    def timeout(*args):
        raise TimeoutError('saved_inverse_pressure_outer_30s_budget')

    store()
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, 30.)
    try:
        research = root/'docs/sandbox/research'
        data = json.loads(saved(research/'source-prefix-trial-v1/native-result.json', INPUT_SHA))
        audit = json.loads(saved(research/'source-prefix-trial-v1/native-audit.json', AUDIT_SHA))
        decoder = module(research/'source-net-panel-v1/replay_native.py', DECODER_SHA, 'pressure_passive_decoder')
        constructor = module(research/'source-wet-storage-v1/run_native.py', CONSTRUCTOR_SHA, 'pressure_actual_storage')
        independent = decoder.decode(json.loads(saved(
            research/'source-endpoint-comparison-v1/pressure-endpoints.json', INDEPENDENT_SHA)))
        require(audit['input_sha256'] == independent['input_sha256'] == INPUT_SHA, 'same_independent_input')
        from sludge_sandbox._heos_kernel import HEOSCandidate
        from sludge_sandbox.source_net_panel import SavedSourceSample
        from sludge_sandbox.source_endpoint_comparison import measure_source_endpoint_pair
        from sludge_sandbox.source_inverse_pressure import enclose_source_inverse_pressure
        original_init = HEOSCandidate.__init__

        def counted_init(self, *args, **kwargs):
            result['backend_constructors_started'] += 1
            original_init(self, *args, **kwargs)
            result['backend_constructors_completed'] += 1
            # The manifest-checked constructor has one native DmassT reference
            # update and ideal-derivative/entropy anchor check per success.
            result['constructor_reference_anchor_checks'] += 1

        targets = ((decoder.ExactSourceColumn, 'evaluate'), (decoder.SourceWetStorage, 'invert'),
                   (decoder.SourceWetStorage, 'evaluate'), (decoder.RigidStorage, 'evaluate_at_temperature'),
                   (decoder.WaterProperties, 'state_tp'), (decoder.WaterProperties, 'state_tp_response'),
                   (decoder.HEOSWaterProperties, 'state_tp'), (decoder.HEOSWaterProperties, 'state_tp_response'),
                   (decoder.WaterChemicalPotential, 'equilibrium_at_liquid_tp'),
                   (HEOSCandidate, 'state_tp'), (HEOSCandidate, 'saturation_pair'))
        with ExitStack() as stack:
            for cls, method in targets:
                stack.enter_context(patch.object(cls, method, forbidden))
            stack.enter_context(patch.object(HEOSCandidate, '__init__', counted_init))
            build_start = time.monotonic()
            storage, _ = constructor.make_case(root)
            result['build_seconds'] = time.monotonic()-build_start
            require(result['backend_constructors_started'] == result['backend_constructors_completed'] == 2,
                    'two_actual_backend_constructors')
            result['storage_provenance'] = decoder.encode(storage.provenance())
            trial = data['trial']
            require(trial['status'] == data['status'] == 'validated_positive_numerical_trial', 'actual_saved_trial')
            ref = trial['reference']['fields']
            captures = [trial['captures'][i]['fields'] for i in (2, -1)]
            require(ref['status'] == 'completed' and [c['role'] for c in captures] == ['prefix_terminal', 'reference'],
                    'complete_actual_endpoints')
            require(captures[0]['time'] == captures[1]['time'] == trial['end'] == ref['times_s'][-1]
                    and captures[1]['state'] == ref['states'][-1], 'same_original_endpoint_time_state')
            samples = tuple(SavedSourceSample(decoder.decode(c['state']), decoder.decode(c['evaluation']), c['role'])
                            for c in captures)
            measured = measure_source_endpoint_pair(*samples,
                operator_identity=decoder.decode(trial['operator_identity']),
                energy_identity=decoder.decode(trial['energy_identity']),
                fixed_dry_mass_kg=decoder.decode(trial['fixed_dry_mass_kg']))
            require(measured.sample_bindings == tuple(c['binding'] for c in captures), 'original_capture_bindings')
            require(len(independent['rows']) == len(samples[0].evaluation.source_states) == 3, 'three_actual_cells')
            for i, row in enumerate(independent['rows']):
                bounds = []
                for sample, other in zip(samples, row['endpoints'], strict=True):
                    evaluation = sample.evaluation
                    bound = enclose_source_inverse_pressure(storage, evaluation.source_states[i],
                                                            evaluation.source_evaluation.cells[i].inverse)
                    bound.check()
                    c = bound.continuation
                    require(c.status == 'conditional_pressure_enclosure', 'conditional_continuation_resolved')
                    require(c.global_slope_pa_k == other['global_conditional_abs_dP_dT']
                            and c.global_radius_pa == other['global_conditional_radius']
                            and c.slope_pa_k == other['bootstrapped_conditional_abs_dP_dT']
                            and c.radius_pa == other['bootstrapped_conditional_radius'], 'independent_exact_pressure_algebra')
                    require(bound.inverse.point.extra_pressure_error_pa > 0 and bound.initial_bounds_pa[2] > 0,
                            'actual_nonzero_volume_error_retained')
                    bounds.append(bound)
                a, b = bounds
                difference = abs(F(a.inverse.point.pressure_pa)-F(b.inverse.point.pressure_pa))
                difference += a.continuation.radius_pa+b.continuation.radius_pa
                require(difference == row['conditional_full_P_difference_upper'], 'independent_pair_bound')
                result['cells'].append(dict(cell=i, conditional_bound_pa=decoder.encode(difference),
                    conditional_bound_pa_display=float(difference), endpoint_bounds=[{
                        f.name: decoder.encode(getattr(bound, f.name)) for f in fields(bound)
                        if f.name not in ('storage', 'state', 'inverse')} for bound in bounds]))
            require(result['new_endpoint_evaluations_attempted'] == 0, 'no_new_endpoint_physics')
            require(time.monotonic()-start < 20, 'saved_inverse_pressure_soft_20s_budget')
        result['status'] = 'conditional_saved_inverse_pressure_completed'
        store()
        print(json.dumps({k: result[k] for k in ('status', 'checks', 'build_seconds', 'wall_seconds',
              'backend_constructors_completed', 'constructor_reference_anchor_checks', 'new_endpoint_evaluations_attempted')}))
    except Exception as exc:
        result.update(status='failed', exception_type=type(exc).__name__, reason=str(exc))
        store()
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        signal.signal(signal.SIGALRM, previous)


if __name__ == '__main__':
    run(*sys.argv[1:])
