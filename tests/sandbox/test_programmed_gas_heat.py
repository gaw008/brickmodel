"""Physical boundary assembly with explicit manufactured gas caloric storage."""
from dataclasses import replace
import math

import numpy as np
import pytest
from scipy.optimize import brentq

from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.integration import DomainExit, integrate
from sludge_sandbox.programmed_gas_heat import ProgrammedGasHeat, ProgrammedGasHeatError, SurfacePolicy
from test_gas_heat_model import model, policy


def boundary(**changes):
    values = dict(identity=ProgramIdentity(program_id='design-boundary', version='1',
                  classification='virtual_design_choice', source_ids=('design:boundary',)),
                  knot_times_s=(0, .1, .3), gas_temperature_k=(900, 1000, 800),
                  radiation_temperature_k=(1100, 900, 1000), total_pressure_pa=(4800, 6000, 4000),
                  species_order=('A', 'B'), mole_fractions=((1, 0), (.5, .5), (0, 1)))
    values.update(changes)
    return BoundaryProgram(**values)


def wrapped(**changes):
    base = model(cell_widths_m=(2.,), gas_volumes_m3=(2.,), conductivities_w_m_k=(2.,),
                 effective_diffusivities_m2_s={'A': (0.,), 'B': (0.,)},
                 permeability_m2=(0.,), relative_permeability=(1.,), viscosity_pa_s=(1.,))
    fields = dict(base_model=base, program=boundary(), convection_w_m2_k=3., emissivity=0.,
                  stefan_boltzmann_w_m2_k4=5.670374419e-8,
                  coefficient_set_id='fixture-heat-film', coefficient_version='1',
                  coefficient_classification='manufactured', coefficient_source_ids=('manufactured:film',),
                  allow_manufactured=True,
                  surface_policy=SurfacePolicy(absolute_residual_w=1e-8, relative_residual=1e-11,
                                               maximum_iterations=200))
    fields.update(changes)
    return ProgrammedGasHeat(**fields)


def test_convection_is_in_series_with_actual_half_cell_and_area():
    op = wrapped()
    state = op.base_model.state_from_temperatures([[2, 0]], [600])
    evaluation = op.evaluate(state, 0)
    # half-cell width 1m, k=2 => G/A=2, film h=3, series=1.2 W/m²K.
    assert evaluation.surface_temperature_k == pytest.approx(780, abs=1e-8)
    assert evaluation.heat.total_in_w == pytest.approx(360, abs=1e-8)
    assert evaluation.rates.face_energy_w[-1] == pytest.approx(-360, abs=1e-8)
    large = wrapped(base_model=replace(op.base_model, face_area_m2=4, gas_volumes_m3=(8.,)))
    state = large.base_model.state_from_temperatures([[8, 0]], [600])
    assert large(state, 0).face_energy_w[-1] == pytest.approx(-1440, abs=1e-7)


def test_radiation_and_convection_balance_independent_nonlinear_reference():
    op = wrapped(emissivity=.8)
    state = op.base_model.state_from_temperatures([[2, 0]], [600])
    e = op.evaluate(state, 0)
    sigma = 5.670374419e-8
    root = brentq(lambda s: 2*(s-600)-3*(900-s)-.8*sigma*(1100**4-s**4), 600, 1100, xtol=1e-11)
    assert e.surface_temperature_k == pytest.approx(root, abs=1e-7)
    assert e.heat.total_in_w == pytest.approx(2*(root-600), abs=1e-7)
    assert abs(e.surface_balance_residual_w) <= 1e-8 + 1e-11*abs(e.heat.total_in_w)


def test_dynamic_pressure_and_composition_affect_actual_mass_and_enthalpy_flux():
    op = wrapped(convection_w_m2_k=0)
    base = replace(op.base_model, permeability_m2=(1e-5,), effective_diffusivities_m2_s={'A': (.1,), 'B': (.1,)})
    op = replace(op, base_model=base)
    state = base.state_from_temperatures([[2, 0]], [600])
    low = op.evaluate(state, .3)
    high = op.evaluate(state, .1)
    assert high.reservoir.pressure_pa == pytest.approx(6000)
    assert low.reservoir.mole_fractions == pytest.approx({'A': 0, 'B': 1})
    assert high.rates.face_species_mol_s[-1].sum() < 0
    assert low.rates.face_species_mol_s[-1].sum() > 0
    assert not np.allclose(low.rates.face_species_mol_s, high.rates.face_species_mol_s)
    assert low.rates.face_energy_w[-1] != high.rates.face_energy_w[-1]
    fixed = replace(op, program=boundary(mole_fractions=((1, 0),)*3))
    assert fixed(state, .1).face_species_mol_s[-1, 1] == 0


def test_zero_conductivity_transmits_no_film_heat_and_adiabatic_case():
    op = wrapped()
    state = op.base_model.state_from_temperatures([[2, 0]], [600])
    insulated = replace(op, base_model=replace(op.base_model, conductivities_w_m_k=(0.,)))
    assert insulated(state, 0).face_energy_w[-1] == 0
    assert insulated.evaluate(state, 0).surface_temperature_k == pytest.approx(900, abs=1e-8)
    off = replace(op, convection_w_m2_k=0, emissivity=0)
    assert off(state, 0).face_energy_w[-1] == 0
    assert off.evaluate(state, 0).surface_temperature_k == pytest.approx(600, abs=1e-9)


def test_real_integration_program_knots_and_outer_ledger():
    op = wrapped()
    initial = op.base_model.state_from_temperatures([[2, 0]], [600])
    result = integrate(initial, op, start_s=0, end_s=.3, policy=policy(initial_step_s=.002, maximum_step_s=.005, relative_tolerance=1e-8),
                       breakpoints_s=op.breakpoints_s(0, .3))
    assert result.status == 'completed'
    assert .1 in result.times_s
    assert result.states[-1].internal_energy_j[0] > initial.internal_energy_j[0]
    # One cell Cv=44 J/K, series G=1.2 W/K. Exact solution on each linear Tg segment.
    temp = 600.
    for dt, gas0, slope in [(.1, 900., 1000.), (.2, 1000., -1000.)]:
        a = 1.2/44
        temp = gas0 + slope*dt - slope/a + (temp-gas0+slope/a)*math.exp(-a*dt)
    assert op.base_model.temperatures_k(result.states[-1])[0] == pytest.approx(temp, abs=2e-6)
    for before, after, step in zip(result.states, result.states[1:], result.steps):
        assert after.internal_energy_j[0]-before.internal_energy_j[0] == pytest.approx(-step.face_energy_j[-1], abs=1e-9)
    assert initial.internal_energy_j[0]-math.fsum(s.face_energy_j[-1] for s in result.steps) == pytest.approx(result.states[-1].internal_energy_j[0], abs=1e-8)


@pytest.mark.parametrize('changes', [dict(convection_w_m2_k=-1), dict(emissivity=1.1),
                                    dict(stefan_boltzmann_w_m2_k4=0), dict(allow_manufactured=False),
                                    dict(coefficient_source_ids=()), dict(coefficient_classification='unknown')])
def test_invalid_explicit_coefficients(changes):
    with pytest.raises(ProgrammedGasHeatError):
        wrapped(**changes)


def test_duplicate_boundary_species_and_time_domains_rejected():
    op = wrapped()
    with pytest.raises(ProgrammedGasHeatError):
        replace(op, base_model=replace(op.base_model, outer_surface_temperature_k=700, outer_heat_source_ids=('x',)))
    with pytest.raises(ProgrammedGasHeatError):
        replace(op, program=boundary(species_order=('B', 'A')))
    state = op.base_model.state_from_temperatures([[2, 0]], [600])
    with pytest.raises(DomainExit):
        op(state, .4)
    with pytest.raises(ProgrammedGasHeatError):
        op(state, math.nan)


def test_inflow_moles_and_donor_enthalpy_independent_half_cell_calculation():
    op = wrapped(convection_w_m2_k=0)
    op = replace(op, base_model=replace(op.base_model, permeability_m2=(1e-5,)))
    state = op.base_model.state_from_temperatures([[2, 0]], [600])
    result = op.evaluate(state, .1)
    velocity = -1e-5 * (6000-4800) / 1  # actual last half-cell = 1 m
    total_flux = velocity * (6000 / (8*1000))
    assert result.rates.face_species_mol_s[-1] == pytest.approx([total_flux/2]*2, abs=1e-14)
    expected_h = 30*(1000-298.15) - 500  # mean formation h of A/B is -500 J/mol
    assert result.rates.face_energy_w[-1] == pytest.approx(total_flux*expected_h, abs=1e-8)
    assert result.heat.total_in_w == 0


def test_roundoff_reservoir_conversion_is_exposed_with_original_program():
    fractions = (.5, .5+2**-52)
    op = wrapped(program=boundary(mole_fractions=(fractions,)*3))
    state = op.base_model.state_from_temperatures([[2, 0]], [600])
    result = op.evaluate(state, .1)
    assert tuple(result.boundary.mole_fractions.values()) == fractions
    assert result.reservoir.reservoir_input_fraction_sum == math.fsum(fractions)
    assert result.reservoir.reservoir_max_abs_fraction_correction > 0
    assert not op.material_qualified
    assert 'design:boundary' in op.source_ids and 'manufactured:film' in op.source_ids


def test_surface_iteration_failure_and_thermochemistry_mutation_are_not_hidden():
    from sludge_sandbox.gas_heat_model import GasHeatModelError

    op = wrapped(emissivity=.8, surface_policy=SurfacePolicy(
        absolute_residual_w=1e-8, relative_residual=1e-11, maximum_iterations=1))
    state = op.base_model.state_from_temperatures([[2, 0]], [600])
    with pytest.raises(ProgrammedGasHeatError, match='surface_iteration_limit'):
        op(state, 0)
    result = integrate(state, op, start_s=0, end_s=.1, policy=policy())
    assert result.status == 'numerical_failure'
    assert result.reason == 'surface_iteration_limit'
    assert result.times_s == (0,)
    op.base_model.thermochemistry.pack_id = 'changed'
    with pytest.raises(GasHeatModelError, match='thermochemistry_changed'):
        op(state, 0)
