"""Fixed-inventory fluid storage along actual planar mechanical closure.

Inversion is conditional on an explicit domain-wide numerical error envelope.
Local response derivatives are checked, never promoted to interval bounds.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Real
from types import MappingProxyType

from .joined_water_vapor import JoinedWaterVapor
from .phase_storage import IdealGasPhase, InversePolicy
from .rigid_water_gas import RigidWaterGas, RigidWaterGasState


class RigidStorageError(ValueError):
    """Invalid identity/domain or a conditional numerical contract failed."""


def _num(x, name, *, positive=False, nonnegative=False):
    try:
        v = float(x) if isinstance(x, Real) and not isinstance(x, bool) else math.nan
    except (OverflowError, ValueError):
        v = math.nan
    if not math.isfinite(v) or (positive and v <= 0) or (nonnegative and v < 0):
        raise RigidStorageError('invalid_' + name)
    return v


def _sum(values):
    try:
        return _num(math.fsum(values), 'finite_sum')
    except OverflowError as exc:
        raise RigidStorageError('sum_overflow') from exc


def _directed(value, *, upper):
    """Outward conversion of a nonnegative exact represented-input expression."""
    try:
        result = _num(float(value), 'bound_arithmetic', nonnegative=True)
    except OverflowError as exc:
        raise RigidStorageError('bound_overflow') from exc
    if (upper and Fraction(result) < value) or (not upper and Fraction(result) > value):
        result = math.nextafter(result, math.inf if upper else -math.inf)
    return _num(result, 'directed_bound', nonnegative=True)


def _product_upper(*values):
    result = Fraction(1)
    for value in values:
        result *= Fraction(value)
    return _directed(result, upper=True)


def _sum_upper(values):
    return _directed(sum((Fraction(v) for v in values), Fraction()), upper=True)


def _range(value):
    if not isinstance(value, tuple) or len(value) != 2:
        raise RigidStorageError('explicit_range_required')
    lo, hi = (_num(x, 'range', positive=True) for x in value)
    if lo >= hi:
        raise RigidStorageError('invalid_range')
    return lo, hi


@dataclass(frozen=True)
class DeclaredNumericalEnvelope:
    temperature_range_k: tuple[float, float]
    pressure_range_pa: tuple[float, float]
    liquid_u_error_j_mol: float
    liquid_v_error_m3_mol: float
    liquid_abs_du_dp_bound_j_mol_pa: float
    gas_u_error_j_mol: Mapping[str, float]
    gas_cv_lower_j_mol_k: Mapping[str, float]
    method: str
    source_ids: tuple[str, ...]

    def __post_init__(self):
        _range(self.temperature_range_k)
        _range(self.pressure_range_pa)
        for name in ('liquid_u_error_j_mol', 'liquid_v_error_m3_mol',
                     'liquid_abs_du_dp_bound_j_mol_pa'):
            _num(getattr(self, name), name, nonnegative=True)
        for name in ('gas_u_error_j_mol', 'gas_cv_lower_j_mol_k'):
            values = getattr(self, name)
            if not isinstance(values, Mapping) or not values:
                raise RigidStorageError('explicit_gas_error_contract_required')
            copied = {}
            for key, value in values.items():
                if not isinstance(key, str) or not key.strip():
                    raise RigidStorageError('invalid_species_key')
                copied[key] = _num(value, name, positive=name == 'gas_cv_lower_j_mol_k', nonnegative=True)
            object.__setattr__(self, name, MappingProxyType(copied))
        if (not isinstance(self.method, str) or not self.method.strip()
                or not isinstance(self.source_ids, tuple) or not self.source_ids
                or any(not isinstance(s, str) or not s.strip() for s in self.source_ids)
                or len(set(self.source_ids)) != len(self.source_ids)):
            raise RigidStorageError('numerical_method_and_sources_required')


@dataclass(frozen=True)
class ClosedStorageState:
    mechanical: RigidWaterGasState
    internal_energy_j: float
    enthalpy_j: float
    closed_heat_capacity_j_k: float
    minimum_heat_capacity_j_k: float
    energy_roundoff_j: float
    pressure_error_bound_pa: float
    energy_error_bound_j: float
    source_ids: tuple[str, ...]
    envelope: DeclaredNumericalEnvelope
    qualification: str = 'conditional_on_declared_domain_wide_numerical_bounds_not_independently_admitted'
    energy_scope: str = 'fixed_inventory_fluid_thermal_storage_no_solid_or_interface_energy'


@dataclass(frozen=True)
class ClosedStorageInverse:
    state: ClosedStorageState
    target_energy_j: float
    energy_residual_j: float
    temperature_error_bound_k: float
    final_temperature_bracket_k: tuple[float, float]
    iterations: int
    policy: InversePolicy


def liquid_pressure_error_bound(state: RigidWaterGasState,
                               envelope: DeclaredNumericalEnvelope,
                               gas_constant: float) -> float:
    """Original residual/compliance bound on the declared stable wet branch."""
    total_n = sum((Fraction(n) for n in state.gas_inventory_mol.values()), Fraction())
    bmin = _num(_directed(total_n * Fraction(gas_constant) * Fraction(state.temperature_k)
                          / Fraction(envelope.pressure_range_pa[1])**2,
                          upper=False), 'pressure_slope_lower_bound', positive=True)
    eps_f = _sum_upper((abs(state.volume_residual_m3), state.volume_resolution_m3,
                        _product_upper(state.liquid_inventory_mol, envelope.liquid_v_error_m3_mol)))
    return _directed(Fraction(eps_f) / Fraction(bmin), upper=True)


@dataclass(frozen=True)
class RigidStorage:
    mechanical: RigidWaterGas
    gas_phases: Mapping[str, IdealGasPhase]
    envelope: DeclaredNumericalEnvelope
    allow_manufactured: bool = False

    def __post_init__(self):
        if type(self.mechanical) is not RigidWaterGas or type(self.envelope) is not DeclaredNumericalEnvelope:
            raise RigidStorageError('explicit_mechanical_and_numerical_contract_required')
        if type(self.allow_manufactured) is not bool or not isinstance(self.gas_phases, Mapping):
            raise RigidStorageError('invalid_provider_configuration')
        ids = set(self.mechanical.gas_species_ids)
        if any(set(x) != ids for x in (self.gas_phases, self.envelope.gas_u_error_j_mol,
                                       self.envelope.gas_cv_lower_j_mol_k)):
            raise RigidStorageError('complete_matching_gas_keys_required')
        for key, phase in self.gas_phases.items():
            if type(phase) is not IdealGasPhase or phase.metadata.species_id != key:
                raise RigidStorageError('identity_bearing_gas_phase_required')
            if phase._curve.gas_constant_j_mol_k != self.mechanical.gas_constant_j_mol_k:
                raise RigidStorageError('gas_constant_mismatch')
            if (phase.metadata.energy_reference_id != 'nist_298.15K_element_standard_formation'
                    or phase.metadata.molar_basis_id != 'mol_of_declared_species'):
                raise RigidStorageError('gas_energy_or_molar_basis_mismatch')
            if key == 'H2O' and phase.molar_mass_kg_mol != self.mechanical.water.reference.molar_mass_kg_mol:
                raise RigidStorageError('water_cross_phase_molar_identity_mismatch')
            if phase.metadata.classification == 'manufactured_test_fixture' and not self.allow_manufactured:
                raise RigidStorageError('manufactured_opt_in_required')
        object.__setattr__(self, 'gas_phases', MappingProxyType(dict(self.gas_phases)))
        lo, hi = self.mechanical.pressure_bracket_pa
        elo, ehi = self.envelope.pressure_range_pa
        if not elo <= lo < hi <= ehi:
            raise RigidStorageError('mechanical_bracket_outside_error_envelope')

    def evaluate_at_temperature(self, temperature_k, liquid_mol, gas_mol):
        t = _num(temperature_k, 'temperature', positive=True)
        if not self.envelope.temperature_range_k[0] <= t <= self.envelope.temperature_range_k[1]:
            raise RigidStorageError('temperature_outside_error_envelope')
        state = self.mechanical.evaluate_at_temperature(t, liquid_mol, gas_mol)
        nl, p = state.liquid_inventory_mol, state.pressure_pa
        r = self.mechanical.gas_constant_j_mol_k
        u_terms, h_terms, cp_terms, rounding, errors, lower = [], [], [], [], [], []
        a, b = state.gas_volume_m3 / t, state.gas_volume_m3 / p
        sources = list(state.source_ids) + list(self.envelope.source_ids)
        if nl:
            response = self.mechanical.water.state_tp_response(t, p, phase='liquid')
            water = response.state
            du_dp = response.molar_du_dp_j_mol_pa
            if abs(du_dp) > self.envelope.liquid_abs_du_dp_bound_j_mol_pa:
                raise RigidStorageError('observed_liquid_pressure_bound_violation')
            u, h = water.internal_energy_j_mol, water.enthalpy_j_mol
            u_terms.append(_num(nl * u, 'liquid_energy'))
            h_terms.append(_num(nl * h, 'liquid_enthalpy'))
            cp_terms.append(nl * water.molar_mass_kg_mol * water.cp_j_kg_k)
            a += nl * response.molar_dv_dt_m3_mol_k
            b -= nl * response.molar_dv_dp_m3_mol_pa
            rounding.extend((_product_upper(nl, math.ulp(u)), math.ulp(u_terms[-1])))
            errors.append(_product_upper(nl, self.envelope.liquid_u_error_j_mol))
        for key, n in state.gas_inventory_mol.items():
            if not n:
                continue
            phase = self.gas_phases[key]
            if type(phase.caloric) is JoinedWaterVapor:
                required_error = phase.caloric.numerical_error(t).internal_energy_error_j_mol
                if self.envelope.gas_u_error_j_mol[key] < required_error:
                    raise RigidStorageError('joined_water_numerical_error_exceeds_declared_gas_budget')
            point = phase.evaluate(t, p)  # total pressure yields additive partial molar volumes
            cp, cv = phase._curve.cp_j_mol_k(t), phase._curve.cv_j_mol_k(t)
            bound = self.envelope.gas_cv_lower_j_mol_k[key]
            if cv < bound:
                raise RigidStorageError('observed_gas_cv_bound_violation')
            lower.append(Fraction(n) * Fraction(bound))
            u_terms.append(_num(n * point.internal_energy_j_mol, 'gas_energy'))
            h_terms.append(_num(n * point.enthalpy_j_mol, 'gas_enthalpy'))
            cp_terms.append(n * cp)
            rounding.extend((_product_upper(n, math.ulp(point.internal_energy_j_mol)), math.ulp(u_terms[-1])))
            errors.append(_product_upper(n, self.envelope.gas_u_error_j_mol[key]))
            sources.extend(phase.metadata.source_ids)
        u, h = _sum(u_terms), _sum(h_terms)
        roundoff = _sum_upper(rounding + [math.ulp(u)])
        cmin = _num(_directed(sum(lower, Fraction()), upper=False),
                    'representable_heat_capacity_lower_bound', positive=True)
        # This lower derivative bound is analytic for the gas volume term.
        if nl:
            eps_p = liquid_pressure_error_bound(state, self.envelope, r)
        else:
            eps_p = _sum_upper((state.pressure_resolution_pa, abs(state.pressure_residual_pa)))
        # The error envelope applies only while the full uncertainty interval stays in domain.
        if nl and not (Fraction(self.mechanical.pressure_bracket_pa[0]) <= Fraction(p) - Fraction(eps_p)
                       and Fraction(p) + Fraction(eps_p) <= Fraction(self.mechanical.pressure_bracket_pa[1])):
            raise RigidStorageError('pressure_uncertainty_outside_envelope')
        errors.extend((roundoff, _product_upper(nl, self.envelope.liquid_abs_du_dp_bound_j_mol_pa, eps_p)))
        error = _sum_upper(errors)
        capacity = _num(_sum(cp_terms) - t * a * a / _num(b, 'compressibility', positive=True),
                        'closed_heat_capacity', positive=True)
        if capacity < cmin:
            raise RigidStorageError('closed_heat_capacity_lower_bound_violation')
        return ClosedStorageState(state, u, h, capacity, cmin, roundoff, eps_p, error,
                                  tuple(dict.fromkeys(sources)), self.envelope)

    def temperature_from_energy(self, target_energy_j, liquid_mol, gas_mol,
                                temperature_bracket_k, policy):
        target = _num(target_energy_j, 'target_energy')
        if type(policy) is not InversePolicy:
            raise RigidStorageError('explicit_inverse_policy_required')
        lo, hi = _range(temperature_bracket_k)
        low = self.evaluate_at_temperature(lo, liquid_mol, gas_mol)
        high = self.evaluate_at_temperature(hi, liquid_mol, gas_mol)
        target_roundoff = math.ulp(target)
        if target < low.internal_energy_j - low.energy_error_bound_j - target_roundoff or target > high.internal_energy_j + high.energy_error_bound_j + target_roundoff:
            raise RigidStorageError('energy_outside_closed_temperature_bracket')
        if not (Fraction(low.internal_energy_j) + Fraction(low.energy_error_bound_j) + Fraction(target_roundoff) < Fraction(target)
                < Fraction(high.internal_energy_j) - Fraction(high.energy_error_bound_j) - Fraction(target_roundoff)):
            raise RigidStorageError('initial_energy_bracket_sign_uncertain')
        middle = lo + (hi - lo) / 2
        for iteration in range(policy.maximum_iterations + 1):
            point = self.evaluate_at_temperature(middle, liquid_mol, gas_mol)
            residual = _sum((point.internal_energy_j, -target))
            budget = _sum_upper((point.energy_error_bound_j, target_roundoff, math.ulp(residual)))
            residual_bound = _sum_upper((abs(residual), budget))
            radius = _directed(Fraction(residual_bound) / Fraction(point.minimum_heat_capacity_j_k), upper=True)
            if (residual_bound <= policy.energy_tolerance_j
                    and radius <= policy.temperature_tolerance_k):
                left = _directed(max(Fraction(lo), Fraction(middle)-Fraction(radius)), upper=False)
                right = _directed(min(Fraction(hi), Fraction(middle)+Fraction(radius)), upper=True)
                return ClosedStorageInverse(point, target, residual, radius,
                                            (left, right),
                                            iteration, policy)
            if budget > policy.energy_tolerance_j or budget / point.minimum_heat_capacity_j_k > policy.temperature_tolerance_k:
                raise RigidStorageError('numerical_envelope_or_representation_exceeds_inverse_tolerance')
            if abs(residual) <= budget:
                raise RigidStorageError('energy_direction_unresolved_by_declared_envelope')
            if middle in (lo, hi):
                raise RigidStorageError('temperature_bracket_unresolvable')
            if residual > 0:
                hi = middle
            else:
                lo = middle
            # A local derivative chooses a trial, never certifies its error.
            # The signed interval and conditional global Cv bound remain the
            # acceptance criteria even when a safeguarded Newton trial is used.
            proposed = middle - residual / point.closed_heat_capacity_j_k
            middle = proposed if math.isfinite(proposed) and lo < proposed < hi else lo + (hi-lo)/2
        raise RigidStorageError('inverse_iteration_limit')
