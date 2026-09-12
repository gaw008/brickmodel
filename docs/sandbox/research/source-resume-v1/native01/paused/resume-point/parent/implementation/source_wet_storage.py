"""Fixed source dry mass coupled to the existing rigid water/gas storage.

Only explicit manufactured constant fluid volumes are currently admitted.
Source Cp does not supply skeletal volume, sorption, kinetics or validation of
the wet material. Inputs are exact binary64 states; unsupported conversion is
rejected rather than silently changing mass, temperature or target energy.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
import math

from .deforming_solid_storage import _digest
from .mass_storage_bridge import MixedError, number, require, upper
from .mass_wet_storage import (
    WetMixedState, WaterElementConvention, lower, check_wet_water, evaluate_wet_fluid,
)
from .phase_storage import InversePolicy
from .rigid_storage import RigidStorage, ClosedStorageState
from .source_mass_caloric import (
    ArlabosseMassCaloric, ReactionDisabled, FixedMassCaloricStorage, _exact,
    SOURCE_ID, NODE_ID, DELTA_H_NODE_ID,
)


def _binary(value, *, positive=False):
    exact = _exact(value)
    converted = number(exact, positive=positive)
    require(F(converted) == exact, 'nonrepresentable_binary64_input')
    return converted


@dataclass(frozen=True)
class ManufacturedFixedFluidVolume:
    """Available liquid-plus-gas volume, not bulk volume or solid density."""
    value_m3: float
    error_m3: float
    rationale: str
    classification: str = 'manufactured_test_fixture'

    def __post_init__(self):
        object.__setattr__(self, 'value_m3', _binary(self.value_m3, positive=True))
        object.__setattr__(self, 'error_m3', _binary(self.error_m3))
        self.check()

    def check(self):
        require(self.classification == 'manufactured_test_fixture', 'source_volume_not_yet_admitted')
        require(type(self.rationale) is str and bool(self.rationale.strip()), 'volume_rationale_required')
        require(type(self.value_m3) is float and type(self.error_m3) is float, 'binary64_volume_required')
        _binary(self.value_m3, positive=True)
        _binary(self.error_m3)
        require(0 <= self.error_m3 < self.value_m3, 'volume_uncertainty_excludes_positive_domain')

    @property
    def source_id(self):
        self.check()
        return 'manufactured:fixed_available_fluid_volume:'+_digest(self)


@dataclass(frozen=True)
class SourceWetPoint:
    fluid: ClosedStorageState
    total_internal_energy_j: float
    solid_internal_energy_j: F
    available_pore_volume_m3: float
    available_volume_error_m3: float
    global_pressure_error_pa: float
    extra_pressure_error_pa: float
    pressure_error_pa: float
    energy_error_j: float
    closed_heat_capacity_j_k: float
    minimum_heat_capacity_j_k: float
    model_identity: str
    source_ids: tuple[str, ...]
    total_enthalpy_j: None = None
    solid_volume_m3: None = None
    fit_error: None = None
    material_qualified: bool = False
    qualification: str = 'source_dry_caloric_with_test_volume_and_conditional_fluid_bounds_not_material_admission'

    @property
    def temperature_k(self):
        return self.fluid.mechanical.temperature_k

    @property
    def pressure_pa(self):
        return self.fluid.mechanical.pressure_pa

    @property
    def gas_volume_m3(self):
        return self.fluid.mechanical.gas_volume_m3


@dataclass(frozen=True)
class SourceWetInverse:
    point: SourceWetPoint
    target_energy_j: float
    energy_residual_j: F
    temperature_error_bound_k: float
    final_temperature_bracket_k: tuple[float, float]
    iterations: int


@dataclass(frozen=True)
class SourceWetStorage:
    caloric: ArlabosseMassCaloric
    dry_mass_kg: float
    fluid_template: RigidStorage
    volume: ManufacturedFixedFluidVolume
    temperature_domain_k: tuple
    chemistry: ReactionDisabled
    water_element_convention: WaterElementConvention
    _identity: str = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, 'dry_mass_kg', _binary(self.dry_mass_kg, positive=True))
        require(type(self.temperature_domain_k) is tuple and len(self.temperature_domain_k) == 2,
                'explicit_temperature_domain')
        object.__setattr__(self, 'temperature_domain_k', tuple(
            _binary(t, positive=True) for t in self.temperature_domain_k))
        object.__setattr__(self, '_identity', self.binding())

    @property
    def solid_ids(self):
        return (self.caloric.component_id,)

    @property
    def gas_ids(self):
        return tuple(self.fluid_template.mechanical.gas_species_ids)

    @property
    def water(self):
        return self.fluid_template.mechanical.water

    def binding(self):
        # Check supported collaborators before any source/provider callbacks.
        require(type(self.caloric) is ArlabosseMassCaloric, 'explicit_source_caloric_required')
        require(type(self.fluid_template) is RigidStorage, 'actual_fluid_storage_required')
        require(type(self.volume) is ManufacturedFixedFluidVolume, 'explicit_available_volume_required')
        require(type(self.chemistry) is ReactionDisabled, 'explicit_disabled_chemistry_required')
        require(type(self.water_element_convention) is WaterElementConvention, 'explicit_water_convention')
        require(type(self.dry_mass_kg) is float, 'binary64_fixed_mass_required')
        _binary(self.dry_mass_kg, positive=True)
        self.volume.check()
        self.caloric._check()
        require(self.gas_ids == ('O2', 'N2', 'H2O'), 'explicit_three_gas_order')
        require(self.chemistry.solid_ids == self.solid_ids and self.chemistry.gas_ids == self.gas_ids,
                'source_chemistry_layout')
        require(type(self.temperature_domain_k) is tuple and len(self.temperature_domain_k) == 2,
                'explicit_temperature_domain')
        lo, hi = (_binary(t, positive=True) for t in self.temperature_domain_k)
        source_lo, source_hi = self.caloric.temperature_domain_k
        env_lo, env_hi = self.fluid_template.envelope.temperature_range_k
        require(source_lo <= F(lo) < F(hi) <= source_hi and env_lo <= lo < hi <= env_hi,
                'source_or_fluid_temperature_domain_exit')
        check_wet_water(self.fluid_template, self.water_element_convention)
        self.water_element_convention.check()
        vapor = self.fluid_template.gas_phases['H2O'].caloric
        providers = tuple((type(w).__module__, type(w).__qualname__, w.implementation)
                          for w in (self.water, vapor._water))
        return _digest(('source_wet_fixed_mass_v1', self.caloric.binding(), self.dry_mass_kg,
            self.fluid_template, providers, self.volume, self.temperature_domain_k, self.chemistry,
            (self.water_element_convention.facts_sha256, self.water_element_convention.facts_json)))

    def _check(self):
        require(self.binding() == self._identity, 'source_wet_provider_content_changed')

    @property
    def model_identity(self):
        self._check()
        return self._identity

    @property
    def source_ids(self):
        self._check()
        values = (SOURCE_ID, NODE_ID, DELTA_H_NODE_ID, self.volume.source_id,
                  'ciaaw-2024-abridged-atomic-weights', self.water_element_convention.facts_sha256)
        values += self.fluid_template.envelope.source_ids+self.fluid_template.mechanical.constant_source_ids
        values += self.water.source_ids+tuple(x for p in self.fluid_template.gas_phases.values()
                                              for x in p.metadata.source_ids)
        return tuple(sorted(set(values)))

    def state(self, liquid_water_mol, gas_amounts_mol, internal_energy_j):
        self._check()
        require(type(gas_amounts_mol) is tuple, 'explicit_gas_inventory_tuple')
        state = WetMixedState((self.dry_mass_kg,), _binary(liquid_water_mol),
            tuple(_binary(n) for n in gas_amounts_mol), _binary(internal_energy_j), self._identity)
        self.check(state)
        return state

    def check(self, state):
        self._check()
        require(type(state) is WetMixedState and state.energy_model_identity == self._identity,
                'source_wet_state_identity')
        require(type(state.solid_mass_kg) is tuple and state.solid_mass_kg == (self.dry_mass_kg,),
                'fixed_dry_mass_cannot_change')
        require(type(state.gas_amounts_mol) is tuple and len(state.gas_amounts_mol) == len(self.gas_ids),
                'source_wet_gas_inventory_shape')
        for n in (*state.solid_mass_kg, state.liquid_water_mol, *state.gas_amounts_mol):
            require(type(n) is float and _binary(n) >= 0, 'invalid_binary64_inventory')
        require(type(state.internal_energy_j) is float, 'binary64_energy_required')
        _binary(state.internal_energy_j)

    def evaluate(self, state, temperature_k):
        self.check(state)
        t = _binary(temperature_k, positive=True)
        require(self.temperature_domain_k[0] <= t <= self.temperature_domain_k[1],
                'source_wet_temperature_domain_exit')
        self.chemistry.evaluate(state.solid_mass_kg, state.gas_amounts_mol)
        result = evaluate_wet_fluid(self.fluid_template, self.gas_ids, state.liquid_water_mol,
            state.gas_amounts_mol, t, self.volume.value_m3, F(self.volume.error_m3))
        out = result.point
        mass = F(self.dry_mass_kg)
        solid_u = mass*self.caloric.specific_internal_energy(F(t))
        total = F(out.internal_energy_j)+solid_u
        energy = number(total)
        err = (F(out.energy_error_bound_j)+abs(F(energy)-total)+F(state.liquid_water_mol)*
               F(result.fluid_template.envelope.liquid_abs_du_dp_bound_j_mol_pa)*result.extra_pressure_error_pa)
        cp = mass*self.caloric.cp(F(t))
        minimum_cp = mass*self.caloric.minimum_specific_heat_capacity(*map(F, self.temperature_domain_k))
        cmin = lower(F(out.minimum_heat_capacity_j_k)+minimum_cp)
        capacity = number(F(out.closed_heat_capacity_j_k)+cp, positive=True)
        require(cmin <= capacity, 'source_wet_capacity_lower_violation')
        point = SourceWetPoint(out, energy, solid_u, self.volume.value_m3, self.volume.error_m3,
            float(result.global_pressure_error_pa), float(result.extra_pressure_error_pa), result.pressure_error_pa,
            upper(err), capacity, cmin, self._identity, tuple(sorted(set(self.source_ids+out.source_ids))))
        self.check(state)
        return point

    def invert(self, state, policy):
        """Same interval/residual gates as the kg/mol wet host; no Newton truth claim."""
        require(type(policy) is InversePolicy, 'explicit_inverse_policy')
        lo, hi = self.temperature_domain_k
        a, b = self.evaluate(state, lo), self.evaluate(state, hi)
        target = F(state.internal_energy_j)
        require(F(a.total_internal_energy_j)+F(a.energy_error_j) <= target <=
                F(b.total_internal_energy_j)-F(b.energy_error_j),
                'source_wet_energy_target_outside_domain_or_resolution')
        for iteration in range(1, policy.maximum_iterations+1):
            t = (lo+hi)/2
            out = self.evaluate(state, t)
            residual = F(out.total_internal_energy_j)-target
            error = F(out.energy_error_j)
            bound = upper((abs(residual)+error)/F(out.minimum_heat_capacity_j_k))
            if abs(residual)+error <= F(policy.energy_tolerance_j) and F(bound) <= F(policy.temperature_tolerance_k):
                return SourceWetInverse(out, float(target), residual, bound, (lo, hi), iteration)
            require(abs(residual) > error, 'source_wet_inverse_sign_unresolved')
            if residual > 0:
                hi = t
            else:
                lo = t
            require(hi-lo > math.ulp(t), 'source_wet_unresolvable_temperature')
        raise MixedError('source_wet_inverse_iteration_limit')

    def provenance(self):
        """Separate source-backed dry term, fluid identity and test-only geometry."""
        self._check()
        dry = FixedMassCaloricStorage(self.caloric, F(self.dry_mass_kg),
            ReactionDisabled(self.solid_ids, (), self.chemistry.rationale))
        return {'schema': 'source_wet_storage_trace_v1', 'model_identity': self._identity,
            'material_qualified': False, 'source_ids': self.source_ids,
            'equation': 'U_total=U_fluid(T,N_liquid,N_gas,V_available)+m_dry*integral(T0,T,Cp_source(s)ds)',
            'dry_sensible_term': dry.registry_payload(),
            'fluid': {'identity': _digest(self.fluid_template), 'envelope': self.fluid_template.envelope.method,
                      'energy_reference': 'existing common liquid/vapor reference; no extra latent heat'},
            'available_volume': {'value_m3': self.volume.value_m3, 'error_m3': self.volume.error_m3,
                'classification': self.volume.classification, 'source_id': self.volume.source_id,
                'rationale': self.volume.rationale},
            'numerical_policy': 'exact represented binary64 states; Fraction source integration and directed aggregate bounds',
            'missing_material_evidence': ['same-material available fluid volume or skeletal volume and bulk geometry',
                'quantified dry Cp fit and incompressibility approximation errors',
                'sorption, material transport, reactions and sintering constitutive evidence'],
            'scope': 'fixed mass/available volume storage only; old WetPair and exact-event hosts are not admitted'}
