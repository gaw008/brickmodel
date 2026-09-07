"""Manufactured A->B chemistry, changing occupied volume and prescribed motion.

Dry tests forbid native water EOS. Independent temperature RHS uses explicit
fixture constants and analytic extent, never the production storage inverse.
"""
from dataclasses import replace
from fractions import Fraction as F
import math

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from test_rigid_storage import water, R
from test_deforming_solid_heat import host
from test_reactions import kinetics
from sludge_sandbox.deforming_solid_storage import solid_provider_identity
from sludge_sandbox.reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy
from sludge_sandbox.solid_fluid_heat import InventoryLayout, SolidFluidHeat
from sludge_sandbox.solid_reactions import SolidReactionConfig, ReactionSpeciesBinding
from sludge_sandbox.reactions import SpeciesDefinition, ReactionDefinition, ReactionNetwork
from sludge_sandbox.integration import IntegrationPolicy, integrate


def reacting_host(water, *, constant=False, weights=10., order=1., equal_volume=False):
    old = host(water, constant=constant)
    p = old.point_storages[0]
    a = p.template.solid_phases['fixture_solid']
    a = replace(a, molar_mass_kg_mol=.012, caloric=replace(a.caloric, species_id='A'))
    b = replace(a, molar_volume_m3_mol=2e-5 if equal_volume else 1e-5,
                caloric=replace(a.caloric, species_id='B',
                    coefficients=(5.,0.,0.,0.,0.,-100.005,0.,-100.005),
                    formation_enthalpy_298_j_mol=-100005.))
    template = replace(p.template, solid_phases={'A': a, 'B': b})
    reference = replace(p.skeleton, fixed_solid_inventory_mol=(('A',2.),('B',0.)),
        solid_provider_identity=solid_provider_identity(template.solid_phases),
        interface_energy_j_m2=100.)
    skeleton = ManufacturedReactingSkeletonEnergy(reference_model=reference,
        composition_offset=1., composition_weights_per_mol=(('A',0.),('B',weights)),
        model_id='manufactured-reacting-skeleton', version='1',
        classification='manufactured_test_fixture', allow_manufactured=True)
    p = replace(p, template=template, skeleton=skeleton)
    layout = InventoryLayout(species_order=('B','fixture','liquid','A'),
        liquid_column_id='liquid', gas_species_order=('fixture',), solid_species_order=('A','B'))
    sources = ('manufactured:reacting-deformation-A-to-B',)
    species = tuple(SpeciesDefinition(n,'solid',{'C':1},a.molar_mass_kg_mol,sources,'manufactured') for n in ('A','B'))
    reaction = ReactionDefinition('A-to-B','1',{'A':-1,'B':1},
        kinetics({'A':order}, prefactor_mol_m3_s=.1, gas_constant_j_mol_k=R),
        'oxygen_free_pyrolysis',sources)
    config = SolidReactionConfig(network=ReactionNetwork(species,(reaction,),allow_manufactured=True),
        bindings=tuple(ReactionSpeciesBinding(n,n,template.solid_phases[n]) for n in ('A','B')),
        storages=(template,),inventory_layout=layout,allow_manufactured=True,
        binding_id='manufactured-reacting-deformation-binding',version='1',source_ids=sources)
    base = SolidFluidHeat(storages=(template,),inventory_layout=layout,
        transport=replace(old.base_model.transport,storages=(template.fluid_template,)),solid_reactions=config)
    return replace(old,base_model=base,point_storages=(p,),solid_inventory_regime='reacting_manufactured')


def initial(op):
    return op.state_from_temperatures([[0.,.01,0.,2.]],[300.],time_s=0.)


def forbid_eos(water, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('dry manufactured chemistry must not call native water EOS')
    monkeypatch.setattr(type(water),'state_tp',forbidden)


def test_reactions_use_current_storage_volume_and_one_inverse(water,monkeypatch):
    forbid_eos(water,monkeypatch)
    op = reacting_host(water,order=2.)
    state = op.state_from_temperatures([[.2,.01,0.,1.8]],[300.],time_s=.5)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',lambda *a:pytest.fail('second inverse'))
    out = op.evaluate(state,.5)
    current = out.current_host
    assert current.solid_reactions.storages[0] is current.storages[0]
    assert current.storages[0] is out.total_inverses[0].state.current_storage
    assert out.thermal_evaluation.storage_inverses[0] is out.total_inverses[0].thermal_inverse
    expected = .1*1.8**2/(1.4e-4*.95)
    actual = out.thermal_evaluation.reaction_cells[0].network_rates.extent_mol_s[0]
    assert actual == pytest.approx(expected,rel=1e-12,abs=1e-14)
    assert actual != pytest.approx(.1*1.8**2/1.4e-4,rel=1e-4)
    assert out.rates.reaction_species_mol_s[0,0] == -out.rates.reaction_species_mol_s[0,3]
    assert set(out.rates.cell_power_components_w)=={'elastic_deformation','interface_deformation','dissipation','bulk_pressure','body'}
    assert out.rates.cell_power_components_w['body'][0]==0.


def test_fixed_default_and_state_binding_are_preserved(water):
    from sludge_sandbox.integration import ConservedState
    op=reacting_host(water)
    with pytest.raises(ValueError,match='regime'):
        replace(op,solid_inventory_regime='fixed_solid')
    old=host(water)
    with pytest.raises(ValueError,match='solid_reactions_not_admitted'):
        replace(old,base_model=op.base_model)
    with pytest.raises(ValueError,match='regime'):
        replace(old,solid_inventory_regime='reacting_manufactured')
    state=initial(op)
    with pytest.raises(ValueError,match='binding'):
        op.evaluate(ConservedState(state.amounts_mol,state.internal_energy_j),0.)
    assert not op.material_qualified


def test_reaction_identity_exact_fractions_and_pore_domain(water):
    from sludge_sandbox.deforming_solid_storage import _digest
    op=reacting_host(water)
    assert _digest(F(1,3)) != _digest(float(F(1,3)))
    config=op.base_model.solid_reactions
    reaction=config.network.reactions[0]
    changed=replace(config,network=replace(config.network,reactions=(replace(reaction,
        stoichiometry={'A':F(-1,3),'B':F(1,3)}),)))
    other=replace(op,base_model=replace(op.base_model,solid_reactions=changed))
    assert other.energy_model_identity!=op.energy_model_identity
    with pytest.raises(ValueError,match='fluid_available_volume'):
        op.state_from_temperatures([[0.,.01,0.,10.]],[300.],time_s=0.)


def test_component_schemas_do_not_mix_semantics():
    from sludge_sandbox.integration import Rates,IntegrationError
    zero=np.zeros(1)
    for keys in (('elastic_deformation','bulk_pressure'),('elastic','pore')):
        Rates(np.zeros((2,1)),np.zeros(2),np.zeros((1,1)),zero,{k:zero for k in keys})
    for keys in (('elastic','bulk_pressure'),('pore','interface_deformation')):
        with pytest.raises(IntegrationError,match='component_work_keys'):
            Rates(np.zeros((2,1)),np.zeros(2),np.zeros((1,1)),zero,{k:zero for k in keys})


def test_changed_inventory_updates_storage_energy_and_pore_volume(water,monkeypatch):
    forbid_eos(water,monkeypatch)
    op=reacting_host(water,constant=True)
    before=initial(op)
    changed=replace(before,amounts_mol=[[.2,.01,0.,1.8]])
    out=op.evaluate(changed,.5)
    sk=out.total_inverses[0].state.skeleton_state
    assert sk.interface_energy_j==pytest.approx(.3*(1+10*.2),abs=1e-14)
    assert out.storage_states[0].solid_volume_m3==pytest.approx(1.8*2e-5+.2*1e-5,abs=1e-18)
    # Δu_BA = -4 J/mol; composition energy is +3 J/mol, C is constant.
    expected=300.+(.2*4.-.2*3.)/(10.+.01*(30.-R))
    assert out.storage_states[0].mechanical.temperature_k==pytest.approx(expected,abs=1e-6,rel=0)
    assert out.rates.cell_power_w[0]==0.
    assert sk.interface_composition_derivative_j_mol['B']==pytest.approx(3.,abs=1e-14)


def scalar_temperature(t, y, *, constant):
    nb=2.*(1.-math.exp(-.1*t))
    nb_rate=.2*math.exp(-.1*t)
    # The existing motion contract is rest-to-rest cubic, not linear in time.
    lam=1. if constant else 1.-.1*t*t*(3.-2.*t)
    bulk=1.4e-4*lam
    volume_rate=0. if constant else -1.4e-5*6.*t*(1.-t)
    pore=bulk-((2.-nb)*2e-5+nb*1e-5)
    pressure=.01*R*y[0]/pore
    elastic0=1.4e-4*(1000./2.+2.*400./3.)*math.log(lam)**2
    # Chain rule removes only fixed-composition deformation power. Chemical
    # and composition-energy derivatives remain in thermal storage balance.
    return [(-pressure*volume_rate-(-4.+10.*(elastic0+.3))*nb_rate)/(10.+.01*(30.-R))]


@pytest.mark.parametrize('constant',[True,False])
def test_actual_reaction_motion_prefixes_and_independent_temperature(water,monkeypatch,constant):
    forbid_eos(water,monkeypatch)
    op=reacting_host(water,constant=constant)
    start=initial(op)
    end=1/8
    # Registered bounded trajectory: <=40 s, <=100 attempts, no wet EOS.
    run=integrate(start,op,start_s=0.,end_s=end,policy=IntegrationPolicy(
        initial_step_s=1/128,maximum_step_s=1/128,minimum_step_s=1e-10,
        relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-10,
        energy_absolute_tolerance_j=1e-6,amount_scale_mol=1.,energy_scale_j=1.,
        maximum_steps=100,maximum_rejections=20,maximum_wall_seconds=40))
    assert run.status=='completed',run.reason
    oracle=solve_ivp(lambda t,y:scalar_temperature(t,y,constant=constant),
        (0.,end),[300.],method='DOP853',rtol=1e-11,atol=1e-11,dense_output=True)
    assert oracle.success
    work=F()
    for t,state,step in zip(run.times_s[1:],run.states[1:],run.steps):
        row=state.amounts_mol[0]
        assert abs(F(float(row[0]))+F(float(row[3]))-2)<=F(1e-10)
        assert row[3]==pytest.approx(2.*math.exp(-.1*t),rel=0,abs=1e-9)
        assert row[1]==.01 and row[2]==0.
        assert np.all(step.face_species_mol==0.)
        work+=F(float(step.cell_work_j[0]))
        assert abs(F(float(state.internal_energy_j[0]))-F(float(start.internal_energy_j[0]))-work)<=F(1e-6)
        out=op.evaluate(state,t)
        assert out.storage_states[0].mechanical.temperature_k==pytest.approx(float(oracle.sol(t)[0]),rel=0,abs=2e-5)
        assert state.energy_model_identity==op.energy_model_identity
        if constant:
            assert step.cell_work_j[0]==0.
    assert run.states[-1].amounts_mol[0,0]>0.
