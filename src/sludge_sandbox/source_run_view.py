"""Bounded passive source-run presentation; no providers, replay or restoration.

Each request admits the saved bundle once. Browser coordinates are display-only;
exact rational components become decimal strings. Canonical export uses the
existing run service and preserves its original record text without conversion.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from .run_service import RunError, read_run_with_source_record, export_run
from .source_study_service import describe_decoded_source_study

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 512 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_FILES = 10000
MAX_CAPTURE_PAGE = 50
MAX_BUILDER_SCAN_BYTES = 8 * 1024 * 1024
SOURCE_KIND = 'source_wet_to_dry_study_v1'


def _require(condition, reason):
    if not condition:
        raise RunError(reason)


class _DisplayBudget:
    """Charge the default UTF-8 JSON representation BEFORE building display data."""
    def __init__(self):
        self.remaining = MAX_RESPONSE_BYTES

    def charge(self, size):
        _require(size <= self.remaining, 'source_view_response_limit_select_specific_field')
        self.remaining -= size

    def string(self, value):
        _require(type(value) is str, 'source_view_nonstring_key_or_value')
        # Every character needs at least one byte; reject a huge scalar before
        # walking, escaping or encoding it. Surrogates cannot be UTF-8 output.
        _require(len(value)+2 <= self.remaining, 'source_view_response_limit_select_specific_field')
        self.charge(2)
        for char in value:
            code = ord(char)
            _require(not 0xD800 <= code <= 0xDFFF, 'source_view_invalid_unicode')
            if char in ('"', '\\', '\b', '\f', '\n', '\r', '\t'):
                size = 2
            elif code < 32:
                size = 6
            else:
                size = 1 if code < 128 else 2 if code < 2048 else 3 if code < 65536 else 4
            self.charge(size)
        return value

    def mapping(self, length):
        self.charge(2 + 2*length + 2*max(0, length-1))  # braces, ': ', ', '

    def array(self, length):
        self.charge(2 + 2*max(0, length-1))

    def scalar(self, item, key=None):
        if type(item) is str:
            return self.string(item)
        if type(item) is int:
            stringify = key in ('numerator', 'denominator') or abs(item) > 2**53-1
            # Upper bound for decimal digits; do not allocate a huge decimal
            # string simply to discover that the remaining budget rejects it.
            digits = max(1, (item.bit_length()*30103)//100000+1) + (item < 0)
            _require(digits+(2 if stringify else 0) <= self.remaining,
                     'source_view_response_limit_select_specific_field')
            text = str(item)
            if stringify:
                return self.string(text)
            self.charge(len(text))
            return item
        if type(item) is float:
            _require(math.isfinite(item), 'source_view_nonfinite_number')
            self.charge(len(repr(item)))
            return item
        if item is None or type(item) is bool:
            self.charge(4 if item is None or item is True else 5)
            return item
        raise RunError('source_view_nonplain_response')


def browser_value(value):
    """Bound expansion incrementally and retain exact integers through JS JSON."""
    budget, visits = _DisplayBudget(), 0
    def visit(item, key=None, depth=0):
        nonlocal visits
        visits += 1
        _require(visits <= 100000 and depth <= 96, 'source_view_response_structure_limit')
        if type(item) is dict:
            budget.mapping(len(item))
            output = {}
            for name, child in item.items():
                budget.string(name)
                output[name] = visit(child, name, depth+1)
            return output
        if type(item) in (list, tuple):
            budget.array(len(item))
            return [visit(v, None, depth+1) for v in item]
        return budget.scalar(item, key)
    return visit(value)


def _relative(name):
    path = PurePosixPath(name)
    _require(bool(name) and not path.is_absolute() and '..' not in path.parts
             and '\\' not in name and str(path) == name, 'source_view_invalid_artifact_path')
    return path


def _read_file(directory, name, expected, limit):
    _relative(name)
    path = directory/name
    _require(not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()),
             'source_view_invalid_artifact_path')
    _require(path.is_file() and path.stat().st_size <= limit, 'source_view_artifact_size_limit')
    with path.open('rb') as stream:
        raw = stream.read(limit+1)
    _require(len(raw) <= limit, 'source_view_artifact_size_limit')
    if expected is not None:
        _require(hashlib.sha256(raw).hexdigest() == expected, 'source_view_artifact_changed_after_validation')
    return raw


def _preflight(directory):
    """Bound filesystem work before the established complete-bundle verifier."""
    raw = _read_file(directory, 'manifest.json', None, MAX_RESPONSE_BYTES)
    manifest = json.loads(raw)
    files = manifest.get('files') if type(manifest) is dict else None
    _require(type(files) is dict and 0 < len(files) <= MAX_MANIFEST_FILES, 'source_view_manifest_limit')
    total = 0
    for name in files:
        _relative(name)
        path = directory/name
        _require(not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()),
                 'source_view_invalid_artifact_path')
        _require(path.is_file(), 'source_view_regular_artifact_required')
        size = path.stat().st_size
        total += size
        _require(size <= MAX_ARTIFACT_BYTES and total <= MAX_BUNDLE_BYTES, 'source_view_bundle_size_limit')


def _open(directory):
    directory = Path(directory).resolve()
    _preflight(directory)
    result, manifest, record = read_run_with_source_record(directory)
    _require(result.get('integration_kind') == SOURCE_KIND, 'source_view_requires_standard_source_run')
    return directory, result, manifest, record


def _assets(directory, manifest):
    return [dict(asset_id=hashlib.sha256(name.encode()).hexdigest(), path=name,
                 sha256=digest, bytes=(directory/name).stat().st_size,
                 text_available=(directory/name).suffix.lower() in ('.json', '.txt', '.html', '.py', '.md')
                    and (directory/name).stat().st_size <= MAX_RESPONSE_BYTES)
            for name, digest in sorted(manifest['files'].items()) if name.startswith('assets/')]


def project_builder_path(graph, parts):
    """Project one journal path with structure and byte limits before expansion."""
    _require(type(graph) is dict and graph.get('schema') == 'source_run_raw_projection_v1',
             'source_view_projection_schema')
    nodes = graph.get('nodes')
    _require(type(nodes) is dict and len(nodes) <= 250000 and type(parts) in (tuple, list)
             and len(parts) <= 32 and all(type(part) is str for part in parts),
             'source_view_projection_limit')
    def unwrap(value):
        if type(value) is dict and set(value) == {'ref'}:
            key = value['ref']
            _require(type(key) is str and key in nodes and type(nodes[key]) is dict,
                     'source_view_projection_missing_reference')
            return nodes[key], key
        return value, None
    def fields_of(value):
        fields = value['fields']
        _require(type(fields) is dict and all(type(key) is str for key in fields),
                 'source_view_projection_fields_mapping_required')
        return fields
    value = graph.get('root')
    for part in parts:
        value, _ = unwrap(value)
        _require(type(value) is dict, 'source_view_projection_path_missing')
        if 'fields' in value:
            mapping = fields_of(value)
            _require(part in mapping, 'source_view_projection_path_missing')
            value = mapping[part]
        else:
            sequence = value.get('values')
            _require(type(sequence) is list and part.isascii() and part.isdecimal() and len(part) <= 9,
                     'source_view_projection_index')
            index = int(part)
            _require(0 <= index < len(sequence), 'source_view_projection_index')
            value = sequence[index]
    visits, budget = 0, _DisplayBudget()
    def expand(item, active, depth=0, field=None):
        nonlocal visits
        visits += 1
        _require(visits <= 10000 and depth <= 48, 'source_view_projection_expansion_limit')
        item, identifier = unwrap(item)
        if identifier is not None:
            _require(identifier not in active, 'source_view_projection_cycle')
            active = active | {identifier}
        if item is None or type(item) in (str, int, bool):
            return budget.scalar(item, field)
        _require(type(item) is dict, 'source_view_projection_unsupported_value')
        if set(item) == {'binary64'}:
            _require(type(item['binary64']) is str and len(item['binary64']) <= 32,
                     'source_view_projection_binary64')
            try:
                value = float.fromhex(item['binary64'])
            except (ValueError, OverflowError) as exc:
                raise RunError('source_view_projection_binary64') from exc
            _require(math.isfinite(value), 'source_view_projection_nonfinite')
            return budget.scalar(value)
        if set(item) == {'fraction'}:
            pair = item['fraction']
            _require(type(pair) is list and len(pair) == 2 and all(type(x) is int for x in pair)
                     and pair[1] > 0, 'source_view_projection_fraction')
            budget.mapping(2)
            output = {}
            for key, number in zip(('numerator', 'denominator'), pair):
                budget.string(key)
                output[key] = budget.scalar(number, key)
            return output
        if 'fields' in item:
            mapping = fields_of(item)
            budget.mapping(len(mapping))
            output = {}
            for key, child in mapping.items():
                budget.string(key)
                output[key] = expand(child, active, depth+1, key)
            return output
        if 'values' in item:
            _require(type(item['values']) is list, 'source_view_projection_values_sequence_required')
            budget.array(len(item['values']))
            return [expand(child, active, depth+1) for child in item['values']]
        # Unavailable runtime objects stay explicit data, never constructors.
        return expand({'fields': {'status': 'unknown', 'reason': 'saved_projection_value_unavailable'}},
                      active, depth+1)
    return expand(value, set())


def _builder(directory, manifest):
    used = 0
    names = sorted(name for name in manifest['files'] if name.startswith('events/') and name.endswith('.json'))
    for name in names[:256]:
        size = (directory/name).stat().st_size
        used += size
        if size > MAX_RESPONSE_BYTES or used > MAX_BUILDER_SCAN_BYTES:
            return None, {'status': 'unknown', 'reason': 'builder_event_not_found_within_passive_scan_budget'}
        raw = _read_file(directory, name, manifest['files'][name], MAX_RESPONSE_BYTES)
        try:
            event = json.loads(raw)
        except (ValueError, RecursionError) as exc:
            raise RunError('source_view_builder_event_json_invalid:'+name) from exc
        _require(type(event) is dict and type(event.get('event')) is str,
                 'source_view_builder_event_object_required:'+name)
        if event['event'] == 'builder_returned':
            payload = event.get('payload')
            _require(type(payload) is dict and payload.get('schema') == 'source_run_raw_projection_v1'
                     and 'root' in payload and type(payload.get('nodes')) is dict
                     and len(payload['nodes']) <= 250000, 'source_view_builder_projection_required:'+name)
            return payload, {'status': 'recorded_hash_bound', 'artifact': name,
                'sha256': manifest['files'][name], 'ordinal': event.get('ordinal'),
                'meaning': 'saved_builder_returned_provenance_not_new_provider_evaluation'}
    return None, {'status': 'unknown', 'reason': 'builder_returned_event_unavailable'}


def _source_trace(directory, manifest, cells):
    try:
        graph, binding = _builder(directory, manifest)
    except RunError as exc:
        if not str(exc).startswith('source_view_builder_'):
            raise  # Integrity/path failures must refuse the view, not become an unknown source link.
        graph, binding = None, {'status': 'unknown', 'reason': str(exc),
                                'meaning': 'saved_builder_provenance_not_available_for_projection'}
    assets = _assets(directory, manifest)
    traced = []
    for cell in cells:
        provenance = None
        if graph is not None:
            try:
                provenance = project_builder_path(graph, ('source_column', 'cells', str(cell['cell_index'])))
                _require(type(provenance) is dict, 'source_view_projection_cell_mapping_required')
            except ValueError as exc:
                provenance = {'status': 'unknown', 'reason': str(exc)}
        registry = provenance.get('dry_sensible_term', {}) if type(provenance) is dict else {}
        _require(type(registry) is dict and type(registry.get('nodes', [])) is list
                 and type(registry.get('sources', [])) is list, 'source_view_projection_registry_shape')
        entries = [*registry.get('nodes', []), *registry.get('sources', [])]
        by_id = {entry['id']: entry for entry in entries if type(entry) is dict and type(entry.get('id')) is str}
        links = []
        for source_id in cell['source_ids']:
            entry = by_id.get(source_id)
            links.append({'source_id': source_id, 'status': 'recorded_registry_entry' if entry else 'unknown',
                          'registry_entry': entry, 'builder_event': binding,
                          'original_path': f"source_column/cells/{cell['cell_index']}/dry_sensible_term" if entry else None})
        water_assets = []
        for name, digest in cell['source_asset_sha256'].items():
            matches = [asset for asset in assets if asset['sha256'] == digest and PurePosixPath(asset['path']).name == name]
            water_assets.append({'recorded_name': name, 'recorded_sha256': digest,
                                 'status': 'hash_bound_asset' if matches else 'unknown', 'assets': matches})
        dry_assets = []
        for source in registry.get('sources', []):
            _require(type(source) is dict and type(source.get('assets', [])) is list,
                     'source_view_projection_registry_source_shape')
            for reference in source.get('assets', []):
                _require(type(reference) is dict and type(reference.get('path')) is str
                         and type(reference.get('sha256')) is str, 'source_view_projection_asset_shape')
                path = 'assets/'+reference['path']
                matches = [asset for asset in assets if asset['path'] == path and asset['sha256'] == reference['sha256']]
                dry_assets.append({'recorded_path': reference['path'], 'recorded_sha256': reference['sha256'],
                                   'status': 'hash_bound_asset' if matches else 'unknown', 'assets': matches})
            digest = source.get('metadata_sha256')
            matches = [asset for asset in assets if digest is not None and asset['sha256'] == digest]
            dry_assets.append({'metadata_source_id': source.get('id'), 'recorded_sha256': digest,
                               'status': 'hash_bound_asset' if matches else 'unknown', 'assets': matches})
        traced.append({'cell_index': cell['cell_index'], 'source_links': links,
            'builder_projection_status': provenance.get('status', 'recorded') if provenance else 'unknown',
            'builder_projection_reason': provenance.get('reason') if provenance else 'builder_returned_unavailable',
            'dry_caloric_registry': registry or None, 'dry_source_assets': dry_assets,
            'water_source_assets': water_assets, 'recorded_fluid_provenance': provenance.get('fluid') if provenance else None,
            'missing_material_evidence': provenance.get('missing_material_evidence') if provenance else None,
            'source_id_coverage_claim': 'only_exact_saved_registry_matches; other_ids_remain_unknown'})
    return {'builder_event': binding, 'cells': traced, 'source_assets_verified': False,
            'artifact_hashes_verified': True, 'material_applicability_verified': False}


def inspect_source_run(directory, *, capture_index=None, cell_index=None, value_path=None,
                       capture_offset=0, capture_limit=MAX_CAPTURE_PAGE):
    """One complete validation/decode pass followed by bounded passive selection."""
    _require(type(capture_offset) is int and capture_offset >= 0 and type(capture_limit) is int
             and 1 <= capture_limit <= MAX_CAPTURE_PAGE, 'source_view_capture_page')
    directory, saved, manifest, record = _open(directory)
    result = {key: saved.get(key) for key in ('schema', 'integration_kind', 'status', 'execution_status', 'reason',
        'case_sha256', 'config_sha256', 'asset_manifest_sha256', 'counts', 'source_record',
        'numerical_comparison_completed', 'numerical_event_accepted', 'scientific_status',
        'material_qualified', 'training_eligible', 'full_firing_cycle', 'resume_authorized')}
    response = {'schema': 'source_run_view_v1', 'result': result, 'study': None,
        'artifact_hashes_verified': True, 'physical_run_reexecuted': False,
        'source_assets_verified': False, 'assets': _assets(directory, manifest),
        'capture_semantics': 'original_RHS_capture_order_not_accepted_trajectory',
        'capabilities': {'inspect': True, 'export': True, 'execute': False, 'restore': False}}
    if record is None:
        _require(capture_index is None and cell_index is None and value_path is None,
                 'source_view_no_admitted_study')
        response['study_unavailable_reason'] = saved.get('source_record_error', 'unknown')
        return browser_value(response)
    reference = saved['source_record']
    response['study'] = describe_decoded_source_study(record, artifact_path=reference['path'],
        file_sha256=reference['sha256'], capture_index=capture_index, cell_index=cell_index, value_path=value_path)
    page = []
    for index in range(capture_offset, min(len(record.captures), capture_offset+capture_limit)):
        capture, observation = record.captures[index], record.observations[index]
        page.append({'capture_index': index, 'ordinal': capture.get('ordinal'), 'phase': capture.get('phase'),
            'role': capture.get('role', observation.sample.role if observation else None),
            'status': 'complete_observation' if observation else ('failed' if index in response['study']['failed_capture_indices'] else 'unreturned'),
            'cell_count': len(observation.context.fixed_dry_mass_kg) if observation else None,
            'return_identity': 'saved_return' if capture.get('evaluation') is not None else 'no_saved_return'})
    response['capture_page'] = {'offset': capture_offset, 'limit': capture_limit, 'items': page,
        'next_offset': capture_offset+capture_limit if capture_offset+capture_limit < len(record.captures) else None}
    selected = response['study'].get('selected_capture')
    if selected:
        selected['return_identity'] = 'saved_return' if record.captures[capture_index].get('evaluation') is not None else 'no_saved_return'
        observation = selected['observation']
        selected['capture_status'] = 'complete_observation' if observation else (
            'failed' if capture_index in response['study']['failed_capture_indices'] else 'unreturned')
        response['source_trace'] = _source_trace(directory, manifest, observation['cells']) if observation else {
            'status': 'unknown', 'reason': 'no_complete_observation_source_binding'}
    return browser_value(response)


def read_source_run_asset(directory, asset_id):
    """Select an already recorded source asset by opaque ID, never a request path."""
    _require(type(asset_id) is str and len(asset_id) == 64 and all(c in '0123456789abcdef' for c in asset_id),
             'source_view_invalid_asset_id')
    directory, _, manifest, _ = _open(directory)
    matches = [asset for asset in _assets(directory, manifest) if asset['asset_id'] == asset_id]
    _require(len(matches) == 1, 'source_view_asset_not_recorded')
    asset = matches[0]
    _require(asset['text_available'], 'source_view_asset_text_unavailable')
    raw = _read_file(directory, asset['path'], asset['sha256'], MAX_RESPONSE_BYTES)
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise RunError('source_view_asset_not_utf8') from exc
    return browser_value({**asset, 'text': text})


def export_source_run(directory):
    """Canonical export has no browser-number presentation conversion."""
    directory = Path(directory).resolve()
    _preflight(directory)
    value = export_run(directory)  # Includes exactly one established admission/decode pass.
    _require(value['result'].get('integration_kind') == SOURCE_KIND, 'source_view_requires_standard_source_run')
    return value
