"""Manufactured chemistry verifies bookkeeping, never a sludge mechanism."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import math

import numpy as np
import pytest

from sludge_sandbox.reactions import (
    ArrheniusMassAction, ReactionDefinition, ReactionError, ReactionNetwork,
    SpeciesDefinition,
)


TEST_SOURCE = ('manufactured:reaction-tests-v1',)


def species():
    # These deliberately rounded masses belong only to this manufactured set.
    return (
        SpeciesDefinition('feed', 'solid', {'C': 1, 'H': 4}, .016, TEST_SOURCE, 'manufactured'),
        SpeciesDefinition('char', 'solid', {'C': 1}, .012, TEST_SOURCE, 'manufactured'),
        SpeciesDefinition('oxygen', 'gas', {'O': 2}, .032, TEST_SOURCE, 'manufactured'),
        SpeciesDefinition('co2', 'gas', {'C': 1, 'O': 2}, .044, TEST_SOURCE, 'manufactured'),
        SpeciesDefinition('h2', 'gas', {'H': 2}, .002, TEST_SOURCE, 'manufactured'),
        SpeciesDefinition('water', 'gas', {'H': 2, 'O': 1}, .018, TEST_SOURCE, 'manufactured'),
    )


def kinetics(base_orders, **changes):
    values = dict(
        candidate_id='manufactured-kinetics', version='1',
        prefactor_mol_m3_s=2., activation_energy_j_mol=0.,
        concentration_reference_mol_m3=1., concentration_basis='current_cell_bulk_volume',
        orders=base_orders, temperature_range_k=(300., 1500.), gas_constant_j_mol_k=8.,
        constant_source_ids=TEST_SOURCE, source_ids=TEST_SOURCE, classification='manufactured',
        prefactor_unit='mol/(m^3 s)', activation_energy_unit='J/mol',
        concentration_unit='mol/m^3', gas_constant_unit='J/(mol K)',
    )
    values.update(changes)
    return ArrheniusMassAction(**values)


def reactions():
    return (
        ReactionDefinition('pyrolysis', '1', {'feed': -1, 'char': 1, 'h2': 2},
                           kinetics({'feed': 1}, candidate_id='pyrolysis-fixture'), 'oxygen_free_pyrolysis', TEST_SOURCE),
        ReactionDefinition('char-oxidation', '1', {'char': -1, 'oxygen': -1, 'co2': 1},
                           kinetics({'char': 1, 'oxygen': 1}, candidate_id='char-fixture'), 'oxygen_consuming', TEST_SOURCE),
        ReactionDefinition('hydrogen-oxidation', '1', {'h2': -2, 'oxygen': -1, 'water': 2},
                           kinetics({'h2': 2, 'oxygen': 1}, candidate_id='hydrogen-fixture'), 'oxygen_consuming', TEST_SOURCE),
    )


@pytest.fixture
def network():
    return ReactionNetwork(species(), reactions(), allow_manufactured=True)


def test_source_matrix_and_independent_conservation(network):
    assert network.species_order == ('feed', 'char', 'oxygen', 'co2', 'h2', 'water')
    assert network.reaction_order == ('pyrolysis', 'char-oxidation', 'hydrogen-oxidation')
    source = network.source_mol_s((.2, .1, .05))
    assert source == pytest.approx((-.2, .1, -.15, .1, .3, .1), abs=1e-15)
    # Element rows written independently of the operator's balancing code.
    for atoms in ((1, 1, 0, 1, 0, 0), (4, 0, 0, 0, 2, 2), (0, 0, 2, 2, 0, 1)):
        assert math.fsum(a*s for a, s in zip(atoms, source)) == pytest.approx(0, abs=1e-15)
    assert math.fsum(s*m for s, m in zip(source, (.016, .012, .032, .044, .002, .018))) == pytest.approx(0, abs=1e-17)
    assert network.stoichiometric_matrix[2] == (0., -1., -1.)


def test_exact_fractional_stoichiometry_is_supported():
    reaction = ReactionDefinition('half', '1', {'h2': -1, 'oxygen': Fraction(-1, 2), 'water': 1},
                                  kinetics({'h2': 1, 'oxygen': .5}), 'oxygen_consuming', TEST_SOURCE)
    net = ReactionNetwork(species(), (reaction,), allow_manufactured=True)
    assert net.source_mol_s((2,)) == (0, 0, -1, 0, -2, 2)


def test_elements_and_mass_are_separate_admission_gates():
    wrong_elements = replace(reactions()[0], stoichiometry={'feed': -1, 'char': 1, 'h2': 1})
    with pytest.raises(ReactionError, match='element_balance'):
        ReactionNetwork(species(), (wrong_elements,), allow_manufactured=True)
    changed = list(species())
    changed[3] = replace(changed[3], molar_mass_kg_mol=.045)
    with pytest.raises(ReactionError, match='mass_balance'):
        ReactionNetwork(changed, reactions(), allow_manufactured=True)


def test_anoxic_pyrolysis_and_zero_reactant_do_not_get_conflated(network):
    rates = network.rates(np.array([1., 0., 0., 0., 0., 0.]), 600., 2.)
    assert rates.extent_mol_s == pytest.approx((2., 0., 0.))
    assert rates.source_mol_s == pytest.approx((-2., 2., 0., 0., 4., 0.))
    assert network.rates((0., 1., 0., 0., 1., 0.), 600., 2.).extent_mol_s == (0., 0., 0.)
    assert not hasattr(rates, 'heat_source_w')


def test_normalized_mass_action_arrhenius_and_volume_are_explicit():
    law = kinetics({'char': .5, 'oxygen': 1.5}, prefactor_mol_m3_s=3.,
                   activation_energy_j_mol=4000., concentration_reference_mol_m3=2.)
    reaction = replace(reactions()[1], kinetics=law)
    net = ReactionNetwork(species(), (reaction,), allow_manufactured=True)
    # c_char/c_ref=1, c_O2/c_ref=4; Ea/(R*T)=1.
    rates = net.rates((0, 4, 16, 0, 0, 0), 500, 2)
    assert rates.extent_mol_s[0] == pytest.approx(3*math.exp(-1)*4**1.5*2, rel=1e-13)


def test_joint_oxygen_consumption_limits_all_reactions_together(network):
    amounts = (0., 10., .15, 0., 10., 0.)
    extents = (0., .1, .05)
    assert network.maximum_forward_step_s(amounts, extents) == pytest.approx(1.)
    remaining = network.amounts_after_extents(amounts, (0., .05, .025))
    assert remaining == pytest.approx((0., 9.95, .075, .05, 9.95, .05))
    with pytest.raises(ReactionError, match='insufficient_inventory'):
        network.amounts_after_extents(amounts, (0., .1, .1))
    # Products from one simultaneous proposal cannot erase an initial deficit.
    with pytest.raises(ReactionError, match='insufficient_inventory'):
        network.amounts_after_extents((1, 0, 1, 0, 0, 0), (.1, .1, 0))
    assert network.maximum_forward_step_s(amounts, (0, 0, 0)) == math.inf


@pytest.mark.parametrize('values', [(1, -1, 0), (1, math.nan, 0), (math.inf, 0, 0), (True, 0, 0), (1,), {'pyrolysis': 1}])
def test_invalid_extents_rejected(network, values):
    with pytest.raises(ReactionError):
        network.source_mol_s(values)


@pytest.mark.parametrize('values', [(1, -1, 0, 0, 0, 0), (1, 0, math.nan, 0, 0, 0), (True, 0, 0, 0, 0, 0), (1,)])
def test_invalid_inventory_rejected(network, values):
    with pytest.raises(ReactionError):
        network.rates(values, 600, 1)


@pytest.mark.parametrize('temperature,volume', [(299, 1), (1501, 1), (math.nan, 1), (600, 0), (600, -1)])
def test_state_outside_rate_domain_rejected(network, temperature, volume):
    with pytest.raises(ReactionError):
        network.rates((1, 1, 1, 0, 1, 0), temperature, volume)


def test_unknown_species_and_orders_cannot_silently_drop():
    with pytest.raises(ReactionError, match='unknown_species'):
        ReactionNetwork(species(), (replace(reactions()[0], stoichiometry={'unknown': -1, 'char': 1}),),
                        allow_manufactured=True)
    with pytest.raises(ReactionError, match='orders_must_cover_reactants'):
        ReactionNetwork(species(), (replace(reactions()[1], kinetics=kinetics({'char': 1})),),
                        allow_manufactured=True)


def test_oxygen_pathway_labels_are_checked_from_explicit_identity():
    with pytest.raises(ReactionError, match='oxygen_free_pathway_consumes_oxygen'):
        ReactionNetwork(species(), (replace(reactions()[1], pathway='oxygen_free_pyrolysis'),),
                        allow_manufactured=True)
    with pytest.raises(ReactionError, match='oxygen_consuming_pathway_requires_oxygen'):
        ReactionNetwork(species(), (replace(reactions()[0], pathway='oxygen_consuming'),),
                        allow_manufactured=True)


def test_manufactured_requires_explicit_mode_and_never_claims_material_qualification():
    with pytest.raises(ReactionError, match='manufactured_requires_test_mode'):
        ReactionNetwork(species(), reactions())
    net = ReactionNetwork(species(), reactions(), allow_manufactured=True)
    assert net.scientific_status == 'manufactured_not_material_qualified'
    assert not net.material_qualified
    assert set(net.source_ids) == set(TEST_SOURCE)


def test_literature_candidate_metadata_is_not_a_qualification_award():
    declared = [replace(item, classification='literature_candidate') for item in species()]
    paths = [replace(item, kinetics=replace(item.kinetics, classification='literature_candidate'))
             for item in reactions()]
    net = ReactionNetwork(declared, paths)
    assert net.scientific_status == 'candidate_sources_not_resolved_not_material_qualified'
    assert not net.material_qualified


@pytest.mark.parametrize('changes', [
    {'phase': 'unknown'}, {'elements': {'H2O': 1}}, {'elements': {'C': .5}},
    {'elements': {'C': True}}, {'elements': {}}, {'molar_mass_kg_mol': 0},
    {'molar_mass_kg_mol': math.nan}, {'source_ids': ()}, {'classification': 'validated'},
])
def test_invalid_species_definition_rejected(changes):
    with pytest.raises(ReactionError):
        replace(species()[0], **changes)


@pytest.mark.parametrize('changes', [
    {'source_ids': ()}, {'version': ''}, {'orders': {'char': -1}},
    {'prefactor_unit': '1/s'}, {'concentration_basis': 'unknown'},
    {'activation_energy_j_mol': math.inf}, {'concentration_reference_mol_m3': 0},
    {'gas_constant_j_mol_k': 0}, {'temperature_range_k': (0, 1000)},
])
def test_incomplete_or_invalid_candidate_is_rejected(changes):
    with pytest.raises(ReactionError):
        kinetics({'char': 1}, **changes)


def test_data_is_copied_and_deeply_frozen(network):
    elements = {'C': 1}
    item = SpeciesDefinition('c', 'solid', elements, .012, list(TEST_SOURCE), 'manufactured')
    elements['H'] = 2
    assert dict(item.elements) == {'C': 1}
    with pytest.raises(TypeError):
        item.elements['H'] = 2
    with pytest.raises(TypeError):
        network.reactions[0].stoichiometry['feed'] = -2
    with pytest.raises(TypeError):
        network.reactions[0].kinetics.orders['feed'] = 2
    with pytest.raises(FrozenInstanceError):
        network.species = ()


def test_reused_candidate_id_version_cannot_name_different_parameter_sets():
    paths = reactions()
    changed = replace(paths[1], kinetics=replace(paths[1].kinetics,
                                                candidate_id=paths[0].kinetics.candidate_id))
    with pytest.raises(ReactionError, match='conflicting_candidate_identity'):
        ReactionNetwork(species(), (paths[0], changed), allow_manufactured=True)


def test_source_product_underflow_does_not_silently_destroy_atoms():
    reaction = ReactionDefinition('half', '1', {'h2': -1, 'oxygen': -.5, 'water': 1},
                                  kinetics({'h2': 1, 'oxygen': .5}), 'oxygen_consuming', TEST_SOURCE)
    net = ReactionNetwork(species(), (reaction,), allow_manufactured=True)
    with pytest.raises(ReactionError, match='source_outside_float_range'):
        net.source_mol_s((5e-324,))


@pytest.mark.parametrize('inventory,extent', [(1e20, 1), (1e16, 3)])
def test_inventory_resolution_cannot_create_products_without_matching_consumption(network, inventory, extent):
    with pytest.raises(ReactionError, match='unresolvable_inventory_increment'):
        network.amounts_after_extents((inventory, 0, 0, 0, 0, 0), (extent, 0, 0))


def test_overflow_and_underflow_have_explicit_failure(network):
    with pytest.raises(ReactionError, match='nonfinite'):
        network.source_mol_s((1e308, 0, 0))
    huge = replace(reactions()[1], kinetics=kinetics({'char': 10, 'oxygen': 10}, prefactor_mol_m3_s=1e308))
    with pytest.raises(ReactionError, match='rate_outside_float_range'):
        ReactionNetwork(species(), (huge,), allow_manufactured=True).rates((0, 10, 10, 0, 0, 0), 600, 1)
    tiny = replace(reactions()[1], kinetics=kinetics({'char': 1, 'oxygen': 1}, activation_energy_j_mol=1e12))
    with pytest.raises(ReactionError, match='rate_outside_float_range'):
        ReactionNetwork(species(), (tiny,), allow_manufactured=True).rates((0, 1, 1, 0, 0, 0), 600, 1)
