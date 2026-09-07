"""Scripted TP numerical control, never a fake EOS or material validation."""
from contextlib import contextmanager
import math
from threading import RLock
from types import SimpleNamespace

import pytest
from sludge_sandbox._heos_kernel import HEOSCandidate
from sludge_sandbox.water_properties import WaterNumericalError, WaterSourceError


class Flash:
    def __init__(self, residuals, *, phase='liquid', seed=None, invalid=None):
        self.residuals = residuals
        self.requested_phase = phase
        self.seed = (1000. if phase == 'liquid' else .5) if seed is None else seed
        self.invalid = invalid
        self.imposed = None
        self.evaluations = []
        self.index = -1
        self.rho = self.seed
        self.target = .1

    def update(self, kind, value, temperature):
        if kind == 'PT':
            self.target, self.rho = value, self.seed
            return
        self.rho = value
        self.evaluations.append(value)
        self.index += 1
        if self.invalid == 'native' and self.index == 1:
            raise ValueError('scripted native trial failure')

    def phase(self):
        if self.invalid == 'phase' and self.index == 1:
            return 'wrong'
        return 'L' if self.requested_phase == 'liquid' else 'V'
    def rhomass(self): return self.rho
    def specify_phase(self, phase): self.imposed = phase
    def unspecify_phase(self): self.imposed = None
    def p(self):
        if self.invalid == 'residual' and self.index == 1:
            return math.nan
        return self.target+self.residuals[min(self.index, len(self.residuals)-1)]
    def hmass(self): return 19.
    def umass(self): return 17.
    def dalphar_dDelta(self): return 0.
    def d2alphar_dDelta2(self):
        return -1e9 if self.invalid == 'slope' and self.index == 1 else 0.


def fixture(residuals, *, phase='liquid', seed=None, invalid=None):
    obj = object.__new__(HEOSCandidate)
    obj._flash = Flash(residuals, phase=phase, seed=seed, invalid=invalid)
    obj._cp = SimpleNamespace(PT_INPUTS='PT', DmassT_INPUTS='DT', iphase_liquid='L',
                              iphase_supercritical_liquid='SL', iphase_gas='V')
    obj._r = 1.
    obj._lock = RLock()
    obj._tp_iterations = []
    flags = {'transaction_enter': 0, 'transaction_exit': 0, 'snapshots': 0}

    @contextmanager
    def transaction():
        flags['transaction_enter'] += 1
        if invalid == 'pre_source':
            raise WaterSourceError('scripted_source_changed_before')
        yield
        flags['transaction_exit'] += 1
        if invalid == 'post_source':
            raise WaterSourceError('scripted_source_changed_after')

    obj._transaction = transaction
    obj._saturation_pair_locked = lambda t: (
        SimpleNamespace(density=997., pressure=.001 if phase == 'liquid' else 1.),
        SimpleNamespace(density=1.))

    def snapshot(t, p, phase):
        flags['snapshots'] += 1
        if invalid == 'snapshot':
            raise WaterNumericalError('scripted_snapshot_invalid')
        return SimpleNamespace(density=obj._flash.rho, pressure=p, phase=phase)

    obj._snapshot = snapshot
    return obj, flags


def solve(obj, phase='liquid'):
    return obj.state_tp(300., .1, phase=phase)


def test_seed_gate_pass_has_one_actual_density_evaluation():
    obj, flags = fixture([0.])
    out = solve(obj)
    assert out.density == 1000.
    assert obj._flash.evaluations == [1000.]
    assert len(obj.last_tp) == 1 and flags == {'transaction_enter': 1, 'transaction_exit': 1, 'snapshots': 1}
    assert obj._flash.imposed is None


def test_improving_full_step_has_no_duplicate_native_evaluation():
    obj, _ = fixture([.001, 0.])
    solve(obj)
    assert len(obj._flash.evaluations) == 2
    first, last = obj.last_tp
    expected = first['rho']*math.exp(-first['residual_pa']/first['slope'])
    assert last['rho'] == expected == obj._flash.evaluations[-1]


def test_worse_full_step_uses_half_of_same_original_direction():
    obj, _ = fixture([.001, .002, 0.])
    solve(obj)
    assert len(obj._flash.evaluations) == 3
    base, full, half = obj.last_tp
    step = -base['residual_pa']/base['slope']
    assert full['rho'] == base['rho']*math.exp(step)
    assert half['rho'] == base['rho']*math.exp(step/2)
    assert full['accepted'] is False and half['accepted'] is True
    assert half['fraction'] == .5
    assert obj._flash.imposed is None


def test_equal_merit_stagnation_fails_after_six_trials():
    obj, flags = fixture([.001])
    with pytest.raises(WaterNumericalError, match='heos_tp_backtracking_failed'):
        solve(obj)
    assert len(obj._flash.evaluations) == 7
    assert len(obj.last_tp) == 7
    assert all(row['accepted'] is False for row in obj.last_tp[1:])
    assert flags['snapshots'] == 0 and obj._flash.imposed is None


@pytest.mark.parametrize('invalid, reason', [('native', 'heos_tp_failed'),
    ('slope', 'heos_tp_invalid_slope'), ('residual', 'heos_tp_invalid_slope'),
    ('phase', 'heos_tp_seed_wrong_phase')])
def test_invalid_first_trial_is_fatal_without_shorter_retry(invalid, reason):
    obj, flags = fixture([.001, .002, 0.], invalid=invalid)
    with pytest.raises(WaterNumericalError, match=reason):
        solve(obj)
    assert len(obj._flash.evaluations) == 2
    assert len(obj.last_tp) == 2
    assert obj.last_tp[-1]['rho'] == obj._flash.evaluations[-1]
    assert obj.last_tp[-1]['fraction'] == 1.
    assert obj.last_tp[-1]['status'] == 'failed'
    assert obj.last_tp[-1]['accepted'] is False
    assert flags['snapshots'] == 0 and obj._flash.imposed is None


def test_original_large_step_is_not_rescued_by_damping():
    obj, _ = fixture([1e8])
    with pytest.raises(WaterNumericalError, match='heos_tp_step_outside_seed_branch'):
        solve(obj)
    assert len(obj._flash.evaluations) == 1 and obj._flash.imposed is None


def test_density_branch_crossing_is_fatal_before_native_trial():
    obj, _ = fixture([100.], seed=997.000001)
    with pytest.raises(WaterNumericalError, match='heos_tp_density_branch'):
        solve(obj)
    assert len(obj._flash.evaluations) == 1 and obj._flash.imposed is None


def test_vapor_uses_original_density_scaled_gate():
    obj, flags = fixture([7e-8], phase='vapor')
    with pytest.raises(WaterNumericalError, match='heos_tp_backtracking_failed'):
        solve(obj, 'vapor')
    assert 7e-8 < 1e-4 and 7e-8 > .5*1e-7
    assert len(obj._flash.evaluations) == 7 and flags['snapshots'] == 0


def test_eighth_accepted_density_cannot_create_a_ninth():
    obj, flags = fixture([.001/(i+1) for i in range(10)])
    with pytest.raises(WaterNumericalError, match='heos_tp_not_converged'):
        solve(obj)
    assert len(obj._flash.evaluations) == 8
    assert sum(bool(row['accepted']) for row in obj.last_tp) == 8
    assert flags['snapshots'] == 0 and obj._flash.imposed is None


def test_seven_six_trial_searches_have_exact_43_evaluation_bound():
    # Five deliberately worse proposals followed by one strict improvement
    # at each of seven updates; none reaches the unchanged physical gate.
    values = [.008]
    for level in range(1, 8):
        values.extend([.02]*5+[.008/(level+1)])
    obj, flags = fixture(values)
    with pytest.raises(WaterNumericalError, match='heos_tp_not_converged'):
        solve(obj)
    assert len(obj._flash.evaluations) == len(obj.last_tp) == 43
    assert sum(bool(row['accepted']) for row in obj.last_tp) == 8
    assert [row['fraction'] for row in obj.last_tp if row['accepted']][1:] == [.03125]*7
    assert flags['snapshots'] == 0


@pytest.mark.parametrize('invalid', ['pre_source', 'post_source'])
def test_source_transaction_failure_never_returns_a_state(invalid):
    obj, flags = fixture([0.], invalid=invalid)
    with pytest.raises(WaterSourceError, match='scripted_source_changed'):
        solve(obj)
    assert flags['snapshots'] == (0 if invalid == 'pre_source' else 1)
    assert obj._flash.imposed is None


def test_final_snapshot_failure_is_not_relabelled_as_success():
    obj, _ = fixture([0.], invalid='snapshot')
    with pytest.raises(WaterNumericalError, match='scripted_snapshot_invalid'):
        solve(obj)
    assert len(obj._flash.evaluations) == 1 and obj._flash.imposed is None


def test_exact_same_density_and_merit_stagnation_is_rejected():
    obj, flags = fixture([.001])
    obj._r = 1e16
    with pytest.raises(WaterNumericalError, match='heos_tp_backtracking_failed'):
        solve(obj)
    assert obj._flash.evaluations == [1000.]*7
    assert len({row['normalized_residual'] for row in obj.last_tp}) == 1
    assert flags['snapshots'] == 0


@pytest.mark.parametrize('residual', [0., 1e-320])
def test_original_zero_underflow_gate_never_admits_nonzero_residual(residual):
    obj, flags = fixture([residual], phase='vapor', seed=1e-320)
    if residual == 0:
        state = obj.state_tp(300., 1e-310, phase='vapor')
        assert state.density == 1e-320 and flags['snapshots'] == 1
        assert obj.last_tp[0]['normalized_residual'] == 0.
    else:
        with pytest.raises(WaterNumericalError, match='heos_tp_backtracking_failed'):
            obj.state_tp(300., 1e-310, phase='vapor')
        assert len(obj._flash.evaluations) == 7 and flags['snapshots'] == 0
        assert all(row['residual_pa'] != 0. and math.isinf(row['normalized_residual']) for row in obj.last_tp)
    assert all(row['gate_pa'] == 0. for row in obj.last_tp)
    assert obj._flash.imposed is None
