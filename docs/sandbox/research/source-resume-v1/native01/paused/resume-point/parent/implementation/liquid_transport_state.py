"""Adapt an already decoded planar mechanical state to liquid face transport."""
from fractions import Fraction
import math
from .liquid_transport import LiquidTransportState,LiquidTransportError
from .phase_storage import LiquidWaterPhase
from .rigid_water_gas import RigidWaterGasState,RigidWaterGas
from .water_properties import WaterState,is_water_provider


def _require(condition,reason):
    if not condition:raise LiquidTransportError(reason)


def _binary(value,*,positive=False):
    _require(type(value) in (int,float,Fraction),'finite_decoded_number_required')
    try:converted=float(value)
    except (OverflowError,ValueError) as exc:raise LiquidTransportError('finite_decoded_number_required') from exc
    _require(math.isfinite(converted) and (converted>0 if positive else converted>=0),'invalid_decoded_number')
    _require(Fraction(value)==Fraction(converted),'decoded_input_not_exact_binary64')
    return converted


def decoded_liquid_state(mechanical: RigidWaterGasState, water: object, *,
                         available_pore_volume_m3: float,
                         pressure_error_pa: float) -> LiquidTransportState:
    """Use the decoded T and planar liquid P, without another energy inverse.

    The caller supplies the actual nominal available volume and its complete
    pressure bound, including any solid/volume uncertainty. This remains a
    fixed-decoded-temperature interval, not a full inverse direction proof.
    Dry states never request liquid TP or invent liquid volume/enthalpy data.
    """
    _require(type(mechanical) is RigidWaterGasState,'actual_decoded_mechanical_state_required')
    _require(is_water_provider(water),'source_gated_water_required')
    _require(dict(mechanical.source_asset_sha256)==dict(water.source_asset_sha256)
             and set(water.source_ids).issubset(mechanical.source_ids),'decoded_water_source_mismatch')
    _require(mechanical.gas_constant_j_mol_k==RigidWaterGas.gas_constant_j_mol_k
             and mechanical.liquid_native_molar_gas_constant_j_mol_k==water.reference.native_molar_gas_constant_j_mol_k,'decoded_water_gas_constant_mismatch')
    _require(mechanical.assumption=='planar_interface_no_capillary_pressure','decoded_planar_interface_required')
    t=_binary(mechanical.temperature_k,positive=True)
    p=_binary(mechanical.pressure_pa,positive=True)
    liquid=_binary(mechanical.liquid_inventory_mol)
    vl=_binary(mechanical.liquid_volume_m3)
    vg=_binary(mechanical.gas_volume_m3,positive=True)
    available=_binary(available_pore_volume_m3,positive=True)
    error=_binary(pressure_error_pa)
    # The closure forms Vg by rounded subtraction of Vl from Vavailable.
    # Compare exact represented operands with a one-ulp subtraction allowance;
    # do not reject a rounded sum above nominal, and never clip either volume.
    volume_rounding=Fraction(math.ulp(vg))
    _require(abs(Fraction(vl)+Fraction(vg)-Fraction(available))<=volume_rounding,'decoded_available_volume_mismatch')
    lo,hi=mechanical.pressure_bracket_pa
    _binary(lo,positive=True);_binary(hi,positive=True)
    _require(Fraction(lo)<=Fraction(p)-Fraction(error)<=Fraction(p)+Fraction(error)<=Fraction(hi),'decoded_pressure_uncertainty_outside_domain')
    if liquid==0:
        _require(vl==0 and mechanical.liquid_pressure_pa is None,'decoded_dry_liquid_state_mismatch')
    else:
        _require(vl>0 and _binary(mechanical.liquid_pressure_pa,positive=True)==p,'decoded_planar_pressure_mismatch')
    volume=enthalpy=None
    if liquid>0:
        point=water.state_tp(t,mechanical.liquid_pressure_pa,phase='liquid')
        _require(type(point) is WaterState and point.reference==water.reference
                 and point.temperature_k==t and point.pressure_pa==mechanical.liquid_pressure_pa,'decoded_liquid_tp_mismatch')
        volume=point.molar_mass_kg_mol/point.density_kg_m3
        enthalpy=point.enthalpy_j_mol
    return LiquidTransportState(temperature_k=mechanical.temperature_k,
        pressure_pa=mechanical.pressure_pa,inventory_mol=mechanical.liquid_inventory_mol,
        saturation=mechanical.liquid_volume_m3/available_pore_volume_m3,
        pressure_error_pa=pressure_error_pa,molar_volume_m3_mol=volume,
        enthalpy_j_mol=enthalpy,metadata=LiquidWaterPhase(water).metadata,
        provider_id=('iapws95_real_fluid_helmholtz' if water.implementation is None else water.implementation.provider_id),
        provider_version=('1.5.5' if water.implementation is None else water.implementation.provider_version),
        source_asset_sha256=tuple(sorted(water.source_asset_sha256.items())))
