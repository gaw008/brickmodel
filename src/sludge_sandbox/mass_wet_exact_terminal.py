"""Actual autonomous mixed samples to speculative exact terminal projection."""
from dataclasses import dataclass
from fractions import Fraction as F
import time
from sludge_sandbox.mass_storage_bridge import require
from sludge_sandbox.mass_wet_transport import WetPair, represented
from sludge_sandbox.mass_wet_exact_stage import (
    Sample, InventoryPolynomial, ExactMixedLedger, components,
    inventory_derivatives, initial_value, advance, make_ledger,
)
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_affine_depletion import ExactAffineSamples, ExactAffineEvidence
from sludge_sandbox.exact_root_order import RootCandidate, NoRootEvidence, _same_first_root
from sludge_sandbox.mass_wet_writeback import (
    MixedWritebackContext, MixedWritebackTotals, MixedCellPanelTerms,
    MixedTerminalEvidence, project_mixed_depletion,
)
from sludge_sandbox.depletion_roundoff import DepletionRoundoffError
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.integration import DomainExit


def source_labels(pair: WetPair) -> tuple:
    """Actual host's declared sources; not external registry authentication."""
    return tuple(dict.fromkeys((*pair.coefficient_source_ids,*pair.face.source_ids,
        *pair.chemical.source_ids,*(v for st in pair.storages for v in st.source_ids))))


@dataclass(frozen=True)
class MixedRootOrder:
    selected_cell: int
    candidates: tuple
    exclusions: tuple
    wet_cells: tuple
    source_binding: str
    levels: int


@dataclass(frozen=True)
class TerminalAttempt:
    status: str
    reason: str | None
    initial_state: tuple
    start: T
    upper: T
    samples: tuple
    predictor_state: tuple | None
    predictor_ledger: ExactMixedLedger | None
    root_order: MixedRootOrder | None
    root_search_evidence: tuple
    component_coefficients: tuple
    inventory_polynomials: tuple
    ledger: ExactMixedLedger | None
    raw_states: tuple | None
    panel_terms: tuple
    evidence: MixedTerminalEvidence | None
    projection: object | None
    evaluations_attempted: int
    evaluations_completed: int
    elapsed_seconds: float
    qualification: str = 'actual_autonomous_samples_speculative_projection_no_mode_switch_no_global_commit_no_event_comparison_or_resume'


def prepare_mixed_terminal(pair: WetPair, initial: tuple, *, start: T, upper: T,
        context: MixedWritebackContext, totals: MixedWritebackTotals,
        time_absolute_s: float, maximum_refinements: int=256,
        maximum_evaluations: int=2, maximum_wall_seconds: float=30., cancel=None) -> TerminalAttempt:
    """Generate actual shared samples and numerical terminal evidence, not an event commit."""
    require(type(pair) is WetPair and type(start) is T and type(upper) is T and start<upper,'typed_terminal_interval')
    require(type(initial) is tuple and len(initial)==2,'complete_actual_initial_state')
    require(type(context) is MixedWritebackContext and type(totals) is MixedWritebackTotals,'original_terminal_context_totals')
    require(type(time_absolute_s) is float and 0<time_absolute_s<float('inf'),'original_positive_time_budget')
    require(type(maximum_refinements) is int and 1<=maximum_refinements<=256,'bounded_root_refinements')
    require(type(maximum_evaluations) is int and maximum_evaluations>=0,'bounded_evaluations')
    require(type(maximum_wall_seconds) is float and 0<maximum_wall_seconds<float('inf'),'bounded_wall')
    begun=time.monotonic();attempted=completed=0;samples=[];predictor=None;predictor_ledger=None;order=None
    search=[];coeff=();polynomials=();ledger=None;raw=None;panel_terms=();evidence=None;projection=None
    binding=pair.binding();modes=pair.interfaces;labels=source_labels(pair)
    context_binding=_digest(context);totals_binding=_digest(totals)

    def guard():
        require(_digest(context)==context_binding and _digest(totals)==totals_binding,'original_terminal_context_or_totals_changed')
        require(pair.binding()==binding and pair.interfaces==modes and source_labels(pair)==labels,'terminal_source_or_modes_changed')
        if cancel is not None and cancel():raise InterruptedError('cancel_requested')
        if time.monotonic()-begun>maximum_wall_seconds:raise TimeoutError('terminal_wall_budget')

    def observe(states,at,role):
        nonlocal attempted,completed
        guard()
        if attempted>=maximum_evaluations:raise TimeoutError('terminal_evaluation_budget')
        attempted+=1;rates=pair.evaluate(states);completed+=1
        sample=Sample(role,at,states,rates,binding,modes);samples.append(sample);guard()
        return sample

    status='prepared';reason=None
    try:
        context.__post_init__();totals.__post_init__()
        require(binding==pair._identity,'actual_host_initial_binding_changed')
        require(context==totals.context and context.operator_identity==binding and context.source_ids==labels,'actual_original_context_binding')
        require(start>=context.original_time and len(initial)==len(context.original_states)==2,'original_interval_and_cell_count')
        for old,current,st in zip(context.original_states,initial,pair.storages):
            st.check(current)
            require(old.energy_model_identity==current.energy_model_identity,'original_energy_model_binding')
            require(context.water_molar_mass_kg_mol==st.water.reference.molar_mass_kg_mol,'roundoff_water_molar_mass_mismatch')
        first=observe(initial,start,'terminal_start')
        horizon=upper.elapsed_since(start)
        tangents=[F(s.liquid_water_mol)/F(c.phase_water_mol_s)
            for s,c,mode in zip(initial,first.rates.cells,modes)
            if mode=='existing_liquid' and c.phase_water_mol_s>0]
        require(bool(tangents),'unsupported_no_positive_initial_evaporation_tangent')
        hm=min(horizon,*tangents)/2;midpoint=start.shifted(hm)
        require(hm>0,'positive_exact_midpoint')
        predictor_ledger=make_ledger(start,midpoint,first.rates)
        predictor=advance(pair,initial,predictor_ledger)
        middle=observe(predictor,midpoint,'terminal_midpoint')
        a,b=components(first.rates),components(middle.rates)
        require(tuple(k for k,v in a)==tuple(k for k,v in b),'actual_shared_component_schema')
        coeff=tuple((k,r,(q-r)/hm) for (k,r),(_,q) in zip(a,b))
        da,db=inventory_derivatives(a),inventory_derivatives(b)
        polynomials=tuple(InventoryPolynomial(*k,initial_value(initial,k),r,(q-r)/(2*hm)) for (k,r),(_,q) in zip(da,db))
        wet=tuple(i for i,mode in enumerate(modes) if mode=='existing_liquid')
        candidate_samples={};excluded=[];liquid_polynomials={}
        for i in wet:
            p=next(p for p in polynomials if p.family=='liquid' and p.cell==i)
            minimum=p.minimum(horizon)[0]
            if minimum>0:
                excluded.append(NoRootEvidence(i,p.initial,p.linear,2*p.quadratic,horizon,minimum));continue
            c0,c1=first.rates.cells[i],middle.rates.cells[i]
            candidate_samples[i]=ExactAffineSamples(start,midpoint,upper,initial[i].liquid_water_mol,
                (0.,0.,-c0.phase_water_mol_s),(0.,0.,-c1.phase_water_mol_s),
                c0.phase_water_mol_s,c1.phase_water_mol_s,labels)
            liquid_polynomials[i]=(p.initial,p.linear,p.quadratic)
        search.append(('shared_domain',tuple(candidate_samples.items()),tuple(excluded)))
        require(bool(candidate_samples),'no_numerical_roots_in_shared_domain')
        bounds={i:(F(),horizon) for i in candidate_samples}
        for level in range(1,maximum_refinements+1):
            guard()
            for i,sample in candidate_samples.items():
                lo,hi=bounds[i];m=(lo+hi)/2
                bounds[i]=(m,hi) if sample.inventory(m)>=0 else (lo,m)
            search.append((level,tuple((i,candidate_samples[i],*bounds[i]) for i in candidate_samples),tuple(excluded)))
            sorted_cells=sorted(bounds,key=lambda i:(bounds[i][0],i));selected=sorted_cells[0]
            coincident=tuple(i for i in sorted_cells if _same_first_root(liquid_polynomials[selected],liquid_polynomials[i],horizon))
            if len(coincident)>1 and all(bounds[selected][1]<bounds[i][0] for i in sorted_cells if i not in coincident):
                raise ValueError('unsupported_exact_coincident_first_roots')
            if not all(bounds[selected][1]<bounds[i][0] for i in sorted_cells[1:]):continue
            records=[]
            try:
                for i,sample in candidate_samples.items():
                    lo,hi=bounds[i]
                    records.append(RootCandidate(i,ExactAffineEvidence(sample,start.shifted(lo),start.shifted(hi),level,time_absolute_s,context.policy)))
            except DepletionRoundoffError as exc:
                if str(exc) in ('invalid_adjacent_lower_root_enclosure','exact_clock_original_correction_budget'):continue
                raise
            order=MixedRootOrder(selected,tuple(records),tuple(excluded),wet,
                _digest((initial,start,midpoint,upper,a,b,binding,modes,labels,time_absolute_s,context.policy)),level)
            break
        require(order is not None,'unsupported_root_order_refinement_budget')
        selected=order.selected_cell;clock=next(r.evidence for r in order.candidates if r.cell_index==selected)
        end=clock.lower;h=end.elapsed_since(start)
        for p in polynomials:
            minimum=p.minimum(h)[0]
            if p.family=='liquid' and modes[p.cell]=='depleted_no_nucleation':require(p.initial==p.linear==p.quadratic==0,'dry_liquid_not_identically_zero')
            elif p.family=='liquid' and p.cell!=selected:require(minimum>0,'other_wet_cell_not_strictly_positive')
            else:require(minimum>=0,'terminal_full_panel_negative_inventory')
        integrals=tuple((k,r*h+slope*h*h/2) for k,r,slope in coeff)
        values=tuple((k,represented(v)) for k,v in integrals)
        ledger=ExactMixedLedger(start,end,integrals,values,tuple((k,F(w)-v) for (k,v),(_,w) in zip(integrals,values)))
        raw=advance(pair,initial,ledger);d=dict(values);panels=[]
        for i,sign in enumerate((-1,1)):
            panels.append(MixedCellPanelTerms(tuple((d['solid',i,j],) for j in range(2)),
                (0.,0.,-d['phase_water',i]),
                tuple((d['chemical_gas',i,j],sign*d['face_species',j],d['phase_water',i] if j==2 else 0.) for j in range(3)),
                (sign*d['face_energy',],)))
        panel_terms=tuple(panels)
        evidence=MixedTerminalEvidence(selected,initial,raw,panel_terms,tuple('wet' if m=='existing_liquid' else 'dry' for m in modes),binding,labels,clock)
        guard();projection=project_mixed_depletion(evidence,context=context,totals=totals);guard()
    except DomainExit as exc:status='domain_exit';reason=str(exc)
    except InterruptedError as exc:status='cancelled';reason=str(exc)
    except TimeoutError as exc:status='resource_limit';reason=str(exc)
    except (ValueError,OverflowError) as exc:status='failed';reason=str(exc)
    if status!='prepared':projection=None
    return TerminalAttempt(status,reason,initial,start,upper,tuple(samples),predictor,predictor_ledger,order,tuple(search),coeff,polynomials,ledger,raw,panel_terms,evidence,projection,attempted,completed,time.monotonic()-begun)
