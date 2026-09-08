"""Real water depletion with manufactured free mechanics; preregistered short case."""
from dataclasses import replace
from fractions import Fraction as F
import json
import os
from pathlib import Path
import numpy as np
from sludge_sandbox.depletion_integration import integrate_depletion, NestedApproachPolicy
from sludge_sandbox.verification_case import encode
from test_depletion_integration import policies
from test_free_water_phase_transfer import free_transfer
from test_water_phase_transfer import ingredients


def test_actual_free_water_depletion_preserves_every_mechanical_and_energy_prefix(ingredients):
    op=free_transfer(ingredients)
    initial=op.base_model.state_from_temperature([[1e-8,.01,1e-5,2.]],300.,
                                               normal_stretch=1.,tangential_stretch=1.)
    p,e=policies()
    p=replace(p,initial_step_s=1e-4,maximum_step_s=1e-4,energy_absolute_tolerance_j=1e-6,
        stretch_absolute_tolerance=1e-9,stretch_scale=1.,maximum_steps=2000,maximum_wall_seconds=120.)
    e=replace(e,terminal_method='affine_midpoint',terminal_window_s=1e-6,
        common_time_horizon_s=1e-4,energy_absolute_j=2e-6,pressure_absolute_pa=.1,
        nested_approach=NestedApproachPolicy(maximum_step_s=1e-4,reuse_ordinary_spine=True))
    out=integrate_depletion(initial,op,start_s=0.,end_s=1e-4,integration_policy=p,event_policy=e)
    payload={name:encode(getattr(out,name)) for name in ('status','reason','times_s','states',
        'steps','events','corrections','refinements','evaluations','rejected_trials','attempted_steps',
        'elapsed_seconds','roundoff_totals','phase_costs','reuse_counts')}
    payload['qualification']='actual_water_manufactured_free_skeleton_short_depletion_not_material_validation'
    payload['integration_policy']=encode(p);payload['event_policy']=encode(e)
    artifact=os.environ.get('BRICK_FREE_DEPLETION_ARTIFACT')
    if artifact:Path(artifact).write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    assert out.status=='completed',out.reason
    assert len(out.events)==1 and out.times_s[-1]==1e-4
    assert out.operator.interfaces==('depleted_no_nucleation',)
    assert out.states[-1].amounts_mol[0,0]==0.
    assert out.events[0].stretch_difference is not None
    assert out.events[0].terminal_panel.stretch_increment is not None
    passed=[r for r in out.refinements if r.status=='comparison_pass']
    assert passed and len(passed[-1].differences)==6
    increments=[F(),F()];exact=[F(),F()];roundoff=[F(),F()];work=F()
    volume=op.base_model.point.skeleton.reference_volume_m3
    max_work=max_water=0.
    for step,state in zip(out.steps,out.states[1:],strict=True):
        assert state.energy_model_identity==initial.energy_model_identity
        assert np.all(state.mechanical_stretches>0)
        assert state.amounts_mol[0,1]==.01 and state.amounts_mol[0,3]==2.
        water=abs(F(float(state.amounts_mol[0,0]))+F(float(state.amounts_mol[0,2]))-F(1e-8)-F(1e-5))
        assert water<=F(1e-11)
        max_water=max(max_water,float(water))
        for i in range(2):
            inc=F(float(step.stretch_increment[i]));q=step.stretch_quadrature_roundoff[i]
            increments[i]+=inc;exact[i]+=inc-q;roundoff[i]+=abs(q)
            change=F(float(state.mechanical_stretches[i]))-F(1.)
            assert abs(change-increments[i])<=F(1e-9)
            assert abs(change-exact[i])<=F(1e-9) and roundoff[i]<=F(1e-9)
        assert set(step.cell_work_components_j)=={'external_traction','body'}
        work+=F(float(step.cell_work_j[0]))
        delta=F(float(state.internal_energy_j[0]))-F(float(initial.internal_energy_j[0]))
        assert abs(delta-work)<=F(1e-6)
        n,t=map(float,state.mechanical_stretches)
        independent_work=float(delta)+101325.*volume*(n*t*t-1.)
        assert abs(independent_work)<=2e-6
        max_work=max(max_work,abs(independent_work))
    final=out.operator.base_model.evaluate(out.states[-1],1e-4).inverse.state
    print(json.dumps(dict(status=out.status,event_time_s=out.events[0].time_s,
        elapsed_s=out.elapsed_seconds,evaluations=out.evaluations,steps=len(out.steps),
        temperature_k=final.thermal_state.mechanical.temperature_k,
        pressure_pa=final.thermal_state.mechanical.pressure_pa,
        stretches=out.states[-1].mechanical_stretches.tolist(),
        max_prefix_external_work_residual_j=max_work,max_water_residual_mol=max_water)))
