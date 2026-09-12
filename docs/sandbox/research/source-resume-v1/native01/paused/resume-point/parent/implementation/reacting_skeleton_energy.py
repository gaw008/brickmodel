"""Explicit manufactured, temperature-independent composition-scaled skeleton.

For q(N)=q0+sum(w_i*N_i), energies, fixed-composition deformation powers,
Piola stresses and viscous dissipation are q times the reference formulas.
Composition derivatives are storage derivatives, NEVER external power. Bounds
cover exact represented binary inputs only, not parameter or constitutive error.
The wrapped fixed-inventory model remains unchanged and retains its guards.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.skeleton_energy import (
    DiagonalSkeletonEnergy, SkeletonEnergyState, SkeletonEnergyError,
    _Interval, _number, _label, _output,
)


@dataclass(frozen=True, kw_only=True)
class ReactingSkeletonEnergyState(SkeletonEnergyState):
    elastic_composition_derivative_j_mol: Mapping[str, float]
    interface_composition_derivative_j_mol: Mapping[str, float]


def _enclosure(value: float, bound: float) -> _Interval:
    return _Interval(Fraction(value)-Fraction(bound), Fraction(value)+Fraction(bound))


@dataclass(frozen=True, kw_only=True)
class ManufacturedReactingSkeletonEnergy:
    reference_model: DiagonalSkeletonEnergy
    composition_offset: float
    composition_weights_per_mol: tuple[tuple[str, float], ...]
    model_id: str
    version: str
    classification: str
    allow_manufactured: bool

    def __post_init__(self) -> None:
        if type(self.reference_model) is not DiagonalSkeletonEnergy:
            raise SkeletonEnergyError('explicit_reference_skeleton_required')
        if self.classification != 'manufactured_test_fixture' or type(self.allow_manufactured) is not bool or not self.allow_manufactured:
            raise SkeletonEnergyError('explicit_manufactured_model_required')
        _label(self.model_id)
        _label(self.version)
        object.__setattr__(self, 'composition_offset', _number(self.composition_offset, 'composition_offset', positive=True))
        weights = self.composition_weights_per_mol
        if not isinstance(weights, tuple) or not weights:
            raise SkeletonEnergyError('complete_composition_weights_required')
        normalized = []
        for item in weights:
            if not isinstance(item, tuple) or len(item) != 2:
                raise SkeletonEnergyError('invalid_composition_weights')
            key, value = item
            _label(key)
            normalized.append((key, _number(value, 'composition_weight', nonnegative=True)))
        keys = [key for key, _ in normalized]
        if len(set(keys)) != len(keys) or set(keys) != dict(self.reference_solid_inventory_mol).keys():
            raise SkeletonEnergyError('complete_composition_weights_required')
        object.__setattr__(self, 'composition_weights_per_mol', tuple(sorted(normalized)))

    @property
    def reference(self) -> ReferenceSlab:
        return self.reference_model.reference

    @property
    def cell_index(self) -> int:
        return self.reference_model.cell_index

    @property
    def reference_volume_m3(self) -> float:
        return self.reference_model.reference_volume_m3

    @property
    def solid_provider_identity(self) -> tuple[object, ...]:
        return self.reference_model.solid_provider_identity

    @property
    def source_ids(self) -> tuple[str, ...]:
        return self.reference_model.source_ids

    @property
    def reference_solid_inventory_mol(self) -> tuple[tuple[str, float], ...]:
        return self.reference_model.fixed_solid_inventory_mol

    @property
    def identity(self) -> tuple[object, ...]:
        return (self.model_id, self.version, self.classification, self.reference_model.identity,
                self.composition_offset, self.composition_weights_per_mol,
                'q=q0+sum(w_i*N_i);E_el=q*E_el_ref;E_interface=q*E_interface_ref',
                'fixed_N_Piola_power_dissipation_Rayleigh=q*reference;dE_dN_i=w_i*E_reference',
                'temperature_independent_positive_offset_nonnegative_weights_complete_nonnegative_N_some_positive_v1',
                'fraction_exact_q_weights_base_value_plus_minus_bound_outward_binary64_v1')

    def evaluate(self, *, normal_stretch: float, tangential_stretch: float, normal_rate_per_s: float,
                 tangential_rate_per_s: float, solid_inventory_mol: Mapping[str, float]) -> ReactingSkeletonEnergyState:
        if not isinstance(solid_inventory_mol, Mapping) or set(solid_inventory_mol) != dict(self.reference_solid_inventory_mol).keys():
            raise SkeletonEnergyError('complete_current_solid_inventory_required')
        amounts = {key: _number(solid_inventory_mol[key], 'solid_mol', nonnegative=True)
                   for key, _ in self.composition_weights_per_mol}
        if not any(amounts.values()):
            raise SkeletonEnergyError('positive_current_solid_inventory_required')
        q = Fraction(self.composition_offset) + sum(Fraction(weight)*Fraction(amounts[key])
                                                   for key, weight in self.composition_weights_per_mol)
        base = self.reference_model.evaluate(normal_stretch=normal_stretch,
            tangential_stretch=tangential_stretch, normal_rate_per_s=normal_rate_per_s,
            tangential_rate_per_s=tangential_rate_per_s,
            solid_inventory_mol=dict(self.reference_solid_inventory_mol))
        values, bounds = {}, {}
        for key, error in base.numerical_error_bounds.items():
            value = getattr(base, key)
            if isinstance(value, tuple):
                pairs = tuple(_output(_enclosure(v, e)*q) for v, e in zip(value, error, strict=True))
                values[key] = tuple(v for v, _ in pairs)
                bounds[key] = tuple(e for _, e in pairs)
            else:
                values[key], bounds[key] = _output(_enclosure(value, error)*q)
        for prefix in ('elastic', 'interface'):
            key = prefix+'_composition_derivative_j_mol'
            energy_key = prefix+'_energy_j'
            enclosure = _enclosure(getattr(base, energy_key), base.numerical_error_bounds[energy_key])
            pairs = {name: _output(enclosure*Fraction(weight))
                     for name, weight in self.composition_weights_per_mol}
            values[key] = MappingProxyType({name: pair[0] for name, pair in pairs.items()})
            bounds[key] = MappingProxyType({name: pair[1] for name, pair in pairs.items()})
        return ReactingSkeletonEnergyState(**values, numerical_error_bounds=MappingProxyType(bounds),
            model_identity=self.identity, normal_stretch=base.normal_stretch,
            tangential_stretch=base.tangential_stretch, normal_rate_per_s=base.normal_rate_per_s,
            tangential_rate_per_s=base.tangential_rate_per_s,
            qualification='manufactured_composition_scaled_temperature_independent_exact_binary_input_numerical_enclosures_only')
