"""Installable passive codec for complete source observations, without resume.

The shared exact-record codec owns primitive representation. This module only
projects a closed set of source dataclasses and validates their associations.
Legacy research JSON is accepted solely through the explicit import entry.
"""
from collections.abc import Mapping
from dataclasses import dataclass, fields
from fractions import Fraction
from types import MappingProxyType, UnionType
import hashlib
import math
import re
import typing

import numpy as np

from .exact_record import pack, unpack, canonical
from .exact_event_clock import ExactEventTime
from .source_net_panel import SavedSourceSample, _validate
from .source_observation_schema import (
    CLASSES, REGISTRY, OPERATOR, ENERGY, SourceObservationRecordError,
    require, strict_json, matches, field_hints, validate_fields, validate_associations,
)

SCHEMA = 'source_observation_record_v1'
VALIDATION_SCOPE = 'passive_complete_source_sample_schema_and_associations_not_eos_authentication_or_resume'
MAX_BYTES = 16 * 1024 * 1024
MAX_NODES = 250_000
MAX_DEPTH = 96


@dataclass(frozen=True)
class SourceObservationContext:
    operator_identity: tuple
    energy_identity: tuple
    fixed_dry_mass_kg: tuple[float, ...]
    interface_modes: tuple[str, ...] | None = None


def _context_check(context: SourceObservationContext) -> None:
    require(type(context) is SourceObservationContext, 'explicit_source_observation_context')
    require(matches(context.operator_identity, OPERATOR) and matches(context.energy_identity, ENERGY),
            'source_context_identity_types')
    require(re.fullmatch('[0-9a-f]{64}', context.operator_identity[1]) is not None
            and all(re.fullmatch('[0-9a-f]{64}', item) is not None for item in context.energy_identity[1]),
            'source_context_identity_sha')
    require(type(context.fixed_dry_mass_kg) is tuple and bool(context.fixed_dry_mass_kg)
            and all(type(x) is float and math.isfinite(x) and x > 0 for x in context.fixed_dry_mass_kg),
            'source_context_fixed_masses')
    if context.interface_modes is not None:
        require(type(context.interface_modes) is tuple
                and len(context.interface_modes) == len(context.fixed_dry_mass_kg)
                and all(type(x) is str and x in ('existing_liquid', 'depleted_no_nucleation')
                        for x in context.interface_modes), 'source_context_modes')


def _provenance(value: Mapping[str, str] | None) -> Mapping:
    if value is None:
        return MappingProxyType({})
    require(isinstance(value, Mapping) and all(type(k) is str and k and type(v) is str
                                              for k, v in value.items()), 'source_provenance_strings')
    return MappingProxyType(dict(value))


def _budget(value: object) -> None:
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        require(count <= MAX_NODES and depth <= MAX_DEPTH, 'source_record_resource_limit')
        if type(item) is dict:
            pending.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            pending.extend((v, depth + 1) for v in item)


def _parse(raw: bytes) -> object:
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'bounded_source_record_bytes_required')
    value = strict_json(raw)
    _budget(value)
    return value


def _project(value: object) -> object:
    cls = type(value)
    if cls in CLASSES:
        validate_fields(value)
        return {'type': cls.__module__ + '.' + cls.__qualname__,
                'fields': {f.name: _project(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, Mapping):
        require(all(type(k) is str for k in value), 'source_mapping_string_keys')
        return {k: _project(v) for k, v in value.items()}
    if cls is tuple:
        return tuple(_project(v) for v in value)
    require(value is None or cls in (str, int, bool, float, Fraction, ExactEventTime, np.ndarray),
            'unsupported_source_value')
    if cls is np.ndarray:
        require(value.dtype == np.float64 and np.all(np.isfinite(value)), 'source_binary64_array')
    if cls is ExactEventTime:
        require(type(value.seconds) is Fraction, 'source_exact_time')
    return value


def _record_type(value: object) -> type | None:
    if isinstance(value, Mapping) and set(value) == {'type', 'fields'}:
        require(type(value['type']) is str and value['type'] in REGISTRY, 'unknown_source_record_class')
        return REGISTRY[value['type']]
    return None


def _restore(value: object, hint: object) -> object:
    origin, args = typing.get_origin(hint), typing.get_args(hint)
    if origin in (typing.Union, UnionType):
        cls = _record_type(value)
        candidates = ([h for h in args if h is cls] if cls is not None else
                      [h for h in args if matches(value, h) or
                       (typing.get_origin(h) is tuple and type(value) is tuple)])
        require(len(candidates) == 1, 'source_union_field_type')
        return _restore(value, candidates[0])
    if isinstance(hint, type) and hint in CLASSES:
        require(_record_type(value) is hint, 'source_nested_record_type:' + hint.__name__)
        body = value['fields']
        require(isinstance(body, Mapping) and set(body) == {f.name for f in fields(hint)},
                'source_complete_record_fields:' + hint.__name__)
        hints = field_hints(hint)
        values = {name: _restore(v, hints[name]) for name, v in body.items()}
        record = hint(**{f.name: values[f.name] for f in fields(hint) if f.init})
        validate_fields(record)
        require(pack(_project(record)) == pack(value), 'source_constructor_changed_fields:' + hint.__name__)
        return record
    if origin is tuple:
        require(type(value) is tuple, 'source_tuple_field')
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_restore(v, args[0]) for v in value)
        require(len(value) == len(args), 'source_tuple_field_length')
        return tuple(_restore(v, h) for v, h in zip(value, args))
    if origin in (Mapping, typing.Mapping):
        require(isinstance(value, Mapping), 'source_mapping_field')
        return MappingProxyType({_restore(k, args[0]): _restore(v, args[1]) for k, v in value.items()})
    require(matches(value, hint), 'source_scalar_or_array_field_type')
    return value


def _check_sample(sample: SavedSourceSample, context: SourceObservationContext) -> str:
    _context_check(context)
    binding = _validate(sample, context.operator_identity, context.energy_identity, context.fixed_dry_mass_kg)
    validate_associations(sample, context.energy_identity)
    if context.interface_modes is not None:
        for mode, state, cell in zip(context.interface_modes, sample.evaluation.source_states,
                                      sample.evaluation.source_evaluation.cells):
            require((mode == 'existing_liquid' and state.liquid_water_mol > 0)
                    or (mode == 'depleted_no_nucleation' and state.liquid_water_mol == 0
                        and cell.phase.phase_water_mol_s == 0
                        and cell.phase.chemical_driving_force_j_mol is None
                        and cell.phase.entropy_production_w_k is None), 'source_declared_mode_mismatch')
    return binding


@dataclass(frozen=True)
class SourceObservationRecord:
    canonical_bytes: bytes
    context: SourceObservationContext
    sample: SavedSourceSample
    sample_binding: str
    provenance: Mapping[str, str]
    validation_scope: str = VALIDATION_SCOPE
    material_qualified: bool = False
    resume_authorized: bool = False

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    def check(self) -> None:
        try:
            expected = decode_source_sample(self.canonical_bytes, expected_context=self.context)
            require(type(self.validation_scope) is str and self.validation_scope == VALIDATION_SCOPE
                    and self.material_qualified is False and self.resume_authorized is False,
                    'source_record_scope_changed')
            require(type(self.sample_binding) is str and self.sample_binding == expected.sample_binding
                    and pack(_project(self.sample)) == pack(_project(expected.sample))
                    and pack(self.provenance) == pack(expected.provenance), 'source_record_content_changed')
        except SourceObservationRecordError:
            raise
        except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError) as exc:
            raise SourceObservationRecordError('invalid_source_observation:' + str(exc)) from exc


def create_source_sample_record(sample: SavedSourceSample, *, context: SourceObservationContext,
                                provenance: Mapping[str, str] | None = None) -> SourceObservationRecord:
    """Return the fully decoded, validated snapshot from one encoding pass.

    The decoder owns the returned passive fields. Reusing this result avoids
    decoding the same newly encoded bytes twice; it does not skip validation
    or cache a caller's mutable sample/context across operations.
    """
    try:
        _context_check(context)
        projected = _project(sample)
        require(type(sample) is SavedSourceSample, 'explicit_saved_source_sample')
        binding = _check_sample(sample, context)
        data = dict(schema=SCHEMA, validation_scope=VALIDATION_SCOPE,
            context=pack({f.name: getattr(context, f.name) for f in fields(context)}),
            sample=pack(projected), sample_binding=binding, provenance=pack(_provenance(provenance)),
            material_qualified=False, resume_authorized=False)
        raw = canonical(data)
        return decode_source_sample(raw, expected_context=context)
    except SourceObservationRecordError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError) as exc:
        raise SourceObservationRecordError('invalid_source_observation:' + str(exc)) from exc


def encode_source_sample(sample: SavedSourceSample, *, context: SourceObservationContext,
                         provenance: Mapping[str, str] | None = None) -> bytes:
    """Snapshot one complete observation; caller provenance does not certify it."""
    return create_source_sample_record(sample, context=context, provenance=provenance).canonical_bytes


def decode_source_sample(raw: bytes, *,
                         expected_context: SourceObservationContext | None = None) -> SourceObservationRecord:
    """Reconstruct only passive records and their saved numerical associations."""
    try:
        data = _parse(raw)
        require(type(data) is dict and set(data) == {'schema', 'validation_scope', 'context', 'sample',
            'sample_binding', 'provenance', 'material_qualified', 'resume_authorized'}, 'source_record_fields')
        require(data['schema'] == SCHEMA and data['validation_scope'] == VALIDATION_SCOPE
                and data['material_qualified'] is False and data['resume_authorized'] is False,
                'source_record_schema_or_scope')
        context_values = unpack(data['context'])
        require(isinstance(context_values, Mapping)
                and set(context_values) == {f.name for f in fields(SourceObservationContext)}, 'source_context_fields')
        context = SourceObservationContext(**context_values)
        _context_check(context)
        if expected_context is not None:
            _context_check(expected_context)
            require(pack(context_values) == pack({f.name: getattr(expected_context, f.name)
                    for f in fields(expected_context)}), 'external_source_context_mismatch')
        sample = _restore(unpack(data['sample']), SavedSourceSample)
        binding = _check_sample(sample, context)
        require(type(data['sample_binding']) is str and binding == data['sample_binding'], 'source_sample_binding')
        provenance = _provenance(unpack(data['provenance']))
        return SourceObservationRecord(canonical(data), context, sample, binding, provenance)
    except SourceObservationRecordError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError) as exc:
        raise SourceObservationRecordError('invalid_source_observation:' + str(exc)) from exc


def _legacy_project(value: object) -> object:
    if type(value) is ExactEventTime:
        return {'type': ExactEventTime.__module__ + '.ExactEventTime',
                'fields': {'seconds': _legacy_project(value.seconds)}}
    if type(value) is Fraction:
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if type(value) is np.ndarray:
        return {'dtype': 'float64', 'shape': list(value.shape), 'values': value.tolist()}
    if type(value) in CLASSES:
        return {'type': type(value).__module__ + '.' + type(value).__qualname__,
                'fields': {f.name: _legacy_project(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, Mapping):
        return {k: _legacy_project(v) for k, v in value.items()}
    if type(value) is tuple:
        return [_legacy_project(v) for v in value]
    return value


def _legacy(value: object) -> object:
    if type(value) is list:
        return tuple(_legacy(v) for v in value)
    if type(value) is not dict:
        require(value is None or type(value) in (str, int, bool, float), 'legacy_primitive')
        require(type(value) is not float or math.isfinite(value), 'legacy_finite_float')
        return value
    if set(value) == {'numerator', 'denominator'}:
        n, d = value['numerator'], value['denominator']
        require(type(n) is type(d) is int and d > 0 and math.gcd(n, d) == 1, 'legacy_canonical_fraction')
        return Fraction(n, d)
    if set(value) == {'dtype', 'shape', 'values'}:
        require(value['dtype'] == 'float64' and type(value['shape']) is list
                and 1 <= len(value['shape']) <= 2
                and all(type(n) is int and n > 0 for n in value['shape']), 'legacy_float64_shape')
        values = _legacy(value['values'])
        def floats(v):
            return all(floats(x) for x in v) if type(v) is tuple else type(v) is float
        require(floats(values), 'legacy_array_float_values')
        array = np.asarray(values, dtype=np.float64)
        require(list(array.shape) == value['shape'] and np.all(np.isfinite(array)), 'legacy_array_shape')
        return np.frombuffer(array.tobytes(), dtype=np.float64).reshape(array.shape)
    if set(value) == {'type', 'fields'}:
        kind = value['type']
        require(type(kind) is str and kind in (*REGISTRY, ExactEventTime.__module__ + '.ExactEventTime'),
                'unknown_legacy_source_record_class')
        cls = REGISTRY.get(kind, ExactEventTime)
        body = value['fields']
        require(type(body) is dict and set(body) == {f.name for f in fields(cls)}, 'legacy_complete_record_fields')
        values = {name: _legacy(v) for name, v in body.items()}
        if cls is not ExactEventTime:
            hints = field_hints(cls)
            require(all(matches(v, hints[k]) for k, v in values.items()), 'legacy_source_field_types')
        record = cls(**{f.name: values[f.name] for f in fields(cls) if f.init})
        if cls is not ExactEventTime:
            validate_fields(record)
        require(canonical(_legacy_project(record)) == canonical(value), 'legacy_constructor_changed_fields')
        return record
    require(all(type(k) is str for k in value), 'legacy_mapping_string_keys')
    return MappingProxyType({k: _legacy(v) for k, v in value.items()})


def import_saved_source_sample(raw: bytes, *, context: SourceObservationContext,
                               provenance: Mapping[str, str] | None = None) -> SourceObservationRecord:
    """Explicit legacy single-capture import; no whole-run restoration or I/O."""
    try:
        data = _parse(raw)
        require(type(data) is dict and set(data) == {'state', 'evaluation', 'role'}, 'legacy_sample_fields')
        sample = SavedSourceSample(_legacy(data['state']), _legacy(data['evaluation']), data['role'])
        return decode_source_sample(encode_source_sample(sample, context=context, provenance=provenance),
                                    expected_context=context)
    except SourceObservationRecordError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError) as exc:
        raise SourceObservationRecordError('invalid_legacy_source_observation:' + str(exc)) from exc
