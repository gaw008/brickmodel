"""Manufactured verification cases; these values do not define a sludge material."""

import math

import pytest

from sludge_sandbox.gas_transport import (
    GasTransportError,
    face_exchange,
    ideal_gas_reservoir,
    ideal_gas_state,
)


# Intentionally manufactured constants, species masses and transport coefficients.
R = 8.0
MASSES = {"O2": 0.04, "N2": 0.02, "product": 0.01}
FACE = dict(
    area_m2=0.25,
    distance_m=0.5,
    face_left_weight=0.5,
    effective_diffusivities_m2_s={"O2": 0.1, "N2": 0.2, "product": 0.3},
    permeability_m2=0.01,
    relative_permeability=0.2,
    viscosity_pa_s=0.5,
)


def state(inventory, *, temperature=300.0, volume=1.0, masses=MASSES, gas_constant=R):
    return ideal_gas_state(
        inventory,
        temperature_k=temperature,
        gas_volume_m3=volume,
        molar_masses_kg_mol=masses,
        gas_constant_j_mol_k=gas_constant,
    )


def test_ideal_state_uses_carrier_inventory_and_current_gas_volume():
    inventory = {"O2": 0.0, "N2": 3.0, "product": 1.0}
    gas = state(inventory, volume=2.0)
    assert gas.pressure_pa == pytest.approx(4800.0)
    assert gas.density_kg_m3 == pytest.approx(0.035)
    assert gas.mole_fractions == pytest.approx({"O2": 0, "N2": 0.75, "product": 0.25})
    assert gas.mass_fractions == pytest.approx({"O2": 0, "N2": 6 / 7, "product": 1 / 7})
    assert state(inventory, volume=1.0).pressure_pa == pytest.approx(2 * gas.pressure_pa)
    assert state(inventory, temperature=600.0, volume=2.0).pressure_pa == pytest.approx(2 * gas.pressure_pa)
    inventory["N2"] = 100.0
    assert gas.concentrations_mol_m3["N2"] == 1.5
    with pytest.raises(TypeError):
        gas.mole_fractions["N2"] = 0


def test_equal_pressure_oxygen_free_counterdiffusion_conserves_mass_not_moles():
    left = state({"O2": 0.0, "N2": 3.0, "product": 1.0})
    right = state({"O2": 0.0, "N2": 1.0, "product": 3.0})
    flow = face_exchange(left, right, **FACE)
    assert flow.darcy_velocity_m_s == 0
    assert flow.advective_donor is None
    assert all(value == 0 for value in flow.advective_mol_s.values())
    assert flow.net_mol_s["O2"] == 0
    assert flow.net_direction["N2"] == "left_to_right"
    assert flow.net_direction["product"] == "right_to_left"
    assert flow.net_direction["O2"] == "stationary"
    # Independent hand calculation: c=4 and j*=(0,.016,-.012) kg/m2/s.
    # Sum j*=.004 => correction drifts right to left, Yright=(0,.4,.6).
    # Upwind-corrected j=(0,.0144,-.0144), replacing the unsafe central discretization.
    assert flow.diffusive_mol_s == pytest.approx({"O2": 0, "N2": 0.18, "product": -0.36})
    assert flow.diffusion_correction_donor == "right"
    assert flow.diffusion_correction_velocity_m_s < 0
    assert math.fsum(MASSES[k] * flow.diffusive_mol_s[k] for k in MASSES) == pytest.approx(0, abs=1e-17)
    assert math.fsum(flow.diffusive_mol_s.values()) != pytest.approx(0)


@pytest.mark.parametrize("reverse", [False, True])
def test_symmetric_binary_diffusivities_do_not_extract_an_empty_species(reverse):
    """Review P1 regression: positive symmetric binary D also triggers the old defect."""
    masses = {"A": 0.02, "B": 0.02, "C": 0.02}
    inventories = [{"A": 0.0, "B": 0.9, "C": 0.1}, {"A": 0.1, "B": 0.1, "C": 0.8}]
    if reverse:
        inventories.reverse()
    left, right = (state(n, masses=masses) for n in inventories)
    # Cantera getMixDiffCoeffs convention for equal molecular weights:
    # D'_k = (1-X_k) / sum_{j!=k}(X_j/D_kj), at Xface=(.05,.5,.45).
    face_x = {k: (left.mole_fractions[k] + right.mole_fractions[k]) / 2 for k in masses}
    binary = {frozenset(("A", "B")): 0.01, frozenset(("A", "C")): 1.0,
              frozenset(("B", "C")): 1.0}
    diffusion = {k: (1 - face_x[k]) / math.fsum(
        face_x[j] / binary[frozenset((k, j))] for j in masses if j != k) for k in masses}
    flow = face_exchange(left, right, area_m2=1, distance_m=1, face_left_weight=0.5,
                         effective_diffusivities_m2_s=diffusion, permeability_m2=0,
                         relative_permeability=1, viscosity_pa_s=1)
    assert flow.net_mol_s["A"] >= 0 if reverse else flow.net_mol_s["A"] <= 0
    assert math.fsum(masses[k] * flow.diffusive_mol_s[k] for k in masses) == pytest.approx(0, abs=1e-17)
    # Empty-side correction donor contains no A, leaving its inward base diffusion.
    assert flow.diffusive_mol_s["A"] == pytest.approx((1 if reverse else -1) * diffusion["A"] * 0.1)
    assert flow.diffusion_correction_donor == ("right" if reverse else "left")


@pytest.mark.parametrize("empty_species", MASSES)
@pytest.mark.parametrize("empty_side", ["left", "right"])
@pytest.mark.parametrize("permeability", [0, 0.01])
def test_zero_inventory_boundary_derivative_is_inward_with_diffusion_and_darcy(
        empty_species, empty_side, permeability):
    left_inventory = {"O2": 0.1, "N2": 0.9, "product": 0.1}
    right_inventory = {"O2": 0.6, "N2": 0.2, "product": 0.8}
    (left_inventory if empty_side == "left" else right_inventory)[empty_species] = 0
    left = state(left_inventory, temperature=310, volume=0.7)
    right = state(right_inventory, temperature=500, volume=1.1)
    flow = face_exchange(left, right, **(FACE | {"permeability_m2": permeability, "face_left_weight": 0.3}))
    for rates in (flow.diffusive_mol_s, flow.advective_mol_s, flow.net_mol_s):
        inventory_derivative = rates[empty_species] * (-1 if empty_side == "left" else 1)
        assert inventory_derivative >= 0
    assert math.fsum(MASSES[k] * flow.diffusive_mol_s[k] for k in MASSES) == pytest.approx(0, abs=1e-17)


def test_non_midpoint_face_reversal_preserves_state_and_reverses_every_rate():
    left = state({"O2": 0.0, "N2": 0.9, "product": 0.1}, temperature=310, volume=0.7)
    right = state({"O2": 0.6, "N2": 0.2, "product": 0.8}, temperature=500, volume=1.1)
    flow = face_exchange(left, right, **(FACE | {"face_left_weight": 0.3}))
    reverse = face_exchange(right, left, **(FACE | {"face_left_weight": 0.7}))
    assert flow.face_temperature_k == pytest.approx(reverse.face_temperature_k)
    assert flow.face_density_kg_m3 == pytest.approx(reverse.face_density_kg_m3)
    for field in ("diffusive_mol_s", "advective_mol_s", "net_mol_s"):
        assert getattr(reverse, field) == pytest.approx({k: -v for k, v in getattr(flow, field).items()})
    assert reverse.diffusion_correction_velocity_m_s == pytest.approx(-flow.diffusion_correction_velocity_m_s)
    assert reverse.diffusion_correction_donor != flow.diffusion_correction_donor


def test_upwind_correction_converges_at_first_order_to_the_continuum_mass_frame_flux():
    masses = {"A": 0.02, "B": 0.02, "C": 0.02}
    center_x = {"A": 0.2, "B": 0.3, "C": 0.5}
    slope = {"A": 0.1, "B": -0.2, "C": 0.1}
    diffusion = {"A": 0.01, "B": 0.1, "C": 1.0}
    # At c=1 and equal M: F_k=-D_k X'_k + X_k sum(D_i X'_i), evaluated at x=0.
    continuum = {"A": 0.0152, "B": 0.0443, "C": -0.0595}
    errors = []
    for spacing in (1.0, 0.5, 0.25, 0.125):
        left = state({k: center_x[k] - spacing / 2 * slope[k] for k in masses}, masses=masses)
        right = state({k: center_x[k] + spacing / 2 * slope[k] for k in masses}, masses=masses)
        flow = face_exchange(left, right, area_m2=1, distance_m=spacing, face_left_weight=0.5,
                             effective_diffusivities_m2_s=diffusion, permeability_m2=0,
                             relative_permeability=1, viscosity_pa_s=1)
        errors.append(max(abs(flow.diffusive_mol_s[k] - continuum[k]) for k in masses))
        assert math.fsum(masses[k] * flow.diffusive_mol_s[k] for k in masses) == pytest.approx(0, abs=1e-17)
    assert errors == pytest.approx([0.0081, 0.00405, 0.002025, 0.0010125])


def test_same_composition_pressure_gradient_drives_darcy_and_reverses():
    left = state({"O2": 1.0, "N2": 3.0, "product": 0.0})
    right = state({"O2": 0.5, "N2": 1.5, "product": 0.0})
    flow = face_exchange(left, right, **FACE)
    assert all(value == 0 for value in flow.diffusive_mol_s.values())
    assert flow.darcy_velocity_m_s == pytest.approx(38.4)
    assert flow.advective_mol_s == pytest.approx({"O2": 7.2, "N2": 21.6, "product": 0})
    assert flow.advective_donor == "left"
    reverse = face_exchange(right, left, **FACE)
    assert reverse.advective_donor == "right"
    assert reverse.net_mol_s == pytest.approx({k: -v for k, v in flow.net_mol_s.items()})


def test_reservoir_inflow_uses_reservoir_composition_and_donor_temperature():
    interior = state({"O2": 0, "N2": 2, "product": 0})
    reservoir = ideal_gas_reservoir(
        pressure_pa=9600,
        temperature_k=600,
        mole_fractions={"O2": 0.25, "N2": 0.75, "product": 0},
        molar_masses_kg_mol=MASSES,
        gas_constant_j_mol_k=R,
    )
    flow = face_exchange(interior, reservoir, **FACE)
    assert flow.advective_donor == "right"
    assert flow.advective_donor_temperature_k == 600
    assert flow.advective_mol_s["O2"] < 0
    assert flow.advective_mol_s["N2"] / flow.advective_mol_s["O2"] == pytest.approx(3)
    assert flow.face_temperature_k == 450
    assert flow.gas_constant_j_mol_k == R
    assert reservoir.pressure_pa == pytest.approx(9600)


def test_all_species_inventory_exchange_is_conservative_and_updates_pressure():
    inventories = [{"O2": 1.0, "N2": 3.0, "product": 2.0}, {"O2": 2.0, "N2": 1.0, "product": 1.0}]
    initial = [state(n) for n in inventories]
    flow = face_exchange(*initial, **FACE)
    assert math.fsum(MASSES[k] * flow.diffusive_mol_s[k] for k in MASSES) == pytest.approx(0, abs=1e-17)
    dt = 1e-5
    updated = [{k: n[k] + sign * dt * flow.net_mol_s[k] for k in MASSES}
               for n, sign in zip(inventories, (-1, 1), strict=True)]
    for k in MASSES:
        assert updated[0][k] + updated[1][k] == pytest.approx(inventories[0][k] + inventories[1][k])
        assert flow.net_mol_s[k] == pytest.approx(flow.diffusive_mol_s[k] + flow.advective_mol_s[k])
    assert all(value > 0 for n in updated for value in n.values())
    assert state(updated[0]).pressure_pa < initial[0].pressure_pa
    assert state(updated[1]).pressure_pa > initial[1].pressure_pa


def test_zero_transport_is_exactly_sealed_without_inventory_clipping():
    left = state({"O2": 0, "N2": 3, "product": 1})
    right = state({"O2": 1, "N2": 1, "product": 0})
    options = FACE | {"permeability_m2": 0, "effective_diffusivities_m2_s": dict.fromkeys(MASSES, 0)}
    flow = face_exchange(left, right, **options)
    assert all(v == 0 for v in flow.net_mol_s.values())


def test_species_mapping_order_is_irrelevant_and_single_species_has_no_diffusion():
    inventory = {"O2": 1.0, "N2": 3.0, "product": 2.0}
    left = state(inventory)
    reordered = state(dict(reversed(list(inventory.items()))))
    assert all(v == 0 for v in face_exchange(left, reordered, **FACE).net_mol_s.values())
    pure_left = state({"carrier": 2}, masses={"carrier": 0.02})
    pure_right = state({"carrier": 1}, masses={"carrier": 0.02})
    flow = face_exchange(pure_left, pure_right,
                         **(FACE | {"effective_diffusivities_m2_s": {"carrier": 0.1}}))
    assert flow.diffusive_mol_s["carrier"] == 0
    # Independent isothermal compressible Darcy solution has flux proportional to pL^2-pR^2.
    analytic_rate = FACE["area_m2"] * FACE["permeability_m2"] * FACE["relative_permeability"]
    analytic_rate *= (pure_left.pressure_pa**2 - pure_right.pressure_pa**2)
    analytic_rate /= 2 * FACE["viscosity_pa_s"] * FACE["distance_m"] * R * 300
    assert flow.net_mol_s["carrier"] == pytest.approx(analytic_rate)


def test_external_interpolation_weight_controls_face_state():
    left = state({"O2": 1, "N2": 3, "product": 0}, temperature=300)
    right = state({"O2": 1, "N2": 1, "product": 0}, temperature=600)
    flow = face_exchange(left, right, **(FACE | {"face_left_weight": 0.25}))
    assert flow.face_temperature_k == pytest.approx(525)
    # Both pressures 9600, Xface O2=.4375, Mbar=.02875.
    assert flow.face_density_kg_m3 == pytest.approx(9600 / (R * 525) * 0.02875)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "1", 10**1000])
@pytest.mark.parametrize("field", ["volume", "temperature", "gas_constant"])
def test_invalid_pore_volume_temperature_or_gas_constant_is_rejected(field, value):
    with pytest.raises(GasTransportError):
        state({"O2": 1, "N2": 3, "product": 0}, **{field: value})


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), True, "1", 10**1000])
def test_invalid_inventory_is_not_clipped(bad):
    with pytest.raises(GasTransportError):
        state({"O2": bad, "N2": 3, "product": 0})


def test_empty_or_vacuum_state_and_missing_carrier_are_rejected():
    for inventory in ({}, dict.fromkeys(MASSES, 0), {"O2": 1, "product": 0}):
        with pytest.raises(GasTransportError):
            state(inventory)


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), True, "1"])
def test_invalid_molar_mass_is_rejected(bad):
    with pytest.raises(GasTransportError):
        state({"O2": 1, "N2": 3, "product": 0}, masses=MASSES | {"O2": bad})


@pytest.mark.parametrize("field,value", [
    ("area_m2", 0), ("distance_m", 0), ("viscosity_pa_s", 0),
    ("permeability_m2", -1), ("relative_permeability", 1.1),
    ("face_left_weight", -0.1), ("distance_m", float("nan")),
    ("area_m2", float("inf")), ("permeability_m2", True),
    ("effective_diffusivities_m2_s", {"O2": 1, "N2": 1}),
    ("effective_diffusivities_m2_s", {"O2": -1, "N2": 1, "product": 1}),
    ("effective_diffusivities_m2_s", {"O2": float("nan"), "N2": 1, "product": 1}),
])
def test_invalid_face_inputs_are_rejected(field, value):
    gas = state({"O2": 1, "N2": 3, "product": 0})
    with pytest.raises(GasTransportError):
        face_exchange(gas, gas, **(FACE | {field: value}))


def test_inconsistent_species_masses_and_gas_constant_are_rejected():
    gas = state({"O2": 1, "N2": 3, "product": 0})
    others = [
        state({"O2": 1, "N2": 3, "product": 0}, masses=MASSES | {"O2": 0.032}),
        state({"O2": 1, "N2": 3, "product": 0}, gas_constant=8.314),
        state({"O2": 1, "N2": 3}, masses={"O2": 0.04, "N2": 0.02}),
    ]
    for other in others:
        with pytest.raises(GasTransportError):
            face_exchange(gas, other, **FACE)


def test_reservoir_fractions_are_validated_not_silently_repaired():
    with pytest.raises(GasTransportError):
        ideal_gas_reservoir(pressure_pa=9600, temperature_k=300,
                            mole_fractions={"O2": 0.2, "N2": 0.9, "product": 0},
                            molar_masses_kg_mol=MASSES, gas_constant_j_mol_k=R)


def test_roundoff_sized_reservoir_normalization_keeps_an_auditable_input_snapshot():
    fractions = {"O2": 0.25, "N2": 0.75 + 5e-13, "product": 0}
    reservoir = ideal_gas_reservoir(pressure_pa=9600, temperature_k=300,
                                    mole_fractions=fractions, molar_masses_kg_mol=MASSES,
                                    gas_constant_j_mol_k=R)
    assert reservoir.reservoir_input_fraction_sum == math.fsum(fractions.values())
    assert reservoir.reservoir_input_fraction_sum != 1.0
    actual_correction = max(abs(fractions[k] - reservoir.mole_fractions[k]) for k in MASSES)
    assert 0 < actual_correction < 1e-12
    assert reservoir.reservoir_max_abs_fraction_correction == actual_correction
    assert dict(reservoir.reservoir_input_mole_fractions) == fractions
    fractions["O2"] = 0.0
    assert reservoir.reservoir_input_mole_fractions["O2"] == 0.25
    with pytest.raises(TypeError):
        reservoir.reservoir_input_mole_fractions["O2"] = 0
    pore = state({"O2": 1, "N2": 3, "product": 0})
    assert pore.reservoir_input_fraction_sum is None
    assert pore.reservoir_max_abs_fraction_correction is None


@pytest.mark.parametrize("pressure", [0, -1, float("nan"), float("inf"), True])
def test_invalid_reservoir_pressure_is_rejected(pressure):
    with pytest.raises(GasTransportError):
        ideal_gas_reservoir(pressure_pa=pressure, temperature_k=300,
                            mole_fractions={"O2": 0.25, "N2": 0.75, "product": 0},
                            molar_masses_kg_mol=MASSES, gas_constant_j_mol_k=R)


def test_finite_inputs_whose_derived_state_or_flux_overflows_are_rejected():
    with pytest.raises(GasTransportError):
        state({"O2": 1e308, "N2": 1e308, "product": 0})
    gas = state({"O2": 1, "N2": 3, "product": 0})
    other = state({"O2": 2, "N2": 3, "product": 0})
    with pytest.raises(GasTransportError):
        face_exchange(gas, other, **(FACE | {"distance_m": 1e-300, "permeability_m2": 1e300}))
