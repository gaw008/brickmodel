"""One source-bound speculative exact terminal; never packet acceptance."""
from dataclasses import dataclass,fields
from fractions import Fraction as F
import time
from sludge_sandbox.integration import ConservedState,IntegrationPolicy,IntegrationError,DomainExit
from sludge_sandbox.depletion_integration import DepletionPolicy
from sludge_sandbox.depletion_roundoff import DepletionRoundoffTotals
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer,_water_bindings
from sludge_sandbox.water_phase_transfer import WaterTransferEvaluation
from sludge_sandbox.exact_terminal_panel import build_exact_affine_panel
from sludge_sandbox.exact_root_order import order_exact_affine_roots
from sludge_sandbox.exact_affine_depletion import exact_depletion_writeback
from sludge_sandbox.deforming_solid_storage import _digest


@dataclass(frozen=True)
class TerminalObservation:
    role:str
    time:ExactEventTime
    state:ConservedState
    evaluation:WaterTransferEvaluation


@dataclass(frozen=True)
class TerminalCosts:
    evaluation_attempts:int
    evaluation_completed:int
    predictor_panels:int
    terminal_panels:int
    mode_transition_attempts:int
    predictor_panel_attempts:int
    terminal_panel_attempts:int
    root_order_attempts:int
    writeback_attempts:int
    elapsed_seconds:float


@dataclass(frozen=True)
class ExactTerminalAttempt:
    status:str
    reason:str|None
    initial_state:ConservedState
    original_operator:ExactFreeWaterTransfer
    input_totals:DepletionRoundoffTotals
    observations:tuple[TerminalObservation,...]
    predictor_panel:object
    root_order:object
    terminal_panel:object
    corrected_state:ConservedState|None
    correction:object
    candidate_totals:DepletionRoundoffTotals|None
    candidate_operator:ExactFreeWaterTransfer|None
    costs:TerminalCosts
    failure_diagnostic:object=None
    qualification:str='single_speculative_terminal_not_packet_or_trajectory_acceptance'


class _TerminalStop(ValueError):
    def __init__(self,status,reason):super().__init__(reason);self.status=status


def execute_exact_terminal(state,operator,*,start,common_endpoint,integration_policy,event_policy,totals,cancel=None):
    if type(state) is not ConservedState or type(operator) is not ExactFreeWaterTransfer:
        raise IntegrationError('explicit_exact_host_state_required')
    if type(start) is not ExactEventTime or type(common_endpoint) is not ExactEventTime or common_endpoint<=start:
        raise IntegrationError('exact_terminal_interval_required')
    if type(integration_policy) is not IntegrationPolicy or type(event_policy) is not DepletionPolicy or event_policy.terminal_method!='affine_midpoint':
        raise IntegrationError('original_affine_policies_required')
    if type(totals) is not DepletionRoundoffTotals or totals.policy!=event_policy.roundoff_policy:
        raise IntegrationError('original_roundoff_totals_required')
    if cancel is not None and not callable(cancel):raise IntegrationError('invalid_cancel_callback')
    begin=time.monotonic();attempts=completed=predictor_count=panel_count=mode_attempts=0
    predictor_attempts=panel_attempts=root_attempts=writeback_attempts=0
    observations=[];predictor=order=panel=corrected=correction=candidate_totals=candidate_operator=None
    original_identity=None
    def guard():
        if cancel is not None and cancel():raise _TerminalStop('cancelled','cancel_requested')
        if time.monotonic()-begin>=integration_policy.maximum_wall_seconds:raise _TerminalStop('resource_limit','wall_time_limit')
        if original_identity is not None and operator.operator_identity!=original_identity:
            raise IntegrationError('terminal_original_operator_changed')
    def observe(view,current,at,role):
        nonlocal attempts,completed
        guard();attempts+=1
        result=view.evaluate(current,at);completed+=1
        # Save actual returned output before subsequent validation can fail.
        observations.append(TerminalObservation(role,at,current,result))
        guard()
        if type(result) is not WaterTransferEvaluation or len(result.cell_transfers)!=len(current.amounts_mol):
            raise IntegrationError('complete_actual_transfer_observation_required')
        result.rates.derivatives(current)
        if result.interface_modes!=view.operator.interfaces:
            raise IntegrationError('actual_transfer_mode_mismatch')
        return result
    def stable_content(view):
        return (_digest(tuple((f.name,getattr(view.operator,f.name)) for f in fields(view.operator) if f.name!='interface_modes')),
                _water_bindings(view.operator))
    try:
        guard();original_identity=operator.operator_identity
        if event_policy.roundoff_policy.molar_mass_kg_mol!=operator.operator.chemical.reference.molar_mass_kg_mol:
            raise IntegrationError('roundoff_water_molar_mass_mismatch')
        model=operator.energy_model_identity
        if state.energy_model_identity!=model:raise IntegrationError('terminal_energy_model_identity_mismatch')
        original_content=stable_content(operator)
        li=operator.operator.liquid_index;vi=operator.operator.water_vapor_index;modes=operator.operator.interfaces
        if (len(modes)!=len(state.amounts_mol) or type(li) is not int or type(vi) is not int
            or li==vi or not 0<=li<state.amounts_mol.shape[1] or not 0<=vi<state.amounts_mol.shape[1]):
            raise IntegrationError('interface_inventory_shape_mismatch')
        wet=tuple(i for i,m in enumerate(modes) if m=='existing_liquid')
        if wet!=tuple(i for i,row in enumerate(state.amounts_mol) if row[li]>0):raise IntegrationError('complete_wet_mode_inventory_required')
        first=observe(operator,state,start,'initial')
        evaporation=lambda ev:tuple(float(item.rate_mol_s) for item in ev.cell_transfers)
        e0=evaporation(first);options=[]
        for i in wet:
            r=F(float(first.rates.face_species_mol_s[i,li]))-F(float(first.rates.face_species_mol_s[i+1,li]))+F(float(first.rates.reaction_species_mol_s[i,li]))
            if r<0:
                if e0[i]<=0:raise IntegrationError('unsupported_non_evaporative_liquid_depletion')
                options.append((F(float(state.amounts_mol[i,li]))/-r,i))
        if not options:raise IntegrationError('no_terminal_depletion_candidate')
        tau,hint=min(options);midpoint=start.shifted(tau/2);upper=min(common_endpoint,start.shifted(2*tau))
        if not start<midpoint<upper:raise IntegrationError('exact_affine_midpoint_outside_interval')
        binding=('exact-operator:'+_digest(original_identity),)
        predictor_attempts+=1
        predictor=build_exact_affine_panel(state,first.rates,first.rates,start=start,midpoint=start.shifted(tau/4),end=midpoint,
            policy=integration_policy,liquid_index=li,selected_cell=hint,wet_cells=wet,source_binding=binding);predictor_count+=1
        if any(predictor.raw_state.amounts_mol[i,li]<=0 for i in wet):raise IntegrationError('affine_midpoint_not_wet')
        middle=observe(operator,predictor.raw_state,midpoint,'midpoint')
        guard();root_attempts+=1
        order=order_exact_affine_roots(state,first.rates,middle.rates,start=start,midpoint=midpoint,upper=upper,
            liquid_index=li,wet_cells=wet,evaporation_start_mol_s=e0,evaporation_mid_mol_s=evaporation(middle),
            source_binding=binding,time_absolute_s=event_policy.time_absolute_s,policy=event_policy.roundoff_policy)
        chosen=next(c.evidence for c in order.candidates if c.cell_index==order.selected_cell)
        endpoint=chosen.lower
        if not midpoint<endpoint<common_endpoint:raise IntegrationError('exact_terminal_root_outside_interval')
        guard()
        panel_attempts+=1
        panel=build_exact_affine_panel(state,first.rates,middle.rates,start=start,midpoint=midpoint,end=endpoint,
            policy=integration_policy,liquid_index=li,selected_cell=order.selected_cell,wet_cells=wet,source_binding=binding);panel_count+=1
        ledger=panel.ledger
        guard();writeback_attempts+=1
        corrected,correction,candidate_totals=exact_depletion_writeback(panel.raw_state,cell_index=order.selected_cell,liquid_index=li,vapor_index=vi,
            panel_liquid_start_mol=float(state.amounts_mol[order.selected_cell,li]),
            panel_liquid_terms_mol=(float(ledger.face_species_mol[order.selected_cell,li]),-float(ledger.face_species_mol[order.selected_cell+1,li]),float(ledger.reaction_species_mol[order.selected_cell,li])),
            positive_evaporated_mol=chosen.positive_evaporated_mol,policy=event_policy.roundoff_policy,totals=totals,clock_evidence=chosen)
        guard();mode_attempts+=1;candidate_operator=operator.with_depleted_cells(corrected,(order.selected_cell,))
        expected=list(modes);expected[order.selected_cell]='depleted_no_nucleation'
        if (candidate_operator.operator.interfaces!=tuple(expected) or stable_content(candidate_operator)!=original_content
            or candidate_operator.energy_model_identity!=model):raise IntegrationError('terminal_mode_transition_content_mismatch')
        observe(candidate_operator,corrected,endpoint,'endpoint')
        guard();status='speculative_completed';reason=None;diagnostic=None
    except (ValueError,TypeError,AttributeError,OverflowError) as exc:
        status=exc.status if isinstance(exc,_TerminalStop) else ('domain_exit' if isinstance(exc,DomainExit) else 'failed');reason=str(exc)
        diagnostic=getattr(exc,'diagnostic',None)
    return ExactTerminalAttempt(status,reason,state,operator,totals,tuple(observations),predictor,order,panel,corrected,correction,
        candidate_totals,candidate_operator,TerminalCosts(attempts,completed,predictor_count,panel_count,mode_attempts,predictor_attempts,panel_attempts,root_attempts,writeback_attempts,time.monotonic()-begin),diagnostic)
