from dataclasses import replace
import math
import pytest

from sludge_sandbox.solid_reactions import SolidReactionConfig,ReactionSpeciesBinding,SolidReactionError
from sludge_sandbox.reactions import ReactionNetwork,ReactionDefinition,SpeciesDefinition
from sludge_sandbox.phase_storage import LiquidWaterPhase
from test_reactions import kinetics
from test_solid_fluid_heat import ingredients,solid_host


def config(ingredients,**kw):
    host=solid_host(ingredients)
    storage=host.storages[0]
    solid=replace(storage.solid_phases['fixture_solid'],molar_mass_kg_mol=.028)
    storage=replace(storage,solid_phases={'fixture_solid':solid})
    definitions=(SpeciesDefinition('solid_alias','solid',{'N':2},.028,('fixture:reaction',),'manufactured'),
        SpeciesDefinition('gas_alias','gas',{'N':2},.028,('fixture:reaction',),'manufactured'))
    law=kinetics({'solid_alias':2},gas_constant_j_mol_k=8.31446261815324,activation_energy_j_mol=1000.,temperature_range_k=(295.,310.))
    network=ReactionNetwork(definitions,(ReactionDefinition('transfer','1',{'solid_alias':-1,'gas_alias':1},law,'other',('fixture:reaction',)),),True)
    bindings=(ReactionSpeciesBinding('solid_alias','fixture_solid',solid),
        ReactionSpeciesBinding('gas_alias','fixture',storage.fluid_template.gas_phases['fixture']))
    values=dict(network=network,bindings=bindings,storages=(storage,),inventory_layout=host.inventory_layout,
        allow_manufactured=True,binding_id='fixture:binding',version='1',source_ids=('fixture:binding',))
    values.update(kw);return SolidReactionConfig(**values)


def test_actual_bulk_temperature_source_maps_aliases_and_preserves_inert(ingredients):
    c=config(ingredients)
    row=[2.,0.,0.,.01]
    decoded=c.storages[0].evaluate_at_temperature(300.,0.,{'fixture':.01,'H2O':0.},{'fixture_solid':2.})
    out=c.evaluate_cell(row,decoded,0)
    expected=2*math.exp(-1000/(8.31446261815324*300))*2**2/.0001
    assert out.network_rates.extent_mol_s[0]==pytest.approx(expected,rel=1e-12,abs=1e-8)
    assert out.source_mol_s==pytest.approx((-expected,0.,0.,expected),rel=1e-12,abs=1e-8)
    assert out.bulk_volume_m3==.0001
    assert out.temperature_k==300.
    assert not c.material_qualified
    assert c.contains_manufactured


def test_explicit_liquid_and_gas_water_aliases_are_distinct(ingredients):
    c=config(ingredients);storage=c.storages[0]
    mass=storage.fluid_template.mechanical.water.reference.molar_mass_kg_mol
    defs=(SpeciesDefinition('wet','liquid',{'H':2,'O':1},mass,('fixture:phase',),'manufactured'),
          SpeciesDefinition('vapor','gas',{'H':2,'O':1},mass,('fixture:phase',),'manufactured'))
    law=kinetics({'wet':1},gas_constant_j_mol_k=8.31446261815324,temperature_range_k=(295.,310.))
    net=ReactionNetwork(defs,(ReactionDefinition('phase','1',{'wet':-1,'vapor':1},law,'other',('fixture:phase',)),),True)
    bindings=(ReactionSpeciesBinding('wet','H2O_liquid',LiquidWaterPhase(storage.fluid_template.mechanical.water)),
              ReactionSpeciesBinding('vapor','H2O',storage.fluid_template.gas_phases['H2O']))
    c=replace(c,network=net,bindings=bindings)
    out=c.evaluate_cell([2.,1e-5,1.,.01],storage.evaluate_at_temperature(300.,1.,{'fixture':.01,'H2O':1e-5},{'fixture_solid':2.}),0)
    assert out.source_mol_s==pytest.approx((0.,2.,-2.,0.),rel=1e-12,abs=1e-12)
    with pytest.raises(SolidReactionError,match='phase'):
        replace(c,bindings=(replace(bindings[0],inventory_column_id='H2O'),replace(bindings[1],inventory_column_id='H2O_liquid')))


def test_binding_coverage_injectivity_and_provider_curve(ingredients):
    c=config(ingredients)
    with pytest.raises(SolidReactionError):replace(c,bindings=c.bindings[:1])
    with pytest.raises(SolidReactionError):replace(c,bindings=(c.bindings[0],replace(c.bindings[1],inventory_column_id='fixture_solid')))
    gas=c.bindings[1].provider
    bad=replace(gas,caloric=replace(gas.caloric,segments=(replace(gas.caloric.segments[0],coefficients=(31.,0.,0.,0.,0.,0.,0.,0.)),)))
    with pytest.raises(SolidReactionError,match='provider_identity'):
        replace(c,bindings=(c.bindings[0],replace(c.bindings[1],provider=bad)))


def test_gas_constant_and_mass_gate(ingredients):
    c=config(ingredients)
    rxn=c.network.reactions[0]
    net=replace(c.network,reactions=(replace(rxn,kinetics=replace(rxn.kinetics,gas_constant_j_mol_k=8.)),))
    with pytest.raises(SolidReactionError,match='gas_constant'):replace(c,network=net)
    defs=tuple(replace(s,molar_mass_kg_mol=.03) for s in c.network.species)
    with pytest.raises(SolidReactionError,match='mass'):replace(c,network=replace(c.network,species=defs))
    with pytest.raises(SolidReactionError,match='manufactured'):replace(c,allow_manufactured=False)


def test_decoded_inventory_mismatch_never_uses_stale_temperature(ingredients):
    c=config(ingredients)
    decoded=c.storages[0].evaluate_at_temperature(300.,0.,{'fixture':.01,'H2O':0.},{'fixture_solid':2.})
    with pytest.raises(SolidReactionError,match='decoded_inventory'):
        c.evaluate_cell([1.,0.,0.,.01],decoded,0)


def test_zero_reactant_and_kinetic_domain(ingredients):
    c=config(ingredients)
    decoded=c.storages[0].evaluate_at_temperature(300.,0.,{'fixture':.01,'H2O':0.},{'fixture_solid':0.})
    out=c.evaluate_cell([0.,0.,0.,.01],decoded,0)
    assert out.network_rates.extent_mol_s==(0.,)
    assert out.source_mol_s==(0.,)*4
    rxn=c.network.reactions[0]
    narrower=replace(c,network=replace(c.network,reactions=(replace(rxn,kinetics=replace(rxn.kinetics,temperature_range_k=(301.,310.))),)))
    with pytest.raises(SolidReactionError,match='kinetic_domain'):narrower.evaluate_cell([0.,0.,0.,.01],decoded,0)


@pytest.mark.parametrize('changes',[{'bindings':()},{'binding_id':''},{'version':''},{'source_ids':()},{'allow_manufactured':1}])
def test_explicit_binding_contract(ingredients,changes):
    with pytest.raises(SolidReactionError):config(ingredients,**changes)


def test_cross_cell_caloric_identity_is_checked(ingredients):
    c=config(ingredients)
    s=c.storages[0];p=s.solid_phases['fixture_solid']
    changed=replace(s,solid_phases={'fixture_solid':replace(p,molar_volume_m3_mol=p.molar_volume_m3_mol*2)})
    with pytest.raises(SolidReactionError,match='provider_identity'):
        replace(c,storages=(s,changed))


def test_public_evaluator_rejects_boolean_inventory_and_wrong_shape(ingredients):
    c=config(ingredients)
    d=c.storages[0].evaluate_at_temperature(300.,0.,{'fixture':.01,'H2O':0.},{'fixture_solid':2.})
    for row in ([True,0.,0.,.01],[2.,0.,.01],[2.,0.,0.,math.inf]):
        with pytest.raises(SolidReactionError):c.evaluate_cell(row,d,0)
