"""Audited event-only water write-back; does not locate a depletion event.

A paired numerical phase correction and binary64 storage rounding are distinct.
Ordinary panel/face/reaction ledgers remain the caller's responsibility.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction
import math
from numbers import Real

import numpy as np

from .integration import ConservedState


class DepletionRoundoffError(ValueError):
    """Invalid event reconstruction or an exceeded declared numerical budget."""


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise DepletionRoundoffError('invalid_'+name)
    try:
        result=float(value)
    except (ValueError, OverflowError) as exc:
        raise DepletionRoundoffError('invalid_'+name) from exc
    if result==0 and value!=0:
        raise DepletionRoundoffError('nonzero_underflow_'+name)
    if not math.isfinite(result) or (positive and result<=0):
        raise DepletionRoundoffError('invalid_'+name)
    return result


@dataclass(frozen=True, kw_only=True)
class DepletionRoundoffPolicy:
    correction_absolute_mol: float
    correction_fraction_evaporated: float
    storage_absolute_mol: float
    cumulative_storage_absolute_mol: float
    element_absolute_mol: float
    cumulative_element_absolute_mol: float
    mass_absolute_kg: float
    cumulative_mass_absolute_kg: float
    cumulative_correction_absolute_mol: float
    molar_mass_kg_mol: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=True))
        if self.correction_fraction_evaporated>1e-8:
            raise DepletionRoundoffError('correction_fraction_exceeds_preregistered_limit')


@dataclass(frozen=True)
class DepletionRoundoffTotals:
    policy: DepletionRoundoffPolicy
    signed_storage_roundoff_mol: Fraction = Fraction(0)
    absolute_storage_roundoff_mol: Fraction = Fraction(0)
    numerical_phase_correction_mol: Fraction = Fraction(0)
    events: int = 0

    def __post_init__(self):
        if type(self.policy) is not DepletionRoundoffPolicy:
            raise DepletionRoundoffError('explicit_policy_required')
        for name in ('signed_storage_roundoff_mol','absolute_storage_roundoff_mol','numerical_phase_correction_mol'):
            if type(getattr(self,name)) is not Fraction:
                raise DepletionRoundoffError('exact_prefix_required')
        if (type(self.events) is not int or self.events<0
                or self.absolute_storage_roundoff_mol<abs(self.signed_storage_roundoff_mol)
                or self.numerical_phase_correction_mol<0):
            raise DepletionRoundoffError('invalid_prefix')
        if self.events==0 and any((self.signed_storage_roundoff_mol,
                self.absolute_storage_roundoff_mol,self.numerical_phase_correction_mol)):
            raise DepletionRoundoffError('nonzero_empty_prefix')
        if self.absolute_storage_roundoff_mol>self.numerical_phase_correction_mol:
            raise DepletionRoundoffError('prefix_roundoff_exceeds_phase_correction')
        _check_budgets(self.absolute_storage_roundoff_mol,self.policy,cumulative=True)
        if self.numerical_phase_correction_mol>Fraction(self.policy.cumulative_correction_absolute_mol):
            raise DepletionRoundoffError('cumulative_phase_correction_budget')


    def to_record(self):
        """Versioned exact event-only prefix, suitable for JSON persistence."""
        return dict(schema='water_depletion_roundoff_prefix_v1',policy=asdict(self.policy),
            signed_storage_roundoff_mol=str(self.signed_storage_roundoff_mol),
            absolute_storage_roundoff_mol=str(self.absolute_storage_roundoff_mol),
            numerical_phase_correction_mol=str(self.numerical_phase_correction_mol),events=self.events)

    @classmethod
    def from_record(cls, record):
        fields={'schema','policy','signed_storage_roundoff_mol','absolute_storage_roundoff_mol',
                'numerical_phase_correction_mol','events'}
        if (type(record) is not dict or set(record)!=fields
                or record['schema']!='water_depletion_roundoff_prefix_v1'
                or type(record['policy']) is not dict
                or set(record['policy'])!=set(DepletionRoundoffPolicy.__dataclass_fields__)):
            raise DepletionRoundoffError('invalid_prefix_record')
        names=('signed_storage_roundoff_mol','absolute_storage_roundoff_mol','numerical_phase_correction_mol')
        if any(type(record[name]) is not str for name in names):
            raise DepletionRoundoffError('exact_prefix_strings_required')
        try:
            values=[Fraction(record[name]) for name in names]
        except (ValueError,ZeroDivisionError) as exc:
            raise DepletionRoundoffError('invalid_exact_prefix') from exc
        return cls(DepletionRoundoffPolicy(**record['policy']),*values,record['events'])


@dataclass(frozen=True)
class DepletionWritebackRecord:
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
    qualification: str = 'event_only_accounting_not_event_time_or_full_trajectory_verification'


def _check_budgets(absolute_residual, policy, *, cumulative=False):
    prefix='cumulative_' if cumulative else ''
    limits=(('storage',absolute_residual,getattr(policy,prefix+'storage_absolute_mol')),
            ('element',2*absolute_residual,getattr(policy,prefix+'element_absolute_mol')),
            ('mass',absolute_residual*Fraction(policy.molar_mass_kg_mol),getattr(policy,prefix+'mass_absolute_kg')))
    for name,value,limit in limits:
        if value>Fraction(limit):
            raise DepletionRoundoffError(prefix+name+'_roundoff_budget')


def _half_neighbor_spacing(exact, rounded):
    represented=Fraction(rounded)
    direction=math.inf if exact>represented else -math.inf
    neighbor=math.nextafter(rounded,direction)
    # Largest finite output still has a finite inward spacing. Overflow itself
    # is rejected before this helper; this is the binary64 overflow midpoint.
    if not math.isfinite(neighbor):
        neighbor=math.nextafter(rounded,-math.inf)
    return abs(Fraction(neighbor)-represented)/2


def depletion_writeback(state, *, cell_index, liquid_index, vapor_index,
                        panel_liquid_start_mol, panel_liquid_terms_mol,
                        positive_evaporated_mol, policy, totals):
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
    if liquid==0:
        raise DepletionRoundoffError('no_positive_liquid_remainder')
    delta=Fraction(liquid)
    local=4*sum((Fraction(math.ulp(v)) for v in (start,*terms,liquid)),Fraction())
    if delta>local:
        raise DepletionRoundoffError('correction_exceeds_local_ulp_limit')
    if delta>Fraction(policy.correction_absolute_mol):
        raise DepletionRoundoffError('correction_absolute_budget')
    evaporated=_number(positive_evaporated_mol,'positive_evaporated')
    if evaporated<0:
        raise DepletionRoundoffError('negative_evaporated')
    if delta>Fraction(evaporated)*Fraction(policy.correction_fraction_evaporated):
        raise DepletionRoundoffError('correction_exceeds_evaporation_fraction')
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
    result=ConservedState(amounts,state.internal_energy_j)
    record=DepletionWritebackRecord(cell_index,liquid_index,vapor_index,liquid,vapor,after,
        -delta,delta,Fraction(after)-Fraction(vapor),residual,Fraction(liquid)-exact_liquid,
        local,evaporated,half)
    return result,record,updated_totals
