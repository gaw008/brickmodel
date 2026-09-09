"""Actual manufactured failure diagnostics without a water backend."""
from fractions import Fraction as F
import pytest
from sludge_sandbox import depletion_integration as m
from test_depletion_ordered_packet import setup


def actual(module,*,ordered=True,start=.5):
    p,e,op,initial,calls=setup(gap=1e-9)
    e=module.DepletionPolicy(**{f:getattr(e,f) for f in ('time_absolute_s','amount_absolute_mol','energy_absolute_j','temperature_absolute_k','pressure_absolute_pa','terminal_window_s','maximum_refinements','roundoff_policy','common_time_horizon_s','safe_inventory_fraction','terminal_method')},
        nested_approach=module.NestedApproachPolicy(maximum_step_s=.001,reuse_ordinary_spine=False),
        ordered_event_policy='ordered_affine_packet_v1' if ordered else None)
    callback=op.evaluate_callback
    def evaluate(state,t,modes):
        v=callback(state,t,modes)
        return module.DepletionEvaluation(v.rates,v.evaporation_mol_s,v.temperatures_k,v.temperature_errors_k,v.pressures_pa,v.pressure_errors_pa)
    op=module.ManufacturedDepletionAdapter(evaluate_callback=evaluate,liquid_index=0,water_vapor_index=1,interfaces=op.interfaces,program_knots_s=(),source_ids=op.source_ids)
    return module.integrate_depletion(initial,op,start_s=start,end_s=start+.03,integration_policy=p,event_policy=e),calls


def frac(x):return F(x['numerator'],x['denominator'])


def test_real_fraction_failure_is_retained_without_callbacks_or_partial_commit():
    result,calls=actual(m)
    assert result.reason=='correction_exceeds_evaporation_fraction'
    assert result.status=='failed'
    assert result.events==result.packets==()
    d=result.refinements[-1].comparison_details['writeback_failure']
    assert d['reason']==result.reason
    assert len(d['previous_uncommitted_frames'])==1
    i=d['cell_index'];li=d['liquid_index']
    n=F(d['initial_state']['amounts_mol'][i][li]);terms=d['signed_liquid_terms_mol']
    raw=d['raw_state']['amounts_mol'][i][li]
    assert float(n+sum(map(F,terms),F()))==raw
    assert F(raw)>F(d['positive_evaporated_mol'])*F(d['roundoff_policy']['correction_fraction_evaporated'])
    assert F(d['positive_evaporated_mol'])<=frac(d['exact_positive_evaporated_mol'])
    assert d['root_order']['selected_cell']==i
    clock=d['clock'];h=F(clock['end_s'])-F(clock['start_s']);hm=F(clock['midpoint_s'])-F(clock['start_s'])
    start_obs=d['initial_observation'];mid_obs=d['midpoint_observation']
    assert clock['start_inventory_mol']==float(n)
    for key,obs in (('liquid_rates_start_mol_s',start_obs),('liquid_rates_mid_mol_s',mid_obs)):
        rr=obs['rates']
        assert tuple(clock[key])==(rr['face_species_mol_s'][i][li],-rr['face_species_mol_s'][i+1][li],rr['reaction_species_mol_s'][i][li])
    for term,a,b in zip(terms,clock['liquid_rates_start_mol_s'],clock['liquid_rates_mid_mol_s']):
        assert term==float(F(a)*h+(F(b)-F(a))*h*h/(2*hm))
    e0=F(start_obs['evaporation_mol_s'][i]);em=F(mid_obs['evaporation_mol_s'][i])
    assert e0==em>0  # This analytic fixture has a constant sink.
    assert frac(d['exact_positive_evaporated_mol'])==e0*h
    import math
    assert F(math.nextafter(d['positive_evaporated_mol'],math.inf))>e0*h
    exactroot=F(clock['start_s'])+n/e0
    assert F(clock['end_s'])<=exactroot<F(math.nextafter(clock['end_s'],math.inf))
    assert exactroot-F(clock['end_s'])<=F(clock['time_absolute_s'])
    fields=d['integrated_fields']
    for cell,row in enumerate(d['initial_state']['amounts_mol']):
        for species,value in enumerate(row):
            expected=F(value)+F(fields['face_species_mol'][cell][species])-F(fields['face_species_mol'][cell+1][species])+F(fields['reaction_species_mol'][cell][species])
            assert float(expected)==d['raw_state']['amounts_mol'][cell][species]
        expected=F(d['initial_state']['internal_energy_j'][cell])+F(fields['face_energy_j'][cell])-F(fields['face_energy_j'][cell+1])+F(fields['cell_work_j'][cell])
        assert float(expected)==d['raw_state']['internal_energy_j'][cell]
    for original,increment,current in zip(d['initial_state']['mechanical_stretches'],d['stretch_increment'],d['raw_state']['mechanical_stretches']):
        assert float(F(original)+F(increment))==current
    assert result.roundoff_totals.numerical_phase_correction_mol==0
    with pytest.raises(TypeError):d['cell_index']=9
    with pytest.raises(TypeError):d['raw_state']['amounts_mol'][i][li]=0.
    with pytest.raises(TypeError):d['previous_uncommitted_frames'][0]['event']['time_s']=0.


def test_default_refusal_keeps_empty_diagnostic_shape():
    result,_=actual(m,ordered=False)
    assert result.reason=='simultaneous_events_not_separated'
    assert result.refinements==()


def test_successful_packet_keeps_events_and_no_failure_diagnostics():
    result,_=actual(m,start=0.)
    assert result.status=='completed',result.reason
    assert len(result.events)==2 and len(result.packets)==1
    assert result.times_s[-1]==.03
    assert abs(result.events[0].time_s-.01)<1e-12
    assert abs(result.events[1].time_s-(.01+5e-10))<1e-12
    assert all('writeback_failure' not in ref.comparison_details for ref in result.refinements)
    assert any(ref.status=='independent_approach_pass' for ref in result.refinements)


def test_diagnostic_capture_error_cannot_replace_actual_physical_refusal(monkeypatch):
    def unavailable(value):raise TypeError('diagnostic sentinel')
    monkeypatch.setattr(m,'_snapshot_failure_diagnostic',unavailable)
    result,_=actual(m)
    assert result.reason=='correction_exceeds_evaporation_fraction'
    assert result.events==result.packets==()
    d=result.refinements[-1].comparison_details['writeback_failure']
    assert d['available'] is False and 'diagnostic sentinel' in d['capture_error']
