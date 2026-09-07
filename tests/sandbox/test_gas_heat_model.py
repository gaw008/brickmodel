"""Manufactured integration cases exercise the actual shared physical operators."""
from dataclasses import FrozenInstanceError, replace
import math
from pathlib import Path

import numpy as np
import pytest

from sludge_sandbox.gas_heat_model import GasHeatModel, GasHeatModelError
from sludge_sandbox.gas_transport import ideal_gas_reservoir
from sludge_sandbox.integration import ConservedState, DomainExit, IntegrationPolicy, integrate
from sludge_sandbox.reactions import ArrheniusMassAction, ReactionDefinition, ReactionNetwork, SpeciesDefinition
from sludge_sandbox.thermochemistry import ShomateGas, ShomateSegment, Thermochemistry, ThermochemistryError, load_thermochemistry


SOURCES = ('manufactured:gas-heat-integration-v1',)


def caloric(names=('A', 'B'), *, cp=30., formations=(0., -1000.)):
    gases = {}
    for name, formation in zip(names, formations):
        segment = ShomateSegment((300., 1800.), (cp, 0, 0, 0, 0, formation/1000-cp*.29815, 0, formation/1000),
                                 formation, 8., SOURCES)
        gases[name] = ShomateGas(name, (segment,), 'manufactured_test_fixture', SOURCES)
    return Thermochemistry('manufactured-continuous-cp-v1', gases, 8., SOURCES, allow_manufactured=True)


def model(**changes):
    values = dict(
        thermochemistry=caloric(), species_order=('A', 'B'),
        molar_masses_kg_mol={'A': .012, 'B': .012}, face_area_m2=1.,
        cell_widths_m=(1., 1.), gas_volumes_m3=(1., 1.),
        conductivities_w_m_k=(1., 1.),
        effective_diffusivities_m2_s={'A': (.1, .1), 'B': (.1, .1)},
        permeability_m2=(1e-5, 1e-5), relative_permeability=(1., 1.),
        viscosity_pa_s=(1., 1.), coefficient_source_ids=SOURCES,
        coefficient_set_id='manufactured-gas-heat-v1', coefficient_version='1',
        coefficient_classification='manufactured',
        allow_manufactured=True,
    )
    values.update(changes)
    return GasHeatModel(**values)


def policy(**changes):
    values = dict(initial_step_s=.01, maximum_step_s=.05, minimum_step_s=1e-10,
                  relative_tolerance=1e-6, amount_absolute_tolerance_mol=1e-10,
                  energy_absolute_tolerance_j=1e-8, amount_scale_mol=1.,
                  energy_scale_j=1000., maximum_steps=10000, maximum_rejections=1000,
                  maximum_wall_seconds=30.)
    values.update(changes)
    return IntegrationPolicy(**values)


def run(operator, initial, end=.3):
    result = integrate(initial, operator, start_s=0., end_s=end, policy=policy())
    assert result.status == 'completed', (result.status, result.reason)
    return result


def test_two_cells_close_energy_with_all_shared_mechanisms_and_controls():
    operator = model()
    initial = operator.state_from_temperatures([[.8, .2], [.3, 1.2]], [600., 900.])
    original = operator(initial, 0.)
    assert np.any(original.face_species_mol_s[1] != 0)
    assert original.face_energy_w[1] != 0
    assert np.all(original.face_species_mol_s[[0, -1]] == 0)
    assert np.all(original.face_energy_w[[0, -1]] == 0)
    result = run(operator, initial)
    final = result.states[-1]
    assert final.amounts_mol.sum(axis=0) == pytest.approx(initial.amounts_mol.sum(axis=0), abs=2e-12)
    assert math.fsum(final.internal_energy_j) == pytest.approx(math.fsum(initial.internal_energy_j), abs=2e-9)
    assert operator.temperatures_k(final) != pytest.approx((600, 900), abs=1e-3)
    # Independent source-free carbon and mass counts are both preserved.
    assert final.amounts_mol.sum() == pytest.approx(2.5, abs=2e-12)
    assert (final.amounts_mol*.012).sum() == pytest.approx(.03, abs=2e-14)
    no_flow = replace(operator, permeability_m2=(0, 0), effective_diffusivities_m2_s={'A': (0, 0), 'B': (0, 0)})
    no_heat = replace(operator, conductivities_w_m_k=(0, 0))
    flow_off = run(no_flow, initial).states[-1]
    heat_off = run(no_heat, initial).states[-1]
    assert np.array_equal(flow_off.amounts_mol, initial.amounts_mol)
    assert not np.allclose(final.amounts_mol, flow_off.amounts_mol, atol=1e-5)
    assert operator.temperatures_k(final) != pytest.approx(no_heat.temperatures_k(heat_off), abs=1e-3)
    for state in (flow_off, heat_off):
        assert math.fsum(state.internal_energy_j) == pytest.approx(math.fsum(initial.internal_energy_j), abs=2e-9)


def test_conduction_only_matches_two_lumped_cells_analytic_limit():
    operator = model(permeability_m2=(0, 0), effective_diffusivities_m2_s={'A': (0, 0), 'B': (0, 0)})
    initial = operator.state_from_temperatures([[1, 0], [1, 0]], [600, 1000])
    end = 2.
    final = run(operator, initial, end).states[-1]
    # Cv=30-8=22 J/K per cell, conductance=1 W/K.
    amplitude = 200*math.exp(-2*end/22)
    assert operator.temperatures_k(final) == pytest.approx((800-amplitude, 800+amplitude), abs=2e-4)


def test_diffusion_only_equal_thermochemistry_matches_binary_exponential():
    operator = model(thermochemistry=caloric(formations=(0, 0)), permeability_m2=(0, 0),
                     conductivities_w_m_k=(0, 0))
    initial = operator.state_from_temperatures([[.8, .2], [.2, .8]], [700, 700])
    end = 1.
    final = run(operator, initial, end).states[-1]
    contrast = .3*math.exp(-.2*end)
    assert final.amounts_mol == pytest.approx(np.array([[.5+contrast, .5-contrast], [.5-contrast, .5+contrast]]), abs=2e-6)
    assert operator.temperatures_k(final) == pytest.approx((700, 700), abs=1e-8)


def test_unequal_half_cells_use_resistances_and_correct_face_temperature():
    operator = model(cell_widths_m=(2, 4), gas_volumes_m3=(2, 4),
                     conductivities_w_m_k=(2, 8), permeability_m2=(2e-5, 8e-5),
                     relative_permeability=(.5, .25), viscosity_pa_s=(2, 4),
                     effective_diffusivities_m2_s={'A': (.2, .8), 'B': (.2, .8)})
    initial = operator.state_from_temperatures([[2, 0], [8, 0]], [600, 900])
    rates = operator(initial, 0.)
    # Pure species -> no diffusion. Face T=2/3*600+1/3*900=700.
    # Both mobilities=5e-6, dp/dx=(14400-4800)/3=3200.
    velocity = -5e-6*3200
    # Face p=8000 Pa and T=700 K -> c=10/7 mol/m3; wrong weights change c.
    # The right donor is pure A, so transported enthalpy is h_A(900).
    molar_flow = velocity*10/7
    conduction = (600-900)/(1/2+2/8)
    assert rates.face_species_mol_s[1, 0] == pytest.approx(molar_flow, rel=1e-10)
    assert rates.face_energy_w[1] == pytest.approx(conduction+molar_flow*operator.thermochemistry.species('A').enthalpy_j_mol(900), abs=1e-7)


def test_diffusivity_uses_both_half_cell_resistances_and_carries_formation_enthalpy():
    operator = model(cell_widths_m=(2, 4), gas_volumes_m3=(2, 4),
                     conductivities_w_m_k=(0, 0), permeability_m2=(0, 0),
                     effective_diffusivities_m2_s={'A': (.2, .8), 'B': (.2, .8)})
    initial = operator.state_from_temperatures([[1.6, .4], [.8, 3.2]], [700, 700])
    rates = operator(initial, 0)
    # D_face=3/(1/.2+2/.8)=.4, c_face=1; J_A=-.4*(.2-.8)/3=.08.
    assert rates.face_species_mol_s[1] == pytest.approx((.08, -.08), abs=1e-12)
    # h_A-h_B=1000 J/mol; there is no conduction or Darcy contribution.
    assert rates.face_energy_w[1] == pytest.approx(80, abs=1e-8)


def gas_reaction(thermo):
    identities = tuple(SpeciesDefinition(name, 'gas', {'C': 1}, .012, SOURCES, 'manufactured')
                       for name in ('A', 'B'))
    law = ArrheniusMassAction(
        'manufactured-A-to-B', '1', .2, 0, 1, 'current_cell_bulk_volume', {'A': 1},
        (300, 1800), thermo.gas_constant_j_mol_k, SOURCES, SOURCES, 'manufactured',
        'mol/(m^3 s)', 'J/mol', 'mol/m^3', 'J/(mol K)',
    )
    reaction = ReactionDefinition('A-to-B', '1', {'A': -1, 'B': 1}, law, 'other', SOURCES)
    return ReactionNetwork(identities, (reaction,), allow_manufactured=True)


def test_actual_balanced_gas_reaction_changes_temperature_at_fixed_energy():
    thermo = caloric()
    operator = model(thermochemistry=thermo, reaction_network=gas_reaction(thermo),
                     cell_widths_m=(1,), gas_volumes_m3=(1,), conductivities_w_m_k=(0,),
                     effective_diffusivities_m2_s={'A': (0,), 'B': (0,)},
                     permeability_m2=(0,), relative_permeability=(1,), viscosity_pa_s=(1,))
    initial = operator.state_from_temperatures([[1, 0]], [600])
    final = run(operator, initial, 1.).states[-1]
    converted = 1-math.exp(-.2)
    assert final.amounts_mol[0] == pytest.approx((1-converted, converted), abs=2e-6)
    assert final.internal_energy_j[0] == pytest.approx(initial.internal_energy_j[0], abs=1e-10)
    assert final.amounts_mol.sum() == pytest.approx(1, abs=1e-12)
    assert operator.temperatures_k(final)[0] == pytest.approx(600+1000*converted/22, abs=1e-4)
    inert_final = run(replace(operator, reaction_network=None), initial, 1.).states[-1]
    assert operator.temperatures_k(inert_final)[0] == pytest.approx(600, abs=1e-8)
    assert np.all(operator(initial, 0).cell_power_w == 0)


def test_explicit_outer_reservoir_uses_half_cell_without_invented_film():
    thermo = caloric(formations=(0, 0))
    reservoir = ideal_gas_reservoir(pressure_pa=8*800, temperature_k=800,
                                   mole_fractions={'A': 1, 'B': 0},
                                   molar_masses_kg_mol={'A': .012, 'B': .012}, gas_constant_j_mol_k=8)
    operator = model(thermochemistry=thermo, outer_reservoir=reservoir, outer_reservoir_source_ids=SOURCES,
                     conductivities_w_m_k=(0, 0))
    initial = operator.state_from_temperatures([[1, 0], [1, 0]], [600, 600])
    rates = operator(initial, 0)
    expected = -1e-5*(6400-4800)/.5  # boundary c=1 mol/m3
    assert rates.face_species_mol_s[-1, 0] == pytest.approx(expected)
    assert rates.face_energy_w[-1] == pytest.approx(expected*thermo.species('A').enthalpy_j_mol(800))
    result = run(operator, initial, .1)
    total_change = result.states[-1].internal_energy_j.sum()-initial.internal_energy_j.sum()
    outer_energy = -math.fsum(step.face_energy_j[-1] for step in result.steps)
    assert total_change == pytest.approx(outer_energy, abs=2e-9)


def test_prescribed_surface_temperature_is_a_half_cell_heat_boundary():
    operator = model(permeability_m2=(0, 0), effective_diffusivities_m2_s={'A': (0, 0), 'B': (0, 0)},
                     outer_surface_temperature_k=lambda time: 800+100*time, outer_heat_source_ids=SOURCES)
    initial = operator.state_from_temperatures([[1, 0], [1, 0]], [600, 600])
    assert operator(initial, .5).face_energy_w[-1] == pytest.approx((600-850)/.5, abs=1e-7)
    result = run(operator, initial, .1)
    change = result.states[-1].internal_energy_j.sum()-initial.internal_energy_j.sum()
    assert change == pytest.approx(-math.fsum(step.face_energy_j[-1] for step in result.steps), abs=2e-9)


def test_real_nist_seam_is_an_honest_domain_exit():
    thermo = load_thermochemistry(Path(__file__).resolve().parents[2]/'data/sandbox/thermochemistry/nist_gases_v1.json')
    gas = thermo.species('N2')
    energy = (gas.segments[0].internal_energy_j_mol(500)+gas.segments[1].internal_energy_j_mol(500))/2
    operator = model(thermochemistry=thermo, species_order=('N2',), molar_masses_kg_mol={'N2': .028},
                     cell_widths_m=(1,), gas_volumes_m3=(1,), conductivities_w_m_k=(0,),
                     effective_diffusivities_m2_s={'N2': (0,)}, permeability_m2=(0,),
                     relative_permeability=(1,), viscosity_pa_s=(1,))
    result = integrate(ConservedState([[1]], [energy]), operator, start_s=0, end_s=1, policy=policy())
    assert result.status == 'domain_exit' and 'energy_in_property_gap' in result.reason
    assert not result.steps


def test_state_domain_and_code_bug_are_distinct(monkeypatch):
    operator = model()
    with pytest.raises(DomainExit):
        operator(ConservedState([[0, 0], [1, 0]], [0, 100]), 0)
    with pytest.raises(GasHeatModelError):
        operator(ConservedState([[1]], [100]), 0)
    initial = operator.state_from_temperatures([[1, 0], [1, 0]], [600, 600])
    monkeypatch.setattr(operator.thermochemistry, 'temperature_from_internal_energy_j',
                        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('code_bug')))
    with pytest.raises(RuntimeError, match='code_bug'):
        operator(initial, 0)


@pytest.mark.parametrize('changes', [
    {'gas_volumes_m3': (0, 1)}, {'gas_volumes_m3': (2, 1)}, {'cell_widths_m': (True, 1)},
    {'face_area_m2': 0}, {'effective_diffusivities_m2_s': {'A': (.1, .1)}},
    {'conductivities_w_m_k': (-1, 1)}, {'viscosity_pa_s': (0, 1)},
    {'relative_permeability': (1.1, 1)}, {'coefficient_source_ids': ()},
    {'allow_manufactured': False},
])
def test_invalid_model_inputs_rejected(changes):
    with pytest.raises(GasHeatModelError):
        model(**changes)


def test_model_data_frozen_and_wrong_reaction_phase_rejected():
    data = {'A': [.1, .1], 'B': [.1, .1]}
    operator = model(effective_diffusivities_m2_s=data)
    data['A'][0] = 5
    assert operator.effective_diffusivities_m2_s['A'][0] == .1
    with pytest.raises(TypeError):
        operator.effective_diffusivities_m2_s['A'] = (3, 3)
    with pytest.raises(FrozenInstanceError):
        operator.face_area_m2 = 4
    net = gas_reaction(operator.thermochemistry)
    wrong = ReactionNetwork((replace(net.species[0], phase='solid'), net.species[1]), net.reactions, allow_manufactured=True)
    with pytest.raises(GasHeatModelError, match='gas_species'):
        model(reaction_network=wrong)
    assert operator.scientific_status == 'operator_integration_validation_not_material_qualified'


def test_mobility_factorization_cannot_silently_turn_nonzero_transport_off():
    operator = model(permeability_m2=(1e-300, 1e-300), relative_permeability=(1e-300, 1e-300),
                     viscosity_pa_s=(1e-300, 1e-300), conductivities_w_m_k=(0, 0),
                     effective_diffusivities_m2_s={'A': (0, 0), 'B': (0, 0)})
    initial = operator.state_from_temperatures([[1, 0], [1, 0]], [600, 900])
    with pytest.raises(GasHeatModelError, match='mobility_factorization_outside_float_range'):
        operator(initial, 0)


def test_thermochemistry_parameter_mutation_is_detected_before_a_step():
    operator = model()
    initial = operator.state_from_temperatures([[1, 0], [1, 0]], [600, 900])
    operator.thermochemistry.gas_constant_j_mol_k = 10
    with pytest.raises(GasHeatModelError, match='thermochemistry_changed_after_construction'):
        operator(initial, 0)


def test_inconsistent_species_and_energy_face_is_numerical_failure(monkeypatch):
    operator = model()
    initial = operator.state_from_temperatures([[.8, .2], [.2, .8]], [600, 900])
    original_face = GasHeatModel._face
    def inconsistent_face(self, *args):
        exchange = original_face(self, *args)
        return replace(exchange, net_mol_s={name: 0 for name in self.species_order})
    monkeypatch.setattr(GasHeatModel, '_face', inconsistent_face)
    result = integrate(initial, operator, start_s=0, end_s=1, policy=policy())
    assert result.status == 'numerical_failure'
    assert 'Inconsistent net species flow' in result.reason


@pytest.mark.parametrize('failure', ['temperature_inverse_not_converged', 'insufficient_energy_resolution'])
def test_thermochemistry_numerical_failure_is_not_material_domain_exit(monkeypatch, failure):
    operator = model()
    initial = operator.state_from_temperatures([[1, 0], [1, 0]], [600, 900])
    def fail(*args):
        raise ThermochemistryError(failure)
    monkeypatch.setattr(operator.thermochemistry, 'temperature_from_internal_energy_j', fail)
    result = integrate(initial, operator, start_s=0, end_s=1, policy=policy())
    assert result.status == 'numerical_failure'
    assert result.reason == failure
