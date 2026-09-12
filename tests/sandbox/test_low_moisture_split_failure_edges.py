"""Independent manufactured callback/clock probes; the fixture disables water EOS."""
from types import SimpleNamespace

from test_low_moisture_split_column import case
from sludge_sandbox.controlled_vapor_column import ControlledVaporColumn
import sludge_sandbox.low_moisture_split_column as split


def test_completed_initial_decode_is_retained_when_cancel_arrives(monkeypatch):
    column, initial = case(monkeypatch)
    actual = ControlledVaporColumn.evaluate
    returned = []

    def record(self, states):
        value = actual(self, states)
        returned.append(value)
        return value

    monkeypatch.setattr(ControlledVaporColumn, 'evaluate', record)
    result = split.integrate_low_moisture_split(
        column, initial, duration_s=1 / 128, steps=1,
        cancel=lambda: bool(returned),
    )
    assert result.status == 'cancelled'
    assert result.evaluations_attempted == result.evaluations_completed == 1
    assert result.states == (initial,) and not result.ledgers
    assert result.failed_trial.last_completed_states is initial
    assert result.failed_trial.last_completed_rates is returned[0]


def test_final_identity_work_is_still_subject_to_wall_budget(monkeypatch):
    column, initial = case(monkeypatch)
    clock = [0.]
    calls = []
    original_digest = split._digest
    monkeypatch.setattr(split, 'time', SimpleNamespace(monotonic=lambda: clock[0]))

    def final_identity_work(value):
        answer = original_digest(value)
        calls.append(value)
        if len(calls) == 2:
            clock[0] = 2.
        return answer

    monkeypatch.setattr(split, '_digest', final_identity_work)
    result = split.integrate_low_moisture_split(
        column, initial, duration_s=1 / 128, steps=1,
        maximum_wall_seconds=1.,
    )
    assert len(calls) == 2
    assert result.elapsed_seconds == 2.
    assert result.status == 'resource_limit'
    assert result.states == (initial,) and not result.ledgers
