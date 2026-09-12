"""Bounded nominal low-water flash on the actual source storage and chemical API.

Instantaneous phase equilibrium is an explicit model choice with unknown
timescale error. This does not return SourceWetInverse: a common-potential and
composition-error certificate for the equilibrium temperature is not available.
No EOS replacement, phase rate, latent source, or implicit host integration.
"""
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from fractions import Fraction as F
import math
import time
from types import MappingProxyType

from sludge_sandbox.arlabosse_low_moisture_storage import (
    LowMoistureSorptionPoint, LowMoistureSorptionStorage,
)
from sludge_sandbox.low_moisture_phase import check_low_moisture_point
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.mass_wet_transport import check_thermal_chemical_sources
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.source_wet_storage import _binary
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential


POLICY_ID = 'LOW_MOISTURE_NOMINAL_PRESSURE_FEASIBLE_EQUILIBRIUM_FLASH_V1'
QUALIFICATION = 'nominal_equilibrium_candidate_not_certified_inverse'
FORCED_BISECTION_PERIOD = 3
LOW_W_JOIN = F(.15)


@dataclass(frozen=True)
class FlashPolicy:
    inverse_policy: InversePolicy
    temperature_range_k: tuple[float, float]
    pressure_inset_pa: float
    composition_tolerance_mol: float
    inventory_tolerance_mol: float
    chemical_tolerance_j_mol: float
    equilibrium_pressure_tolerance_pa: float
    temperature_subdivisions: int
    maximum_composition_iterations: int
    maximum_provider_calls: int
    maximum_elapsed_s: float

    def __post_init__(self) -> None:
        if type(self.inverse_policy) is not InversePolicy:
            raise ValueError('flash_explicit_inverse_policy')
        replace(self.inverse_policy)
        if type(self.temperature_range_k) is not tuple or len(self.temperature_range_k) != 2:
            raise ValueError('flash_temperature_interval')
        lo, hi = (_binary(v, positive=True) for v in self.temperature_range_k)
        if not 325. <= lo < hi <= 338.:
            raise ValueError('flash_temperature_range_outside_declared_scope')
        for name in ('pressure_inset_pa', 'composition_tolerance_mol',
                     'inventory_tolerance_mol', 'chemical_tolerance_j_mol',
                     'equilibrium_pressure_tolerance_pa', 'maximum_elapsed_s'):
            _binary(getattr(self, name), positive=True)
        for name in ('temperature_subdivisions', 'maximum_composition_iterations',
                     'maximum_provider_calls'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError('flash_positive_integer_'+name)

    def definition(self) -> dict:
        return {
            'id': POLICY_ID, 'classification': 'numerical_policy',
            'equilibrium_assumption': 'instantaneous local phase equilibrium; timescale error unknown',
            'assumption_classification': 'virtual_design_choice',
            'temperature_range_k': self.temperature_range_k,
            'pressure_inset_pa': self.pressure_inset_pa,
            'composition_tolerance_mol': self.composition_tolerance_mol,
            'inventory_tolerance_mol': self.inventory_tolerance_mol,
            'chemical_tolerance_j_mol': self.chemical_tolerance_j_mol,
            'equilibrium_pressure_tolerance_pa': self.equilibrium_pressure_tolerance_pa,
            'energy_tolerance_j': self.inverse_policy.energy_tolerance_j,
            'nominal_temperature_width_tolerance_k': self.inverse_policy.temperature_tolerance_k,
            'maximum_temperature_iterations': self.inverse_policy.maximum_iterations,
            'maximum_composition_iterations': self.maximum_composition_iterations,
            'maximum_provider_calls': self.maximum_provider_calls,
            'maximum_elapsed_s': self.maximum_elapsed_s,
            'temperature_subdivisions': self.temperature_subdivisions,
            'strategy': 'bracket secant, every third iteration midpoint; verified local sign probes near tolerance',
            'pressure_prefilter': 'nominal stable-liquid boundary inversion with declared volume envelope; every actual point rechecks original complete pressure interval',
            'pressure_monotonicity_scope': 'conditional on the existing stable liquid branch; boundary values check Pmax*vmax<RT, not a new interval EOS certificate',
            'sign_scope': 'nominal chemical signs; energy signs resolve given-composition error only',
            'unknown_numerical_errors': ['log/activity error', 'equilibrium composition energy propagation',
                                         'certified equilibrium temperature error'],
            'domain_scope': 'all visited points admitted; bounded probes do not certify absence of unvisited domain holes',
            'budget_scope': 'top-level provider calls; does not count nested EOS iterations or preempt an in-flight provider',
            'qualification': QUALIFICATION,
        }


@dataclass(frozen=True)
class FlashTrial:
    kind: str
    temperature_k: float | None = None
    liquid_mol: F | None = None
    status: str = 'completed'
    reason: str | None = None
    point: LowMoistureSorptionPoint | None = field(default=None, repr=False)
    energy_residual_j: F | None = None
    chemical_residual_j_mol: float | None = None
    pressure_residual_pa: F | None = None


class FlashFailure(ValueError):
    """Named failure retaining completed trials, including excluded scan nodes."""

    def __init__(self, reason: str, trials: tuple[FlashTrial, ...] = (), counts: dict | None = None,
                 last_completed_provider_result: object | None = None,
                 last_completed_provider_context: tuple | None = None):
        super().__init__(reason)
        self.reason = reason
        self.trials = tuple(trials)
        self.counts = MappingProxyType(dict(counts or {}))
        self.last_completed_provider_result = last_completed_provider_result
        self.last_completed_provider_context = last_completed_provider_context


@dataclass(frozen=True)
class _CompositionPoint:
    state: WetMixedState
    point: LowMoistureSorptionPoint
    requested_liquid_mol: F
    requested_vapor_mol: F
    liquid_projection_error_mol: F
    vapor_projection_error_mol: F
    pressure_residual_pa: F
    chemical_residual_j_mol: float | None
    chemical_state: str
    sign: int
    equilibrium_partial_pressure_pa: float
    water_partial_pressure_pa: float
    energy_residual_j: F

    @property
    def x(self) -> F:
        return F(self.state.liquid_water_mol)


@dataclass(frozen=True)
class NominalEquilibriumCandidate:
    state: WetMixedState
    point: LowMoistureSorptionPoint
    exact_liquid_mol: F
    exact_vapor_mol: F
    liquid_projection_error_mol: F
    vapor_projection_error_mol: F
    water_projection_residual_mol: F
    energy_residual_j: F
    nominal_temperature_bracket_k: tuple[float, float]
    composition_bracket_mol: tuple[F, F]
    equilibrium_partial_pressure_pa: float
    water_partial_pressure_pa: float
    equilibrium_pressure_residual_pa: F
    chemical_potential_residual_j_mol: float | None
    chemical_state: str
    source_ids: tuple[str, ...]
    policy: FlashPolicy
    trials: tuple[FlashTrial, ...]
    counts: MappingProxyType
    certified_temperature_error_bound_k: None = None
    equilibrium_composition_energy_error_j: None = None
    nominal_chemical_numerical_error_j_mol: None = None
    qualification: str = QUALIFICATION
    material_qualified: bool = False
    training_eligible: bool = False


def _fraction(value: int | float | F) -> F:
    if type(value) not in (int, float, F):
        raise ValueError('explicit_finite_real_input')
    return F(value)


def _project(value: F) -> float:
    out = float(value)
    if not math.isfinite(out) or (value and not out):
        raise ValueError('flash_nonzero_projection_underflow_or_overflow')
    return out


def _inward(value: F, direction: int) -> float:
    out = _project(value)
    if (direction > 0 and F(out) < value) or (direction < 0 and F(out) > value):
        out = math.nextafter(out, math.inf if direction > 0 else -math.inf)
    return out


def _proposal(lo: F, hi: F, flo: F, fhi: F, iteration: int) -> F:
    candidate = (lo+hi)/2
    if iteration % FORCED_BISECTION_PERIOD and fhi != flo:
        secant = lo-flo*(hi-lo)/(fhi-flo)
        if lo < secant < hi:
            candidate = secant
    binary = _project(candidate)
    if not lo < F(binary) < hi:
        binary = _project((lo+hi)/2)
    if not lo < F(binary) < hi:
        raise ValueError('flash_unrepresentable_interior_candidate')
    return F(binary)


class _Engine:
    def __init__(self, storage: LowMoistureSorptionStorage, chemical: WaterChemicalPotential,
                 total: F, carrier: tuple[float, float], target: float, policy: FlashPolicy):
        self.storage, self.chemical, self.total = storage, chemical, total
        self.carrier, self.target, self.policy = carrier, target, policy
        self.trials: list[FlashTrial] = []
        self.counts = dict(provider_calls=0, storage_evaluations=0,
            liquid_boundary_evaluations=0, pure_equilibrium_evaluations=0,
            vapor_evaluations=0, equilibrium_temperature_evaluations=0)
        self.started = time.monotonic()
        self.last_completed_provider_result: object | None = None
        self.last_completed_provider_context: tuple | None = None

    def fail(self, reason: str) -> FlashFailure:
        return FlashFailure(reason, tuple(self.trials), self.counts,
            self.last_completed_provider_result, self.last_completed_provider_context)

    def clock(self) -> None:
        if time.monotonic()-self.started > self.policy.maximum_elapsed_s:
            raise self.fail('flash_elapsed_budget')

    def call(self, kind: str, callback: Callable, *args):
        self.clock()
        if self.counts['provider_calls'] >= self.policy.maximum_provider_calls:
            raise self.fail('flash_provider_call_budget')
        self.counts['provider_calls'] += 1
        self.counts[kind] += 1
        out = callback(*args)
        # A returned value remains observable even when the callback used up
        # the wall budget. Do this before the post-callback deadline check.
        self.last_completed_provider_result = out
        self.last_completed_provider_context = (kind, args)
        self.clock()
        return out

    def pressure_interval(self, t: float) -> tuple[F, F]:
        """Do not decode the often inadmissible all-vapor inventory endpoint."""
        st, p = self.storage, self.policy
        low, high = map(F, st.pressure_domain_pa)
        low, high = low+F(p.pressure_inset_pa), high-F(p.pressure_inset_pa)
        if not low < high:
            raise self.fail('flash_pressure_inset_exhausts_domain')
        low, high = F(_inward(low, 1)), F(_inward(high, -1))
        r_t = F(self.chemical.gas_constant_j_mol_k)*F(t)
        volume, error = F(st.volume.value_m3), F(st.volume.error_m3)
        carriers = sum(map(F, self.carrier), F())
        if self.total == 0:
            if not low <= carriers*r_t/(volume+error) <= carriers*r_t/(volume-error) <= high:
                raise self.fail('flash_empty_composition_interval')
            return F(), F()
        liquids = [self.call('liquid_boundary_evaluations', self.chemical.liquid_tp, t, float(x))
                   for x in (low, high)]
        volumes = []
        for liquid, pressure in zip(liquids, (low, high)):
            state = liquid.state
            if state.temperature_k != t or F(state.pressure_pa) != pressure or state.phase != 'liquid':
                raise self.fail('flash_boundary_liquid_correspondence')
            volumes.append(F(_binary(state.molar_mass_kg_mol, positive=True))/
                           F(_binary(state.density_kg_m3, positive=True)))
        ve = F(_binary(st.fluid_template.envelope.liquid_v_error_m3_mol))
        if (ve < 0 or min(volumes)-ve <= 0 or volumes[1]-ve > volumes[0]+ve
                or high*(max(volumes)+ve) >= r_t):
            raise self.fail('flash_pressure_monotonicity_not_supported')
        # Worst declared input volumes, plus separate nominal inward pressure
        # reserve. Actual storage still admits its complete pressure interval.
        a = ((carriers+self.total)*r_t-high*(volume-error))/(r_t-high*(volumes[1]+ve))
        b = ((carriers+self.total)*r_t-low*(volume+error))/(r_t-low*(volumes[0]-ve))
        cap = F(st.dry_mass_kg)*LOW_W_JOIN/F(st.wet._mass)
        lo, hi = max(F(), a), min(self.total, cap, b)
        if lo >= hi:
            raise self.fail('flash_empty_composition_interval')
        lo, hi = F(_inward(lo, 1)), F(_inward(hi, -1))
        if lo >= hi:
            raise self.fail('flash_unrepresentable_composition_interval')
        self.trials.append(FlashTrial('pressure_prefilter', t, lo))
        return lo, hi

    def point(self, t: float, x: F) -> _CompositionPoint:
        nc, nv = _project(x), _project(self.total-x)
        ex, ev = F(nc)-x, F(nv)-(self.total-x)
        if nc < 0 or nv < 0 or abs(ex)+abs(ev) > F(self.policy.inventory_tolerance_mol):
            raise self.fail('flash_inventory_projection_budget')
        state = self.storage.state(nc, (*self.carrier, nv), self.target)
        out = self.call('storage_evaluations', self.storage.evaluate, state, t)
        self.trials.append(FlashTrial('storage', t, F(nc), point=out))
        check_low_moisture_point(self.storage, self.chemical, out)
        mechanical = out.fluid.mechanical
        if (type(out) is not LowMoistureSorptionPoint or out.model_identity != self.storage.model_identity
                or out.temperature_k != t or mechanical.liquid_inventory_mol != nc
                or tuple(mechanical.gas_inventory_mol[k] for k in self.storage.gas_ids) != state.gas_amounts_mol):
            raise self.fail('flash_point_inventory_or_identity_mismatch')
        pressure, pe = F(_binary(out.pressure_pa, positive=True)), F(_binary(out.pressure_error_pa))
        lo, hi = map(F, self.storage.pressure_domain_pa)
        if pe < 0 or not lo <= pressure-pe <= pressure+pe <= hi:
            raise self.fail('flash_complete_pressure_interval_exit')
        error = F(_binary(out.energy_error_j))
        if error < 0:
            raise self.fail('flash_invalid_energy_error')
        residual = F(_binary(out.total_internal_energy_j))-F(self.target)
        pv = _project(F(nv)*F(self.chemical.gas_constant_j_mol_k)*F(t)/
                      F(_binary(out.gas_volume_m3, positive=True)))
        peq, mu = 0., None
        if nc:
            pure = self.call('pure_equilibrium_evaluations',
                self.chemical.equilibrium_at_liquid_tp, t, out.pressure_pa)
            activity = _binary(out.excess.activity, positive=True)
            if activity > 1:
                raise self.fail('flash_activity_domain_exit')
            peq = _project(F(_binary(pure.equilibrium_partial_pressure_pa, positive=True))*F(activity))
            if nv:
                vapor = self.call('vapor_evaluations', self.chemical.ideal_vapor, t, pv)
                mu = _binary(math.fsum((pure.liquid.chemical_potential_j_mol,
                    out.excess.mu_ex_j_mol, -vapor.chemical_potential_j_mol)))
        elif out.excess.activity != 0:
            raise self.fail('flash_zero_inventory_activity_mismatch')
        sign = (1 if mu > 0 else -1 if mu < 0 else 0) if mu is not None else (1 if nc else -1 if nv else 0)
        name = ('finite_nominal_chemical_potential' if mu is not None else
                'zero_total_water_no_finite_water_mu' if not nc and not nv else
                'plus_infinity_zero_vapor_limit' if not nv else 'minus_infinity_zero_condensed_limit')
        result = _CompositionPoint(state, out, x, self.total-x, ex, ev,
            F(peq)-F(pv), mu, name, sign, peq, pv, residual)
        self.trials.append(FlashTrial('chemical_and_energy', t, F(nc), point=out,
            energy_residual_j=residual, chemical_residual_j_mol=mu,
            pressure_residual_pa=result.pressure_residual_pa))
        return result

    def chemical_ok(self, out: _CompositionPoint) -> bool:
        return (out.chemical_residual_j_mol is not None and
                abs(out.chemical_residual_j_mol) <= self.policy.chemical_tolerance_j_mol and
                abs(out.pressure_residual_pa) <= F(self.policy.equilibrium_pressure_tolerance_pa))

    def composition(self, t: float) -> tuple[_CompositionPoint, tuple[F, F]]:
        self.counts['equilibrium_temperature_evaluations'] += 1
        lo, hi = self.pressure_interval(t)
        if self.total == 0:
            return self.point(t, F()), (F(), F())
        a, b = self.point(t, lo), self.point(t, hi)
        if not a.sign <= 0 <= b.sign:
            raise self.fail('flash_composition_no_sign_bracket')
        for iteration in range(1, self.policy.maximum_composition_iterations+1):
            x = _proposal(a.x, b.x, a.pressure_residual_pa, b.pressure_residual_pa, iteration)
            out = self.point(t, x)
            if self.chemical_ok(out):
                # Two real side evaluations can validate a small nominal
                # bracket without bisecting the full old interval 40 times.
                radius = F(self.policy.composition_tolerance_mol)/2
                left, right = max(a.x, x-radius), min(b.x, x+radius)
                left, right = F(_inward(left, 1)), F(_inward(right, -1))
                if left < x < right:
                    near_a, near_b = self.point(t, left), self.point(t, right)
                    if near_a.sign <= 0 <= near_b.sign:
                        return out, (left, right)
            if b.x-a.x <= F(self.policy.composition_tolerance_mol) and self.chemical_ok(out):
                return out, (a.x, b.x)
            if out.sign > 0:
                b = out
            elif out.sign < 0:
                a = out
            else:
                raise self.fail('flash_chemical_sign_unresolved')
        raise self.fail('flash_composition_iteration_limit')

    def energy_ok(self, out: _CompositionPoint) -> bool:
        return abs(out.energy_residual_j)+F(out.point.energy_error_j) <= F(self.policy.inverse_policy.energy_tolerance_j)

    def energy_sign(self, out: _CompositionPoint) -> int:
        if abs(out.energy_residual_j) <= F(out.point.energy_error_j):
            if out.energy_residual_j == 0 and out.point.energy_error_j == 0:
                return 0
            raise self.fail('flash_energy_sign_unresolved')
        return 1 if out.energy_residual_j > 0 else -1

    def finish(self, out: _CompositionPoint, xb: tuple[F, F], tb: tuple[float, float]) -> NominalEquilibriumCandidate:
        self.storage._check()
        self.chemical._check_identity()
        check_thermal_chemical_sources(self.storage, self.chemical)
        self.clock()
        return NominalEquilibriumCandidate(out.state, out.point,
            out.requested_liquid_mol, out.requested_vapor_mol,
            out.liquid_projection_error_mol, out.vapor_projection_error_mol,
            out.liquid_projection_error_mol+out.vapor_projection_error_mol,
            out.energy_residual_j, tb, xb, out.equilibrium_partial_pressure_pa,
            out.water_partial_pressure_pa, out.pressure_residual_pa,
            out.chemical_residual_j_mol, out.chemical_state,
            tuple(sorted(set(out.point.source_ids+self.chemical.source_ids+(POLICY_ID,)))),
            self.policy, tuple(self.trials), MappingProxyType(dict(self.counts)))

    def run(self) -> NominalEquilibriumCandidate:
        lo, hi = map(F, self.policy.temperature_range_k)
        previous = None
        for i in range(self.policy.temperature_subdivisions+1):
            t = _project(lo+(hi-lo)*i/self.policy.temperature_subdivisions)
            try:
                out, xb = self.composition(t)
            except FlashFailure as exc:
                if exc.reason not in ('flash_empty_composition_interval', 'flash_composition_no_sign_bracket'):
                    raise
                self.trials.append(FlashTrial('excluded_temperature', t, status='excluded', reason=exc.reason))
                previous = None
                continue
            sign = self.energy_sign(out)
            if sign == 0 and self.energy_ok(out):
                return self.finish(out, xb, (t, t))
            if previous is not None and previous[0].energy_residual_j < 0 < out.energy_residual_j:
                a, b = previous[0], out
                break
            previous = (out, xb)
        else:
            raise self.fail('flash_temperature_bracket_not_found_within_scan_budget')
        for iteration in range(1, self.policy.inverse_policy.maximum_iterations+1):
            ta, tb = F(a.point.temperature_k), F(b.point.temperature_k)
            t = float(_proposal(ta, tb, a.energy_residual_j, b.energy_residual_j, iteration))
            try:
                out, xb = self.composition(t)
                if self.energy_ok(out):
                    radius = F(self.policy.inverse_policy.temperature_tolerance_k)/2
                    near_lo = _inward(max(ta, F(t)-radius), 1)
                    near_hi = _inward(min(tb, F(t)+radius), -1)
                    if near_lo < t < near_hi:
                        pa, _ = self.composition(near_lo)
                        pb, _ = self.composition(near_hi)
                        if self.energy_sign(pa) <= 0 <= self.energy_sign(pb):
                            return self.finish(out, xb, (near_lo, near_hi))
                    if tb-ta <= F(self.policy.inverse_policy.temperature_tolerance_k):
                        return self.finish(out, xb, (float(ta), float(tb)))
                if self.energy_sign(out) > 0:
                    b = out
                else:
                    a = out
            except FlashFailure:
                raise
            except Exception as exc:
                self.trials.append(FlashTrial('failed_temperature', t, status='failed', reason=str(exc)))
                raise self.fail('flash_domain_hole_or_provider_failure') from exc
        raise self.fail('flash_temperature_iteration_limit')


def flash(storage: LowMoistureSorptionStorage, chemical: WaterChemicalPotential,
          total_water_mol: int | float | F, carrier_mol: tuple[float, float],
          target_energy_j: float, policy: FlashPolicy) -> NominalEquilibriumCandidate:
    """Return only a nominal source-bound single-cell equilibrium candidate.

    total_water_mol may be the exact Fraction sum of original float inventories.
    Carrier order is O2,N2, with a positive sum. Target remains exact binary64.
    No caller state is changed. Every failure carries the completed bounded log.
    """
    try:
        if type(storage) is not LowMoistureSorptionStorage or type(chemical) is not WaterChemicalPotential:
            raise ValueError('actual_low_storage_and_chemical_required')
        if type(policy) is not FlashPolicy:
            raise ValueError('explicit_flash_policy_required')
        replace(policy)
        total, target = _fraction(total_water_mol), _binary(target_energy_j)
        if total < 0 or type(carrier_mol) is not tuple or len(carrier_mol) != 2:
            raise ValueError('explicit_nonnegative_inventory_required')
        carrier = tuple(_binary(n) for n in carrier_mol)
        if any(n < 0 for n in carrier) or not sum(map(F, carrier), F()):
            raise ValueError('positive_total_carrier_required')
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise FlashFailure('flash_invalid_input: '+str(exc)) from exc
    engine = _Engine(storage, chemical, total, carrier, target, policy)
    try:
        storage._check()
        chemical._check_identity()
        check_thermal_chemical_sources(storage, chemical)
        tl, th = storage.temperature_domain_k
        pl, ph = map(_binary, storage.pressure_domain_pa)
        if not tl <= policy.temperature_range_k[0] < policy.temperature_range_k[1] <= th:
            raise ValueError('temperature_policy_exits_actual_storage_domain')
        if not 90000. <= pl < ph <= 110000. or storage.gas_ids != ('O2', 'N2', 'H2O'):
            raise ValueError('unsupported_pressure_or_species_domain')
        volume, error = F(_binary(storage.volume.value_m3, positive=True)), F(_binary(storage.volume.error_m3))
        if not 0 <= error < volume:
            raise ValueError('invalid_available_volume_envelope')
        _binary(storage.dry_mass_kg, positive=True)
        _binary(storage.wet._mass, positive=True)
    except Exception as exc:
        raise engine.fail('flash_provider_validation: '+str(exc)) from exc
    try:
        return engine.run()
    except FlashFailure:
        raise
    except Exception as exc:
        engine.trials.append(FlashTrial('provider_failure', status='failed', reason=str(exc)))
        raise engine.fail('flash_provider_failure: '+str(exc)) from exc
