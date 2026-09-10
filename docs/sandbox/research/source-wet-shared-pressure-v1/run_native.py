"""One new N3 study with explicit wet-pressure evidence and the frozen old inputs."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch


PARENT = 'source-multicell-transition-v1/run_native.py'
PARENT_SHA = '1250733f5eddb41f4c4bbdb1bdbad235d553ecb79c98c12a7c848362774c556c'
SERIALIZER = 'exact-source-column-v1/run_native.py'
SERIALIZER_SHA = 'b0b873960bdc8bc9f2299fc3d0d008fd5fa5a9d3f7a972eb0f080ec3a2d39ab5'
EXTRA_REQUEST_CAP = 16


def load(root, name, digest):
    path = root / 'docs/sandbox/research' / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('frozen_native_helper_changed:' + name)
    spec = importlib.util.spec_from_file_location('wet_pair_' + name.split('/')[0].replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(root, directory):
    root, directory = Path(root), Path(directory)
    directory.mkdir(exist_ok=False)
    start = time.monotonic()
    record = {'status': 'started', 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'parent_runner_sha256': PARENT_SHA, 'extra_request_cap': EXTRA_REQUEST_CAP,
              'extra_requests': [], 'wet_pairs': [], 'pure_comparison_eos_attempts': 0,
              'material_qualified': False,
              'scope': 'new_actual_N3_same_inputs_explicit_shared_wet_and_dry_volume'}

    def save():
        record['wrapper_seconds'] = time.monotonic() - start
        pending = directory / 'pressure-observations.pending'
        pending.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
        pending.replace(directory / 'pressure-observations.json')

    def require(ok, reason):
        if not ok:
            raise ValueError(reason)

    code = 1
    try:
        save()
        parent = load(root, PARENT, PARENT_SHA)
        serializer = load(root, SERIALIZER, SERIALIZER_SHA).serialize
        encode = lambda value: parent.saved_record(value, serializer)
        import sludge_sandbox.source_dry_transition as transitions
        import sludge_sandbox.source_wet_shared_pressure as wet
        from sludge_sandbox.water_heos import HEOSWaterProperties
        actual_transition = transitions.evaluate_source_dry_transition
        actual_compare = transitions.compare_source_dry_candidates
        actual_collect = wet.collect_source_wet_pressure_pair
        actual_state_tp = HEOSWaterProperties.state_tp

        def guarded_compare(*args, **kwargs):
            def forbidden(*unused, **unused_kwargs):
                record['pure_comparison_eos_attempts'] += 1
                save()
                raise AssertionError('comparison_or_check_called_EOS')
            with patch.object(HEOSWaterProperties, 'state_tp', forbidden):
                return actual_compare(*args, **kwargs)

        def with_wet_strategy(refinement, **kwargs):
            column = refinement.approach.proposal.original_trial.adapter.column
            selected = refinement.approach.proposal.choice.selected_root.polynomial.cell
            require(column.cell_count == 3 and selected == 1, 'original_three_cells_middle_root')
            declarations = tuple(None if i == selected else wet.declare_source_shared_wet_volume(storage)
                                 for i, storage in enumerate(column.storages))
            record['wet_volume_declarations'] = encode(declarations)
            record['live_wet_parameter_bindings'] = [
                {'cell_index': i, 'storage_object_id': id(value.storage), 'volume_object_id': id(value.volume),
                 'same_original_storage': value.storage is column.storages[i],
                 'same_original_volume': value.volume is column.storages[i].volume}
                for i, value in enumerate(declarations) if value is not None]
            save()
            return actual_transition(refinement, **kwargs, shared_wet_volumes=declarations)

        def counted_collect(a, b, *, shared_volume, cancel=None):
            pair_index = len(record['wet_pairs'])
            item = {'pair_index': pair_index, 'storage_identity': shared_volume.storage.model_identity,
                    'storage_object_id': id(shared_volume.storage), 'volume_object_id': id(shared_volume.volume),
                    'endpoints': encode((a, b)), 'status': 'started'}
            record['wet_pairs'].append(item)
            save()

            def observed_state(self, temperature, pressure, *, phase):
                require(self is shared_volume.storage.water, 'same_actual_pair_water_provider')
                require(len(record['extra_requests']) < EXTRA_REQUEST_CAP, 'wet_pair_request_cap')
                attempt = {'ordinal': len(record['extra_requests']) + 1, 'pair_index': pair_index,
                           'provider_object_id': id(self), 'temperature_k': temperature,
                           'pressure_pa': pressure, 'phase': phase, 'status': 'started'}
                record['extra_requests'].append(attempt)
                save()
                try:
                    returned = actual_state_tp(self, temperature, pressure, phase=phase)
                    attempt.update(status='returned', water_state=encode(returned))
                    save()
                    return returned
                except Exception as exc:
                    attempt.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
                    save()
                    raise

            try:
                with patch.object(HEOSWaterProperties, 'state_tp', observed_state):
                    pair = actual_collect(a, b, shared_volume=shared_volume, cancel=cancel)
                item.update(status='returned', pair=encode(pair))
                save()
                return pair
            except Exception as exc:
                item.update(status='failed', exception_type=type(exc).__name__, exception=str(exc),
                            attempts=encode(getattr(exc, 'attempts', ())))
                save()
                raise

        with patch.object(transitions, 'evaluate_source_dry_transition', with_wet_strategy), \
             patch.object(transitions, 'compare_source_dry_candidates', guarded_compare), \
             patch.object(wet, 'collect_source_wet_pressure_pair', counted_collect), \
             (directory / 'parent-stdout.log').open('w') as stream, redirect_stdout(stream):
            code = parent.run(root, directory / 'parent-native-result.json')
        parent_raw = (directory / 'parent-native-result.json').read_bytes()
        parent_data = json.loads(parent_raw)
        record['parent_output_sha256'] = hashlib.sha256(parent_raw).hexdigest()
        record['parent_exit_code'] = code
        record['status'] = parent_data['status']
        record['actual_pressure_strategy'] = (parent_data.get('transition', {}).get('fields', {}).get('pressure_strategy'))
        record['inherited_parent_initial_strategy_label'] = parent_data.get('pressure_strategy')
        record['parent_label_scope'] = 'frozen_parent_initial_label_only; actual_strategy_is_nested_transition'
        record['distinct_extra_request_keys'] = len({
            (a['provider_object_id'], a['temperature_k'], a['pressure_pa'], a['phase'])
            for a in record['extra_requests']})
        record['numerical_event_accepted'] = parent_data.get('numerical_event_accepted', False)
        save()
        final = dict(parent_data)
        final['inherited_parent_initial_strategy_label'] = parent_data.get('pressure_strategy')
        final['pressure_strategy'] = record['actual_pressure_strategy']
        final['new_pressure_study'] = record
        (directory / 'native-result.json').write_text(json.dumps(final, indent=2, allow_nan=False) + '\n')
    except Exception as exc:
        record.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
        save()
        code = 1
    print(json.dumps({key: record.get(key) for key in ('status', 'numerical_event_accepted',
        'actual_pressure_strategy', 'distinct_extra_request_keys', 'wrapper_seconds', 'exception_type', 'exception')}
        | {'extra_requests': len(record['extra_requests']), 'wet_pairs': len(record['wet_pairs'])}))
    return code


if __name__ == '__main__':
    raise SystemExit(run(*sys.argv[1:]))
