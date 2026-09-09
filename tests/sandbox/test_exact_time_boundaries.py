"""Exact numerical times cannot silently enter legacy float consumers."""
from fractions import Fraction

import pytest

from sludge_sandbox.boundary_program import BoundaryProgramError
from sludge_sandbox.checkpoint import CheckpointError, _ledger
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.exact_integration import ExactStepLedger
from sludge_sandbox.integration import ConservedState, IntegrationError, integrate
from sludge_sandbox.verification_case import encode
from test_exact_clock import scalar
from test_exact_integration import policy


def test_legacy_integrator_and_program_refuse_exact_query_times():
    start = ExactEventTime(Fraction())
    end = ExactEventTime(Fraction(1))
    calls = []
    with pytest.raises(IntegrationError, match="invalid_start"):
        integrate(ConservedState([[1.]], [300.]),
                  lambda state, time: calls.append(time),
                  start_s=start, end_s=end, policy=policy())
    assert calls == []
    with pytest.raises(BoundaryProgramError, match="invalid_evaluation_time"):
        scalar().at(start)


def test_legacy_checkpoint_refuses_serialized_exact_ledger_times():
    start = ExactEventTime(Fraction(10**12))
    end = start.shifted(Fraction(1, 10**10))
    ledger = ExactStepLedger(start, end, [[0.], [0.]], [0., 0.], [[0.]], [0.])
    assert start.display().seconds_binary64 == end.display().seconds_binary64
    with pytest.raises(CheckpointError, match="checkpoint_invalid_ledger_time"):
        _ledger(encode(ledger))
