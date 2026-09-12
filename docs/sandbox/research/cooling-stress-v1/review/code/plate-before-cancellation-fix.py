"""Manufactured constant-coefficient thermoelastic half-plate in reference geometry.

The supplied temperatures belong to one half of a mirror-symmetric plate. A
common in-plane strain enforces zero membrane force, with plane stress and no
bending. This declaration cannot infer symmetry of an unprovided other half.
Temperature is the state; no conserved-energy host, water EOS or reaction is used.
"""
from dataclasses import dataclass, field
import math
from numbers import Real

from .exchanges import ExchangeError, conduction_rate_w
from .geometry import ReferenceSlab


class ThermoelasticPlateError(ValueError):
    """Input or arithmetic leaves the explicitly declared thermoelastic domain."""


def _number(value, name, *, positive=False, nonnegative=False):
    try:
        valid = isinstance(value, Real) and not isinstance(value, bool)
        value = float(value) if valid else math.nan
    except (ValueError, OverflowError) as exc:
        raise ThermoelasticPlateError(f"invalid_{name}") from exc
    if not math.isfinite(value) or (positive and value <= 0.) or (nonnegative and value < 0.):
        raise ThermoelasticPlateError(f"invalid_{name}")
    return value


def _sum(values, name):
    try:
        return _number(math.fsum(values), name)
    except (OverflowError, ValueError) as exc:
        raise ThermoelasticPlateError(f"unrepresentable_{name}") from exc


def _bounds(values, name, *, positive=False):
    try:
        pair = tuple(_number(x, name, positive=positive) for x in values)
    except TypeError as exc:
        raise ThermoelasticPlateError(f"invalid_{name}") from exc
    if len(pair) != 2 or pair[0] >= pair[1]:
        raise ThermoelasticPlateError(f"invalid_{name}")
    return pair


@dataclass(frozen=True, slots=True)
class ThermoelasticPoint:
    temperature_k: float
    in_plane_strain: float
    elastic_strain: float
    stress_pa: float
    helmholtz_j_m3: float
    internal_energy_j_m3: float
    entropy_j_m3_k: float
    fixed_strain_heat_capacity_j_m3_k: float


@dataclass(frozen=True, slots=True)
class CoolingPlateEvaluation:
    temperatures_k: tuple[float, ...]
    reference_cell_volumes_m3: tuple[float, ...]
    points: tuple[ThermoelasticPoint, ...]
    in_plane_strain: float
    in_plane_strain_rate_per_s: float
    temperature_rates_k_s: tuple[float, ...]
    face_heat_outward_w: tuple[float, ...]
    cell_heat_in_w: tuple[float, ...]
    cell_mechanical_power_w: tuple[float, ...]
    cell_u_rates_j_m3_s: tuple[float, ...]
    cell_s_rates_j_m3_k_s: tuple[float, ...]
    external_heat_in_w: float
    reservoir_entropy_rate_w_k: float
    face_entropy_production_w_k: tuple[float, ...]
    total_internal_energy_j: float
    total_helmholtz_energy_j: float
    total_entropy_j_k: float
    total_internal_energy_rate_w: float
    total_entropy_rate_w_k: float
    total_mechanical_power_w: float
    total_entropy_production_w_k: float
    ledger_scope: str = field(default="reference_half_slab", init=False)
    full_slab_mirror_factor: int = field(default=2, init=False)
    material_qualified: bool = field(default=False, init=False)
    qualification: str = field(default="manufactured_constant_coefficient_symmetric_free_plane_stress", init=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class CoolingThermoelasticPlate:
    """No coefficient or mechanical/boundary-domain default is supplied.

    C is heat capacity per reference volume on the stress-free path, not at
    fixed strain. strain_bounds apply to common strain, thermal eigenstrain,
    and elastic mismatch; their small-strain adequacy is a declared assumption.

    fixed_temperature means the *outer surface* itself is at outer_temperature_k,
    with conductive distance half a cell and no film resistance. adiabatic turns
    that one face off. The center face is always insulated. All energy/entropy
    accounts cover the half-plate, distinct from the two in-plane work directions.
    """
    reference: ReferenceSlab
    biaxial_modulus_pa: float
    linear_expansion_per_k: float
    stress_free_heat_capacity_j_m3_k: float
    reference_temperature_k: float
    conductivity_w_m_k: float
    temperature_bounds_k: tuple[float, float]
    strain_bounds: tuple[float, float]
    outer_temperature_k: float
    outer_boundary: str
    coefficient_classification: str
    mechanical_regime: str
    _width_m: float = field(init=False, repr=False)
    _volume_m3: float = field(init=False, repr=False)
    _m_alpha: float = field(init=False, repr=False)
    _b: float = field(init=False, repr=False)

    def __post_init__(self):
        if type(self.reference) is not ReferenceSlab:
            raise ThermoelasticPlateError("explicit_reference_slab_required")
        if type(self.coefficient_classification) is not str or self.coefficient_classification != "manufactured":
            raise ThermoelasticPlateError("explicit_manufactured_coefficients_required")
        if type(self.mechanical_regime) is not str or self.mechanical_regime != "symmetric_free_plane_stress":
            raise ThermoelasticPlateError("symmetric_free_plane_stress_required")
        if type(self.outer_boundary) is not str or self.outer_boundary not in ("fixed_temperature", "adiabatic"):
            raise ThermoelasticPlateError("explicit_supported_outer_boundary_required")
        for name in ("biaxial_modulus_pa", "stress_free_heat_capacity_j_m3_k",
                     "reference_temperature_k", "outer_temperature_k"):
            object.__setattr__(self, name, _number(getattr(self, name), name, positive=True))
        object.__setattr__(self, "linear_expansion_per_k", _number(self.linear_expansion_per_k, "linear_expansion"))
        object.__setattr__(self, "conductivity_w_m_k", _number(self.conductivity_w_m_k, "conductivity", nonnegative=True))
        temperature_bounds = _bounds(self.temperature_bounds_k, "temperature_bounds", positive=True)
        strain_bounds = _bounds(self.strain_bounds, "strain_bounds")
        if not temperature_bounds[0] <= self.reference_temperature_k <= temperature_bounds[1]:
            raise ThermoelasticPlateError("reference_temperature_outside_domain")
        if not strain_bounds[0] <= 0. <= strain_bounds[1]:
            raise ThermoelasticPlateError("reference_zero_strain_outside_domain")
        object.__setattr__(self, "temperature_bounds_k", temperature_bounds)
        object.__setattr__(self, "strain_bounds", strain_bounds)
        width = _number(self.reference.half_thickness_m / self.reference.cells, "cell_width", positive=True)
        volume = _number(width * self.reference.reference_area_m2, "reference_cell_volume", positive=True)
        # Multiplication in this order avoids squaring a tiny alpha first.
        m_alpha = _number(self.biaxial_modulus_pa * self.linear_expansion_per_k, "M_alpha")
        b = _number(m_alpha * self.linear_expansion_per_k, "M_alpha_squared", nonnegative=True)
        if self.linear_expansion_per_k != 0. and (m_alpha == 0. or b == 0.):
            raise ThermoelasticPlateError("unrepresentable_thermoelastic_coupling")
        object.__setattr__(self, "_width_m", width)
        object.__setattr__(self, "_volume_m3", volume)
        object.__setattr__(self, "_m_alpha", m_alpha)
        object.__setattr__(self, "_b", b)
        # The declared whole temperature domain must retain positive Ce.
        self._ce(temperature_bounds[1])

    def _ce(self, temperature):
        value = self.stress_free_heat_capacity_j_m3_k - 2. * (self._b * temperature)
        return _number(value, "fixed_strain_heat_capacity", positive=True)

    def _strain(self, value, name):
        value = _number(value, name)
        if not self.strain_bounds[0] <= value <= self.strain_bounds[1]:
            raise ThermoelasticPlateError(f"{name}_outside_strain_domain")
        return value

    def constitutive_point(self, temperature_k, in_plane_strain) -> ThermoelasticPoint:
        """Independent T,e point; e=0 is in-plane restrained, still plane stress."""
        temperature = _number(temperature_k, "temperature", positive=True)
        if not self.temperature_bounds_k[0] <= temperature <= self.temperature_bounds_k[1]:
            raise ThermoelasticPlateError("temperature_outside_domain")
        strain = self._strain(in_plane_strain, "in_plane_strain")
        delta = temperature - self.reference_temperature_k
        eigenstrain = self._strain(self.linear_expansion_per_k * delta, "thermal_eigenstrain")
        mismatch = self._strain(strain - eigenstrain, "elastic_strain")
        ce = self._ce(temperature)
        stress = _number(self.biaxial_modulus_pa * mismatch, "stress")
        log_ratio = (math.log1p(delta / self.reference_temperature_k)
                     if abs(delta) <= .5 * self.reference_temperature_k
                     else math.log(temperature) - math.log(self.reference_temperature_k))
        c = self.stress_free_heat_capacity_j_m3_k
        elastic_free_energy = _number(stress * mismatch, "elastic_free_energy", nonnegative=True)
        psi = _sum((c * (delta - temperature * log_ratio), elastic_free_energy), "helmholtz")
        entropy_coupling = _number(2. * self._m_alpha * mismatch, "entropy_coupling")
        entropy = _sum((c * log_ratio, entropy_coupling), "entropy")
        # This equivalent form avoids cancellation of two large M alpha^2 T^2
        # terms near the reference state. Elastic free energy alone is not u.
        internal = _sum((c * delta, elastic_free_energy, temperature * entropy_coupling), "internal_energy")
        return ThermoelasticPoint(temperature, strain, mismatch, stress, psi, internal, entropy, ce)

    def evaluate(self, temperatures_k) -> CoolingPlateEvaluation:
        """Jointly solve common strain rate and temperature rates at this stage.

        face_heat_outward_w[f] is positive in +z (center toward outer surface).
        Each shared internal face is computed once. Q_i=F_i-F_(i+1), while
        external_heat_in_w=-F_outer. Mechanical transfer is reported separately.
        """
        try:
            temperatures = tuple(_number(t, "temperature", positive=True) for t in temperatures_k)
        except TypeError as exc:
            raise ThermoelasticPlateError("one_temperature_per_half_slab_cell_required") from exc
        cells = self.reference.cells
        if len(temperatures) != cells:
            raise ThermoelasticPlateError("one_temperature_per_half_slab_cell_required")
        # Anchoring the mean makes exactly uniform input exactly stress free.
        centered_mean = _sum(((t - temperatures[0]) / cells for t in temperatures), "centered_mean_temperature")
        average = _sum((temperatures[0], centered_mean), "mean_temperature")
        strain = self._strain(self.linear_expansion_per_k * (average - self.reference_temperature_k), "in_plane_strain")
        points = tuple(self.constitutive_point(t, strain) for t in temperatures)
        k, area, width = self.conductivity_w_m_k, self.reference.reference_area_m2, self._width_m
        faces = [0.]
        try:
            for left, right in zip(temperatures[:-1], temperatures[1:]):
                faces.append(conduction_rate_w(
                    left, right, area_m2=area, left_distance_m=width / 2.,
                    right_distance_m=width / 2., left_conductivity_w_m_k=k,
                    right_conductivity_w_m_k=k,
                ))
            # The same material's two quarter-cell resistances sum to the one
            # physical center-to-surface half-cell distance; no exterior layer.
            outer = 0. if self.outer_boundary == "adiabatic" else conduction_rate_w(
                temperatures[-1], self.outer_temperature_k, area_m2=area,
                left_distance_m=width / 4., right_distance_m=width / 4.,
                left_conductivity_w_m_k=k, right_conductivity_w_m_k=k,
            )
        except ExchangeError as exc:
            raise ThermoelasticPlateError(str(exc)) from exc
        faces.append(outer)
        heat = tuple(_sum((left, -right), "cell_heat") for left, right in zip(faces[:-1], faces[1:]))
        volume = self._volume_m3
        q = tuple(_number(value / volume, "volumetric_heat_rate") for value in heat)
        ce = tuple(p.fixed_strain_heat_capacity_j_m3_k for p in points)
        coupling = tuple(_number(2. * (self._b * t), "thermal_coupling", nonnegative=True) for t in temperatures)
        numerator = _sum((qq / dd / cells for qq, dd in zip(q, ce)), "mean_rate_numerator")
        correction = _sum((cc / dd / cells for cc, dd in zip(coupling, ce)), "mean_rate_correction")
        denominator = _sum((1., correction), "mean_rate_denominator")
        mean_rate = _number(numerator / denominator, "mean_temperature_rate")
        rates = tuple(_number((qq - cc * mean_rate) / dd, "temperature_rate") for qq, cc, dd in zip(q, coupling, ce))
        strain_rate = _number(self.linear_expansion_per_k * mean_rate, "in_plane_strain_rate")
        power = tuple(_number(2. * volume * p.stress_pa * strain_rate, "local_mechanical_power") for p in points)
        # These derivatives come from u(T,e) and s(T,e), independently of Q+P.
        u_strain_derivative = _number(2. * _sum((self.biaxial_modulus_pa * strain,
            self._m_alpha * self.reference_temperature_k), "u_strain_base"), "u_strain_derivative")
        u_rates = tuple(_sum((dd * td, u_strain_derivative * strain_rate), "u_rate") for dd, td in zip(ce, rates))
        s_rates = tuple(_sum((dd / t * td, 2. * self._m_alpha * strain_rate), "s_rate") for dd, t, td in zip(ce, temperatures, rates))
        face_entropy = [0.]
        for flux, left, right in zip(faces[1:-1], temperatures[:-1], temperatures[1:]):
            face_entropy.append(_number(flux * ((left - right) / left) / right, "internal_entropy_production", nonnegative=True))
        face_entropy.append(_number(outer * ((temperatures[-1] - self.outer_temperature_k) / temperatures[-1]) / self.outer_temperature_k, "boundary_entropy_production", nonnegative=True))
        return CoolingPlateEvaluation(
            temperatures_k=temperatures,
            reference_cell_volumes_m3=(volume,) * cells,
            points=points, in_plane_strain=strain,
            in_plane_strain_rate_per_s=strain_rate,
            temperature_rates_k_s=rates, face_heat_outward_w=tuple(faces),
            cell_heat_in_w=heat, cell_mechanical_power_w=power,
            cell_u_rates_j_m3_s=u_rates, cell_s_rates_j_m3_k_s=s_rates,
            external_heat_in_w=-outer,
            reservoir_entropy_rate_w_k=_number(outer / self.outer_temperature_k, "reservoir_entropy_rate"),
            face_entropy_production_w_k=tuple(face_entropy),
            total_internal_energy_j=_sum((volume * p.internal_energy_j_m3 for p in points), "total_internal_energy"),
            total_helmholtz_energy_j=_sum((volume * p.helmholtz_j_m3 for p in points), "total_helmholtz"),
            total_entropy_j_k=_sum((volume * p.entropy_j_m3_k for p in points), "total_entropy"),
            total_internal_energy_rate_w=_sum((volume * value for value in u_rates), "total_internal_energy_rate"),
            total_entropy_rate_w_k=_sum((volume * value for value in s_rates), "total_entropy_rate"),
            total_mechanical_power_w=_sum(power, "total_mechanical_power"),
            total_entropy_production_w_k=_sum(face_entropy, "total_entropy_production"),
        )
