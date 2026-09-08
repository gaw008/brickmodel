"""Actual water, manufactured two-cell compatible mechanics, fixed phases."""
from dataclasses import replace
from fractions import Fraction as F
import json
import os
from pathlib import Path
import numpy as np
from sludge_sandbox.integration import integrate
from sludge_sandbox.verification_case import encode
from sludge_sandbox.checkpoint import audit_integration
from test_free_solid_slab import host
from test_deforming_solid_storage import exact_volume_wet_model
from test_rigid_storage import water
from test_integration import policy


def wet_host(water):
    base=host(water);exact=exact_volume_wet_model(water)
    points=tuple(replace(p,template=exact.template,
        skeleton=replace(p.skeleton,solid_provider_identity=exact.skeleton.solid_provider_identity))
        for p in base.point_storages)
    transport=replace(base.base_model.transport,storages=tuple(p.template.fluid_template for p in points))
    thermal=replace(base.base_model,storages=tuple(p.template for p in points),transport=transport)
    return replace(base,base_model=thermal,point_storages=points,external_pressure_pa=101325.)


def test_actual_wet_two_cell_free_trajectory_and_refinement(water):
    op=wet_host(water)
    initial=op.state_from_temperatures([[1.,.01,2.],[.5,.008,2.]],[300.,301.],
                                      normal_stretches=(1.,1.),tangential_stretch=1.)
    outputs=[];decoded=[];max_work=0.;payload=[]
    for cap in (1e-4,5e-5):
        numerical=policy(initial_step_s=cap,maximum_step_s=cap,relative_tolerance=1e-7,
            amount_absolute_tolerance_mol=1e-11,energy_absolute_tolerance_j=1e-6,
            stretch_absolute_tolerance=1e-9,stretch_scale=1.,maximum_steps=4,
            maximum_rejections=4,maximum_wall_seconds=60.)
        out=integrate(initial,op,start_s=0.,end_s=1e-4,policy=numerical)
        payload.append({'policy':encode(numerical),'result':encode(out)})
        artifact=os.environ.get('BRICK_FREE_SLAB_WET_ARTIFACT')
        if artifact:Path(artifact).write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
        assert out.status=='completed',out.reason
        constraint_abs=F()
        for state,ledger in zip(out.states[1:],out.steps,strict=True):
            assert np.array_equal(state.amounts_mol,initial.amounts_mol)
            n0,n1,t=map(float,state.mechanical_stretches)
            delta=sum((F(float(a))-F(float(b)) for a,b in zip(state.internal_energy_j,initial.internal_energy_j,strict=True)),F())
            volume=F(.00014)*((F(n0)+F(n1))*F(t)**2-2)
            residual=abs(delta+F(101325.)*volume)
            assert residual<F(4e-6)
            max_work=max(max_work,float(residual))
            constraint_abs+=abs(sum(map(F,map(float,ledger.cell_work_components_j['mechanical_constraint'])),F()))
            assert constraint_abs<=F(1e-6)
        audit_integration(encode(out),numerical,start_s=0.,end_s=1e-4)
        final=op.evaluate(out.states[-1],1e-4)
        assert final.free.zero_balance_enclosed
        for inverse,state in zip(final.total_inverses,final.storage_states,strict=True):
            assert inverse.thermal_inverse.state is state
        outputs.append(out);decoded.append(final)
    coarse,fine=outputs
    assert np.max(np.abs(coarse.states[-1].mechanical_stretches-fine.states[-1].mechanical_stretches))<2e-7
    assert np.max(np.abs(coarse.states[-1].internal_energy_j-fine.states[-1].internal_energy_j))<2e-6
    temperatures=[[s.mechanical.temperature_k for s in d.storage_states] for d in decoded]
    assert np.max(np.abs(np.array(temperatures[0])-temperatures[1]))<2e-6
    assert max(abs(t-start) for t,start in zip(temperatures[-1],(300.,301.),strict=True))>1e-8
    print(json.dumps(dict(qualification='real_water_manufactured_two_cell_fixed_phase_short_trajectory',
        accepted=[len(o.steps) for o in outputs],rejected=[o.rejected_trials for o in outputs],
        evaluations=[o.evaluations for o in outputs],elapsed_s=[o.elapsed_seconds for o in outputs],
        temperatures_k=temperatures,stretches=[o.states[-1].mechanical_stretches.tolist() for o in outputs],
        maximum_prefix_external_work_residual_j=max_work)))
