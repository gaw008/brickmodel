"""Explicit numerical strategy declaration; validation performs no EOS calls."""
import pytest
from test_paired_event_case import paired_payload
from test_event_case import save

STRATEGY = 'guarded_liquid_endpoint_interpolation_v1'


def test_explicit_pressure_strategy_is_preserved(tmp_path):
    p = paired_payload()
    p['numerics']['pressure_policy']['strategy'] = STRATEGY
    assert save(tmp_path, p).payload['numerics']['pressure_policy']['strategy'] == STRATEGY


def test_default_case_does_not_gain_strategy(tmp_path):
    assert 'strategy' not in save(tmp_path, paired_payload()).payload['numerics']['pressure_policy']


@pytest.mark.parametrize('value', [None, True, 1, '', 'bisection', 'newton', [], {}])
def test_unknown_or_implicit_strategy_is_rejected(tmp_path, value):
    from sludge_sandbox.verification_case import CaseError
    p = paired_payload()
    p['numerics']['pressure_policy']['strategy'] = value
    with pytest.raises(CaseError):
        save(tmp_path, p)
