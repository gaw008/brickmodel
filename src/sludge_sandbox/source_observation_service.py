"""File and display boundary for one complete, passively checked source observation.

Import selects one explicit legacy capture. It does not validate its surrounding
run, reconstruct providers, attach live parameters or authorize continuation.
"""
from collections.abc import Mapping
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from .exact_record import _unique
from .source_observation_record import (
    SourceObservationContext,
    decode_source_sample,
    import_saved_source_sample,
)


MAX_IMPORT_BYTES = 64 * 1024 * 1024
MAX_RECORD_BYTES = 16 * 1024 * 1024


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _read_bounded(path, limit, reason):
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        _require(stat.S_ISREG(opened.st_mode), 'source_observation_regular_file_required')
        _require(opened.st_size <= limit, reason)
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
    finally:
        os.close(descriptor)
    _require(len(raw) <= limit, reason)
    return raw


def _constant(value):
    raise ValueError('source_capture_nonfinite_json')


def _identity(value, *, energy):
    """Convert only the fixed identity shape, without recursive traversal."""
    _require(type(value) is list and len(value) == 3
             and type(value[0]) is str
             and type(value[2]) is list
             and all(type(item) is str for item in value[2]),
             'source_capture_identity_shape')
    if energy:
        _require(type(value[1]) is list
                 and all(type(item) is str for item in value[1]),
                 'source_capture_identity_shape')
        middle = tuple(value[1])
    else:
        _require(type(value[1]) is str, 'source_capture_identity_shape')
        middle = value[1]
    return value[0], middle, tuple(value[2])


def _write_new(path, raw):
    """Publish a fully written file with exclusive creation; never replace output."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent,
                                         prefix='.source-observation-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _summary(record, path, file_bytes, cell_index):
    sample = record.sample
    count = len(record.context.fixed_dry_mass_kg)
    _require(cell_index is None or (type(cell_index) is int and 0 <= cell_index < count),
             'source_observation_cell_index')
    indices = range(count) if cell_index is None else (cell_index,)
    cells = []
    for i in indices:
        saved = sample.evaluation.source_evaluation.cells[i]
        point = saved.inverse.point
        cells.append({
            'cell_index': i,
            'fixed_dry_mass_kg': record.context.fixed_dry_mass_kg[i],
            'amounts_mol': sample.state.amounts_mol[i].tolist(),
            'internal_energy_j': float(sample.state.internal_energy_j[i]),
            'temperature_k': point.temperature_k,
            'temperature_error_bound_k': saved.inverse.temperature_error_bound_k,
            'pressure_pa': point.pressure_pa,
            'reported_temperature_pressure_error_pa': point.pressure_error_pa,
            'source_ids': list(point.source_ids),
            'source_asset_sha256': dict(point.fluid.mechanical.source_asset_sha256),
            'qualification': point.qualification,
        })
    modes = record.context.interface_modes
    return {
        'status': 'observation_record_valid',
        'record_path': str(Path(path).resolve()),
        'record_sha256': record.sha256,
        'file_sha256': hashlib.sha256(file_bytes).hexdigest(),
        'file_is_canonical': file_bytes == record.canonical_bytes,
        'sample_binding': record.sample_binding,
        'validation_scope': record.validation_scope,
        'provenance': dict(record.provenance),
        'role': sample.role,
        'time': sample.evaluation.time.to_record(),
        'time_seconds_display': sample.evaluation.time.display().seconds_binary64,
        'species_ids': list(record.context.energy_identity[2]),
        'cell_count': count,
        'selected_cell_index': cell_index,
        'interface_modes': list(modes) if modes is not None else None,
        'cells': cells,
        'column_source_ids': list(sample.evaluation.source_evaluation.source_ids),
        'material_qualified': False,
        'resume_authorized': False,
        'source_assets_verified': False,
        'full_run_validated': False,
        'scientific_status': 'saved_declared_observation_not_material_validation',
    }


def inspect_source_observation(path, *, cell_index=None):
    """Read exact preserved values and declared source references without EOS."""
    raw = _read_bounded(path, MAX_RECORD_BYTES, 'source_observation_file_limit')
    record = decode_source_sample(raw)
    return _summary(record, path, raw, cell_index)


def import_source_capture(source, output, *, capture_index):
    """Import one explicit packed_input/evaluation/phase legacy capture.

The input SHA binds the complete supplied file. Only the selected observation
and its explicit context are validated; the rest of the run remains unaudited.
"""
    _require(type(capture_index) is int and capture_index >= 0, 'source_capture_index')
    raw = _read_bounded(source, MAX_IMPORT_BYTES, 'source_capture_file_limit')
    try:
        document = json.loads(raw, object_pairs_hook=_unique, parse_constant=_constant)
    except (TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('source_capture_invalid_json') from exc
    _require(type(document) is dict and type(document.get('captures')) is list,
             'source_capture_list_required')
    _require(capture_index < len(document['captures']), 'source_capture_index')
    capture = document['captures'][capture_index]
    _require(type(capture) is dict and type(capture.get('evaluation')) is dict,
             'source_capture_complete_evaluation_required')
    _require(not capture.get('failure'), 'source_capture_failed_observation')
    provenance = document.get('adapter_provenance')
    _require(isinstance(provenance, Mapping)
             and type(provenance.get('fixed_dry_mass_kg')) is list,
             'source_capture_explicit_mass_context_required')
    _require(all(name in capture for name in
                 ('packed_input', 'operator_identity', 'energy_identity', 'phase', 'time')),
             'source_capture_complete_context_required')
    fields = capture['evaluation'].get('fields')
    _require(type(fields) is dict and 'time' in fields,
             'source_capture_evaluation_time_required')
    _require(json.dumps(capture['time'], sort_keys=True, separators=(',', ':'), allow_nan=False)
             == json.dumps(fields['time'], sort_keys=True, separators=(',', ':'), allow_nan=False),
             'source_capture_time_mismatch')
    modes = capture.get('interface_modes')
    _require(modes is None or type(modes) is list, 'source_capture_interface_modes')
    context = SourceObservationContext(
        _identity(capture['operator_identity'], energy=False),
        _identity(capture['energy_identity'], energy=True),
        tuple(provenance['fixed_dry_mass_kg']),
        None if modes is None else tuple(modes),
    )
    payload = {'state': capture['packed_input'], 'evaluation': capture['evaluation'],
               'role': capture['phase']}
    origin = {
        'input_format': 'explicit_saved_source_capture',
        'input_sha256': hashlib.sha256(raw).hexdigest(),
        'input_path': str(Path(source).resolve()),
        'capture_index': str(capture_index),
        'import_scope': 'selected_observation_only_not_complete_run_validation',
    }
    ordinal = capture.get('ordinal')
    if ordinal is not None:
        _require(type(ordinal) is int and ordinal > 0, 'source_capture_ordinal')
        origin['capture_ordinal'] = str(ordinal)
    record = import_saved_source_sample(
        json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode(),
        context=context, provenance=origin,
    )
    summary = _summary(record, output, record.canonical_bytes, None)
    _write_new(output, record.canonical_bytes)
    return summary
