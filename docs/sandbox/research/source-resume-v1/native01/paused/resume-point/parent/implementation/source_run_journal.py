"""Durable, bounded raw evidence before source-study validation.

This projection is diagnostic data, never a numeric record decoder or a way to
restore live providers. Nonfinite returns remain explicitly tagged failures.
"""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .source_record_io import publish_record_bytes

MAX_EVENT_BYTES = 64 * 1024 * 1024
MAX_JOURNAL_BYTES = 256 * 1024 * 1024
MAX_NODES = 250_000


def raw_projection(value):
    """Keep complete dataclass fields and shared references, without validation."""
    nodes, identities, owners = {}, {}, []
    visits = 0

    def visit(item, depth=0):
        nonlocal visits
        visits += 1
        if depth > 96 or visits > 2_000_000:
            raise ValueError('source_raw_projection_resource_limit')
        cls = type(item)
        if item is None or cls in (str, bool, int):
            return item
        if cls is float:
            return {'binary64': item.hex()} if math.isfinite(item) else {'nonfinite_binary64': repr(item)}
        if cls is Fraction:
            return {'fraction': [item.numerator, item.denominator]}
        key = id(item)
        if key in identities:
            return {'ref': identities[key]}
        if len(nodes) >= MAX_NODES:
            raise ValueError('source_raw_projection_node_limit')
        node_id = str(len(nodes))
        identities[key] = node_id
        owners.append(item)
        node = {'type': cls.__module__ + '.' + cls.__qualname__}
        nodes[node_id] = node
        child = lambda x: visit(x, depth + 1)
        if cls is np.ndarray:
            if item.size > 250_000:
                raise ValueError('source_raw_array_limit')
            node.update(dtype=str(item.dtype), shape=list(item.shape),
                        values=[child(v.item()) for v in item.flat])
        elif isinstance(item, BaseException):
            node.update(message=str(item), args=child(item.args), fields=child(vars(item)),
                        cause=child(item.__cause__ or item.__context__))
        elif cls.__module__ == 'sludge_sandbox.exact_source_column' and cls.__name__ == 'ExactSourceColumn':
            node.update(live_reference_only=True, identity=child(item._identity),
                        modes=child(item.column.interface_modes))
        elif cls.__module__ == 'sludge_sandbox.source_wet_storage' and cls.__name__ == 'SourceWetStorage':
            node.update(live_reference_only=True, identity=child(item._identity))
        elif isinstance(item, Mapping):
            if not all(type(k) is str for k in item):
                raise ValueError('source_raw_mapping_keys')
            node['fields'] = {k: child(v) for k, v in item.items()}
        elif cls in (list, tuple):
            node['values'] = [child(v) for v in item]
        elif isinstance(item, Path):
            node['path'] = str(item)
        elif is_dataclass(item) and not isinstance(item, type):
            node['fields'], node['uninitialized_fields'] = {}, []
            for field in fields(item):
                try:
                    field_value = getattr(item, field.name)
                except AttributeError:
                    node['uninitialized_fields'].append(field.name)
                else:
                    node['fields'][field.name] = child(field_value)
        else:
            # Native kernel handles are not serializable scientific evidence.
            # Their containing wrapper supplies its explicit implementation data.
            node.update(unavailable=True, reason='opaque_runtime_object_not_serializable')
        return {'ref': node_id}

    root = visit(value)
    return {'schema': 'source_run_raw_projection_v1', 'root': root, 'nodes': nodes,
            'numeric_validation_performed': False, 'resume_authorized': False}


class SourceRunJournal:
    """Append immutable event files; a killed worker leaves its last start."""
    def __init__(self, directory):
        self.directory = Path(directory) / 'events'
        self.directory.mkdir()
        self.count = 0
        self.total_bytes = 0

    def append(self, event, payload):
        value = {'event': event, 'ordinal': self.count + 1, 'payload': raw_projection(payload)}
        raw = (json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')) + '\n').encode()
        if len(raw) > MAX_EVENT_BYTES or self.total_bytes + len(raw) > MAX_JOURNAL_BYTES:
            raise ValueError('source_run_journal_byte_limit')
        name = f'{self.count + 1:06d}.json'
        publish_record_bytes(self.directory / name, raw, temporary_prefix='.event-')
        self.count += 1
        self.total_bytes += len(raw)
        return {'path': 'events/' + name, 'sha256': hashlib.sha256(raw).hexdigest()}
