"""Preregistered single-cell wet event followed by Joined-vapor high-temperature heat."""
from dataclasses import replace
from fractions import Fraction as F
import math
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import brentq
from sludge_sandbox.depletion_integration import integrate_depletion
from sludge_sandbox.phase_storage import InversePolicy
from test_joined_water_host import ingredients,joined,host,independent_u
from test_programmed_water_phase_transfer import programmed_transfer
from test_depletion_integration import policies


def wet_to_hot_host(ingredients,joined):
    thermal=host(ingredients,joined,500.)
    old=programmed_transfer(ingredients)
    fluid=thermal.storages[0].fluid_template
    fluid=replace(fluid,envelope=replace(fluid.envelope,temperature_range_k=(295.,600.)))
    storage=replace(thermal.storages[0],fluid_template=fluid)
    thermal=replace(thermal,storages=(storage,),transport=replace(thermal.transport,storages=(fluid,),
        conductivities_w_m_k=(.1,),temperature_brackets_k=((295.,310.),),
        effective_diffusivities_m2_s={n:(0.,) for n in thermal.gas_species_order},
        inverse_policy=InversePolicy(1e-6,1e-6,120)),dry_temperature_brackets_k=((295.,600.),),
        inverse_bracket_policy_id='numerical:wet-to-hot',inverse_bracket_policy_version='1',
        inverse_bracket_policy_reason='Retain wet EOS search domain and use broad bracket only after exact liquid depletion.')
    boundary=replace(old.base_model.program,knot_times_s=(0.,600.),gas_temperature_k=(1000.,)*2,
        radiation_temperature_k=(1000.,)*2,total_pressure_pa=(4e5,)*2,mole_fractions=((1.,0.),)*2)
    op=replace(old,base_model=replace(old.base_model,base_model=thermal,program=boundary),
        coefficients_mol_s_pa=(1e-6,),dry_policy='metastable_no_nucleation')
    return op,thermal.state_from_temperatures([[2.,1e-8,1e-6,.001]],[300.])


def run_wet_to_hot(ingredients,joined):
    op,initial=wet_to_hot_host(ingredients,joined)
    p,e=policies()
    p=replace(p,initial_step_s=1/1024,maximum_step_s=2.,maximum_steps=20000,maximum_wall_seconds=240.)
    e=replace(e,time_absolute_s=1e-7,amount_absolute_mol=1e-10,energy_absolute_j=1e-6,
        temperature_absolute_k=1e-5,pressure_absolute_pa=1.,terminal_window_s=1/16384,
        common_time_horizon_s=1/256,roundoff_policy=replace(e.roundoff_policy,
            molar_mass_kg_mol=op.chemical.reference.molar_mass_kg_mol))
    return op,integrate_depletion(initial,op,start_s=0.,end_s=600.,integration_policy=p,event_policy=e)


def independent_dry_temperature(op,result):
    vapor=op.base_model.base_model.storages[0].fluid_template.gas_phases['H2O'].caloric
    event=result.events[0];state=result.states[result.times_s.index(event.time_s)]
    nw=float(state.amounts_mol[0,1]);nt=float(state.amounts_mol[0,3]);r=vapor.gas_constant_j_mol_k
    def water_u(t):
        # Existing independent Decimal original-Cp integral and fixed low anchor;
        # remove that oracle's explicitly manufactured solid contribution.
        return (independent_u(vapor,t)-2*(-100000+50*t-1e5*1e-6))/.01
    def energy(t):return 2*(-100000+50*t-1e5*1e-6)+nw*water_u(t)+nt*(30-r)*t
    start=brentq(lambda t:energy(t)-state.internal_energy_j[0],295.,310.,xtol=1e-10)
    def capacity(t):
        if t<=500:cp=vapor.low_model.cp_j_mol_k(t)
        else:
            segment=vapor.source_gas.segment_for(t)
            a,b,c,d,e,*_=segment.coefficients;x=t/1000
            cp=a+b*x+c*x*x+d*x*x*x+e/(x*x)
        return 100+nw*(cp-r)+nt*(30-r)
    def elapsed(t):
        points=[start]+([500.] if start<500<t else [])+[t]
        return math.fsum(quad(lambda x:15*capacity(x)/(1000-x),a,b,epsabs=1e-8,epsrel=1e-11)[0]
                         for a,b in zip(points,points[1:]))
    target=brentq(lambda t:elapsed(t)-(600-event.time_s),start,599.,xtol=1e-9)
    return start,target


def audit_wet_to_hot(op,result):
    assert result.status=='completed',result.reason
    assert result.times_s[-1]==600. and len(result.events)==1
    assert result.states[0].amounts_mol[0,2]==1e-6
    assert result.operator.interfaces==('depleted_no_nucleation',)
    assert result.operator.coefficients_mol_s_pa==op.coefficients_mol_s_pa==(1e-6,)
    assert result.operator.dry_policy=='metastable_no_nucleation'
    assert len(result.states)==len(result.times_s)==len(result.steps)+1
    assert result.times_s[0]==0. and all(a<b for a,b in zip(result.times_s,result.times_s[1:]))
    event=result.events[0]
    assert 0.<event.time_s<event.common_time_s<=600.
    assert event.time_s in result.times_s
    assert sum(step is event.terminal_panel for step in result.steps)==1
    c=event.correction
    if c is None:
        assert not result.corrections
        assert result.roundoff_totals.signed_storage_roundoff_mol==0
        assert result.roundoff_totals.absolute_storage_roundoff_mol==0
        assert result.roundoff_totals.numerical_phase_correction_mol==0
        assert result.roundoff_totals.events==0
    else:
        assert len(result.corrections)==1 and result.corrections[0] is event.correction
        assert (c.cell_index,c.liquid_index,c.vapor_index)==(0,2,1)
        assert c.ideal_liquid_increment_mol==-F(c.liquid_before_mol)
        assert c.ideal_vapor_increment_mol==F(c.liquid_before_mol)
        assert c.ideal_liquid_increment_mol==-c.ideal_vapor_increment_mol
        assert c.actual_vapor_increment_mol==F(c.vapor_after_mol)-F(c.vapor_before_mol)
        assert c.vapor_storage_roundoff_mol==c.actual_vapor_increment_mol-c.ideal_vapor_increment_mol
        assert result.roundoff_totals.signed_storage_roundoff_mol==c.vapor_storage_roundoff_mol
        assert result.roundoff_totals.absolute_storage_roundoff_mol==abs(c.vapor_storage_roundoff_mol)
        assert result.roundoff_totals.numerical_phase_correction_mol==c.ideal_vapor_increment_mol
        assert result.roundoff_totals.events==1
    first=result.states[0];water0=F(float(first.amounts_mol[0,1]))+F(float(first.amounts_mol[0,2]))
    heat=F(0);max_water=F(0);max_energy=F(0);max_column=F(0)
    cumulative=[F(0) for _ in range(4)]
    mass=F(op.chemical.reference.molar_mass_kg_mol)
    for i,state in enumerate(result.states):
        assert np.array_equal(state.amounts_mol[:,[0,3]],first.amounts_mol[:,[0,3]])
        dw=F(float(state.amounts_mol[0,1]))+F(float(state.amounts_mol[0,2]))-water0
        max_water=max(max_water,abs(dw))
        assert abs(dw)<=F(1e-12)  # O atoms and water molecules
        assert abs(2*dw)<=F(2e-12)  # H atoms
        assert abs(dw*mass)<=F(1e-13)
        if result.times_s[i]>=event.time_s:assert state.amounts_mol[0,2]==0.
        if i:
            step=result.steps[i-1]
            assert (step.start_s,step.end_s)==(result.times_s[i-1],result.times_s[i])
            assert np.all(step.face_species_mol==0)
            for col in range(4):
                increment=(F(float(step.face_species_mol[0,col]))-F(float(step.face_species_mol[-1,col]))
                           +F(float(step.reaction_species_mol[0,col])))
                if step is event.terminal_panel and c is not None:
                    if col==2:increment+=c.ideal_liquid_increment_mol
                    if col==1:increment+=c.ideal_vapor_increment_mol+c.vapor_storage_roundoff_mol
                actual=F(float(state.amounts_mol[0,col]))-F(float(result.states[i-1].amounts_mol[0,col]))
                assert abs(actual-increment)<=F(1e-12)
                cumulative[col]+=increment
            q=F(float(step.face_energy_j[0]))-F(float(step.face_energy_j[-1]))+F(float(step.cell_work_j[0]))
            assert abs(F(float(state.internal_energy_j[0]))-F(float(result.states[i-1].internal_energy_j[0]))-q)<=F(1e-7)
            heat+=q
        for col in range(4):
            residual=F(float(state.amounts_mol[0,col]))-F(float(first.amounts_mol[0,col]))-cumulative[col]
            max_column=max(max_column,abs(residual))
            assert abs(residual)<=F(1e-12)
        max_energy=max(max_energy,abs(F(float(state.internal_energy_j[0]))-F(float(first.internal_energy_j[0]))-heat))
    assert tuple(cumulative)==result.cumulative_amounts_mol
    assert (heat,)==result.cumulative_energy_j
    assert cumulative[1]+cumulative[2]==(c.vapor_storage_roundoff_mol if c is not None else 0)
    assert max_water<=F(1e-12) and max_energy<=F(1e-7)
    final=result.operator.evaluate(result.states[-1],600.)
    t=final.base_evaluation.storage_states[0].mechanical.temperature_k
    assert t-final.base_evaluation.storage_inverses[0].temperature_error_bound_k>500.
    assert final.cell_transfers[0].status=='metastable_no_nucleation_condensation_drive_unknown'
    assert final.cell_transfers[0].hypothetical_equilibrium is None
    assert final.base_evaluation.conductive_into_cell_w==pytest.approx((1000-t)/15,rel=0,abs=1e-7)
    start,expected=independent_dry_temperature(op,result)
    assert t==pytest.approx(expected,rel=0,abs=5e-4)
    return dict(final_temperature_k=t,independent_dry_final_temperature_k=expected,
                independent_event_temperature_k=start,maximum_water_residual_mol=float(max_water),maximum_energy_residual_j=float(max_energy),
                maximum_individual_inventory_prefix_residual_mol=float(max_column))


def test_wet_to_hot_initial_source_and_policy_are_explicit(ingredients,joined):
    op,initial=wet_to_hot_host(ingredients,joined)
    out=op.evaluate(initial,0.)
    assert op.interfaces==('existing_liquid',)
    assert out.cell_transfers[0].rate_mol_s>0
    assert out.base_evaluation.conductive_into_cell_w==pytest.approx(700/15,rel=0,abs=1e-7)
    assert np.all(out.rates.face_species_mol_s==0)
    assert out.base_evaluation.base_evaluation.temperature_brackets_k==((295.,310.),)


def test_actual_wet_event_continues_to_high_temperature(ingredients,joined):
    op,result=run_wet_to_hot(ingredients,joined)
    audit_wet_to_hot(op,result)
