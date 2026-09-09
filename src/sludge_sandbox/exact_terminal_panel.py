"""Full-state numerical affine quadrature; no event acceptance or mode change."""
from dataclasses import dataclass
from fractions import Fraction as F
import math
import numpy as np
from sludge_sandbox.integration import ConservedState, Rates, IntegrationPolicy, IntegrationError
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.exact_integration import ExactStepLedger


@dataclass(frozen=True)
class ExactAffinePanel:
    raw_state: ConservedState
    ledger: ExactStepLedger
    source_binding: tuple[str, ...]
    qualification: str = 'caller_bound_affine_samples_not_true_rhs_or_event_acceptance'


def minimum(n: F, r: F, a: F, h: F) -> F:
    points=[F(),h]
    if a>0 and 0 < -r/a < h:
        points.append(-r/a)
    return min(n+r*x+a*x*x/2 for x in points)


def rounded(value: F) -> float:
    try:
        result=float(value)
    except OverflowError as exc:
        raise IntegrationError('affine_unrepresentable_integral') from exc
    if not math.isfinite(result) or (value and result==0):
        raise IntegrationError('affine_unrepresentable_integral')
    return result


def build_exact_affine_panel(state: ConservedState, first: Rates, midpoint_rates: Rates, *,
        start: ExactEventTime, midpoint: ExactEventTime, end: ExactEventTime,
        policy: IntegrationPolicy, liquid_index: int, selected_cell: int,
        wet_cells: tuple[int,...], source_binding: tuple[str,...]) -> ExactAffinePanel:
    if type(state) is not ConservedState or type(first) is not Rates or type(midpoint_rates) is not Rates or type(policy) is not IntegrationPolicy:
        raise IntegrationError('explicit_affine_state_rates_policy_required')
    if any(type(v) is not ExactEventTime for v in (start,midpoint,end)) or not start<midpoint<end:
        raise IntegrationError('exact_ordered_affine_times_required')
    if type(source_binding) is not tuple or not source_binding or any(type(v) is not str or not v or v.strip()!=v for v in source_binding):
        raise IntegrationError('explicit_caller_source_binding_required')
    cells,species=state.amounts_mol.shape
    if type(liquid_index) is not int or not 0<=liquid_index<species or type(selected_cell) is not int or not 0<=selected_cell<cells:
        raise IntegrationError('invalid_affine_phase_indices')
    if type(wet_cells) is not tuple or any(type(v) is not int or not 0<=v<cells for v in wet_cells) or len(set(wet_cells))!=len(wet_cells) or selected_cell not in wet_cells:
        raise IntegrationError('complete_explicit_wet_cells_required')
    if set(wet_cells)!={i for i in range(cells) if state.amounts_mol[i,liquid_index]>0}:
        raise IntegrationError('complete_positive_liquid_cells_required')
    if any(state.amounts_mol[i,liquid_index]<=0 for i in wet_cells):
        raise IntegrationError('wet_cell_requires_positive_start')
    first.derivatives(state)
    names=('face_species_mol_s','face_energy_w','reaction_species_mol_s','cell_power_w')
    for name in names:
        if getattr(midpoint_rates,name).shape!=getattr(first,name).shape:
            raise IntegrationError('affine_rate_shape_mismatch')
    mechanical=state.mechanical_stretches is not None
    if (midpoint_rates.mechanical_rates_per_s is not None)!=mechanical or (mechanical and midpoint_rates.mechanical_rates_per_s.shape!=state.mechanical_stretches.shape):
        raise IntegrationError('affine_mechanical_rate_shape')
    if mechanical and policy.stretch_absolute_tolerance is None:
        raise IntegrationError('explicit_stretch_scales_required')
    parts0,parts1=first.cell_power_components_w,midpoint_rates.cell_power_components_w
    if (parts0 is None)!=(parts1 is None) or (parts0 is not None and set(parts0)!=set(parts1)):
        raise IntegrationError('affine_component_schema_changed')
    h=end.elapsed_since(start);hm=midpoint.elapsed_since(start)
    def integral(a,b):
        exact=tuple(F(float(x))*h+(F(float(y))-F(float(x)))*h*h/(2*hm) for x,y in zip(a.flat,b.flat))
        return np.array([rounded(v) for v in exact]).reshape(a.shape),exact
    fields=[integral(getattr(first,name),getattr(midpoint_rates,name))[0] for name in names]
    fn,fu,rn,work=fields
    for i,j in np.ndindex(state.amounts_mol.shape):
        def net(r):return F(float(r.face_species_mol_s[i,j]))-F(float(r.face_species_mol_s[i+1,j]))+F(float(r.reaction_species_mol_s[i,j]))
        r=net(first);a=(net(midpoint_rates)-r)/hm
        value=minimum(F(float(state.amounts_mol[i,j])),r,a,h)
        strict=j==liquid_index and i in wet_cells and i!=selected_cell
        if value<0 or (strict and value==0):
            raise IntegrationError('affine_inventory_polynomial_not_admissible')
    def update(before, terms, tolerance):
        out=np.empty_like(before)
        for idx in np.ndindex(before.shape):
            delta=sum((F(float(t[idx])) for t in terms),F())
            value=F(float(before[idx]))+delta
            out[idx]=rounded(value) if value else 0.
            if abs(F(float(out[idx]))-value)>F(tolerance):
                raise IntegrationError('affine_state_roundoff_budget')
        return out
    amounts=update(state.amounts_mol,(fn[:-1],-fn[1:],rn),policy.amount_absolute_tolerance_mol)
    energy=update(state.internal_energy_j,(fu[:-1],-fu[1:],work),policy.energy_absolute_tolerance_j)
    stretch=None;increment=None;roundoff=None
    if mechanical:
        for n,r,m in zip(state.mechanical_stretches,first.mechanical_rates_per_s,midpoint_rates.mechanical_rates_per_s):
            if minimum(F(float(n)),F(float(r)),(F(float(m))-F(float(r)))/hm,h)<=0:
                raise IntegrationError('affine_stretch_polynomial_not_positive')
        increment,exact=integral(first.mechanical_rates_per_s,midpoint_rates.mechanical_rates_per_s)
        stretch=update(state.mechanical_stretches,(increment,),policy.stretch_absolute_tolerance)
        roundoff=tuple(F(float(v))-x for v,x in zip(increment,exact))
        if any(abs(F(float(v))-F(float(n))-x)>F(policy.stretch_absolute_tolerance) or abs(e)>F(policy.stretch_absolute_tolerance) for v,n,x,e in zip(stretch,state.mechanical_stretches,exact,roundoff)):
            raise IntegrationError('affine_stretch_quadrature_budget')
    components=None;component_roundoff=None
    if parts0 is not None:
        components={};component_roundoff={}
        for key in parts0:
            values,exact=integral(parts0[key],parts1[key]);components[key]=values
            component_roundoff[key]=tuple(F(float(v))-x for v,x in zip(values,exact))
    raw=ConservedState(amounts,energy,state.energy_model_identity,mechanical_stretches=stretch)
    ledger=ExactStepLedger(start,end,*fields,components,component_roundoff,stretch_increment=increment,stretch_quadrature_roundoff=roundoff)
    if ledger.component_sum_residual_j is not None and any(abs(v)>F(policy.energy_absolute_tolerance_j) for v in ledger.component_sum_residual_j):
        raise IntegrationError('affine_component_sum_budget')
    return ExactAffinePanel(raw,ledger,source_binding)
