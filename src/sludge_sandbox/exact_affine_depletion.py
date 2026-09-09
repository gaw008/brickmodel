"""Exact rational affine terminal clocks; explicitly not a coupled event solver."""
from dataclasses import dataclass
from fractions import Fraction
import math
import numpy as np
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.integration import ConservedState
from sludge_sandbox.depletion_roundoff import (DepletionRoundoffError,DepletionRoundoffPolicy,
    DepletionRoundoffTotals,_number,_check_budgets,_half_neighbor_spacing)


def _triple(value):
    if type(value) is not tuple or len(value)!=3:
        raise DepletionRoundoffError('complete_signed_liquid_triple_required')
    return tuple(_number(x,'affine_rate') for x in value)


def _positive_integral(rate,acceleration,duration):
    end=rate+acceleration*duration
    if min(rate,end)>=0:return rate*duration+acceleration*duration*duration/2
    if max(rate,end)<=0:return Fraction()
    zero=-rate/acceleration
    primitive=lambda h:rate*h+acceleration*h*h/2
    return primitive(zero) if rate>0 else primitive(duration)-primitive(zero)


def _down(value):
    result=float(value)
    return math.nextafter(result,-math.inf) if Fraction(result)>value else result


@dataclass(frozen=True)
class ExactAffineSamples:
    """Signed components: left face, negative right face, cell source."""
    start: ExactEventTime
    midpoint: ExactEventTime
    upper: ExactEventTime
    start_inventory_mol: float
    liquid_rates_start_mol_s: tuple[float,float,float]
    liquid_rates_mid_mol_s: tuple[float,float,float]
    evaporation_start_mol_s: float
    evaporation_mid_mol_s: float
    source_ids: tuple[str,...]

    def __post_init__(self):
        if any(type(t) is not ExactEventTime for t in (self.start,self.midpoint,self.upper)) or not self.start<self.midpoint<self.upper:
            raise DepletionRoundoffError('exact_ordered_sample_times_required')
        for name in ('start_inventory_mol','evaporation_start_mol_s','evaporation_mid_mol_s'):
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=name=='start_inventory_mol'))
        for name in ('liquid_rates_start_mol_s','liquid_rates_mid_mol_s'):
            object.__setattr__(self,name,_triple(getattr(self,name)))
        if (type(self.source_ids) is not tuple or not self.source_ids or
            any(type(x) is not str or not x or x.strip()!=x for x in self.source_ids) or len(set(self.source_ids))!=len(self.source_ids)):
            raise DepletionRoundoffError('explicit_unique_source_labels_required')
        h=self.upper.elapsed_since(self.start)
        r=sum(map(Fraction,self.liquid_rates_start_mol_s),Fraction())
        a=sum(self.accelerations,Fraction())
        if max(r,r+a*h)>=0 or self.inventory(h)>0:
            raise DepletionRoundoffError('monotone_first_root_bracket_required')

    @property
    def accelerations(self):
        hm=self.midpoint.elapsed_since(self.start)
        return tuple((Fraction(b)-Fraction(a))/hm for a,b in zip(self.liquid_rates_start_mol_s,self.liquid_rates_mid_mol_s))

    def inventory(self,h):
        return Fraction(self.start_inventory_mol)+sum((Fraction(r)*h+a*h*h/2 for r,a in zip(self.liquid_rates_start_mol_s,self.accelerations)),Fraction())

    def terms(self,h):
        return tuple(float(Fraction(r)*h+a*h*h/2) for r,a in zip(self.liquid_rates_start_mol_s,self.accelerations))

    def gross(self,h):
        r=Fraction(self.evaporation_start_mol_s)
        a=(Fraction(self.evaporation_mid_mol_s)-r)/self.midpoint.elapsed_since(self.start)
        return _positive_integral(r,a,h)


@dataclass(frozen=True)
class ExactAffineEvidence:
    samples: ExactAffineSamples
    lower: ExactEventTime
    upper: ExactEventTime
    iterations: int
    time_absolute_s: float
    policy: DepletionRoundoffPolicy

    def __post_init__(self):
        if type(self.samples) is not ExactAffineSamples or type(self.policy) is not DepletionRoundoffPolicy:
            raise DepletionRoundoffError('explicit_samples_policy_required')
        self.samples.__post_init__()
        if type(self.iterations) is not int or not 1<=self.iterations<=256:
            raise DepletionRoundoffError('bounded_refinement_required')
        if type(self.lower) is not ExactEventTime or type(self.upper) is not ExactEventTime:
            raise DepletionRoundoffError('exact_bracket_required')
        object.__setattr__(self,'time_absolute_s',_number(self.time_absolute_s,'time_absolute',positive=True))
        # There is no nearest rational below an irrational root. This is the
        # adjacent dyadic bin of the declared domain at the stated level.
        full=self.samples.upper.elapsed_since(self.samples.start)
        width=full/(2**self.iterations)
        h=self.lower.elapsed_since(self.samples.start)
        if (h<=0 or h/width!=(h/width).__floor__() or self.upper.elapsed_since(self.lower)!=width
            or self.upper>self.samples.upper or self.samples.inventory(h)<0
            or self.samples.inventory(h+width)>0 or width>Fraction(self.time_absolute_s)):
            raise DepletionRoundoffError('invalid_adjacent_lower_root_enclosure')
        raw=float(Fraction(self.samples.start_inventory_mol)+sum(map(Fraction,self.signed_terms_mol),Fraction()))
        local=4*sum((Fraction(math.ulp(x)) for x in (self.samples.start_inventory_mol,*self.signed_terms_mol,raw)),Fraction())
        if (raw<0 or Fraction(raw)>local+self.samples.inventory(h)
            or Fraction(raw)>Fraction(self.policy.correction_absolute_mol)
            or Fraction(raw)>Fraction(self.positive_evaporated_mol)*Fraction(self.policy.correction_fraction_evaporated)):
            raise DepletionRoundoffError('exact_clock_original_correction_budget')

    @property
    def signed_terms_mol(self):return self.samples.terms(self.lower.elapsed_since(self.samples.start))

    @property
    def exact_positive_evaporated_mol(self):return self.samples.gross(self.lower.elapsed_since(self.samples.start))

    @property
    def positive_evaporated_mol(self):return _down(self.exact_positive_evaporated_mol)

    def inventory_residual(self,start_mol,terms):
        # Revalidate before trusting even a manually constructed frozen object.
        self.__post_init__()
        if start_mol!=self.samples.start_inventory_mol or tuple(terms)!=self.signed_terms_mol:
            raise DepletionRoundoffError('exact_clock_signed_panel_binding_mismatch')
        return self.samples.inventory(self.lower.elapsed_since(self.samples.start))


def locate_exact_affine(samples,*,time_absolute_s,policy,maximum_refinements=256):
    if type(samples) is not ExactAffineSamples or type(policy) is not DepletionRoundoffPolicy:
        raise DepletionRoundoffError('explicit_samples_policy_required')
    samples.__post_init__()
    time_absolute_s=_number(time_absolute_s,'time_absolute',positive=True)
    if type(maximum_refinements) is not int or not 1<=maximum_refinements<=256:
        raise DepletionRoundoffError('bounded_refinement_required')
    low=Fraction();high=samples.upper.elapsed_since(samples.start)
    for count in range(1,maximum_refinements+1):
        mid=(low+high)/2
        if samples.inventory(mid)>=0:low=mid
        else:high=mid
        try:
            return ExactAffineEvidence(samples,samples.start.shifted(low),samples.start.shifted(high),count,time_absolute_s,policy)
        except DepletionRoundoffError as exc:
            if str(exc) not in ('invalid_adjacent_lower_root_enclosure','exact_clock_original_correction_budget'):
                raise
    raise DepletionRoundoffError('exact_clock_refinement_budget_exhausted')


@dataclass(frozen=True)
class ExactDepletionWritebackRecord:
    cell_index: int
    liquid_index: int
    vapor_index: int
    liquid_before_mol: float
    vapor_before_mol: float
    vapor_after_mol: float
    ideal_liquid_increment_mol: Fraction
    ideal_vapor_increment_mol: Fraction
    actual_vapor_increment_mol: Fraction
    vapor_storage_roundoff_mol: Fraction
    panel_liquid_roundoff_mol: Fraction
    local_correction_limit_mol: Fraction
    positive_evaporated_mol: float
    half_neighbor_spacing_mol: Fraction
    qualification: str = 'exact_clock_event_only_accounting_not_coupled_trajectory_verification'
    clock_evidence: ExactAffineEvidence | None = None
    numerical_clock_inventory_residual_mol: Fraction = Fraction(0)


def exact_depletion_writeback(state, *, cell_index, liquid_index, vapor_index,
                        panel_liquid_start_mol, panel_liquid_terms_mol,
                        positive_evaporated_mol, policy, totals, clock_evidence=None):
    """Round one already-localized evaporation panel onto its dry phase face.

    The caller supplies its saved panel liquid terms and separate gross phase
    evaporation diagnostic, never net liquid removal as a surrogate. This
    function checks their arithmetic, not their physical derivation. It cannot
    authorize an event, select a dry constitutive branch, or reset global audits.
    """
    if type(state) is not ConservedState or type(policy) is not DepletionRoundoffPolicy:
        raise DepletionRoundoffError('explicit_state_policy_required')
    if type(totals) is not DepletionRoundoffTotals or totals.policy!=policy:
        raise DepletionRoundoffError('prefix_policy_mismatch')
    cells,columns=state.amounts_mol.shape
    for index,size in ((cell_index,cells),(liquid_index,columns),(vapor_index,columns)):
        if type(index) is not int or not 0<=index<size:
            raise DepletionRoundoffError('invalid_index')
    if liquid_index==vapor_index:
        raise DepletionRoundoffError('distinct_phase_columns_required')
    start=_number(panel_liquid_start_mol,'panel_liquid_start',positive=True)
    if not isinstance(panel_liquid_terms_mol,(tuple,list)) or not panel_liquid_terms_mol:
        raise DepletionRoundoffError('explicit_panel_terms_required')
    terms=tuple(_number(v,'panel_term') for v in panel_liquid_terms_mol)
    exact_liquid=Fraction(start)+sum(map(Fraction,terms),Fraction())
    if exact_liquid<0:
        raise DepletionRoundoffError('negative_panel_liquid')
    liquid=float(state.amounts_mol[cell_index,liquid_index])
    try:
        reconstructed=float(exact_liquid)
    except OverflowError as exc:
        raise DepletionRoundoffError('unrepresentable_panel_liquid') from exc
    if reconstructed!=liquid:
        raise DepletionRoundoffError('panel_state_mismatch')

    delta=Fraction(liquid)
    local=4*sum((Fraction(math.ulp(v)) for v in (start,*terms,liquid)),Fraction())
    if type(clock_evidence) is not ExactAffineEvidence:
        raise DepletionRoundoffError('explicit_exact_clock_evidence_required')
    clock_residual=clock_evidence.inventory_residual(start,terms)
    if clock_evidence.policy != policy or positive_evaporated_mol != clock_evidence.positive_evaporated_mol:
        raise DepletionRoundoffError('exact_clock_policy_or_evaporation_mismatch')
    if delta>local+clock_residual:
        raise DepletionRoundoffError('correction_exceeds_local_ulp_limit')
    if delta>Fraction(policy.correction_absolute_mol):
        raise DepletionRoundoffError('correction_absolute_budget')
    evaporated=_number(positive_evaporated_mol,'positive_evaporated')
    if evaporated<0:
        raise DepletionRoundoffError('negative_evaporated')
    if delta>Fraction(evaporated)*Fraction(policy.correction_fraction_evaporated):
        raise DepletionRoundoffError('correction_exceeds_evaporation_fraction')
    if liquid == 0:
        return state,None,totals
    vapor=float(state.amounts_mol[cell_index,vapor_index])
    exact_vapor=Fraction(vapor)+delta
    try:
        after=float(exact_vapor)
    except OverflowError as exc:
        raise DepletionRoundoffError('unrepresentable_vapor_writeback') from exc
    if not math.isfinite(after):
        raise DepletionRoundoffError('unrepresentable_vapor_writeback')
    residual=Fraction(after)-exact_vapor
    half=_half_neighbor_spacing(exact_vapor,after)
    if abs(residual)>half:
        raise DepletionRoundoffError('storage_rounding_exceeds_neighbor_half_ulp')
    _check_budgets(abs(residual),policy)
    updated_totals=DepletionRoundoffTotals(policy,
        totals.signed_storage_roundoff_mol+residual,
        totals.absolute_storage_roundoff_mol+abs(residual),
        totals.numerical_phase_correction_mol+delta,totals.events+1)
    amounts=np.array(state.amounts_mol)
    amounts[cell_index,liquid_index]=0.
    amounts[cell_index,vapor_index]=after
    result=ConservedState(amounts,state.internal_energy_j,energy_model_identity=state.energy_model_identity,
                          mechanical_stretches=state.mechanical_stretches)
    record=ExactDepletionWritebackRecord(cell_index,liquid_index,vapor_index,liquid,vapor,after,
        -delta,delta,Fraction(after)-Fraction(vapor),residual,Fraction(liquid)-exact_liquid,
        local,evaporated,half,clock_evidence=clock_evidence,
        numerical_clock_inventory_residual_mol=clock_residual)
    return result,record,updated_totals
