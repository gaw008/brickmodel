"""Compare frozen actual endpoints. No host restoration or native EOS run."""
from contextlib import ExitStack
from dataclasses import fields
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

INPUT_SHA = '7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505'
AUDIT_SHA = '477744e6e77122ed8a9148bd49d5c86f931b45f95dc293440167414ea66c4f59'
DECODER_SHA = '0b7b12500a0ad2bcce7ae69c4d539efe86b839212072a28d9ff23b8d92e94df1'


def run(root, output, independent):
    root, output, independent = Path(root), Path(output), Path(independent)
    started = time.monotonic()
    result = {'status':'started','scope':'saved_actual_endpoint_accounting_not_trial_restoration',
              'input_sha256':INPUT_SHA,'audit_sha256':AUDIT_SHA,'decoder_sha256':DECODER_SHA,
              'new_source_evaluations':0,'event_policy':None,
              'event_gates':'not_evaluated_missing_explicit_policy',
              'full_inverse_pressure_gate':'unresolved','event_time_gate':'not_evaluated',
              'event_admitted':False,'material_qualified':False,'checks':0}
    def require(ok, reason):
        if not ok:
            raise AssertionError(reason)
        result['checks'] += 1
    def saved(path, expected):
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, 'frozen_file_changed:'+str(path))
        return raw
    def store():
        result['wall_seconds'] = time.monotonic()-started
        output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    store()
    try:
        research = root/'docs/sandbox/research'
        data = json.loads(saved(research/'source-prefix-trial-v1/native-result.json', INPUT_SHA))
        audit = json.loads(saved(research/'source-prefix-trial-v1/native-audit.json', AUDIT_SHA))
        require(audit['input_sha256'] == INPUT_SHA, 'same_audited_input')
        decoder_path = research/'source-net-panel-v1/replay_native.py'
        saved(decoder_path, DECODER_SHA)
        spec = importlib.util.spec_from_file_location('frozen_passive_source_decoder',decoder_path)
        decoder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(decoder)
        from sludge_sandbox.source_net_panel import SavedSourceSample
        from sludge_sandbox.source_endpoint_comparison import measure_source_endpoint_pair
        targets = ((decoder.ExactSourceColumn,'evaluate'),(decoder.SourceWetStorage,'invert'),
                   (decoder.SourceWetStorage,'evaluate'),(decoder.RigidStorage,'evaluate_at_temperature'),
                   (decoder.WaterProperties,'state_tp'),(decoder.HEOSWaterProperties,'state_tp'),
                   (decoder.WaterChemicalPotential,'equilibrium_at_liquid_tp'))
        with ExitStack() as stack:
            for cls, method in targets:
                stack.enter_context(patch.object(cls,method,decoder.reject_physics))
            trial = data['trial']
            require(trial['status'] == data['status'] == 'validated_positive_numerical_trial',
                    'saved_successful_trial_required')
            ref = trial['reference']['fields']
            require(ref['status'] == 'completed', 'saved_complete_reference_required')
            captures = [trial['captures'][i]['fields'] for i in (2,-1)]
            require([x['role'] for x in captures] == ['prefix_terminal','reference'], 'actual_endpoint_roles')
            require(captures[0]['time'] == captures[1]['time'] == trial['end'] == ref['times_s'][-1],
                    'saved_same_exact_endpoint')
            require(captures[1]['state'] == ref['states'][-1], 'saved_reference_state')
            samples = tuple(SavedSourceSample(decoder.decode(x['state']),decoder.decode(x['evaluation']),x['role'])
                            for x in captures)
            measurement = measure_source_endpoint_pair(*samples,
                operator_identity=decoder.decode(trial['operator_identity']),
                energy_identity=decoder.decode(trial['energy_identity']),
                fixed_dry_mass_kg=decoder.decode(trial['fixed_dry_mass_kg']))
            require(measurement.sample_bindings == tuple(x['binding'] for x in captures),
                    'original_actual_capture_bindings')
            measurement.check()
            independent_raw = independent.read_bytes()
            result['independent_sha256'] = hashlib.sha256(independent_raw).hexdigest()
            other = decoder.decode(json.loads(independent_raw))
            require(other['input_sha256'] == INPUT_SHA and len(other['rows']) == len(samples[0].state.amounts_mol),
                    'independent_same_input_and_count')
            for i,row in enumerate(other['rows']):
                require(measurement.amount_differences_mol[i] == row['absolute_N_differences'], 'independent_N')
                require(measurement.energy_differences_j[i] == row['absolute_U_difference'], 'independent_U')
                require(measurement.temperature_bounds_k[i] == row['T_difference_plus_errors'], 'independent_T')
                require(measurement.reported_pressure_bounds_pa[i] == row['reported_P_difference_plus_errors'], 'independent_P')
                for sample in samples:
                    point = sample.evaluation.source_evaluation.cells[i].inverse.point
                    require(point.extra_pressure_error_pa > 0 and point.pressure_error_pa > point.fluid.pressure_error_bound_pa,
                            'nonzero_available_volume_error_included')
            require(measurement.comparison_time_offset_s == F(), 'exact_same_time_offset')
            result['measurement'] = {f.name:decoder.encode(getattr(measurement,f.name))
                                     for f in fields(measurement) if f.name != 'samples'}
            result['maxima_display'] = dict(zip(('N_mol','U_j','T_k','reported_T_P_pa'),map(float,measurement.maxima)))
        result['status'] = 'saved_endpoint_accounting_completed'
        store()
        print(json.dumps({k:result[k] for k in ('status','checks','maxima_display','wall_seconds')}))
        return 0
    except Exception as exc:
        result.update(status='failed',exception_type=type(exc).__name__,reason=str(exc))
        store()
        raise


if __name__ == '__main__':
    sys.exit(run(*sys.argv[1:]))
