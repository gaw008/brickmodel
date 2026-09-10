"""Actual source-host wet/dry execution with explicitly manufactured water."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest

from test_source_wet_column import setup
from test_source_prefix_trial import POLICY
from test_depletion_integration import policies
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
from sludge_sandbox.source_approach import propose_source_approach,evaluate_source_approach
from sludge_sandbox.source_root_comparison import evaluate_source_root_refinement
from sludge_sandbox.source_terminal import build_source_terminal
from sludge_sandbox.source_dry_transition import (execute_source_dry_candidate,
    evaluate_source_dry_transition,SourceDryTransitionError)
from sludge_sandbox.integration import DomainExit
from sludge_sandbox.boundary_program import BoundaryProgram,ProgramIdentity
from sludge_sandbox.exact_boundary_program import ExactProgramView
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.programmed_source_wet_column import ProgrammedSourceWetColumn


def prepare(patch,base=None):
    programmed=base is not None
    if programmed:
        program=BoundaryProgram(identity=ProgramIdentity(program_id='source-dry-test',version='1',
            classification='virtual_design_choice',source_ids=('design:source-dry-test-furnace',)),
            knot_times_s=(0.,.0002,.001),gas_temperature_k=(340.,)*3,
            radiation_temperature_k=(340.,)*3,total_pressure_pa=(1e5,)*3,
            species_order=base.gas_ids,mole_fractions=((.25,.6875,.0625),)*3)
        model=ProgrammedSourceWetColumn(base,ExactProgramView(program,F()),
            outer_conductivity_w_m_k=.5,convection_w_m2_k=10.,emissivity=0.,
            stefan_boltzmann_w_m2_k4=5.670374419e-8,gas_diffusivities_m2_s=(0.,)*3,
            gas_permeability_m2=0.,gas_viscosity_pa_s=1.8e-5,
            coefficient_source_ids=('manufactured:source-dry-test-coefficients',),
            surface_policy=SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=100))
    else:
        model,_=setup(patch,count=1)
    storage=model.storages[0]
    state=storage.state(1e-11,(.125,.25,1e-12),0.)
    state=replace(state,internal_energy_j=storage.evaluate(state,325.).total_internal_energy_j)
    adapter=ExactSourceColumn(model); initial=adapter.pack((state,))
    phase=adapter.evaluate(initial,T(F())).source_evaluation.cells[0].phase.phase_water_mol_s
    assert phase>0
    horizon=F(3,2)*F(state.liquid_water_mol)/F(phase)
    assert 0<horizon<F(.0002)
    numerical=replace(POLICY,initial_step_s=float(horizon),maximum_step_s=float(horizon),
        minimum_step_s=2**-30,maximum_steps=8,maximum_wall_seconds=30.)
    seed=evaluate_source_prefix_trial(adapter,initial,start=T(F()),end=T(horizon),
        integration_policy=numerical,maximum_callbacks=16)
    assert seed.reason=='source_prefix_negative_inventory_minimum' and len(seed.captures)==2
    base=getattr(model,'base',model)
    event=replace(policies()[1],maximum_refinements=32,terminal_method='affine_midpoint',
        roundoff_policy=replace(policies()[1].roundoff_policy,molar_mass_kg_mol=base.chemical.reference.molar_mass_kg_mol))
    approach=evaluate_source_approach(propose_source_approach(seed,event_policy=event),maximum_callbacks=16)
    assert approach.status=='validated_positive_numerical_approach',approach.reason
    refinement=evaluate_source_root_refinement(approach,maximum_callbacks=16)
    assert refinement.clock is not None,refinement.reason
    return refinement,T(F(.0003)) if programmed else seed.end


@pytest.fixture(scope='module')
def actual():
    with pytest.MonkeyPatch.context() as patch:
        yield prepare(patch)


@pytest.fixture(scope='module')
def programmed(actual):
    with pytest.MonkeyPatch.context() as patch:
        yield prepare(patch,actual[0].approach.proposal.original_trial.adapter.column)


def test_actual_terminal_uses_full_source_ledger_and_original_writeback(actual,monkeypatch):
    refinement,_=actual; seed=refinement.approach.proposal.original_trial
    terminal=build_source_terminal(seed,event_policy=refinement.approach.proposal.event_policy)
    assert terminal.clock.lower>seed.captures[1].time
    assert terminal.clock.upper>terminal.clock.lower
    assert terminal.clock.iterations<=terminal.event_policy.maximum_refinements
    assert terminal.clock.iterations==terminal.root_order.order.refinement_level+terminal.additional_clock_rounds
    assert terminal.corrected_state.amounts_mol[0,0]==0
    assert terminal.dry_adapter.interfaces==('depleted_no_nucleation',)
    np.testing.assert_array_equal(terminal.corrected_state.internal_energy_j,terminal.prefix.raw_state.internal_energy_j)
    water=lambda s:sum(map(F,s.amounts_mol[0,[0,3]]),F())
    assert water(terminal.corrected_state)-water(terminal.prefix.raw_state)==terminal.totals.signed_storage_roundoff_mol
    monkeypatch.setattr(ExactSourceColumn,'evaluate',lambda *a,**k:pytest.fail('terminal check called physics'))
    terminal.check()
    with pytest.raises(ValueError):replace(terminal,additional_clock_rounds=0).check()


@pytest.fixture(scope='module')
def completed(actual):
    refinement,end=actual
    return evaluate_source_dry_transition(refinement,end=end,maximum_callbacks_per_path=24)


def test_actual_wet_event_then_dry_reference_and_two_path_comparison(completed):
    out=completed
    assert len(out.candidates)==2
    for candidate in out.candidates:
        assert candidate.status=='executed_dry_candidate'
        assert candidate.seed.initial.amounts_mol[0,0]>0
        assert candidate.captures[0].state.amounts_mol[0,0]==0
        assert candidate.captures[0].time==candidate.terminal.clock.lower
        assert candidate.captures[-1].time==candidate.end>candidate.captures[0].time
        assert len(candidate.reference.steps)>=1
        assert all(c.evaluation.source_evaluation.cells[0].phase.phase_water_mol_s==0 for c in candidate.captures)
        assert all(c.state.energy_model_identity==candidate.seed.energy_identity for c in candidate.captures)
    assert [r.phase for r in out.balance_paths[0]][:2]==['wet_terminal','writeback']
    assert [r.phase for r in out.balance_paths[1]][:3]==['wet_reference','wet_terminal','writeback']
    assert out.endpoint_differences[0][0]=='event' and out.endpoint_differences[1][0]=='common'
    assert out.endpoint_differences[1][1]==out.endpoint_differences[1][2]
    assert all(all(row[:3]) for row in out.endpoint_gates)
    assert not out.material_qualified


def test_terminal_reuses_bound_prior_root_depth(completed):
    for index,candidate in enumerate(completed.candidates):
        terminal=candidate.terminal
        prior=completed.refinement.clock
        assert terminal.prior_clock is prior and terminal.root_index==index
        assert terminal.reused_clock_rounds==max(prior.refined_roots[index].refinements,
                                               terminal.root_order.order.refinement_level)
        assert terminal.clock.iterations==terminal.reused_clock_rounds+terminal.additional_clock_rounds
        assert terminal.clock.iterations<=terminal.event_policy.maximum_refinements
        with pytest.raises(ValueError):
            replace(terminal,root_index=1-index).check()
        with pytest.raises(ValueError):
            replace(terminal,reused_clock_rounds=terminal.reused_clock_rounds+1).check()


def test_actual_remaining_dry_policy_is_frozen(completed):
    candidate=completed.candidates[0]
    revised=replace(candidate.dry_policy,maximum_wall_seconds=candidate.seed.policy.maximum_wall_seconds)
    with pytest.raises(ValueError):replace(candidate,dry_policy=revised).check()


def test_passive_complete_record_replay_and_tamper_refusal(completed,monkeypatch):
    monkeypatch.setattr(ExactSourceColumn,'evaluate',lambda *a,**k:pytest.fail('passive check called physics'))
    completed.check()
    with pytest.raises(ValueError):replace(completed,numerical_event_accepted=not completed.numerical_event_accepted).check()
    candidate=completed.candidates[0]
    step=replace(candidate.reference.steps[0],face_energy_j=candidate.reference.steps[0].face_energy_j+1)
    with pytest.raises(ValueError):
        replace(candidate,reference=replace(candidate.reference,steps=(step,*candidate.reference.steps[1:]))).check()


@pytest.mark.parametrize('cancelled',[False,True])
def test_stop_preserves_source_candidate_without_invented_callbacks(actual,cancelled):
    refinement,end=actual; seed=refinement.approach.proposal.original_trial
    out=execute_source_dry_candidate(seed,event_policy=refinement.approach.proposal.event_policy,end=end,
        maximum_callbacks=1,cancel=(lambda:True) if cancelled else None)
    assert out.status==('cancelled' if cancelled else 'resource_limit')
    assert len(out.captures)==(0 if cancelled else 1)
    if not cancelled:
        assert out.reference.status!='completed'
        assert out.reference.evaluations>len(out.captures)
        assert out.captures[0].state.amounts_mol[0,0]==0
    out.check()


def test_actual_dry_callback_domain_exit_is_preserved(actual,monkeypatch):
    refinement,end=actual; seed=refinement.approach.proposal.original_trial
    actual_call=ExactSourceColumn.evaluate
    def failing(self,state,when):
        if self.interfaces==('depleted_no_nucleation',):raise DomainExit('dry-condensation-domain-exit')
        return actual_call(self,state,when)
    monkeypatch.setattr(ExactSourceColumn,'evaluate',failing)
    out=execute_source_dry_candidate(seed,event_policy=refinement.approach.proposal.event_policy,end=end,maximum_callbacks=8)
    assert out.status!='executed_dry_candidate' and out.captures
    assert out.captures[0].failure=='dry-condensation-domain-exit'
    assert out.captures[0].evaluation is None
    out.check()


@pytest.mark.parametrize('as_float',[False,True])
def test_failed_dry_attempt_time_binding_has_no_mutable_alias(actual,monkeypatch,as_float):
    refinement,end=actual
    def fail(*args,**kwargs):raise DomainExit('retained exact dry input')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',fail)
    out=execute_source_dry_candidate(refinement.approach.proposal.original_trial,
        event_policy=refinement.approach.proposal.event_policy,end=end,maximum_callbacks=8)
    capture=out.captures[0]
    assert capture.time is not capture.input_binding[2]
    changed=(capture.time.seconds+end.seconds)/2
    object.__setattr__(capture.time,'seconds',float(changed) if as_float else changed)
    with pytest.raises(ValueError):out.check()


def test_pressure_assessment_failure_preserves_completed_actual_dry_run(actual,monkeypatch):
    import sludge_sandbox.source_dry_transition as module
    refinement,end=actual
    def fail(*a,**k):raise RuntimeError('assessment-retained')
    monkeypatch.setattr(module,'enclose_source_dry_pressure',fail)
    with pytest.raises(SourceDryTransitionError) as caught:
        evaluate_source_dry_transition(refinement,end=end,maximum_callbacks_per_path=24)
    assert len(caught.value.candidates)==1
    candidate=caught.value.candidates[0]
    assert candidate.reference.status=='completed' and candidate.captures[-1].time==end
    assert candidate.status=='failed' and 'assessment-retained' in candidate.reason


@pytest.mark.parametrize('change',[{'terminal_method':'euler'},{'maximum_refinements':2},{'terminal_window_s':1e-12}])
def test_original_terminal_controls_refuse_without_new_physics(actual,monkeypatch,change):
    refinement,end=actual; seed=refinement.approach.proposal.original_trial
    monkeypatch.setattr(ExactSourceColumn,'evaluate',lambda *a,**k:pytest.fail('refused terminal evaluated physics'))
    out=execute_source_dry_candidate(seed,event_policy=replace(refinement.approach.proposal.event_policy,**change),
        end=end,maximum_callbacks=24)
    assert out.status=='failed' and not out.captures and out.reference is None


def test_programmed_dry_segment_advances_energy_and_resolves_exact_knot(programmed):
    refinement,end=programmed
    out=evaluate_source_dry_transition(refinement,end=end,maximum_callbacks_per_path=32)
    for candidate in out.candidates:
        assert T(F(.0002)) in candidate.reference.times_s
        assert candidate.reference.states[-1].internal_energy_j[0]>candidate.terminal.corrected_state.internal_energy_j[0]
        assert candidate.captures[-1].evaluation.source_evaluation.cells[0].inverse.point.temperature_k>candidate.captures[0].evaluation.source_evaluation.cells[0].inverse.point.temperature_k
        assert candidate.terminal.seed.adapter.interfaces==('existing_liquid',)
    assert all(abs(row.energy_residual_j)<=F(refinement.approach.trial.policy.energy_absolute_tolerance_j)
               for path in out.balance_paths for row in path)
