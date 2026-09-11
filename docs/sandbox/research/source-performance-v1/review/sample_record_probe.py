"""Small saved-observation regression; no new physical evaluation."""
import ast
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import time
from unittest.mock import patch

import numpy as np
import sludge_sandbox.source_observation_record as module
from sludge_sandbox.source_study_audit import _sample_record
from sludge_sandbox.source_net_panel import SavedSourceSample
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.source_wet_storage import SourceWetStorage
from sludge_sandbox.water_properties import WaterProperties
from sludge_sandbox.water_heos import HEOSWaterProperties

out = Path(__file__).parent
repo = Path('/Users/wanggaoying/Desktop/brickmodel-github')
started = time.monotonic()
old_source = subprocess.check_output(['git', 'show', '86d9733:src/sludge_sandbox/source_observation_record.py'], cwd=repo).decode()
old_ast = ast.parse(old_source)
function = next(n for n in old_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'encode_source_sample')
namespace = dict(vars(module))
exec(compile(ast.Module(body=[function], type_ignores=[]), '<baseline-encode-86d9733>', 'exec'), namespace)
old_encode = namespace['encode_source_sample']
fixture = repo/'tests/sandbox/fixtures/source-observation-v1/native-captures.json'
saved = json.loads(fixture.read_bytes())
checks = []
calls = []

def require(value, name):
    assert value, name
    checks.append(name)

def forbidden(*args, **kwargs):
    calls.append('forbidden_physics')
    raise AssertionError('physics forbidden')

def tuples(value):
    return tuple(tuples(v) for v in value) if type(value) is list else value

def error(operation):
    try:
        operation()
    except module.SourceObservationRecordError as exc:
        return type(exc).__name__, str(exc)
    raise AssertionError('expected original rejection')

with ExitStack() as stack:
    for cls in (ExactSourceColumn, SourceWetStorage, WaterProperties, HEOSWaterProperties):
        stack.enter_context(patch.object(cls, '__init__', forbidden))
    for cls, names in ((ExactSourceColumn, ('evaluate',)), (SourceWetStorage, ('evaluate', 'invert')),
                       (WaterProperties, ('state_tp', 'state_tp_response', 'saturation_pair', 'ideal_vapor')),
                       (HEOSWaterProperties, ('state_tp', 'state_tp_response', 'saturation_pair', 'ideal_vapor'))):
        for name in names:
            stack.enter_context(patch.object(cls, name, forbidden))
    for index, capture in enumerate(saved['captures']):
        context = module.SourceObservationContext(tuples(capture['operator_identity']), tuples(capture['energy_identity']),
            tuple(saved['adapter_provenance']['fixed_dry_mass_kg']), tuples(capture['interface_modes']))
        sample = SavedSourceSample(module._legacy(capture['packed_input']), module._legacy(capture['evaluation']), capture['phase'])
        provenance = {'review': 'saved actual native observation; caller claim only'}
        baseline = old_encode(sample, context=context, provenance=provenance)
        old_record = module.decode_source_sample(baseline)
        record = module.create_source_sample_record(sample, context=context, provenance=provenance)
        require(record.canonical_bytes == baseline == module.encode_source_sample(sample, context=context, provenance=provenance), f'{index}:baseline_bytes')
        require(module.pack(module._project(record.sample)) == module.pack(module._project(old_record.sample)), f'{index}:all_sample_fields')
        require(record.context == old_record.context and record.sample_binding == old_record.sample_binding, f'{index}:context_binding')
        require(record.provenance == old_record.provenance and record.validation_scope == old_record.validation_scope
                and record.material_qualified is False and record.resume_authorized is False, f'{index}:metadata_scope')
        require(record.sample is not sample and record.context is not context
                and not np.shares_memory(record.sample.state.amounts_mol, sample.state.amounts_mol), f'{index}:owned_snapshot')
        for array in (record.sample.state.amounts_mol, record.sample.state.internal_energy_j,
                      record.sample.evaluation.rates.face_species_mol_s):
            try:
                array.setflags(write=True)
            except ValueError:
                pass
            else:
                raise AssertionError('array writable')
        require(True, f'{index}:readonly_buffers')
        bad_context = replace(context, operator_identity=('source_wrong', '0' * 64))
        for suffix, kwargs in [('context', dict(context=bad_context)), ('provenance', dict(context=context, provenance={'a': 1}))]:
            require(error(lambda: old_encode(sample, **kwargs)) == error(lambda: module.create_source_sample_record(sample, **kwargs)), f'{index}:same_{suffix}_error')
        decoder, decodes = module.decode_source_sample, []
        def counted(raw, **kwargs):
            decodes.append(kwargs)
            return decoder(raw, **kwargs)
        with patch.object(module, 'decode_source_sample', counted):
            from_study = _sample_record(sample.state, sample.evaluation, sample.role, (context,), context.interface_modes)
        require(len(decodes) == 1 and decodes[0]['expected_context'] is context, f'{index}:single_decode_and_external_context')
        require(from_study.canonical_bytes == old_encode(sample, context=context), f'{index}:study_baseline_bytes')
        # Mutate caller-owned containers after validation; the decoded snapshot is independent.
        provenance['review'] = 'changed'
        object.__setattr__(context, 'fixed_dry_mass_kg', (0.3,) * len(context.fixed_dry_mass_kg))
        object.__setattr__(sample.state, 'internal_energy_j', np.zeros_like(sample.state.internal_energy_j))
        require(record.context == old_record.context and record.provenance == old_record.provenance
                and module.pack(module._project(record.sample)) == module.pack(module._project(old_record.sample)), f'{index}:caller_mutation_isolation')
        record.check()
        require(True, f'{index}:passive_check_after_input_mutation')

require(not calls, 'zero_physics')
result = dict(status='passed', checks=checks, check_count=len(checks), elapsed_seconds=time.monotonic()-started,
    baseline='86d9733 original encode AST, same unchanged decoder and schema', native_observations=len(saved['captures']),
    fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(), live_physics_calls=len(calls))
(out/'SAMPLE_RECORD_PROBE.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
