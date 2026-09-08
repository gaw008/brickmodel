"""Short native-water free trajectory; fixed phase inventories, not full firing."""
import json
import numpy as np
from sludge_sandbox.integration import integrate
from test_free_solid_cell import host
from test_integration import policy
from test_rigid_storage import water


def test_native_wet_free_trajectory_and_time_refinement(water):
    op=host(water)
    initial=op.state_from_temperature([[1.,.01,2.]],300.,normal_stretch=1.,tangential_stretch=1.)
    initial_volume=op.point.skeleton.reference_volume_m3
    outputs=[];metrics=[]
    for step in (.001,.0005):
        result=integrate(initial,op,start_s=0.,end_s=.001,
            policy=policy(initial_step_s=step,maximum_step_s=step,relative_tolerance=1e-7,
                stretch_absolute_tolerance=1e-9,stretch_scale=1.,energy_absolute_tolerance_j=1e-6,
                maximum_steps=4,maximum_rejections=4,maximum_wall_seconds=30.))
        print(json.dumps(dict(step_s=step,status=result.status,reason=result.reason,
            accepted=len(result.steps),rejected=result.rejected_trials,evaluations=result.evaluations,
            elapsed_s=result.elapsed_seconds)),flush=True)
        assert result.status=='completed',result.reason
        assert len(result.steps)==round(.001/step) and result.rejected_trials==0
        final=result.states[-1];point=op.evaluate(final,.001).inverse.state
        work_residual=float(final.internal_energy_j[0]-initial.internal_energy_j[0]+
            101325*(point.deformation.current.volumes_m3[0]-initial_volume))
        assert abs(work_residual)<2e-6
        assert all(np.array_equal(state.amounts_mol,initial.amounts_mol) for state in result.states)
        assert point.thermal_state.mechanical.temperature_k<300.
        assert point.free_rates.zero_balance_enclosed
        outputs.append((final,point))
        metrics.append(dict(step_s=step,accepted=len(result.steps),rejected=result.rejected_trials,
            elapsed_s=result.elapsed_seconds,temperature_k=point.thermal_state.mechanical.temperature_k,
            pressure_pa=point.thermal_state.mechanical.pressure_pa,stretches=final.mechanical_stretches.tolist(),
            external_work_residual_j=work_residual))
    assert np.max(np.abs(outputs[0][0].mechanical_stretches-outputs[1][0].mechanical_stretches))<2e-7
    assert abs(outputs[0][1].thermal_state.mechanical.temperature_k-outputs[1][1].thermal_state.mechanical.temperature_k)<2e-6
    print(json.dumps({'qualification':'short_manufactured_fixed_phase_wet_trajectory','runs':metrics}))
