"""Complete shared-panel numerical affine root ordering, not a true RHS certificate."""
from dataclasses import dataclass,fields,is_dataclass
from fractions import Fraction as F
from collections.abc import Mapping
import hashlib,json
import numpy as np
from sludge_sandbox.integration import ConservedState,Rates,IntegrationError
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.exact_affine_depletion import ExactAffineSamples,ExactAffineEvidence
from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy,DepletionRoundoffError,_number
from sludge_sandbox.rational_polynomial import polynomial_gcd,refine_descending_bracket


class ExactRootOrderError(ValueError):
    def __init__(self,reason,*,diagnostic=None):
        super().__init__(reason)
        self.diagnostic=diagnostic


def _data(value):
    if isinstance(value,F):return [value.numerator,value.denominator]
    if isinstance(value,np.ndarray):return _data(value.tolist())
    if isinstance(value,np.generic):return _data(value.item())
    if is_dataclass(value):return {f.name:_data(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,Mapping):return {k:_data(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [_data(v) for v in value]
    if value is None or type(value) in (str,int,float,bool):return value
    raise ExactRootOrderError('unsupported_input_binding_type')


def _minimum(n,r,a,h):
    points=[F(),h]
    if a>0 and 0<-r/a<h:points.append(-r/a)
    return min(n+r*t+a*t*t/2 for t in points)


def _same_first_root(left,right,h):
    """Exact polynomial gcd; both inputs already strictly decreasing here."""
    a=polynomial_gcd(left,right)
    if len(a)==3:return True  # Proportional quadratics with the same domain root.
    if len(a)==2:return 0<-a[0]/a[1]<=h
    return False


@dataclass(frozen=True)
class RootCandidate:
    cell_index:int
    evidence:ExactAffineEvidence


@dataclass(frozen=True)
class NoRootEvidence:
    cell_index:int
    initial_mol:F
    rate_mol_s:F
    acceleration_mol_s2:F
    domain_duration_s:F
    minimum_mol:F


@dataclass(frozen=True)
class ExactRootOrder:
    selected_cell:int
    candidates:tuple[RootCandidate,...]
    exclusions:tuple[NoRootEvidence,...]
    wet_cells:tuple[int,...]
    input_sha256:str
    refinement_level:int
    qualification:str='complete_shared_numerical_affine_order_not_true_rhs_certificate'


def order_exact_affine_roots(state,first,midpoint_rates,*,start,midpoint,upper,liquid_index,
                             wet_cells,evaporation_start_mol_s,evaporation_mid_mol_s,
                             source_binding,time_absolute_s,policy,maximum_refinements=256):
    if type(state) is not ConservedState or type(first) is not Rates or type(midpoint_rates) is not Rates:
        raise ExactRootOrderError('explicit_state_and_shared_rates_required')
    if any(type(t) is not ExactEventTime for t in (start,midpoint,upper)) or not start<midpoint<upper:
        raise ExactRootOrderError('exact_shared_sample_times_required')
    cells,species=state.amounts_mol.shape
    if type(liquid_index) is not int or not 0<=liquid_index<species:
        raise ExactRootOrderError('liquid_index_required')
    expected=tuple(i for i in range(cells) if state.amounts_mol[i,liquid_index]>0)
    if type(wet_cells) is not tuple or any(type(i) is not int for i in wet_cells) or wet_cells!=expected:
        raise ExactRootOrderError('complete_ordered_positive_liquid_cells_required')
    if not expected:raise ExactRootOrderError('no_positive_liquid_inventory')
    if type(source_binding) is not tuple or not source_binding or any(type(x) is not str or not x or x.strip()!=x for x in source_binding) or len(set(source_binding))!=len(source_binding):
        raise ExactRootOrderError('explicit_unique_source_binding_required')
    if type(policy) is not DepletionRoundoffPolicy or type(maximum_refinements) is not int or not 1<=maximum_refinements<=256:
        raise ExactRootOrderError('explicit_policy_and_refinement_budget_required')
    time_absolute_s=_number(time_absolute_s,'time_absolute',positive=True)
    first.derivatives(state)
    for name in ('face_species_mol_s','face_energy_w','reaction_species_mol_s','cell_power_w'):
        if getattr(first,name).shape!=getattr(midpoint_rates,name).shape:
            raise ExactRootOrderError('shared_rate_shape_mismatch')
    if (first.mechanical_rates_per_s is None)!=(midpoint_rates.mechanical_rates_per_s is None):
        raise ExactRootOrderError('shared_mechanical_schema_mismatch')
    if first.mechanical_rates_per_s is not None and first.mechanical_rates_per_s.shape!=midpoint_rates.mechanical_rates_per_s.shape:
        raise ExactRootOrderError('shared_mechanical_shape_mismatch')
    if (None if first.cell_power_components_w is None else tuple(first.cell_power_components_w))!=(None if midpoint_rates.cell_power_components_w is None else tuple(midpoint_rates.cell_power_components_w)):
        raise ExactRootOrderError('shared_component_schema_mismatch')
    for values in (evaporation_start_mol_s,evaporation_mid_mol_s):
        if type(values) is not tuple or len(values)!=cells:
            raise ExactRootOrderError('full_evaporation_observations_required')
        for value in values:_number(value,'evaporation')
    binding=(state,first,midpoint_rates,start,midpoint,upper,liquid_index,wet_cells,
             evaporation_start_mol_s,evaporation_mid_mol_s,source_binding,time_absolute_s,policy,maximum_refinements)
    digest=hashlib.sha256(json.dumps(_data(binding),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    h=upper.elapsed_since(start);hm=midpoint.elapsed_since(start);samples={};excluded=[];polynomials={}
    for cell in wet_cells:
        def terms(obs):return (float(obs.face_species_mol_s[cell,liquid_index]),-float(obs.face_species_mol_s[cell+1,liquid_index]),float(obs.reaction_species_mol_s[cell,liquid_index]))
        left,right=terms(first),terms(midpoint_rates)
        n=F(float(state.amounts_mol[cell,liquid_index]));r=sum(map(F,left),F());a=(sum(map(F,right),F())-r)/hm
        minimum=_minimum(n,r,a,h)
        if minimum>0:
            excluded.append(NoRootEvidence(cell,n,r,a,h,minimum));continue
        try:
            samples[cell]=ExactAffineSamples(start,midpoint,upper,float(n),left,right,
                evaporation_start_mol_s[cell],evaporation_mid_mol_s[cell],source_binding)
        except DepletionRoundoffError as exc:
            raise ExactRootOrderError('unsupported_candidate:'+str(cell)+':'+str(exc)) from exc
        polynomials[cell]=(n,r,a/2)
    if not samples:raise ExactRootOrderError('no_roots_in_shared_domain',diagnostic=(digest,wet_cells,tuple(excluded),()))
    bounds={i:(F(),h) for i in samples}
    for level in range(1,maximum_refinements+1):
        for i,sample in samples.items():
            bounds[i]=refine_descending_bracket(polynomials[i],*bounds[i])
        ordered=sorted(bounds,key=lambda i:(bounds[i][0],i))
        first_cell=ordered[0]
        if all(bounds[first_cell][1]<bounds[i][0] for i in ordered[1:]):
            records=[]
            try:
                for i,sample in samples.items():
                    lo,hi=bounds[i]
                    records.append(RootCandidate(i,ExactAffineEvidence(sample,start.shifted(lo),start.shifted(hi),level,time_absolute_s,policy)))
            except DepletionRoundoffError as exc:
                if str(exc) not in ('invalid_adjacent_lower_root_enclosure','exact_clock_original_correction_budget'):raise
                continue
            return ExactRootOrder(first_cell,tuple(records),tuple(excluded),wet_cells,digest,level)
        coincident=tuple(i for i in ordered if _same_first_root(polynomials[first_cell],polynomials[i],h))
        if len(coincident)>1 and all(bounds[first_cell][1]<bounds[j][0] for j in ordered if j not in coincident):
            raise ExactRootOrderError('unsupported_exact_coincident_first_roots',
                diagnostic=(digest,wet_cells,tuple(excluded),tuple((i,samples[i],bounds[i]) for i in samples)))
    raise ExactRootOrderError('unsupported_root_order_refinement_budget',
        diagnostic=(digest,wet_cells,tuple(excluded),tuple((i,samples[i],bounds[i]) for i in samples)))


def _same_typed_record(actual,expected):
    """Exact record types matter: bool/int and Fraction/float are not aliases."""
    if type(actual) is not type(expected):return False
    if is_dataclass(expected):
        return all(_same_typed_record(getattr(actual,f.name),getattr(expected,f.name)) for f in fields(expected))
    if type(expected) is tuple:
        return len(actual)==len(expected) and all(_same_typed_record(a,b) for a,b in zip(actual,expected))
    if expected is None or type(expected) in (str,int,float,bool,F):return actual==expected
    return False


def verify_exact_root_order(record,*args,**kwargs):
    """Recompute pure input binding and all roots, never trust a public record."""
    if type(record) is not ExactRootOrder or not _same_typed_record(record,order_exact_affine_roots(*args,**kwargs)):
        raise ExactRootOrderError('root_order_input_or_evidence_mismatch')
