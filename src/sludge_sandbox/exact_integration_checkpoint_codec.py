"""Versioned, closed pure-data codec for ordinary accepted-prefix checkpoints.

Both directions replay the saved numerical callbacks through ``checkpoint.check``;
they never construct an EOS/provider or call a new physical operator. This checks
the saved arithmetic, not source authenticity or historical wall-clock truth.
An application must separately bind its live operator and debit actual decoding
and reconstruction time through ``admission_elapsed_seconds`` before continuation.
"""
from collections.abc import Mapping
from dataclasses import dataclass, fields
from fractions import Fraction
import hashlib
import json
import math
import re
from types import MappingProxyType, UnionType
import typing

import numpy as np
from numpy.typing import NDArray

from .exact_event_clock import ExactEventTime
from .exact_integration import ExactIntegrationResult, ExactStepLedger
from .exact_integration_checkpoint import (
    ExactCallbackObservation, ExactIntegrationCheckpoint, ExactIntegrationProblem,
)
from .integration import ConservedState, IntegrationPolicy, Rates

SCHEMA = 'exact_integration_checkpoint_v1'
VALIDATION_SCOPE = 'ordinary_checkpoint_closed_schema_and_passive_arithmetic_replay'
MAX_BYTES = 32 * 1024 * 1024
MAX_NODES = 300_000
MAX_DEPTH = 96
MAX_INTEGER_BITS = 4096
MAX_STRING_BYTES = 65_536
MAX_ARRAY_VALUES = 250_000
MAX_OBSERVATIONS = 4096
MAX_ACCEPTED_STEPS = 256

# Explicit version-one class AND field names: an upstream added field cannot be
# silently admitted to this wire schema. No input controls imports or attributes.
_FIELD_NAMES = {
    ExactEventTime: 'seconds',
    ConservedState: 'amounts_mol internal_energy_j energy_model_identity mechanical_stretches',
    Rates: ('face_species_mol_s face_energy_w reaction_species_mol_s cell_power_w '
            'cell_power_components_w component_sum_residual_w mechanical_rates_per_s'),
    IntegrationPolicy: ('initial_step_s maximum_step_s minimum_step_s relative_tolerance '
        'amount_absolute_tolerance_mol energy_absolute_tolerance_j amount_scale_mol energy_scale_j '
        'maximum_steps maximum_rejections maximum_wall_seconds stretch_absolute_tolerance stretch_scale'),
    ExactStepLedger: ('start_s end_s face_species_mol face_energy_j reaction_species_mol cell_work_j '
        'cell_work_components_j component_quadrature_roundoff_j component_sum_residual_j '
        'stretch_increment stretch_quadrature_roundoff'),
    ExactIntegrationResult: ('status reason times_s states steps evaluations rejected_trials elapsed_seconds '
        'attempted_trials cumulative_absolute_component_residual_j'),
    ExactCallbackObservation: ('ordinal attempt_index role state time rates returned_type validated '
        'failure_kind failure_message'),
    ExactIntegrationProblem: 'initial start_s end_s policy breakpoints_s',
    ExactIntegrationCheckpoint: ('problem result next_step_s knot_index component_schema cumulative_n '
        'cumulative_u cumulative_components cumulative_stretch cumulative_stretch_exact '
        'cumulative_stretch_roundoff observations binding_sha256 phase initial_probe_done'),
}
_REGISTRY = {cls.__name__: cls for cls in _FIELD_NAMES}
_HINTS = {cls: typing.get_type_hints(cls) for cls in _FIELD_NAMES}
_SHA = re.compile('[0-9a-f]{64}')


class ExactCheckpointCodecError(ValueError):
    """Malformed, over-budget or numerically inconsistent checkpoint data."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExactCheckpointCodecError(reason)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


@dataclass
class _Budget:
    nodes: int = 0
    array_values: int = 0
    wire_bytes: int = 0

    def reserve(self, size: int) -> None:
        self.wire_bytes += size
        _require(self.wire_bytes <= MAX_BYTES, 'checkpoint_codec_encoding_size_limit')

    def visit(self, depth: int) -> None:
        self.nodes += 1
        _require(depth <= MAX_DEPTH and self.nodes <= MAX_NODES, 'checkpoint_codec_tree_limit')

    def array(self, size: int) -> None:
        self.array_values += size
        _require(self.array_values <= MAX_ARRAY_VALUES, 'checkpoint_codec_array_limit')


def _string(value: str) -> None:
    _require(len(value.encode('utf-8')) <= MAX_STRING_BYTES, 'checkpoint_codec_string_limit')


def _integer(value: int) -> None:
    _require(value.bit_length() <= MAX_INTEGER_BITS, 'checkpoint_codec_integer_limit')


def _matches(value: object, hint: object) -> bool:
    """Fail closed on the trusted whitelist's annotations; bool is never real."""
    origin, args = typing.get_origin(hint), typing.get_args(hint)
    if origin in (typing.Union, UnionType):
        return any(_matches(value, item) for item in args)
    if hint is float:
        # IntegrationPolicy intentionally accepts exact Python ints as real
        # inputs. Their original representation is retained, never coerced.
        return type(value) in (int, float)
    if hint in (str, bool, int, Fraction, type(None)):
        return type(value) is hint
    if hint is tuple:
        return type(value) is tuple  # Only the opaque energy identity; constructor checks it.
    if origin is tuple:
        if type(value) is not tuple:
            return False
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_matches(item, args[0]) for item in value)
        return len(value) == len(args) and all(_matches(v, h) for v, h in zip(value, args))
    if origin is Mapping:
        return type(value) in (dict, MappingProxyType) and all(
            _matches(k, args[0]) and _matches(v, args[1]) for k, v in value.items())
    if origin is np.ndarray or origin is NDArray or hint is np.ndarray:
        return type(value) is np.ndarray
    if hint in _FIELD_NAMES:
        return type(value) is hint
    return False


def _record_fields(cls: type, values: Mapping[str, object]) -> None:
    names = set(_FIELD_NAMES[cls].split())
    _require(names == {field.name for field in fields(cls)}, 'checkpoint_codec_runtime_schema_changed')
    _require(set(values) == names, 'checkpoint_codec_record_fields:' + cls.__name__)
    for name, value in values.items():
        _require(_matches(value, _HINTS[cls][name]),
                 'checkpoint_codec_field_type:' + cls.__name__ + '.' + name)


def _encode(value: object, budget: _Budget, depth: int = 0) -> object:
    budget.visit(depth)
    # Conservative structural overhead keeps live inputs bounded before JSON
    # serialization or passive replay can duplicate their complete history.
    budget.reserve(128)
    cls = type(value)
    if value is None or cls is bool:
        return value
    if cls is str:
        _string(value)
        budget.reserve(len(_canonical(value)))
        return value
    if cls is int:
        _integer(value)
        budget.reserve(len(str(value)))
        return value
    if cls is float:
        _require(math.isfinite(value), 'checkpoint_codec_finite_float')
        return {'float_hex': value.hex()}
    if cls is Fraction:
        _integer(value.numerator)
        _integer(value.denominator)
        budget.reserve(len(str(value.numerator)) + len(str(value.denominator)))
        return {'fraction': [value.numerator, value.denominator]}
    if cls is np.ndarray:
        _require(value.dtype == np.float64 and value.ndim in (1, 2) and value.size > 0,
                 'checkpoint_codec_binary64_array')
        budget.array(value.size)
        budget.reserve(16 * value.size)
        _require(np.all(np.isfinite(value)), 'checkpoint_codec_finite_array')
        # Fixed little-endian wire storage also preserves -0 and subnormal bits.
        return {'array': {'shape': list(value.shape), 'dtype': '<f8',
                          'data_hex': value.astype('<f8', copy=False).tobytes().hex()}}
    if cls is tuple:
        return {'tuple': [_encode(item, budget, depth + 1) for item in value]}
    if cls in (dict, MappingProxyType):
        _require(all(type(key) is str for key in value), 'checkpoint_codec_mapping_keys')
        for key in value:
            _string(key)
            budget.reserve(len(_canonical(key)))
        return {'mapping': [[key, _encode(item, budget, depth + 1)] for key, item in value.items()]}
    _require(cls in _FIELD_NAMES, 'checkpoint_codec_unknown_type')
    body = {field.name: getattr(value, field.name) for field in fields(cls)}
    _record_fields(cls, body)
    return {'record': cls.__name__,
            'fields': {name: _encode(item, budget, depth + 1) for name, item in body.items()}}


def _array(body: object, budget: _Budget) -> np.ndarray:
    _require(type(body) is dict and set(body) == {'shape', 'dtype', 'data_hex'},
             'checkpoint_codec_array_fields')
    shape = body['shape']
    _require(type(shape) is list and len(shape) in (1, 2) and
             all(type(n) is int and n > 0 for n in shape), 'checkpoint_codec_array_shape')
    size = math.prod(shape)
    budget.array(size)  # Before bytes allocation or ndarray construction.
    data = body['data_hex']
    _require(body['dtype'] == '<f8' and type(data) is str and len(data) == 16 * size
             and re.fullmatch('[0-9a-f]+', data) is not None, 'checkpoint_codec_array_bytes')
    little = np.frombuffer(bytes.fromhex(data), dtype='<f8').reshape(shape)
    _require(np.all(np.isfinite(little)), 'checkpoint_codec_finite_array')
    # Keep a bytes-backed, native binary64 snapshot even on a big-endian host.
    return np.frombuffer(little.astype(np.float64, copy=False).tobytes(), dtype=np.float64).reshape(shape)


def _decode(value: object, budget: _Budget, depth: int = 0) -> object:
    budget.visit(depth)
    if value is None or type(value) in (str, bool, int):
        return value
    _require(type(value) is dict, 'checkpoint_codec_tagged_value')
    tags = set(value)
    if tags == {'float_hex'}:
        raw = value['float_hex']
        _require(type(raw) is str and len(raw) <= 32, 'checkpoint_codec_float_hex')
        number = float.fromhex(raw)
        _require(math.isfinite(number) and number.hex() == raw, 'checkpoint_codec_canonical_float')
        return number
    if tags == {'fraction'}:
        pair = value['fraction']
        _require(type(pair) is list and len(pair) == 2 and all(type(x) is int for x in pair)
                 and pair[1] > 0 and math.gcd(*pair) == 1, 'checkpoint_codec_canonical_fraction')
        return Fraction(*pair)
    if tags == {'array'}:
        return _array(value['array'], budget)
    if tags == {'tuple'}:
        _require(type(value['tuple']) is list, 'checkpoint_codec_tuple')
        return tuple(_decode(item, budget, depth + 1) for item in value['tuple'])
    if tags == {'mapping'}:
        pairs = value['mapping']
        _require(type(pairs) is list, 'checkpoint_codec_mapping_pairs')
        result = {}
        for pair in pairs:
            _require(type(pair) is list and len(pair) == 2 and type(pair[0]) is str
                     and pair[0] not in result, 'checkpoint_codec_unique_mapping_keys')
            result[pair[0]] = _decode(pair[1], budget, depth + 1)
        return MappingProxyType(result)
    _require(tags == {'record', 'fields'} and type(value['record']) is str
             and value['record'] in _REGISTRY and type(value['fields']) is dict,
             'checkpoint_codec_registered_record')
    cls = _REGISTRY[value['record']]
    _require(set(value['fields']) == set(_FIELD_NAMES[cls].split()),
             'checkpoint_codec_record_fields:' + cls.__name__)
    body = {name: _decode(item, budget, depth + 1) for name, item in value['fields'].items()}
    _record_fields(cls, body)
    record = cls(**{field.name: body[field.name] for field in fields(cls) if field.init})
    # Includes init=False diagnostics. Constructors cannot silently normalize or
    # replace original bits, mapping order, derived fields, or scalar types.
    _require(_encode(record, _Budget()) == value,
             'checkpoint_codec_constructor_changed_fields:' + cls.__name__)
    return record


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        _require(key not in result, 'checkpoint_codec_duplicate_json_key')
        result[key] = value
    return result


def _parse_integer(raw: str) -> int:
    _require(len(raw) <= 1235, 'checkpoint_codec_integer_limit')
    value = int(raw)
    _integer(value)
    return value


def _reject_json_number(raw: str) -> object:
    raise ExactCheckpointCodecError('checkpoint_codec_untagged_real:' + raw[:32])


def _parse(raw: bytes) -> object:
    _require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'checkpoint_codec_bounded_bytes')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object,
                       parse_int=_parse_integer, parse_float=_reject_json_number,
                       parse_constant=_reject_json_number)
    budget = _Budget()
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        budget.visit(depth)
        if type(item) is dict:
            for key, child in item.items():
                _string(key)
                # Array hex has its own byte/count cap; arbitrary strings do not.
                if key == 'data_hex' and type(child) is str:
                    _require(len(child) <= MAX_ARRAY_VALUES * 16, 'checkpoint_codec_array_limit')
                else:
                    pending.append((child, depth + 1))
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            _string(item)
    return value


def _check(checkpoint: ExactIntegrationCheckpoint) -> None:
    _require(type(checkpoint) is ExactIntegrationCheckpoint, 'checkpoint_codec_checkpoint_type')
    _require(len(checkpoint.observations) <= MAX_OBSERVATIONS and
             len(checkpoint.result.steps) <= MAX_ACCEPTED_STEPS, 'checkpoint_codec_replay_limit')
    checkpoint.check()


def encode_exact_checkpoint(checkpoint: ExactIntegrationCheckpoint) -> bytes:
    """Return canonical full evidence after bounded schema and arithmetic checks.

    Only a clean interior accepted-boundary pause is persistable. Failure tails
    and generic run results need their separate evidence formats.
    """
    try:
        payload = _encode(checkpoint, _Budget())
        _check(checkpoint)
        data = {'schema': SCHEMA, 'validation_scope': VALIDATION_SCOPE,
                'source_resume_authorized': False, 'checkpoint': payload,
                'payload_sha256': hashlib.sha256(_canonical(payload)).hexdigest()}
        raw = _canonical(data)
        _parse(raw)  # The encoder observes the same wire resource limits.
        return raw
    except ExactCheckpointCodecError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError) as exc:
        raise ExactCheckpointCodecError('invalid_exact_checkpoint:' + str(exc)) from exc


def decode_exact_checkpoint(raw: bytes) -> ExactIntegrationCheckpoint:
    """Restore and passively replay pure data; grant no live source authority."""
    try:
        data = _parse(raw)
        _require(type(data) is dict and set(data) == {'schema', 'validation_scope',
                 'source_resume_authorized', 'checkpoint', 'payload_sha256'}, 'checkpoint_codec_envelope')
        _require(data['schema'] == SCHEMA and data['validation_scope'] == VALIDATION_SCOPE
                 and data['source_resume_authorized'] is False, 'checkpoint_codec_version_and_scope')
        sha = data['payload_sha256']
        _require(type(sha) is str and _SHA.fullmatch(sha) is not None and
                 sha == hashlib.sha256(_canonical(data['checkpoint'])).hexdigest(),
                 'checkpoint_codec_payload_sha256')
        checkpoint = _decode(data['checkpoint'], _Budget())
        _check(checkpoint)
        return checkpoint
    except ExactCheckpointCodecError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError) as exc:
        raise ExactCheckpointCodecError('invalid_exact_checkpoint:' + str(exc)) from exc
