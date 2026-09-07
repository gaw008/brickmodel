"""Two-cell real-water coupling; all solid/kinetic/mobility values manufactured."""
from dataclasses import replace
import numpy as np
from sludge_sandbox.phase_storage import InversePolicy
from test_reactive_solid_fluid_heat import reactive_host
from test_liquid_solid_fluid_heat import liquid_host
from test_programmed_water_phase_transfer import programmed_transfer
from test_solid_fluid_heat import ingredients


def coupled_host(ingredients):
    thermal=reactive_host(ingredients,cells=2)
    liquid=liquid_host(ingredients).liquid_transport
    relation=replace(liquid.relations[0],saturation_knots=(0.,1e-5,1.),
        permeability_m2=(1e-14,)*3,relative_permeability=(0.,1.,1.),
        viscosity_pa_s=(.001,)*3,relation_kind='tabulated_saturation_relation',
        model_id='manufactured:vanishing-liquid-mobility',
        source_ids=('manufactured:vanishing-liquid-mobility',))
    thermal=replace(thermal,liquid_transport=replace(liquid,relations=(relation,relation)),
        transport=replace(thermal.transport,conductivities_w_m_k=(.1,.1),
            effective_diffusivities_m2_s={n:((0.,0.) if n=='fixture' else (1e-7,1e-7)) for n in thermal.gas_species_order},
            inverse_policy=InversePolicy(1e-6,1e-6,120)))
    old=programmed_transfer(ingredients)
    program=replace(old.base_model.program,knot_times_s=(0.,1/512,1/256),
        gas_temperature_k=(330.,340.,335.),radiation_temperature_k=(330.,340.,335.),
        total_pressure_pa=(3e4,)*3,species_order=thermal.gas_species_order,
        mole_fractions=((.9,.005,.095,0.),)*3)
    op=replace(old,base_model=replace(old.base_model,base_model=thermal,program=program),
        coefficients_mol_s_pa=(1e-6,1e-6))
    initial=thermal.state_from_temperatures([
        [.01,1e-8,1e-6,.001,.0001,.001,0.],
        [.01,1e-8,4e-6,.0012,.0001,.001,0.]], [300.,301.])
    return op,initial


def test_initial_two_cell_water_liquid_heat_and_reactions_are_active(ingredients):
    op,initial=coupled_host(ingredients)
    observation=op.evaluate(initial,0.)
    base=observation.base_evaluation.base_evaluation
    assert all(cell.rate_mol_s>0 for cell in observation.cell_transfers)
    assert base.liquid_faces[0].molar_flow_mol_s!=0
    assert base.liquid_faces[0].enthalpy_flow_w!=0
    assert all(all(rate>0 for rate in cell.network_rates.extent_mol_s) for cell in base.reaction_cells)
    assert observation.rates.face_energy_w[1]!=0
    assert observation.base_evaluation.conductive_into_cell_w>0
    assert observation.rates.face_species_mol_s[-1,4]!=0  # finite oxygen boundary flow
    # Mixture correction also transports the zero-bare-D tracer; audit that
    # actual face flux, rather than assuming zero coefficient means immobility.
    assert observation.rates.face_species_mol_s[-1,3]!=0
    assert op.breakpoints_s(0.,1/256)==(1/512,)


def run_coupled_host(ingredients):
    from sludge_sandbox.depletion_integration import integrate_depletion
    from test_depletion_integration import policies
    op,initial=coupled_host(ingredients)
    policy,event=policies()
    policy=replace(policy,initial_step_s=1/1024,maximum_step_s=1/256,
        maximum_steps=1500,maximum_rejections=150,maximum_wall_seconds=600.)
    event=replace(event,time_absolute_s=1e-7,amount_absolute_mol=1e-10,
        energy_absolute_j=1e-6,temperature_absolute_k=1e-5,pressure_absolute_pa=1.,
        terminal_window_s=1/1048576,common_time_horizon_s=1/256,safe_inventory_fraction=.4,
        roundoff_policy=replace(event.roundoff_policy,
            molar_mass_kg_mol=op.chemical.reference.molar_mass_kg_mol))
    result=integrate_depletion(initial,op,start_s=0.,end_s=1/256,
        integration_policy=policy,event_policy=event)
    return op,result


def audit_coupled_host(op,result):
    from fractions import Fraction as F
    assert result.status=='completed',result.reason
    assert result.times_s[-1]==1/256 and 1/512 in result.times_s
    assert len(result.times_s)==len(result.states)==len(result.steps)+1
    assert len(result.events)==2
    assert {e.cell_index for e in result.events}=={0,1}
    assert result.events[0].time_s<result.events[1].time_s<result.times_s[-1]
    assert result.operator.interfaces==('depleted_no_nucleation',)*2
    assert result.operator.coefficients_mol_s_pa==op.coefficients_mol_s_pa==(1e-6,)*2
    assert result.safe_inventory_fraction==.4
    assert np.all(result.states[-1].amounts_mol[:,2]==0)
    first=result.states[0]
    assert np.all(first.amounts_mol[:,2]>0)
    cumulative=[[F(0) for _ in range(7)] for _ in range(2)]
    energy=[F(0),F(0)];external=[F(0)]*7
    projections=[[F(0) for _ in range(7)] for _ in range(2)]
    scalar_max=F(0);energy_max=F(0);element_max=F(0);mass_max=F(0)
    liquid_flow=F(0);liquid_absolute=F(0)
    totals_signed=F(0);totals_abs=F(0);correction_total=F(0)
    vectors=((1,0,0,0,0,1,1),(0,2,2,0,0,0,0),
             (0,1,1,0,2,0,2),(0,0,0,1,0,0,0),(0,1,1,0,0,0,0))
    mass=(.012,op.chemical.reference.molar_mass_kg_mol,
          op.chemical.reference.molar_mass_kg_mol,.028,.032,.012,.044)
    records={e.time_s:e.correction for e in result.events if e.correction is not None}
    for i,(step,after) in enumerate(zip(result.steps,result.states[1:])):
        before_terms=[row.copy() for row in cumulative]
        before_energy=energy.copy()
        assert (step.start_s,step.end_s)==(result.times_s[i],result.times_s[i+1])
        for col in range(7):
            external[col]+=F(float(step.face_species_mol[0,col]))-F(float(step.face_species_mol[-1,col]))
        liquid_flow+=F(float(step.face_species_mol[1,2]))
        liquid_absolute+=abs(F(float(step.face_species_mol[1,2])))
        for cell in range(2):
            energy[cell]+=F(float(step.face_energy_j[cell]))-F(float(step.face_energy_j[cell+1]))+F(float(step.cell_work_j[cell]))
            for col in range(7):
                cumulative[cell][col]+=F(float(step.face_species_mol[cell,col]))-F(float(step.face_species_mol[cell+1,col]))+F(float(step.reaction_species_mol[cell,col]))
        record=records.get(step.end_s)
        if record is not None:
            assert record.ideal_liquid_increment_mol==-record.ideal_vapor_increment_mol
            actual=F(record.vapor_after_mol)-F(record.vapor_before_mol)
            residual=actual-record.ideal_vapor_increment_mol
            assert residual==record.vapor_storage_roundoff_mol
            cell=record.cell_index
            for col,delta in ((record.liquid_index,record.ideal_liquid_increment_mol),
                              (record.vapor_index,actual)):
                cumulative[cell][col]+=delta;projections[cell][col]+=delta
            totals_signed+=residual;totals_abs+=abs(residual)
            correction_total+=record.ideal_vapor_increment_mol
        system_residual=[]
        for col in range(7):
            for cell in range(2):
                error=F(float(after.amounts_mol[cell,col]))-F(float(first.amounts_mol[cell,col]))-cumulative[cell][col]
                scalar_max=max(scalar_max,abs(error))
                step_error=F(float(after.amounts_mol[cell,col]))-F(float(result.states[i].amounts_mol[cell,col]))-(cumulative[cell][col]-before_terms[cell][col])
                scalar_max=max(scalar_max,abs(step_error))
            system_residual.append(sum((F(float(after.amounts_mol[cell,col]))-F(float(first.amounts_mol[cell,col]))-projections[cell][col] for cell in range(2)),F(0))-external[col])
        for vector in vectors:
            element_max=max(element_max,abs(sum((system_residual[j]*vector[j] for j in range(7)),F(0))))
        mass_max=max(mass_max,abs(sum((system_residual[j]*F(mass[j]) for j in range(7)),F(0))))
        for cell in range(2):
            energy_max=max(energy_max,abs(F(float(after.internal_energy_j[cell]))-F(float(first.internal_energy_j[cell]))-energy[cell]))
            energy_max=max(energy_max,abs(F(float(after.internal_energy_j[cell]))-F(float(result.states[i].internal_energy_j[cell]))-(energy[cell]-before_energy[cell])))
    assert scalar_max<=F(1e-10)
    assert element_max<=F(1e-10)
    assert mass_max<=F(1e-12)
    assert energy_max<=F(1e-7)
    assert liquid_absolute>0
    assert np.all(result.states[-1].amounts_mol[:,5]<first.amounts_mol[:,5])
    assert np.all(result.states[-1].amounts_mol[:,6]>first.amounts_mol[:,6])
    assert result.roundoff_totals.signed_storage_roundoff_mol==totals_signed
    assert result.roundoff_totals.absolute_storage_roundoff_mol==totals_abs
    assert result.roundoff_totals.numerical_phase_correction_mol==correction_total
    assert result.roundoff_totals.events==len(records)
    final=result.operator.evaluate(result.states[-1],result.times_s[-1])
    assert final.base_evaluation.conductive_into_cell_w>0
    assert all(all(rate>0 for rate in cell.network_rates.extent_mol_s) for cell in final.base_evaluation.base_evaluation.reaction_cells)
    assert final.base_evaluation.base_evaluation.liquid_faces[0].molar_flow_mol_s==0
    return dict(max_amount_residual_mol=float(scalar_max),max_element_residual_mol=float(element_max),
        max_mass_residual_kg=float(mass_max),max_energy_prefix_j=float(energy_max),
        integrated_internal_liquid_mol=float(liquid_flow),absolute_internal_liquid_mol=float(liquid_absolute))
