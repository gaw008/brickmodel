"""Model diagnostics, not physical quality predictions."""
import math
from temperature import evaluate
from solver import conductance

NOT_MODELLED={k:{'status':'not_modelled','value':None} for k in (
    'energy','pressure','pore_closure','thermal_expansion_flow','equation_of_state',
    'shrinkage','strength','emissions','t_close','t_escape')}
ASSUMPTIONS=['prescribed_spatially_uniform_temperature','fixed_geometry_and_porosity',
             'fixed_c_star_not_constant_pressure_air','shared_equimolar_diffusion',
             'single_C_O2_CO2_reaction','synthetic_assumption','unknown_real_material',
             'u_core_is_first_cell_average','surface_is_half_cell_Robin_reconstruction']


def numerical_label(frozen,execution,audit,binding):
    if not frozen: return 'not_verified_for_custom_case'
    if audit is False or binding=='failed' or execution=='numerical_failure': return 'failed'
    if execution=='integrated' and audit is True and binding=='bound': return 'passed_frozen_suite'
    return 'not_run'


def event(times,values,remaining,upper):
    if values[0]<=remaining: return dict(tau=times[0],bracket_tau=[times[0],times[0]],status='initially_reached')
    for i in range(1,len(times)):
        if values[i]<=remaining:
            t=times[i-1]+(times[i]-times[i-1])*(values[i-1]-remaining)/(values[i-1]-values[i])
            return dict(tau=t,bracket_tau=[times[i-1],times[i]],status='reached_diagnostic_threshold')
    return dict(tau=None,bracket_tau=None,status='excluded_by_oxygen_budget' if upper is not None and upper<1-remaining else 'not_reached_by_horizon')


def row(s,t,state,*,test_only_dirichlet=False):
    d=s.to_dict(); c=evaluate(s,t); n=len(state.u); gamma=d['reaction']['Gamma']
    g=2*c.a_D*n if test_only_dirichlet else conductance(c.a_D,c.b,1/n); ue=state.u_res if state.u_res is not None else 1.
    ju=g*(state.u[-1]-ue)
    surf=state.u[-1] if c.b==0 else ue+ju/c.b
    if test_only_dirichlet: surf=1.
    return dict(scenario_id=s.id,tau=t,T_K=c.T_K,K_tau=c.K,d_tau=c.d,a_D=c.a_D,b=c.b,g=g,
                H=state.H,S_D=state.S_D,S_B=state.S_B,Da_O2=gamma*c.K/c.a_D,
                u_core=state.u[0],u_surface=surf,f_mean=sum(state.f)/n,f_max=max(state.f),
                co2_body=sum(state.v)/n,co2_generated=state.generated,co2_net_out=state.net_v,
                u_res=state.u_res,v_res=state.v_res,source_rate=sum(gamma*c.K*f*u for f,u in zip(state.f,state.u))/n)


def compute(s,raw):
    d=s.to_dict(); gamma=d['reaction']['Gamma']; mode=d['boundary']['mode']; rho=d['boundary']['reservoir_ratio']
    upper=None if mode=='infinite' else min(1.,(1+(rho or 0))/gamma)
    rows=[row(s,t,y,test_only_dirichlet=raw.test_only_dirichlet) for t,y in raw.records]; times=[r['tau'] for r in rows]
    events={}
    for name,field in [('mean','f_mean'),('local','f_max')]:
        for percent,remaining in ((95,.05),(99,.01)):
            events[f'{name}{percent}']=event(times,[r[field] for r in rows],remaining,upper)
    peak=max(r['source_rate'] for r in rows)
    return dict(scenario_id=s.id,input=d,execution_status=raw.execution_status,
                budget_status='not_applicable_infinite' if upper is None else ('oxygen_budget_limited' if upper<1 else 'sufficient_upper_bound'),
                conversion_upper_bound=upper,oxygen_budget_inequality=None if upper is None else {'Gamma':gamma,'available_O2':1+(rho or 0)},
                events=events,at_tau_10=next((r for r in rows if abs(r['tau']-10)<1e-12),None),at_end=rows[-1],
                tau_source_peak=next((r['tau'] for r in rows if r['source_rate']==peak),None) if peak else None,
                source_peak_status='sampled_peak' if peak else 'identically_zero',
                ideal_oxygen_f_lower_bound=math.exp(-rows[-1]['H']),
                assumptions=ASSUMPTIONS,not_modelled=NOT_MODELLED,physical_time_seconds=None,physical_time_status='uncalibrated',
                material_mapping='unknown_real_material',provenance='synthetic_assumption',
                units={'tau':'1','T_K':'K','inventory':'1','source_rate':'normalized_inventory_per_dimensionless_tau'},
                steps=raw.steps,rejected_steps=raw.rejected_steps,min_step=raw.min_step,max_step=raw.max_step,knot_times=raw.knot_times)
