from __future__ import annotations

import time as clock

import numpy as np
from scipy.integrate import solve_ivp

from .common import GASES, REACTIONS, SIGMA_SB, ModelContext, boundary, finalize_result, oxygen_available_mol_m3, reaction_rates, sintering_rate


def run_l0(ctx: ModelContext):
    n_r, n_g = len(REACTIONS), len(GASES)
    rtol = float(ctx.parameters.get("solver_rtol", 1e-6))
    atol = float(ctx.parameters.get("solver_atol", 1e-8))
    if not (np.isfinite(rtol) and np.isfinite(atol) and rtol > 0.0 and atol > 0.0):
        raise ValueError("solver_rtol and solver_atol must be finite and positive")
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
        rates = reaction_rates(
            ctx,
            np.array([temperature]),
            extents[:, None],
            bc["oxygen_mole_fraction"],
            oxygen_available_mol_m3(ctx, time_s),
        )[:, 0]

        gas_source = ctx.rho_dry * (rates @ ctx.gas_mass_matrix)
        morphology_scale = ctx.morphology_transport_factor / 0.55
        external_mass_transfer = max(0.0, bc["km_m_s"] * morphology_scale * float(ctx.parameters.get("mass_transfer_scale", 1.0)))
        internal_mass_transfer = ctx.diffusivity / ctx.half_thickness_m
        surface_mass_transfer = (
            0.0
            if external_mass_transfer == 0.0
            else 1.0 / (1.0 / external_mass_transfer + 1.0 / internal_mass_transfer)
        )
        volume_ratio = float(np.exp(np.clip(y[gas_start + n_g], -50.0, 50.0)))
        dry_loss = np.array([
            0.0,
            ctx.potentials[1].reactant_mass_kg_per_kg_dry,
            ctx.potentials[2].gas_mass_kg_per_kg_dry,
            ctx.potentials[3].gas_mass_kg_per_kg_dry,
        ])
        solid_mass = ctx.rho_dry - ctx.rho_dry * float(np.dot(extents, dry_loss))
        total_porosity = float(np.clip(1.0 - solid_mass / (ctx.true_density * volume_ratio), 1e-9, 1.0))
        open_porosity = max(total_porosity * ctx.connectivity, 1e-9)
        current_pore_concentration = gas / (open_porosity * volume_ratio)
        surface_outflow = surface_mass_transfer * current_pore_concentration * volume_ratio ** (2.0 / 3.0)
        outflow = surface_outflow / ctx.half_thickness_m
        external_h = bc["h_W_m2_K"] * float(ctx.parameters.get("h_scale", 1.0))
        effective_h = 0.0 if external_h == 0.0 else 1.0 / (1.0 / external_h + ctx.half_thickness_m / (3.0 * ctx.conductivity))
        heat_boundary = (
            effective_h * (bc["gas_temperature_K"] - temperature)
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
    solution = solve_ivp(rhs, (0.0, ctx.residence_time_s), y0, method="BDF", t_eval=t_eval, rtol=rtol, atol=atol, max_step=ctx.residence_time_s / 240.0)
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
        {"method": "BDF", "rtol": rtol, "atol": atol, "nfev": int(solution.nfev), "njev": int(solution.njev), "nlu": int(solution.nlu), "wall_time_s": wall, "cells": 1},
    )
