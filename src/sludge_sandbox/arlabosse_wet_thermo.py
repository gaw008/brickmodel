"""Conditional fixed-pressure wet Gibbs model, not validated sludge thermodynamics.

The two reviewed isotherm interpolants and zero excess heat capacity are explicit
new approximations. Upstream discrete readings remain unchanged. All H/G/S use
kg dry matter; water partial properties use kg water (or an explicitly named mol).
"""
from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

from .arlabosse_caloric import ArlabosseDryCaloric, NODE_ID as DRY_CP_ID
from .arlabosse_desorption95 import (
    ArlabosseDesorption95, AW_NODE_ID, HEAT_NODE_ID,
)
from .water_chemical_potential import WaterChemicalPotential
from .water_properties import _verify_sources

MODEL_SHA256 = 'bfc82cb377158d83e0b7eb25289f34db467611f5de137fdfc24c76a1d162edaa'
MODEL_ID = 'ARLABOSSE2005_CONDITIONAL_WET_GIBBS_V1'
MODEL_PATH = 'data/sandbox/research/arlabosse-wet-thermo-v1/model.json'
T_MIN, T_REF, W_MIN, W_REF, PRESSURE = 308.15, 368.15, .15, .8, 100000.
_W_NODES = (.15, .2, .3, .4, .5, .6, .7, .8)
_Q_NODES = (.15, .2, .3, .4, .7, .8)
_QUALIFICATION = 'conditional_exploration_not_validated_wet_material'
_BOUNDS_SCOPE = ('node_readout_box_propagation_only_not_total_uncertainty; '
                 'shared_calibration_correlations_not_independent_random_errors')


class WetThermodynamicError(ValueError):
    """Unsupported input, source identity, constitutive state or inversion."""


def _number(value, name, *, minimum=None, maximum=None, positive=False):
    if type(value) not in (int, float, Fraction, Decimal):
        raise WetThermodynamicError('finite_number_required_' + name)
    try:
        exact = Fraction(repr(value)) if type(value) is float else Fraction(value)
        if ((minimum is not None and exact < Fraction(str(minimum))) or
                (maximum is not None and exact > Fraction(str(maximum))) or
                (positive and exact <= 0)):
            raise WetThermodynamicError('outside_declared_domain_' + name)
        result = float(exact)
    except (ValueError, OverflowError) as exc:
        if isinstance(exc, WetThermodynamicError):
            raise
        raise WetThermodynamicError('finite_number_required_' + name) from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise WetThermodynamicError('finite_number_required_' + name)
    return result


def _finite(value, name):
    if not math.isfinite(value):
        raise WetThermodynamicError('nonfinite_model_result_' + name)
    return value


def _sum(*values):
    try:
        return _finite(math.fsum(values), 'sum')
    except OverflowError as exc:
        raise WetThermodynamicError('model_arithmetic_overflow') from exc


def _exp(value):
    try:
        result = math.exp(value)
    except OverflowError as exc:
        raise WetThermodynamicError('activity_or_pressure_unrepresentable') from exc
    if not math.isfinite(result) or result <= 0:
        raise WetThermodynamicError('activity_or_pressure_unrepresentable')
    return result


@dataclass(frozen=True)
class _Linear:
    """Analytic linear segments and quadratic integrals, evaluated in binary64."""
    x: tuple[float, ...]
    y: tuple[float, ...]

    def __post_init__(self):
        if (len(self.x) != len(self.y) or len(self.x) < 2 or
                any(not math.isfinite(y) for y in self.y) or
                any(a >= b for a, b in zip(self.x, self.x[1:]))):
            raise WetThermodynamicError('invalid_interpolant')

    def value(self, x):
        if not self.x[0] <= x <= self.x[-1]:
            raise WetThermodynamicError('interpolant_extrapolation_forbidden')
        if x in self.x:
            return self.y[self.x.index(x)]
        i = min(bisect_right(self.x, x) - 1, len(self.x) - 2)
        return _sum(self.y[i], (x-self.x[i]) * self.slope(i))

    def slope(self, i):
        return (self.y[i+1]-self.y[i])/(self.x[i+1]-self.x[i])

    def slopes(self, x):
        """One-sided derivatives; a domain endpoint has only its inward side."""
        i = bisect_left(self.x, x)
        if i < len(self.x) and self.x[i] == x:
            return (self.slope(i-1) if i else None,
                    self.slope(i) if i < len(self.x)-1 else None)
        value = self.slope(i-1)
        return value, value

    def integral(self, a, b):
        if b < a:
            return -self.integral(b, a)
        if not self.x[0] <= a <= b <= self.x[-1]:
            raise WetThermodynamicError('interpolant_extrapolation_forbidden')
        knots = (a,) + tuple(x for x in self.x if a < x < b) + (b,)
        return _sum(*(0.5*(hi-lo)*(self.value(lo)+self.value(hi))
                      for lo, hi in zip(knots, knots[1:])))


@dataclass(frozen=True)
class WetThermodynamicState:
    temperature_k: float
    moisture_kg_water_per_kg_dry: float
    specific_enthalpy_j_kg_dry: float
    specific_gibbs_j_kg_dry: float
    specific_entropy_j_kg_dry_k: float
    heat_capacity_j_kg_dry_k: float
    heat_capacity_j_kg_wet_k: float
    water_chemical_potential_j_kg_water: float
    water_chemical_potential_j_mol: float
    partial_water_enthalpy_j_kg_water: float
    vapor_enthalpy_j_kg_water: float
    liquid_enthalpy_j_kg_water: float
    total_desorption_heat_j_kg_water: float
    activity: float
    pure_model_equilibrium_vapor_pressure_pa: float
    model_equilibrium_vapor_pressure_pa: float
    composition_derivative_left_j_kg_water: float | None
    composition_derivative_right_j_kg_water: float | None
    chemical_equilibrium_residual_j_mol: float
    model_q95_j_kg_water: float
    source_readings_at_moisture: dict | None
    activity_readout_only_bounds: tuple[float, float]
    desorption_heat_readout_only_bounds_j_kg_water: tuple[float, float]
    source_ids: tuple[str, ...]
    model_id: str = MODEL_ID
    model_sha256: str = MODEL_SHA256
    liquid_mechanical_pressure_pa: float = PRESSURE
    bounds_scope: str = _BOUNDS_SCOPE
    composition_derivative_unit: str = '(J/kg water)/(kg water/kg dry matter)'
    classification: str = 'derived_from_evidence'
    qualification: str = _QUALIFICATION
    interpolation_model_error: None = None
    temperature_extension_model_error: None = None
    water_reference_model_error: None = None
    experimental_uncertainty: None = None
    material_qualified: bool = False
    training_eligible: bool = False
    full_firing_cycle: bool = False

    def to_record(self):
        return asdict(self)


@dataclass(frozen=True)
class WetEnthalpyInverse:
    state: WetThermodynamicState
    target_enthalpy_j: float
    dry_mass_kg: float
    residual_j: float
    residual_tolerance_j: float
    temperature_bracket_k: tuple[float, float]
    bracket_width_k: float
    temperature_tolerance_k: float
    iterations: int
    maximum_iterations: int
    convergence: str
    endpoint_roundoff_allowance_j: float
    target_outside_nominal_endpoint_range: bool
    numerical_scope: str = 'binary64_residual_and_bracket_not_material_uncertainty'

    def to_record(self):
        return asdict(self)


@dataclass(frozen=True)
class WetDryingHeat:
    temperature_k: float
    start_moisture: float
    end_moisture: float
    dry_mass_kg: float
    removed_water_kg: float
    heat_j: float
    vapor_carried_enthalpy_j: float
    material_enthalpy_change_j: float
    energy_identity_residual_j: float
    heat_readout_only_bounds_j: tuple[float, float]
    source_ids: tuple[str, ...]
    model_id: str = MODEL_ID
    model_sha256: str = MODEL_SHA256
    qualification: str = _QUALIFICATION
    bounds_scope: str = _BOUNDS_SCOPE
    interpolation_model_error: None = None
    temperature_extension_model_error: None = None
    water_reference_model_error: None = None
    experimental_uncertainty: None = None
    material_qualified: bool = False
    training_eligible: bool = False
    full_firing_cycle: bool = False

    def to_record(self):
        return asdict(self)


@dataclass(frozen=True, init=False)
class ArlabosseWetThermodynamics:
    """Pinned-source conditional model; no arbitrary water or source provider API.

    Public operations recheck source assets. Construction uses the existing
    source-gated Python IAPWS water backend and evaluates its reference state.
    The public domain is a design choice, not wet-property experimental coverage.
    """
    repository_root: Path
    water_directory: Path
    _dry: ArlabosseDryCaloric = field(repr=False)
    _desorption: ArlabosseDesorption95 = field(repr=False)
    _chemical: WaterChemicalPotential = field(repr=False)
    _m: _Linear = field(repr=False)
    _q: _Linear = field(repr=False)
    _m_lo: _Linear = field(repr=False)
    _m_hi: _Linear = field(repr=False)
    _q_lo: _Linear = field(repr=False)
    _q_hi: _Linear = field(repr=False)
    _readings_json: str = field(repr=False)
    _latent_reference: float
    _mass: float
    _rs: float

    def __init__(self, repository_root, water_directory):
        root = Path(repository_root).resolve()
        object.__setattr__(self, 'repository_root', root)
        object.__setattr__(self, 'water_directory', Path(water_directory).resolve())
        self._model_definition()
        dry = ArlabosseDryCaloric(root/'data/sandbox/research/arlabosse2005/source.json', root)
        desorption = ArlabosseDesorption95(root/'data/sandbox/research/arlabosse95/source.json', root)
        chemical = WaterChemicalPotential(self.water_directory)
        object.__setattr__(self, '_dry', dry)
        object.__setattr__(self, '_desorption', desorption)
        object.__setattr__(self, '_chemical', chemical)
        mass = _number(chemical.reference.molar_mass_kg_mol, 'water_molar_mass', positive=True)
        rs = chemical.gas_constant_j_mol_k/mass
        object.__setattr__(self, '_mass', mass)
        object.__setattr__(self, '_rs', rs)
        reference = chemical.equilibrium_at_liquid_tp(T_REF, PRESSURE)
        latent = _sum(reference.vapor.enthalpy_j_mol/mass, -reference.liquid.enthalpy_j_mol/mass)
        object.__setattr__(self, '_latent_reference', _finite(latent, 'reference_latent'))
        points = tuple(desorption.at_moisture(w, temperature=T_REF, unit='K') for w in _W_NODES)
        object.__setattr__(self, '_readings_json', json.dumps([p.to_record() for p in points]))
        for name, bounds in (('_m', None), ('_m_lo', 0), ('_m_hi', 1)):
            values = tuple(rs*T_REF*math.log(float(p.activity.value if bounds is None
                                  else p.activity.digitization_bounds[bounds])) for p in points)
            object.__setattr__(self, name, _Linear(_W_NODES, values))
        heat_points = tuple(p for p in points if p.total_desorption_heat.value is not None)
        if tuple(float(p.moisture_kg_water_per_kg_dry_matter) for p in heat_points) != _Q_NODES:
            raise WetThermodynamicError('reviewed_heat_node_identity_changed')
        for name, bounds in (('_q', None), ('_q_lo', 0), ('_q_hi', 1)):
            values = tuple(float(p.total_desorption_heat.value if bounds is None
                                 else p.total_desorption_heat.digitization_bounds[bounds]) for p in heat_points)
            object.__setattr__(self, name, _Linear(_Q_NODES, values))
        # Slopes and log(activity) have their extrema at these T/W endpoints.
        # This checks nominal constitutive admissibility, not measurement validity.
        for t in (T_MIN, T_REF):
            for w in _W_NODES:
                self._excess(t, w)

    def _model_definition(self):
        try:
            raw = (self.repository_root/MODEL_PATH).read_bytes()
            if hashlib.sha256(raw).hexdigest() != MODEL_SHA256:
                raise WetThermodynamicError('reviewed_wet_model_metadata_changed')
            definition = json.loads(raw)
            for asset in definition['upstream'] + definition['assets']:
                path = (self.repository_root/asset['path']).resolve()
                if not path.is_relative_to(self.repository_root):
                    raise WetThermodynamicError('wet_model_asset_outside_repository')
                if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
                    raise WetThermodynamicError('reviewed_wet_model_asset_changed')
            return definition
        except OSError as exc:
            raise WetThermodynamicError('reviewed_wet_model_asset_unavailable') from exc

    def _check_sources(self):
        self._model_definition()
        self._dry._source()
        self._desorption._load()
        _verify_sources(self.water_directory)  # Hash/runtime checks only; no EOS evaluation.
        self._chemical._check_identity()
        if (self._chemical.reference.molar_mass_kg_mol != self._mass or
                self._chemical.gas_constant_j_mol_k/self._mass != self._rs):
            raise WetThermodynamicError('wet_water_reference_changed')

    def definition(self):
        self._check_sources()
        definition = self._model_definition()
        definition['model_sha256'] = MODEL_SHA256
        definition['source_point_records'] = json.loads(self._readings_json)
        definition['water'] = {
            'source_ids': list(self._chemical.source_ids),
            'source_asset_sha256': dict(self._chemical.source_asset_sha256),
            'reference': asdict(self._chemical.reference),
            'molar_mass_kg_mol': self._mass,
            'gas_constant_j_mol_k': self._chemical.gas_constant_j_mol_k,
            'gas_constant_j_kg_water_k': self._rs,
            'chemical_method_id': self._chemical.method_id,
            'caloric_method_id': self._chemical.caloric_method_id,
            'backend': 'python',
        }
        definition['dry_reference'] = 'h_dry(T0)=s_dry(T0)=0; sensible differences only, not formation values'
        definition['source_ids'] = list(self._source_ids())
        definition['bounds_scope'] = _BOUNDS_SCOPE
        definition['inverse_numerical_policy'] = {
            'endpoint_roundoff_allowance': '8*max(ulp(target_j),ulp(endpoint_j)); explicit arithmetic allowance, not a proved total error bound',
            'temperature_tolerance_k': [1e-12, 1.], 'maximum_iterations': [1, 512],
            'outside_allowance': 'reject; no physical-domain clipping',
        }
        return definition

    def _source_ids(self):
        return (DRY_CP_ID, 'ARLABOSSE2005_WET_CP_EQ1', AW_NODE_ID,
                HEAT_NODE_ID, 'SRC_ARLABOSSE_2005_CONTACT_DRYING',
                'FERRASSE_LECOMTE_2004') + tuple(self._chemical.source_ids)

    def _excess(self, t, w):
        ratio = t/T_REF
        m = self._m.value(w)
        b = self._latent_reference-self._q.value(w)
        mu = _sum(ratio*m, (1-ratio)*b)
        log_activity = mu/(self._rs*t)
        if log_activity > 0:
            raise WetThermodynamicError('unsupported_activity_above_one')
        activity = _exp(log_activity)
        derivatives = []
        for dm, dq in zip(self._m.slopes(w), self._q.slopes(w)):
            derivative = None if dm is None or dq is None else _sum(ratio*dm, -(1-ratio)*dq)
            if derivative is not None and derivative < 0:
                raise WetThermodynamicError('unsupported_composition_instability')
            derivatives.append(derivative)
        return mu, b, activity, tuple(derivatives)

    def evaluate(self, temperature_k, moisture):
        self._check_sources()
        t = _number(temperature_k, 'temperature_k', minimum=T_MIN, maximum=T_REF)
        w = _number(moisture, 'moisture', minimum=W_MIN, maximum=W_REF)
        return self._evaluate(t, w)

    def _evaluate(self, t, w):
        mu_ex, b, activity, derivatives = self._excess(t, w)
        eq = self._chemical.equilibrium_at_liquid_tp(t, PRESSURE)
        liquid, vapor = eq.liquid, eq.vapor
        hl = liquid.enthalpy_j_mol/self._mass
        gl = liquid.chemical_potential_j_mol/self._mass
        sl = liquid.entropy_j_mol_k/self._mass
        hv = vapor.enthalpy_j_mol/self._mass
        latent = _sum(hv, -hl)
        gex0 = self._m.integral(W_REF, w)
        hex0 = _sum(self._latent_reference*(w-W_REF), -self._q.integral(W_REF, w))
        sex = _sum(hex0, -gex0)/T_REF
        hd = float(self._dry.delta_h(T_REF, t, unit='K').value)
        sd = _sum((1434-3.29*273.15)*math.log(t/T_REF), 3.29*(t-T_REF))
        enthalpy = _sum(hd, w*hl, hex0)
        entropy = _sum(sd, w*sl, sex)
        gibbs = _sum(hd, -t*sd, w*gl, hex0, -t*sex)
        cp = _sum(float(self._dry.cp(t, unit='K').value), w*liquid.state.cp_j_kg_k)
        if liquid.state.cp_j_kg_k <= 0 or cp <= 0:
            raise WetThermodynamicError('unsupported_nonpositive_heat_capacity')
        mu = _sum(gl, mu_ex)
        pressure = _finite(eq.equilibrium_partial_pressure_pa*activity, 'equilibrium_pressure')
        if pressure <= 0:
            raise WetThermodynamicError('activity_or_pressure_unrepresentable')
        gas = self._chemical.ideal_vapor(t, pressure)
        residual = _sum(mu*self._mass, -gas.chemical_potential_j_mol)
        if abs(residual) > 1e-7:
            raise WetThermodynamicError('wet_chemical_equilibrium_residual')
        ratio = t/T_REF
        activity_bounds = (
            _exp(_sum(ratio*self._m_lo.value(w), (1-ratio)*(self._latent_reference-self._q_hi.value(w)))/(self._rs*t)),
            _exp(_sum(ratio*self._m_hi.value(w), (1-ratio)*(self._latent_reference-self._q_lo.value(w)))/(self._rs*t)),
        )
        delta_latent = _sum(latent, -self._latent_reference)
        q_bounds = (_sum(delta_latent, self._q_lo.value(w)),
                    _sum(delta_latent, self._q_hi.value(w)))
        point = next((p for p in json.loads(self._readings_json)
                      if float(Fraction(int(p['moisture_kg_water_per_kg_dry_matter']['numerator']),
                                        int(p['moisture_kg_water_per_kg_dry_matter']['denominator']))) == w), None)
        return WetThermodynamicState(
            t, w, enthalpy, gibbs, entropy, cp, cp/(1+w), mu, mu*self._mass,
            _sum(hl, b), hv, hl, _sum(delta_latent, self._q.value(w)), activity,
            eq.equilibrium_partial_pressure_pa, pressure, *derivatives, residual,
            self._q.value(w), point, activity_bounds, q_bounds, self._source_ids())

    def inverse_enthalpy(self, target_j, *, dry_mass_kg, moisture,
                         temperature_tolerance_k=1e-7, maximum_iterations=80):
        """Invert fixed-W H; outside targets exceeding the 8-ulp policy are rejected.

        Newton proposals are safeguarded inside the middle 80% of the bracket.
        Both bracket width and residual must pass, except an exact binary64 zero
        or endpoint match. Outside endpoints, an explicitly reported eight-ulp
        arithmetic allowance is permitted; it is not a proved total error bound.
        No experimental accuracy follows from these checks.
        """
        self._check_sources()
        target = _number(target_j, 'target_enthalpy')
        md = _number(dry_mass_kg, 'dry_mass_kg', positive=True)
        w = _number(moisture, 'moisture', minimum=W_MIN, maximum=W_REF)
        tolerance = _number(temperature_tolerance_k, 'temperature_tolerance_k', minimum=1e-12, maximum=1.)
        if type(maximum_iterations) is not int or not 1 <= maximum_iterations <= 512:
            raise WetThermodynamicError('maximum_iterations_integer_1_to_512_required')
        lo, hi = T_MIN, T_REF
        low, high = self._evaluate(lo, w), self._evaluate(hi, w)
        hlo = _finite(md*low.specific_enthalpy_j_kg_dry, 'endpoint_enthalpy')
        hhi = _finite(md*high.specific_enthalpy_j_kg_dry, 'endpoint_enthalpy')
        if not hlo < hhi:
            raise WetThermodynamicError('enthalpy_range_not_resolvable_or_monotone')
        outside = not hlo <= target <= hhi
        endpoint = hlo if target < hlo else hhi
        endpoint_allowance = 8*max(math.ulp(target), math.ulp(endpoint)) if outside else 0.
        if outside and abs(target-endpoint) > endpoint_allowance:
            raise WetThermodynamicError('target_enthalpy_outside_declared_temperature_domain')
        # Minimum dry Cp is a conservative derivative scale when admitted liquid
        # Cp is positive; the ulp term is explicitly binary64 arithmetic slack.
        residual_limit = _sum(md*float(self._dry.cp(T_MIN, unit='K').value)*tolerance,
                              8*math.ulp(target), 8*math.ulp(hlo), 8*math.ulp(hhi))
        def done(state, residual, iterations, reason):
            return WetEnthalpyInverse(state, target, md, residual, residual_limit,
                                      (lo, hi), hi-lo, tolerance, iterations,
                                      maximum_iterations, reason, endpoint_allowance, outside)
        if outside:
            if target < hlo:
                hi = lo
                return done(low, hlo-target, 0, 'binary64_endpoint_roundoff')
            lo = hi
            return done(high, hhi-target, 0, 'binary64_endpoint_roundoff')
        if target == hlo:
            hi = lo
            return done(low, 0., 0, 'binary64_endpoint_match')
        if target == hhi:
            lo = hi
            return done(high, 0., 0, 'binary64_endpoint_match')
        t = (lo+hi)/2
        for iteration in range(1, maximum_iterations+1):
            state = self._evaluate(t, w)
            residual = _sum(_finite(md*state.specific_enthalpy_j_kg_dry, 'enthalpy'), -target)
            if residual == 0:
                lo = hi = t
                return done(state, residual, iteration, 'binary64_zero_residual')
            if residual < 0:
                lo = t
            else:
                hi = t
            if hi-lo <= tolerance and abs(residual) <= residual_limit:
                return done(state, residual, iteration, 'residual_and_bracket')
            derivative = _finite(md*state.heat_capacity_j_kg_dry_k, 'enthalpy_derivative')
            if derivative <= 0:
                raise WetThermodynamicError('enthalpy_derivative_not_positive')
            proposal = t-residual/derivative
            width = hi-lo
            t = proposal if lo+.1*width < proposal < hi-.1*width else (lo+hi)/2
            if t in (lo, hi):
                raise WetThermodynamicError('enthalpy_inverse_temperature_resolution_exhausted')
        raise WetThermodynamicError(
            f'enthalpy_inverse_iteration_budget_exhausted: iterations={maximum_iterations}; '
            f'residual_j={residual!r}; bracket_k=({lo!r},{hi!r})')

    def isothermal_drying_heat(self, temperature_k, start_moisture, end_moisture,
                              dry_mass_kg=1.):
        """Analytic piecewise q integral; q already contains vaporization heat."""
        self._check_sources()
        t = _number(temperature_k, 'temperature_k', minimum=T_MIN, maximum=T_REF)
        a = _number(start_moisture, 'start_moisture', minimum=W_MIN, maximum=W_REF)
        b = _number(end_moisture, 'end_moisture', minimum=W_MIN, maximum=W_REF)
        md = _number(dry_mass_kg, 'dry_mass_kg', positive=True)
        if b > a:
            raise WetThermodynamicError('drying_requires_nonincreasing_moisture')
        start, end = self._evaluate(t, a), self._evaluate(t, b)
        delta_latent = _sum(start.vapor_enthalpy_j_kg_water,
                            -start.liquid_enthalpy_j_kg_water, -self._latent_reference)
        heat = _finite(md*_sum(delta_latent*(a-b), self._q.integral(b, a)), 'drying_heat')
        removed = _finite(md*(a-b), 'removed_water')
        carried = _finite(removed*start.vapor_enthalpy_j_kg_water, 'vapor_carried_enthalpy')
        change = _finite(md*_sum(end.specific_enthalpy_j_kg_dry,
                                -start.specific_enthalpy_j_kg_dry), 'material_enthalpy_change')
        bounds = tuple(_finite(md*_sum(delta_latent*(a-b), q.integral(b, a)), 'heat_bound')
                       for q in (self._q_lo, self._q_hi))
        return WetDryingHeat(t, a, b, md, removed, heat, carried, change,
                            _sum(heat, -change, -carried), bounds, self._source_ids())
