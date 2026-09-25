"""Condensed-water exchange from recorded full mu/h and declared mobility.

This reuses the entropy-force algebra of sorption_moisture_face, with an
explicit mobility rather than a borrowed total-loss diffusivity divided by a
thermodynamic factor. No additional heat conduction or latent source is added.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CondensedExchange:
    molar_flow_mol_s: float
    carried_energy_w: float
    entropy_production_w_k: float
    driving_force_j_mol_k: float
    face_partial_enthalpy_j_mol: float
    mobility_mol2_k_j_s: float


def condensed_exchange(left, right, *, area_m2, distance_m, mobility_density_mol2_k_j_s_m):
    tl,tr=left['temperature_k'],right['temperature_k']
    ml,mr=left['condensed_chemical_potential_j_mol'],right['condensed_chemical_potential_j_mol']
    hf=(left['condensed_partial_enthalpy_j_mol']+right['condensed_partial_enthalpy_j_mol'])/2
    force=math.fsum((ml/tl,-mr/tr,hf*(1/tr-1/tl)))
    mobility=area_m2/distance_m*mobility_density_mol2_k_j_s_m
    flow=mobility*force
    return CondensedExchange(flow,hf*flow,mobility*force*force,force,hf,mobility)


@dataclass(frozen=True)
class SharedSpeciesExchange:
    net_mol_s: dict


@dataclass(frozen=True)
class CoupledFaceRate:
    exchange: SharedSpeciesExchange
    energy_out_w: float
    gas_face: object
    condensed_face: CondensedExchange


def combine_faces(gas_face, condensed_face):
    rates=dict(gas_face.exchange.net_mol_s)
    rates['H2O']=math.fsum((rates['H2O'],condensed_face.molar_flow_mol_s))
    return CoupledFaceRate(SharedSpeciesExchange(rates),
        math.fsum((gas_face.energy_out_w,condensed_face.carried_energy_w)),gas_face,condensed_face)
