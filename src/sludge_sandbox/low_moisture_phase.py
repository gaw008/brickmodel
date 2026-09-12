"""Reversible low-water sorption, including explicit ideal dry/vacuum limits.

The liquid reference at zero inventory is hypothetical, never an extra water
pool. Singular chemical potentials/entropy rates use named limits, not NaN or
infinity floats. This interface does not assert a finite drying-out time.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import math

from .arlabosse_low_moisture_storage import LowMoistureSorptionStorage, LowMoistureSorptionPoint
from .mass_storage_bridge import require
from .mass_wet_transport import check_thermal_chemical_sources, represented
from .source_wet_storage import _binary
from .water_chemical_potential import WaterChemicalPotential


PHASE_ID='ARLABOSSE_REVERSIBLE_LOW_MOISTURE_PHASE_V1'


@dataclass(frozen=True)
class LowMoistureEquilibrium:
    pure_equilibrium: object
    equilibrium_partial_pressure_pa: float
    phase_enthalpy_difference_j_mol: float
    chemical_potential_residual_j_mol: float | None
    activity: float
    excess_partial_water_enthalpy_j_mol: float
    liquid_reference_scope: str
    source_ids: tuple[str,...]
    model_id: str = PHASE_ID
    material_qualified: bool = False
    training_eligible: bool = False
    model_error: None = None


@dataclass(frozen=True)
class LowMoisturePhaseEvaluation:
    phase_water_mol_s: float
    water_partial_pressure_pa: float
    equilibrium: LowMoistureEquilibrium
    chemical_driving_force_j_mol: float | None
    entropy_production_w_k: float | None
    chemical_drive_state: str
    entropy_state: str
    material_qualified: bool = False
    training_eligible: bool = False
    zero_inventory_assumption: str = 'reversible adsorption without nucleation barrier or hysteresis'


def check_low_moisture_point(storage,chemical,point):
    """Check source/inventory correspondence without another EOS evaluation."""
    require(type(storage) is LowMoistureSorptionStorage and
            type(chemical) is WaterChemicalPotential, 'actual_low_sorption_providers')
    storage._check()
    require(type(point) is LowMoistureSorptionPoint and point.model_identity==storage.model_identity,
            'actual_low_sorption_point_identity')
    check_thermal_chemical_sources(storage,chemical)
    t=_binary(point.temperature_k,positive=True)
    require(storage.temperature_domain_k[0]<=t<=storage.temperature_domain_k[1],
            'low_sorption_point_temperature_domain')
    p,err=F(_binary(point.pressure_pa,positive=True)),F(_binary(point.pressure_error_pa))
    lo,hi=map(F,storage.pressure_domain_pa)
    require(err>=0 and lo<=p-err and p+err<=hi,'low_sorption_point_pressure_domain')
    mechanical=point.fluid.mechanical
    nc=F(_binary(mechanical.liquid_inventory_mol))
    require(nc>=0,'low_sorption_negative_inventory')
    if nc:
        require(F(_binary(mechanical.liquid_pressure_pa,positive=True))==p,
                'low_sorption_point_planar_pressure')
    else:
        require(mechanical.liquid_pressure_pa is None and mechanical.liquid_volume_m3==0,
                'low_sorption_dry_point_has_no_liquid_phase')
    w=nc*F(storage.wet._mass)/F(storage.dry_mass_kg)
    expected=storage.excess.evaluate(t,w)
    mass=F(storage.dry_mass_kg)
    require(point.excess==expected and
            point.excess_internal_energy_j==mass*expected.h_ex_j_kg_dry and
            point.excess_entropy_j_k==mass*expected.s_ex_j_kg_dry_k and
            point.excess_helmholtz_energy_j==point.excess_internal_energy_j-F(t)*point.excess_entropy_j_k,
            'low_sorption_point_excess_mismatch')


def evaluate_low_moisture_phase(storage,chemical,point,water_vapor_mol,transfer_coefficient):
    check_low_moisture_point(storage,chemical,point)
    nv=_binary(water_vapor_mol)
    coefficient=_binary(transfer_coefficient)
    require(nv>=0 and nv==point.fluid.mechanical.gas_inventory_mol['H2O'],
            'low_sorption_vapor_inventory_mismatch')
    require(coefficient>=0,'nonnegative_low_sorption_transfer_coefficient')
    t=point.temperature_k
    volume=_binary(point.gas_volume_m3,positive=True)
    pv=represented(F(nv)*F(chemical.gas_constant_j_mol_k)*F(t)/F(volume))
    # The same pure-liquid standard state is used for positive and zero Nc.
    # At zero it does not assert actual liquid occupancy or a nucleation event.
    pure=chemical.equilibrium_at_liquid_tp(t,point.pressure_pa)
    activity=point.excess.activity
    peq=represented(F(pure.equilibrium_partial_pressure_pa)*F(activity))
    dry=point.fluid.mechanical.liquid_inventory_mol==0
    require((dry and activity==0 and peq==0) or (not dry and 0<activity<=1 and peq>0),
            'low_sorption_activity_inventory_correspondence')
    residual=None
    if peq>0:
        vapor=chemical.ideal_vapor(t,peq)
        residual=math.fsum((pure.liquid.chemical_potential_j_mol,
                            point.excess.mu_ex_j_mol,-vapor.chemical_potential_j_mol))
        require(math.isfinite(residual) and abs(residual)<=1e-7,
                'low_sorption_chemical_equilibrium_residual')
    heat=represented(F(pure.phase_enthalpy_difference_j_mol)-F(point.excess.partial_h_ex_j_mol))
    require(heat>0,'low_sorption_nonpositive_desorption_enthalpy')
    eq=LowMoistureEquilibrium(pure,peq,heat,residual,activity,point.excess.partial_h_ex_j_mol,
        'hypothetical_standard_state_at_zero_inventory' if dry else 'pure_liquid_reference_with_sorption_excess',
        tuple(sorted(set(point.source_ids+pure.source_ids+(PHASE_ID,)))))
    phase=represented(F(coefficient)*(F(peq)-F(pv)))
    if peq>0 and pv>0:
        logarithm=math.log1p((peq-pv)/pv) if abs(peq-pv)<.5*pv else math.log(peq)-math.log(pv)
        mu=represented(F(chemical.gas_constant_j_mol_k)*F(t)*F(logarithm))
        require(peq==pv or mu!=0,'low_sorption_chemical_drive_unresolved')
        entropy=represented(F(phase)*F(mu)/F(t))
        require(entropy>=0,'low_sorption_phase_entropy_negative')
        drive_state='finite'
        entropy_state='finite' if phase else 'no_exchange'
    else:
        mu=None
        drive_state=('both_zero_no_finite_chemical_potential' if peq==pv==0 else
            'minus_infinity_at_zero_inventory' if peq==0 else 'plus_infinity_at_zero_vapor')
        entropy=0. if phase==0 else None
        entropy_state='no_exchange' if phase==0 else 'positive_infinite_boundary_limit'
    storage._check()
    return LowMoisturePhaseEvaluation(phase,pv,eq,mu,entropy,drive_state,entropy_state)
