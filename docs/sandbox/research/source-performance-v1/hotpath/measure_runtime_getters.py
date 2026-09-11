"""Bounded read-only CoolProp metadata measurement; no state construction/EOS."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from statistics import median
from time import perf_counter


def main() -> None:
    started = perf_counter()
    import CoolProp.CoolProp as cp

    import_seconds = perf_counter() - started
    manifest_path = Path(
        '/Users/wanggaoying/Desktop/brickmodel-github/data/sandbox/water/'
        'heos-8.0.0-approved-manifest.json'
    )
    manifest_bytes = manifest_path.read_bytes()
    expected = json.loads(manifest_bytes)
    expected_config = json.dumps(expected['config'], sort_keys=True)
    samples = []
    for index in range(32):
        t0 = perf_counter()
        config_raw = cp.get_config_as_json_string()
        t1 = perf_counter()
        config = json.dumps(json.loads(config_raw), sort_keys=True)
        t2 = perf_counter()
        fluid_raw = cp.get_fluid_param_string('Water', 'JSON')
        t3 = perf_counter()
        fluid_sha256 = hashlib.sha256(fluid_raw.encode()).hexdigest()
        t4 = perf_counter()
        # This canonical parse/hash is constructor-only, not _transaction work.
        canonical = json.dumps(json.loads(fluid_raw), sort_keys=True, separators=(',', ':'))
        canonical_sha256 = hashlib.sha256(canonical.encode()).hexdigest()
        t5 = perf_counter()
        assert config == expected_config
        assert fluid_sha256 == expected['fluid_sha256']
        assert canonical_sha256 == expected['fluid_canonical_sha256']
        samples.append({
            'index': index,
            'config_getter_seconds': t1 - t0,
            'config_parse_sort_seconds': t2 - t1,
            'fluid_getter_seconds': t3 - t2,
            'fluid_encode_hash_seconds': t4 - t3,
            'fluid_parse_canonical_hash_seconds': t5 - t4,
            'actual_transaction_one_check_seconds': t4 - t0,
            'config_bytes': len(config_raw.encode()),
            'fluid_bytes': len(fluid_raw.encode()),
            'fluid_sha256': fluid_sha256,
        })
    keys = [key for key in samples[0] if key.endswith('_seconds')]
    result = {
        'scope': 'read-only metadata; no AbstractState/provider construction, EOS or setters',
        'get_config_calls': 32,
        'get_fluid_json_calls': 32,
        'constructor_calls': 0,
        'eos_calls': 0,
        'setter_calls': 0,
        'import_seconds': import_seconds,
        'elapsed_seconds': perf_counter() - started,
        'coolprop_version': importlib.metadata.version('CoolProp'),
        'loaded_extension': cp.__file__,
        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
        'samples': samples,
        'summary': {
            key: {
                'total': sum(row[key] for row in samples),
                'mean': sum(row[key] for row in samples) / len(samples),
                'median': median(row[key] for row in samples),
                'minimum': min(row[key] for row in samples),
                'maximum': max(row[key] for row in samples),
            } for key in keys
        },
    }
    output = Path(__file__).with_name('RUNTIME_GETTERS.json')
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'samples'}, indent=2))


if __name__ == '__main__':
    main()
