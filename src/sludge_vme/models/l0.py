from __future__ import annotations

import time as clock

import numpy as np
from scipy.integrate import solve_ivp

from .common import GASES, REACTIONS, SIGMA_SB, ModelContext, boundary, finalize_result, reaction_rates, sintering_rate


def run_l0(ctx: ModelContext):
    n_r, n_g = len(REACTIONS), len(GASES)
    t_eval = np.linspace(0.0, ctx.residence_time_s, 121)
    initial_temperature = float(ctx.case.raw["forming"]["initial_temperature_K"])
    y0 = np.zeros(1 + n_r + n_g + 1 + n_g + 2)
    y0[0] = initial_temperature
    rho_heat = ctx.rho_dry * (1.0 + ctx.water_ratio)

    def rhs(time_s: float, y: np.ndarray) -> np.ndarray:
        temperature = y[0]
        extents = y[1 : 1 + n_r]
        gas_start = 1 + n_r
        gas = y[gas_start : gas_start + n_g]
        bc = boundary(ctx, time_s)
        rates = reaction_rates(ctx, np.array([temperature]), extents[:, None], bc["oxygen_mole_fraction"])[:, 0]

        gas_source = ctx.rho_dry * (rates @ ctx.gas_mass_matrix)
        release_rate = max(0.0, bc["km_m_s"] * float(ctx.parameters.get("mass_transfer_scale", 1.0)) / ctx.half_thickness_m)
        outflow = release_rate * np.maximum(gas, 0.0)
        heat_boundary = (
            bc["h_W_m2_K"] * float(ctx.parameters.get("h_scale", 1.0)) * (bc["gas_temperature_K"] - temperature)
            + ctx.emissivity * SIGMA_SB * (bc["wall_temperature_K"] ** 4 - temperature**4)
        ) / ctx.half_thickness_m
        heat_reaction = -ctx.rho_dry * float(np.dot([item.deltaH_J_per_kg_dry for item in ctx.potentials], rates))
        derivative = np.zeros_like(y)
        derivative[0] = (heat_boundary + heat_reaction) / (rho_heat * ctx.cp)
        derivative[1 : 1 + n_r] = rates
        derivative[gas_start : gas_start + n_g] = gas_source - outflow
        derivative[gas_start + n_g] = -float(sintering_rate(ctx, np.array([temperature]))[0])
        released_start = gas_start + n_g + 1
        derivative[released_start : released_start + n_g] = outflow
        derivative[-2] = heat_boundary
        derivative[-1] = heat_reaction
        return derivative

    started = clock.perf_counter()
    solution = solve_ivp(rhs, (0.0, ctx.residence_time_s), y0, method="BDF", t_eval=t_eval, rtol=1e-6, atol=1e-8, max_step=ctx.residence_time_s / 240.0)
    wall = clock.perf_counter() - started
    y = solution.y.T
    gas_start = 1 + n_r
    released_start = gas_start + n_g + 1
    return finalize_result(
        ctx,
        "L0",
        solution.t,
        np.array([0.0]),
        y[:, 0, None],
        y[:, 1 : 1 + n_r, None],
        y[:, gas_start : gas_start + n_g, None],
        y[:, gas_start + n_g, None],
        y[:, released_start : released_start + n_g],
        y[:, -2],
        y[:, -1],
        bool(solution.success),
        str(solution.message),
        {"method": "BDF", "nfev": int(solution.nfev), "njev": int(solution.njev), "nlu": int(solution.nlu), "wall_time_s": wall, "cells": 1},
    )
