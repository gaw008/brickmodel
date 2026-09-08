"""Current global-geometry fixed-solid thermodynamics without a mechanical closure.

Explicit manufactured point storage, not a free traction solver or material model.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from fractions import Fraction
import math

import numpy as np

from sludge_sandbox.deforming_solid_storage import (
    DeformingStorageError, SCOPE, TotalEnergyTarget, _digest, _label, _num,
    _out, _upper, solid_provider_identity,
)
from sludge_sandbox.dynamic_solid_storage import DynamicStorageErrorBounds
from sludge_sandbox.geometry import CurrentSlab
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.skeleton_energy import DiagonalSkeletonEnergy, SkeletonEnergyState
from sludge_sandbox.solid_fluid_storage import SolidFluidStorage, SolidFluidStorageError, SolidFluidState, SolidFluidInverse


@dataclass(frozen=True)
class CurrentDeformationPoint:
    normal_stretches: tuple[float, ...]
    cell_index: int
    tangential_stretch: float
    current: CurrentSlab


@dataclass(frozen=True)
class CurrentSolidState:
    thermal_state: SolidFluidState
    skeleton_state: SkeletonEnergyState
    deformation: CurrentDeformationPoint
    total_energy_j: float
    energy_error_bound_j: float
    mechanical_energy_error_bound_j: float
    total_addition_roundoff_j: float
    current_bulk_error_bound_m3: float
    error_bounds: DynamicStorageErrorBounds
    model_identity: tuple
    current_storage: SolidFluidStorage
    energy_scope: str = SCOPE
    qualification: str = 'manufactured_fixed_solid_current_state_storage_not_material_admission'



@dataclass(frozen=True)
class CurrentSolidInverse:
    state: CurrentSolidState
    thermal_inverse: SolidFluidInverse
    target: TotalEnergyTarget
    total_energy_residual_j: float
    subtraction_roundoff_j: float
    temperature_error_bound_k: float


@dataclass(frozen=True, kw_only=True)
class CurrentSolidStorage:
    template: SolidFluidStorage
    skeleton: DiagonalSkeletonEnergy
    error_bounds: DynamicStorageErrorBounds
    model_id: str
    version: str
    allow_manufactured: bool
    _template_digest: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (type(self.template) is not SolidFluidStorage or
                type(self.skeleton) is not DiagonalSkeletonEnergy or
                type(self.error_bounds) is not DynamicStorageErrorBounds):
            raise DeformingStorageError('explicit_dynamic_storage_skeleton_bounds_required')
        if self.allow_manufactured is not True:
            raise DeformingStorageError('manufactured_opt_in_required')
        _label(self.model_id)
        _label(self.version)
        if solid_provider_identity(self.template.solid_phases) != self.skeleton.solid_provider_identity:
            raise DeformingStorageError('actual_solid_identity_mismatch')
        if {key for key, _ in self.skeleton.fixed_solid_inventory_mol} != set(self.template.solid_phases):
            raise DeformingStorageError('complete_fixed_solid_inventory_required')
        expected, actual = self.skeleton.reference_volume_m3, self.template.bulk_volume_m3
        if abs(actual-expected) > 2*max(math.ulp(actual), math.ulp(expected)):
            raise DeformingStorageError('reference_bulk_volume_mismatch')
        for domain in (self.error_bounds.normal_stretch_range, self.error_bounds.tangential_stretch_range):
            if not self.skeleton.stretch_range[0] <= domain[0] < domain[1] <= self.skeleton.stretch_range[1]:
                raise DeformingStorageError('error_domain_outside_skeleton_domain')
        object.__setattr__(self, '_template_digest', _digest(self.template))

    @property
    def identity(self) -> tuple:
        return (self.model_id, self.version, self._template_digest, self.skeleton.identity,
                _digest(self.error_bounds), 'current_fixed_solid_total_point_v1', SCOPE)

    def target(self, value_j: float, error_bound_j: float) -> TotalEnergyTarget:
        return TotalEnergyTarget(value_j, error_bound_j, self.identity)

    def _prepare(self, normal_stretches: tuple[float, ...], tangential_stretch: float,
                 solid_mol: Mapping[str, float]) -> tuple[CurrentDeformationPoint, SkeletonEnergyState, SolidFluidStorage, float, float]:
        if _digest(self.template) != self._template_digest:
            raise DeformingStorageError('runtime_template_identity_changed')
        reference = self.skeleton.reference
        # Global geometry validates complete numeric/positive shape first.
        geometry = reference.deform(normal_stretches, tangential_stretch=tangential_stretch)
        normals=tuple(float(v) for v in normal_stretches)
        for value in normals:
            if not self.error_bounds.normal_stretch_range[0] <= value <= self.error_bounds.normal_stretch_range[1]:
                raise DeformingStorageError('current_stretch_outside_error_domain')
        normal_stretch=normals[self.skeleton.cell_index]
        # Validate exact fixed inventory and original skeleton stretch domain.
        skeleton = self.skeleton.evaluate(normal_stretch=normal_stretch,
            tangential_stretch=tangential_stretch, normal_rate_per_s=0., tangential_rate_per_s=0.,
            solid_inventory_mol=solid_mol)
        normal, tangent = skeleton.normal_stretch, skeleton.tangential_stretch
        for value, domain in ((normal, self.error_bounds.normal_stretch_range),
                              (tangent, self.error_bounds.tangential_stretch_range)):
            if not domain[0] <= value <= domain[1]:
                raise DeformingStorageError('current_stretch_outside_error_domain')
        reference = self.skeleton.reference
        # A bytes-backed current-geometry snapshot cannot be made writable again.
        geometry = CurrentSlab(*(np.frombuffer(value.tobytes(), dtype=value.dtype).reshape(value.shape)
            for value in (geometry.widths_m, geometry.faces_m, geometry.centers_m,
                          geometry.face_areas_m2, geometry.reference_volumes_m3,
                          geometry.volumes_m3, geometry.volume_ratios)))
        deformation = CurrentDeformationPoint(normals, self.skeleton.cell_index, tangent, geometry)
        exact_v0 = Fraction(reference.reference_area_m2)*Fraction(reference.half_thickness_m)/reference.cells
        reference_error = Fraction(self.template.bulk_volume_error_m3)+abs(Fraction(self.template.bulk_volume_m3)-exact_v0)
        jacobian = Fraction(normal)*Fraction(tangent)**2
        current = float(geometry.volumes_m3[self.skeleton.cell_index])
        volume_error = (jacobian*reference_error+abs(Fraction(current)-jacobian*exact_v0)+
                        Fraction(self.error_bounds.additional_bulk_volume_error_m3))
        bulk_error = _upper(volume_error)
        exact_solid_volume = sum((Fraction(float(solid_mol[key]))*Fraction(phase.molar_volume_m3_mol)
                                  for key, phase in self.template.solid_phases.items()), Fraction())
        available = Fraction(current)-exact_solid_volume
        if available <= 0:
            raise SolidFluidStorageError('no_positive_fluid_available_volume')
        fluid = replace(self.template.fluid_template, mechanical=replace(
            self.template.fluid_template.mechanical, available_pore_volume_m3=_out(available)))
        storage = replace(self.template, fluid_template=fluid, bulk_volume_m3=current,
                          bulk_volume_error_m3=bulk_error)
        elastic_error = Fraction(skeleton.numerical_error_bounds['elastic_energy_j'])
        v0_error = reference_error+abs(Fraction(self.skeleton.reference_volume_m3)-exact_v0)
        geometry_error = ((abs(Fraction(skeleton.elastic_energy_j))+elastic_error)*v0_error/
                          Fraction(self.skeleton.reference_volume_m3))
        mechanical_error = (elastic_error+Fraction(skeleton.numerical_error_bounds['interface_energy_j'])+
                            geometry_error+Fraction(self.error_bounds.additional_mechanical_energy_error_j))
        return deformation, skeleton, storage, _upper(mechanical_error), bulk_error

    def _assemble(self, thermal: SolidFluidState, deformation: CurrentDeformationPoint,
                  skeleton: SkeletonEnergyState, storage: SolidFluidStorage,
                  error: float, bulk_error: float) -> CurrentSolidState:
        exact = Fraction(thermal.internal_energy_j)+Fraction(skeleton.elastic_energy_j)+Fraction(skeleton.interface_energy_j)
        total = _out(exact)
        rounding = abs(Fraction(total)-exact)
        bound = _upper(Fraction(thermal.energy_error_bound_j)+Fraction(error)+rounding)
        return CurrentSolidState(thermal, skeleton, deformation, total, bound, error,
            _upper(rounding), bulk_error, self.error_bounds, self.identity, storage)

    def forward(self, temperature_k: float, *, normal_stretches: tuple[float, ...], tangential_stretch: float,
                liquid_mol: float, gas_mol: Mapping[str, float], solid_mol: Mapping[str, float]) -> CurrentSolidState:
        deformation, skeleton, storage, error, bulk = self._prepare(normal_stretches, tangential_stretch, solid_mol)
        thermal = storage.evaluate_at_temperature(temperature_k, liquid_mol, gas_mol, solid_mol)
        return self._assemble(thermal, deformation, skeleton, storage, error, bulk)

    def temperature_from_total_energy(self, target: TotalEnergyTarget, *, normal_stretches: tuple[float, ...],
            tangential_stretch: float, liquid_mol: float, gas_mol: Mapping[str, float],
            solid_mol: Mapping[str, float],
            temperature_bracket_k: tuple[float, float], policy: InversePolicy) -> CurrentSolidInverse:
        if type(target) is not TotalEnergyTarget or target.energy_scope != SCOPE or target.model_identity != self.identity:
            raise DeformingStorageError('matching_explicit_total_energy_target_required')
        deformation, skeleton, storage, error, bulk = self._prepare(normal_stretches, tangential_stretch, solid_mol)
        exact = Fraction(target.value_j)-Fraction(skeleton.elastic_energy_j)-Fraction(skeleton.interface_energy_j)
        thermal_target = _out(exact)
        rounding = abs(Fraction(thermal_target)-exact)
        target_error = _upper(Fraction(target.error_bound_j)+Fraction(error)+rounding)
        inverse = storage.temperature_from_energy(thermal_target, liquid_mol, gas_mol, solid_mol,
            temperature_bracket_k, policy, target_energy_error_bound_j=target_error)
        state = self._assemble(inverse.state, deformation, skeleton, storage, error, bulk)
        residual = _out(Fraction(state.total_energy_j)-Fraction(target.value_j))
        return CurrentSolidInverse(state, inverse, target, residual, _upper(rounding), inverse.temperature_error_bound_k)
