"""Installed passive read/write exercise against three frozen actual artifacts."""
import argparse
from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import signal
import time
from unittest.mock import patch

import numpy as np

from sludge_sandbox.source_observation_record import (
    SourceObservationContext, decode_source_sample, encode_source_sample,
    import_saved_source_sample,
)
from sludge_sandbox.source_observation_service import inspect_source_observation


INPUTS = {
    'n3': (32, 45527737, '2660d33ec0e832e006d5adcccd8ddcf38cc314ac5e65a17830cdf2f73cbdc51d'),
    'n1': (32, 14524919, 'a9d2d658a259e72f871e4f96c8d3e0172def2720a2901bc91c06e78e5a97d4dc'),
    'programmed': (47, 6476290, '033dccd09ed268eeb2ce9570a37d52f66d4eb5da18b68f2f44a89bd01054c4f2'),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def legacy(value):
    """Independent field enumeration, including all constructor-derived fields."""
    if type(value) is Fraction:
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if isinstance(value, np.ndarray):
        return {'dtype': str(value.dtype), 'shape': list(value.shape), 'values': value.tolist()}
    if is_dataclass(value):
        return {'type': type(value).__module__ + '.' + type(value).__qualname__,
                'fields': {f.name: legacy(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, Mapping):
        return {k: legacy(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [legacy(v) for v in value]
    return value


def run(args):
    output = args.output
    output.mkdir(parents=False, exist_ok=False)
    start = time.monotonic()
    result = {'status': 'started', 'scope': 'complete_saved_observations_only',
              'soft_budget_seconds': 60, 'hard_budget_seconds': 90,
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'inputs': [], 'records': [], 'checks': 0, 'live_physics_calls': 0,
              'material_qualified': False, 'resume_authorized': False,
              'full_run_validated': False, 'source_assets_verified': False}

    def check(ok, reason):
        if not ok:
            raise ValueError(reason)
        result['checks'] += 1

    def forbidden(*unused, **kwargs):
        result['live_physics_calls'] += 1
        raise AssertionError('passive_saved_exercise_reached_live_physics')

    def alarm(*unused):
        raise TimeoutError('saved_exercise_hard_budget')

    previous = signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, 90)
    try:
        with ExitStack() as stack:
            from sludge_sandbox.exact_source_column import ExactSourceColumn
            from sludge_sandbox.source_wet_storage import SourceWetStorage
            from sludge_sandbox.source_wet_column import SourceWetColumn
            from sludge_sandbox.programmed_source_wet_column import ProgrammedSourceWetColumn
            from sludge_sandbox.rigid_storage import RigidStorage
            from sludge_sandbox.rigid_water_gas import RigidWaterGas
            from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
            from sludge_sandbox.water_properties import WaterProperties
            from sludge_sandbox.water_heos import HEOSWaterProperties
            from sludge_sandbox._heos_kernel import HEOSCandidate
            for cls in (ExactSourceColumn, SourceWetStorage, SourceWetColumn,
                        ProgrammedSourceWetColumn, RigidStorage, RigidWaterGas,
                        WaterChemicalPotential, WaterProperties, HEOSWaterProperties, HEOSCandidate):
                stack.enter_context(patch.object(cls, '__init__', forbidden))
            for cls, name in ((ExactSourceColumn, 'evaluate'), (SourceWetStorage, 'evaluate'),
                              (SourceWetStorage, 'invert'), (RigidStorage, 'evaluate_at_temperature'),
                              (WaterProperties, 'state_tp'), (HEOSWaterProperties, 'state_tp')):
                stack.enter_context(patch.object(cls, name, forbidden))
            for module, name in (
                ('sludge_sandbox.source_wet_column', 'integrate_source_column'),
                ('sludge_sandbox.exact_depletion_integration', 'integrate_exact_depletion'),
                ('sludge_sandbox.exact_integration', 'integrate_exact'),
            ):
                stack.enter_context(patch(module + '.' + name, forbidden))
            for kind, (count, byte_count, digest) in INPUTS.items():
                path = getattr(args, kind).resolve()
                raw = path.read_bytes()
                check(len(raw) == byte_count and hashlib.sha256(raw).hexdigest() == digest,
                      'frozen_input_identity:' + kind)
                data = json.loads(raw)
                check(len(data['captures']) == count, 'capture_count:' + kind)
                result['inputs'].append({'kind': kind, 'path': str(path), 'bytes': len(raw),
                                         'sha256': digest, 'capture_count': count})
                masses = tuple(data['adapter_provenance']['fixed_dry_mass_kg'])
                for index, capture in enumerate(data['captures']):
                    check(time.monotonic() - start < 60, 'saved_exercise_soft_budget')
                    result['attempt'] = {'kind': kind, 'capture_index': index}
                    original_state = capture['packed_input']
                    original_evaluation = capture['evaluation']
                    check(canonical(capture['time']) == canonical(original_evaluation['fields']['time']),
                          'outer_exact_time')
                    if kind == 'programmed':
                        operator = original_evaluation['fields']['operator_identity']
                        energy = original_state['fields']['energy_model_identity']
                        modes = None
                        role = 'legacy_programmed_observation'
                        adaptation = 'recorded_nested_identities_explicit_import_role_modes_unknown'
                    else:
                        operator, energy = capture['operator_identity'], capture['energy_identity']
                        modes = tuple(capture['interface_modes'])
                        role = capture['phase']
                        adaptation = 'recorded_outer_context'
                    context = SourceObservationContext(
                        (operator[0], operator[1], tuple(operator[2])),
                        (energy[0], tuple(energy[1]), tuple(energy[2])), masses, modes)
                    provenance = {'input_sha256': digest, 'input_path': str(path),
                                  'capture_index': str(index), 'capture_ordinal': str(capture['ordinal']),
                                  'import_context': adaptation}
                    record = import_saved_source_sample(canonical({'state': original_state,
                        'evaluation': original_evaluation, 'role': role}),
                        context=context, provenance=provenance)
                    target = output / f'{kind}-{index:03d}.json'
                    with target.open('xb') as stream:
                        stream.write(record.canonical_bytes)
                    restored = decode_source_sample(target.read_bytes(), expected_context=context)
                    restored.check()
                    check(canonical(legacy(restored.sample.state)) == canonical(original_state), 'all_state_fields')
                    check(canonical(legacy(restored.sample.evaluation)) == canonical(original_evaluation), 'all_evaluation_fields')
                    check(encode_source_sample(restored.sample, context=context, provenance=provenance)
                          == target.read_bytes(), 'canonical_reencode')
                    summary = inspect_source_observation(target)
                    check(summary['interface_modes'] == (list(modes) if modes is not None else None), 'declared_modes')
                    check(all(summary[name] is False for name in ('material_qualified', 'resume_authorized',
                          'source_assets_verified', 'full_run_validated')), 'no_qualification_upgrade')
                    check(summary['provenance'] == provenance and summary['role'] == role, 'declared_origin')
                    check(summary['cell_count'] == len(masses), 'complete_cell_count')
                    for i, row in enumerate(summary['cells']):
                        check(row['cell_index'] == i and row['fixed_dry_mass_kg'] == masses[i], 'original_cell_index_mass')
                        check(row['amounts_mol'] == original_state['fields']['amounts_mol']['values'][i]
                              and row['internal_energy_j'] == original_state['fields']['internal_energy_j']['values'][i], 'state_display')
                        point = original_evaluation['fields']['source_evaluation']['fields']['cells'][i]['fields']['inverse']['fields']['point']['fields']
                        check(row['temperature_k'] == point['fluid']['fields']['mechanical']['fields']['temperature_k']
                              and row['pressure_pa'] == point['fluid']['fields']['mechanical']['fields']['pressure_pa']
                              and row['source_ids'] == point['source_ids'], 'preserved_output_and_sources')
                    result['records'].append({'kind': kind, 'capture_index': index, 'ordinal': capture['ordinal'],
                        'record_file': target.name, 'record_sha256': restored.sha256,
                        'sample_binding': restored.sample_binding, 'bytes': target.stat().st_size,
                        'cell_count': len(masses), 'role': role, 'interface_modes': summary['interface_modes'],
                        'source_rate_type': type(restored.sample.evaluation.source_evaluation).__name__})
            check(len(result['records']) == 111, 'all_111_observations')
            result['status'] = 'passed'
    except Exception as exc:
        result['status'] = 'failed'
        result['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        result['wall_seconds'] = time.monotonic() - start
        (output / 'RESULT.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('inputs', 'records')}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('n3', 'n1', 'programmed', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    raise SystemExit(run(parser.parse_args()))
