"""Manufactured-input checks only; no Wang observations or fitted parameters."""
from pathlib import Path
import math
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.integrate import quad

# Entrypoints own these explicit imports. The solver does not edit sys.path.
HERE = Path(__file__).resolve().parent
D1_PATH = HERE.parents[1] / "wang2021-drying-holdout-v1" / "reproduce"
sys.path.insert(0, str(D1_PATH))
sys.path.insert(0, str(HERE))

from wang_d1 import L, Parameters, coefficients, mean_curve
import startup_model
from startup_model import startup_curve


P = Parameters(2e-9, 1e-6, 20000.)
TIMES = [0., 10., 60., 300., 1200., 3600., 12000.]


def test_zero_startup_converges_to_d1_analytic_reference():
    reference, _ = mean_curve(P, 50., .45, TIMES)
    errors = []
    for cells in (16, 32, 64):
        prediction, info = startup_curve(
            P, 50., .45, TIMES, tau_s=0., cells=cells,
            rtol=1e-11, atol=1e-13,
        )
        errors.append(float(np.max(np.abs(prediction - reference))))
        assert info["activation"] == "constant_one_tau_zero"
    assert errors[0] > 3.5 * errors[1]
    assert errors[1] > 3.5 * errors[2]
    assert errors[2] < 2e-5


@pytest.mark.parametrize("tau", [0., 600.])
def test_single_cell_matches_independent_integrated_decay(tau):
    times = [0., 1., 60., 600., 12000.]
    d, k = coefficients(P, 50., .45)
    # Independent scalar quadrature of the one-cell resistance law. This does
    # not call the solver's RHS, Jacobian, or activation implementation.
    def decay_rate(t):
        a = 1. if tau == 0. else 1. - math.exp(-t / tau)
        return 1. / (L / (k * a) + L**2 / (2. * d)) if a else 0.

    reference = np.array([
        math.exp(-quad(decay_rate, 0., t, epsabs=1e-13, epsrel=1e-13)[0])
        for t in times
    ])
    prediction, info = startup_curve(
        P, 50., .45, times, tau_s=tau, cells=1,
        rtol=1e-11, atol=1e-13,
    )
    np.testing.assert_allclose(prediction, reference, rtol=2e-9, atol=2e-11)
    assert info["mass_balance_max_abs"] < 2e-12


def test_integrated_outflow_and_accepted_states_conserve_mass():
    prediction, info = startup_curve(P, 50., .45, TIMES, tau_s=600., cells=31)
    outflow = np.array(info["cumulative_outflow_at_times"])
    assert outflow[0] == 0.
    assert outflow[-1] > .9
    np.testing.assert_allclose(prediction + outflow, 1., rtol=0., atol=2e-12)
    assert info["mass_balance_max_abs"] < 2e-12
    assert -1e-10 <= info["cell_min"] <= info["cell_max"] <= 1. + 1e-10
    assert np.all(np.diff(prediction) <= 1e-10)
    assert info["mean_increase_max"] <= 1e-10
    assert info["diagnostic_scope"] == "accepted_steps_and_requested_times"
    assert info["accepted_steps"] > 0
    assert info["wall_seconds"] > 0.
    assert info["cells"] == 31
    assert info["dx_m"] == L / 31
    assert info["rtol"] == 1e-9
    assert info["atol"] == 1e-11
    assert not {"modes", "tail_bound", "roots"}.intersection(info)


def test_nonzero_startup_grid_and_tolerance_refinement():
    solutions = [startup_curve(
        P, 50., .45, TIMES, tau_s=600., cells=n,
        rtol=1e-11, atol=1e-13,
    )[0] for n in (32, 64, 128)]
    coarse_delta = float(np.max(np.abs(solutions[0] - solutions[1])))
    fine_delta = float(np.max(np.abs(solutions[1] - solutions[2])))
    assert coarse_delta > 3.5 * fine_delta
    assert fine_delta < 2e-5
    ordinary, _ = startup_curve(P, 50., .45, TIMES, tau_s=600., cells=64)
    assert float(np.max(np.abs(ordinary - solutions[1]))) < 1e-7


def test_duplicate_times_preserve_order_and_initial_only_needs_no_solver():
    repeated, info = startup_curve(
        P, np.float64(50.), np.float64(.45), np.array([0., 0., 30., 30., 60.]),
        tau_s=np.float64(600.), cells=np.int64(4),
    )
    assert repeated[0] == repeated[1] == 1.
    assert repeated[2] == repeated[3]
    assert len(info["cumulative_outflow_at_times"]) == 5
    initial, initial_info = startup_curve(P, 50., .45, [0., 0.], tau_s=0., cells=1)
    np.testing.assert_array_equal(initial, [1., 1.])
    assert initial_info["nfev"] == initial_info["njev"] == initial_info["nlu"] == 0
    assert initial_info["accepted_steps"] == 0
    assert initial_info["mean_increase_max"] == 0.
    assert initial_info["cumulative_outflow_at_times"] == [0., 0.]


@pytest.mark.parametrize("times", [
    [], [0., -1.], [2., 1.], [math.nan], [math.inf], [[1.]], 1., [True], ["1"],
    [0., True],
])
def test_invalid_time_vectors_are_rejected(times):
    with pytest.raises(ValueError):
        startup_curve(P, 50., .45, times, tau_s=600., cells=4)


@pytest.mark.parametrize("keyword,value", [
    ("tau_s", -1.), ("tau_s", math.nan), ("tau_s", math.inf), ("tau_s", True),
    ("cells", 0), ("cells", -1), ("cells", 1.5), ("cells", True),
    ("rtol", 0.), ("rtol", 1e-20), ("rtol", math.nan), ("rtol", True),
    ("atol", 0.), ("atol", math.inf), ("atol", True),
])
def test_invalid_solver_inputs_are_rejected(keyword, value):
    kwargs = {"tau_s": 600., "cells": 4, keyword: value}
    with pytest.raises(ValueError):
        startup_curve(P, 50., .45, [0., 10.], **kwargs)


@pytest.mark.parametrize("p,t,h", [(None, 50., .45), (P, 39., .45), (P, 50., .61)])
def test_d1_parameter_and_label_domain_is_preserved(p, t, h):
    with pytest.raises(ValueError):
        startup_curve(p, t, h, [0., 10.], tau_s=600., cells=4)


@pytest.mark.parametrize("failure_call", [1, 3])
def test_budget_guard_failure_propagates(failure_call):
    calls = 0
    class BudgetExceeded(RuntimeError):
        pass

    def guard():
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise BudgetExceeded("manufactured budget exhaustion")

    with pytest.raises(BudgetExceeded, match="manufactured budget exhaustion"):
        startup_curve(P, 50., .45, TIMES, tau_s=600., cells=4, guard=guard)
    assert calls == failure_call


def test_diagnostics_preserve_solver_counts_and_independent_outflow(monkeypatch):
    original = startup_model.solve_ivp
    recorded = {}

    def recording_solver(*args, **kwargs):
        result = original(*args, **kwargs)
        recorded.update(nfev=result.nfev, njev=result.njev, nlu=result.nlu)
        # Perturb only the independently integrated state to check that the
        # reported balance is not manufactured from 1 - mean(u).
        result.y[-1] += .125
        original_dense = result.sol
        def perturbed_dense(t):
            values = original_dense(t)
            values[-1] += .125
            return values
        result.sol = perturbed_dense
        return result

    monkeypatch.setattr(startup_model, "solve_ivp", recording_solver)
    prediction, info = startup_curve(P, 50., .45, TIMES, tau_s=600., cells=4)
    assert all(info[key] == value for key, value in recorded.items())
    assert info["mass_balance_max_abs"] == pytest.approx(.125, abs=2e-12)
    np.testing.assert_allclose(
        prediction + info["cumulative_outflow_at_times"], 1.125,
        rtol=0., atol=2e-12,
    )


def test_mean_increase_uses_sorted_union_of_accepted_and_requested_times(monkeypatch):
    # Accepted-only MR rises by .025; requested-only MR rises by .05. The
    # sorted union reveals the .125 rise from requested t=600 to accepted 900.
    accepted_mean = np.array([1., .9, .925, .85])
    sampled_mean = np.array([1., .8, .85])
    result = SimpleNamespace(
        success=True, message="manufactured diagnostic fixture", status=0,
        t=np.array([0., 300., 900., 1200.]),
        y=np.vstack((accepted_mean, accepted_mean, [0., .1, .075, .15])),
        sol=lambda times: np.vstack((sampled_mean, sampled_mean, [0., .2, .15])),
        nfev=10, njev=1, nlu=2,
    )
    monkeypatch.setattr(startup_model, "solve_ivp", lambda *args, **kwargs: result)
    _, info = startup_curve(P, 50., .45, [0., 600., 1200.], tau_s=600., cells=2)
    assert info["mean_increase_max"] == pytest.approx(.125, abs=1e-15)
