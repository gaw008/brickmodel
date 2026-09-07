"""Manufactured face/boundary conditions; gas fit arithmetic uses the sourced NIST pack."""

from pathlib import Path
from dataclasses import replace

import pytest

from sludge_sandbox.exchanges import ExchangeError, boundary_heat, conduction_rate_w, gas_enthalpy_exchange
from sludge_sandbox.gas_transport import face_exchange, ideal_gas_reservoir
from sludge_sandbox.thermochemistry import load_thermochemistry


def test_conduction_respects_series_resistances_and_shared_face_sign():
    # Two manufactured layers: resistance = 0.1/2 + 0.3/6 = 0.1 m2 K/W.
    arguments = dict(area_m2=0.4, left_distance_m=0.1, right_distance_m=0.3,
                     left_conductivity_w_m_k=2, right_conductivity_w_m_k=6)
    assert conduction_rate_w(400, 300, **arguments) == pytest.approx(400)
    assert conduction_rate_w(300, 400, **arguments) == pytest.approx(-400)
    arguments["right_conductivity_w_m_k"] = 0
    assert conduction_rate_w(400, 300, **arguments) == 0


def test_boundary_uses_separate_gas_and_radiative_ambient_temperatures():
    result = boundary_heat(surface_temperature_k=400, gas_temperature_k=500,
                           radiation_temperature_k=300, area_m2=0.2,
                           convection_w_m2_k=10, emissivity=0.8, stefan_boltzmann_w_m2_k4=1e-8)
    assert result.convective_in_w == pytest.approx(200)
    assert result.radiative_in_w == pytest.approx(-28)
    assert result.total_in_w == pytest.approx(172)


@pytest.mark.parametrize("bad", [None, True, float("nan"), float("inf"), -1])
def test_invalid_thermal_input_is_rejected(bad):
    with pytest.raises(ExchangeError):
        conduction_rate_w(bad, 300, area_m2=1, left_distance_m=1, right_distance_m=1,
                          left_conductivity_w_m_k=1, right_conductivity_w_m_k=1)


def gas_case(thermo, constant=None):
    # Molar masses/transport coefficients are explicit manufactured test values.
    args = dict(molar_masses_kg_mol={"O2": 0.032, "N2": 0.028},
                gas_constant_j_mol_k=thermo.gas_constant_j_mol_k if constant is None else constant)
    left = ideal_gas_reservoir(pressure_pa=110000, temperature_k=600,
                               mole_fractions={"O2": 0.2, "N2": 0.8}, **args)
    right = ideal_gas_reservoir(pressure_pa=100000, temperature_k=800,
                                mole_fractions={"O2": 0.8, "N2": 0.2}, **args)
    return face_exchange(left, right, area_m2=0.1, distance_m=0.01, face_left_weight=0.5,
                         effective_diffusivities_m2_s={"O2": 1e-5, "N2": 2e-5},
                         permeability_m2=1e-14, relative_permeability=1, viscosity_pa_s=1e-5)


def test_diffusion_and_advection_use_their_respective_enthalpy_temperatures():
    path = Path(__file__).resolve().parents[2]/"data/sandbox/thermochemistry/nist_gases_v1.json"
    thermo = load_thermochemistry(path)
    gas = gas_case(thermo)
    result = gas_enthalpy_exchange(gas, thermo)
    expected_diffusion = sum(rate * thermo.species(k).enthalpy_j_mol(700)
                             for k, rate in gas.diffusive_mol_s.items())
    expected_advection = sum(rate * thermo.species(k).enthalpy_j_mol(600)
                             for k, rate in gas.advective_mol_s.items())
    assert result.diffusive_w == pytest.approx(expected_diffusion)
    assert result.advective_w == pytest.approx(expected_advection)
    assert result.total_w == pytest.approx(expected_diffusion + expected_advection)
    assert result.thermochemistry_source_ids
    assert result.provenance_status == "source_links_declared_not_registry_validated"
    with pytest.raises(ExchangeError, match="gas constant"):
        gas_enthalpy_exchange(gas_case(thermo, constant=9), thermo)


def test_net_species_flow_must_match_the_energy_bearing_components():
    path = Path(__file__).resolve().parents[2]/"data/sandbox/thermochemistry/nist_gases_v1.json"
    thermo = load_thermochemistry(path)
    gas = replace(gas_case(thermo), net_mol_s={"O2": 0, "N2": 0})
    with pytest.raises(ExchangeError, match="net species"):
        gas_enthalpy_exchange(gas, thermo)


def test_overflowing_opposite_enthalpy_rates_give_structured_failure():
    path = Path(__file__).resolve().parents[2]/"data/sandbox/thermochemistry/nist_gases_v1.json"
    thermo = load_thermochemistry(path)
    rates = {"O2": 1e308, "N2": -1e308}
    gas = replace(gas_case(thermo), net_mol_s=rates, diffusive_mol_s=rates,
                  advective_mol_s={"O2": 0, "N2": 0})
    with pytest.raises(ExchangeError):
        gas_enthalpy_exchange(gas, thermo)
