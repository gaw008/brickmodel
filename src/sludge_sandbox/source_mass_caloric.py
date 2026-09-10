"""Source-specific fixed dry-mass sensible storage, without invented chemistry.

This is a point caloric adapter, not a wet-cell/PDE solver or material admission.
Under the explicitly selected incompressible, temperature-independent-volume
approximation, source delta_h equals delta_u. The fit's physical uncertainty is
unknown. All arithmetic here is exact rational arithmetic on the nominal fit;
float inputs mean their binary64 value, unlike the source reader's decimal mode.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction as F
import math

from .arlabosse_caloric import (
    ArlabosseDryCaloric, SOURCE_SHA256, SOURCE_ID, NODE_ID, DELTA_H_NODE_ID,
)
from .deforming_solid_storage import _digest
from .phase_storage import InversePolicy


MATERIAL_ID = 'arlabosse2005-original-mixed-feed-dry-matter'
TEMPERATURE_DOMAIN_K = (F(6163, 20), F(7563, 20))
ASSUMPTION = 'fixed_composition_incompressible_temperature_independent_volume'
ENERGY_NODE_ID = 'ARLABOSSE2005_FIXED_DRY_MASS_SENSIBLE_U'


class SourceMassCaloricError(ValueError):
    """The fixed-composition source caloric contract cannot be satisfied."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise SourceMassCaloricError(reason)


def _exact(value: object) -> F:
    if type(value) in (int, F):
        return F(value)
    if type(value) is float and math.isfinite(value):
        return F.from_float(value)
    if type(value) is Decimal and value.is_finite():
        return F(value)
    raise SourceMassCaloricError('finite_exact_numeric_required')


def _labels(values: tuple[str, ...]) -> None:
    _require(type(values) is tuple and all(type(v) is str and bool(v.strip())
             and v == v.strip() for v in values), 'explicit_component_ids_required')
    _require(len(set(values)) == len(values), 'duplicate_component_id')


@dataclass(frozen=True)
class DisabledChemicalRates:
    solid_kg_s: tuple[F, ...]
    gas_mol_s: tuple[F, ...]
    chemical_reference_power_w: F = F(0)
    phase_transfer_included: bool = False


@dataclass(frozen=True)
class ReactionDisabled:
    """An explicit stage choice; says nothing about formation energies or phase transfer."""
    solid_ids: tuple[str, ...]
    gas_ids: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        _labels(self.solid_ids)
        _labels(self.gas_ids)
        _require(bool(self.solid_ids or self.gas_ids), 'empty_chemical_layout')
        _require(not set(self.solid_ids).intersection(self.gas_ids), 'phase_component_overlap')
        _require(type(self.rationale) is str and bool(self.rationale.strip()), 'reaction_disabled_rationale_required')

    def evaluate(self, solid_masses_kg: tuple, gas_amounts_mol: tuple) -> DisabledChemicalRates:
        for values, ids in ((solid_masses_kg, self.solid_ids), (gas_amounts_mol, self.gas_ids)):
            _require(type(values) is tuple and len(values) == len(ids), 'chemical_inventory_layout')
            _require(all(_exact(v) >= 0 for v in values), 'negative_chemical_inventory')
        return DisabledChemicalRates((F(0),)*len(self.solid_ids), (F(0),)*len(self.gas_ids))


@dataclass(frozen=True)
class ArlabosseMassCaloric:
    provider: ArlabosseDryCaloric
    reference_temperature_k: F
    assumption: str = ASSUMPTION
    _identity: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _require(type(self.provider) is ArlabosseDryCaloric, 'explicit_arlabosse_provider_required')
        _require(self.assumption == ASSUMPTION, 'unsupported_caloric_assumption')
        object.__setattr__(self, 'reference_temperature_k', self._temperature(self.reference_temperature_k))
        object.__setattr__(self, '_identity', self.binding())

    @property
    def component_id(self) -> str:
        return MATERIAL_ID

    @property
    def temperature_domain_k(self) -> tuple[F, F]:
        return TEMPERATURE_DOMAIN_K

    @property
    def specific_volume_m3_kg(self) -> None:
        return None

    def _temperature(self, value: object) -> F:
        t = _exact(value)
        _require(TEMPERATURE_DOMAIN_K[0] <= t <= TEMPERATURE_DOMAIN_K[1], 'temperature_outside_source_domain')
        return t

    def binding(self) -> str:
        _require(type(self.provider) is ArlabosseDryCaloric, 'explicit_arlabosse_provider_required')
        _require(self.assumption == ASSUMPTION, 'unsupported_caloric_assumption')
        _require(type(self.reference_temperature_k) is F, 'exact_reference_temperature_required')
        self._temperature(self.reference_temperature_k)
        # Reusing cp performs the existing exact metadata and asset checks.
        self.provider.cp(self.reference_temperature_k, unit='K')
        return _digest(('source_mass_caloric_v1', SOURCE_SHA256, MATERIAL_ID,
                        TEMPERATURE_DOMAIN_K, self.reference_temperature_k, F(0), self.assumption,
                        'exact_rational_float_binary64_input_no_physical_fit_error_bound'))

    def _check(self) -> None:
        _require(self.binding() == self._identity, 'caloric_content_changed')

    def cp(self, temperature_k: object) -> F:
        self._check()
        return self.provider.cp(self._temperature(temperature_k), unit='K').value

    def specific_internal_energy(self, temperature_k: object) -> F:
        """Relative u(T0)=0 coordinate; never an absolute formation energy."""
        self._check()
        return self.provider.delta_h(self.reference_temperature_k, self._temperature(temperature_k), unit='K').value

    def minimum_specific_heat_capacity(self, lower_k: object, upper_k: object) -> F:
        lower, upper = self._temperature(lower_k), self._temperature(upper_k)
        _require(lower <= upper, 'ordered_temperature_bracket_required')
        # The pinned source Eq2 has strictly positive slope. This is a bound
        # on its nominal fit over the whole interval, not on unknown fit error.
        return self.cp(lower)


@dataclass(frozen=True)
class CaloricEnergyTarget:
    internal_energy_j: F
    model_identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'internal_energy_j', _exact(self.internal_energy_j))
        _require(type(self.model_identity) is str and len(self.model_identity) == 64
                 and all(c in '0123456789abcdef' for c in self.model_identity), 'energy_identity_required')


@dataclass(frozen=True)
class MassCaloricPoint:
    temperature_k: F
    internal_energy_j: F
    closed_heat_capacity_j_k: F
    minimum_heat_capacity_j_k: F
    model_identity: str
    source_ids: tuple[str, ...] = (SOURCE_ID, NODE_ID, DELTA_H_NODE_ID)
    node_id: str = ENERGY_NODE_ID
    numerical_energy_error_bound_j: F = F(0)
    fit_error: None = None
    material_qualified: bool = False
    qualification: str = 'conditional_incompressible_fixed_dry_mass_nominal_fit_not_wet_or_reacting_storage'


@dataclass(frozen=True)
class MassCaloricInverse:
    point: MassCaloricPoint
    energy_residual_j: F
    temperature_error_bound_k: F
    final_temperature_bracket_k: tuple[F, F]
    iterations: int


@dataclass(frozen=True)
class FixedMassCaloricStorage:
    caloric: ArlabosseMassCaloric
    dry_mass_kg: F
    chemistry: ReactionDisabled
    _identity: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _require(type(self.caloric) is ArlabosseMassCaloric, 'explicit_source_mass_caloric_required')
        mass = _exact(self.dry_mass_kg)
        _require(mass > 0, 'positive_fixed_dry_mass_required')
        object.__setattr__(self, 'dry_mass_kg', mass)
        _require(type(self.chemistry) is ReactionDisabled, 'explicit_reaction_disabled_required')
        _require(self.chemistry.solid_ids == (self.caloric.component_id,) and not self.chemistry.gas_ids,
                 'fixed_dry_chemistry_layout')
        object.__setattr__(self, '_identity', self.binding())

    def binding(self) -> str:
        _require(type(self.caloric) is ArlabosseMassCaloric, 'explicit_source_mass_caloric_required')
        _require(type(self.chemistry) is ReactionDisabled, 'explicit_reaction_disabled_required')
        _require(type(self.dry_mass_kg) is F and self.dry_mass_kg > 0, 'positive_fixed_dry_mass_required')
        _require(self.chemistry.solid_ids == (self.caloric.component_id,) and not self.chemistry.gas_ids,
                 'fixed_dry_chemistry_layout')
        self.caloric._check()
        return _digest(('fixed_dry_mass_caloric_v1', self.caloric.binding(), self.dry_mass_kg, self.chemistry))

    def _check(self) -> None:
        _require(self.binding() == self._identity, 'fixed_mass_content_changed')

    @property
    def model_identity(self) -> str:
        self._check()
        return self._identity

    @property
    def material_qualified(self) -> bool:
        return False

    def target(self, energy_j: object) -> CaloricEnergyTarget:
        return CaloricEnergyTarget(_exact(energy_j), self.model_identity)

    def evaluate(self, temperature_k: object) -> MassCaloricPoint:
        self._check()
        t = self.caloric._temperature(temperature_k)
        # Chemistry is explicitly zero; no A/B components, oxygen reference,
        # or ReactionNetwork is constructed to obtain this sensible energy.
        self.chemistry.evaluate((self.dry_mass_kg,), ())
        point = MassCaloricPoint(t, self.dry_mass_kg*self.caloric.specific_internal_energy(t),
            self.dry_mass_kg*self.caloric.cp(t), self.dry_mass_kg*self.caloric.minimum_specific_heat_capacity(
                *self.caloric.temperature_domain_k), self._identity)
        self._check()
        return point

    def invert(self, target: CaloricEnergyTarget, policy: InversePolicy) -> MassCaloricInverse:
        self._check()
        _require(type(target) is CaloricEnergyTarget and target.model_identity == self._identity, 'target_identity_mismatch')
        _require(type(policy) is InversePolicy, 'explicit_inverse_policy_required')
        lo, hi = self.caloric.temperature_domain_k
        a, b = self.evaluate(lo), self.evaluate(hi)
        energy = target.internal_energy_j
        _require(a.internal_energy_j <= energy <= b.internal_energy_j, 'energy_target_outside_source_domain')
        for endpoint in (a, b):
            if endpoint.internal_energy_j == energy:
                return MassCaloricInverse(endpoint, F(0), F(0), (lo, hi), 0)
        for iteration in range(1, policy.maximum_iterations+1):
            t = (lo+hi)/2
            point = self.evaluate(t)
            residual = point.internal_energy_j-energy
            bound = abs(residual)/point.minimum_heat_capacity_j_k
            if abs(residual) <= F(policy.energy_tolerance_j) and bound <= F(policy.temperature_tolerance_k):
                return MassCaloricInverse(point, residual, bound, (lo, hi), iteration)
            if residual > 0:
                hi = t
            else:
                lo = t
        raise SourceMassCaloricError('caloric_inverse_iteration_limit')

    def registry_payload(self) -> dict:
        """Trace coordinates and assumptions separately from measured Cp evidence."""
        self._check()
        payload = self.caloric.provider.registry_payload()
        domain = payload['nodes'][0]['domain']
        assumption_id = 'ARLABOSSE2005_FIXED_COMPOSITION_RIGID_ASSUMPTION'
        anchor_id = 'ARLABOSSE2005_SENSIBLE_REFERENCE_T'
        mass_id = 'ARLABOSSE2005_FIXED_DRY_MASS'
        chemistry_id = 'ARLABOSSE2005_DISABLED_CHEMISTRY_CHOICE'
        common = {'basis': 'kg dry matter of original Arlabosse2005 mixed feed',
            'dependencies': [], 'citations': [], 'domain': domain,
            'applicability': {'status': 'conditional', 'rationale': 'Original source material and fixed-composition caloric stage only.'},
            'uncertainty': {'status': 'not_applicable', 'rationale': 'Explicit coordinate or scenario choice, not a measured material parameter.'}}
        def design(identifier: str, unit: str, value: object, rationale: str) -> dict:
            return {**common, 'id': identifier, 'evidence_kind': 'virtual_design_choice',
                    'role': 'design_input', 'unit': unit, 'value': value, 'rationale': rationale,
                    'value_encoding': 'exact_rational_numerator_denominator' if type(value) is dict else 'scalar'}
        payload['nodes'].extend([
            design(assumption_id, '1', 1, 'Explicit incompressible temperature-independent-volume approximation; its physical error is unknown. No volume value is supplied.'),
            {**common, 'id': anchor_id, 'evidence_kind': 'numerical_policy', 'role': 'numerical_setting',
             'unit': 'K', 'value': {'numerator': self.caloric.reference_temperature_k.numerator,
                                   'denominator': self.caloric.reference_temperature_k.denominator},
             'value_encoding': 'exact_rational_numerator_denominator',
             'rationale': 'Exact rational reference temperature with relative u(T0)=0; no formation enthalpy is assigned.'},
            design(mass_id, 'kg', {'numerator': self.dry_mass_kg.numerator, 'denominator': self.dry_mass_kg.denominator},
                   'Exact rational fixed dry mass; changing mass creates a different storage identity.'),
            design(chemistry_id, '1', 0, self.chemistry.rationale),
            {**common, 'id': ENERGY_NODE_ID, 'role': 'equation', 'evidence_kind': 'derived_from_evidence',
             'unit': 'J', 'value': 'U=m*integral(T0,T,Cp(T)dT), relative u(T0)=0',
             'dependencies': [DELTA_H_NODE_ID, assumption_id, anchor_id, mass_id, chemistry_id],
             'derivation': 'source_mass_caloric.FixedMassCaloricStorage.evaluate reuses source delta_h under explicit incompressibility and fixed composition; no wet volume closure.',
             'uncertainty': {'status': 'unquantified', 'rationale': 'Source fit uncertainty and approximation error are unknown; exact rational arithmetic bounds only numerical error.'}}
        ])
        return payload
