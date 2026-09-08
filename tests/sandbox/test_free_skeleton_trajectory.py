"""Manufactured mechanics trajectory oracle; no thermal EOS or material admission."""
import math
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from sludge_sandbox.integration import ConservedState,Rates,integrate
from sludge_sandbox.free_skeleton_rates import solve_free_rates
from test_free_skeleton_rates import model
from test_integration import policy


@pytest.mark.parametrize('external',[0.,100.])
def test_free_traction_trajectory_and_external_work_against_independent_ode(external):
    sk=model()
    v=sk.reference_volume_m3
    def independent(_,y):
        n,t=y[:2];theta=math.log(n)+2*math.log(t)
        pn=(1000*theta+800*(math.log(n)-theta/3))/n
        pt=(1000*theta+800*(math.log(t)-theta/3))/t+.5*.003*t/v
        nd=n*n*(-external*t*t-pn)/1000
        td=t*t*(-external*n*t-pt)/1000
        return [nd,td,-external*v*(t*t*nd+2*n*t*td)]
    reference=solve_ivp(independent,(0.,.1),[1.1,.9,1.],method='DOP853',
                        rtol=1e-12,atol=1e-14)
    assert reference.success
    def operator(state,time):
        n,t=state.mechanical_stretches
        out=solve_free_rates(sk,normal_stretch=float(n),tangential_stretch=float(t),
            pore_pressure_pa=0.,external_pressure_pa=external,solid_inventory_mol={'solid':2.})
        assert out.zero_balance_enclosed
        return Rates([[0.],[0.]],[0.,0.],[[0.]],[out.external_power_w],
                     mechanical_rates_per_s=out.rates)
    initial=ConservedState([[2.]],[1.],('manufactured-free-trajectory','v1'),
                           mechanical_stretches=[1.1,.9])
    result=integrate(initial,operator,start_s=0.,end_s=.1,
        policy=policy(initial_step_s=.05,maximum_step_s=.05,
          stretch_absolute_tolerance=1e-9,stretch_scale=1.,relative_tolerance=1e-8))
    assert result.status=='completed',result.reason
    final=result.states[-1]
    assert np.max(np.abs(final.mechanical_stretches-reference.y[:2,-1]))<2e-7
    assert abs(final.internal_energy_j[0]-reference.y[2,-1])<2e-8
    n,t=final.mechanical_stretches
    volume_change=v*(n*t*t-1.1*.9*.9)
    assert abs(final.internal_energy_j[0]-1.+external*volume_change)<2e-8
    if external==0.:
        assert all(s.internal_energy_j[0]==1. for s in result.states)
        # Recoverable energy falls while total stays fixed: no extra heat source.
        def recoverable(state):
            n,t=state.mechanical_stretches
            theta=math.log(n)+2*math.log(t)
            dev=(math.log(n)-theta/3,math.log(t)-theta/3)
            return v*(500*theta**2+400*(dev[0]**2+2*dev[1]**2))+.0015*t*t
        assert recoverable(final)<recoverable(initial)
