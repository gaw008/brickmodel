"""Avoid duplicate passive decoding without removing source/schema validation."""
from dataclasses import replace

import pytest

from test_source_observation_record import observations, no_codec_physics, legacy
from sludge_sandbox.source_observation_record import (
    SourceObservationRecordError, create_source_sample_record, encode_source_sample,
)


@pytest.mark.parametrize('kind', ['SourceColumnRates', 'LiquidSourceColumnRates',
                                  'ProgrammedSourceRates', 'ProgrammedLiquidSourceRates'])
def test_record_creation_retains_complete_canonical_bytes_and_readonly_snapshot(observations, kind):
    sample, context = observations[kind]
    provenance = {'artifact_sha256': 'a'*64}
    expected = encode_source_sample(sample, context=context, provenance=provenance)
    record = create_source_sample_record(sample, context=context, provenance=provenance)
    assert record.canonical_bytes == expected
    assert legacy(record.sample) == legacy(sample)
    assert record.context == context
    assert not record.material_qualified and not record.resume_authorized
    provenance['artifact_sha256'] = 'b'*64
    assert record.provenance['artifact_sha256'] == 'a'*64
    with pytest.raises(ValueError):
        record.sample.state.amounts_mol.setflags(write=True)
    with pytest.raises(TypeError):
        record.provenance['artifact_sha256'] = 'c'*64


def test_record_creation_still_rejects_wrong_source_context_and_provenance(observations):
    sample, context = observations['SourceColumnRates']
    for bad in (replace(context, operator_identity='changed'),
                replace(context, interface_modes=('depleted_no_nucleation',)*2)):
        with pytest.raises(SourceObservationRecordError):
            create_source_sample_record(sample, context=bad)
    with pytest.raises(SourceObservationRecordError):
        create_source_sample_record(sample, context=context, provenance={'artifact_sha256': 3})


def test_whole_study_sample_reuses_the_encoder_validated_record(observations, monkeypatch):
    import sludge_sandbox.source_observation_record as module
    from sludge_sandbox.source_study_audit import _sample_record
    sample, context = observations['SourceColumnRates']
    expected = encode_source_sample(sample, context=context)
    decode, calls = module.decode_source_sample, []
    def counted(raw, **kwargs):
        calls.append(raw)
        return decode(raw, **kwargs)
    monkeypatch.setattr(module, 'decode_source_sample', counted)
    record = _sample_record(sample.state, sample.evaluation, sample.role, (context,), context.interface_modes)
    assert record.canonical_bytes == expected
    assert calls == [expected]  # Measured duplicate decoding must not return.
