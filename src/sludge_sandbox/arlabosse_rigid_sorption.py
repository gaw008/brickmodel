"""Conditional sorption Helmholtz excess on the existing rigid wet storage.

F_ex=m_dry*(h_ex(W)-T*s_ex(W)) is independent of pore volume. Thus U_ex
is independent of T, fixed-inventory Cv and mechanical pressure are unchanged,
and the added partial liquid-water enthalpy equals its partial internal energy.
This is an explicitly bounded model extension, not material qualification.
"""
from dataclasses import dataclass, field, fields, replace
from fractions import Fraction as F
import math

from .arlabosse_wet_thermo import (
    ArlabosseWetThermodynamics, MODEL_ID, MODEL_SHA256, T_MIN, T_REF, W_MIN, W_REF,
    _Linear,
)
from .deforming_solid_storage import _digest
from .mass_storage_bridge import MixedError, number, require, upper
from .mass_wet_storage import WetMixedState, WaterElementConvention
from .phase_storage import InversePolicy
from .rigid_storage import RigidStorage
from .source_mass_caloric import ArlabosseMassCaloric, ReactionDisabled
from .source_wet_storage import (
    ManufacturedFixedFluidVolume, SourceWetInverse, SourceWetPoint, SourceWetStorage,
    _binary,
)
from .water_properties import WaterProperties


SORPTION_ID = 'ARLABOSSE2005_RIGID_SORPTION_HELMHOLTZ_V1'
EXPLORATION_PRESSURE_PA = (90000., 110000.)
QUALIFICATION = 'conditional_source_sorption_rigid_excess_with_unknown_extension_errors_not_material_admission'


def _value(curve: _Linear, x: F) -> F:
    """Exact linear interpolation of the existing represented binary64 nodes."""
    for index in range(len(curve.x)-1):
        a, b = F(curve.x[index]), F(curve.x[index+1])
        if a <= x <= b:
            ya, yb = F(curve.y[index]), F(curve.y[index+1])
            return ya+(yb-ya)*(x-a)/(b-a)
    raise MixedError('sorption_interpolation_domain_exit')


def _integral(curve: _Linear, a: F, b: F) -> F:
    """Integrate each linear piece exactly; no hidden quadrature allowance."""
    if a == b:
        return F(0)
    if b < a:
        return -_integral(curve, b, a)
    edges = (a, *(F(x) for x in curve.x if a < F(x) < b), b)
    return sum(((_value(curve, lo)+_value(curve, hi))*(hi-lo)/2
                for lo, hi in zip(edges, edges[1:])), F(0))


@dataclass(frozen=True, kw_only=True)
class ArlabosseSorptionPoint(SourceWetPoint):
    """Base fluid state plus excess values; model errors remain unquantified."""
    moisture_kg_water_per_kg_dry: float
    excess_internal_energy_j: F
    excess_entropy_j_k: F
    excess_helmholtz_energy_j: F
    excess_chemical_potential_j_mol: float
    excess_partial_water_enthalpy_j_mol: float
    activity: float
    excess_volume_m3: float = 0.
    pressure_extension_model_error: None = None
    temperature_extension_model_error: None = None
    interpolation_model_error: None = None
    experimental_uncertainty: None = None
    training_eligible: bool = False
    qualification: str = QUALIFICATION
    numerical_scope: str = 'base_conditional_energy_bound_plus_exact_binary_node_excess_and_final_projection; nominal_mu_and_activity'


@dataclass(frozen=True)
class ArlabosseSorptionStorage:
    """Explicit source-specific wrapper; only this exact base/wet pair is admitted.

    Pressure limits must be chosen explicitly inside the 90--110 kPa exploratory
    domain. The complete base pressure interval must remain within these limits.
    No implicit liquid/vapor backend bridge or pressure-dependent excess is used.
    """
    base: SourceWetStorage
    wet: ArlabosseWetThermodynamics
    pressure_domain_pa: tuple[float, float]
    _identity: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, '_identity', self.binding())

    @property
    def caloric(self) -> ArlabosseMassCaloric:
        return self.base.caloric

    @property
    def dry_mass_kg(self) -> float:
        return self.base.dry_mass_kg

    @property
    def fluid_template(self) -> RigidStorage:
        return self.base.fluid_template

    @property
    def volume(self) -> ManufacturedFixedFluidVolume:
        return self.base.volume

    @property
    def chemistry(self) -> ReactionDisabled:
        return self.base.chemistry

    @property
    def water_element_convention(self) -> WaterElementConvention:
        return self.base.water_element_convention

    @property
    def solid_ids(self) -> tuple[str, ...]:
        return self.base.solid_ids

    @property
    def gas_ids(self) -> tuple[str, ...]:
        return self.base.gas_ids

    @property
    def water(self) -> WaterProperties:
        return self.base.water

    @property
    def temperature_domain_k(self) -> tuple[float, float]:
        lo, hi = self.base.temperature_domain_k
        return max(lo, T_MIN), min(hi, T_REF)

    def binding(self) -> str:
        """Recheck source assets and bind the actual coefficients and base identity."""
        require(type(self.base) is SourceWetStorage, 'actual_source_wet_storage_required')
        require(type(self.wet) is ArlabosseWetThermodynamics, 'actual_arlabosse_wet_thermodynamics_required')
        self.base._check()
        self.wet._check_sources()
        require(type(self.pressure_domain_pa) is tuple and len(self.pressure_domain_pa) == 2,
                'explicit_sorption_pressure_domain')
        plo, phi = (_binary(p, positive=True) for p in self.pressure_domain_pa)
        require(EXPLORATION_PRESSURE_PA[0] <= plo < phi <= EXPLORATION_PRESSURE_PA[1],
                'sorption_pressure_domain_outside_exploration')
        require(self.temperature_domain_k[0] < self.temperature_domain_k[1],
                'sorption_empty_temperature_domain')
        water, chemical = self.base.water, self.wet._chemical
        require(type(water) is type(chemical.water) and water.implementation == chemical.water.implementation,
                'sorption_water_backend_mismatch')
        require(water.reference == chemical.reference and
                water.source_asset_sha256 == chemical.source_asset_sha256 and
                water.reference.molar_mass_kg_mol == self.wet._mass and
                self.fluid_template.mechanical.gas_constant_j_mol_k == chemical.gas_constant_j_mol_k,
                'sorption_water_reference_mismatch')
        return _digest((SORPTION_ID, MODEL_ID, MODEL_SHA256, self.base.binding(),
            self.wet.definition(), self.wet._m, self.wet._q, self.wet._latent_reference,
            self.wet._mass, self.wet._rs, self.pressure_domain_pa, self.temperature_domain_k,
            type(water).__module__, type(water).__qualname__, water.implementation))

    def _check(self) -> None:
        require(self.binding() == self._identity, 'sorption_provider_content_changed')

    @property
    def model_identity(self) -> str:
        self._check()
        return self._identity

    @property
    def source_ids(self) -> tuple[str, ...]:
        self._check()
        return tuple(sorted(set(self.base.source_ids+self.wet._source_ids()+
                                (SORPTION_ID, MODEL_ID, MODEL_SHA256))))

    def state(self, liquid_water_mol: float, gas_amounts_mol: tuple[float, ...],
              internal_energy_j: float) -> WetMixedState:
        """Create a newly bound state; a base state is never implicitly accepted."""
        self._check()
        old = self.base.state(liquid_water_mol, gas_amounts_mol, internal_energy_j)
        state = replace(old, energy_model_identity=self._identity)
        self.check(state)
        return state

    def _base_state(self, state: WetMixedState) -> WetMixedState:
        # All callers validate the wrapper identity before this private conversion.
        return replace(state, energy_model_identity=self.base._identity)

    def _moisture(self, state: WetMixedState) -> F:
        moisture = F(state.liquid_water_mol)*F(self.wet._mass)/F(self.dry_mass_kg)
        require(F(W_MIN) <= moisture <= F(W_REF), 'sorption_moisture_domain_exit')
        return moisture

    def check(self, state: WetMixedState) -> None:
        self._check()
        require(type(state) is WetMixedState and state.energy_model_identity == self._identity,
                'sorption_state_identity')
        self.base.check(self._base_state(state))
        self._moisture(state)

    def evaluate(self, state: WetMixedState, temperature_k: float) -> ArlabosseSorptionPoint:
        """Add the exact nominal excess to base U and account for its projection."""
        self.check(state)
        t = _binary(temperature_k, positive=True)
        require(self.temperature_domain_k[0] <= t <= self.temperature_domain_k[1],
                'sorption_temperature_domain_exit')
        moisture = self._moisture(state)
        base = self.base.evaluate(self._base_state(state), t)
        plo, phi = map(F, self.pressure_domain_pa)
        p, p_error = F(base.pressure_pa), F(base.pressure_error_pa)
        require(plo <= p-p_error and p+p_error <= phi, 'sorption_pressure_domain_exit')
        hex_ = (F(self.wet._latent_reference)*(moisture-F(W_REF))-
                _integral(self.wet._q, F(W_REF), moisture))
        sex = (hex_-_integral(self.wet._m, F(W_REF), moisture))/F(T_REF)
        mass = F(self.dry_mass_kg)
        excess_u, excess_s = mass*hex_, mass*sex
        total = F(base.total_internal_energy_j)+excess_u
        energy = number(total)
        error = F(base.energy_error_j)+abs(F(energy)-total)
        mu, _, activity, _ = self.wet._excess(t, float(moisture))
        partial_h = F(self.wet._mass)*(F(self.wet._latent_reference)-_value(self.wet._q, moisture))
        values = {item.name: getattr(base, item.name) for item in fields(SourceWetPoint)}
        values.update(total_internal_energy_j=energy, energy_error_j=upper(error),
            model_identity=self._identity, qualification=QUALIFICATION,
            source_ids=tuple(sorted(set(base.source_ids+self.wet._source_ids()+
                                       (SORPTION_ID, MODEL_ID, MODEL_SHA256)))))
        point = ArlabosseSorptionPoint(**values,
            moisture_kg_water_per_kg_dry=number(moisture), excess_internal_energy_j=excess_u,
            excess_entropy_j_k=excess_s, excess_helmholtz_energy_j=excess_u-F(t)*excess_s,
            excess_chemical_potential_j_mol=number(F(mu)*F(self.wet._mass)),
            excess_partial_water_enthalpy_j_mol=number(partial_h), activity=activity)
        self.check(state)
        return point

    def invert(self, state: WetMixedState, policy: InversePolicy) -> SourceWetInverse:
        """Bisection on full U avoids target-subtraction loss and keeps the original policy.

        The same conservative residual/capacity and endpoint gates as the base
        apply. The entire temperature bracket must fit the pressure domain.
        """
        require(type(policy) is InversePolicy, 'explicit_inverse_policy')
        self.check(state)
        lo, hi = self.temperature_domain_k
        a, b = self.evaluate(state, lo), self.evaluate(state, hi)
        target = F(state.internal_energy_j)
        require(F(a.total_internal_energy_j)+F(a.energy_error_j) <= target <=
                F(b.total_internal_energy_j)-F(b.energy_error_j),
                'sorption_energy_target_outside_domain_or_resolution')
        for iteration in range(1, policy.maximum_iterations+1):
            t = (lo+hi)/2
            out = self.evaluate(state, t)
            residual = F(out.total_internal_energy_j)-target
            error = F(out.energy_error_j)
            bound = upper((abs(residual)+error)/F(out.minimum_heat_capacity_j_k))
            if abs(residual)+error <= F(policy.energy_tolerance_j) and F(bound) <= F(policy.temperature_tolerance_k):
                return SourceWetInverse(out, float(target), residual, bound, (lo, hi), iteration)
            require(abs(residual) > error, 'sorption_inverse_sign_unresolved')
            if residual > 0:
                hi = t
            else:
                lo = t
            require(hi-lo > math.ulp(t), 'sorption_unresolvable_temperature')
        raise MixedError('sorption_inverse_iteration_limit')

    def provenance(self) -> dict:
        """Return fresh source records, reference offset and unquantified extensions."""
        self._check()
        offset = F(self.dry_mass_kg)*self.caloric.specific_internal_energy(F(T_REF))
        return {'schema': 'arlabosse_rigid_sorption_storage_v1', 'model_identity': self._identity,
            'source_ids': self.source_ids, 'base': self.base.provenance(),
            'wet_definition': self.wet.definition(),
            'equations': {'F_ex': 'md*(hex(W)-T*sex(W))', 'U': 'U_base+md*hex(W)',
                'hex': 'L95*(W-0.8)-integral(0.8,W,q95)',
                'sex': '(hex-integral(0.8,W,m95))/368.15',
                'W': 'N_liquid*M_water/md; gas water excluded'},
            'temperature_domain_k': self.temperature_domain_k, 'pressure_domain_pa': self.pressure_domain_pa,
            'pressure_scope': 'exploratory zero-excess-volume extension, not measured pressure coverage',
            'dry_reference_offset_j': number(offset),
            'dry_reference_offset_exact_j': [offset.numerator, offset.denominator],
            'dry_reference_scope': 'base dry sensible U minus dry U referenced at 368.15 K; fixed md constant only',
            'excess_volume_m3': 0., 'fixed_inventory_capacity_change_j_k': 0.,
            'numerical_scope': 'exact rational integral of represented wet m/q nodes and W; base conditional energy error plus final U projection; mu/activity are nominal readouts',
            'pressure_extension_model_error': None, 'temperature_extension_model_error': None,
            'interpolation_model_error': None, 'experimental_uncertainty': None,
            'material_qualified': False, 'training_eligible': False, 'qualification': QUALIFICATION}
