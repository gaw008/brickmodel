"""Keep statuses actually returned by the source runtime as failed evidence."""
from fractions import Fraction
from dataclasses import replace
import pytest

from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.integration import IntegrationError
from sludge_sandbox.source_observation_record import SourceObservationContext
from sludge_sandbox.source_study_record import encode_source_study, decode_source_study
from sludge_sandbox.source_study_schema import SourceStudyFailure


def context(adapter):
    return SourceObservationContext(adapter.operator_identity, adapter.energy_model_identity,
        tuple(s.dry_mass_kg for s in adapter.column.storages), adapter.interfaces)


def test_runtime_unsupported_trial_remains_exportable(monkeypatch):
    from test_source_prefix_trial import fixture, POLICY
    from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
    adapter, initial = fixture(monkeypatch)
    # Unsupported initial liquid inventory is checked before any model callback.
    amounts = initial.amounts_mol.copy()
    amounts[0, 0] = 0.
    initial = replace(initial, amounts_mol=amounts)
    monkeypatch.setattr(ExactSourceColumn, 'evaluate',
        lambda *a, **k: pytest.fail('unsupported state evaluated physics'))
    trial = evaluate_source_prefix_trial(adapter, initial, start=ExactEventTime(Fraction()),
        end=ExactEventTime(Fraction(1, 16384)), integration_policy=POLICY, maximum_callbacks=16)
    assert trial.status == 'unsupported' and not trial.captures
    trial.check()
    saved = decode_source_study(encode_source_study({'seed': trial}, contexts=(context(adapter),)))
    assert saved.roots['seed'].status == 'unsupported'
    assert saved.audit['checks']['preserved_failed_trials'] == 1


def test_runtime_numerical_failure_candidate_remains_exportable(monkeypatch):
    from test_source_dry_transition import prepare
    from sludge_sandbox.source_dry_transition import execute_source_dry_candidate
    refinement, end = prepare(monkeypatch)
    seed = refinement.approach.proposal.original_trial
    calls = []

    def fail_first_dry(adapter, state, at):
        assert adapter.interfaces == ('depleted_no_nucleation',)
        calls.append(at)
        raise IntegrationError('manufactured first dry callback failure')

    monkeypatch.setattr(ExactSourceColumn, 'evaluate', fail_first_dry)
    candidate = execute_source_dry_candidate(seed,
        event_policy=refinement.approach.proposal.event_policy, end=end, maximum_callbacks=24)
    assert candidate.status == candidate.reference.status == 'numerical_failure'
    assert len(calls) == len(candidate.captures) == 1
    candidate.check()
    failure = SourceStudyFailure('IntegrationError', candidate.reason, 'dry_candidate',
                                 {'candidate': candidate})
    record = decode_source_study(encode_source_study({'failure': failure},
        contexts=(context(seed.adapter), context(candidate.terminal.dry_adapter))))
    assert record.roots['failure'].records['candidate'].status == 'numerical_failure'
