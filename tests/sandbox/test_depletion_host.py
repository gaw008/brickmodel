"""Real water/solid inventory and oven boundary used by the depletion experiment."""
from dataclasses import replace
from sludge_sandbox.phase_storage import InversePolicy
from test_programmed_water_phase_transfer import programmed_transfer
from test_solid_fluid_heat import ingredients


def wet_dry_host(ingredients):
    op=programmed_transfer(ingredients)
    thermal=op.base_model.base_model
    thermal=replace(thermal,transport=replace(thermal.transport,
        inverse_policy=InversePolicy(1e-6,1e-6,120)))
    boundary=replace(op.base_model.program,knot_times_s=(0.,1/64,1/32),
        gas_temperature_k=(330.,340.,335.),radiation_temperature_k=(330.,340.,335.))
    op=replace(op,base_model=replace(op.base_model,base_model=thermal,program=boundary),
        coefficients_mol_s_pa=(1e-6,))
    initial=thermal.state_from_temperatures([[2.,1e-8,1e-6,.001]],[300.])
    return op,initial


def test_real_initial_state_is_wet_and_physical_source_is_active(ingredients):
    import pytest
    op,initial=wet_dry_host(ingredients)
    out=op.evaluate(initial,0.)
    assert out.cell_transfers[0].rate_mol_s>0
    assert out.base_evaluation.conductive_into_cell_w==pytest.approx(2.,rel=0,abs=1e-7)
    assert (out.base_evaluation.base_evaluation.rates.face_species_mol_s==0).all()
    assert op.breakpoints_s(0.,1/32)==(1/64,)


def run_wet_dry_host(ingredients):
    from sludge_sandbox.depletion_integration import integrate_depletion
    from test_depletion_integration import policies
    op,initial=wet_dry_host(ingredients)
    policy,event=policies()
    policy=replace(policy,initial_step_s=1/1024,maximum_step_s=1/256,
        maximum_steps=500,maximum_wall_seconds=120.)
    event=replace(event,time_absolute_s=1e-7,amount_absolute_mol=1e-10,
        energy_absolute_j=1e-6,temperature_absolute_k=1e-5,pressure_absolute_pa=1.,
        terminal_window_s=1/16384,common_time_horizon_s=1/256,
        roundoff_policy=replace(event.roundoff_policy,
            molar_mass_kg_mol=op.chemical.reference.molar_mass_kg_mol))
    result=integrate_depletion(initial,op,start_s=0.,end_s=1/32,
        integration_policy=policy,event_policy=event)
    return op,result


def assert_wet_dry_host(op,result):
    from fractions import Fraction
    import numpy as np
    import pytest
    assert result.status=='completed',result.reason
    assert result.times_s[-1]==1/32 and 1/64 in result.times_s
    assert len(result.events)==1
    event=result.events[0]
    signed=Fraction(0);absolute=Fraction(0);correction=Fraction(0)
    for item in result.corrections:
        assert item.ideal_liquid_increment_mol==-Fraction(item.liquid_before_mol)
        assert item.ideal_vapor_increment_mol==Fraction(item.liquid_before_mol)
        actual=Fraction(item.vapor_after_mol)-Fraction(item.vapor_before_mol)
        assert actual==item.actual_vapor_increment_mol
        residual=actual-item.ideal_vapor_increment_mol
        assert residual==item.vapor_storage_roundoff_mol
        signed+=residual;absolute+=abs(residual);correction+=item.ideal_vapor_increment_mol
    assert result.roundoff_totals.signed_storage_roundoff_mol==signed
    assert result.roundoff_totals.absolute_storage_roundoff_mol==absolute
    assert result.roundoff_totals.numerical_phase_correction_mol==correction
    assert result.roundoff_totals.events==len(result.corrections)
    assert 0<event.time_s<1/64
    assert result.operator.interfaces==('depleted_no_nucleation',)
    assert result.operator.coefficients_mol_s_pa==op.coefficients_mol_s_pa==(1e-6,)
    first=result.states[0]
    assert first.amounts_mol[0,2]>0
    water0=Fraction(float(first.amounts_mol[0,1]))+Fraction(float(first.amounts_mol[0,2]))
    energy0=Fraction(float(first.internal_energy_j[0]));heat=Fraction(0)
    previous=first
    for index,(at,state) in enumerate(zip(result.times_s,result.states)):
        assert np.array_equal(state.amounts_mol[:,[0,3]],first.amounts_mol[:,[0,3]])
        dw=Fraction(float(state.amounts_mol[0,1]))+Fraction(float(state.amounts_mol[0,2]))-water0
        assert abs(dw)<=Fraction(1e-12)
        assert abs(dw)*Fraction(op.chemical.reference.molar_mass_kg_mol)<=Fraction(1e-13)
        assert abs(2*dw)<=Fraction(2e-12)  # H atoms; O equals water amount.
        if index:
            step=result.steps[index-1]
            assert (step.start_s,step.end_s)==(result.times_s[index-1],at)
            q=sum(map(Fraction,map(float,step.face_energy_j[:-1]))) - sum(map(Fraction,map(float,step.face_energy_j[1:]))) + sum(map(Fraction,map(float,step.cell_work_j)))
            heat+=q
            assert abs(Fraction(float(state.internal_energy_j[0]))-Fraction(float(previous.internal_energy_j[0]))-q)<=Fraction(1e-7)
        assert abs(Fraction(float(state.internal_energy_j[0]))-energy0-heat)<=Fraction(1e-7)
        current=op if at<event.time_s else result.operator
        observation=current.evaluate(state,at).base_evaluation
        temperature=observation.storage_states[0].mechanical.temperature_k
        gas_temperature=float(np.interp(at,(0.,1/64,1/32),(330.,340.,335.)))
        assert observation.conductive_into_cell_w==pytest.approx((gas_temperature-temperature)/15,rel=0,abs=1e-7)
        if at>=event.time_s:assert state.amounts_mol[0,2]==0
        previous=state
    event_state=result.states[result.times_s.index(event.time_s)]
    at_event=result.operator.evaluate(event_state,event.time_s).base_evaluation
    final=result.operator.evaluate(result.states[-1],result.times_s[-1]).base_evaluation
    assert final.storage_states[0].mechanical.temperature_k-final.storage_inverses[0].temperature_error_bound_k > at_event.storage_states[0].mechanical.temperature_k+at_event.storage_inverses[0].temperature_error_bound_k


def test_actual_wet_depletion_keeps_oven_heat_and_continues(ingredients):
    op,result=run_wet_dry_host(ingredients)
    assert_wet_dry_host(op,result)
