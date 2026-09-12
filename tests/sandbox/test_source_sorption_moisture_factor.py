"""Actual factor adapter with manufactured m/q curves; no file reads or EOS.

The imported fixture keeps the exact storage/wet classes but supplies explicit
manufactured source and fluid seams. Only this adapter's file-backed _check is
patched here; its factor and the storage identity checks execute normally.
"""
from fractions import Fraction as F
import math

import pytest

from test_arlabosse_rigid_sorption import fixture
from sludge_sandbox.arlabosse_rigid_sorption import ArlabosseSorptionStorage
from sludge_sandbox.arlabosse_wet_thermo import _Linear, T_REF
from sludge_sandbox.sorption_moisture_face import CondensedWaterPoint
from sludge_sandbox.source_sorption_moisture import ADAPTER_ID, MakelaMoistureTransport


@pytest.fixture
def context(fixture, monkeypatch):
    config = object.__new__(MakelaMoistureTransport)
    monkeypatch.setattr(MakelaMoistureTransport, '_check', lambda self: None)
    yield fixture, config
    # Factor calculation may check source identities; it never evaluates fluid U.
    assert fixture.controls.callbacks == 0


def storage_with_curves(context, m, q):
    fixture, _ = context
    object.__setattr__(fixture.wet, '_m', m)
    object.__setattr__(fixture.wet, '_q', q)
    # Rebind the deliberately new manufactured curves instead of bypassing the
    # production guard that rejects changes to an already bound storage.
    return ArlabosseSorptionStorage(fixture.base, fixture.wet, (90000., 110000.))


def point(storage, t, w):
    return CondensedWaterPoint(t, w, F(100000), F(-200000), F(-100000),
        F(storage.wet._mass), 'manufactured:factor_reference', ('manufactured:factor_input',),
        'manufactured_test_fixture')


def distinct_curves():
    # Independent known slopes: m=80 then160 at W=.5;
    # q=-16 then-120 at W=.625. All coordinates/values are binary exact.
    return (_Linear((.3125, .5, .75), (-100., -85., -45.)),
            _Linear((.3125, .625, .75), (100., 95., 80.)))


def test_secant_crosses_distinct_m_and_q_knots(context):
    storage = storage_with_curves(context, *distinct_curves())
    left, right = point(storage, F(330), F(3, 8)), point(storage, F(350), F(11, 16))
    result = context[1].factor(storage, left, right)
    # Across this interval: Delta m=40, Delta q=-23/2, Delta W=5/16.
    # Hence independent average slopes are 128 and -184/5.
    ratio, mass = F(340)/F(T_REF), F(storage.wet._mass)
    expected = mass*(ratio*128+(1-ratio)*F(184, 5))
    assert result.gamma_j_mol == expected
    assert result.gamma_j_mol != mass*(ratio*80+(1-ratio)*16)
    assert result.gamma_j_mol != mass*(ratio*160+(1-ratio)*120)
    assert result.temperature_k == 340 and result.moisture_interval == (F(3, 8), F(11, 16))
    assert result.method == 'declared_secant'
    assert ADAPTER_ID in result.source_ids
    assert context[1].factor(storage, right, left) == result


@pytest.mark.parametrize('w,m_slope,q_slope', [
    (F(1, 2), F(120), F(-16)),     # m-only knot: average the two m sides.
    (F(5, 8), F(160), F(-68)),     # q-only knot: reuse m slope on both sides.
    (F(7, 16), F(80), F(-16)),     # Within a single piece.
    (F(5, 16), F(80), F(-16)),     # Left endpoint: one side only.
    (F(3, 4), F(160), F(-120)),    # Right endpoint: one side only.
])
def test_same_W_uses_positive_one_sided_or_symmetric_mean(context, w, m_slope, q_slope):
    storage = storage_with_curves(context, *distinct_curves())
    left, right = point(storage, F(330), w), point(storage, F(350), w)
    result = context[1].factor(storage, left, right)
    ratio = F(340)/F(T_REF)
    assert result.gamma_j_mol == F(storage.wet._mass)*(ratio*m_slope-(1-ratio)*q_slope)
    assert result.method == 'declared_same_W_limit' and result.moisture_interval == (w, w)


def test_common_knot_pairs_matching_sides_before_averaging(context):
    m, _ = distinct_curves()
    q = _Linear((.3125, .5, .75), (100., 94., 70.))  # q slopes -32 and -96.
    storage = storage_with_curves(context, m, q)
    same = point(storage, F(340), F(1, 2))
    result = context[1].factor(storage, same, same)
    ratio = F(340)/F(T_REF)
    assert result.gamma_j_mol == F(storage.wet._mass)*(ratio*120+(1-ratio)*64)


@pytest.mark.parametrize('bad_side,bad_slope', [('left', F(0)), ('left', F(-16)),
                                             ('right', F(0)), ('right', F(-16))])
def test_one_nonpositive_side_rejected_even_when_average_positive(context, bad_side, bad_slope):
    slopes = (bad_slope, F(128)) if bad_side == 'left' else (F(128), bad_slope)
    middle = F(-100)+slopes[0]*F(3, 16)
    end = middle+slopes[1]*F(1, 4)
    m = _Linear((.3125, .5, .75), (-100., float(middle), float(end)))
    q = _Linear((.3125, .75), (2000000., 2000000.))
    storage = storage_with_curves(context, m, q)
    same = point(storage, F(T_REF), F(1, 2))
    assert sum(slopes)/2 > 0  # Checking only the final mean would incorrectly pass.
    with pytest.raises(ValueError, match='positive_one_sided_moisture_factor'):
        context[1].factor(storage, same, same)


@pytest.mark.parametrize('middle_q_slope', [F(700), F(800)])
def test_positive_global_secant_cannot_hide_nonpositive_interior_piece(context, middle_q_slope):
    # m has no interior knots; q alone introduces a middle zero/negative Gamma.
    # Tface/Tref=7/8, dm/dW=100, dq/dW=700 gives exactly zero Gamma there.
    m = _Linear((.3125, .75), (-100., -56.25))
    after_middle = F(2000000)+middle_q_slope*F(1, 8)
    q = _Linear((.3125, .4375, .5625, .75),
                (2000000., 2000000., float(after_middle), float(after_middle)))
    storage = storage_with_curves(context, m, q)
    temperature = F(T_REF)*F(7, 8)
    left, right = point(storage, temperature, F(3, 8)), point(storage, temperature, F(11, 16))
    global_slope = F(7, 8)*100-F(1, 8)*middle_q_slope*F(2, 5)
    assert global_slope > 0
    assert F(7, 8)*100-F(1, 8)*middle_q_slope <= 0
    with pytest.raises(ValueError, match='positive_piecewise_moisture_factor'):
        context[1].factor(storage, left, right)


def test_adjacent_float_temperatures_keep_exact_half_ulp_face_temperature(context):
    m = _Linear((.3125, .75), (-100., -44.))  # Constant slope 128.
    q = _Linear((.3125, .75), (2000000., 2000000.))
    storage = storage_with_curves(context, m, q)
    tl, tr = F(330.), F(math.nextafter(330., math.inf))
    left, right = point(storage, tl, F(3, 8)), point(storage, tr, F(11, 16))
    result = context[1].factor(storage, left, right)
    exact_mean = (tl+tr)/2
    assert F(float(exact_mean)) != exact_mean
    assert result.temperature_k == exact_mean
    assert result.gamma_j_mol == F(storage.wet._mass)*128*exact_mean/F(T_REF)
    assert result.gamma_j_mol != F(storage.wet._mass)*128*F(float(exact_mean))/F(T_REF)
