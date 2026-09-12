"""Local nonideal water exchange paired with the rigid sorption energy model.

The source activity is a conditional pressure extension, not a measured pore
transport law. The kinetic coefficient remains an explicitly declared fixture.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import math

from .arlabosse_rigid_sorption import ArlabosseSorptionPoint, ArlabosseSorptionStorage, _value
from .arlabosse_wet_thermo import W_MIN, W_REF
from .mass_storage_bridge import require
from .mass_wet_transport import (
    WetPhaseEvaluation, check_thermal_chemical_sources, evaluate_wet_phase, represented,
)
from .source_wet_storage import _binary
from .water_chemical_potential import WaterChemicalPotential


@dataclass(frozen=True)
class SorptionEquilibrium:
    pure_equilibrium: object
    equilibrium_partial_pressure_pa: float
    phase_enthalpy_difference_j_mol: float
    chemical_potential_residual_j_mol: float
    activity: float
    excess_partial_water_enthalpy_j_mol: float
    source_ids: tuple[str, ...]
    method_id: str = 'arlabosse_zero_excess_volume_rigid_sorption_phase_v1'
    pressure_extension_model_error: None = None
    qualification: str = 'conditional_sorption_with_manufactured_transport'
    material_qualified: bool = False
    training_eligible: bool = False


def check_sorption_point(storage, chemical, point):
    """Check represented sorption quantities against their actual source model; no EOS."""
    require(type(storage) is ArlabosseSorptionStorage, 'actual_sorption_storage_required')
    require(type(chemical) is WaterChemicalPotential, 'actual_sorption_chemical_provider_required')
    storage._check()
    require(type(point) is ArlabosseSorptionPoint, 'actual_sorption_point_required')
    require(point.model_identity == storage.model_identity, 'sorption_point_identity_mismatch')
    check_thermal_chemical_sources(storage, chemical)
    # A public frozen dataclass can still be copied with dataclasses.replace.
    # Recheck the quantities used by this leaf before any water EOS callback.
    t = _binary(point.temperature_k, positive=True)
    require(storage.temperature_domain_k[0] <= t <= storage.temperature_domain_k[1],
            'sorption_phase_temperature_domain_exit')
    pressure = F(_binary(point.pressure_pa, positive=True))
    error = F(_binary(point.pressure_error_pa))
    plo, phi = map(F, storage.pressure_domain_pa)
    require(error >= 0 and plo <= pressure-error and pressure+error <= phi,
            'sorption_phase_pressure_domain_exit')
    mechanical = point.fluid.mechanical
    require(_binary(mechanical.liquid_pressure_pa, positive=True) == point.pressure_pa,
            'sorption_phase_requires_planar_common_pressure')
    mass = F(storage.wet._mass)
    moisture = F(_binary(mechanical.liquid_inventory_mol, positive=True))*mass/F(storage.dry_mass_kg)
    require(F(W_MIN) <= moisture <= F(W_REF) and
            point.moisture_kg_water_per_kg_dry == float(moisture),
            'sorption_phase_moisture_mismatch_or_domain_exit')
    mu_ex, _, expected_activity, _ = storage.wet._excess(t, float(moisture))
    expected_partial_h = mass*(F(storage.wet._latent_reference)-_value(storage.wet._q, moisture))
    require(point.activity == expected_activity and
            point.excess_chemical_potential_j_mol == float(F(mu_ex)*mass) and
            point.excess_partial_water_enthalpy_j_mol == float(expected_partial_h),
            'sorption_phase_excess_model_mismatch')


def evaluate_sorption_phase(storage, chemical, point, water_vapor_mol,
                             transfer_coefficient, mode):
    """Exchange the SAME water between condensed and vapor inventories.

    U already includes both phase energies and the sorption excess. No latent
    or desorption source is added to the conserved-energy rate a second time.
    """
    require(mode == 'existing_liquid', 'sorption_dry_interface_not_supported')
    require(_binary(transfer_coefficient) >= 0, 'nonnegative_sorption_transfer_coefficient')
    check_sorption_point(storage, chemical, point)
    t = point.temperature_k
    # Reuse its provider/inventory checks and equilibrium at actual pore
    # pressure. A zero coefficient avoids evaluating an unused pure-water rate
    # which can overflow even when the corrected sorption drive is zero.
    pure = evaluate_wet_phase(chemical, point, water_vapor_mol, 0., mode)
    activity = _binary(point.activity, positive=True)
    require(activity <= 1., 'sorption_activity_above_one')
    peq = represented(F(pure.equilibrium.equilibrium_partial_pressure_pa)*F(activity))
    require(peq > 0, 'sorption_equilibrium_pressure_not_representable')
    vapor = chemical.ideal_vapor(t, peq)
    residual = math.fsum((pure.equilibrium.liquid.chemical_potential_j_mol,
                         point.excess_chemical_potential_j_mol,
                         -vapor.chemical_potential_j_mol))
    require(math.isfinite(residual) and abs(residual) <= 1e-7,
            'sorption_chemical_equilibrium_residual')
    q = represented(F(pure.equilibrium.phase_enthalpy_difference_j_mol)
                    - F(point.excess_partial_water_enthalpy_j_mol))
    require(q > 0, 'sorption_nonpositive_desorption_enthalpy')
    eq = SorptionEquilibrium(pure.equilibrium, peq, q, residual, activity,
        point.excess_partial_water_enthalpy_j_mol,
        tuple(sorted(set(pure.equilibrium.source_ids+point.source_ids))))
    pv = pure.water_partial_pressure_pa
    phase = represented(F(transfer_coefficient)*(F(peq)-F(pv)))
    if pv == 0:
        mu = entropy = None  # The ideal-gas chemical potential at zero is not finite.
    else:
        log = math.log1p((peq-pv)/pv) if abs(peq-pv) < .5*pv else math.log(peq)-math.log(pv)
        mu = represented(F(chemical.gas_constant_j_mol_k)*F(t)*F(log))
        require(peq == pv or mu != 0, 'sorption_chemical_drive_unresolvable')
        entropy = represented(F(phase)*F(mu)/F(t))
        require(entropy >= 0, 'sorption_phase_direction_entropy')
    storage._check()
    return WetPhaseEvaluation(phase, pv, eq, mu, entropy)
