"""Pure constant-coefficient reference-plate energy map and global inverse.

The defining potential is that of CoolingThermoelasticPlate. Exact represented
binary inputs define the algebraic model; rational arithmetic encloses its
square roots. This does not certify coefficients, geometry or a real material.
There is no time integration, fluid closure, inventory default or state repair.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Sequence
from fractions import Fraction as F
import math
from numbers import Real
import time

from sludge_sandbox.cooling_thermoelastic_plate import (
    CoolingThermoelasticPlate, CoolingPlateEvaluation, ThermoelasticPoint,
    ThermoelasticPlateError,
)


class EnergyStorageError(ValueError):
    """Invalid input or unresolved numerical operation; not a domain event."""


class EnergyDomainError(EnergyStorageError):
    """A supplied state is outside its domain, or no domain solution exists."""


class EnergyResolutionError(EnergyStorageError):
    """The requested existence/precision/representation certificate is unresolved."""


def _number(value, name, *, positive=False, nonnegative=False):
    if not isinstance(value, Real) or isinstance(value, bool):
        raise EnergyStorageError(f'invalid_{name}')
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise EnergyStorageError(f'invalid_{name}') from exc
    if (not math.isfinite(result) or (positive and result <= 0.)
            or (nonnegative and result < 0.)):
        raise EnergyStorageError(f'invalid_{name}')
    return result


def _vector(values, name, *, nonnegative=False):
    try:
        result = tuple(_number(v, name, nonnegative=nonnegative) for v in values)
    except TypeError as exc:
        raise EnergyStorageError(f'invalid_{name}') from exc
    if not result:
        raise EnergyStorageError(f'nonempty_{name}_required')
    return result


def _nearest(value):
    try:
        result = float(value)
    except OverflowError as exc:
        raise EnergyResolutionError('unrepresentable_binary64_output') from exc
    if not math.isfinite(result):
        raise EnergyResolutionError('unrepresentable_binary64_output')
    return result


def _up(value):
    result = _nearest(value)
    return math.nextafter(result, math.inf) if F(result) < value else result


def _down(value):
    result = _nearest(value)
    return math.nextafter(result, -math.inf) if F(result) > value else result


def _sqrt_bounds(value, bits):
    """Exact dyadic enclosure, width at most 2**(-bits), using integer isqrt."""
    if value < 0:
        raise EnergyResolutionError('negative_square_root_argument')
    scale = 1 << bits
    scaled_numerator = value.numerator << (2*bits)
    integer = math.isqrt(scaled_numerator // value.denominator)
    lower = F(integer, scale)
    exact = integer*integer*value.denominator == scaled_numerator
    return lower, lower if exact else F(integer+1, scale)


@dataclass(frozen=True, slots=True)
class EnergyTarget:
    cell_energy_j: tuple[float, ...]
    absolute_error_j: tuple[float, ...]

    def __post_init__(self):
        energy = _vector(self.cell_energy_j, 'target_energy')
        errors = _vector(self.absolute_error_j, 'target_absolute_error', nonnegative=True)
        if len(energy) != len(errors):
            raise EnergyStorageError('target_error_shape_mismatch')
        object.__setattr__(self, 'cell_energy_j', energy)
        object.__setattr__(self, 'absolute_error_j', errors)


@dataclass(frozen=True, slots=True)
class EnergyInversePolicy:
    energy_tolerance_j: float
    temperature_tolerance_k: float
    maximum_iterations: int
    square_root_bits: int

    def __post_init__(self):
        for name in ('energy_tolerance_j','temperature_tolerance_k'):
            object.__setattr__(self, name, _number(getattr(self,name), name, positive=True))
        if type(self.maximum_iterations) is not int or not 1 <= self.maximum_iterations <= 4096:
            raise EnergyStorageError('maximum_iterations_must_be_1_to_4096')
        if type(self.square_root_bits) is not int or not 8 <= self.square_root_bits <= 4096:
            raise EnergyStorageError('square_root_bits_must_be_8_to_4096')


@dataclass(frozen=True, slots=True)
class StrainEnergyState:
    temperatures_k: tuple[float, ...]
    in_plane_strain: float
    cell_energy_j: tuple[float, ...]
    energy_roundoff_bound_j: tuple[float, ...]
    constitutive_points: tuple[ThermoelasticPoint, ...]
    material_qualified: bool = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class FreeEnergyState:
    temperatures_k: tuple[float, ...]
    mean_temperature_k: float
    in_plane_strain: float
    cell_energy_j: tuple[float, ...]
    energy_roundoff_bound_j: tuple[float, ...]
    plate_evaluation: CoolingPlateEvaluation
    plate_energy_difference_bound_j: tuple[float, ...]
    plate_strain_difference_bound: float
    material_qualified: bool = field(default=False, init=False)
    energy_scope: str = field(default='constant_C_thermoelastic_reference_half_plate_total_energy', init=False)


@dataclass(frozen=True, slots=True)
class EnergyInverse:
    state: FreeEnergyState
    target: EnergyTarget
    policy: EnergyInversePolicy
    cell_energy_residual_j: tuple[float, ...]
    energy_residual_abs_bound_j: tuple[float, ...]
    combined_energy_residual_bound_j: tuple[float, ...]
    temperature_error_bound_k: float
    minimum_energy_jacobian_eigenvalue_j_k: float
    mean_temperature_bracket_k: tuple[float, float]
    scalar_residual_interval_k: tuple[float, float]
    iterations: int
    existence_certificate: str
    target_interval_admissible: bool
    elapsed_s: float
    uniqueness: str = field(default='strictly_monotone_global_energy_map_on_declared_temperature_box', init=False)
    representation: str = field(default='actual_returned_binary64_T_recomputed_in_exact_binary_input_energy_map', init=False)


@dataclass(frozen=True, slots=True)
class ThermoelasticEnergyStorage:
    plate: CoolingThermoelasticPlate
    _n: int = field(init=False, repr=False)
    _v: F = field(init=False, repr=False)
    _c: F = field(init=False, repr=False)
    _m: F = field(init=False, repr=False)
    _alpha: F = field(init=False, repr=False)
    _b: F = field(init=False, repr=False)
    _tr: F = field(init=False, repr=False)
    _lo: F = field(init=False, repr=False)
    _hi: F = field(init=False, repr=False)
    _slo: F = field(init=False, repr=False)
    _shi: F = field(init=False, repr=False)
    _dmin: F = field(init=False, repr=False)

    def __post_init__(self):
        if type(self.plate) is not CoolingThermoelasticPlate:
            raise EnergyStorageError('explicit_frozen_plate_required')
        p = self.plate
        # Same represented uniform cell volume used by the frozen plate. Its
        # physical geometry/parameter uncertainty is not inferred to be zero.
        volume = (p.reference.half_thickness_m/p.reference.cells)*p.reference.reference_area_m2
        constants = dict(_n=p.reference.cells, _v=F(volume),
            _c=F(p.stress_free_heat_capacity_j_m3_k), _m=F(p.biaxial_modulus_pa),
            _alpha=F(p.linear_expansion_per_k), _tr=F(p.reference_temperature_k),
            _lo=F(p.temperature_bounds_k[0]), _hi=F(p.temperature_bounds_k[1]),
            _slo=F(p.strain_bounds[0]), _shi=F(p.strain_bounds[1]))
        constants['_b'] = constants['_m']*constants['_alpha']**2
        constants['_dmin'] = constants['_v']*(constants['_c']-2*constants['_b']*constants['_hi'])
        if constants['_dmin'] <= 0:
            raise EnergyStorageError('positive_exact_Ce_lower_bound_required')
        for name,value in constants.items():
            object.__setattr__(self,name,value)
        # The first inverse supports a whole rectangular temperature domain.
        # A narrower correlated strain domain needs a different existence proof;
        # reject that configuration rather than treating a Newton trial as a
        # physical domain event or projecting its strain back into range.
        strain_extrema = (self._alpha*(self._lo-self._tr), self._alpha*(self._hi-self._tr),
                          self._alpha*(self._lo-self._hi), self._alpha*(self._hi-self._lo))
        if any(s < self._slo or s > self._shi for s in strain_extrema):
            raise EnergyStorageError('complete_temperature_box_strain_admissibility_required')

    @property
    def cells(self) -> int:
        """Number of uniform reference half-plate cells."""
        return self._n

    @property
    def reference_cell_volume_m3(self) -> float:
        """Represented fixed volume used by the frozen plate's energy ledger."""
        return float(self._v)

    def _temperatures(self, temperatures):
        values = _vector(temperatures,'temperature')
        if len(values) != self._n:
            raise EnergyStorageError('temperature_shape_mismatch')
        exact = tuple(map(F, values))
        if any(t < self._lo or t > self._hi for t in exact):
            raise EnergyDomainError('temperature_outside_declared_domain')
        return values, exact

    def _check_strains(self, temperatures, strain):
        eigen = tuple(self._alpha*(t-self._tr) for t in temperatures)
        if any(s < self._slo or s > self._shi for s in
               (strain,)+eigen+tuple(strain-s for s in eigen)):
            raise EnergyDomainError('strain_outside_declared_domain')

    def _free_exact(self, temperatures):
        mean = sum(temperatures,F())/self._n
        strain = self._alpha*(mean-self._tr)
        self._check_strains(temperatures,strain)
        energy = tuple(self._v*(self._c*(t-self._tr)+self._b*(mean*mean-t*t)) for t in temperatures)
        return mean,strain,energy

    @staticmethod
    def _rounded_energy(energy):
        represented = tuple(_nearest(e) for e in energy)
        errors = tuple(_up(abs(F(value)-exact)) for value,exact in zip(represented,energy))
        return represented,errors

    def at_strain(self, temperatures_k: Sequence[float], in_plane_strain: float) -> StrainEnergyState:
        """Evaluate total energy at an explicit common strain, without force elimination."""
        values,temperatures = self._temperatures(temperatures_k)
        strain = F(_number(in_plane_strain,'in_plane_strain'))
        self._check_strains(temperatures,strain)
        energy = tuple(self._v*(self._c*(t-self._tr)+self._m*(strain+self._alpha*self._tr)**2
                               -self._b*t*t) for t in temperatures)
        represented,errors = self._rounded_energy(energy)
        try:
            points = tuple(self.plate.constitutive_point(t,float(strain)) for t in values)
        except ThermoelasticPlateError as exc:
            raise EnergyResolutionError(f'final_plate_point_unavailable:{exc}') from exc
        return StrainEnergyState(values,float(strain),represented,errors,points)

    def forward(self, temperatures_k: Sequence[float]) -> FreeEnergyState:
        """Eliminate the common strain and evaluate the actual returned temperature field."""
        values,temperatures = self._temperatures(temperatures_k)
        mean,strain,energy = self._free_exact(temperatures)
        represented,errors = self._rounded_energy(energy)
        try:
            evaluation = self.plate.evaluate(values)
        except ThermoelasticPlateError as exc:
            raise EnergyResolutionError(f'final_plate_stage_unavailable:{exc}') from exc
        differences = tuple(_up(abs(self._v*F(point.internal_energy_j_m3)-exact))
                            for point,exact in zip(evaluation.points,energy))
        strain_difference = _up(abs(F(evaluation.in_plane_strain)-strain))
        return FreeEnergyState(values,_nearest(mean),_nearest(strain),represented,errors,
                               evaluation,differences,strain_difference)

    def _h(self,t):
        return self._c*t-self._b*t*t

    def _h_inverse_bounds(self,y,bits):
        # Feasible scalar interval proves y lies in h([lo,hi]). Exact boundary
        # evaluation preserves a true boundary root; no temperature is clipped.
        if y == self._h(self._lo):
            return self._lo,self._lo
        if y == self._h(self._hi):
            return self._hi,self._hi
        if not self._h(self._lo) < y < self._h(self._hi):
            raise EnergyResolutionError('scalar_trial_outside_proved_feasible_interval')
        low,high = _sqrt_bounds(self._c*self._c-4*self._b*y,bits)
        return 2*y/(self._c+high), 2*y/(self._c+low)

    def _scalar(self,q,x,bits):
        temperatures = tuple(self._h_inverse_bounds(value-self._b*q,bits) for value in x)
        ml,mh = _sqrt_bounds(q,bits)
        f_low = sum((t[0] for t in temperatures),F())/self._n-mh
        f_high = sum((t[1] for t in temperatures),F())/self._n-ml
        return temperatures,(f_low,f_high)

    def _interval_newton(self,qlo,qhi,q,sign,mean_bracket,bits):
        """Intersect a proved root interval with m + F(m)/[-F'].

        The mean-value theorem applies on the whole feasible interval. All
        four signed endpoint quotients are required if F's enclosure crosses
        zero. Dyadic outward rounding bounds rational denominator growth; it
        encloses the exact intersection and never changes a target energy.
        """
        mean_lo = max(self._lo,mean_bracket[0])
        mean_hi = min(self._hi,mean_bracket[1])
        ce_min = self._c-2*self._b*self._hi
        ce_max = self._c-2*self._b*self._lo
        if not 0 < mean_lo <= mean_hi or not 0 < ce_min <= ce_max:
            raise EnergyResolutionError('invalid_interval_newton_domain_bound')
        lower = self._b/ce_max+1/(2*mean_hi)
        upper = self._b/ce_min+1/(2*mean_lo)
        offsets = tuple(value/slope for value in sign for slope in (lower,upper))
        root_lo,root_hi = q+min(offsets),q+max(offsets)
        if root_lo > qhi or root_hi < qlo:
            raise EnergyResolutionError('interval_newton_lost_proved_root')
        scale = 1 << bits
        outward_lo = F((root_lo.numerator*scale)//root_lo.denominator,scale)
        outward_hi = F(-((-root_hi.numerator*scale)//root_hi.denominator),scale)
        return max(qlo,outward_lo),min(qhi,outward_hi)

    def _assess(self, temperatures, target, policy):
        try:
            values,exact_t = self._temperatures(temperatures)
        except EnergyDomainError as exc:
            raise EnergyResolutionError('rounded_scalar_trial_leaves_proved_temperature_box') from exc
        _,strain,energies = self._free_exact(exact_t)
        residuals = tuple(e-F(target_e) for e,target_e in zip(energies,target.cell_energy_j))
        combined = tuple(abs(r)+F(error) for r,error in zip(residuals,target.absolute_error_j))
        _,norm = _sqrt_bounds(sum((value*value for value in combined),F()),policy.square_root_bits)
        # Use the reported, downward-representable capacity in the radius too.
        # Then the returned fields themselves certify norm <= radius*lower;
        # separately rounding exact-dmin and norm/exact-dmin would not compose.
        lower = _down(self._dmin)
        if lower <= 0.:
            raise EnergyResolutionError('capacity_lower_bound_not_representable')
        radius = norm/F(lower)
        budget_ok = (all(value <= F(policy.energy_tolerance_j) for value in combined)
                     and radius <= F(policy.temperature_tolerance_k))
        # With no target uncertainty, existence has already been established by
        # the scalar signs. Otherwise an enclosed ball and strong monotonicity
        # give existence for every target in the stated energy box.
        uncertainty_admitted = True
        if any(target.absolute_error_j):
            strain_radius = abs(self._alpha)*radius
            uncertainty_admitted = all(self._lo <= t-radius and t+radius <= self._hi for t in exact_t)
            strains_and_radii = [(strain,strain_radius)]
            strains_and_radii += [(self._alpha*(t-self._tr),strain_radius) for t in exact_t]
            strains_and_radii += [(strain-self._alpha*(t-self._tr),2*strain_radius) for t in exact_t]
            uncertainty_admitted = uncertainty_admitted and all(
                self._slo <= s-r and s+r <= self._shi for s,r in strains_and_radii)
        return values,residuals,combined,radius,budget_ok,uncertainty_admitted

    def _finish(self, assessment, target, policy, bracket, scalar, iterations, certificate, started):
        values,residuals,combined,radius,budget_ok,admitted = assessment
        if not budget_ok:
            raise EnergyResolutionError('returned_binary64_temperature_cannot_meet_requested_budget')
        if not admitted:
            raise EnergyResolutionError('target_uncertainty_not_certified_inside_domain')
        lower = _down(self._dmin)
        if lower <= 0.:
            raise EnergyResolutionError('capacity_lower_bound_not_representable')
        state = self.forward(values)  # The only full plate evaluation in inverse.
        # Re-evaluate from exactly the returned T, never from a scalar iterate
        # or from a modified target, before returning the final certificate.
        final = self._assess(state.temperatures_k,target,policy)
        if final != assessment:
            raise EnergyResolutionError('final_temperature_reassessment_changed')
        return EnergyInverse(state,target,policy,tuple(_nearest(r) for r in residuals),
            tuple(_up(abs(r)) for r in residuals),tuple(_up(v) for v in combined),
            _up(radius),lower,(_down(bracket[0]),_up(bracket[1])),
            (_down(scalar[0]),_up(scalar[1])),iterations,certificate,True,time.monotonic()-started)

    def inverse(self,target: EnergyTarget,policy: EnergyInversePolicy) -> EnergyInverse:
        """Prove a domain root, then meet residual and target-uncertainty budgets."""
        started = time.monotonic()
        if type(target) is not EnergyTarget or type(policy) is not EnergyInversePolicy:
            raise EnergyStorageError('explicit_target_and_inverse_policy_required')
        if len(target.cell_energy_j) != self._n:
            raise EnergyStorageError('target_shape_mismatch')
        if any(error > policy.energy_tolerance_j for error in target.absolute_error_j):
            raise EnergyResolutionError('target_energy_error_exceeds_requested_budget')
        x = tuple(F(energy)/self._v+self._c*self._tr for energy in target.cell_energy_j)
        if self._b == 0:
            exact_t = tuple(value/self._c for value in x)
            if any(t < self._lo or t > self._hi for t in exact_t):
                raise EnergyDomainError('linear_energy_target_has_no_temperature_domain_solution')
            values = tuple(_nearest(t) for t in exact_t)
            assessment = self._assess(values,target,policy)
            mean = sum(exact_t,F())/self._n
            return self._finish(assessment,target,policy,(mean,mean),(F(),F()),0,
                                'exact_linear_domain_solution',started)
        qlo = max([self._lo*self._lo]+[(value-self._h(self._hi))/self._b for value in x])
        qhi = min([self._hi*self._hi]+[(value-self._h(self._lo))/self._b for value in x])
        if qlo > qhi:
            raise EnergyDomainError('empty_feasible_mean_square_interval')
        endpoints = [self._scalar(qlo,x,policy.square_root_bits),self._scalar(qhi,x,policy.square_root_bits)]
        for q,(t_bounds,sign) in zip((qlo,qhi),endpoints):
            if sign == (F(),F()):
                values = tuple(_nearest((low+high)/2) for low,high in t_bounds)
                assessment = self._assess(values,target,policy)
                bracket = _sqrt_bounds(q,policy.square_root_bits)
                return self._finish(assessment,target,policy,bracket,sign,0,
                                    'exact_scalar_endpoint_root',started)
        lower_sign,upper_sign = endpoints[0][1],endpoints[1][1]
        if lower_sign[1] < 0 or upper_sign[0] > 0:
            raise EnergyDomainError('monotone_scalar_has_no_domain_root')
        if not lower_sign[0] > 0 or not upper_sign[1] < 0:
            raise EnergyResolutionError('domain_existence_endpoint_sign_unresolved')
        previous_values = None
        for iteration in range(1,policy.maximum_iterations+1):
            q = (qlo+qhi)/2
            t_bounds,sign = self._scalar(q,x,policy.square_root_bits)
            values = tuple(_nearest((low+high)/2) for low,high in t_bounds)
            assessment = self._assess(values,target,policy)
            mean_bracket = (_sqrt_bounds(qlo,policy.square_root_bits)[0],
                            _sqrt_bounds(qhi,policy.square_root_bits)[1])
            if assessment[4] and assessment[5]:
                return self._finish(assessment,target,policy,mean_bracket,sign,iteration,
                                    'strict_monotone_scalar_endpoint_bracket',started)
            if sign == (F(),F()):
                return self._finish(assessment,target,policy,_sqrt_bounds(q,policy.square_root_bits),
                                    sign,iteration,'exact_scalar_interior_root',started)
            newlo,newhi = self._interval_newton(qlo,qhi,q,sign,mean_bracket,policy.square_root_bits)
            # The signed half-interval remains a proved bisection fallback if
            # Newton yields no useful contraction. Intersect both certificates.
            if sign[0] > 0:
                newlo = max(newlo,q)
            elif sign[1] < 0:
                newhi = min(newhi,q)
            elif newlo == qlo and newhi == qhi:
                raise EnergyResolutionError('scalar_sign_unresolved_at_requested_precision')
            if newlo > newhi:
                raise EnergyResolutionError('interval_newton_bisection_intersection_empty')
            qlo,qhi = newlo,newhi
            if values == previous_values:
                left,_ = self._scalar(qlo,x,policy.square_root_bits)
                right,_ = self._scalar(qhi,x,policy.square_root_bits)
                # Monotone Ti(q): these enclose every exact root temperature.
                nearest_fixed = all(_nearest(r[0]) == _nearest(l[1]) == value
                                    for l,r,value in zip(left,right,values))
                if nearest_fixed:
                    reason = ('target_uncertainty_not_certified_inside_domain' if not assessment[5]
                              else 'nearest_binary64_temperature_budget_unresolved')
                    raise EnergyResolutionError(reason)
            previous_values = values
        raise EnergyResolutionError('energy_inverse_iteration_limit')
