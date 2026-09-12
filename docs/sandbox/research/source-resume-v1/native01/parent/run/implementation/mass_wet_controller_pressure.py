"""Explicit event/common sample contexts; no extra native query or commit."""
from dataclasses import dataclass
from fractions import Fraction as F
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.mass_storage_bridge import require
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.mass_wet_transport import WetPair,WetCellRate,WetRates
from sludge_sandbox.mass_wet_exact_stage import Sample,pressure_radius
from sludge_sandbox.mass_wet_pressure_session import PressureSession
from sludge_sandbox.mass_wet_pressure_interval import encoded
from sludge_sandbox.integration import DomainExit


@dataclass(frozen=True)
class ControllerPressureQueryContext:
    comparison_kind: str
    side: str
    refinement_level: int
    refinement_role: str
    event_index: int | None
    selected_cell: int | None
    cell: int
    time: T
    source_binding: str
    interfaces: tuple
    original_controller_inputs_json: bytes

    def __post_init__(self):
        require(self.comparison_kind in ('event','common') and self.side in ('reference','candidate'), 'explicit_controller_pressure_role')
        require(type(self.refinement_level) is int and self.refinement_level>=1 and self.refinement_role in ('terminal','independent'),'explicit_pressure_refinement')
        if self.comparison_kind=='event':
            require(type(self.event_index) is int and self.event_index>=0 and type(self.selected_cell) is int and self.selected_cell in (0,1),'explicit_pressure_event_index')
        else:require(self.event_index is None and self.selected_cell is None,'common_pressure_has_no_event_index')
        require(type(self.cell) is int and self.cell in (0,1),'explicit_pressure_query_cell')
        require(type(self.time) is T and type(self.source_binding) is str and self.source_binding,'explicit_pressure_time_source')
        require(type(self.interfaces) is tuple and len(self.interfaces)==2 and all(m in ('existing_liquid','depleted_no_nucleation') for m in self.interfaces),'explicit_pressure_modes')
        require(type(self.original_controller_inputs_json) is bytes and self.original_controller_inputs_json,'immutable_original_controller_inputs')


def controller_pressure_radius(pair: WetPair,states: tuple,sample: Sample,cell: int,*,
        pressure_session: PressureSession,context: ControllerPressureQueryContext,
        caller_guard=None,remaining_caller_wall=None) -> F:
    """Bind an existing post-event/common observation, then prove only wet cells.

    Context identifies a comparison and preserves original input bytes; it is
    not by itself an authentication token or permission to select an event.
    """
    require(type(pair) is WetPair and type(pressure_session) is PressureSession,'actual_controller_pressure_host_session')
    require(type(states) is tuple and len(states)==2 and all(type(s) is WetMixedState for s in states),'complete_controller_pressure_states')
    require(type(cell) is int and cell in (0,1),'actual_controller_pressure_cell')
    require(type(sample) is Sample and sample.state is states and type(context) is ControllerPressureQueryContext,'actual_controller_pressure_sample_context')
    context.__post_init__()
    require(context.cell==cell and type(sample.rates) is WetRates and len(sample.rates.cells)==2,'actual_controller_pressure_rate_layout')
    require(sample.time==context.time and sample.role==('event_endpoint' if context.comparison_kind=='event' else 'common_endpoint'),'actual_controller_pressure_time_role')
    require(sample.source_binding==context.source_binding==pair.binding() and sample.interfaces==context.interfaces==pair.interfaces,'actual_controller_pressure_source_modes')
    rate=sample.rates.cells[cell]
    require(type(rate) is WetCellRate,'actual_controller_pressure_cell_rate')
    if caller_guard is not None:caller_guard()
    if states[cell].liquid_water_mol==0:
        require(pair.interfaces[cell]=='depleted_no_nucleation','zero_liquid_requires_depleted_mode')
        return pressure_radius(pair,states[cell],rate.inverse,cell,None)
    require(pair.interfaces[cell]=='existing_liquid','positive_liquid_requires_wet_mode')
    attempt=pressure_session.query(pair,states,rate,cell,context=encoded((context,states,rate,cell)),
        caller_guard=caller_guard,remaining_caller_wall=remaining_caller_wall)
    if attempt.status!='proved_conditional_query':
        error={'cancelled':InterruptedError,'resource_limit':TimeoutError,'domain_exit':DomainExit}.get(attempt.failure_kind,ValueError)
        raise error(attempt.reason or 'controller_pressure_unresolved')
    require(attempt.failure_kind is None and type(attempt.pressure_radius_pa) is F and attempt.pressure_radius_pa>=0,'proved_exact_controller_pressure_radius')
    if caller_guard is not None:caller_guard()
    return attempt.pressure_radius_pa
