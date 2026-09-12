"""Restore a numerical projection; no continuation or audit authorization."""
from dataclasses import dataclass,fields,replace
from collections.abc import Mapping
from types import MappingProxyType
from sludge_sandbox.exact_record import (read_exact_run,validate_binding,pack,canonical,
    EvidenceNode,REGISTRY)
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer
from sludge_sandbox.exact_depletion_integration import ExactDepletionResult

class ProjectionRestoreError(ValueError):pass

def require(ok,reason):
    if not ok:raise ProjectionRestoreError(reason)

def equal(left,right):return canonical(pack(left))==canonical(pack(right))

# Explicit value-type whitelist. No providers/inverses or classes named by input
# are imported. Historical observations remain declared numerical projections.
_TYPES=frozenset({'WaterState','WaterReference','WaterImplementation','ConservedState','Rates','IntegrationPolicy',
 'ExactStepLedger','ExactDepletionResult','ExactPacketFrame','ExactPacketRefinement','ExactPacketPath',
 'ExactTerminalAttempt','TerminalCosts','ExactAffinePanel','ExactRootOrder','RootCandidate','NoRootEvidence',
 'ExactAffineSamples','ExactAffineEvidence','ExactDepletionWritebackRecord','DepletionRoundoffPolicy',
 'DepletionRoundoffTotals','DepletionPolicy','NestedApproachPolicy','PressureComparisonPolicy',
 'SharedConstantParameterBox','CellWaterTransfer','WaterPhaseEquilibrium','WaterVaporChemicalState',
 'WaterLiquidChemicalState'})
_PROJECTIONS=frozenset({'Observation','TerminalObservation'})

@dataclass(frozen=True)
class RestoredExactProjection:
    result:ExactDepletionResult
    record_sha256:str
    canonical_record_bytes:bytes
    rebound_committed_ledgers:int
    resume_authorized:bool=False
    scope:str='typed_numerical_projection_with_canonical_ledger_aliases_not_continuation_authority'
    historical_observation_contract:str='saved_numerical_evidence_no_live_inverse_or_provider_graph'


def _canonicalize_committed_ledgers(result):
    """Associate by full value and exact time, then restore the id-based seam."""
    require(type(result) is ExactDepletionResult,'explicit_exact_result')
    require(len(result.steps)+1==len(result.states)==len(result.times_s),'complete_prefix')
    indices={}
    for i,ledger in enumerate(result.steps):
        key=(ledger.start_s,ledger.end_s)
        require(key not in indices,'duplicate_accepted_ledger_interval')
        require(key==(result.times_s[i],result.times_s[i+1]),'accepted_ledger_time_binding')
        indices[key]=i
    packets=[];used=set()
    for packet in result.packets:
        frames=[]
        for frame in packet:
            terminal=frame.terminal;panel=terminal.terminal_panel;key=(panel.ledger.start_s,panel.ledger.end_s)
            require(key in indices,'missing_committed_ledger')
            i=indices[key];accepted=result.steps[i]
            require(i not in used,'duplicate_committed_ledger')
            require(equal(panel.ledger,accepted),'committed_ledger_value_mismatch')
            require(equal(terminal.initial_state,result.states[i]) and equal(terminal.corrected_state,result.states[i+1]),'committed_state_binding')
            if terminal.correction is not None:
                require(terminal.correction.cell_index==terminal.root_order.selected_cell,'correction_selected_cell_binding')
                require(terminal.correction.clock_evidence is not None,'correction_clock_required')
                selected=next(c.evidence for c in terminal.root_order.candidates if c.cell_index==terminal.root_order.selected_cell)
                require(equal(terminal.correction.clock_evidence,selected),'correction_selected_clock_binding')
            rebound=replace(terminal,terminal_panel=replace(panel,ledger=accepted))
            frames.append(replace(frame,terminal=rebound));used.add(i)
        packets.append(tuple(frames))
    restored=replace(result,packets=tuple(packets))
    require(equal(restored,result),'restoration_changed_numerical_evidence')
    # Check the actual Python relationship needed by the current audit_commit.
    for packet in restored.packets:
        for frame in packet:
            ledger=frame.terminal.terminal_panel.ledger
            require(ledger is restored.steps[indices[(ledger.start_s,ledger.end_s)]],'canonical_alias_not_restored')
    return restored,len(used)


def restore_exact_projection(raw,*,original_operator,case_sha256,runtime_identity):
    try:
        require(type(raw) is bytes and type(original_operator) is ExactFreeWaterTransfer,'explicit_restore_inputs')
        # Never use a caller-supplied parsed wrapper or unchecked cached values.
        checked=validate_binding(read_exact_run(raw),original_operator,case_sha256=case_sha256,runtime_identity=runtime_identity)
        views={original_operator.operator.interfaces:original_operator}
        def restore(v):
            if type(v) is EvidenceNode:
                if v.kind=='OperatorReference':
                    if v.modes not in views:
                        views[v.modes]=ExactFreeWaterTransfer(replace(original_operator.operator,interface_modes=v.modes))
                    view=views[v.modes]
                    require(equal(view.operator_identity,v.identity),'live_mode_source_mismatch')
                    return view
                if v.kind in _PROJECTIONS:
                    return EvidenceNode(v.kind,MappingProxyType({k:restore(x) for k,x in v.values.items()}))
                require(v.kind in _TYPES,'unsupported_numerical_projection_kind')
                cls=REGISTRY[v.kind]
                obj=cls(**{f.name:restore(getattr(v,f.name)) for f in fields(cls) if f.init})
                require(equal(obj,v),'restored_derived_field_mismatch:'+v.kind)
                return obj
            if type(v) is tuple:return tuple(restore(x) for x in v)
            if isinstance(v,Mapping):return MappingProxyType({k:restore(x) for k,x in v.items()})
            return v
        result=restore(checked.result)
        require(equal(result,checked.result),'complete_projection_mismatch')
        result,count=_canonicalize_committed_ledgers(result)
        # No assertions about numerical-proof, resource or resume admission here.
        original_operator.operator_identity
        return RestoredExactProjection(result,checked.sha256,checked.canonical_bytes,count)
    except ProjectionRestoreError:raise
    except (ValueError,TypeError,AttributeError,KeyError,OverflowError,StopIteration) as exc:
        raise ProjectionRestoreError('exact_projection_rejected:'+str(exc)) from exc
