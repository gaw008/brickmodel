"""Named dry common endpoint must not create a one-ULP final panel."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState,Rates
import sludge_sandbox.depletion_integration as m
from test_depletion_integration import policies

def run(method='euler',second=False,cap=1e-4):
 p,e=policies();p=replace(p,initial_step_s=cap,maximum_step_s=cap,maximum_wall_seconds=5.,stretch_absolute_tolerance=1e-9,stretch_scale=1.)
 e=m.DepletionPolicy(**(vars(e)|{'terminal_method':method,'terminal_window_s':4e-5,'common_time_horizon_s':1e-4,'time_absolute_s':1e-10}))
 cells=2 if second else 1
 def callback(s,t,modes):
  sinks=[1. if mode=='existing_liquid' else 0. for mode in modes]
  return m.DepletionEvaluation(Rates(np.zeros((cells+1,2)),np.zeros(cells+1),[[-x,x] for x in sinks],np.ones(cells),mechanical_rates_per_s=np.ones(cells+1)*.1),tuple(sinks),(300.,)*cells,(0.,)*cells,(0.,)*cells,(0.,)*cells)
 op=m.ManufacturedDepletionAdapter(evaluate_callback=callback,liquid_index=0,water_vapor_index=1,interfaces=('existing_liquid',)*cells,program_knots_s=(),source_ids=('manufactured:clock-reproduction',))
 rows=[[3.041741714178811e-05,0.]]+([[.0002,0.]] if second else [])
 initial=ConservedState(rows,[1.]*cells,mechanical_stretches=[1.]*(cells+1))
 result=m.integrate_depletion(initial,op,start_s=0.,end_s=1e-4,integration_policy=p,event_policy=e)
 return result,p,e

@pytest.mark.parametrize('method,second,cap',[
    ('euler',False,1e-4),('affine_midpoint',False,1e-4),
    ('euler',True,1e-4),('euler',False,1e-5)])
def test_dry_common_endpoint_and_remaining_liquid_limits(method,second,cap):
    at=3.041741714178811e-05;end=1e-4
    assert at+(end-at)<end
    result,p,e=run(method,second,cap)
    assert result.status=='completed',result.reason
    assert len(result.events)==1 and result.times_s[-1]==end
    for step,state in zip(result.steps,result.states[1:],strict=True):
        # The cap is nominal binary duration; the original integrator uses
        # rounded absolute endpoints and integrates their full actual difference.
        assert F(step.end_s)<=F(float(F(step.start_s)+F(cap)))
        for energy in state.internal_energy_j:
            assert abs(F(float(energy))-F(1)-F(step.end_s))<F(1e-12)
        for stretch in state.mechanical_stretches:
            assert abs(F(float(stretch))-F(1)-F(.1)*F(step.end_s))<F(1e-9)
    if second:
        dry=[s for s in result.steps if s.start_s>=result.events[0].time_s]
        assert len(dry)>=2
        for step in dry:
            assert F(step.end_s)-F(step.start_s)<=F(e.safe_inventory_fraction)*(F(.0002)-F(step.start_s))
