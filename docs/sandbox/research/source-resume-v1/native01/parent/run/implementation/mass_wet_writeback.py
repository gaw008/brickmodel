"""Local mixed-state projection with caller-bound exact affine evidence.

No root search, actual source/provider verification, mode switch, event admission,
whole-trajectory audit or resume permission is supplied by this primitive.
"""
from dataclasses import dataclass,replace,fields
from fractions import Fraction as F
import math
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.exact_affine_depletion import ExactAffineEvidence
from sludge_sandbox.depletion_roundoff import (DepletionRoundoffPolicy,DepletionRoundoffTotals,
    DepletionRoundoffError,_check_budgets,_half_neighbor_spacing)

def need(ok,reason):
    if not ok:raise DepletionRoundoffError(reason)
def digest(value):
    need(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'explicit_binding_digest')
def labels(value):
    need(type(value) is tuple and value and all(type(x) is str and x and x.strip()==x for x in value) and len(set(value))==len(value),'explicit_source_labels')
def time_value(t):
    need(type(t) is ExactEventTime and type(t.seconds) is F,'exact_time_required')
def number(v):
    need(type(v) is float and math.isfinite(v),'represented_finite_float_required');return F(v)
def state(s):
    need(type(s) is WetMixedState,'typed_mixed_state_required')
    digest(s.energy_model_identity)
    need(type(s.solid_mass_kg) is tuple and len(s.solid_mass_kg)==2 and type(s.gas_amounts_mol) is tuple and len(s.gas_amounts_mol)==3,'explicit_AB_O2_N2_H2O_layout')
    for x in (*s.solid_mass_kg,s.liquid_water_mol,*s.gas_amounts_mol):need(number(x)>=0,'negative_inventory')
    number(s.internal_energy_j)
def terms(row):
    need(type(row) is tuple and row,'complete_signed_terms')
    return tuple(number(v) for v in row)
def rounded(v):
    try:r=float(v)
    except OverflowError as e:raise DepletionRoundoffError('unrepresentable_panel_or_vapor') from e
    need(math.isfinite(r) and (v==0 or r!=0),'unrepresentable_panel_or_vapor');return r

@dataclass(frozen=True)
class MixedWritebackContext:
    original_states: tuple
    original_time: ExactEventTime
    operator_identity: str
    source_ids: tuple
    water_molar_mass_kg_mol: float
    policy: DepletionRoundoffPolicy
    original_liquid_fraction_limit: F
    def __post_init__(self):
        need(type(self.original_states) is tuple and self.original_states,'original_states_required')
        for s in self.original_states:state(s)
        time_value(self.original_time);digest(self.operator_identity);labels(self.source_ids)
        need(type(self.policy) is DepletionRoundoffPolicy,'original_roundoff_policy_required')
        # Reconstruct without mutating even a forged original frozen instance.
        values={f.name:getattr(self.policy,f.name) for f in fields(self.policy)}
        need(all(type(v) is float for v in values.values()),'typed_policy_fields')
        need(DepletionRoundoffPolicy(**values)==self.policy,'invalid_original_policy')
        need(number(self.water_molar_mass_kg_mol)>0 and self.water_molar_mass_kg_mol==self.policy.molar_mass_kg_mol,'same_water_molar_mass')
        need(type(self.original_liquid_fraction_limit) is F and 0<self.original_liquid_fraction_limit<=F('1e-8'),'explicit_conservative_original_liquid_fraction')

@dataclass(frozen=True)
class MixedWritebackTotals:
    context: MixedWritebackContext
    per_cell: tuple
    def __post_init__(self):
        need(type(self.context) is MixedWritebackContext,'typed_context_required');self.context.__post_init__()
        need(type(self.per_cell) is tuple and len(self.per_cell)==len(self.context.original_states),'complete_per_cell_totals')
        for original,total in zip(self.context.original_states,self.per_cell):
            need(type(total) is DepletionRoundoffTotals and total.policy==self.context.policy,'original_per_cell_policy')
            total.__post_init__()
            need(total.numerical_phase_correction_mol<=F(original.liquid_water_mol)*self.context.original_liquid_fraction_limit,'original_cell_liquid_fraction_budget')
        self.aggregate
    @classmethod
    def empty(cls,context):
        return cls(context,tuple(DepletionRoundoffTotals(context.policy) for _ in context.original_states))
    @property
    def aggregate(self):
        return DepletionRoundoffTotals(self.context.policy,
            sum((t.signed_storage_roundoff_mol for t in self.per_cell),F()),
            sum((t.absolute_storage_roundoff_mol for t in self.per_cell),F()),
            sum((t.numerical_phase_correction_mol for t in self.per_cell),F()),sum(t.events for t in self.per_cell))

@dataclass(frozen=True)
class MixedCellPanelTerms:
    solid_kg: tuple
    liquid_mol: tuple
    gas_mol: tuple
    energy_j: tuple
    def __post_init__(self):
        need(type(self.solid_kg) is tuple and len(self.solid_kg)==2 and type(self.gas_mol) is tuple and len(self.gas_mol)==3,'complete_panel_layout')
        for row in (*self.solid_kg,self.liquid_mol,*self.gas_mol,self.energy_j):terms(row)

@dataclass(frozen=True)
class MixedTerminalEvidence:
    cell_index: int
    panel_start_states: tuple
    raw_states: tuple
    panel_terms: tuple
    modes: tuple
    operator_identity: str
    source_ids: tuple
    clock: ExactAffineEvidence
    def __post_init__(self):
        need(type(self.panel_start_states) is tuple and self.panel_start_states,'complete_panel_start')
        n=len(self.panel_start_states)
        need(type(self.cell_index) is int and 0<=self.cell_index<n,'selected_cell_index')
        need(type(self.raw_states) is tuple and type(self.panel_terms) is tuple and type(self.modes) is tuple and len(self.raw_states)==len(self.panel_terms)==len(self.modes)==n,'complete_terminal_fields')
        digest(self.operator_identity);labels(self.source_ids)
        need(type(self.clock) is ExactAffineEvidence,'existing_exact_clock_required');self.clock.__post_init__()
        for before,after,panel,mode in zip(self.panel_start_states,self.raw_states,self.panel_terms,self.modes):
            state(before);state(after);need(type(panel) is MixedCellPanelTerms,'typed_panel_terms');panel.__post_init__()
            need(type(mode) is str and mode in ('wet','dry'),'explicit_existing_mode')
            need(before.energy_model_identity==after.energy_model_identity,'panel_model_changed')
            need((before.liquid_water_mol>0)==(mode=='wet'),'mode_initial_inventory_mismatch')
            if mode=='dry':need(after.liquid_water_mol==0,'dry_cell_rewet_unsupported')
            vectors=((before.solid_mass_kg,after.solid_mass_kg,panel.solid_kg),(before.gas_amounts_mol,after.gas_amounts_mol,panel.gas_mol),((before.liquid_water_mol,),(after.liquid_water_mol,),(panel.liquid_mol,)),((before.internal_energy_j,),(after.internal_energy_j,),(panel.energy_j,)))
            for a,b,rows in vectors:
                for x,y,row in zip(a,b,rows):need(rounded(F(x)+sum(terms(row),F()))==y,'whole_raw_panel_state_mismatch')
        i=self.cell_index;sample=self.clock.samples
        need(self.modes[i]=='wet','selected_existing_liquid_required')
        need(sample.source_ids==self.source_ids,'clock_source_binding')
        need(self.panel_start_states[i].liquid_water_mol==sample.start_inventory_mol,'selected_clock_inventory_binding')
        need(self.panel_terms[i].liquid_mol==self.clock.signed_terms_mol,'signed_clock_panel_binding')
        # Current mixed host has no liquid face flux or water chemical source.
        for row,phase in ((sample.liquid_rates_start_mol_s,sample.evaporation_start_mol_s),(sample.liquid_rates_mid_mol_s,sample.evaporation_mid_mol_s)):
            need(row[0]==0 and row[1]==0 and F(row[2])==-F(phase),'phase_only_liquid_sample_required')

@dataclass(frozen=True)
class MixedWritebackRecord:
    evidence: MixedTerminalEvidence
    original_state: WetMixedState
    ideal_liquid_increment_mol: F
    ideal_vapor_increment_mol: F
    actual_vapor_increment_mol: F
    vapor_storage_roundoff_mol: F
    panel_liquid_roundoff_mol: F
    local_ulp_limit_mol: F
    clock_inventory_residual_mol: F
    gross_positive_evaporation_exact_mol: F
    gross_positive_evaporation_down_mol: float
    half_neighbor_spacing_mol: F

@dataclass(frozen=True)
class MixedWritebackCandidate:
    states: tuple
    record: MixedWritebackRecord | None
    totals: MixedWritebackTotals
    qualification: str='local_projection_only_no_mode_switch_event_acceptance_source_authentication_or_resume'

def project_mixed_depletion(evidence,*,context,totals):
    """Return new immutable candidate only after every original budget passes.

    Caller must separately bind the supplied operator/source digests and sample
    rates to actual provider evaluations, root ordering and physical stages.
    """
    need(type(context) is MixedWritebackContext and type(totals) is MixedWritebackTotals and type(evidence) is MixedTerminalEvidence,'explicit_local_projection_inputs')
    context.__post_init__();totals.__post_init__();evidence.__post_init__()
    need(totals.context==context,'original_context_changed')
    need(evidence.operator_identity==context.operator_identity and evidence.source_ids==context.source_ids,'original_operator_source_binding')
    need(len(evidence.raw_states)==len(context.original_states),'original_cell_count')
    need(evidence.clock.samples.start>=context.original_time,'panel_before_original_time')
    for original,before in zip(context.original_states,evidence.panel_start_states):need(original.energy_model_identity==before.energy_model_identity,'original_model_binding')
    i=evidence.cell_index;raw=evidence.raw_states[i];panel=evidence.panel_terms[i];start=evidence.panel_start_states[i].liquid_water_mol;clock=evidence.clock
    need(clock.policy==context.policy,'original_clock_policy')
    residual=clock.inventory_residual(start,panel.liquid_mol)
    exact_liquid=F(start)+sum(terms(panel.liquid_mol),F());need(exact_liquid>=0,'negative_represented_panel_liquid')
    delta=F(raw.liquid_water_mol);local=4*sum((F(math.ulp(x)) for x in (start,*panel.liquid_mol,raw.liquid_water_mol)),F())
    need(delta<=local+residual,'correction_exceeds_local_ulp_limit')
    p=context.policy;need(delta<=F(p.correction_absolute_mol),'correction_absolute_budget')
    gross=clock.positive_evaporated_mol
    need(delta<=F(gross)*F(p.correction_fraction_evaporated),'correction_exceeds_evaporation_fraction')
    need(totals.per_cell[i].numerical_phase_correction_mol+delta<=F(context.original_states[i].liquid_water_mol)*context.original_liquid_fraction_limit,'original_cell_liquid_fraction_budget')
    if delta==0:return MixedWritebackCandidate(evidence.raw_states,None,totals)
    vapor=raw.gas_amounts_mol[2];exact_vapor=F(vapor)+delta;after=rounded(exact_vapor);error=F(after)-exact_vapor;half=_half_neighbor_spacing(exact_vapor,after)
    need(abs(error)<=half,'storage_rounding_exceeds_neighbor_half_ulp');_check_budgets(abs(error),p)
    old=totals.per_cell[i];updated=DepletionRoundoffTotals(p,old.signed_storage_roundoff_mol+error,old.absolute_storage_roundoff_mol+abs(error),old.numerical_phase_correction_mol+delta,old.events+1)
    cells=list(totals.per_cell);cells[i]=updated;next_totals=MixedWritebackTotals(context,tuple(cells))
    gas=raw.gas_amounts_mol[:2]+(after,);states=list(evidence.raw_states);states[i]=replace(raw,liquid_water_mol=0.,gas_amounts_mol=gas)
    record=MixedWritebackRecord(evidence,context.original_states[i],-delta,delta,F(after)-F(vapor),error,F(raw.liquid_water_mol)-exact_liquid,local,residual,clock.exact_positive_evaporated_mol,gross,half)
    return MixedWritebackCandidate(tuple(states),record,next_totals)
