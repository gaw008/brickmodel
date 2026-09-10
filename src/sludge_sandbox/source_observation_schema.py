"""Closed passive source-observation types; never instantiate a live provider.

This schema checks recorded structure and numerical associations. Source labels
remain recorded provenance, not independent authentication of an EOS execution.
"""
from collections.abc import Mapping
from dataclasses import MISSING, fields
from fractions import Fraction
from functools import lru_cache
from types import MappingProxyType, UnionType
import json
import math
import re
import typing

import numpy as np

from .integration import ConservedState, Rates
from .exact_event_clock import ExactEventTime
from .exact_source_column import SourceExactEvaluation
from .source_net_panel import SavedSourceSample
from .mass_wet_storage import WetMixedState
from .source_wet_column import (SourceColumnCell, ColumnFaceRate, LiquidColumnFaceRate,
                                SourceColumnRates, LiquidSourceColumnRates)
from .programmed_source_wet_column import (ProgrammedSourceRates, ProgrammedLiquidSourceRates,
                                          SourceSurfaceObservation)
from .source_wet_storage import SourceWetInverse, SourceWetPoint
from .rigid_storage import ClosedStorageState, DeclaredNumericalEnvelope
from .rigid_water_gas import RigidWaterGasState, PressurePolicy, PressureTrialRecord
from .mass_wet_transport import WetPhaseEvaluation, WetFaceEvaluation
from .water_chemical_potential import (WaterPhaseEquilibrium, WaterLiquidChemicalState,
                                       WaterVaporChemicalState)
from .water_properties import WaterState, WaterReference
from .water_implementation import WaterImplementation
from .source_mass_caloric import DisabledChemicalRates
from .gas_transport import GasState, GasFaceExchange
from .liquid_transport import (LiquidFaceExchange, LiquidMobility, LiquidConnection,
                               LiquidTransportState)
from .phase_storage import PhaseMetadata
from .exact_boundary_program import ExactBoundaryState
from .boundary_program import ProgramIdentity
from .exchanges import BoundaryHeat

CLASSES = (SavedSourceSample, ConservedState, Rates, SourceExactEvaluation, WetMixedState,
    SourceColumnRates, LiquidSourceColumnRates, ProgrammedSourceRates, ProgrammedLiquidSourceRates,
    SourceSurfaceObservation, SourceColumnCell, ColumnFaceRate, LiquidColumnFaceRate,
    SourceWetInverse, SourceWetPoint, ClosedStorageState, DeclaredNumericalEnvelope,
    RigidWaterGasState, PressurePolicy, PressureTrialRecord, WetPhaseEvaluation, WetFaceEvaluation,
    WaterPhaseEquilibrium, WaterLiquidChemicalState, WaterVaporChemicalState, WaterState,
    WaterReference, WaterImplementation, DisabledChemicalRates, GasState, GasFaceExchange,
    LiquidFaceExchange, LiquidMobility, LiquidConnection, LiquidTransportState, PhaseMetadata,
    ExactBoundaryState, ProgramIdentity, BoundaryHeat)
REGISTRY = MappingProxyType({cls.__module__ + '.' + cls.__qualname__: cls for cls in CLASSES})
SOURCE_RATES = (SourceColumnRates, LiquidSourceColumnRates, ProgrammedSourceRates, ProgrammedLiquidSourceRates)
FLOATS = tuple[float, ...]
LABELS = tuple[str, ...]
OPERATOR = tuple[str, str, LABELS]
ENERGY = tuple[str, LABELS, LABELS]
ASSETS = tuple[tuple[str, str], ...]

# Broad annotations in the runtime records do not authorize arbitrary objects.
OVERRIDES = {
    (ConservedState, 'amounts_mol'): np.ndarray,
    (ConservedState, 'internal_energy_j'): np.ndarray,
    (ConservedState, 'mechanical_stretches'): type(None),
    (Rates, 'face_species_mol_s'): np.ndarray,
    (Rates, 'face_energy_w'): np.ndarray,
    (Rates, 'reaction_species_mol_s'): np.ndarray,
    (Rates, 'cell_power_w'): np.ndarray,
    (Rates, 'mechanical_rates_per_s'): type(None),
    (Rates, 'cell_power_components_w'): type(None),
    (Rates, 'component_sum_residual_w'): type(None),
    (SavedSourceSample, 'state'): ConservedState,
    (SavedSourceSample, 'evaluation'): SourceExactEvaluation,
    (ConservedState, 'energy_model_identity'): ENERGY,
    (SourceExactEvaluation, 'source_states'): tuple[WetMixedState, ...],
    (SourceExactEvaluation, 'source_evaluation'): typing.Union[SOURCE_RATES],
    (SourceExactEvaluation, 'operator_identity'): OPERATOR,
    (WetMixedState, 'solid_mass_kg'): FLOATS,
    (WetMixedState, 'gas_amounts_mol'): FLOATS,
    (SourceColumnRates, 'cells'): tuple[SourceColumnCell, ...],
    (SourceColumnRates, 'gas_states'): tuple[GasState, ...],
    (SourceColumnRates, 'faces'): tuple[ColumnFaceRate | LiquidColumnFaceRate, ...],
    (SourceColumnRates, 'source_ids'): LABELS,
    (LiquidSourceColumnRates, 'liquid_states'): tuple[LiquidTransportState, ...],
    (ProgrammedLiquidSourceRates, 'liquid_states'): tuple[LiquidTransportState, ...],
    (SourceColumnCell, 'inverse'): SourceWetInverse,
    (SourceColumnCell, 'phase'): WetPhaseEvaluation,
    (SourceColumnCell, 'chemistry'): DisabledChemicalRates,
    (ColumnFaceRate, 'gas_mol_s'): FLOATS,
    (ColumnFaceRate, 'diffusive_enthalpy_w'): FLOATS,
    (ColumnFaceRate, 'advective_enthalpy_w'): FLOATS,
    (ColumnFaceRate, 'shared_evaluation'): WetFaceEvaluation | None,
    (LiquidColumnFaceRate, 'liquid_exchange'): LiquidFaceExchange | None,
    (WetPhaseEvaluation, 'equilibrium'): WaterPhaseEquilibrium,
    (WetFaceEvaluation, 'exchange'): GasFaceExchange,
    (LiquidFaceExchange, 'liquid_source_identity'): tuple[PhaseMetadata, str, str, ASSETS],
}


class SourceObservationRecordError(ValueError):
    """Malformed, unsupported, changed, or internally inconsistent evidence."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise SourceObservationRecordError(reason)


@lru_cache(maxsize=len(CLASSES))
def field_hints(cls: type) -> dict:
    hints = typing.get_type_hints(cls)
    for base in reversed(cls.__mro__):
        for (owner, name), hint in OVERRIDES.items():
            if base is owner:
                hints[name] = hint
    return {field.name: hints[field.name] for field in fields(cls)}


def _label(value: object) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _sha(value: object) -> bool:
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def strict_json(raw: bytes | str) -> object:
    def unique(items):
        out = {}
        for key, value in items:
            require(key not in out, 'duplicate_json_key')
            out[key] = value
        return out
    def constant(_):
        raise SourceObservationRecordError('nonfinite_json')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)


def matches(value: object, hint: object) -> bool:
    """Exhaustive field matching; unknown annotations fail closed."""
    origin, args = typing.get_origin(hint), typing.get_args(hint)
    if origin in (typing.Union, UnionType):
        return any(matches(value, item) for item in args)
    if origin is typing.Literal:
        return any(type(value) is type(item) and value == item for item in args)
    if hint is None or hint is type(None):
        return value is None
    if hint is float:
        return type(value) in (int, float) and math.isfinite(value)
    if hint in (int, str, bool, Fraction):
        return type(value) is hint
    if hint is ExactEventTime:
        return type(value) is ExactEventTime and type(value.seconds) is Fraction
    if origin is tuple:
        if type(value) is not tuple:
            return False
        if len(args) == 2 and args[1] is Ellipsis:
            return all(matches(item, args[0]) for item in value)
        return len(value) == len(args) and all(matches(item, sub) for item, sub in zip(value, args))
    if origin in (Mapping, typing.Mapping):
        return (isinstance(value, Mapping) and all(matches(k, args[0]) and matches(v, args[1])
                                                   for k, v in value.items()))
    if hint is np.ndarray or origin is np.ndarray:
        return type(value) is np.ndarray and value.dtype == np.float64 and np.all(np.isfinite(value))
    if isinstance(hint, type) and hint in CLASSES:
        return type(value) is hint
    return False


def validate_fields(record: object) -> None:
    cls = type(record)
    require(cls in CLASSES, 'unsupported_source_record_type')
    for name, hint in field_hints(cls).items():
        require(matches(getattr(record, name), hint), 'source_field_type:' + cls.__name__ + '.' + name)
    for item in fields(record):
        value = getattr(record, item.name)
        if item.name == 'source_ids':
            require(bool(value) and all(_label(v) for v in value), 'source_labels_required')
        if item.name in ('model_identity', 'energy_model_identity') and cls not in (ConservedState,):
            require(_sha(value), 'source_model_sha_required')
        if item.name in ('material_qualified', 'full_inverse_liquid_direction_certified',
                         'full_inverse_direction_certified', 'phase_transfer_included'):
            require(value is False, 'source_qualification_upgrade')
        if item.name in ('qualification', 'energy_scope', 'liquid_pressure_interval_scope',
                         'pressure_interval_scope', 'assumption', 'method_id', 'classification',
                         'native_reference', 'energy_reference', 'entropy_reference', 'interpolation_method') and item.default is not MISSING:
            require(type(value) is type(item.default) and value == item.default, 'source_contract_changed:' + item.name)
    if cls is WaterImplementation:
        descriptor = strict_json(record.canonical_descriptor)
        require(json.dumps(descriptor, sort_keys=True, separators=(',', ':'), allow_nan=False)
                == record.canonical_descriptor, 'source_water_descriptor_noncanonical')
    if cls is WaterLiquidChemicalState:
        require(record.state.phase == 'liquid', 'source_chemical_liquid_phase')
    if cls is SourceWetInverse:
        require(record.temperature_error_bound_k >= 0 and record.iterations > 0
                and record.final_temperature_bracket_k[0] <= record.point.temperature_k
                <= record.final_temperature_bracket_k[1], 'source_inverse_bounds')
    if cls is SourceWetPoint:
        require(all(getattr(record, name) >= 0 for name in ('available_volume_error_m3',
                    'global_pressure_error_pa', 'extra_pressure_error_pa', 'pressure_error_pa', 'energy_error_j'))
                and record.available_pore_volume_m3 > record.available_volume_error_m3
                and record.minimum_heat_capacity_j_k > 0, 'source_point_bounds')
        require(record.total_enthalpy_j is record.solid_volume_m3 is record.fit_error is None,
                'source_unknown_property_invented')
    if cls is Rates:
        require(record.mechanical_rates_per_s is record.cell_power_components_w
                is record.component_sum_residual_w is None, 'source_fixed_rate_schema')
    if cls is ConservedState:
        require(record.mechanical_stretches is None, 'source_fixed_state_schema')
    if cls is RigidWaterGasState:
        require(record.pressure_bracket_qualification in (
            'not_recorded_legacy_constructor', 'numerical_forward_function_only_excludes_eos_error'),
            'source_pressure_bracket_qualification')
        require(all(_label(k) and _sha(v) for k, v in record.source_asset_sha256.items()),
                'source_asset_identity')
    if cls is PressureTrialRecord:
        require(record.status in ('started', 'failed', 'evaluated', 'finished', 'bracket_updated'),
                'source_pressure_trial_status')
        require((record.status == 'failed') == (record.failure is not None), 'source_trial_failure_status')
    if cls is LiquidFaceExchange:
        require(record.direction_qualification in ('conditional_direction_resolved',
                                                  'nominal_direction_not_certified'),
                'source_liquid_direction_qualification')
    if cls is SourceSurfaceObservation:
        require(record.status in ('balanced', 'adiabatic', 'insulated_surface_undetermined'), 'source_surface_status')


def validate_associations(sample: SavedSourceSample, energy_identity: tuple) -> None:
    """Check saved cross-links; no caloric provider or liquid EOS is called."""
    evaluation = sample.evaluation
    raw = evaluation.source_evaluation
    n = len(evaluation.source_states)
    require(len(raw.gas_states) == n, 'complete_source_gas_states')
    liquid = type(raw) in (LiquidSourceColumnRates, ProgrammedLiquidSourceRates)
    programmed = type(raw) in (ProgrammedSourceRates, ProgrammedLiquidSourceRates)
    require(not liquid or len(raw.liquid_states) == n, 'complete_source_liquid_states')
    for i, (state, cell, gas) in enumerate(zip(evaluation.source_states, raw.cells, raw.gas_states)):
        inverse, point = cell.inverse, cell.inverse.point
        mechanical = point.fluid.mechanical
        require(point.model_identity == state.energy_model_identity == energy_identity[1][i],
                'source_inverse_model_binding')
        require(type(inverse.target_energy_j) is float and inverse.target_energy_j == state.internal_energy_j
                and inverse.energy_residual_j == Fraction(point.total_internal_energy_j) - Fraction(state.internal_energy_j),
                'source_inverse_energy_binding')
        require(mechanical.liquid_inventory_mol == state.liquid_water_mol
                and tuple(mechanical.gas_inventory_mol) and set(mechanical.gas_inventory_mol) == {'O2', 'N2', 'H2O'}
                and tuple(mechanical.gas_inventory_mol[k] for k in ('O2', 'N2', 'H2O')) == state.gas_amounts_mol,
                'source_inverse_inventory_binding')
        require(point.temperature_k == gas.temperature_k, 'source_gas_temperature_binding')
        names = ('O2', 'N2', 'H2O')
        require(mechanical.gas_volume_m3 > 0 and set(gas.concentrations_mol_m3) == set(names)
                and gas.gas_constant_j_mol_k == mechanical.gas_constant_j_mol_k
                and gas.reservoir_input_mole_fractions is None
                and all(gas.concentrations_mol_m3[k] == amount / mechanical.gas_volume_m3
                        for k, amount in zip(names, state.gas_amounts_mol)), 'source_gas_inventory_binding')
        # Producers append these source labels; boundary/transport/caloric
        # sources may add others. Subset checks do not authenticate the labels.
        equilibrium = cell.phase.equilibrium
        water_sources = set(equilibrium.liquid.state.source_ids)
        require(water_sources <= set(mechanical.source_ids) <= set(point.fluid.source_ids)
                <= set(point.source_ids) <= set(raw.source_ids)
                and set(point.fluid.envelope.source_ids) <= set(point.fluid.source_ids),
                'source_label_associations')
        require(water_sources <= set(equilibrium.liquid.source_ids) <= set(equilibrium.source_ids)
                <= set(raw.source_ids) and set(equilibrium.vapor.source_ids) <= set(equilibrium.source_ids),
                'source_phase_labels')
        require((state.liquid_water_mol == 0 and mechanical.liquid_pressure_pa is None)
                or (state.liquid_water_mol > 0 and mechanical.liquid_pressure_pa == point.pressure_pa),
                'source_liquid_mode_binding')
        if liquid:
            saved = raw.liquid_states[i]
            require(saved.temperature_k == point.temperature_k and saved.pressure_pa == point.pressure_pa
                    and saved.inventory_mol == state.liquid_water_mol and saved.pressure_error_pa == point.pressure_error_pa,
                    'source_liquid_state_binding')
    for face in raw.faces:
        require(len(face.gas_mol_s) == len(face.diffusive_enthalpy_w) == len(face.advective_enthalpy_w) == 3,
                'source_face_vector_shape')
        require(type(face) is (LiquidColumnFaceRate if liquid and face.right_cell is not None
                              and face.left_cell is not None else ColumnFaceRate), 'source_face_variant')
        outer = programmed and face.face_id == n
        shared_required = 0 < face.face_id < n or outer
        require((type(face.shared_evaluation) is WetFaceEvaluation) if shared_required
                else face.shared_evaluation is None, 'source_shared_observation_presence')
        if face.shared_evaluation is not None:
            shared = face.shared_evaluation
            conduction = -raw.surface.conductive_into_cell_w if outer else shared.conduction_w
            require(face.conduction_w == conduction
                    and face.diffusive_enthalpy_w == shared.diffusive_enthalpy_w
                    and face.advective_enthalpy_w == shared.advective_enthalpy_w,
                    'source_face_shared_binding')

            require(tuple(shared.exchange.net_mol_s[k] for k in ('O2', 'N2', 'H2O')) == face.gas_mol_s,
                    'source_face_gas_binding')
            extra = (face.liquid_enthalpy_w,) if type(face) is LiquidColumnFaceRate else ()
            require(face.energy_w == math.fsum((conduction, *face.diffusive_enthalpy_w,
                                               *face.advective_enthalpy_w, *extra)), 'source_face_energy_binding')
        if type(face) is LiquidColumnFaceRate:
            exchange = face.liquid_exchange
            require(type(exchange) is LiquidFaceExchange, 'complete_source_liquid_face')
            require(exchange.donor in (None, 'left', 'right'), 'source_liquid_donor')
            left, right = raw.liquid_states[face.left_cell], raw.liquid_states[face.right_cell]
            require(exchange.liquid_source_identity == left.identity == right.identity,
                    'source_liquid_face_identity')
            donor = left if exchange.donor == 'left' else right if exchange.donor == 'right' else None
            projection = (Fraction(exchange.enthalpy_flow_w) - Fraction(exchange.molar_flow_mol_s)
                          * Fraction(donor.enthalpy_j_mol)) if donor is not None else Fraction()
            require(face.liquid_mol_s == exchange.molar_flow_mol_s
                    and face.liquid_enthalpy_w == exchange.enthalpy_flow_w
                    and face.liquid_enthalpy_projection_w == projection, 'source_liquid_face_binding')
