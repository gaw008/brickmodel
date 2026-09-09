"""Original-prefix arithmetic audit; deliberately not exact-record resume authority."""
from dataclasses import dataclass, fields
from fractions import Fraction as F
from types import MappingProxyType
from typing import Mapping
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer
from sludge_sandbox.exact_record import ExactRunRecord, EvidenceNode, pack, validate_binding
from sludge_sandbox.integration import ConservedState, IntegrationPolicy
from sludge_sandbox.depletion_integration import DepletionPolicy
from sludge_sandbox.depletion_roundoff import DepletionRoundoffTotals
from sludge_sandbox.exact_affine_depletion import ExactAffineSamples, ExactAffineEvidence, exact_depletion_writeback
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.deforming_solid_storage import _digest


class ExactAuditError(ValueError):
    """External identity or an original prefix budget does not hold."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ExactAuditError(reason)


@dataclass(frozen=True)
class PartialExactAudit:
    record_sha256: str
    accepted_prefixes: int
    committed_events: int
    maxima: Mapping[str, F]
    scope: str = 'partial_audit_original_prefix_and_selected_writeback'
    resume_authorized: bool = False
    missing_gates: tuple[str, ...] = (
        'all_candidate_root_order_and_full_panel_positivity',
        'actual_RK_and_terminal_quadrature_reconstruction',
        'all_event_common_six_gates_and_pressure_certificates',
        'two_consecutive_passes_and_independent_approach',
        'discarded_attempt_resource_reconstruction_and_continuation_budget',
    )


def _state(node: EvidenceNode) -> ConservedState:
    require(type(node) is EvidenceNode and node.kind == 'ConservedState', 'explicit_state')
    return ConservedState(**dict(node.values))


def _selected_writeback(terminal, ep, totals, li, vi):
    """Reconstruct selected source-sample affine proof and existing budget boundary."""
    cell = terminal.root_order.selected_cell
    candidates = [c for c in terminal.root_order.candidates if c.cell_index == cell]
    require(len(candidates) == 1, 'one_selected_candidate')
    saved = candidates[0].evidence
    require(saved.samples.kind == 'ExactAffineSamples', 'selected_affine_samples')
    samples = ExactAffineSamples(**dict(saved.samples.values))
    require(samples.source_ids == ('exact-operator:'+_digest(terminal.original_operator.identity),), 'selected_actual_operator_source_labels')
    require(pack(saved.policy) == pack(ep.roundoff_policy), 'selected_original_roundoff_policy')
    evidence = ExactAffineEvidence(**{f.name: (samples if f.name == 'samples' else ep.roundoff_policy if f.name == 'policy' else getattr(saved, f.name)) for f in fields(ExactAffineEvidence)})
    require(F(evidence.time_absolute_s) == F(ep.time_absolute_s), 'selected_original_time_gate')
    first, mid, last = terminal.observations
    require((first.role,mid.role,last.role)==('initial','midpoint','endpoint'), 'terminal_observation_roles')
    require(first.time == samples.start and mid.time == samples.midpoint and last.time == evidence.lower, 'sample_times')
    require(pack(first.state)==pack(terminal.initial_state), 'sample_initial_state')
    require(samples.start_inventory_mol == first.state.amounts_mol[cell,li], 'sample_initial_liquid')
    for observation, rates, evaporation in ((first,samples.liquid_rates_start_mol_s,samples.evaporation_start_mol_s), (mid,samples.liquid_rates_mid_mol_s,samples.evaporation_mid_mol_s)):
        r = observation.evaluation.rates
        actual = (F(float(r.face_species_mol_s[cell,li])), -F(float(r.face_species_mol_s[cell+1,li])), F(float(r.reaction_species_mol_s[cell,li])))
        require(rates == actual, 'selected_sample_signed_rates')
        require(evaporation == F(float(observation.evaluation.cell_transfers[cell].rate_mol_s)), 'selected_gross_samples')
    ledger = terminal.terminal_panel.ledger
    require(ledger.start_s==samples.start and ledger.end_s==evidence.lower, 'selected_panel_time')
    terms=(float(ledger.face_species_mol[cell,li]),-float(ledger.face_species_mol[cell+1,li]),float(ledger.reaction_species_mol[cell,li]))
    raw=_state(terminal.terminal_panel.raw_state)
    corrected, correction, updated=exact_depletion_writeback(raw,cell_index=cell,liquid_index=li,vapor_index=vi,
        panel_liquid_start_mol=samples.start_inventory_mol,panel_liquid_terms_mol=terms,
        positive_evaporated_mol=evidence.positive_evaporated_mol,policy=ep.roundoff_policy,totals=totals,clock_evidence=evidence)
    require(pack(corrected)==pack(terminal.corrected_state), 'recomputed_writeback_state')
    require(pack(correction)==pack(terminal.correction), 'recomputed_writeback_record')
    require(pack(totals)==pack(terminal.input_totals) and pack(updated)==pack(terminal.candidate_totals), 'terminal_original_cumulative_totals')
    return correction, updated


def audit_exact_run(record: ExactRunRecord, actual_original_operator: ExactFreeWaterTransfer, *, original_initial: ConservedState,
                    start: ExactEventTime, end: ExactEventTime, integration_policy: IntegrationPolicy,
                    event_policy: DepletionPolicy, case_sha256: str, runtime_identity: Mapping[str, object]) -> PartialExactAudit:
    """Always reparse/rebind bytes; no trust in replaceable record object fields."""
    require(type(original_initial) is ConservedState and type(integration_policy) is IntegrationPolicy and type(event_policy) is DepletionPolicy, 'explicit_external_original_inputs')
    require(type(start) is ExactEventTime and type(end) is ExactEventTime, 'explicit_external_exact_interval')
    checked=validate_binding(record,actual_original_operator,case_sha256=case_sha256,runtime_identity=runtime_identity)
    r=checked.result
    require(pack(checked.states[0])==pack(original_initial) and checked.start==start and checked.end==end, 'external_original_initial_interval')
    require(pack(r.initial_policy)==pack(integration_policy) and pack(r.event_policy)==pack(event_policy), 'external_original_policies')
    require(original_initial.energy_model_identity==actual_original_operator.energy_model_identity, 'external_energy_identity')
    require(event_policy.roundoff_policy.molar_mass_kg_mol==actual_original_operator.operator.chemical.reference.molar_mass_kg_mol,'external_water_molar_mass')
    require(original_initial.mechanical_stretches is not None and integration_policy.stretch_absolute_tolerance is not None,'original_mechanical_contract')
    li,vi=checked.binding['liquid_index'],checked.binding['water_vapor_index']
    totals=DepletionRoundoffTotals(event_policy.roundoff_policy); corrections={}; event_count=0
    for packet in r.packets:
        for frame in packet:
            terminal=frame.terminal
            indexes=[i for i,l in enumerate(checked.ledgers) if pack(l)==pack(terminal.terminal_panel.ledger)]
            require(len(indexes)==1 and indexes[0] not in corrections,'unique_committed_panel')
            c,totals=_selected_writeback(terminal,event_policy,totals,li,vi)
            corrections[indexes[0]]=c;event_count+=1
    require(pack(totals)==pack(r.roundoff_totals),'original_final_roundoff_totals')
    n0,e0,s0=original_initial.amounts_mol,original_initial.internal_energy_j,original_initial.mechanical_stretches
    cells,cols=n0.shape
    cn=[[F() for _ in range(cols)] for _ in range(cells)];cu=[F()]*cells;cp=cu.copy()
    cs=[F()]*(cells+1);cx=cs.copy();cq=cs.copy()
    maxima={k:F() for k in ('amount','energy','component_absolute','stretch_represented','stretch_exact','stretch_absolute_quadrature')}
    def budget(key,value,limit):
        maxima[key]=max(maxima[key],value)
        require(value<=F(limit),'original_'+key+'_prefix_budget')
    schema=None
    for index,(ledger,state) in enumerate(zip(checked.ledgers,checked.states[1:])):
        previous=checked.states[index];c=corrections.get(index)
        for cell in range(cells):
            for species in range(cols):
                increment=F(float(ledger.face_species_mol[cell,species]))-F(float(ledger.face_species_mol[cell+1,species]))+F(float(ledger.reaction_species_mol[cell,species]))
                if c is not None and cell==c.cell_index:
                    if species==li:increment+=c.ideal_liquid_increment_mol
                    if species==vi:increment+=c.ideal_vapor_increment_mol+c.vapor_storage_roundoff_mol
                cn[cell][species]+=increment
                budget('amount',abs(F(float(state.amounts_mol[cell,species]))-F(float(previous.amounts_mol[cell,species]))-increment),integration_policy.amount_absolute_tolerance_mol)
                budget('amount',abs(F(float(state.amounts_mol[cell,species]))-F(float(n0[cell,species]))-cn[cell][species]),integration_policy.amount_absolute_tolerance_mol)
            increment=F(float(ledger.face_energy_j[cell]))-F(float(ledger.face_energy_j[cell+1]))+F(float(ledger.cell_work_j[cell]))
            cu[cell]+=increment
            budget('energy',abs(F(float(state.internal_energy_j[cell]))-F(float(previous.internal_energy_j[cell]))-increment),integration_policy.energy_absolute_tolerance_j)
            budget('energy',abs(F(float(state.internal_energy_j[cell]))-F(float(e0[cell]))-cu[cell]),integration_policy.energy_absolute_tolerance_j)
        parts=ledger.cell_work_components_j
        require(parts is not None,'full_power_components_required')
        if schema is None:schema=tuple(parts)
        require(tuple(parts)==schema,'original_component_schema')
        for cell in range(cells):
            residual=F(float(ledger.cell_work_j[cell]))-sum((F(float(v[cell])) for v in parts.values()),F())
            require(residual==ledger.component_sum_residual_j[cell],'recomputed_component_residual')
            cp[cell]+=abs(residual);budget('component_absolute',cp[cell],integration_policy.energy_absolute_tolerance_j)
        for j in range(cells+1):
            inc=F(float(ledger.stretch_increment[j]));error=ledger.stretch_quadrature_roundoff[j];exact=inc-error
            cs[j]+=inc;cx[j]+=exact;cq[j]+=abs(error)
            local=F(float(state.mechanical_stretches[j]))-F(float(previous.mechanical_stretches[j]))
            change=F(float(state.mechanical_stretches[j]))-F(float(s0[j]))
            budget('stretch_represented',max(abs(local-inc),abs(change-cs[j])),integration_policy.stretch_absolute_tolerance)
            budget('stretch_exact',max(abs(local-exact),abs(change-cx[j])),integration_policy.stretch_absolute_tolerance)
            budget('stretch_absolute_quadrature',cq[j],integration_policy.stretch_absolute_tolerance)
    # Recheck actual provider binding after arithmetic work, without any EOS.
    final=validate_binding(checked,actual_original_operator,case_sha256=case_sha256,runtime_identity=runtime_identity)
    require(final.sha256==checked.sha256,'audit_record_identity_changed')
    return PartialExactAudit(checked.sha256,len(checked.ledgers),event_count,MappingProxyType(maxima))
