"""Recompute committed affine terminal arithmetic; no EOS or resume authority."""
from dataclasses import dataclass, fields, replace
from fractions import Fraction as F
from collections.abc import Mapping
from types import MappingProxyType
from sludge_sandbox.exact_record import (read_exact_run,validate_binding,pack,EvidenceNode,
    REGISTRY,ExactRecordError)
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.integration import ConservedState,Rates,IntegrationPolicy
from sludge_sandbox.depletion_integration import DepletionPolicy
from sludge_sandbox.depletion_roundoff import DepletionRoundoffTotals
from sludge_sandbox.exact_root_order import verify_exact_root_order
from sludge_sandbox.exact_terminal_panel import build_exact_affine_panel
from sludge_sandbox.exact_affine_depletion import exact_depletion_writeback

class TerminalProofAuditError(ValueError):pass

def require(ok,reason):
    if not ok:raise TerminalProofAuditError(reason)

def same(actual,expected,label):require(pack(actual)==pack(expected),label)

# Only numerical value types required by these proof functions are constructed.
_NUMERIC={'ConservedState','Rates','ExactStepLedger','ExactAffinePanel','ExactRootOrder',
 'RootCandidate','NoRootEvidence','ExactAffineSamples','ExactAffineEvidence',
 'ExactDepletionWritebackRecord','DepletionRoundoffPolicy','DepletionRoundoffTotals'}

def numeric(v):
    if type(v) is EvidenceNode:
        require(v.kind in _NUMERIC,'explicit_numeric_record_required')
        cls=REGISTRY[v.kind]
        obj=cls(**{f.name:numeric(getattr(v,f.name)) for f in fields(cls) if f.init})
        same(obj,v,'numeric_derived_field_mismatch');return obj
    if type(v) is tuple:return tuple(numeric(x) for x in v)
    if isinstance(v,Mapping):return {k:numeric(x) for k,x in v.items()}
    return v


def geometry_binding(view,state,observation):
    """Actual state-only point preparation; deliberately no thermal inversion."""
    op=view.operator;host=op.base_model
    view.operator_identity;host._check_state(state);op._check_interface_state(state)
    normals=tuple(map(float,state.mechanical_stretches[:-1]));tangent=float(state.mechanical_stretches[-1])
    prepared=[]
    for i,(point,row) in enumerate(zip(host.point_storages,state.amounts_mol,strict=True)):
        deformation,skeleton,storage,mech_error,bulk_error=point._prepare(normals,tangent,host.inventory_layout.solid_inventory(row))
        require(point.skeleton.cell_index==i and len(deformation.current.volumes_m3)==len(state.amounts_mol),'actual_point_geometry_order')
        fluid=storage.fluid_template
        temp=observation.temperatures_k[i];pressure=observation.pressures_pa[i]
        require(fluid.envelope.temperature_range_k[0]<=temp<=fluid.envelope.temperature_range_k[1],'reported_temperature_source_domain')
        require(fluid.mechanical.pressure_bracket_pa[0]<=pressure<=fluid.mechanical.pressure_bracket_pa[1],'reported_pressure_source_domain')
        prepared.append((point.identity,float(deformation.current.volumes_m3[i]),float(deformation.current.widths_m[i]),
            float(deformation.current.face_areas_m2[i]),storage.bulk_volume_error_m3,mech_error,bulk_error))
    view.operator_identity
    return tuple(prepared)


def observation_binding(view,node,state):
    op=view.operator
    require(node.interface_modes==op.interfaces,'observation_modes')
    for key in ('coefficient_set_id','coefficient_version','coefficient_classification','dry_policy'):
        require(getattr(node,key)==getattr(op,key),'observation_'+key)
    require(set(op.source_ids).issubset(node.source_ids),'observation_actual_source_ids')
    rates=numeric(node.rates);rates.derivatives(state)
    require(len(node.cell_transfers)==len(state.amounts_mol),'complete_phase_observations')
    require(all(d.coefficient_mol_s_pa==coefficient for d,coefficient in zip(node.cell_transfers,op.coefficients_mol_s_pa,strict=True)),'actual_phase_coefficients')
    return rates


@dataclass(frozen=True)
class TerminalProofReport:
    record_sha256:str
    committed_terminals:int
    candidates_checked:int
    exclusions_checked:int
    event_rows:tuple
    scope:str='committed_affine_numerical_proofs_and_actual_state_geometry_not_full_rhs_or_resume'
    remaining_gates:tuple=('full_original_prefix','six_gate_refinement_comparisons','cumulative_resources','continuation_admission')


def audit_committed_terminal_proofs(raw,*,original_operator,original_initial,start,end,
        integration_policy,event_policy,case_sha256,runtime_identity):
    try:
        return _audit(raw,original_operator,original_initial,start,end,integration_policy,event_policy,case_sha256,runtime_identity)
    except TerminalProofAuditError:raise
    except (ValueError,TypeError,AttributeError,KeyError,OverflowError) as exc:
        raise TerminalProofAuditError('terminal_proof_rejected:'+str(exc)) from exc


def _audit(raw,original_operator,original_initial,start,end,p,ep,case_sha,runtime):
    require(type(original_operator) is ExactFreeWaterTransfer and type(original_initial) is ConservedState and type(p) is IntegrationPolicy and type(ep) is DepletionPolicy,'explicit_external_inputs')
    checked=validate_binding(read_exact_run(raw),original_operator,case_sha256=case_sha,runtime_identity=runtime)
    same(checked.states[0],original_initial,'original_initial_binding');same(checked.result.initial_policy,p,'original_integration_policy')
    same(checked.result.event_policy,ep,'original_event_policy');require(checked.start==start and checked.end==end,'original_time_interval')
    li,vi=original_operator.operator.liquid_index,original_operator.operator.water_vapor_index
    require(ep.roundoff_policy.molar_mass_kg_mol==original_operator.operator.chemical.reference.molar_mass_kg_mol,'actual_water_molar_mass')
    views={original_operator.operator.interfaces:original_operator}
    def view_for(ref):
        if ref.modes not in views:views[ref.modes]=ExactFreeWaterTransfer(replace(original_operator.operator,interface_modes=ref.modes))
        view=views[ref.modes];same(view.operator_identity,ref.identity,'actual_terminal_source');return view
    totals=DepletionRoundoffTotals(ep.roundoff_policy);rows=[];nc=ne=0
    for packet_index,packet in enumerate(checked.result.packets):
        require(bool(packet),'empty_committed_packet')
        for frame_index,frame in enumerate(packet):
            attempt=frame.terminal
            require(attempt.status=='speculative_completed' and attempt.reason is None,'committed_terminal_status')
            require(tuple(o.role for o in attempt.observations)==('initial','midpoint','endpoint'),'exact_terminal_observation_roles')
            first,middle,last=attempt.observations
            state=numeric(attempt.initial_state)
            same(first.state,state,'first_actual_state');same(attempt.input_totals,totals,'original_cumulative_input_totals')
            view=view_for(attempt.original_operator);candidate_view=view_for(attempt.candidate_operator)
            same(state.energy_model_identity,view.energy_model_identity,'actual_energy_identity')
            same(first.time,attempt.predictor_panel.ledger.start_s,'first_panel_time')
            r0=observation_binding(view,first.evaluation,state)
            wet=tuple(i for i,m in enumerate(view.operator.interfaces) if m=='existing_liquid')
            require(wet==tuple(i for i,row in enumerate(state.amounts_mol) if row[li]>0),'all_wet_inventory_modes')
            evaporation=lambda o:tuple(float(c.rate_mol_s) for c in o.cell_transfers)
            e0=evaporation(first.evaluation);options=[]
            for i in wet:
                rate=F(float(r0.face_species_mol_s[i,li]))-F(float(r0.face_species_mol_s[i+1,li]))+F(float(r0.reaction_species_mol_s[i,li]))
                if rate<0:
                    require(e0[i]>0,'non_evaporative_candidate');options.append((F(float(state.amounts_mol[i,li]))/-rate,i))
            require(bool(options),'missing_initial_candidate');tau,hint=min(options)
            midpoint=first.time.shifted(tau/2);upper=min(frame.common_time,first.time.shifted(2*tau))
            binding=('exact-operator:'+_digest(view.operator_identity),)
            predictor=build_exact_affine_panel(state,r0,r0,start=first.time,midpoint=first.time.shifted(tau/4),end=midpoint,
                policy=p,liquid_index=li,selected_cell=hint,wet_cells=wet,source_binding=binding)
            same(predictor,attempt.predictor_panel,'whole_predictor_panel');same(middle.state,predictor.raw_state,'actual_midpoint_state')
            require(middle.time==midpoint and all(predictor.raw_state.amounts_mol[i,li]>0 for i in wet),'wet_midpoint_time_state')
            rm=observation_binding(view,middle.evaluation,predictor.raw_state)
            order=numeric(attempt.root_order)
            verify_exact_root_order(order,state,r0,rm,start=first.time,midpoint=midpoint,upper=upper,liquid_index=li,
                wet_cells=wet,evaporation_start_mol_s=e0,evaporation_mid_mol_s=evaporation(middle.evaluation),
                source_binding=binding,time_absolute_s=ep.time_absolute_s,policy=ep.roundoff_policy)
            selected=next(c.evidence for c in order.candidates if c.cell_index==order.selected_cell)
            require(midpoint<selected.lower<frame.common_time,'selected_terminal_domain')
            terminal=build_exact_affine_panel(state,r0,rm,start=first.time,midpoint=midpoint,end=selected.lower,
                policy=p,liquid_index=li,selected_cell=order.selected_cell,wet_cells=wet,source_binding=binding)
            same(terminal,attempt.terminal_panel,'whole_terminal_panel');ledger=terminal.ledger;i=order.selected_cell
            corrected,correction,newtotals=exact_depletion_writeback(terminal.raw_state,cell_index=i,liquid_index=li,vapor_index=vi,
                panel_liquid_start_mol=float(state.amounts_mol[i,li]),panel_liquid_terms_mol=(float(ledger.face_species_mol[i,li]),
                    -float(ledger.face_species_mol[i+1,li]),float(ledger.reaction_species_mol[i,li])),
                positive_evaporated_mol=selected.positive_evaporated_mol,policy=ep.roundoff_policy,totals=totals,clock_evidence=selected)
            same(corrected,attempt.corrected_state,'corrected_full_state');same(correction,attempt.correction,'complete_writeback_record')
            same(newtotals,attempt.candidate_totals,'cumulative_writeback_totals');same(last.state,corrected,'endpoint_observation_state')
            require(last.time==selected.lower,'endpoint_exact_time')
            modes=list(view.operator.interfaces);modes[i]='depleted_no_nucleation'
            require(candidate_view.operator.interfaces==tuple(modes),'actual_mode_transition')
            observation_binding(candidate_view,last.evaluation,corrected)
            geometries=tuple(geometry_binding(v,numeric(o.state),o.evaluation) for v,o in ((view,first),(view,middle),(candidate_view,last)))
            rows.append((packet_index,frame_index,i,first.time,midpoint,selected.lower,len(order.candidates),len(order.exclusions),geometries))
            nc+=len(order.candidates);ne+=len(order.exclusions);totals=newtotals
    same(totals,checked.result.roundoff_totals,'final_committed_roundoff_totals')
    return TerminalProofReport(checked.sha256,len(rows),nc,ne,tuple(rows))
