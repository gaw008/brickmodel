"""Installed-package passive preservation and CLI check; never execute the model."""
from collections import Counter
from collections.abc import Mapping
from contextlib import ExitStack, redirect_stdout
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import signal
import sys
import time
from unittest.mock import patch

import numpy as np

SOURCE_SHA = '6c55383e8d2063ed6c81f2126b40542ba44ee173fc1671b227573b908bfbfc53'
OMITTED_LIVE_FIELDS = {
    'SourcePrefixTrial': {'adapter'}, 'SourceTerminal': {'dry_adapter'},
    'SourceInversePressure': {'storage'}, 'SourceDryPressure': {'storage'},
    'SourceSharedDryVolume': {'storage'}, 'SourceSharedWetVolume': {'storage'},
}


def run(source, output, trace):
    from sludge_sandbox.cli import main
    from sludge_sandbox.exact_event_clock import ExactEventTime
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.source_study_record import decode_source_study
    from sludge_sandbox.source_study_schema import SourceStudyNode
    from sludge_sandbox.source_study_service import inspect_source_study, query_source_study
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.water_heos import HEOSWaterProperties

    started = time.perf_counter()
    counts = Counter()
    trace['checks'] = counts
    trace['stage'] = 'read_original'
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    original = json.loads(raw)
    installed = Path(next(iter(importlib.util.find_spec('sludge_sandbox').submodule_search_locations)))
    assert 'site-packages' in installed.parts
    target = output / 'study-record.json'
    assert not target.exists()

    def forbidden(*args, **kwargs):
        counts['forbidden_live_calls'] += 1
        raise AssertionError('passive record invoked live physics')

    def invoke_cli(arguments, name):
        trace['stage'] = name
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                code = main(arguments)
        finally:
            (output / (name + '.json')).write_text(stream.getvalue())
        assert code == 0, name + ': CLI returned ' + str(code)
        return json.loads(stream.getvalue())

    def check(before, after, path):
        counts['retained_value_visits'] += 1
        if type(before) is dict and set(before) == {'numerator', 'denominator'}:
            assert type(after) is Fraction, path
            assert (before['numerator'], before['denominator']) == (after.numerator, after.denominator), path
            counts['exact_fractions'] += 1
        elif type(before) is dict and set(before) == {'dtype', 'shape', 'values'}:
            assert type(after) is np.ndarray and str(after.dtype) == before['dtype'], path
            assert list(after.shape) == before['shape'], path
            expected = np.asarray(before['values'], dtype=np.float64)
            assert expected.shape == after.shape and expected.tobytes() == after.tobytes(), path
            assert not after.flags.writeable, path
            counts['arrays'] += 1
            counts['array_scalars'] += after.size
        elif type(before) is dict and set(before) == {'type', 'fields'}:
            if before['type'] == 'sludge_sandbox.exact_event_clock.ExactEventTime':
                assert type(after) is ExactEventTime, path
                assert set(before['fields']) == {'seconds'}, path
                check(before['fields']['seconds'], after.seconds, path + '/seconds')
                counts['exact_times'] += 1
                return
            if type(after) is SourceStudyNode:
                assert after.kind == before['type'], path
                extras = OMITTED_LIVE_FIELDS.get(before['type'].rsplit('.', 1)[-1], set())
                values = after.values
            else:
                assert is_dataclass(after) and not isinstance(after, type), path
                assert type(after).__module__ + '.' + type(after).__qualname__ == before['type'], path
                extras = set()
                values = {field.name: getattr(after, field.name) for field in fields(after)}
            assert set(values) == set(before['fields']) | extras, path
            for field in extras:
                reference = values[field]
                assert type(reference) is SourceStudyNode, path
                assert reference.kind == 'sludge_sandbox.source_study_schema.SourceLiveReference', path
                assert reference.available is False and reference.modes is None, path
                assert reference.scope == 'archived_reference_not_live_object_or_resume_authority', path
                counts['explicit_missing_live_references'] += 1
            for key, value in before['fields'].items():
                check(value, values[key], path + '/' + key)
            counts['complete_typed_occurrences'] += 1
        elif type(before) is dict:
            assert isinstance(after, Mapping) and set(before) == set(after), path
            for key, value in before.items():
                check(value, after[key], path + '/' + key)
            counts['mappings'] += 1
        elif type(before) is list:
            assert type(after) is tuple and len(before) == len(after), path
            for index, (a, b) in enumerate(zip(before, after)):
                check(a, b, path + '/' + str(index))
            counts['sequences'] += 1
        else:
            assert type(before) is type(after), path
            assert (before.hex() == after.hex()) if type(before) is float else (before == after), path
            counts['scalars'] += 1

    with ExitStack() as stack:
        for cls in (ExactSourceColumn, SourceWetStorage, WaterProperties, HEOSWaterProperties):
            stack.enter_context(patch.object(cls, '__init__', forbidden))
        for cls in (ExactSourceColumn, SourceWetStorage):
            stack.enter_context(patch.object(cls, 'evaluate', forbidden))
        for cls in (WaterProperties, HEOSWaterProperties):
            stack.enter_context(patch.object(cls, 'state_tp', forbidden))
        imported = invoke_cli(['source-study-import', str(source), '--output', str(target)], 'cli-import')
        trace['stage'] = 'decode_canonical'
        canonical = target.read_bytes()
        record = decode_source_study(canonical)
        trace['stage'] = 'compare_all_original_values'
        restored = dict(record.metadata) | dict(record.roots) | {'captures': record.captures}
        check(original, restored, 'original')
        assert len(record.captures) == len(record.observations) == 32
        assert all(observation is not None for observation in record.observations)
        for index, observation in enumerate(record.observations):
            capture = original['captures'][index]
            path = 'observation/' + str(index)
            check(capture['packed_input'], observation.sample.state, path + '/state')
            check(capture['evaluation'], observation.sample.evaluation, path + '/evaluation')
            check(capture['phase'], observation.sample.role, path + '/role')
            check(capture['time'], observation.sample.evaluation.time, path + '/time')
            check(capture['operator_identity'], observation.context.operator_identity, path + '/operator')
            check(capture['energy_identity'], observation.context.energy_identity, path + '/energy')
            check(capture['interface_modes'], observation.context.interface_modes, path + '/modes')
            counts['complete_indexed_observations'] += 1
        assert record.roots['transition'].numerical_event_accepted is True
        assert record.material_qualified is False and record.resume_authorized is False
        assert record.provenance['original_file_sha256'] == SOURCE_SHA
        value_path = 'transition/cell_selected_pressure_gates'
        selected = query_source_study(record, value_path)
        assert selected == [[True, True, True], [True, True, True]]
        options = dict(capture_index=16, cell_index=1, value_path=value_path)
        trace['stage'] = 'python_inspect'
        expected = inspect_source_study(target, **options)
        observed = invoke_cli(['source-study-inspect', str(target), '--capture-index', '16',
                              '--cell', '1', '--path', value_path], 'cli-inspect')
        assert observed == expected
        counts['cli_python_parity'] += 1
        assert imported['record_sha256'] == record.sha256
        assert counts['forbidden_live_calls'] == 0
        (output / 'record-audit.json').write_text(json.dumps(expected['audit'], indent=2) + '\n')
        return dict(status='passed', elapsed_seconds=time.perf_counter() - started,
                    installed_package=str(installed), original_sha256=SOURCE_SHA,
                    original_bytes=len(raw), canonical_bytes=len(canonical),
                    canonical_sha256=record.sha256, dag_nodes=len(json.loads(canonical)['nodes']),
                    capture_count=len(record.captures), observation_count=len(record.observations),
                    checks=dict(counts), numerical_event_accepted=True, material_qualified=False,
                    resume_authorized=False, eos_calls=0, model_executions=0,
                    scope='all_original_values_preserved_and_saved_arithmetic_audited_not_source_authentication')


if __name__ == '__main__':
    source, output = map(Path, sys.argv[1:3])
    output.mkdir(parents=True, exist_ok=False)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('passive audit 180 second limit')))
    signal.alarm(180)
    trace = {'stage': 'starting'}
    try:
        result = run(source, output, trace)
    except BaseException as exc:
        (output / 'failure.json').write_text(json.dumps(dict(type=type(exc).__name__, message=str(exc),
                                                           **trace), indent=2) + '\n')
        raise
    finally:
        signal.alarm(0)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
