"""Thermochemical transcription checks and independent numerical identities.

NIST's tabulated values are rounded evaluations of its fit, not independent
experimental validation. Their tolerances below follow the printed precision.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from sludge_sandbox.thermochemistry import ThermochemistryError, load_thermochemistry


DATA = Path(__file__).resolve().parents[2] / 'data/sandbox/thermochemistry/nist_gases_v1.json'


@pytest.fixture
def thermo():
    return load_thermochemistry(DATA)


@pytest.mark.parametrize('species,temperature,cp,delta_h', [
    ('O2', 300, 29.39, 0.05), ('O2', 1000, 34.86, 22.70),
    ('O2', 3000, 39.87, 98.01), ('N2', 300, 29.12, 0.05),
    ('N2', 1000, 32.69, 21.46), ('N2', 3000, 37.03, 92.71),
    ('CO2', 500, 44.61, 8.31), ('CO2', 1500, 58.40, 61.71),
    ('H2O', 500, 35.22, 6.92), ('H2O', 2000, 51.20, 72.79),
])
def test_published_nist_table_points(thermo, species, temperature, cp, delta_h):
    gas = thermo.species(species)
    assert gas.cp_j_mol_k(temperature) == pytest.approx(cp, abs=0.0051)
    assert gas.enthalpy_j_mol(temperature) - gas.formation_enthalpy_298_j_mol == pytest.approx(
        delta_h * 1000, abs=5.1,
    )
    assert gas.source_ids


def test_formation_energy_is_included_and_not_a_second_heat_source(thermo):
    water = thermo.species('H2O')
    assert water.formation_enthalpy_298_j_mol == -241826.4
    assert water.enthalpy_j_mol(1000) == pytest.approx(-215826.4, abs=5.1)
    assert thermo.species('CO2').formation_enthalpy_298_j_mol == -393522.4


def test_gas_constant_matches_exact_si_definitions(thermo):
    # The exact N_A and k values are read from the CODATA 2022 source listing.
    assert thermo.gas_constant_j_mol_k == pytest.approx(6.02214076e23 * 1.380649e-23, abs=2e-15, rel=0)
    assert 'nist-codata-2022' in thermo.source_ids_for({'O2': 1})


@pytest.mark.parametrize('species,temperature', [('O2', 800), ('N2', 300), ('CO2', 1400), ('H2O', 700)])
def test_energy_derivatives_and_ideal_gas_identity(thermo, species, temperature):
    gas = thermo.species(species)
    epsilon = 0.002
    dh = (gas.enthalpy_j_mol(temperature + epsilon) - gas.enthalpy_j_mol(temperature - epsilon)) / (2 * epsilon)
    du = (gas.internal_energy_j_mol(temperature + epsilon) - gas.internal_energy_j_mol(temperature - epsilon)) / (2 * epsilon)
    assert dh == pytest.approx(gas.cp_j_mol_k(temperature), abs=2e-7)
    assert du == pytest.approx(gas.cv_j_mol_k(temperature), abs=2e-7)
    assert gas.enthalpy_j_mol(temperature) - gas.internal_energy_j_mol(temperature) == pytest.approx(
        thermo.gas_constant_j_mol_k * temperature, abs=1e-9,
    )


def test_mixture_energy_inversion_and_zero_water_domain(thermo):
    amounts = {'O2': 0.2, 'N2': 0.7, 'CO2': 0.06, 'H2O': 0.04}
    for temperature in (501, 800, 1500, 3000):
        energy = thermo.mixture_internal_energy_j(amounts, temperature)
        assert thermo.temperature_from_internal_energy_j(energy, amounts) == pytest.approx(temperature, abs=1e-8)
    # Known zero inventory does not impose a physical-property evaluation.
    amounts = {'O2': 1, 'H2O': 0}
    energy = thermo.mixture_internal_energy_j(amounts, 300)
    assert thermo.temperature_from_internal_energy_j(energy, amounts) == pytest.approx(300, abs=1e-8)


def test_tiny_inventory_does_not_make_absolute_energy_tolerance_accept_wrong_temperature(thermo):
    amounts = {'O2': 1e-30}
    energy = thermo.mixture_internal_energy_j(amounts, 380)
    assert thermo.temperature_from_internal_energy_j(energy, amounts) == pytest.approx(380, abs=1e-8)


@pytest.mark.parametrize('amount,temperature', [(1e-320, 1500), (5e-324, 380)])
def test_subnormal_energy_quantization_cannot_claim_temperature_accuracy(thermo, amount, temperature):
    amounts = {'O2': amount}
    energy = thermo.mixture_internal_energy_j(amounts, temperature)
    with pytest.raises(ThermochemistryError, match='insufficient_energy_resolution'):
        thermo.temperature_from_internal_energy_j(energy, amounts)


@pytest.mark.parametrize('species,temperature', [('H2O', 499.9), ('CO2', 297), ('O2', 6001), ('N2', 99)])
def test_no_temperature_extrapolation(thermo, species, temperature):
    with pytest.raises(ThermochemistryError, match='temperature_out_of_domain'):
        thermo.species(species).enthalpy_j_mol(temperature)


@pytest.mark.parametrize('amounts', [{}, {'O2': 0}, {'O2': -1}, {'O2': float('nan')}, {'O2': True}, {'unknown': 0}])
def test_invalid_or_undefined_inventory_is_rejected(thermo, amounts):
    with pytest.raises(ThermochemistryError):
        thermo.temperature_from_internal_energy_j(0, amounts)


def test_nonfinite_or_unreachable_energy_is_rejected(thermo):
    for energy in (float('nan'), float('inf'), True, 1e12, -1e12):
        with pytest.raises(ThermochemistryError):
            thermo.temperature_from_internal_energy_j(energy, {'O2': 1})


def test_finite_terms_overflowing_the_mixture_sum_have_structured_failure(thermo):
    with pytest.raises(ThermochemistryError, match='nonfinite_mixture_energy'):
        thermo.mixture_internal_energy_j({'O2': 6e302, 'N2': 6e302}, 6000)
    with pytest.raises(ThermochemistryError, match='nonfinite_mixture_energy'):
        thermo.mixture_internal_energy_j({'O2': 8e302, 'N2': 8e302}, 6000)


def test_original_shomate_seams_are_reported_without_smoothing(thermo):
    seams = thermo.species('CO2').seam_diagnostics()
    assert len(seams) == 1
    assert seams[0]['temperature_k'] == 1200
    assert seams[0]['cp_right_minus_left_j_mol_k'] != 0
    assert seams[0]['h_right_minus_left_j_mol'] != 0
    gas = thermo.species('CO2')
    assert gas.enthalpy_j_mol(1200) == gas.segments[1].enthalpy_j_mol(1200)


def _manufactured_pack(jump_j):
    # Two independently chosen caloric branches: cp=30 J/(mol K), hf=0.
    # These are constructed fixtures, never a real or measured material.
    pack = json.loads(DATA.read_text())
    species = deepcopy(pack['species'][0])
    species.update(species_id='fixture', classification='manufactured_test_fixture',
                   formation_enthalpy_298_j_mol=0, source_ids=['fixture:caloric'])
    species['segments'] = [
        {'temperature_range_k': [300, 500], 'coefficients': [30, 0, 0, 0, 0, 0, 0, 0], 'source_ids': ['fixture:caloric']},
        {'temperature_range_k': [500, 800], 'coefficients': [30, 0, 0, 0, 0, jump_j/1000, 0, 0], 'source_ids': ['fixture:caloric']},
    ]
    pack['species'] = [species]
    return pack


def test_manufactured_models_require_explicit_test_mode(tmp_path):
    path = tmp_path/'fixture.json'
    path.write_text(json.dumps(_manufactured_pack(0)))
    with pytest.raises(ThermochemistryError, match='manufactured_model_requires_test_mode'):
        load_thermochemistry(path)
    assert load_thermochemistry(path, allow_manufactured=True).species('fixture')


@pytest.mark.parametrize('jump,code', [(100, 'energy_in_property_gap'), (-100, 'ambiguous_temperature')])
def test_discontinuous_fit_gaps_and_overlaps_are_not_clamped(tmp_path, jump, code):
    path = tmp_path/'fixture.json'
    path.write_text(json.dumps(_manufactured_pack(jump)))
    gas = load_thermochemistry(path, allow_manufactured=True)
    energy = (30 - gas.gas_constant_j_mol_k) * 500 + jump/2
    with pytest.raises(ThermochemistryError, match=code):
        gas.temperature_from_internal_energy_j(energy, {'fixture': 1})


def test_nonpositive_heat_capacity_is_rejected_before_inversion(tmp_path):
    pack = _manufactured_pack(0)
    pack['species'][0]['segments'][0]['coefficients'][0] = 5
    path = tmp_path/'fixture.json'
    path.write_text(json.dumps(pack))
    with pytest.raises(ThermochemistryError, match='nonpositive_heat_capacity'):
        load_thermochemistry(path, allow_manufactured=True)


def test_loader_refuses_unit_ambiguity_and_duplicate_keys(tmp_path):
    pack = json.loads(DATA.read_text())
    pack['units']['enthalpy'] = 'kJ/mol'
    path = tmp_path/'bad.json'
    path.write_text(json.dumps(pack))
    with pytest.raises(ThermochemistryError, match='units'):
        load_thermochemistry(path)
    path.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(ThermochemistryError, match='duplicate_key'):
        load_thermochemistry(path)


def test_loader_does_not_ignore_unknown_fields(tmp_path):
    pack = json.loads(DATA.read_text())
    pack['species'][0]['silently_override_reference'] = 0
    path = tmp_path/'bad.json'
    path.write_text(json.dumps(pack))
    with pytest.raises(ThermochemistryError, match='schema_fields'):
        load_thermochemistry(path)


def test_heat_capacity_sign_change_between_positive_endpoints_is_rejected(tmp_path):
    pack = _manufactured_pack(0)
    pack['species'][0]['segments'] = [{
        'temperature_range_k': [300, 800],
        'coefficients': [292.5, -1100, 1000, 0, 0, 0, 0, 0],
        'source_ids': ['fixture:caloric'],
    }]
    path = tmp_path/'fixture.json'
    path.write_text(json.dumps(pack))
    with pytest.raises(ThermochemistryError, match='nonpositive_heat_capacity'):
        load_thermochemistry(path, allow_manufactured=True)


def test_manufactured_composition_change_heats_at_fixed_total_energy(tmp_path):
    pack = _manufactured_pack(0)
    reactant = pack['species'][0]
    product = deepcopy(reactant)
    product['species_id'] = 'product'
    product['formation_enthalpy_298_j_mol'] = -1000
    for segment in product['segments']:
        segment['coefficients'][5] = -1
        segment['coefficients'][7] = -1
    pack['species'].append(product)
    path = tmp_path/'reaction_fixture.json'
    path.write_text(json.dumps(pack))
    model = load_thermochemistry(path, allow_manufactured=True)
    initial_energy = model.mixture_internal_energy_j({'fixture': 1}, 400)
    expected = 400 + 1000/(30-model.gas_constant_j_mol_k)
    # No extra reaction-heat term: formation-energy change is already in U.
    actual = model.temperature_from_internal_energy_j(initial_energy, {'product': 1})
    assert actual == pytest.approx(expected, abs=1e-8)
