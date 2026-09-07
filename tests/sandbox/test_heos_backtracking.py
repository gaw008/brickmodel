"""No native EOS: scripted responses exercise solver control and fail-closed behavior.

These are numerical control tests, not thermodynamic validation. Density changes
are observed independently; scripted pressure/Gibbs responses deliberately need
not form a consistent EOS.
"""
import math
from types import SimpleNamespace
import pytest
from sludge_sandbox._heos_kernel import HEOSCandidate
from sludge_sandbox.water_properties import WaterNumericalError


class Flash:
    def __init__(self, residuals, invalid=None, seeds=(1000., 1.)):
        self.residuals = residuals
        self.invalid = invalid
        self.seeds = seeds
        self.evaluations = []
        self.pair_index = -1
        self.imposed = None

    def update(self, kind, value, temperature):
        if kind == 'QT':
            self.q = value
            self.rho = self.seeds[value]
            return
        self.rho = value
        if self.imposed == 'L':
            self.pair_index += 1
        self.evaluations.append((self.imposed, value))
        if self.invalid == 'native' and self.pair_index == 1:
            raise ValueError('native trial failure')

    def phase(self): return 'two'
    def Q(self): return self.q
    def rhomass(self): return self.rho
    def specify_phase(self, phase): self.imposed = phase
    def unspecify_phase(self): self.imposed = None
    def residual(self):
        return self.residuals[min(self.pair_index, len(self.residuals)-1)]
    def p(self): return 1000. + (self.residual()[0] if self.imposed == 'L' else 0.)
    def hmass(self): return self.residual()[1] if self.imposed == 'L' else 0.
    def umass(self): return 17.
    def smass(self): return 0.
    def dalphar_dDelta(self): return 0.
    def d2alphar_dDelta2(self):
        if self.invalid == 'slope' and self.pair_index == 1:
            return -1e9
        return 0.


def candidate(residuals, **kwargs):
    obj = object.__new__(HEOSCandidate)
    obj._flash = Flash(residuals, **kwargs)
    obj._cp = SimpleNamespace(QT_INPUTS='QT', DmassT_INPUTS='DT',
                              iphase_twophase='two', iphase_liquid='L', iphase_gas='V')
    obj._r = 1.
    obj._coexistence = []
    obj._snapshot = lambda t, p, phase: SimpleNamespace(
        density=obj._flash.rho, pressure=p, h=0., s=0.)
    return obj


def test_full_step_converges_without_duplicate_evaluation():
    obj = candidate([(1e-3, 0.), (0., 0.)])
    obj._saturation_pair_locked(300.)
    # Two evaluations per pair, followed by the two final snapshot updates.
    assert len(obj._flash.evaluations) == 6
    assert len(obj._coexistence) == 2


def test_half_step_rescues_worse_full_step():
    obj = candidate([(1e-3, 0.), (2e-3, 0.), (0., 0.)])
    obj._saturation_pair_locked(300.)
    trials = obj._flash.evaluations
    seed, full, half = trials[0][1], trials[2][1], trials[4][1]
    assert math.log(half/seed) == pytest.approx(math.log(full/seed)/2, abs=3e-16)
    assert len(obj._coexistence) == 2
    assert len(trials) == 8


def test_no_improvement_has_bounded_explicit_failure():
    obj = candidate([(1e-3, 0.)])
    with pytest.raises(WaterNumericalError, match='heos_coexistence_backtracking_failed'):
        obj._saturation_pair_locked(300.)
    assert len(obj._flash.evaluations) == 14  # initial pair + six trials
    assert len(obj._coexistence) == 1


@pytest.mark.parametrize('invalid, message', [('slope', 'heos_coexistence_invalid'),
                                            ('native', 'heos_saturation_failed')])
def test_invalid_trial_is_not_silently_retried(invalid, message):
    obj = candidate([(1e-3, 0.)], invalid=invalid)
    with pytest.raises(WaterNumericalError, match=message):
        obj._saturation_pair_locked(300.)
    assert len(obj._flash.evaluations) == 3
    assert obj._flash.imposed is None


def test_invalid_seed_branch_fails_before_eos():
    obj = candidate([(1e-3, 0.)], seeds=(321., 1.))
    with pytest.raises(WaterNumericalError, match='density_branches'):
        obj._saturation_pair_locked(300.)
    assert obj._flash.evaluations == []


def test_eight_outer_iterations_remain_bounded():
    obj = candidate([(1e-2/(i+1), 0.) for i in range(20)])
    with pytest.raises(WaterNumericalError, match='heos_coexistence_not_converged'):
        obj._saturation_pair_locked(300.)
    assert len(obj._coexistence) == 8
    assert len(obj._flash.evaluations) == 16


def test_trial_crossing_density_branch_is_fatal():
    obj = candidate([(1., 0.)], seeds=(322.000001, 1.))
    with pytest.raises(WaterNumericalError, match='density_branches'):
        obj._saturation_pair_locked(300.)
    assert len(obj._flash.evaluations) == 2


def test_original_newton_step_limit_is_not_rescued_by_damping():
    obj = candidate([(1e9, 0.)])
    with pytest.raises(WaterNumericalError, match='step_outside_seed_branch'):
        obj._saturation_pair_locked(300.)
    assert len(obj._flash.evaluations) == 2


@pytest.mark.parametrize('residual', [(1.01e-4, 0.), (0., 1.01e-6)])
def test_each_original_absolute_gate_is_enforced(residual):
    obj = candidate([residual])
    with pytest.raises(WaterNumericalError, match='backtracking_failed'):
        obj._saturation_pair_locked(300.)
    assert len(obj._flash.evaluations) == 14
