from __future__ import annotations

import time as clock

import numpy as np
from scipy.integrate import solve_ivp

from .common import GASES, REACTIONS, SIGMA_SB, ModelContext, boundary, finalize_result, reaction_rates, sintering_rate
from .fvm import block_jacobian_sparsity, finite_volume_laplacian


def run_l1(ctx: ModelContext, cells: int = 21):
    n_r, n_g = len(REACTIONS), len(GASES)
    length = ctx.half_thickness_m
    dx = length / cells
    t_eval = np.linspace(0.0, ctx.residence_time_s, 101)
    initial_temperature = float(ctx.case.raw["forming"]["initial_temperature_K"])
    fields = 2 + n_r + n_g
    y0 = np.zeros(cells * fields + n_g + 2)
    y0[:cells] = initial_temperature
    rho_heat = ctx.rho_dry * (1.0 + ctx.water_ratio)
    conductivity = ctx.conductivity
    diffusivity = ctx.diffusivity
    alpha_heat = conductivity / (rho_heat * ctx.cp)

    alpha_start = cells
    gas_start = alpha_start + n_r * cells
    volume_start = gas_start + n_g * cells
    released_start = volume_start + cells

    def rhs(time_s: float, y: np.ndarray) -> np.ndarray:
        temperature = y[:cells]
        extents = y[alpha_start:gas_start].reshape(n_r, cells)
        gas = y[gas_start:volume_start].reshape(n_g, cells)
        bc = boundary(ctx, time_s)
        rates = reaction_rates(ctx, temperature, extents, bc["oxygen_mole_fraction"])

        gas_source = ctx.rho_dry * np.tensordot(ctx.gas_mass_matrix.T, rates, axes=(1, 0))
        q_in = (
            bc["h_W_m2_K"] * float(ctx.parameters.get("h_scale", 1.0)) * (bc["gas_temperature_K"] - temperature[-1])
            + ctx.emissivity * SIGMA_SB * (bc["wall_temperature_K"] ** 4 - temperature[-1] ** 4)
        )
        heat_reaction = -ctx.rho_dry * np.tensordot(np.array([item.deltaH_J_per_kg_dry for item in ctx.potentials]), rates, axes=(0, 0))
        derivative = np.zeros_like(y)
        derivative[:cells] = alpha_heat * finite_volume_laplacian(temperature, dx, q_in / conductivity) + heat_reaction / (rho_heat * ctx.cp)
        derivative[alpha_start:gas_start] = rates.reshape(-1)
        mass_transfer = bc["km_m_s"] * float(ctx.parameters.get("mass_transfer_scale", 1.0))
        outflow = np.maximum(gas[:, -1], 0.0) * mass_transfer
        gas_derivative = np.zeros_like(gas)
        for index in range(n_g):
            gas_derivative[index] = diffusivity * finite_volume_laplacian(gas[index], dx, -outflow[index] / diffusivity) + gas_source[index]
        derivative[gas_start:volume_start] = gas_derivative.reshape(-1)
        derivative[volume_start:released_start] = -sintering_rate(ctx, temperature)
        derivative[released_start : released_start + n_g] = outflow / length
        derivative[-2] = q_in / length
        derivative[-1] = float(heat_reaction.mean())
        return derivative

    started = clock.perf_counter()
    method = "BDF"
    solution = solve_ivp(
        rhs,
        (0.0, ctx.residence_time_s),
        y0,
        method=method,
        t_eval=t_eval,
        rtol=1e-6,
        atol=1e-9,
        max_step=ctx.residence_time_s / 180.0,
        jac_sparsity=block_jacobian_sparsity(cells, n_r, n_g),
    )
    if not solution.success:
        method = "Radau"
        solution = solve_ivp(
            rhs,
            (0.0, ctx.residence_time_s),
            y0,
            method=method,
            t_eval=t_eval,
            rtol=1e-6,
            atol=1e-9,
            max_step=ctx.residence_time_s / 240.0,
            jac_sparsity=block_jacobian_sparsity(cells, n_r, n_g),
        )
    wall = clock.perf_counter() - started
    y = solution.y.T
    extents = y[:, alpha_start:gas_start].reshape(-1, n_r, cells)
    gas = y[:, gas_start:volume_start].reshape(-1, n_g, cells)
    x = (np.arange(cells) + 0.5) * dx
    return finalize_result(
        ctx,
        "L1",
        solution.t,
        x,
        y[:, :cells],
        extents,
        gas,
        y[:, volume_start:released_start],
        y[:, released_start : released_start + n_g],
        y[:, -2],
        y[:, -1],
        bool(solution.success),
        str(solution.message),
        {"method": method, "nfev": int(solution.nfev), "njev": int(solution.njev), "nlu": int(solution.nlu), "wall_time_s": wall, "cells": cells},
    )
