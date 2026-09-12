"""File and query interface for complete passive source-study evidence."""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .exact_event_clock import ExactEventTime
from .exact_record import EvidenceNode
from .source_observation_service import describe_source_observation
from .source_record_io import publish_record_bytes, read_record_bytes
from .source_study_schema import SourceStudyNode, has_capture_failure


MAX_IMPORT_BYTES = 64 * 1024 * 1024
MAX_RECORD_BYTES = 64 * 1024 * 1024
MAX_QUERY_BYTES = 1024 * 1024
MAX_QUERY_NODES = 100_000
MAX_QUERY_DEPTH = 96


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _plain(value):
    """Bound expansion while displaying an admitted DAG as ordinary JSON values."""
    remaining = MAX_QUERY_BYTES
    visits = 0

    def charge(size):
        nonlocal remaining
        _require(size <= remaining, 'source_study_query_too_large_select_specific_field')
        remaining -= size

    def enter(depth):
        nonlocal visits
        visits += 1
        _require(visits <= MAX_QUERY_NODES, 'source_study_query_node_limit')
        _require(depth <= MAX_QUERY_DEPTH, 'source_study_query_depth_limit')

    def mapping(items, depth):
        # Charge JSON punctuation before allocating the expanded container.
        charge(2 + max(len(items) - 1, 0) + len(items))
        output = {}
        for key, item in items:
            _require(type(key) is str, 'source_study_display_keys')
            visit(key, depth + 1)
            output[key] = visit(item, depth + 1)
        return output

    def array_values(array, depth):
        enter(depth)
        charge(2 + max(len(array) - 1, 0))
        if array.ndim == 1:
            return [visit(float(item), depth + 1) for item in array]
        return [array_values(row, depth + 1) for row in array]

    def visit(item, depth):
        enter(depth)
        if item is None or type(item) in (str, int, bool, float):
            if type(item) is str:
                # A single large string is rejected before JSON escaping it.
                _require(len(item) <= remaining, 'source_study_query_too_large_select_specific_field')
            if type(item) is float:
                _require(math.isfinite(item), 'source_study_nonfinite_display')
            charge(len(json.dumps(item, ensure_ascii=False, allow_nan=False,
                                  separators=(',', ':')).encode()))
            return item
        if type(item) is Fraction:
            return mapping((('numerator', item.numerator), ('denominator', item.denominator)), depth)
        if type(item) is ExactEventTime:
            return visit(item.to_record(), depth + 1)
        if type(item) in (EvidenceNode, SourceStudyNode):
            return mapping((('type', item.kind), ('fields', item.values)), depth)
        if type(item) is np.ndarray:
            _require(item.dtype == np.float64 and item.ndim in (1, 2), 'source_study_display_array')
            # Traverse array views incrementally instead of allocating tolist()
            # before the display budget has admitted their elements.
            charge(2 + 2 + 3)  # object braces, commas and colons
            output = {}
            for key, part in (('dtype', str(item.dtype)), ('shape', tuple(item.shape))):
                visit(key, depth + 1)
                output[key] = visit(part, depth + 1)
            visit('values', depth + 1)
            output['values'] = array_values(item, depth + 1)
            return output
        if isinstance(item, Mapping):
            return mapping(item.items(), depth)
        if type(item) is tuple:
            charge(2 + max(len(item) - 1, 0))
            return [visit(part, depth + 1) for part in item]
        if is_dataclass(item) and not isinstance(item, type):
            return mapping((('type', type(item).__module__ + '.' + type(item).__qualname__),
                ('fields', {f.name: getattr(item, f.name) for f in fields(item)})), depth)
        raise ValueError('source_study_unsupported_display_value')

    return visit(value, 0)


def _values(value):
    if type(value) in (EvidenceNode, SourceStudyNode):
        return value.values
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value):
        return {f.name: getattr(value, f.name) for f in fields(value)}
    raise ValueError('source_study_path_requires_record_or_sequence')


def query_source_study(record, value_path):
    """Select saved stage, original capture or run-metadata fields."""
    _require(type(value_path) is str and 0 < len(value_path) <= 1024,
             'source_study_value_path')
    parts = value_path.split('/')
    _require(len(parts) <= 32 and all(parts), 'source_study_value_path')
    value = record.roots
    if parts[0] in ('captures', 'metadata'):
        value = {parts[0]: getattr(record, parts[0])}
    for part in parts:
        if type(value) is tuple:
            _require(part.isascii() and part.isdecimal() and len(part) <= 9,
                     'source_study_sequence_index')
            index = int(part)
            _require(0 <= index < len(value), 'source_study_sequence_index')
            value = value[index]
        else:
            values = _values(value)
            _require(part in values, 'source_study_path_not_found:' + part)
            value = values[part]
    result = _plain(value)
    size = len(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode())
    _require(size <= MAX_QUERY_BYTES, 'source_study_query_too_large_select_specific_field')
    return result


def _summary(record, path, raw, *, capture_index=None, cell_index=None, value_path=None):
    _require(capture_index is None or (type(capture_index) is int
             and 0 <= capture_index < len(record.captures)), 'source_study_capture_index')
    _require(cell_index is None or capture_index is not None,
             'source_study_cell_requires_capture_index')
    stages = {}
    for name, value in record.roots.items():
        content = _values(value)
        stages[name] = {key: _plain(content[key]) for key in
            ('status', 'reason', 'qualification', 'numerical_event_accepted', 'material_qualified',
             'exception_type', 'message', 'stage')
            if key in content}
    failed = [i for i, capture in enumerate(record.captures)
              if has_capture_failure(capture)]
    result = {
        'status': 'source_study_record_valid',
        'record_path': str(Path(path).resolve()),
        'record_sha256': record.sha256,
        'file_sha256': hashlib.sha256(raw).hexdigest(),
        'file_is_canonical': raw == record.canonical_bytes,
        'provenance': dict(record.provenance),
        'reported_status': record.metadata.get('status'),
        'stages': stages,
        'capture_count': len(record.captures),
        'complete_observation_count': sum(value is not None for value in record.observations),
        'failed_capture_indices': failed,
        'unreturned_capture_indices': [i for i, value in enumerate(record.observations)
                                       if value is None and i not in failed],
        'audit': _plain(record.audit),
        'material_qualified': False,
        'resume_authorized': False,
        'source_assets_verified': False,
        'physical_run_reexecuted': False,
    }
    if capture_index is not None:
        capture = record.captures[capture_index]
        selected = {key: _plain(capture[key]) for key in
                    ('ordinal', 'phase', 'role', 'time', 'failure', 'failure_kind', 'exception',
                     'exception_type', 'interface_modes')
                    if key in capture}
        selected['capture_index'] = capture_index
        observation = record.observations[capture_index]
        if observation is None:
            _require(cell_index is None, 'source_study_capture_has_no_complete_cell_observation')
            selected['observation'] = None
            selected['recorded_input'] = _plain(capture.get('packed_input', capture.get('state')))
            if capture.get('evaluation') is not None:
                selected['recorded_return_path'] = f'captures/{capture_index}/evaluation'
        else:
            selected['observation'] = describe_source_observation(observation, cell_index=cell_index)
        result['selected_capture'] = selected
    if value_path is not None:
        result['selected_value'] = {'path': value_path, 'value': query_source_study(record, value_path)}
    return result



def describe_decoded_source_study(record, *, artifact_path, file_sha256,
                                  capture_index=None, cell_index=None, value_path=None):
    """Format a record already admitted by the containing run's validation pass.

    The supplied file digest is the verified outer manifest binding. Comparing
    it to the canonical record digest keeps original-file canonicality separate
    without rereading or decoding a second time. This does not verify sources.
    """
    result = _summary(record, artifact_path, record.canonical_bytes,
                      capture_index=capture_index, cell_index=cell_index, value_path=value_path)
    result['record_path'] = str(artifact_path)
    result['file_sha256'] = file_sha256
    result['file_is_canonical'] = file_sha256 == hashlib.sha256(record.canonical_bytes).hexdigest()
    return result


def inspect_source_study(path, *, capture_index=None, cell_index=None, value_path=None):
    from .source_study_record import decode_source_study
    raw = read_record_bytes(path, MAX_RECORD_BYTES, size_reason='source_study_file_limit',
                            regular_reason='source_study_regular_file_required')
    record = decode_source_study(raw)
    return _summary(record, path, raw, capture_index=capture_index,
                    cell_index=cell_index, value_path=value_path)


def import_source_study(source, output, *, source_format='source_multicell_native_v1'):
    from .source_study_record import import_saved_source_study
    raw = read_record_bytes(source, MAX_IMPORT_BYTES, size_reason='source_study_import_file_limit',
                            regular_reason='source_study_regular_file_required')
    record = import_saved_source_study(raw, source_format=source_format, provenance={
        'input_path': str(Path(source).resolve()),
        'input_sha256': hashlib.sha256(raw).hexdigest(),
        'input_format': source_format,
    })
    result = _summary(record, output, record.canonical_bytes)
    publish_record_bytes(output, record.canonical_bytes, temporary_prefix='.source-study-')
    return result
