"""Explicit exact-time adapter for the reviewed autonomous free-slab transfer."""
from dataclasses import dataclass, field, fields, is_dataclass
from collections.abc import Mapping
from .exact_event_clock import ExactEventTime
from .free_solid_slab import FreeSolidSlab
from .water_phase_transfer import WaterPhaseTransfer, WaterTransferEvaluation
from .integration import ConservedState, IntegrationError, Rates
from .deforming_solid_storage import _digest
from .water_properties import is_water_provider

SCHEMA = 'exact_autonomous_free_slab_transfer_v1'


def _water_bindings(value, path=()):
    """Fingerprint all actual provider slots, including ideal-vapor bridges.

    Stop at the provider: native kernels/caches are runtime objects, not source
    descriptors. The whole operator's canonical digest separately binds inputs.
    """
    if is_water_provider(value):
        kind=type(value)
        return ((path,kind.__module__,kind.__qualname__,_digest(value.implementation)),)
    if is_dataclass(value) and not isinstance(value,type):
        return tuple(item for descriptor in fields(value)
                     for item in _water_bindings(getattr(value,descriptor.name),path+(descriptor.name,)))
    if isinstance(value,Mapping):
        return tuple(item for key in sorted(value)
                     for item in _water_bindings(value[key],path+(key,)))
    if isinstance(value,(tuple,list)):
        return tuple(item for index,child in enumerate(value)
                     for item in _water_bindings(child,path+(index,)))
    return ()


@dataclass(frozen=True)
class ExactFreeWaterTransfer:
    operator: WaterPhaseTransfer
    _identity: tuple = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.operator) is not WaterPhaseTransfer or type(self.operator.base_model) is not FreeSolidSlab:
            raise IntegrationError('explicit_direct_free_slab_transfer_required')
        object.__setattr__(self, '_identity', self._binding())

    def _binding(self) -> tuple:
        try:
            self.operator.chemical._check_identity()
            return (SCHEMA, _digest(self.operator), _water_bindings(self.operator))
        except (ValueError, TypeError, AttributeError, OverflowError) as exc:
            raise IntegrationError('exact_autonomous_source_binding_invalid') from exc

    @property
    def operator_identity(self) -> tuple:
        if self._binding() != self._identity:
            raise IntegrationError('exact_autonomous_source_binding_changed')
        return self._identity

    @property
    def energy_model_identity(self) -> tuple:
        self.operator_identity
        return self.operator.base_model.energy_model_identity

    def evaluate(self, state: ConservedState, time: ExactEventTime) -> WaterTransferEvaluation:
        if type(time) is not ExactEventTime:
            raise IntegrationError('exact_event_time_required')
        self.operator_identity
        result = self.operator.evaluate_autonomous(state)
        self.operator_identity
        return result

    def __call__(self, state: ConservedState, time: ExactEventTime) -> Rates:
        return self.evaluate(state, time).rates

    def breakpoints(self, start: ExactEventTime, end: ExactEventTime) -> tuple:
        if type(start) is not ExactEventTime or type(end) is not ExactEventTime or end <= start:
            raise IntegrationError('ordered_exact_time_interval_required')
        self.operator_identity
        return ()

    def with_depleted_cells(self, state: ConservedState, cell_indices: tuple[int, ...]) -> 'ExactFreeWaterTransfer':
        self.operator_identity
        return ExactFreeWaterTransfer(self.operator.with_depleted_cells(state, cell_indices))
