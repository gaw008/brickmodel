"""Passive source observation persistence; manufactured providers, no native EOS."""
from dataclasses import replace
from fractions import Fraction as F
import json

import pytest

from sludge_sandbox.source_observation_record import (
    SourceObservationContext, SourceObservationRecordError,
    encode_source_sample, decode_source_sample, import_saved_source_sample,
)


def test_empty_input_is_not_a_source_observation():
    with pytest.raises(SourceObservationRecordError):
        decode_source_sample(b'{}')


@pytest.fixture(scope='module')
def observations():
    from test_source_wet_column import setup
    from test_programmed_source_wet_column import setup as programmed_setup
    from test_source_liquid_column import config
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.exact_event_clock import ExactEventTime
    from sludge_sandbox.source_net_panel import SavedSourceSample
    result = {}
    for programmed in (False, True):
        with pytest.MonkeyPatch.context() as patch:
            model, states = (programmed_setup(patch, count=2, translation=F(2**80)) if programmed
                             else setup(patch, count=2))
            for liquid in (False, True):
                chosen = (replace(model, base=replace(model.base, liquid_transport=config(2))) if programmed
                          else replace(model, liquid_transport=config(2))) if liquid else model
                adapter = ExactSourceColumn(chosen)
                packed = adapter.pack(states)
                observation = adapter.evaluate(packed, ExactEventTime(F(2**80) + F(1, 17)))
                sample = SavedSourceSample(packed, observation, 'actual_manufactured_observation')
                context = SourceObservationContext(adapter.operator_identity, adapter.energy_model_identity,
                    tuple(s.solid_mass_kg[0] for s in states), tuple(adapter.interfaces))
                result[type(observation.source_evaluation).__name__] = sample, context
    return result


@pytest.fixture(autouse=True)
def no_codec_physics(monkeypatch, observations):
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    from sludge_sandbox.rigid_storage import RigidStorage
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.water_heos import HEOSWaterProperties
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    def forbidden(*args, **kwargs):
        pytest.fail('passive codec reached physics')
    for cls, name in ((ExactSourceColumn, 'evaluate'), (SourceWetStorage, 'evaluate'),
        (SourceWetStorage, 'invert'), (RigidStorage, 'evaluate_at_temperature'),
        (WaterProperties, 'state_tp'), (HEOSWaterProperties, 'state_tp'),
        (WaterChemicalPotential, 'equilibrium_at_liquid_tp')):
        monkeypatch.setattr(cls, name, forbidden)


def legacy(value):
    """Original research representation, independent of the new tagged carrier."""
    from dataclasses import fields, is_dataclass
    from collections.abc import Mapping
    import numpy as np
    if type(value) is F:
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


@pytest.mark.parametrize('kind', ['SourceColumnRates', 'LiquidSourceColumnRates',
                                  'ProgrammedSourceRates', 'ProgrammedLiquidSourceRates'])
def test_four_actual_variants_roundtrip_and_explicit_legacy_import(observations, kind):
    sample, context = observations[kind]
    original = legacy(sample)
    raw = encode_source_sample(sample, context=context, provenance={'artifact_sha256': 'a'*64})
    out = decode_source_sample(raw, expected_context=context)
    assert legacy(out.sample) == original
    assert out.canonical_bytes == raw
    assert out.context.interface_modes == ('existing_liquid',)*2
    assert len(out.sha256) == 64 and not out.material_qualified and not out.resume_authorized
    out.check()
    old = json.dumps({'state': legacy(sample.state), 'evaluation': legacy(sample.evaluation), 'role': sample.role}).encode()
    imported = import_saved_source_sample(old, context=context, provenance={'artifact_sha256': 'a'*64})
    assert imported.canonical_bytes == raw
    with pytest.raises(ValueError):
        out.sample.state.amounts_mol.setflags(write=True)
    with pytest.raises(TypeError):
        out.provenance['artifact_sha256'] = 'b'*64


def test_unknown_modes_stay_unknown_and_explicit_modes_are_checked(observations):
    sample, context = observations['SourceColumnRates']
    out = decode_source_sample(encode_source_sample(sample, context=replace(context, interface_modes=None)))
    assert out.context.interface_modes is None
    for bad in (('depleted_no_nucleation',)*2, ('existing_liquid',), (True, True)):
        with pytest.raises(SourceObservationRecordError):
            encode_source_sample(sample, context=replace(context, interface_modes=bad))


@pytest.mark.parametrize('raw', [b'{"schema":1,"schema":2}', b'NaN', b'Infinity', b'[]', b'{'])
def test_invalid_json_is_a_named_error(raw):
    with pytest.raises(SourceObservationRecordError):
        decode_source_sample(raw)


def test_foreign_context_and_post_read_mutation_are_rejected(observations):
    sample, context = observations['LiquidSourceColumnRates']
    raw = encode_source_sample(sample, context=context)
    with pytest.raises(SourceObservationRecordError, match='context'):
        decode_source_sample(raw, expected_context=replace(context, fixed_dry_mass_kg=(1., 1.)))
    out = decode_source_sample(raw)
    object.__setattr__(out.sample.evaluation.source_evaluation, 'source_ids', ('forged:source',))
    with pytest.raises(SourceObservationRecordError):
        out.check()


@pytest.mark.parametrize('field,value', [('material_qualified', True), ('total_enthalpy_j', 1.),
                                         ('qualification', 'certified'), ('fit_error', F(0))])
def test_qualifications_and_unknown_properties_cannot_be_invented(observations, field, value):
    sample, context = observations['SourceColumnRates']
    raw = sample.evaluation.source_evaluation
    cell = raw.cells[0]
    changed = replace(cell, inverse=replace(cell.inverse, point=replace(cell.inverse.point, **{field: value})))
    forged = replace(sample, evaluation=replace(sample.evaluation,
                     source_evaluation=replace(raw, cells=(changed, *raw.cells[1:]))))
    with pytest.raises(SourceObservationRecordError):
        encode_source_sample(forged, context=context)


def test_arbitrary_nested_object_and_bool_as_number_rejected(observations):
    sample, context = observations['SourceColumnRates']
    raw = sample.evaluation.source_evaluation
    for cell in (replace(raw.cells[0], inverse='not an inverse'),
                 replace(raw.cells[0], inverse=replace(raw.cells[0].inverse, iterations=True))):
        forged = replace(sample, evaluation=replace(sample.evaluation,
                         source_evaluation=replace(raw, cells=(cell, *raw.cells[1:]))))
        with pytest.raises(SourceObservationRecordError):
            encode_source_sample(forged, context=context)


@pytest.mark.parametrize('change', ['unknown_class', 'extra_field', 'fraction_bool', 'fraction_unreduced',
                                    'array_bool', 'array_dtype', 'clock_float'])
def test_legacy_rejects_untrusted_structural_changes(observations, change):
    sample, context = observations['LiquidSourceColumnRates']
    data = {'state': legacy(sample.state), 'evaluation': legacy(sample.evaluation), 'role': sample.role}
    if change == 'unknown_class':
        data['evaluation']['type'] = 'os.system'
    elif change == 'extra_field':
        data['evaluation']['fields']['resume_authorized'] = True
    elif change.startswith('fraction'):
        value = data['evaluation']['fields']['time']['fields']['seconds']
        if change == 'fraction_bool':
            value['numerator'] = True
        else:
            value['numerator'] *= 2
            value['denominator'] *= 2
    elif change == 'clock_float':
        data['evaluation']['fields']['time']['fields']['seconds'] = 1.
    elif change == 'array_bool':
        data['state']['fields']['amounts_mol']['values'][0][0] = True
    else:
        data['state']['fields']['amounts_mol']['dtype'] = 'float32'
    with pytest.raises(SourceObservationRecordError):
        import_saved_source_sample(json.dumps(data).encode(), context=context)


def test_pressure_attempt_failure_text_and_optional_ledger_survive(observations):
    from sludge_sandbox.rigid_water_gas import PressureTrialRecord
    sample, context = observations['SourceColumnRates']
    raw = sample.evaluation.source_evaluation
    cell = raw.cells[0]
    fluid = cell.inverse.point.fluid
    attempt = PressureTrialRecord(1e5, (1e4, 1e7), (None, None), 'manufactured_saved_failure',
                                  'failed', failure='')
    mechanical = replace(fluid.mechanical, pressure_trial_ledger=(attempt,))
    changed = replace(cell, inverse=replace(cell.inverse,
        point=replace(cell.inverse.point, fluid=replace(fluid, mechanical=mechanical))))
    sample = replace(sample, role='manufactured_optional_record_branch', evaluation=replace(sample.evaluation,
                     source_evaluation=replace(raw, cells=(changed, *raw.cells[1:]))))
    out = decode_source_sample(encode_source_sample(sample, context=context))
    ledger = out.sample.evaluation.source_evaluation.cells[0].inverse.point.fluid.mechanical.pressure_trial_ledger
    assert ledger == (attempt,) and ledger[0].failure == ''
    old = json.dumps({'state': legacy(sample.state), 'evaluation': legacy(sample.evaluation), 'role': sample.role}).encode()
    assert import_saved_source_sample(old, context=context).canonical_bytes == out.canonical_bytes


def test_changed_derived_gas_pressure_is_not_patched_during_restore(observations):
    sample, context = observations['SourceColumnRates']
    raw = sample.evaluation.source_evaluation
    gas = replace(raw.gas_states[0])
    object.__setattr__(gas, 'pressure_pa', gas.pressure_pa + 1.)
    sample = replace(sample, evaluation=replace(sample.evaluation,
                     source_evaluation=replace(raw, gas_states=(gas, *raw.gas_states[1:]))))
    with pytest.raises(SourceObservationRecordError, match='constructor_changed_fields'):
        encode_source_sample(sample, context=context)


def test_nonfinite_water_descriptor_and_inverse_bounds_are_rejected(observations):
    from sludge_sandbox.water_implementation import WaterImplementation
    sample, context = observations['SourceColumnRates']
    raw = sample.evaluation.source_evaluation
    cell = raw.cells[0]
    # This metadata constructor itself accepts JSON NaN; the observation codec must not.
    implementation = WaterImplementation('water_implementation_v1', 'manufactured', '1',
                                         ('manufactured:metadata',), '{"bad":NaN}')
    equilibrium = cell.phase.equilibrium
    water = replace(equilibrium.liquid.state, implementation=implementation)
    phase = replace(cell.phase, equilibrium=replace(equilibrium,
                    liquid=replace(equilibrium.liquid, state=water)))
    for changed in (replace(cell, phase=phase),
                    replace(cell, inverse=replace(cell.inverse, temperature_error_bound_k=-1.))):
        forged = replace(sample, evaluation=replace(sample.evaluation,
                         source_evaluation=replace(raw, cells=(changed, *raw.cells[1:]))))
        with pytest.raises(SourceObservationRecordError):
            encode_source_sample(forged, context=context)


def test_new_numeric_carrier_is_canonical_and_rejects_wrong_type_or_extra_fields(observations):
    from sludge_sandbox.exact_record import pack
    sample, context = observations['SourceColumnRates']
    original = encode_source_sample(sample, context=context)
    def find(v, kind):
        if type(v) is dict:
            m = v.get('mapping', {})
            if m.get('type') == kind:
                return m['fields']['mapping']
            for child in v.values():
                found = find(child, kind)
                if found is not None:
                    return found
        elif type(v) is list:
            for child in v:
                found = find(child, kind)
                if found is not None:
                    return found
        return None
    cases = [('sludge_sandbox.source_wet_storage.SourceWetInverse', 'iterations', True),
             ('sludge_sandbox.source_wet_column.SourceColumnCell', 'inverse', 'os.system'),
             ('sludge_sandbox.source_wet_storage.SourceWetPoint', 'unrecognized', 0)]
    for kind, key, value in cases:
        data = json.loads(original)
        find(data, kind)[key] = pack(value)
        with pytest.raises(SourceObservationRecordError):
            decode_source_sample(json.dumps(data).encode())
    data = json.loads(original)
    data['sample_binding'] = 'f'*64
    with pytest.raises(SourceObservationRecordError, match='binding'):
        decode_source_sample(json.dumps(data).encode())


def test_bounded_record_and_original_registry_are_unchanged(monkeypatch):
    import sludge_sandbox.source_observation_record as module
    from sludge_sandbox.exact_record import REGISTRY
    assert 'SourceExactEvaluation' not in REGISTRY
    monkeypatch.setattr(module, 'MAX_BYTES', 8)
    with pytest.raises(SourceObservationRecordError, match='bounded'):
        decode_source_sample(b' '*9)
    monkeypatch.setattr(module, 'MAX_BYTES', 10_000)
    with pytest.raises(SourceObservationRecordError, match='resource_limit'):
        decode_source_sample(('['*100 + '0' + ']'*100).encode())


def test_reference_metadata_and_nested_liquid_phase_cannot_be_relabelled(observations):
    sample, context = observations['SourceColumnRates']
    raw = sample.evaluation.source_evaluation
    cell = raw.cells[0]
    equilibrium = cell.phase.equilibrium
    original = equilibrium.liquid.state
    for water in (replace(original, phase='vapor'),
                  replace(original, reference=replace(original.reference, energy_reference='invented_reference'))):
        phase = replace(cell.phase, equilibrium=replace(equilibrium,
                        liquid=replace(equilibrium.liquid, state=water)))
        changed = replace(cell, phase=phase)
        forged = replace(sample, evaluation=replace(sample.evaluation,
                         source_evaluation=replace(raw, cells=(changed, *raw.cells[1:]))))
        with pytest.raises(SourceObservationRecordError):
            encode_source_sample(forged, context=context)


@pytest.fixture(scope='module')
def preserved_native_sample():
    """Original saved N3 callback only; no model reconstruction or new EOS."""
    from pathlib import Path
    saved = json.loads((Path(__file__).parent / 'fixtures/source-observation-v1/native-captures.json').read_bytes())
    capture = saved['captures'][0]
    def tuples(value):
        return tuple(tuples(v) for v in value) if type(value) is list else value
    context = SourceObservationContext(tuples(capture['operator_identity']), tuples(capture['energy_identity']),
        tuple(saved['adapter_provenance']['fixed_dry_mass_kg']), tuples(capture['interface_modes']))
    record = import_saved_source_sample(json.dumps({'state': capture['packed_input'],
        'evaluation': capture['evaluation'], 'role': capture['phase']}).encode(), context=context)
    return record.sample, context


@pytest.mark.parametrize('change', ['missing_internal_observation', 'swapped_same_temperature_gas',
                                   'detached_mechanical_sources', 'invented_direction_qualification'])
def test_saved_association_regressions(preserved_native_sample, change):
    sample, context = preserved_native_sample
    raw = sample.evaluation.source_evaluation
    if change == 'missing_internal_observation':
        raw = replace(raw, faces=(raw.faces[0], replace(raw.faces[1], shared_evaluation=None), *raw.faces[2:]))
    elif change == 'swapped_same_temperature_gas':
        assert raw.gas_states[0].temperature_k == raw.gas_states[1].temperature_k
        assert raw.gas_states[0].concentrations_mol_m3 != raw.gas_states[1].concentrations_mol_m3
        raw = replace(raw, gas_states=(raw.gas_states[1], raw.gas_states[0], *raw.gas_states[2:]))
    elif change == 'detached_mechanical_sources':
        cell = raw.cells[0]
        fluid = cell.inverse.point.fluid
        mechanical = replace(fluid.mechanical, source_ids=('forged:missing-original-water-sources',))
        changed = replace(cell, inverse=replace(cell.inverse,
            point=replace(cell.inverse.point, fluid=replace(fluid, mechanical=mechanical))))
        raw = replace(raw, cells=(changed, *raw.cells[1:]))
    else:
        face = raw.faces[1]
        changed = replace(face, liquid_exchange=replace(face.liquid_exchange,
                          direction_qualification='full_inverse_direction_certified'))
        raw = replace(raw, faces=(raw.faces[0], changed, *raw.faces[2:]))
    forged = replace(sample, evaluation=replace(sample.evaluation, source_evaluation=raw))
    with pytest.raises(SourceObservationRecordError):
        encode_source_sample(forged, context=context)
