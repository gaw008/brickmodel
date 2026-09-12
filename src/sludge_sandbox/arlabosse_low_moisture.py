"""Source-joined, explicitly virtual low-water Helmholtz/Gibbs excess.

No EOS calls occur here. h/s/f are per kg dry matter; chemical potential,
partial enthalpy and composition derivatives are already molar. Fractions
preserve represented source/input algebra, not exact experimental physics.
"""
from dataclasses import dataclass, field, fields
from decimal import Decimal
from fractions import Fraction as F
import hashlib
import json
import math

from .arlabosse_wet_thermo import (
    ArlabosseWetThermodynamics, T_MIN, T_REF, W_MIN, W_REF, WetThermodynamicError,
    _Linear, _Q_NODES, _W_NODES,
)


MODEL_ID = 'ARLABOSSE2005_LOW_MOISTURE_EXCESS_V1'
MODEL_PATH = 'data/sandbox/research/arlabosse-low-moisture-v1/model.json'
MODEL_SHA256 = '906f2a8a7b1d97c30f38edd51d019f874b14c9caf178b7aeb0f3797adb7b4a3f'
Numeric = int | float | F | Decimal


class LowMoistureError(ValueError):
    """Source, domain or finite numerical representation was not admitted."""


def _exact(value: Numeric, label: str) -> F:
    if type(value) not in (int, float, F, Decimal):
        raise LowMoistureError(label+'_finite_number_required')
    try:
        return F(value)
    except (OverflowError, ValueError) as exc:
        raise LowMoistureError(label+'_finite_number_required') from exc


def _nominal(value: F, label: str) -> float:
    try:
        result = float(value)
    except OverflowError as exc:
        raise LowMoistureError(label+'_representation_overflow') from exc
    if not math.isfinite(result):
        raise LowMoistureError(label+'_representation_overflow')
    if value != 0 and result == 0:
        raise LowMoistureError(label+'_representation_underflow')
    return result


def _value(curve: _Linear, w: F) -> F:
    for i in range(len(curve.x)-1):
        a, b = F(curve.x[i]), F(curve.x[i+1])
        if a <= w <= b:
            ya, yb = F(curve.y[i]), F(curve.y[i+1])
            return ya+(yb-ya)*(w-a)/(b-a)
    raise LowMoistureError('represented_curve_domain_exit')


def _integral(curve: _Linear, a: F, b: F) -> F:
    if b < a:
        return -_integral(curve, b, a)
    edges = (a, *(F(x) for x in curve.x if a < F(x) < b), b)
    return sum(((_value(curve, lo)+_value(curve, hi))*(hi-lo)/2
                for lo, hi in zip(edges, edges[1:])), F(0))


def _slopes(curve: _Linear, w: F) -> tuple[F | None, F | None]:
    left = right = None
    for i in range(len(curve.x)-1):
        a, b = F(curve.x[i]), F(curve.x[i+1])
        slope = (F(curve.y[i+1])-F(curve.y[i]))/(b-a)
        if a < w <= b:
            left = slope
        if a <= w < b:
            right = slope
    return left, right


def _log_ratio(w: F, join: F) -> F:
    delta = w-join
    if abs(delta) <= join/2:
        value = math.log1p(_nominal(delta/join, 'log1p_input'))
    else:
        value = math.log(_nominal(w, 'positive_moisture'))-math.log(float(join))
    if not math.isfinite(value) or (delta != 0 and value == 0):
        raise LowMoistureError('logarithm_not_representable')
    return F(value)


def _activity(mu_mol: F, rt: F) -> float:
    if mu_mol > 0:
        raise LowMoistureError('activity_above_one')
    result = math.exp(_nominal(mu_mol/rt, 'log_activity'))
    if result <= 0 or not math.isfinite(result):
        raise LowMoistureError('activity_representation_underflow')
    return result


@dataclass(frozen=True, kw_only=True)
class LowMoistureExcessPoint:
    """Exact h and nominal-log-conditional s/f; unknown errors stay unknown.

    At zero the finite thermodynamic primitives are analytical limits. Null mu
    and Gamma are accompanied by limit labels, not missing-data substitutions.
    """
    temperature_k: F
    moisture_kg_water_per_kg_dry: F
    h_ex_j_kg_dry: F
    s_ex_j_kg_dry_k: F
    f_ex_j_kg_dry: F
    mu_ex_j_mol: float | None
    partial_h_ex_j_mol: float
    activity: float
    gamma_left_j_mol: float | None
    gamma_right_j_mol: float | None
    branch: str
    mu_state: str
    gamma_state: str
    model_identity: str
    source_ids: tuple[str, ...]
    excess_cp_j_kg_dry_k: F = F(0)
    excess_volume_m3_kg_dry: F = F(0)
    model_error: None = None
    log_numerical_error: None = None
    activity_numerical_error: None = None
    experimental_uncertainty: None = None
    material_qualified: bool = False
    training_eligible: bool = False
    full_firing_cycle: bool = False
    numerical_scope: str = 'exact_represented_node_h; nominal_log_conditional_s_f; nominal_molar_partials_and_activity; no_total_error_bound'

    def to_record(self) -> dict:
        """Fresh strict-JSON-compatible record; rational values remain exact."""
        record = {}
        for item in fields(self):
            value = getattr(self, item.name)
            record[item.name] = ({'numerator': str(value.numerator),
                                  'denominator': str(value.denominator)}
                                 if isinstance(value, F) else value)
        return record


@dataclass(frozen=True)
class ArlabosseLowMoisture:
    """Explicit extension of one actual wet source provider, never an EOS proxy."""
    wet: ArlabosseWetThermodynamics
    _identity: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, '_identity', self.binding())

    def _model_definition(self) -> dict:
        root = self.wet.repository_root
        try:
            raw = (root/MODEL_PATH).read_bytes()
            if hashlib.sha256(raw).hexdigest() != MODEL_SHA256:
                raise LowMoistureError('low_moisture_model_metadata_changed')
            definition = json.loads(raw)
            for asset in definition['upstream']:
                path = (root/asset['path']).resolve()
                if not path.is_relative_to(root):
                    raise LowMoistureError('low_moisture_source_outside_repository')
                if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
                    raise LowMoistureError('low_moisture_source_asset_changed')
            return definition
        except OSError as exc:
            raise LowMoistureError('low_moisture_source_asset_unavailable') from exc

    def _snapshot(self) -> dict:
        if type(self.wet) is not ArlabosseWetThermodynamics:
            raise LowMoistureError('actual_arlabosse_wet_thermodynamics_required')
        try:
            definition = self._model_definition()
            upstream = self.wet.definition()  # Actual public source checks; no EOS.
        except WetThermodynamicError as exc:
            raise LowMoistureError('low_moisture_upstream_source_changed_or_unavailable') from exc
        m, q = self.wet._m, self.wet._q
        if (type(m) is not _Linear or type(q) is not _Linear or
                m.x != _W_NODES or q.x != _Q_NODES):
            raise LowMoistureError('low_moisture_represented_node_identity_changed')
        mass = _exact(self.wet._mass, 'molar_mass')
        r = _exact(self.wet._chemical.gas_constant_j_mol_k, 'gas_constant')
        if mass <= 0 or r <= 0:
            raise LowMoistureError('positive_water_constants_required')
        return {
            'model': definition, 'model_sha256': MODEL_SHA256,
            'wet_definition': upstream,
            'actual_m_nodes': [list(m.x), list(m.y)],
            'actual_q_nodes': [list(q.x), list(q.y)],
            'latent_reference_j_kg_water': self.wet._latent_reference,
            'molar_mass_kg_mol': self.wet._mass,
            'gas_constant_j_mol_k': self.wet._chemical.gas_constant_j_mol_k,
        }

    def binding(self) -> str:
        """Verify source bytes and the actual immutable-model coefficient snapshot."""
        try:
            raw = json.dumps(self._snapshot(), sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode()
        except (TypeError, ValueError) as exc:
            if isinstance(exc, LowMoistureError):
                raise
            raise LowMoistureError('low_moisture_source_snapshot_invalid') from exc
        digest = hashlib.sha256(raw).hexdigest()
        if hasattr(self, '_identity') and digest != self._identity:
            raise LowMoistureError('low_moisture_provider_content_changed')
        return digest

    @property
    def source_ids(self) -> tuple[str, ...]:
        self.binding()
        return tuple(sorted(set(self.wet._source_ids()+(MODEL_ID, MODEL_SHA256))))

    def definition(self) -> dict:
        self.binding()
        snapshot = self._snapshot()
        result = snapshot.pop('model')
        result['binding'] = self._identity
        result['actual_source_binding'] = snapshot
        return result

    def evaluate(self, temperature_k: Numeric, moisture_kg_water_per_kg_dry: Numeric) -> LowMoistureExcessPoint:
        """Evaluate exact inventory algebra and explicit zero-water limits."""
        self.binding()
        t = _exact(temperature_k, 'temperature')
        w = _exact(moisture_kg_water_per_kg_dry, 'moisture')
        if not F(T_MIN) <= t <= F(T_REF):
            raise LowMoistureError('low_moisture_temperature_domain_exit')
        if not 0 <= w <= F(W_REF):
            raise LowMoistureError('low_moisture_moisture_domain_exit')
        j, anchor, t0 = F(W_MIN), F(W_REF), F(T_REF)
        mass = F(self.wet._mass)
        r = F(self.wet._chemical.gas_constant_j_mol_k)
        latent = F(self.wet._latent_reference)
        m, q = self.wet._m, self.wet._q
        bjoin = latent-_value(q, j)
        mjoin = _value(m, j)
        hjoin = latent*(j-anchor)-_integral(q, anchor, j)
        sjoin = (hjoin-_integral(m, anchor, j))/t0
        cjoin = (bjoin-mjoin)/t0
        mu_join = mass*(bjoin-t*cjoin)
        if w < j:
            h = hjoin+bjoin*(w-j)
            # The zero branch is analytical; positive W is never replaced by epsilon.
            log_ratio = _log_ratio(w, j) if w else F(0)
            psi = w*log_ratio-w+j
            s = sjoin+cjoin*(w-j)-(r/mass)*psi
            partial_h = mass*bjoin
            if w == 0:
                mu, activity, gamma = None, 0., None
                branch, mu_state = 'analytic_dry_endpoint', 'minus_infinity_at_zero_inventory'
                gamma_state = 'positive_infinite_boundary_limit'
            else:
                mu = _nominal(mu_join+r*t*log_ratio, 'chemical_potential')
                activity = _nominal(F(_activity(mu_join, r*t))*w/j, 'activity')
                gamma = _nominal(r*t/w, 'gamma')
                branch, mu_state, gamma_state = 'virtual_low_moisture', 'finite', 'finite_low_moisture'
            gamma_left = gamma_right = gamma
        else:
            h = latent*(w-anchor)-_integral(q, anchor, w)
            s = (h-_integral(m, anchor, w))/t0
            b = latent-_value(q, w)
            mu_exact = mass*((t/t0)*_value(m, w)+(1-t/t0)*b)
            mu, partial_h = _nominal(mu_exact, 'chemical_potential'), mass*b
            activity = _activity(mu_exact, r*t)
            sides = []
            for dm, dq in zip(_slopes(m, w), _slopes(q, w)):
                g = mass*((t/t0)*dm-(1-t/t0)*dq) if dm is not None and dq is not None else None
                if g is not None and g < 0:
                    raise LowMoistureError('negative_source_composition_derivative')
                sides.append(_nominal(g, 'gamma') if g is not None else None)
            gamma_left, gamma_right = sides
            if w == j:
                gamma_left = _nominal(r*t/j, 'gamma')
            branch, mu_state = 'represented_source_curve', 'finite'
            gamma_state = 'finite_one_sided_join' if w == j else 'finite_source_one_sided_or_piecewise'
        return LowMoistureExcessPoint(
            temperature_k=t, moisture_kg_water_per_kg_dry=w,
            h_ex_j_kg_dry=h, s_ex_j_kg_dry_k=s, f_ex_j_kg_dry=h-t*s,
            mu_ex_j_mol=mu, partial_h_ex_j_mol=_nominal(partial_h, 'partial_enthalpy'),
            activity=activity, gamma_left_j_mol=gamma_left, gamma_right_j_mol=gamma_right,
            branch=branch, mu_state=mu_state, gamma_state=gamma_state,
            model_identity=self._identity,
            source_ids=tuple(sorted(set(self.wet._source_ids()+(MODEL_ID, MODEL_SHA256)))),
        )
