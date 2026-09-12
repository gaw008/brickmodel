"""Constant-D diffusion with a hypothesized startup of surface exchange.

The layer has D1's full thickness L, a sealed bottom, and the top law
    -D du/dx = k a(t) u_surface,  a(t) = 1 - exp(-t/tau).
For tau=0 the surface activation is exactly one. This is an exchange hypothesis,
not a measured temperature, area, geometry change, or material qualification.
Entrypoints must explicitly put the original D1 module on their import path.
"""
import math
from numbers import Integral, Real
from time import perf_counter

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import csc_matrix

from wang_d1 import L, coefficients


def _number(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite real number")
    return result


def startup_curve(p, temperature_c, rh, times_s, *, tau_s, cells,
                  rtol=1e-9, atol=1e-11, guard=lambda: None):
    """Return layer-mean MR and actual BDF/FVM diagnostics.

    Times are finite, nonnegative, nondecreasing seconds; duplicates retain their
    positions. Uniform cell averages initially equal one. The independent final
    state integrates normalized top outflow, dq/dt=J_top/L, starting at zero.
    No clipping, modal approximation, or reconstructed outflow is used.

    Diagnostics cover accepted integration steps and requested output times.
    They are observations of this solve, not rigorous discretization bounds.
    Guard exceptions propagate unchanged, including from RHS/Jacobian calls.
    """
    started = perf_counter()
    temperature_c = _number(temperature_c, "temperature_c")
    rh = _number(rh, "rh")
    d, k = coefficients(p, temperature_c, rh)
    if not (math.isfinite(d) and d > 0. and math.isfinite(k) and k > 0.):
        raise ValueError("positive finite D1 transport coefficients required")
    tau_s = _number(tau_s, "tau_s")
    if tau_s < 0.:
        raise ValueError("tau_s must be nonnegative")
    if isinstance(cells, (bool, np.bool_)) or not isinstance(cells, Integral) or cells < 1:
        raise ValueError("cells must be a positive integer")
    cells = int(cells)
    rtol, atol = _number(rtol, "rtol"), _number(atol, "atol")
    # SciPy otherwise silently increases rtol below this floor. Reject instead
    # so the returned requested tolerance is also the one actually used.
    if rtol < 100. * np.finfo(float).eps or atol <= 0.:
        raise ValueError("rtol must be at least 100 machine epsilons and atol positive")
    if not callable(guard):
        raise ValueError("guard must be callable")
    try:
        # Preserve individual types: [True, 2.] must not turn True into 1.0
        # before the finite-real-input check.
        raw_times = np.asarray(times_s, dtype=object)
    except (TypeError, ValueError) as exc:
        raise ValueError("nonempty nonnegative nondecreasing time vector required") from exc
    if raw_times.ndim != 1 or not raw_times.size:
        raise ValueError("nonempty nonnegative nondecreasing time vector required")
    times = np.array([_number(t, "time") for t in raw_times], dtype=float)
    if np.any(times < 0.) or np.any(times[1:] < times[:-1]):
        raise ValueError("nonempty nonnegative nondecreasing time vector required")
    try:
        dx = L / cells
        alpha = d / dx**2
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("grid spacing and diffusion rate must be finite and positive") from exc
    if not (math.isfinite(dx) and dx > 0. and math.isfinite(alpha) and alpha > 0.):
        raise ValueError("grid spacing and diffusion rate must be finite and positive")

    info = {
        "method": "BDF", "cells": cells, "dx_m": dx, "length_m": L,
        "rtol": rtol, "atol": atol, "tau_s": tau_s,
        "temperature_c": temperature_c, "rh": rh,
        "diffusivity_m2_s": d, "exchange_m_s": k,
        "activation": "constant_one_tau_zero" if tau_s == 0. else "negative_expm1",
        "diagnostic_scope": "accepted_steps_and_requested_times",
    }
    guard()
    if times[-1] == 0.:
        info.update(
            solver_ran=False, nfev=0, njev=0, nlu=0, accepted_steps=0,
            cell_min=1., cell_max=1., mass_balance_max_abs=0., mean_increase_max=0.,
            cumulative_outflow_at_times=[0.] * len(times),
            solver_status=0, solver_message="initial state only",
        )
        guard()
        info["wall_seconds"] = perf_counter() - started
        return np.ones_like(times), info

    # The last cell average is dx/2 from the surface. Both the half-cell
    # diffusion resistance and the time-dependent Robin resistance are retained.
    if tau_s == 0.:
        constant_transfer = k / (1. + k * dx / (2. * d))
        def transfer(t):
            return constant_transfer
    else:
        def transfer(t):
            activated_k = k * -math.expm1(-t / tau_s)
            return activated_k / (1. + activated_k * dx / (2. * d))

    def rhs(t, state):
        guard()
        derivative = np.zeros_like(state)
        # Every internal transfer leaves one cell and enters its neighbor.
        internal = alpha * (state[:cells - 1] - state[1:cells])
        derivative[:cells - 1] -= internal
        derivative[1:cells] += internal
        top_flux = transfer(t) * state[cells - 1]
        derivative[cells - 1] -= top_flux / dx
        derivative[cells] = top_flux / L
        return derivative

    diagonal = np.zeros(cells)
    if cells > 1:
        diagonal[:] = -2. * alpha
        diagonal[0] = diagonal[-1] = -alpha
    base_data = np.concatenate((diagonal, np.full(2 * (cells - 1), alpha), [0.]))
    rows = np.concatenate((np.arange(cells), np.arange(cells - 1),
                           np.arange(1, cells), [cells]))
    columns = np.concatenate((np.arange(cells), np.arange(1, cells),
                              np.arange(cells - 1), [cells - 1]))

    def jacobian(t, state):
        guard()
        boundary = transfer(t)
        data = base_data.copy()
        data[cells - 1] -= boundary / dx
        data[-1] = boundary / L
        return csc_matrix((data, (rows, columns)), shape=(cells + 1, cells + 1))

    initial = np.ones(cells + 1)
    initial[-1] = 0.
    solution = solve_ivp(
        rhs, (0., float(times[-1])), initial,
        method="BDF", jac=jacobian, rtol=rtol, atol=atol, dense_output=True,
    )
    guard()
    if not solution.success:
        raise RuntimeError(f"startup integration failed: {solution.message}")
    samples = solution.sol(times)
    if not (np.all(np.isfinite(solution.y)) and np.all(np.isfinite(samples))):
        raise RuntimeError("startup integration returned a nonfinite state")
    mean = np.mean(samples[:cells], axis=0)
    accepted_mean = np.mean(solution.y[:cells], axis=0)
    accepted_balance = accepted_mean + solution.y[-1] - 1.
    sampled_balance = mean + samples[-1] - 1.
    # Check the chronologically merged trajectory, since a rise can cross from
    # a requested sample to an accepted step (or vice versa). Prefer accepted
    # states where both grids contain the exact same time.
    _, chronological = np.unique(np.concatenate((solution.t, times)), return_index=True)
    merged_mean = np.concatenate((accepted_mean, mean))[chronological]
    info.update(
        solver_ran=True, nfev=int(solution.nfev), njev=int(solution.njev),
        nlu=int(solution.nlu), accepted_steps=len(solution.t) - 1,
        cell_min=float(min(np.min(solution.y[:cells]), np.min(samples[:cells]))),
        cell_max=float(max(np.max(solution.y[:cells]), np.max(samples[:cells]))),
        mass_balance_max_abs=float(max(np.max(np.abs(accepted_balance)),
                                       np.max(np.abs(sampled_balance)))),
        mean_increase_max=float(max(0., np.max(np.diff(merged_mean)))),
        cumulative_outflow_at_times=samples[-1].tolist(),
        solver_status=int(solution.status), solver_message=str(solution.message),
    )
    guard()
    info["wall_seconds"] = perf_counter() - started
    return mean, info
