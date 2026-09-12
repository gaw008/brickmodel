"""Passive presentation only: no EOS, native integration, execution or restore."""
import json
from pathlib import Path

import pytest


def test_exact_browser_numbers_preserve_integer_components():
    from sludge_sandbox.source_run_view import browser_value
    numerator = 2**80+19
    value = browser_value({'time': {'numerator': numerator, 'denominator': 3}, 'count': 4})
    assert value == {'time': {'numerator': str(numerator), 'denominator': '3'}, 'count': 4}
    assert json.loads(json.dumps(value))['time']['numerator'] == str(numerator)


def test_projection_cycle_is_refused_without_provider_construction():
    from sludge_sandbox.source_run_view import project_builder_path
    graph = {'schema': 'source_run_raw_projection_v1', 'root': {'ref': '0'},
             'nodes': {'0': {'fields': {'loop': {'ref': '0'}}}}}
    with pytest.raises(ValueError, match='source_view_projection'):
        project_builder_path(graph, ('loop',))

import copy
import hashlib
from fractions import Fraction


@pytest.fixture(autouse=True)
def forbid_physics(monkeypatch):
    from test_source_study_cli import _forbid_physics
    _forbid_physics(monkeypatch)
    import sludge_sandbox.integration as integration
    import sludge_sandbox.source_run_builder as builder
    import sludge_sandbox.source_trajectory_record as restore
    def forbidden(*args, **kwargs):
        pytest.fail('passive source view attempted execution or restore')
    monkeypatch.setattr(integration, 'integrate', forbidden)
    monkeypatch.setattr(builder, 'build_source_run', forbidden)
    monkeypatch.setattr(restore, 'restore_source_trajectory', forbidden)


@pytest.fixture
def source_bundle(tmp_path):
    from test_source_study_record import minimal_saved_study
    from sludge_sandbox.source_study_record import import_saved_source_study, encode_source_study
    from sludge_sandbox.source_run_journal import SourceRunJournal
    from sludge_sandbox.run_service import _seal
    root = tmp_path/'source-run'
    root.mkdir()
    case = b'{"test_only":true}'
    (root/'case.json').write_bytes(case)
    case_sha = hashlib.sha256(case).hexdigest()
    original = json.loads(minimal_saved_study())
    clock = {'numerator': 2**80+19, 'denominator': 3}
    original['captures'][0]['time']['fields']['seconds'] = clock
    original['captures'][0]['evaluation']['fields']['time']['fields']['seconds'] = clock
    failed = copy.deepcopy(original['captures'][0]); failed['ordinal'] = 2
    failed.pop('evaluation'); failed['failure'] = 'test_only_saved_failure'; failed['failure_kind'] = 'operator_failed'
    unreturned = copy.deepcopy(original['captures'][0]); unreturned['ordinal'] = 3; unreturned.pop('evaluation'); unreturned['failure_kind'] = 'unreturned'
    original['captures'].extend((failed, unreturned))
    record = import_saved_source_study(json.dumps(original).encode())
    counts = {'rhs_started': 3, 'rhs_returned': 1}
    metadata = dict(record.metadata, case_sha256=case_sha, counts=counts)
    raw = encode_source_study(record.roots, contexts=record.contexts, captures=record.captures,
                              metadata=metadata, provenance=record.provenance)
    (root/'source-study-record.json').write_bytes(raw)
    asset = root/'assets/fixture-source.txt'; asset.parent.mkdir(); asset.write_bytes(b'fixture source bytes\n')
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    dry = {'nodes': [{'id': 'ARLABOSSE2005_DRY_CP_EQ2', 'unit': 'fixture_only', 'dependencies': [], 'citations': []}],
           'sources': [{'id': 'SRC_ARLABOSSE_2005_CONTACT_DRYING', 'title': 'test-only metadata',
                        'assets': [{'path': 'fixture-source.txt', 'sha256': digest}]}]}
    SourceRunJournal(root).append('builder_returned', {'source_column': {'cells': [
        {'dry_sensible_term': dry, 'fluid': {'scope': 'test-only saved provenance'}} for _ in range(3)]}})
    saved = dict(schema='sandbox_run_v1', integration_kind='source_wet_to_dry_study_v1',
        status='cancelled', execution_status='cancelled', reason=record.metadata['reason'], case_sha256=case_sha,
        scientific_status='manufactured_view_fixture_not_physical_run',
        counts=counts, source_record={'path': 'source-study-record.json', 'sha256': hashlib.sha256(raw).hexdigest()},
        material_qualified=False, training_eligible=False, full_firing_cycle=False, resume_authorized=False,
        numerical_comparison_completed=False, numerical_event_accepted=False)
    (root/'result.json').write_text(json.dumps(saved))
    _seal(root)
    return root


def test_shared_view_decodes_once_and_keeps_trial_failed_unreturned_identity(source_bundle, monkeypatch):
    import sludge_sandbox.source_run_service as service
    from sludge_sandbox.source_run_view import inspect_source_run
    original = service.decode_source_study
    calls = []
    def decode(raw):
        calls.append(1)
        return original(raw)
    monkeypatch.setattr(service, 'decode_source_study', decode)
    result = inspect_source_run(source_bundle, capture_index=0, cell_index=1)
    assert len(calls) == 1
    assert result['result']['status'] == 'cancelled'
    assert not result['result']['material_qualified'] and not result['result']['full_firing_cycle']
    assert result['artifact_hashes_verified'] and not result['source_assets_verified']
    selected = result['study']['selected_capture']
    assert selected['capture_index'] == 0 and selected['ordinal'] == 1
    assert selected['observation']['time']['numerator'] == str(2**80+19)
    assert selected['observation']['time']['denominator'] == '3'
    assert [x['status'] for x in result['capture_page']['items']] == ['complete_observation', 'failed', 'failed']
    assert result['capture_semantics'] == 'original_RHS_capture_order_not_accepted_trajectory'
    assert result['study']['source_assets_verified'] is False
    assert result['source_trace']['cells'][0]['source_links'][0]['registry_entry']['unit'] == 'fixture_only'
    for index, kind in ((1, 'failed'), (2, 'failed')):
        selected = inspect_source_run(source_bundle, capture_index=index)['study']['selected_capture']
        assert selected['capture_status'] == kind and selected['observation'] is None
        assert selected['recorded_input'] is not None
        assert selected['return_identity'] == 'no_saved_return'


def test_asset_and_canonical_export_preserve_original_bytes(source_bundle):
    from sludge_sandbox.source_run_view import inspect_source_run, read_source_run_asset, export_source_run
    view = inspect_source_run(source_bundle)
    asset = view['assets'][0]
    assert read_source_run_asset(source_bundle, asset['asset_id'])['text'].encode() == (source_bundle/asset['path']).read_bytes()
    exported = export_source_run(source_bundle)
    assert exported['canonical_source_record']['text'].encode() == (source_bundle/'source-study-record.json').read_bytes()
    assert hashlib.sha256(exported['canonical_source_record']['text'].encode()).hexdigest() == exported['canonical_source_record']['sha256']


@pytest.mark.parametrize('options', [{'capture_index': -1}, {'capture_index': 3}, {'cell_index': 0},
    {'capture_index': 1, 'cell_index': 0}, {'capture_limit': 51}, {'capture_offset': -1},
    {'value_path': '../../etc/passwd'}, {'value_path': 'captures/9999999999999'}])
def test_selection_bounds_refuse_unknown_paths(source_bundle, options):
    from sludge_sandbox.source_run_view import inspect_source_run
    with pytest.raises(ValueError):
        inspect_source_run(source_bundle, **options)


def test_path_traversal_and_unknown_asset_id_refused(source_bundle):
    from sludge_sandbox.source_run_view import read_source_run_asset
    for identifier in ('../case.json', '/etc/passwd', 'a'*64, '0'*65):
        with pytest.raises(ValueError):
            read_source_run_asset(source_bundle, identifier)


@pytest.mark.parametrize('change', ['source_bytes', 'scope_resealed'])
def test_tampered_bytes_or_qualifications_refused_by_inspect_and_export(source_bundle, change):
    from sludge_sandbox.source_run_view import inspect_source_run, export_source_run
    from sludge_sandbox.run_service import _seal
    if change == 'source_bytes':
        (source_bundle/'assets/fixture-source.txt').write_text('tampered')
    else:
        result = json.loads((source_bundle/'result.json').read_text()); result['material_qualified'] = True
        (source_bundle/'result.json').write_text(json.dumps(result)); _seal(source_bundle)
    for function in (inspect_source_run, export_source_run):
        with pytest.raises(ValueError):
            function(source_bundle)


def test_cli_inspect_and_export_share_verified_python_boundary(source_bundle, tmp_path, capsys):
    from sludge_sandbox.cli import main
    from sludge_sandbox.source_run_view import inspect_source_run
    assert main(['inspect', str(source_bundle), '--capture-index', '0', '--cell', '2']) == 0
    assert json.loads(capsys.readouterr().out) == inspect_source_run(source_bundle, capture_index=0, cell_index=2)
    output = tmp_path/'export.json'
    assert main(['export', str(source_bundle), '--output', str(output)]) == 0
    capsys.readouterr()
    assert json.loads(output.read_text())['canonical_source_record']['text'].encode() == (source_bundle/'source-study-record.json').read_bytes()
    assert main(['export', str(source_bundle), '--output', str(output)]) == 1
    capsys.readouterr()


def test_real_saved_source_bundle_trace_joins_original_builder_without_physics():
    from sludge_sandbox.source_run_view import inspect_source_run
    path = Path('/private/tmp/brick-source-run-service-v1/native-job01/run')
    if not path.is_dir():
        pytest.skip('optional local archived source run not available')
    view = inspect_source_run(path, capture_index=0, cell_index=0)
    cell = view['source_trace']['cells'][0]
    assert view['result']['status'] == 'completed'
    assert view['source_trace']['builder_event']['artifact'] == 'events/000013.json'
    assert any(link['source_id'] == 'ARLABOSSE2005_DRY_CP_EQ2' and link['registry_entry'] for link in cell['source_links'])
    assert any(item['status'] == 'hash_bound_asset' for item in cell['dry_source_assets'])
    assert any(item['recorded_name'] == 'source_facts.json' and item['status'] == 'hash_bound_asset' for item in cell['water_source_assets'])
    assert any(item['recorded_name'] == 'water_implementation_v1.json' and item['status'] == 'unknown' for item in cell['water_source_assets'])


def test_dag_byte_budget_refuses_before_large_json_allocation(monkeypatch):
    from sludge_sandbox import source_run_view as view
    graph = {'schema': 'source_run_raw_projection_v1', 'root': {'ref': 'root'}, 'nodes': {
        'root': {'values': [{'ref': 'shared'} for _ in range(256)]},
        'shared': {'fields': {'text': 'x'*65536}}}}
    original = json.dumps
    allocated = []
    def measured(*args, **kwargs):
        text = original(*args, **kwargs)
        allocated.append(len(text.encode()))
        return text
    monkeypatch.setattr(view.json, 'dumps', measured)
    with pytest.raises(ValueError, match='source_view_response_limit'):
        view.project_builder_path(graph, ())
    assert max(allocated, default=0) <= view.MAX_RESPONSE_BYTES


@pytest.mark.parametrize('value', [ {'\x00'*40: 'small'}, {'text': '\n'*80}, ['é'*40]*3,
                                    {'numerator': 10**1000, 'denominator': 1} ])
def test_browser_budget_counts_keys_escaping_utf8_and_large_scalar_before_encoding(monkeypatch, value):
    from sludge_sandbox import source_run_view as view
    monkeypatch.setattr(view, 'MAX_RESPONSE_BYTES', 128)
    original = json.dumps
    allocated = []
    def measured(*args, **kwargs):
        text = original(*args, **kwargs)
        allocated.append(len(text.encode()))
        return text
    monkeypatch.setattr(view.json, 'dumps', measured)
    with pytest.raises(ValueError, match='source_view_response_limit'):
        view.browser_value(value)
    assert max(allocated, default=0) <= 128


@pytest.mark.parametrize('node', [{'fields': []}, {'fields': 7}, {'values': {}}, {'fraction': [1]},
                                 {'fraction': '1/3'}, {'binary64': []}])
def test_malformed_projection_is_controlled_run_error(node):
    from sludge_sandbox.source_run_view import project_builder_path
    from sludge_sandbox.run_service import RunError
    graph = {'schema': 'source_run_raw_projection_v1', 'root': {'ref': '0'}, 'nodes': {'0': node}}
    with pytest.raises(RunError, match='source_view_projection'):
        project_builder_path(graph, ())


def test_malformed_builder_cell_remains_explicit_unknown_in_verified_view(source_bundle):
    from sludge_sandbox.source_run_view import inspect_source_run
    from sludge_sandbox.run_service import _seal
    path = source_bundle/'events/000001.json'
    event = json.loads(path.read_text())
    graph = event['payload']; nodes = graph['nodes']
    root = nodes[graph['root']['ref']]
    column = nodes[root['fields']['source_column']['ref']]
    cells = nodes[column['fields']['cells']['ref']]
    nodes[cells['values'][0]['ref']]['fields'] = []
    path.write_text(json.dumps(event)); _seal(source_bundle)
    result = inspect_source_run(source_bundle, capture_index=0, cell_index=0)
    cell = result['source_trace']['cells'][0]
    assert cell['builder_projection_status'] == 'unknown'
    assert cell['builder_projection_reason'] == 'source_view_projection_fields_mapping_required'
    assert cell['dry_caloric_registry'] is None
    assert all(link['status'] == 'unknown' for link in cell['source_links'])


@pytest.mark.parametrize('event', [[], {}, {'event': 'builder_returned'},
    {'event': 'builder_returned', 'payload': None},
    {'event': 'builder_returned', 'payload': {'schema': 'source_run_raw_projection_v1', 'root': {'ref': '0'}, 'nodes': []}}])
def test_malformed_builder_events_remain_unknown_without_server_exception(source_bundle, event):
    from sludge_sandbox.source_run_view import inspect_source_run
    from sludge_sandbox.run_service import _seal
    (source_bundle/'events/000001.json').write_text(json.dumps(event)); _seal(source_bundle)
    result = inspect_source_run(source_bundle, capture_index=0, cell_index=0)
    binding = result['source_trace']['builder_event']
    assert binding['status'] == 'unknown'
    assert binding['reason'].startswith('source_view_builder_')
    assert result['source_trace']['cells'][0]['dry_caloric_registry'] is None


def test_builder_changed_after_validation_still_refuses_whole_view(source_bundle, monkeypatch):
    from sludge_sandbox import source_run_view as view
    original = view._builder
    def changed(directory, manifest):
        (directory/'events/000001.json').write_text('{}')
        return original(directory, manifest)
    monkeypatch.setattr(view, '_builder', changed)
    with pytest.raises(ValueError, match='source_view_artifact_changed_after_validation'):
        view.inspect_source_run(source_bundle, capture_index=0, cell_index=0)
