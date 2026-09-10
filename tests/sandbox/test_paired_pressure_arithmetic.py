"""Pure interval extraction and full legacy certificate golden regression."""
from dataclasses import asdict, replace
from fractions import Fraction as F
import hashlib
import json

import pytest

from test_paired_pressure import fixture, certify, endpoints


def legacy_cases():
    a, b, shared = fixture()
    dry_a, dry_b = replace(a, liquid_mol=F()), replace(b, liquid_mol=F())
    cases = [
        ('wet', a, b, shared, {}),
        ('reversed_wet', b, a, shared, {}),
        ('identical_wet', a, a, shared, {}),
        ('identical_dry', dry_a, dry_a, shared, {}),
        ('dry_difference', dry_a, dry_b, shared, {}),
        ('wet_dry', a, dry_b, shared, {}),
        ('dry_wet', dry_a, b, shared, {}),
        ('independent_errors', replace(a, independent_volume_error_m3=F(1,1000)),
         replace(b, independent_volume_error_m3=F(2,1000)), shared, {}),
        ('endpoint_errors', a, b, shared,
         {'liquid_a': endpoints(a, b.root_interval_pa, F(1,100)),
          'liquid_b': endpoints(b, b.root_interval_pa, F(3,100))}),
        ('distinct_intervals', replace(a, root_interval_pa=(F(3,4), F(5,2))), b, shared, {}),
        ('two_solids', replace(a, solid_mol=(F(1,2),F(1,3))),
         replace(b, solid_mol=(F(1,2)+F(1,10**8),F(1,3)-F(1,10**7))),
         replace(shared, species=('first','second'), solid_volume_m3_mol=(F(1),F(2)),
                 solid_error_m3_mol=(F(1,10),F(1,20))), {}),
        ('source_error', replace(a, source_identity='b'*64), b, shared, {}),
        ('temperature_error', replace(a, temperature_k=F(20)), b, shared, {}),
        ('geometry_error', replace(a, bulk_volume_m3=F(11)), b, shared, {}),
        ('missing_liquid', a, b, shared, {'liquid_a':None}),
        ('wrong_pivot', a, b, shared,
         {'liquid_a':endpoints(a,(F(3,2),F(3,2)))}),
        ('bool_constant', a, b, shared, {'gas_constant_j_mol_k':True}),
        ('underflow', dry_a, replace(dry_a, gas_mol=F(1)+F(1,10**400)), shared, {}),
    ]
    return cases


def encoded(value):
    if type(value) is F:
        return {'fraction': [value.numerator, value.denominator]}
    if type(value) is float:
        return {'float_hex': value.hex()}
    if type(value) is bytes:
        return {'bytes_hex': value.hex()}
    if type(value) is dict:
        return {key: encoded(v) for key, v in value.items()}
    if type(value) in (tuple, list):
        return [encoded(v) for v in value]
    return value


def legacy_capture():
    results = {}
    for name, a, b, shared, kwargs in legacy_cases():
        try:
            certificate = certify(a, b, shared, **kwargs)
        except ValueError as exc:
            outcome = {'error_type': type(exc).__module__+'.'+type(exc).__qualname__, 'error': str(exc)}
        else:
            outcome = {'all_fields': asdict(certificate), 'public_record': certificate.to_record()}
        results[name] = encoded(outcome)
    return results


# Filled from the actual pre-extraction capture at HEAD fe9d684, before edits.
LEGACY_SHA256 = '2f72372a45e054d9271a653c940f87cf1fd002983e71db7febc15f98053c3c27'


def test_all_legacy_fields_input_bytes_and_qualifications_are_unchanged():
    data = json.dumps(legacy_capture(), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    assert hashlib.sha256(data).hexdigest() == LEGACY_SHA256


def test_pure_interval_arithmetic_encloses_signed_samples():
    from sludge_sandbox.rational_intervals import (
        interval_difference, interval_sum, interval_divide_positive, residual_to_root_bound,
    )
    left, right = (F(-7,3), F(5,4)), (F(2,7), F(9,5))
    difference = interval_difference(left, right)
    numerator = interval_sum((difference, (F(-1,9), F(3,8))))
    result = interval_divide_positive(numerator, (F(1,11), F(13,6)))
    for i in range(9):
        a = left[0] + F(i,8)*(left[1]-left[0])
        for j in range(9):
            b = right[0] + F(j,8)*(right[1]-right[0])
            for k in range(9):
                extra = F(-1,9) + F(k,8)*(F(3,8)+F(1,9))
                divisor = F(1,11) + F(k,8)*(F(13,6)-F(1,11))
                value = (a-b+extra)/divisor
                assert result[0] <= value <= result[1]
    assert result[0] < 0 < result[1]
    bound = residual_to_root_bound(numerator, F(1,11))
    # Independent linear residual F(x)=r-k*x has root r/k.
    for r in (numerator[0], F(), numerator[1]):
        for k in (F(1,11), F(2,3), F(7)):
            assert abs(r/k) <= bound
    assert type(bound) is F
    assert interval_sum(()) == (F(), F())


@pytest.mark.parametrize('bad', [(F(2),F(1)), [F(1),F(2)], (True,F(2)), (F(1),2.),
                                (F(1),), 'interval'])
def test_interval_helpers_reject_unordered_or_nonexact_bounds(bad):
    from sludge_sandbox.rational_intervals import interval_sum, RationalIntervalError
    with pytest.raises(RationalIntervalError):
        interval_sum((bad,))


@pytest.mark.parametrize('denominator', [(F(),F(1)), (F(-1),F(2)), (F(-2),F(-1)),
                                        (F(2),F(1)), (F(1),True)])
def test_interval_division_requires_strict_positive_exact_denominator(denominator):
    from sludge_sandbox.rational_intervals import interval_divide_positive, RationalIntervalError
    with pytest.raises(RationalIntervalError):
        interval_divide_positive((F(-1),F(1)), denominator)


@pytest.mark.parametrize('compliance', [F(), F(-1), True, 1., None])
def test_residual_bound_requires_strict_positive_exact_compliance(compliance):
    from sludge_sandbox.rational_intervals import residual_to_root_bound, RationalIntervalError
    with pytest.raises(RationalIntervalError):
        residual_to_root_bound((F(-1), F(1)), compliance)
