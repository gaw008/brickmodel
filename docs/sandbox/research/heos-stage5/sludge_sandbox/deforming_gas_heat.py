"""Prescribed compatible gas chambers with explicit pressure-matched actuator work.

This is a gas-only mechanical integration model, not porous brick skeleton
mechanics. Transport is relative to the moving partitions. Each chamber's
external actuator supplies -p*dV, including internal partition work when
neighboring pressures differ. Flow enthalpy already contains its flow work.
"""
from dataclasses import dataclass, field, replace

import numpy as np
from numpy.typing import NDArray

from .deformation_program import (
    PrescribedSlabMotion, MotionSnapshot, ReferenceGeometryAlignment, DeformationProgramError,
)
from .gas_heat_model import GasHeatModel, GasHeatEvaluation, _sources
from .integration import ConservedState, IntegrationError, Rates, _array


class DeformingGasHeatError(IntegrationError):
    """Unsupported mechanics, inconsistent geometry or unrepresentable work."""


@dataclass(frozen=True, kw_only=True)
class DeformingGasHeatEvaluation:
    rates: Rates
    motion: MotionSnapshot
    gas_evaluation: GasHeatEvaluation
    mechanical_power_w: NDArray[np.float64]
    pressure_for_work_pa: NDArray[np.float64]
    work_model_identity: tuple
    source_ids: tuple[str, ...]
    qualification: str = 'prescribed_gas_actuator_work_not_skeleton_or_sintering_prediction'


@dataclass(frozen=True, kw_only=True)
class DeformingGasHeat:
    base_model: GasHeatModel
    motion: PrescribedSlabMotion
    mechanical_regime: str
    work_model_id: str
    work_model_version: str
    work_source_ids: tuple[str, ...]
    allow_manufactured: bool = False
    reference_alignment: ReferenceGeometryAlignment = field(init=False)

    def __post_init__(self):
        # A custom operator could supply body heat or lab-frame advection;
        # these need separate contracts and cannot enter through inheritance.
        if type(self.base_model) is not GasHeatModel:
            raise DeformingGasHeatError('explicit_gas_only_base_required')
        if type(self.motion) is not PrescribedSlabMotion:
            raise DeformingGasHeatError('explicit_compatible_motion_required')
        if self.mechanical_regime != 'prescribed_cellwise_quasistatic_gas_chambers':
            raise DeformingGasHeatError('unsupported_mechanical_regime')
        if type(self.allow_manufactured) is not bool:
            raise DeformingGasHeatError('invalid_manufactured_permission')
        base = self.base_model
        if base.coefficient_classification != 'manufactured':
            raise DeformingGasHeatError('fixed_transport_requires_explicit_manufactured_network')
        if not self.allow_manufactured:
            raise DeformingGasHeatError('manufactured_requires_explicit_host_permission')
        for value in (self.work_model_id, self.work_model_version):
            if not isinstance(value, str) or not value or value != value.strip():
                raise DeformingGasHeatError('explicit_work_model_identity_required')
        try:
            sources = _sources(self.work_source_ids)
        except IntegrationError as exc:
            raise DeformingGasHeatError(str(exc)) from exc
        if any(value != value.strip() for value in sources):
            raise DeformingGasHeatError('invalid_work_source_id')
        object.__setattr__(self, 'work_source_ids', sources)
        try:
            alignment = self.motion.validate_reference_geometry(
                cell_count=len(base.cell_widths_m), face_area_m2=base.face_area_m2,
                cell_widths_m=base.cell_widths_m, gas_volumes_m3=base.gas_volumes_m3)
        except DeformationProgramError as exc:
            raise DeformingGasHeatError(str(exc)) from exc
        object.__setattr__(self, 'reference_alignment', alignment)

    @property
    def material_qualified(self):
        return False

    @property
    def scientific_status(self):
        return 'prescribed_gas_mechanical_integration_not_material_qualified'

    @property
    def work_model_identity(self):
        return (self.work_model_id, self.work_model_version, self.mechanical_regime,
                'minus_current_cell_pressure_times_total_cell_volume_rate', self.work_source_ids)

    @property
    def source_ids(self):
        return tuple(sorted(set(self.base_model.source_ids + self.motion.source_ids + self.work_source_ids)))

    def breakpoints_s(self, start_s, end_s):
        return self.motion.breakpoints_s(start_s, end_s)

    def evaluate(self, state: ConservedState, time_s: float) -> DeformingGasHeatEvaluation:
        base = self.base_model
        # Check the original frozen caloric binding BEFORE replace copies it;
        # otherwise reconstruction could legitimize an edited mutable wrapper.
        base._check_state(state)
        try:
            snapshot = self.motion.sample(time_s)
        except DeformationProgramError as exc:
            raise DeformingGasHeatError(str(exc)) from exc
        geometry = snapshot.current
        instantaneous = replace(base, face_area_m2=float(geometry.face_areas_m2[0]),
                                cell_widths_m=tuple(map(float, geometry.widths_m)),
                                gas_volumes_m3=tuple(map(float, geometry.volumes_m3)))
        observation = instantaneous.evaluate(state, time_s)
        if np.any(observation.rates.cell_power_w != 0):
            raise DeformingGasHeatError('unpartitioned_body_power_not_supported')
        pressures = _array([g.pressure_pa for g in observation.gas_states], 'work_pressures', 1)
        try:
            with np.errstate(over='raise', invalid='raise', under='raise'):
                power = _array(-pressures * snapshot.volume_rates_m3_s, 'mechanical_power', 1)
        except FloatingPointError as exc:
            raise DeformingGasHeatError('mechanical_power_outside_float_range') from exc
        original = observation.rates
        rates = Rates(original.face_species_mol_s, original.face_energy_w,
                      original.reaction_species_mol_s, power)
        return DeformingGasHeatEvaluation(
            rates=rates, motion=snapshot, gas_evaluation=observation,
            mechanical_power_w=power, pressure_for_work_pa=pressures,
            work_model_identity=self.work_model_identity, source_ids=self.source_ids)

    def __call__(self, state: ConservedState, time_s: float) -> Rates:
        return self.evaluate(state, time_s).rates
