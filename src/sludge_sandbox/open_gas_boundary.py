"""Shared outward gas/enthalpy exchange with an explicit ideal-gas reservoir.

Transport coefficients are supplied, not inferred material properties. Diffusion
uses the existing mass-frame correction, advection the existing Darcy donor.
The caller supplies one molar enthalpy reference for every energy-bearing flow
and for its stored internal energy. No phase-change heat is added here.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from fractions import Fraction
import math

from .exchanges import conduction_rate_w
from .gas_transport import GasFaceExchange, GasState, face_exchange


@dataclass(frozen=True)
class GasBoundaryTransfer:
    area_m2: float
    cell_distance_m: float
    reservoir_distance_m: float
    cell_conductivity_w_m_k: float
    reservoir_conductivity_w_m_k: float
    effective_diffusivities_m2_s: Mapping[str, float]
    permeability_m2: float
    relative_permeability: float
    viscosity_pa_s: float


@dataclass(frozen=True)
class OpenGasBoundaryRate:
    exchange: GasFaceExchange
    conduction_out_w: float
    diffusive_enthalpy_out_w: Mapping[str, float]
    advective_enthalpy_out_w: Mapping[str, float]
    energy_out_w: float


def open_gas_boundary_rate(
    cell: GasState,
    reservoir: GasState,
    transfer: GasBoundaryTransfer,
    enthalpy_j_mol: Callable[[str, float], float],
) -> OpenGasBoundaryRate:
    """Positive rates leave the cell; counterdiffusion retains species signs.

    Both sides use the same supplied caloric function. Its domains and energy
    reference must match the host. The heat path is an explicit two-resistance
    model, not a resolved oven or a measured convection coefficient.
    """
    dl, dr = transfer.cell_distance_m, transfer.reservoir_distance_m
    exchange = face_exchange(
        cell, reservoir, area_m2=transfer.area_m2, distance_m=dl+dr,
        face_left_weight=dr/(dl+dr),
        effective_diffusivities_m2_s=transfer.effective_diffusivities_m2_s,
        permeability_m2=transfer.permeability_m2,
        relative_permeability=transfer.relative_permeability,
        viscosity_pa_s=transfer.viscosity_pa_s,
    )
    diffuse = {
        key: rate*enthalpy_j_mol(key, exchange.face_temperature_k) if rate else 0.0
        for key, rate in exchange.diffusive_mol_s.items()
    }
    advect = {
        key: rate*enthalpy_j_mol(key, exchange.advective_donor_temperature_k) if rate else 0.0
        for key, rate in exchange.advective_mol_s.items()
    }
    heat = conduction_rate_w(
        cell.temperature_k, reservoir.temperature_k, area_m2=transfer.area_m2,
        left_distance_m=dl, right_distance_m=dr,
        left_conductivity_w_m_k=transfer.cell_conductivity_w_m_k,
        right_conductivity_w_m_k=transfer.reservoir_conductivity_w_m_k,
    )
    energy = math.fsum((heat, *diffuse.values(), *advect.values()))
    return OpenGasBoundaryRate(exchange, heat, diffuse, advect, energy)


@dataclass(frozen=True)
class OpenGasUpdate:
    amounts_mol: Mapping[str, float]
    internal_energy_j: float
    outward_amounts_mol: Mapping[str, Fraction]
    outward_energy_j: Fraction
    amount_projection_mol: Mapping[str, Fraction]
    energy_projection_j: Fraction


def apply_open_gas_rate(
    amounts_mol: Mapping[str, float], internal_energy_j: float,
    rate: OpenGasBoundaryRate, duration_s: Fraction,
) -> OpenGasUpdate:
    """Apply a supplied frozen rate once, retaining binary projection errors.

    This is inventory bookkeeping, not positivity control or a time-step policy.
    The caller must use a positive interval that remains in its physical domain.
    Inventory keys must cover the same species as the rate. A midpoint driver
    applies its accepted rate to the old accepted state.
    """
    outward = {key: duration_s*Fraction(rate.exchange.net_mol_s[key]) for key in amounts_mol}
    targets = {key: Fraction(amount)-outward[key] for key, amount in amounts_mol.items()}
    amounts = {key: float(value) for key, value in targets.items()}
    energy_out = duration_s*Fraction(rate.energy_out_w)
    target_energy = Fraction(internal_energy_j)-energy_out
    energy = float(target_energy)
    return OpenGasUpdate(
        amounts, energy, outward, energy_out,
        {key: Fraction(amounts[key])-value for key, value in targets.items()},
        Fraction(energy)-target_energy,
    )
