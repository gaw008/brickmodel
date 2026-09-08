"""Preregistered actual water mixed-interface reduced slab numerical check.

Native execution is root-owned,600s integrate/660s entire child. Coefficients
and mechanics are manufactured; this is not material validation.
"""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import traceback
from typing import Any
import numpy as np
from sludge_sandbox.depletion_integration import integrate_depletion,NestedApproachPolicy
from sludge_sandbox.verification_case import encode
from test_depletion_integration import policies
from test_free_slab_phase_transfer import slab_transfer
from test_water_phase_transfer import ingredients


def _save(path: Path,payload: dict[str,Any]) -> None:
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)


def _snapshot(evaluation: Any) -> dict[str,Any]:
    base=evaluation.base_evaluation
    return {'rates':encode(evaluation.rates),'cell_transfers':encode(evaluation.cell_transfers),
        'geometry':encode(base.geometry),'free':encode(base.free),
        'thermal_inverses':encode(base.storage_inverses),'gas_states':encode(base.gas_states),
        'source_ids':evaluation.source_ids,'model_identity':encode(base.model_identity),
        'total_energy_j':[inv.state.total_energy_j for inv in base.total_inverses],
        'total_energy_error_j':[inv.state.energy_error_bound_j for inv in base.total_inverses],
        'temperature_error_k':[inv.temperature_error_bound_k for inv in base.total_inverses]}


def test_actual_two_cell_depletion_retains_wet_spectator_and_constraint_work(ingredients,tmp_path: Path) -> None:
    directory=os.environ.get('BRICK_FREE_SLAB_DEPLETION_ARTIFACT')
    path=Path(directory) if directory else tmp_path/'free-slab-depletion.json'
    if path.exists():raise RuntimeError('depletion_artifact_already_exists')
    payload: dict[str,Any]={'status':'started','qualification':'actual_water_manufactured_fixed_solid_reduced_slab_not_material_validation',
        'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    _save(path,payload)
    try:
        op=slab_transfer(ingredients)
        initial=op.base_model.state_from_temperatures([[1e-8,.01,1e-5,2.],[.5,.008,.001,2.]],
            [300.,301.],normal_stretches=(1.,1.),tangential_stretch=1.)
        p,e=policies()
        p=replace(p,initial_step_s=1e-4,maximum_step_s=1e-4,energy_absolute_tolerance_j=1e-6,
            stretch_absolute_tolerance=1e-9,stretch_scale=1.,maximum_steps=2000,maximum_wall_seconds=600.)
        e=replace(e,roundoff_policy=replace(e.roundoff_policy,molar_mass_kg_mol=op.chemical.reference.molar_mass_kg_mol),
            terminal_method='affine_midpoint',terminal_window_s=1e-6,common_time_horizon_s=1e-4,
            energy_absolute_j=2e-6,pressure_absolute_pa=.1,
            nested_approach=NestedApproachPolicy(maximum_step_s=1e-4,reuse_ordinary_spine=True))
        payload.update(initial=encode(initial),integration_policy=encode(p),event_policy=encode(e),
            operator_source_ids=op.source_ids,energy_model_identity=encode(op.base_model.energy_model_identity),
            water_source_assets=encode(op.chemical.source_asset_sha256))
        _save(path,payload)
        callback=op.evaluate(initial,0.)
        payload['initial_callback']=_snapshot(callback)
        _save(path,payload)
        first_rate=callback.cell_transfers[0].rate_mol_s
        free=callback.base_evaluation.free
        assert abs(free.constraint_power_sum_w)<=free.constraint_power_sum_error_w
        assert first_rate>0 and callback.cell_transfers[1].rate_mol_s<0
        assert 0.<1e-8/first_rate<1e-4
        out=integrate_depletion(initial,op,start_s=0.,end_s=1e-4,integration_policy=p,event_policy=e)
        payload['integration']={name:encode(getattr(out,name)) for name in ('status','reason','times_s','states',
            'steps','events','corrections','refinements','evaluations','rejected_trials','attempted_steps',
            'elapsed_seconds','roundoff_totals','phase_costs','reuse_counts')}
        payload['final_interfaces']=out.operator.interfaces
        _save(path,payload)
        assert out.status=='completed',out.reason
        assert len(out.steps)>0 and len(out.events)==1
        assert len(out.states)==len(out.times_s)==len(out.steps)+1 and out.times_s[-1]==1e-4
        assert out.events[0].cell_index==0 and out.operator.interfaces==('depleted_no_nucleation','existing_liquid')
        assert out.states[-1].amounts_mol[0,0]==0. and out.states[-1].amounts_mol[1,0]>0.
        event=out.events[0]
        assert event.stretch_difference is not None and event.stretch_difference<=p.stretch_absolute_tolerance
        assert event.terminal_panel.stretch_increment.shape==(3,)
        assert event.terminal_evidence.midpoint_state.mechanical_stretches.shape==(3,)
        passes=[r for r in out.refinements if r.status=='comparison_pass']
        independent=[r for r in out.refinements if r.status=='independent_approach_pass']
        assert len(passes)>=2 and passes[-1].level==passes[-2].level+1 and independent
        limits=(e.time_absolute_s,e.amount_absolute_mol,e.energy_absolute_j,e.temperature_absolute_k,
            e.pressure_absolute_pa,p.stretch_absolute_tolerance)
        for record in passes[-2:]+independent:
            assert len(record.differences)==6
            assert all(value<=limit for value,limit in zip(record.differences,limits,strict=True))
        for record in independent:
            assert record.comparison_details['approach_grid_a_s']!=record.comparison_details['approach_grid_b_s']
        increments=[F()]*3;exact=[F()]*3;roundoff=[F()]*3
        exchanges=[F()]*2;component_residual=[F()]*2
        constraint_abs=F();constraint_local_abs=[F(),F()]
        metrics={'max_water_mol':0.,'max_cell_ledger_j':0.,'max_global_external_work_j':0.}
        volumes=tuple(F(point.skeleton.reference_volume_m3) for point in op.base_model.point_storages)
        for step,state in zip(out.steps,out.states[1:],strict=True):
            assert state.energy_model_identity==initial.energy_model_identity
            assert state.mechanical_stretches.shape==(3,) and np.all(state.mechanical_stretches>0)
            assert set(step.cell_work_components_j)=={'external_traction','mechanical_constraint','body'}
            constraints=tuple(map(F,map(float,step.cell_work_components_j['mechanical_constraint'])))
            constraint_abs+=abs(sum(constraints,F()))
            assert constraint_abs<=F(p.energy_absolute_tolerance_j)
            for i,value in enumerate(constraints):constraint_local_abs[i]+=abs(value)
            for i in range(2):
                assert state.amounts_mol[i,1]==initial.amounts_mol[i,1] and state.amounts_mol[i,3]==2.
                water=sum((F(float(state.amounts_mol[i,j]))-F(float(initial.amounts_mol[i,j])) for j in (0,2)),F())
                assert abs(water)<=F(1e-11)
                metrics['max_water_mol']=max(metrics['max_water_mol'],float(abs(water)))
                exchanges[i]+=F(float(step.face_energy_j[i]))-F(float(step.face_energy_j[i+1]))+F(float(step.cell_work_j[i]))
                delta=F(float(state.internal_energy_j[i]))-F(float(initial.internal_energy_j[i]))
                assert abs(delta-exchanges[i])<=F(p.energy_absolute_tolerance_j)
                metrics['max_cell_ledger_j']=max(metrics['max_cell_ledger_j'],float(abs(delta-exchanges[i])))
                residual=sum((F(float(values[i])) for values in step.cell_work_components_j.values()),F())-F(float(step.cell_work_j[i]))
                component_residual[i]+=abs(residual)
                assert component_residual[i]<=F(p.energy_absolute_tolerance_j)
            for i in range(3):
                inc=F(float(step.stretch_increment[i]));q=step.stretch_quadrature_roundoff[i]
                increments[i]+=inc;exact[i]+=inc-q;roundoff[i]+=abs(q)
                change=F(float(state.mechanical_stretches[i]))-F(float(initial.mechanical_stretches[i]))
                assert abs(change-increments[i])<=F(p.stretch_absolute_tolerance)
                assert abs(change-exact[i])<=F(p.stretch_absolute_tolerance) and roundoff[i]<=F(p.stretch_absolute_tolerance)
            n0,n1,t=map(F,map(float,state.mechanical_stretches))
            dvolume=volumes[0]*(n0*t*t-1)+volumes[1]*(n1*t*t-1)
            global_delta=sum((F(float(u))-F(float(u0)) for u,u0 in zip(state.internal_energy_j,initial.internal_energy_j,strict=True)),F())
            external=global_delta+F(op.base_model.external_pressure_pa)*dvolume
            assert abs(external)<=F(4e-6)
            metrics['max_global_external_work_j']=max(metrics['max_global_external_work_j'],float(abs(external)))
        assert all(value>F(1e-10) for value in constraint_local_abs)
        metrics['cumulative_constraint_sum_abs_j']=float(constraint_abs)
        metrics['cumulative_local_constraint_abs_j']=list(map(float,constraint_local_abs))
        payload['audits']=metrics
        _save(path,payload)
        final=out.operator.evaluate(out.states[-1],1e-4)
        payload['final_callback']=_snapshot(final)
        _save(path,payload)
        free=final.base_evaluation.free
        assert abs(free.constraint_power_sum_w)<=free.constraint_power_sum_error_w
        payload['status']='passed'
        _save(path,payload)
    except BaseException as exc:
        payload.update(status='failed',exception_type=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc())
        _save(path,payload)
        raise
