"""Local mathematical liquid/gas root certificate, not phase admission."""
from dataclasses import dataclass
from decimal import localcontext
from sludge_sandbox.water_interval_eos import Interval, I, pressure_interval


@dataclass(frozen=True)
class RootRectangle:
    temperature: Interval
    liquid_molar_density: Interval
    effective_available_volume: Interval
    pressure: Interval
    lower_residual: Interval
    upper_residual: Interval
    liquid_pressure_derivative: Interval
    total_residual_derivative: Interval
    qualification: str = 'local_unique_mathematical_root_only_not_stable_phase_certificate'


def enclose_local_root(source, source_sha256, *, temperature,
                       liquid_molar_density, effective_available_volume,
                       liquid_mol, gas_mol, gas_constant, liquid_volume_scale, precision=60):
    """Certify a root for every T and effective-volume value in the rectangle.

    F = p_liquid(T,rho) - Ng Rg T / (Veff - Nl*scale/rho).
    Its rho derivative is dp_liquid/drho plus a positive gas-volume term.
    Strict signs at the two density faces and positive derivative throughout
    give one continuous local root for each T,Veff pair. The density bracket
    must be supplied explicitly; neither a native seed nor a sampled sign is
    itself accepted as evidence. Veff may include separately justified bulk
    volume and liquid-volume error intervals; this routine invents neither.
    """
    if type(precision) is not int or precision < 40:
        raise ValueError('explicit_precision_at_least_40')
    if not all(type(v) is Interval for v in
               (temperature, liquid_molar_density, effective_available_volume)):
        raise TypeError('explicit_intervals_required')
    if liquid_molar_density.lo >= liquid_molar_density.hi:
        raise ValueError('nonzero_density_bracket_required')
    # Native molar density uses its own mass convention. Public liquid volume
    # is (M_public/M_native)/rho_native; require that scale explicitly.
    nl, ng, rg, scale = I(liquid_mol), I(gas_mol), I(gas_constant), I(liquid_volume_scale)
    if min(nl.lo, ng.lo, rg.lo, scale.lo) <= 0:
        raise ValueError('strict_positive_liquid_gas_constant_required')
    with localcontext() as ctx:
        ctx.prec = precision
        def gas_pressure(rho):
            volume = effective_available_volume - nl*scale/rho
            if volume.lo <= 0:
                raise ValueError('rectangle_gas_volume_not_positive')
            return ng*rg*temperature/volume
        low = I(liquid_molar_density.lo)
        high = I(liquid_molar_density.hi)
        pl, _ = pressure_interval(source, source_sha256, temperature, low, precision=precision)
        ph, _ = pressure_interval(source, source_sha256, temperature, high, precision=precision)
        fl = pl - gas_pressure(low)
        fh = ph - gas_pressure(high)
        if not (fl.hi < 0 < fh.lo):
            raise ValueError('strict_uniform_root_face_signs_unresolved')
        _, derivative = pressure_interval(source, source_sha256, temperature,
                                          liquid_molar_density, precision=precision)
        volume = effective_available_volume - nl*scale/liquid_molar_density
        total_derivative = derivative + ng*rg*temperature*nl*scale/(liquid_molar_density**2*volume**2)
        if derivative.lo <= 0 or total_derivative.lo <= 0:
            raise ValueError('local_positive_compliance_unresolved')
        return RootRectangle(temperature, liquid_molar_density, effective_available_volume,
            gas_pressure(liquid_molar_density), fl, fh, derivative, total_derivative)
