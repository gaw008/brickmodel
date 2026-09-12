"""Independent manufactured probes of solver algebra and validation."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
RESEARCH = ROOT/'docs/sandbox/research'
sys.path[:0] = [str(RESEARCH/'wang2021-drying-holdout-v1/reproduce')]
spec = importlib.util.spec_from_file_location('review_solver',
    RESEARCH/'wang2021-startup-v1/reproduce/startup_model.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from wang_d1 import Parameters

PARAMETERS = Parameters(3e-9, 8e-7, 40000.)


@pytest.mark.parametrize('times', [[True, 2.], [np.bool_(True), np.float64(2.)]])
def test_mixed_boolean_times_rejected_before_solver(monkeypatch, times):
    def forbidden(*args, **kwargs):
        raise AssertionError('invalid input reached solver')
    monkeypatch.setattr(module, 'solve_ivp', forbidden)
    with pytest.raises(ValueError, match='time must be a finite real number'):
        module.startup_curve(PARAMETERS, 40., .3, times, tau_s=600., cells=2)


@pytest.mark.parametrize('cells', [1, 2, 16])
@pytest.mark.parametrize('tau', [0., 600.])
def test_semidiscrete_water_identity_and_sparse_jacobian(monkeypatch, cells, tau):
    class Inspected(Exception):
        pass

    def inspect(rhs, span, initial, *, jac, **kwargs):
        state = np.r_[np.linspace(.13, .87, cells), .25]
        for t in (0., 1e-10, 600.):
            derivative = rhs(t, state)
            assert abs(float(np.mean(derivative[:-1])+derivative[-1])) < 1e-15
            actual = jac(t, state).toarray()
            difference = np.column_stack([
                (rhs(t, state + np.eye(cells+1)[j]*1e-5)
                 - rhs(t, state - np.eye(cells+1)[j]*1e-5))/(2e-5)
                for j in range(cells+1)])
            np.testing.assert_allclose(actual, difference, rtol=2e-9, atol=1e-12)
            np.testing.assert_allclose(np.mean(actual[:-1], axis=0)+actual[-1], 0., atol=1e-15)
        raise Inspected

    monkeypatch.setattr(module, 'solve_ivp', inspect)
    with pytest.raises(Inspected):
        module.startup_curve(PARAMETERS, 40., .3, [600.], tau_s=tau, cells=cells)


def test_zero_time_has_all_physical_gate_fields_without_solver(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('initial state called solver')
    monkeypatch.setattr(module, 'solve_ivp', forbidden)
    mean, diagnostic = module.startup_curve(PARAMETERS, 40., .3, [0., 0.], tau_s=600., cells=2)
    np.testing.assert_array_equal(mean, [1., 1.])
    assert diagnostic['mass_balance_max_abs'] == 0.
    assert diagnostic['mean_increase_max'] == 0.
    assert diagnostic['cell_min'] == diagnostic['cell_max'] == 1.
