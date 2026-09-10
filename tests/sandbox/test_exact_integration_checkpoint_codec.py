"""Persistent ordinary checkpoints with manufactured numerical operators, no EOS."""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json

import numpy as np
import pytest

from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_integration import integrate_exact_checkpointed
from sludge_sandbox.exact_integration_checkpoint import _digest, _same, _seal
from sludge_sandbox.exact_integration_checkpoint_codec import (
    ExactCheckpointCodecError, decode_exact_checkpoint, encode_exact_checkpoint,
)
from sludge_sandbox.integration import ConservedState, DomainExit, Rates, _Reject
from test_exact_integration import initial, policy, rates


def run(p, operator, *, continuation=None, pause=False, origin=F(), **kwargs):
    return integrate_exact_checkpointed(initial(), operator, start_s=T(origin),
        end_s=T(origin + 4 * F(p.initial_step_s)), policy=p, continuation=continuation,
        pause_after_commit=(lambda cp: True) if pause else None, **kwargs)


@pytest.fixture
def checkpoint():
    return run(policy(), lambda s, t: rates(s), pause=True).checkpoint


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def rehash(data):
    data['payload_sha256'] = hashlib.sha256(canonical(data['checkpoint'])).hexdigest()
    return canonical(data)


def test_nonstationary_rejected_prefix_roundtrip_then_continue_matches_all_callbacks():
    p = replace(policy(), initial_step_s=.025, maximum_step_s=.025,
                relative_tolerance=1e-5, amount_absolute_tolerance_mol=1e-8)
    uninterrupted, continued = [], []
    def operator(calls):
        def evaluate(state, when):
            calls.append((state, when))
            if len(calls) == 3:
                raise DomainExit('')
            return replace(rates(state), reaction_species_mol_s=np.array([
                [state.amounts_mol[0, 0], 0.], [0., 0.]]))
        return evaluate
    expected = run(p, operator(uninterrupted))
    actual_operator = operator(continued)
    first = run(p, actual_operator, pause=True)
    cp = first.checkpoint
    assert cp is not None and cp.result.rejected_trials > 0
    assert not np.array_equal(cp.problem.initial.amounts_mol, cp.result.states[-1].amounts_mol)
    calls_before = len(continued)
    raw = encode_exact_checkpoint(cp)
    restored = decode_exact_checkpoint(raw)
    restored.check()
    assert len(continued) == calls_before
    assert _same(restored, cp) and restored.binding_sha256 == cp.binding_sha256
    assert restored.observations[2].failure_kind == 'DomainExit'
    assert restored.observations[2].failure_message == ''
    assert encode_exact_checkpoint(restored) == raw
    final = run(p, actual_operator, continuation=restored)
    assert expected.result.status == final.result.status == 'completed'
    assert _same(replace(final.result, elapsed_seconds=0.),
                 replace(expected.result, elapsed_seconds=0.))
    assert _same(tuple(continued), tuple(uninterrupted))
    assert _same(final.observations, expected.observations)
    assert final.result.elapsed_seconds >= cp.elapsed_seconds


def test_full_exact_origin_mapping_order_bits_and_immutable_arrays():
    p = policy()
    origin = F(10**30, 7)
    def op(state, when):
        base = rates(state)
        face = base.face_species_mol_s.copy()
        face[0, 1] = -0.0
        return replace(base, face_species_mol_s=face)
    cp = run(p, op, pause=True, origin=origin).checkpoint
    restored = decode_exact_checkpoint(encode_exact_checkpoint(cp))
    assert restored.problem.start_s.seconds == origin
    assert restored.next_step_s == cp.next_step_s
    assert restored.result.elapsed_seconds.hex() == cp.elapsed_seconds.hex()
    for a, b in zip(cp.observations, restored.observations):
        assert tuple(a.rates.cell_power_components_w) == tuple(b.rates.cell_power_components_w)
        assert a.rates.face_species_mol_s.tobytes() == b.rates.face_species_mol_s.tobytes()
        with pytest.raises(ValueError):
            b.state.amounts_mol.setflags(write=True)
    assert np.signbit(restored.observations[0].rates.face_species_mol_s[0, 1])


def test_original_step_and_wall_budget_are_preserved_after_persistence():
    p = replace(policy(), maximum_steps=1)
    cp = run(p, lambda s, t: rates(s), pause=True).checkpoint
    restored = decode_exact_checkpoint(encode_exact_checkpoint(cp))
    calls = []
    out = run(p, lambda s, t: calls.append(t) or rates(s), continuation=restored)
    assert out.result.reason == 'accepted_step_limit' and calls == []
    assert out.result.evaluations == cp.result.evaluations
    p = policy()
    cp = run(p, lambda s, t: rates(s), pause=True).checkpoint
    out = run(p, lambda s, t: calls.append(t) or rates(s),
        continuation=decode_exact_checkpoint(encode_exact_checkpoint(cp)),
        admission_elapsed_seconds=float(p.maximum_wall_seconds))
    assert out.result.reason == 'wall_time_limit' and calls == []
    assert out.result.elapsed_seconds >= cp.elapsed_seconds + p.maximum_wall_seconds


@pytest.mark.parametrize('field', ['next_step_s', 'cumulative_n', 'cumulative_u',
                                  'cumulative_stretch', 'component_schema'])
def test_resealed_numeric_tampering_is_rejected_by_passive_replay(checkpoint, field):
    if field == 'next_step_s':
        changed = checkpoint.next_step_s / 2
    elif field == 'component_schema':
        changed = tuple(reversed(checkpoint.component_schema))
    else:
        old = getattr(checkpoint, field)
        changed = (old[0] + F(1, 10**18), *old[1:])
    with pytest.raises(ExactCheckpointCodecError):
        encode_exact_checkpoint(_seal(replace(checkpoint, **{field: changed})))


@pytest.mark.parametrize('mutation', ['unknown_class', 'missing', 'extra', 'bool_counter',
    'float_counter', 'fraction_bool', 'fraction_unreduced', 'array_shape', 'array_nonfinite',
    'array_truncated', 'mapping_duplicate', 'scope', 'version', 'binding'])
def test_malformed_fields_are_rejected_even_with_rehashed_payload(checkpoint, mutation):
    data = json.loads(encode_exact_checkpoint(checkpoint))
    body = data['checkpoint']['fields']
    result = body['result']['fields']
    rates_body = body['observations']['tuple'][0]['fields']['rates']['fields']
    if mutation == 'unknown_class':
        body['problem']['record'] = 'os.system'
    elif mutation == 'missing':
        del body['next_step_s']
    elif mutation == 'extra':
        body['unregistered'] = None
    elif mutation == 'bool_counter':
        result['evaluations'] = True
    elif mutation == 'float_counter':
        result['evaluations'] = {'float_hex': float(checkpoint.result.evaluations).hex()}
    elif mutation == 'fraction_bool':
        body['next_step_s'] = {'fraction': [True, 2]}
    elif mutation == 'fraction_unreduced':
        body['next_step_s'] = {'fraction': [2, 4]}
    elif mutation.startswith('array_'):
        array = rates_body['face_energy_w']['array']
        if mutation == 'array_shape':
            array['shape'] = [10**12]
        elif mutation == 'array_nonfinite':
            array['data_hex'] = np.full(3, np.nan, dtype='<f8').tobytes().hex()
        else:
            array['data_hex'] = array['data_hex'][:-2]
    elif mutation == 'mapping_duplicate':
        pairs = rates_body['cell_power_components_w']['mapping']
        pairs.append(pairs[0])
    elif mutation == 'scope':
        data['source_resume_authorized'] = True
    elif mutation == 'version':
        data['schema'] = 'exact_integration_checkpoint_v999'
    else:
        body['binding_sha256'] = '0' * 64
    with pytest.raises(ExactCheckpointCodecError):
        decode_exact_checkpoint(rehash(data))


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'NaN', b'Infinity', b'1.0',
    b'{', b'[]', b'"\\ud800"', b'[' * 1000 + b']' * 1000, b'1' * 5000])
def test_invalid_json_is_bounded_and_normalized(raw):
    with pytest.raises(ExactCheckpointCodecError):
        decode_exact_checkpoint(raw)


def test_bytes_only_truncation_and_wire_integrity(checkpoint):
    raw = encode_exact_checkpoint(checkpoint)
    for wrong in (raw.decode(), bytearray(raw), raw[:-1]):
        with pytest.raises(ExactCheckpointCodecError):
            decode_exact_checkpoint(wrong)
    data = json.loads(raw)
    data['checkpoint']['fields']['result']['fields']['evaluations'] += 1
    with pytest.raises(ExactCheckpointCodecError, match='payload'):
        decode_exact_checkpoint(canonical(data))


def test_non_boundary_evidence_is_not_a_persistable_checkpoint(checkpoint):
    wrong = _seal(replace(checkpoint, result=replace(checkpoint.result, status='running', reason=None)))
    with pytest.raises(ExactCheckpointCodecError):
        encode_exact_checkpoint(wrong)


def test_rehashed_wire_next_step_is_still_replayed(checkpoint):
    data = json.loads(encode_exact_checkpoint(checkpoint))
    changed = replace(checkpoint, next_step_s=checkpoint.next_step_s / 2)
    body = data['checkpoint']['fields']
    body['next_step_s'] = {'fraction': [changed.next_step_s.numerator, changed.next_step_s.denominator]}
    body['binding_sha256'] = _digest(changed)
    with pytest.raises(ExactCheckpointCodecError, match='replay_numeric_state_changed'):
        decode_exact_checkpoint(rehash(data))


def test_constructor_derived_component_residual_cannot_be_forged(checkpoint):
    data = json.loads(encode_exact_checkpoint(checkpoint))
    body = data['checkpoint']['fields']['observations']['tuple'][0]['fields']['rates']['fields']
    body['component_sum_residual_w']['tuple'][0] = {'fraction': [1, 1]}
    with pytest.raises(ExactCheckpointCodecError, match='constructor_changed_fields:Rates'):
        decode_exact_checkpoint(rehash(data))


def test_mapping_order_is_not_normalized_on_decode(checkpoint):
    data = json.loads(encode_exact_checkpoint(checkpoint))
    body = data['checkpoint']['fields']['observations']['tuple'][0]['fields']['rates']['fields']
    body['cell_power_components_w']['mapping'].reverse()
    with pytest.raises(ExactCheckpointCodecError, match='constructor_changed_fields:Rates'):
        decode_exact_checkpoint(rehash(data))


def test_handled_internal_rejection_is_data_not_an_instantiated_exception():
    calls = []
    def operator(state, when):
        calls.append(when)
        if len(calls) == 3:
            raise _Reject('manufactured numerical rejection')
        return rates(state)
    cp = run(policy(), operator, pause=True).checkpoint
    assert cp.result.rejected_trials == 1
    restored = decode_exact_checkpoint(encode_exact_checkpoint(cp))
    assert restored.observations[2].failure_kind == '_Reject'
    assert restored.observations[2].failure_message == 'manufactured numerical rejection'
    assert len(calls) == cp.result.evaluations


def test_policy_integer_representation_and_no_optional_mechanics_roundtrip():
    p = replace(policy(), maximum_wall_seconds=30, stretch_absolute_tolerance=None, stretch_scale=None)
    state = ConservedState([[1., 0.]], [-0.0], energy_model_identity=('opaque', ('identity',)))
    cp = integrate_exact_checkpointed(state, lambda s, t: Rates(
        np.zeros((2, 2)), np.zeros(2), np.zeros((1, 2)), np.zeros(1)),
        start_s=T(F()), end_s=T(4 * F(p.initial_step_s)), policy=p,
        pause_after_commit=lambda cp: True).checkpoint
    restored = decode_exact_checkpoint(encode_exact_checkpoint(cp))
    assert type(restored.problem.policy.maximum_wall_seconds) is int
    assert restored.cumulative_stretch is None and restored.component_schema is None
    assert restored.problem.initial.energy_model_identity == state.energy_model_identity
    assert np.signbit(restored.problem.initial.internal_energy_j[0])


@pytest.mark.parametrize('limit', ['MAX_BYTES', 'MAX_NODES', 'MAX_DEPTH', 'MAX_ARRAY_VALUES',
                                   'MAX_OBSERVATIONS', 'MAX_ACCEPTED_STEPS'])
def test_declared_resource_caps_reject_before_passive_replay(checkpoint, monkeypatch, limit):
    from sludge_sandbox import exact_integration_checkpoint_codec as codec
    raw = encode_exact_checkpoint(checkpoint)
    monkeypatch.setattr(codec, limit, 0)
    def forbidden(_checkpoint):
        pytest.fail('resource rejection must happen before replay')
    monkeypatch.setattr(type(checkpoint), 'check', forbidden)
    with pytest.raises(ExactCheckpointCodecError):
        decode_exact_checkpoint(raw)
    with pytest.raises(ExactCheckpointCodecError):
        encode_exact_checkpoint(checkpoint)


def test_float64_subnormal_bits_survive_observation_persistence():
    def operator(state, when):
        base = rates(state)
        face = base.face_species_mol_s.copy()
        face[0, 1] = np.nextafter(0., 1.)
        return replace(base, face_species_mol_s=face)
    cp = run(policy(), operator, pause=True).checkpoint
    restored = decode_exact_checkpoint(encode_exact_checkpoint(cp))
    assert restored.observations[0].rates.face_species_mol_s.tobytes() == (
        cp.observations[0].rates.face_species_mol_s.tobytes())


def test_cycle_and_unregistered_object_are_rejected_without_physics(checkpoint):
    from sludge_sandbox.exact_integration_checkpoint import ExactIntegrationProblem
    problem = ExactIntegrationProblem(checkpoint.problem.initial, checkpoint.problem.start_s,
        checkpoint.problem.end_s, checkpoint.problem.policy, checkpoint.problem.breakpoints_s)
    wrong = replace(checkpoint, problem=problem)
    object.__setattr__(problem, 'initial', problem)
    with pytest.raises(ExactCheckpointCodecError):
        encode_exact_checkpoint(wrong)
    with pytest.raises(ExactCheckpointCodecError):
        encode_exact_checkpoint(object())


@pytest.mark.parametrize('quantity', ['amount', 'energy', 'stretch'])
def test_persisted_original_roundoff_debt_rejects_the_second_step(quantity):
    # Original integrator counterexample: each step loses 1 at 2**53, while the
    # unchanged original absolute budget is 1.5. A reset would admit both steps.
    p = replace(policy(), initial_step_s=1., maximum_step_s=1., minimum_step_s=.5,
        amount_absolute_tolerance_mol=1.5, energy_absolute_tolerance_j=1.5,
        stretch_absolute_tolerance=1.5)
    state = ConservedState([[float(2**53) if quantity == 'amount' else 1.]],
        [float(2**53) if quantity == 'energy' else 0.],
        mechanical_stretches=[float(2**53), 1.] if quantity == 'stretch' else None)
    def operator(s, t):
        return Rates(np.zeros((2, 1)), np.zeros(2), np.array([[float(quantity == 'amount')]]),
            np.array([float(quantity == 'energy')]),
            mechanical_rates_per_s=np.array([1., 0.]) if quantity == 'stretch' else None)
    kwargs = dict(start_s=T(F()), end_s=T(F(3)), policy=p)
    baseline = integrate_exact_checkpointed(state, operator, **kwargs)
    partial = integrate_exact_checkpointed(state, operator, **kwargs, pause_after_commit=lambda cp: True)
    restored = decode_exact_checkpoint(encode_exact_checkpoint(partial.checkpoint))
    final = integrate_exact_checkpointed(state, operator, **kwargs, continuation=restored)
    assert final.result.reason == baseline.result.reason == 'cumulative_' + quantity + '_roundoff'
    assert _same(replace(final.result, elapsed_seconds=0.), replace(baseline.result, elapsed_seconds=0.))


def test_persisted_absolute_component_residual_budget_is_not_reset():
    p = replace(policy(), initial_step_s=.25, maximum_step_s=.25, minimum_step_s=.125,
                energy_absolute_tolerance_j=1e-17)
    state = ConservedState([[1.]], [0.])
    def operator(s, t):
        return Rates(np.zeros((2, 1)), np.zeros(2), np.zeros((1, 1)), np.array([.5]),
            {'elastic': np.array([.1]), 'body': np.array([.4])})
    kwargs = dict(start_s=T(F()), end_s=T(F(1)), policy=p)
    cp = integrate_exact_checkpointed(state, operator, **kwargs, pause_after_commit=lambda cp: True).checkpoint
    delta = abs(F(.125) - F(.025) - F(.1))
    restored = decode_exact_checkpoint(encode_exact_checkpoint(cp))
    assert restored.cumulative_components == (delta,)
    assert delta <= F(p.energy_absolute_tolerance_j) < 2 * delta
    final = integrate_exact_checkpointed(state, operator, **kwargs, continuation=restored)
    assert final.result.reason == 'cumulative_component_sum_roundoff'
