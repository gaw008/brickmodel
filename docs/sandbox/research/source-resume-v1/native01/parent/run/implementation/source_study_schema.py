"""Closed passive source-study types; no JSON-selected imports or live objects."""
from collections.abc import Mapping
from dataclasses import dataclass, fields
from fractions import Fraction as F
from functools import lru_cache
from types import MappingProxyType, UnionType
import math
import typing

import numpy as np

from . import source_observation_schema as observation
from . import integration as integration
from . import exact_integration as integration_exact
from . import exact_affine_depletion as affine
from . import exact_event_clock as clock
from . import depletion_integration as depletion
from . import depletion_roundoff as roundoff
from . import source_prefix_trial as trial
from . import source_net_panel as panel
from . import source_net_prefix as prefix
from . import source_net_roots as roots
from . import source_approach as approach
from . import source_root_comparison as comparison
from . import source_terminal as terminal
from . import source_dry_transition as transition
from . import source_endpoint_comparison as endpoints
from . import source_inverse_pressure as wet
from . import source_dry_pressure as dry
from . import source_dry_shared_pressure as shared_dry
from . import source_wet_shared_pressure as shared_wet
from . import source_wet_column as column
from .source_wet_storage import ManufacturedFixedFluidVolume
from .mass_wet_exact_stage import InventoryPolynomial
from .liquid_transport import SaturationMobilityTable, LiquidConnection
from .solid_fluid_heat import LiquidTransportConfig
from .pressure_comparison import PressureComparisonPolicy
from .paired_pressure_host import SharedConstantParameterBox


class SourceStudyRecordError(ValueError):
    """Malformed, unsupported or internally inconsistent passive evidence."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SourceStudyRecordError(reason)


@dataclass(frozen=True)
class SourceStudyNode:
    """A complete archived runtime record; it is not a runtime instance."""
    kind: str
    values: Mapping[str, object]

    def __getattr__(self, name: str) -> object:
        try:
            return self.values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


@dataclass(frozen=True)
class SourceLiveReference:
    kind: str
    available: bool
    identity: object
    modes: tuple[str, ...] | None
    scope: str = 'archived_reference_not_live_object_or_resume_authority'


@dataclass(frozen=True)
class SourceStudyFailure:
    exception_type: str
    message: str
    stage: str | None
    records: Mapping[str, object]


EXTRA_CLASSES = (
    integration.IntegrationPolicy, integration_exact.ExactStepLedger, integration_exact.ExactIntegrationResult,
    depletion.DepletionPolicy, depletion.NestedApproachPolicy, roundoff.DepletionRoundoffPolicy,
    roundoff.DepletionRoundoffTotals, affine.ExactAffineSamples, affine.ExactAffineEvidence,
    affine.ExactDepletionWritebackRecord, clock.ExactTimeInterval, InventoryPolynomial,
    trial.TrialCapture, trial.SourcePrefixTrial, panel.SourceAffinePanel, prefix.SourcePrefix,
    prefix.SourcePrefixAudit, roots.QuadraticNoRoot, roots.QuadraticRoot, roots.InventoryRootOrder,
    roots.SourcePanelRootOrder, approach.PositiveApproachChoice, approach.SourceApproachProposal,
    approach.SourceApproachResult, comparison.SourceRootClockComparison, comparison.SourceRootRefinement,
    comparison.SourceCommonEndpointComparison, terminal.SourceTerminal, transition.SourceDryCandidate,
    transition.SourceTransitionBalance, transition.SourceTransitionCellBalance, transition.SourceDryTransition,
    endpoints.SourceEndpointDifferences, endpoints.SourceEndpointComparison, wet.PressureContinuation,
    wet.SourceInversePressure, wet.SourceTrialPressure, dry.DryPressureContinuation, dry.SourceDryPressure,
    shared_dry.SourceSharedDryVolume, shared_dry.SourceDryPressureErrorParts, shared_dry.SourceSharedDryPressurePair,
    shared_wet.SourceSharedWetVolume, shared_wet.WetPairSupport, shared_wet.WetVolumeObservation,
    shared_wet.SourceWetPairEvidence, shared_wet.SourceWetPressureErrorParts, shared_wet.SourceSharedWetPressurePair,
    column.ColumnFaceIntegral, column.LiquidColumnFaceIntegral, ManufacturedFixedFluidVolume,
    SaturationMobilityTable, LiquidTransportConfig, PressureComparisonPolicy, SharedConstantParameterBox,
    SourceLiveReference, SourceStudyFailure,
)
CLASSES = tuple(dict.fromkeys((*observation.CLASSES, *EXTRA_CLASSES)))
REGISTRY = MappingProxyType({c.__module__+'.'+c.__qualname__:c for c in CLASSES})
LIVE_FIELDS = MappingProxyType({
    trial.SourcePrefixTrial: ('adapter',), terminal.SourceTerminal: ('dry_adapter',),
    wet.SourceInversePressure: ('storage',), dry.SourceDryPressure: ('storage',),
    shared_dry.SourceSharedDryVolume: ('storage',), shared_wet.SourceSharedWetVolume: ('storage',),
})
MINIMA = tuple[tuple[str,int,int,F,F], ...]
OVERRIDES = {
    (integration_exact.ExactStepLedger,'face_species_mol'): np.ndarray,
    (integration_exact.ExactStepLedger,'face_energy_j'): np.ndarray,
    (integration_exact.ExactStepLedger,'reaction_species_mol'): np.ndarray,
    (integration_exact.ExactStepLedger,'cell_work_j'): np.ndarray,
    (integration_exact.ExactStepLedger,'stretch_increment'): np.ndarray | None,
    (integration_exact.ExactStepLedger,'cell_work_components_j'): Mapping[str,np.ndarray] | None,
    (trial.SourcePrefixTrial,'adapter'): SourceLiveReference,
    (terminal.SourceTerminal,'dry_adapter'): SourceLiveReference,
    (terminal.SourceTerminal,'correction'): affine.ExactDepletionWritebackRecord | None,
    (transition.SourceDryCandidate,'event_policy'): depletion.DepletionPolicy,
    (wet.SourceInversePressure,'storage'): SourceLiveReference,
    (dry.SourceDryPressure,'storage'): SourceLiveReference,
    (shared_dry.SourceSharedDryVolume,'storage'): SourceLiveReference,
    (shared_wet.SourceSharedWetVolume,'storage'): SourceLiveReference,
    (trial.SourcePrefixTrial,'operator_identity'): observation.OPERATOR,
    (trial.SourcePrefixTrial,'energy_identity'): observation.ENERGY,
    (trial.SourcePrefixTrial,'fixed_dry_mass_kg'): observation.FLOATS,
    (panel.SourceAffinePanel,'operator_identity'): observation.OPERATOR,
    (panel.SourceAffinePanel,'energy_identity'): observation.ENERGY,
    (panel.SourceAffinePanel,'fixed_dry_mass_kg'): observation.FLOATS,
    (panel.SourceAffinePanel,'sample_bindings'): tuple[str,str,clock.ExactEventTime],
    (panel.SourceAffinePanel,'inventories'): tuple[InventoryPolynomial,...],
    (panel.SourceAffinePanel,'energies'): tuple[InventoryPolynomial,...],
    (prefix.SourcePrefix,'minima'): MINIMA,
    (approach.PositiveApproachChoice,'minima'): MINIMA,
    (prefix.SourcePrefix,'integrals'): tuple[tuple[str,tuple[F,...],tuple[F,...]],...],
    (prefix.SourcePrefix,'face_diagnostics'): tuple[column.ColumnFaceIntegral | column.LiquidColumnFaceIntegral,...],
    (column.ColumnFaceIntegral,'gas_mol'): tuple[F,...],
    (column.ColumnFaceIntegral,'diffusive_enthalpy_j'): tuple[F,...],
    (column.ColumnFaceIntegral,'advective_enthalpy_j'): tuple[F,...],
    (roots.InventoryRootOrder,'earliest_labels'): tuple[tuple[str,int,int],...],
    (roots.InventoryRootOrder,'zero_initial_labels'): tuple[tuple[str,int,int],...],
    (roots.SourcePanelRootOrder,'operator_identity'): observation.OPERATOR,
    (roots.SourcePanelRootOrder,'sample_bindings'): tuple[str,str,clock.ExactEventTime],
    (endpoints.SourceEndpointDifferences,'operator_identity'): observation.OPERATOR,
    (endpoints.SourceEndpointDifferences,'energy_identity'): observation.ENERGY,
    (endpoints.SourceEndpointDifferences,'fixed_dry_mass_kg'): observation.FLOATS,
    (LiquidTransportConfig,'relations'): tuple[SaturationMobilityTable,...],
    (LiquidTransportConfig,'connections'): tuple[LiquidConnection,...],
    (SourceLiveReference,'identity'): object,
    (SourceStudyFailure,'records'): Mapping[str,object],
    (depletion.DepletionPolicy,'pressure_comparison'): PressureComparisonPolicy | None,
}
POLICIES = (integration.IntegrationPolicy, depletion.DepletionPolicy, depletion.NestedApproachPolicy,
            roundoff.DepletionRoundoffPolicy, PressureComparisonPolicy, SharedConstantParameterBox)
# These unparameterized runtime annotations are explicitly closed structural
# tuples. Each child is still recursively restricted to the registry/primitives;
# their semantic shapes are checked by the relevant passive arithmetic audit.


@lru_cache(maxsize=None)
def hints(cls: type) -> dict[str,object]:
    if cls in observation.CLASSES:
        result = observation.field_hints(cls)
    else:
        result = typing.get_type_hints(cls)
    for base in reversed(cls.__mro__):
        for (owner,name),hint in OVERRIDES.items():
            if owner is base:
                result[name] = hint
    return {field.name:result[field.name] for field in fields(cls)}


def matches(value: object, hint: object, *, policy_number: bool=False) -> bool:
    origin,args = typing.get_origin(hint),typing.get_args(hint)
    if origin in (typing.Union,UnionType):
        return any(matches(value,a,policy_number=policy_number) for a in args)
    if origin is typing.Literal:
        return any(type(value) is type(a) and value==a for a in args)
    if hint is None or hint is type(None):
        return value is None
    if hint is object:
        return safe_value(value)
    if hint is float:
        return type(value) in ((float,int) if policy_number else (float,)) and math.isfinite(value)
    if hint in (str,int,bool,F,clock.ExactEventTime):
        return type(value) is hint
    if hint is np.ndarray or origin is np.ndarray:
        return type(value) is np.ndarray and value.dtype==np.float64 and bool(np.all(np.isfinite(value)))
    if hint is tuple or origin is tuple:
        if type(value) is not tuple:
            return False
        if not args:
            return all(safe_value(v) for v in value)
        if len(args)==2 and args[1] is Ellipsis:
            return all(matches(v,args[0],policy_number=policy_number) for v in value)
        return len(value)==len(args) and all(matches(v,h,policy_number=policy_number) for v,h in zip(value,args))
    if hint is Mapping or origin in (Mapping,typing.Mapping):
        return isinstance(value,Mapping) and (all(type(k) is str and safe_value(v) for k,v in value.items())
            if not args else all(matches(k,args[0],policy_number=policy_number)
                and matches(v,args[1],policy_number=policy_number) for k,v in value.items()))
    if isinstance(hint,type) and hint in CLASSES:
        return type(value) is SourceStudyNode and REGISTRY.get(value.kind) is hint
    return False


def safe_value(value: object) -> bool:
    pending=[value];seen=set()
    while pending:
        item=pending.pop()
        if item is None or type(item) in (str,int,bool,F,clock.ExactEventTime):continue
        if type(item) is float:
            if not math.isfinite(item):return False
        elif type(item) is SourceStudyNode:
            if item.kind not in REGISTRY:return False
        elif type(item) is np.ndarray:
            if item.dtype!=np.float64 or not bool(np.all(np.isfinite(item))):return False
        elif type(item) is tuple or isinstance(item,Mapping):
            if id(item) in seen:continue
            seen.add(id(item))
            if isinstance(item,Mapping):
                if not all(type(k) is str for k in item):return False
                pending.extend(item.values())
            else:pending.extend(item)
        else:return False
    return True


def validate_node(node: SourceStudyNode) -> None:
    require(type(node) is SourceStudyNode and node.kind in REGISTRY,'unknown_source_study_class')
    cls = REGISTRY[node.kind]
    require(isinstance(node.values,Mapping) and set(node.values)=={f.name for f in fields(cls)},
            'source_study_complete_fields:'+cls.__name__)
    expected = hints(cls)
    for name,value in node.values.items():
        require(matches(value,expected[name],policy_number=cls in POLICIES),
                'source_study_field_type:'+cls.__name__+'.'+name)
    for field in fields(cls):
        if field.name in ('qualification','assumptions','validation_scope') and field.default is not None:
            from dataclasses import MISSING
            if field.default is not MISSING:
                require(node.values[field.name]==field.default,'source_study_qualification_changed:'+cls.__name__)
        if field.name in ('material_qualified','source_certified','event_admitted','resume_authorized'):
            require(node.values[field.name] is False,'source_study_authority_changed:'+cls.__name__)


def reify(value: object, memo: dict[int,object] | None=None) -> object:
    """Construct only explicit passive records; never source stages/live models."""
    memo = {} if memo is None else memo
    key=id(value)
    if key in memo:
        return memo[key]
    if type(value) is SourceStudyNode:
        validate_node(value)
        cls=REGISTRY[value.kind]
        require(cls not in LIVE_FIELDS and cls not in (trial.SourcePrefixTrial,approach.SourceApproachProposal,
            approach.SourceApproachResult,comparison.SourceRootRefinement,comparison.SourceCommonEndpointComparison,
            terminal.SourceTerminal,transition.SourceDryCandidate,transition.SourceDryTransition,
            endpoints.SourceEndpointComparison,wet.SourceTrialPressure,shared_dry.SourceSharedDryPressurePair,
            shared_wet.SourceSharedWetPressurePair,SourceLiveReference,SourceStudyFailure),
            'live_dependent_study_node_not_reconstructible')
        values={k:reify(v,memo) for k,v in value.values.items()}
        result=cls(**{f.name:values[f.name] for f in fields(cls) if f.init})
        from .source_net_prefix import _same
        require(all(_same(getattr(result,f.name),values[f.name]) for f in fields(cls)),
                'source_study_constructor_changed_fields:'+cls.__name__)
        if cls in observation.CLASSES:
            observation.validate_fields(result)
    elif type(value) is tuple:
        result=tuple(reify(v,memo) for v in value)
    elif isinstance(value,Mapping):
        result=MappingProxyType({k:reify(v,memo) for k,v in value.items()})
    else:
        result=value
    memo[key]=result
    return result


def has_capture_failure(capture: Mapping[str,object]) -> bool:
    """Recognize explicit saved failure metadata, including empty messages."""
    values=tuple(capture.get(key) for key in ('failure','failure_kind','exception','exception_type'))
    require(all(value is None or type(value) is str for value in values),'source_study_capture_failure_fields')
    return any(type(value) is str for value in values)
