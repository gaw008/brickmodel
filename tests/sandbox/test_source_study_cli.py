"""Complete source-study file/service/CLI boundary, with original capture indices."""
import hashlib
import json
import os
from fractions import Fraction
from types import MappingProxyType, SimpleNamespace

import pytest


def _forbid_physics(patch):
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.water_heos import HEOSWaterProperties

    def forbidden(*args, **kwargs):
        pytest.fail('source-study file service called live physics')

    for cls in (ExactSourceColumn, SourceWetStorage, WaterProperties, HEOSWaterProperties):
        patch.setattr(cls, '__init__', forbidden)
    for cls in (ExactSourceColumn, SourceWetStorage):
        patch.setattr(cls, 'evaluate', forbidden)
    for cls in (WaterProperties, HEOSWaterProperties):
        patch.setattr(cls, 'state_tp', forbidden)


@pytest.fixture(autouse=True)
def forbid_physics(monkeypatch):
    _forbid_physics(monkeypatch)


@pytest.fixture(scope='module')
def saved_study(tmp_path_factory):
    from test_source_study_record import minimal_saved_study
    from sludge_sandbox.source_study_service import import_source_study
    directory = tmp_path_factory.mktemp('source-study-service')
    source, output = directory / 'original.json', directory / 'record.json'
    original = minimal_saved_study()
    source.write_bytes(original)
    with pytest.MonkeyPatch.context() as patch:
        _forbid_physics(patch)
        summary = import_source_study(source, output)
    return source, output, original, summary


def test_source_study_public_service_exists():
    from sludge_sandbox.source_study_service import import_source_study, inspect_source_study
    assert callable(import_source_study) and callable(inspect_source_study)


def test_complete_saved_capture_preserves_original_index_values_and_stopped_status(saved_study):
    from sludge_sandbox.source_study_service import inspect_source_study
    source, output, original, imported = saved_study
    assert inspect_source_study(output) == imported
    assert imported['status'] == 'source_study_record_valid'
    assert imported['reported_status'] == 'cancelled'
    assert imported['capture_count'] == imported['complete_observation_count'] == 1
    assert imported['record_sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert imported['provenance']['input_sha256'] == hashlib.sha256(original).hexdigest()
    assert imported['provenance']['input_path'] == str(source.resolve())
    assert not imported['resume_authorized'] and not imported['material_qualified']
    current = inspect_source_study(output, capture_index=0, cell_index=2)
    selected = current['selected_capture']
    assert selected['capture_index'] == 0 and selected['ordinal'] == 1
    observation = selected['observation']
    assert observation['selected_cell_index'] == 2 and len(observation['cells']) == 1
    expected = json.loads(original)['captures'][0]['packed_input']['fields']
    assert observation['cells'][0]['amounts_mol'] == expected['amounts_mol']['values'][2]
    assert observation['cells'][0]['internal_energy_j'] == expected['internal_energy_j']['values'][2]
    assert 'file_sha256' not in observation and 'record_path' not in observation
    assert not observation['resume_authorized'] and not current['physical_run_reexecuted']


def test_cli_import_and_capture_inspection_use_same_service(saved_study, tmp_path, capsys):
    from sludge_sandbox.cli import main
    from sludge_sandbox.source_study_service import inspect_source_study
    source, _, _, _ = saved_study
    output = tmp_path / 'cli.json'
    assert main(['source-study-import', str(source), '--output', str(output)]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported == inspect_source_study(output)
    assert main(['source-study-inspect', str(output), '--capture-index', '0', '--cell', '1']) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected == inspect_source_study(output, capture_index=0, cell_index=1)


def test_original_capture_and_metadata_fields_are_queryable(saved_study):
    from sludge_sandbox.source_study_service import inspect_source_study
    _, output, _, _ = saved_study
    capture = inspect_source_study(output, value_path='captures/0/phase')
    assert capture['selected_value']['value'] == 'initial_rate_probe'
    metadata = inspect_source_study(output, value_path='metadata/status')
    assert metadata['selected_value']['value'] == 'cancelled'


def test_returned_failure_keeps_raw_response_queryable_without_success_observation(tmp_path):
    from test_source_study_record import minimal_saved_study
    from sludge_sandbox.source_study_service import import_source_study, inspect_source_study
    original = json.loads(minimal_saved_study())
    capture = original['captures'][0]
    capture['failure'] = 'returned evaluation time did not match the requested time'
    capture['failure_kind'] = 'returned_evaluation_validation_failed'
    capture['evaluation']['fields']['time']['fields']['seconds'] = {'numerator': 1, 'denominator': 1}
    source, output = tmp_path / 'failed-original.json', tmp_path / 'failed-record.json'
    source.write_text(json.dumps(original))
    imported = import_source_study(source, output)
    assert imported['failed_capture_indices'] == [0]
    assert imported['complete_observation_count'] == 0
    result = inspect_source_study(output, capture_index=0,
                                 value_path='captures/0/evaluation/time/seconds')
    selected = result['selected_capture']
    assert selected['observation'] is None
    assert selected['recorded_return_path'] == 'captures/0/evaluation'
    assert selected['recorded_input'] is not None
    assert result['selected_value']['value'] == {'numerator': 1, 'denominator': 1}


@pytest.mark.parametrize('options', [
    {'capture_index': -1}, {'capture_index': 1}, {'capture_index': True},
    {'cell_index': 0}, {'capture_index': 0, 'cell_index': 3},
])
def test_bad_original_capture_or_cell_does_not_guess(saved_study, options):
    from sludge_sandbox.source_study_service import inspect_source_study
    with pytest.raises(ValueError):
        inspect_source_study(saved_study[1], **options)


def test_publication_never_overwrites_existing_record(saved_study):
    from sludge_sandbox.source_study_service import import_source_study
    source, output, _, _ = saved_study
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        import_source_study(source, output)
    assert output.read_bytes() == before
    assert not list(output.parent.glob('.source-study-*'))


def test_unsupported_import_format_leaves_no_output(saved_study, tmp_path):
    from sludge_sandbox.source_study_service import import_source_study
    output = tmp_path / 'unsupported.json'
    with pytest.raises(ValueError):
        import_source_study(saved_study[0], output, source_format='automatic_guessing')
    assert not output.exists()


def test_import_file_limit_applies_before_parsing(tmp_path, monkeypatch):
    import sludge_sandbox.source_study_service as module
    source, output = tmp_path / 'large', tmp_path / 'result'
    source.write_bytes(b'xxxxx')
    monkeypatch.setattr(module, 'MAX_IMPORT_BYTES', 4)
    with pytest.raises(ValueError, match='source_study_import_file_limit'):
        module.import_source_study(source, output)
    assert not output.exists()


@pytest.mark.parametrize('operation', ['import', 'inspect'])
def test_fifo_rejected_without_opening_a_blocking_stream(tmp_path, operation):
    from sludge_sandbox.source_study_service import import_source_study, inspect_source_study
    source = tmp_path / 'pipe'
    os.mkfifo(source)
    with pytest.raises(ValueError, match='source_study_regular_file_required'):
        if operation == 'import':
            import_source_study(source, tmp_path / 'output')
        else:
            inspect_source_study(source)


def _query_fixture():
    """Only path navigation is manufactured here; it is not study admission."""
    from sludge_sandbox.exact_record import EvidenceNode
    node = EvidenceNode('DisplayFixture', MappingProxyType({'bounds': ((Fraction(1, 3),),)}))
    return SimpleNamespace(roots=MappingProxyType({'transition': node}))


def test_exact_field_query_and_display_size_limit(monkeypatch):
    import sludge_sandbox.source_study_service as module
    record = _query_fixture()
    assert module.query_source_study(record, 'transition/bounds/0/0') == {'numerator': 1, 'denominator': 3}
    monkeypatch.setattr(module, 'MAX_QUERY_BYTES', 1)
    with pytest.raises(ValueError, match='query_too_large'):
        module.query_source_study(record, 'transition/bounds')


@pytest.mark.parametrize('path', [
    '', 'transition//bounds', 'transition/__class__', 'transition/bounds/-1',
    'transition/bounds/1', 'transition/bounds/0000000000', 'transition/bounds/0/0/no_field',
])
def test_query_does_not_invoke_attributes_or_guess_bad_paths(path):
    from sludge_sandbox.source_study_service import query_source_study
    with pytest.raises(ValueError):
        query_source_study(_query_fixture(), path)


def test_actual_codec_node_supports_stage_fields_and_failure_query(tmp_path):
    from sludge_sandbox.source_study_record import encode_source_study
    from sludge_sandbox.source_study_schema import SourceStudyFailure
    from sludge_sandbox.source_study_service import inspect_source_study
    failure = SourceStudyFailure('RuntimeError', 'original failure text', 'recorded_stage', {})
    raw = encode_source_study({'failure': failure}, contexts=())
    path = tmp_path / 'actual-node.json'
    path.write_bytes(raw)
    result = inspect_source_study(path, value_path='failure/message')
    assert result['stages']['failure']['message'] == 'original failure text'
    assert result['stages']['failure']['stage'] == 'recorded_stage'
    assert result['selected_value']['value'] == 'original failure text'


def test_shared_dag_display_stops_before_serializing_expanded_document(monkeypatch):
    import sludge_sandbox.source_study_service as module
    from sludge_sandbox.source_study_record import encode_source_study, decode_source_study
    from sludge_sandbox.source_study_schema import SourceStudyFailure
    shared = 'x' * 4096
    for _ in range(15):
        shared = (shared, shared)
    raw = encode_source_study({'failure': SourceStudyFailure('RuntimeError', 'kept', 'test',
                              {'shared': shared})}, contexts=())
    record = decode_source_study(raw)
    assert len(raw) < 100_000
    calls = []
    original = module.json.dumps

    def checked(value, **kwargs):
        encoded = original(value, **kwargs)
        calls.append(len(encoded.encode()))
        assert len(encoded.encode()) <= module.MAX_QUERY_BYTES
        return encoded

    monkeypatch.setattr(module.json, 'dumps', checked)
    with pytest.raises(ValueError, match='query_too_large'):
        module.query_source_study(record, 'failure')
    assert calls and max(calls) < 10_000


@pytest.mark.parametrize('budget', ['MAX_QUERY_NODES', 'MAX_QUERY_DEPTH'])
def test_display_traversal_budget_is_enforced_during_expansion(monkeypatch, budget):
    import sludge_sandbox.source_study_service as module
    monkeypatch.setattr(module, budget, 2)
    with pytest.raises(ValueError, match='query_(node|depth)_limit'):
        module.query_source_study(_query_fixture(), 'transition')


@pytest.mark.parametrize('key,message', [
    ('exception', 'recorded provider exception'),
    ('exception_type', 'ExampleProviderError'),
    ('failure', ''),
    ('failure_kind', 'returned_validation_failure'),
])
def test_exception_capture_is_failed_and_keeps_its_original_text(tmp_path, key, message):
    from test_source_study_record import minimal_saved_study
    from sludge_sandbox.source_study_service import import_source_study, inspect_source_study
    document = json.loads(minimal_saved_study())
    capture = document['captures'][0]
    capture['evaluation'] = None
    capture[key] = message
    source, output = tmp_path / 'exception.json', tmp_path / 'record.json'
    source.write_text(json.dumps(document))
    imported = import_source_study(source, output)
    assert imported['failed_capture_indices'] == [0]
    assert imported['unreturned_capture_indices'] == []
    selected = inspect_source_study(output, capture_index=0)['selected_capture']
    assert selected[key] == message
    assert selected['observation'] is None and selected['recorded_input'] is not None
