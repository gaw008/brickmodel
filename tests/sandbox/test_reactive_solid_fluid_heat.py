"""Manufactured kinetics coupled to real extensive storage, never sludge admission."""
from dataclasses import replace
import pytest
from sludge_sandbox.solid_fluid_heat import SolidFluidHeatError
from test_solid_fluid_heat import solid_host,ingredients


def test_reaction_config_cannot_be_a_duck_object(ingredients):
    with pytest.raises(SolidFluidHeatError,match='reaction'):
        replace(solid_host(ingredients),solid_reactions=object())

import math
import numpy as np
from sludge_sandbox.solid_fluid_heat import SolidFluidHeat,InventoryLayout
from sludge_sandbox.phase_storage import IdealGasPhase
from sludge_sandbox.reactions import SpeciesDefinition,ReactionDefinition,ReactionNetwork
from sludge_sandbox.integration import IntegrationPolicy,integrate
from test_reactions import kinetics


def reactive_host(ingredients,*,cells=1):
    from sludge_sandbox.solid_reactions import SolidReactionConfig,ReactionSpeciesBinding
    host=solid_host(ingredients,cells=cells,heat=0.)
    templates=[];storages=[]
    names=('fixture','H2O','O2','CO2')
    for original in host.storages:
        template=original.fluid_template
        curve=template.gas_phases['fixture'].caloric
        oxygen=IdealGasPhase(replace(curve,species_id='O2'),.032,0,('nist-codata-2022',))
        seg=replace(curve.segments[0],coefficients=(30.,0.,0.,0.,0.,-200.,0.,-200.),formation_enthalpy_298_j_mol=-200000.)
        co2=IdealGasPhase(replace(curve,species_id='CO2',segments=(seg,)),.044,0,('nist-codata-2022',))
        template=replace(template,mechanical=replace(template.mechanical,gas_species_ids=names),
            gas_phases=dict(template.gas_phases)|{'O2':oxygen,'CO2':co2},
            envelope=replace(template.envelope,gas_u_error_j_mol={n:1e-9 for n in names},gas_cv_lower_j_mol_k={n:20. for n in names}))
        solid=original.solid_phases['fixture_solid']
        feed=replace(solid,molar_mass_kg_mol=.012,caloric=replace(solid.caloric,species_id='feed',
            coefficients=(50.,0.,0.,0.,0.,-99.,0.,-99.),formation_enthalpy_298_j_mol=-99000.))
        char=replace(solid,molar_mass_kg_mol=.012,molar_volume_m3_mol=2e-6,
            caloric=replace(solid.caloric,species_id='char'))
        templates.append(template);storages.append(replace(original,fluid_template=template,solid_phases={'feed':feed,'char':char}))
    transport=replace(host.transport,storages=tuple(templates),gas_species_order=names,
        effective_diffusivities_m2_s={n:(0.,)*cells for n in names})
    layout=InventoryLayout(species_order=('char','H2O','H2O_liquid','fixture','O2','feed','CO2'),
        liquid_column_id='H2O_liquid',gas_species_order=names,solid_species_order=('feed','char'))
    source=('manufactured:coupled-reaction',)
    species=(SpeciesDefinition('feed','solid',{'C':1},.012,source,'manufactured'),
        SpeciesDefinition('char','solid',{'C':1},.012,source,'manufactured'),
        SpeciesDefinition('oxygen','gas',{'O':2},.032,source,'manufactured'),
        SpeciesDefinition('co2','gas',{'C':1,'O':2},.044,source,'manufactured'))
    r=templates[0].mechanical.gas_constant_j_mol_k
    pathways=(ReactionDefinition('pyrolysis','1',{'feed':-1,'char':1},kinetics({'feed':1},candidate_id='manufactured-feed-channel',
        prefactor_mol_m3_s=.1,gas_constant_j_mol_k=r,temperature_range_k=(293.,500.)),'oxygen_free_pyrolysis',source),
        ReactionDefinition('oxidation','1',{'char':-1,'oxygen':-1,'co2':1},kinetics({'char':1,'oxygen':1},candidate_id='manufactured-oxidation-channel',
        prefactor_mol_m3_s=.001,gas_constant_j_mol_k=r,temperature_range_k=(293.,500.)),'oxygen_consuming',source))
    network=ReactionNetwork(species,pathways,allow_manufactured=True)
    bindings=(ReactionSpeciesBinding('feed','feed',storages[0].solid_phases['feed']),
        ReactionSpeciesBinding('char','char',storages[0].solid_phases['char']),
        ReactionSpeciesBinding('oxygen','O2',templates[0].gas_phases['O2']),
        ReactionSpeciesBinding('co2','CO2',templates[0].gas_phases['CO2']))
    config=SolidReactionConfig(network=network,bindings=bindings,storages=tuple(storages),inventory_layout=layout,
        allow_manufactured=True,binding_id='manufactured:coupled-binding',version='1',source_ids=source)
    return SolidFluidHeat(storages=tuple(storages),inventory_layout=layout,transport=transport,solid_reactions=config)


def test_zero_oxygen_stops_only_oxidation_and_source_has_no_extra_heat(ingredients):
    host=reactive_host(ingredients)
    state=host.state_from_temperatures([[.01,1e-5,0.,.001,0.,.001,0.]],[300.])
    out=host.evaluate(state,0)
    rates=out.reaction_cells[0].network_rates
    assert rates.extent_mol_s[0]>0
    assert rates.extent_mol_s[1]==0
    assert out.rates.reaction_species_mol_s[0,5]<0
    assert out.rates.reaction_species_mol_s[0,0]>0
    assert out.rates.cell_power_w[0]==0


def test_finite_oxygen_closed_reaction_integrates_energy_elements_and_analytic_feed(ingredients):
    host=reactive_host(ingredients)
    initial=host.state_from_temperatures([[.01,1e-5,0.,.001,.0001,.001,0.]],[300.])
    run=integrate(initial,host,start_s=0,end_s=.1,policy=IntegrationPolicy(
        initial_step_s=.01,maximum_step_s=.02,minimum_step_s=1e-10,relative_tolerance=1e-7,
        amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-5,
        amount_scale_mol=.001,energy_scale_j=1.,maximum_steps=100,maximum_rejections=20,maximum_wall_seconds=120))
    assert run.status=='completed',run.reason
    for state in run.states:
        row=state.amounts_mol[0]
        assert np.all(row>=0)
        assert math.fsum(row[[0,5,6]])==pytest.approx(.011,rel=0,abs=1e-10)
        assert math.fsum(row[[4,6]])==pytest.approx(.0001,rel=0,abs=1e-10)
        mass=.012*(row[0]+row[5])+.032*row[4]+.044*row[6]
        assert mass==pytest.approx(.012*.011+.032*.0001,rel=0,abs=1e-10)
        assert state.internal_energy_j[0]==pytest.approx(initial.internal_energy_j[0],rel=0,abs=1e-6)
        assert 0<=row[4]<=.0001
    final=run.states[-1]
    assert final.amounts_mol[0,5]==pytest.approx(.001*math.exp(-.1*.1),rel=0,abs=1e-9)
    assert final.amounts_mol[0,4]<.0001
    inverse=host.decode_inverse(final)[0]
    assert inverse.state.mechanical.temperature_k-inverse.temperature_error_bound_k>300.
    assert inverse.state.solid_volume_m3!=host.storages[0].evaluate_at_temperature(300.,*host._inputs(initial.amounts_mol[0])).solid_volume_m3


def test_reaction_diagnostics_survive_program_water_and_liquid_chain(ingredients):
    from test_liquid_solid_fluid_heat import liquid_host
    from test_programmed_water_phase_transfer import programmed_transfer
    host=reactive_host(ingredients,cells=2)
    host=replace(host,liquid_transport=liquid_host(ingredients).liquid_transport,
        transport=replace(host.transport,conductivities_w_m_k=(.1,.1)))
    old=programmed_transfer(ingredients)
    boundary=replace(old.base_model.program,species_order=host.gas_species_order,
        mole_fractions=((.9,.05,.05,0.),)*3)
    program=replace(old.base_model,base_model=host,program=boundary)
    op=replace(old,base_model=program,coefficients_mol_s_pa=(1e-7,1e-7))
    state=host.state_from_temperatures([[.01,1e-5,2.,.02,.0001,.001,0.],
                                      [.01,1e-5,1.,.01,.0001,.001,0.]],[300.,301.])
    out=op.evaluate(state,.0005)
    base=out.base_evaluation.base_evaluation
    assert len(base.reaction_cells)==2
    assert len(base.liquid_faces)==1
    assert base.reaction_cells[0].network_rates.extent_mol_s[1]>0
    assert base.liquid_faces[0].molar_flow_mol_s>0
    assert out.rates.reaction_species_mol_s[0,5]==base.reaction_cells[0].source_mol_s[5]
    assert out.rates.reaction_species_mol_s[0,1]>0
    assert out.base_evaluation.boundary.gas_temperature_k==340.
    assert op.breakpoints_s(0,.001)==(.0005,)
    assert out.rates.cell_power_w[0]==0


def test_positive_activation_energy_uses_actual_decoded_temperature(ingredients):
    host=reactive_host(ingredients)
    network=host.solid_reactions.network
    reactions=tuple(replace(r,kinetics=replace(r.kinetics,activation_energy_j_mol=12000.)) for r in network.reactions)
    host=replace(host,solid_reactions=replace(host.solid_reactions,network=replace(network,reactions=reactions)))
    row=[[.01,1e-5,0.,.001,.0001,.001,0.]]
    cold=host.evaluate(host.state_from_temperatures(row,[300.]),0).reaction_cells[0]
    hot=host.evaluate(host.state_from_temperatures(row,[305.]),0).reaction_cells[0]
    r=host.storages[0].fluid_template.mechanical.gas_constant_j_mol_k
    expected=math.exp(12000./r*(1/cold.temperature_k-1/hot.temperature_k))
    assert expected>1
    for a,b in zip(cold.network_rates.extent_mol_s,hot.network_rates.extent_mol_s):
        assert b/a==pytest.approx(expected,rel=1e-12,abs=0)


def test_only_manufactured_reaction_reaches_wrapper_gate(ingredients):
    from test_programmed_water_phase_transfer import programmed_transfer
    from test_water_phase_transfer import transfer
    from sludge_sandbox.water_phase_transfer import WaterPhaseTransferError
    from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeatError
    host=reactive_host(ingredients)
    storage=host.storages[0]
    template=storage.fluid_template
    gases={n:(p if n=='H2O' else replace(p,caloric=replace(p.caloric,classification='literature_constitutive_model')))
           for n,p in template.gas_phases.items()}
    template=replace(template,gas_phases=gases)
    solids={n:replace(p,caloric=replace(p.caloric,classification='literature_constitutive_model'),
        volume_classification='literature_constitutive_model',error_classification='derived_from_evidence')
        for n,p in storage.solid_phases.items()}
    storage=replace(storage,fluid_template=template,solid_phases=solids,geometry_classification='virtual_design_choice')
    # Classification-only controls on synthetic records, never a material source claim.
    bindings=tuple(replace(b,provider=(solids.get(b.inventory_column_id) or gases[b.inventory_column_id]))
                   for b in host.solid_reactions.bindings)
    config=replace(host.solid_reactions,bindings=bindings,storages=(storage,))
    host=replace(host,storages=(storage,),transport=replace(host.transport,storages=(template,),
        coefficient_classification='literature_candidate'),solid_reactions=config)
    old=programmed_transfer(ingredients).base_model
    program=replace(old.program,species_order=host.gas_species_order,mole_fractions=((.9,.05,.05,0.),)*3)
    with pytest.raises(ProgrammedSolidFluidHeatError,match='manufactured'):
        replace(old,base_model=host,program=program,coefficient_classification='literature_candidate',allow_manufactured=False)
    with pytest.raises(WaterPhaseTransferError,match='manufactured'):
        replace(transfer(ingredients),base_model=host,coefficient_classification='literature_constitutive_model',allow_manufactured=False)
    clean=replace(host,solid_reactions=None)
    replace(old,base_model=clean,program=program,coefficient_classification='literature_candidate',allow_manufactured=False)
    replace(transfer(ingredients),base_model=clean,coefficient_classification='literature_constitutive_model',allow_manufactured=False)


def test_old_positional_evaluation_fields_keep_their_meaning():
    from sludge_sandbox.solid_fluid_heat import SolidFluidHeatEvaluation
    from sludge_sandbox.integration import Rates
    rates=Rates(np.zeros((2,1)),np.zeros(2),np.zeros((1,1)),np.zeros(1))
    out=SolidFluidHeatEvaluation(rates,(),(),(),'old-qualification',(),'fixed_decoded_temperature',False)
    assert out.liquid_pressure_interval_scope=='fixed_decoded_temperature'
    assert out.full_inverse_liquid_direction_certified is False
    assert out.reaction_cells==()


def test_kinetic_temperature_domain_exits_as_domain(ingredients):
    from sludge_sandbox.integration import DomainExit
    host=reactive_host(ingredients)
    network=host.solid_reactions.network
    reactions=tuple(replace(r,kinetics=replace(r.kinetics,temperature_range_k=(301.,500.))) for r in network.reactions)
    host=replace(host,solid_reactions=replace(host.solid_reactions,network=replace(network,reactions=reactions)))
    state=host.state_from_temperatures([[.01,1e-5,0.,.001,.0001,.001,0.]],[300.])
    with pytest.raises(DomainExit,match='kinetic_domain'):host.evaluate(state,0)
