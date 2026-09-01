from __future__ import annotations

import time as clock

import numpy as np
from scipy.integrate import solve_ivp

from .common import GASES, REACTIONS, SIGMA_SB, ModelContext, boundary, finalize_result, oxygen_available_mol_m3, reaction_rates, sintering_rate
from .fvm import block_jacobian_sparsity, conservative_fick_rate, finite_volume_laplacian


def run_l1(ctx: ModelContext, cells: int = 21):
    n_r, n_g = len(REACTIONS), len(GASES)
    rtol = float(ctx.parameters.get("solver_rtol", 1e-6))
    atol = float(ctx.parameters.get("solver_atol", 1e-9))
    if not (np.isfinite(rtol) and np.isfinite(atol) and rtol > 0.0 and atol > 0.0):
        raise ValueError("solver_rtol and solver_atol must be finite and positive")
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
        rates = reaction_rates(
            ctx,
            temperature,
            extents,
            bc["oxygen_mole_fraction"],
            oxygen_available_mol_m3(ctx, time_s),
        )

        gas_source = ctx.rho_dry * np.tensordot(ctx.gas_mass_matrix.T, rates, axes=(1, 0))
        q_in = (
            bc["h_W_m2_K"] * float(ctx.parameters.get("h_scale", 1.0)) * (bc["gas_temperature_K"] - temperature[-1])
            + ctx.emissivity * SIGMA_SB * (bc["wall_temperature_K"] ** 4 - temperature[-1] ** 4)
        )
        heat_reaction = -ctx.rho_dry * np.tensordot(np.array([item.deltaH_J_per_kg_dry for item in ctx.potentials]), rates, axes=(0, 0))
        derivative = np.zeros_like(y)
        derivative[:cells] = alpha_heat * finite_volume_laplacian(temperature, dx, q_in / conductivity) + heat_reaction / (rho_heat * ctx.cp)
        derivative[alpha_start:gas_start] = rates.reshape(-1)
        morphology_scale = ctx.morphology_transport_factor / 0.55
        mass_transfer = bc["km_m_s"] * morphology_scale * float(ctx.parameters.get("mass_transfer_scale", 1.0))
        volume_ratio = np.exp(np.clip(y[volume_start:released_start], -50.0, 50.0))
        dry_loss = np.array([
            0.0,
            ctx.potentials[1].reactant_mass_kg_per_kg_dry,
            ctx.potentials[2].gas_mass_kg_per_kg_dry,
            ctx.potentials[3].gas_mass_kg_per_kg_dry,
        ])
        local_feed_loss = ctx.rho_dry * np.tensordot(dry_loss, extents, axes=(0, 0))
        solid_mass = ctx.rho_dry - local_feed_loss
        total_porosity = np.clip(1.0 - solid_mass / (ctx.true_density * volume_ratio), 1e-9, 1.0)
        open_porosity = np.maximum(total_porosity * ctx.connectivity, 1e-9)
        outflow = np.zeros(n_g)
        gas_derivative = np.zeros_like(gas)
        for index in range(n_g):
            fick_rate, outflow[index] = conservative_fick_rate(
                gas[index],
                open_porosity,
                volume_ratio,
                diffusivity_m2_s=diffusivity,
                dx_reference_m=dx,
                surface_mass_transfer_m_s=mass_transfer,
            )
            gas_derivative[index] = fick_rate + gas_source[index]
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
        rtol=rtol,
        atol=atol,
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
            rtol=rtol,
            atol=atol,
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
        {"method": method, "rtol": rtol, "atol": atol, "nfev": int(solution.nfev), "njev": int(solution.njev), "nlu": int(solution.nlu), "wall_time_s": wall, "cells": cells},
    )
