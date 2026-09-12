"""Bounded point probes only; no time integration or material qualification."""
from dataclasses import FrozenInstanceError, asdict
from fractions import Fraction as F
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

import pytest

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'src'))
from sludge_sandbox.geometry import ReferenceSlab
from equation_points import dense_solve

path = Path(os.environ.get('REVIEW_SOURCE_PATH', ROOT/'src/sludge_sandbox/cooling_thermoelastic_plate.py'))
spec = importlib.util.spec_from_file_location('sludge_sandbox.independent_review_plate', path)
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def plate(**changes):
    options = dict(reference=ReferenceSlab(.02, .01, 2), biaxial_modulus_pa=1e9,
        linear_expansion_per_k=1e-4, stress_free_heat_capacity_j_m3_k=1e5,
        reference_temperature_k=300., conductivity_w_m_k=1.,
        temperature_bounds_k=(290., 310.), strain_bounds=(-.01, .01),
        outer_temperature_k=295., outer_boundary='adiabatic',
        coefficient_classification='manufactured', mechanical_regime='symmetric_free_plane_stress')
    options.update(changes)
    return model.CoolingThermoelasticPlate(**options)


def test_single_cell_positive_ce_retains_uniform_mode_and_compatibility():
    op = plate(reference=ReferenceSlab(.02, .01, 1), biaxial_modulus_pa=1.,
        stress_free_heat_capacity_j_m3_k=1., linear_expansion_per_k=math.sqrt((1-1e-12)/600),
        temperature_bounds_k=(299., 300.), strain_bounds=(-.1, .1),
        outer_temperature_k=299., outer_boundary='fixed_temperature')
    out = op.evaluate([300.])
    assert out.points[0].fixed_strain_heat_capacity_j_m3_k > 0
    expected = out.cell_heat_in_w[0]/out.reference_cell_volumes_m3[0]
    assert out.temperature_rates_k_s[0] == pytest.approx(expected, rel=1e-12)
    assert out.in_plane_strain_rate_per_s == pytest.approx(op.linear_expansion_per_k*out.temperature_rates_k_s[0], rel=1e-12)


def test_adiabatic_zero_flux_does_not_evaluate_inactive_reservoir_ratio():
    op = plate(reference=ReferenceSlab(.02, .01, 1), biaxial_modulus_pa=1.,
        stress_free_heat_capacity_j_m3_k=1., linear_expansion_per_k=0.,
        reference_temperature_k=1e-100, conductivity_w_m_k=0.,
        temperature_bounds_k=(5e-101, 2e-100), strain_bounds=(-.1, .1),
        outer_temperature_k=1e308)
    out = op.evaluate([1e-100])
    assert out.temperature_rates_k_s == (0.,)
    assert out.total_entropy_production_w_k == out.reservoir_entropy_rate_w_k == 0.


def test_actual_two_cell_stage_matches_prefrozen_exact_point():
    exact = json.loads((HERE/'EQUATION_POINTS.json').read_text())['two_equal_cells_adiabatic']
    out = plate().evaluate([304., 300.])
    for actual, expected in zip(out.temperature_rates_k_s, exact['temperatures_rate'], strict=True):
        assert actual == pytest.approx(float(F(expected)), rel=2e-14)
    for actual, expected in zip(out.cell_mechanical_power_w, exact['local_mechanical_power'], strict=True):
        assert actual == pytest.approx(float(F(expected)), rel=2e-13)
    assert out.total_internal_energy_j == pytest.approx(float(F(exact['energy'])), abs=1e-12)
    assert out.total_entropy_production_w_k == pytest.approx(float(F(exact['entropy_production'])), rel=2e-14)


def test_three_cells_dense_fraction_solution_and_all_local_ledgers():
    op = plate(reference=ReferenceSlab(.03, .02, 3), conductivity_w_m_k=2., outer_boundary='fixed_temperature')
    temperatures = [303., 301., 299.]
    out = op.evaluate(temperatures)
    assert out.face_heat_outward_w == pytest.approx((0., 8., 8., 32.))
    assert out.cell_heat_in_w == pytest.approx((-8., 0., -24.))
    matrix = [[(F(100000)-20*F(t) if i == j else F(0))+20*F(t)/3 for j in range(3)] for i, t in enumerate(temperatures)]
    expected = dense_solve(matrix, [F(-40000), F(0), F(-120000)])
    for value, reference in zip(out.temperature_rates_k_s, expected, strict=True):
        assert value == pytest.approx(float(reference), rel=2e-14, abs=1e-14)
    assert out.in_plane_strain_rate_per_s == pytest.approx(1e-4*math.fsum(out.temperature_rates_k_s)/3, rel=2e-14)
    for i, temperature in enumerate(temperatures):
        volume = out.reference_cell_volumes_m3[i]
        assert volume*out.cell_u_rates_j_m3_s[i] == pytest.approx(out.cell_heat_in_w[i]+out.cell_mechanical_power_w[i], abs=2e-13)
        assert temperature*out.cell_s_rates_j_m3_k_s[i] == pytest.approx(out.cell_heat_in_w[i]/volume, abs=2e-10)
    assert out.total_mechanical_power_w == pytest.approx(0., abs=1e-13)
    assert out.total_internal_energy_rate_w == pytest.approx(-32., abs=1e-12)
    assert out.total_entropy_rate_w_k+out.reservoir_entropy_rate_w_k == pytest.approx(out.total_entropy_production_w_k, abs=2e-16)
    expected_entropy = 4*2**2/(303*301)+4*2**2/(301*299)+8*4**2/(299*295)
    assert out.total_entropy_production_w_k == pytest.approx(expected_entropy, rel=2e-14)
    assert out.cell_mechanical_power_w[0] != 0.
    assert volume*out.cell_u_rates_j_m3_s[0]-out.cell_heat_in_w[0] == pytest.approx(out.cell_mechanical_power_w[0], abs=2e-13)


def test_sign_of_alpha_changes_stress_and_strain_but_not_thermal_feedback():
    positive = plate(outer_boundary='fixed_temperature').evaluate([304., 301.])
    negative = plate(linear_expansion_per_k=-1e-4, outer_boundary='fixed_temperature').evaluate([304., 301.])
    assert negative.temperature_rates_k_s == positive.temperature_rates_k_s
    assert negative.in_plane_strain == -positive.in_plane_strain
    assert negative.in_plane_strain_rate_per_s == -positive.in_plane_strain_rate_per_s
    assert negative.cell_mechanical_power_w == positive.cell_mechanical_power_w
    for left, right in zip(negative.points, positive.points, strict=True):
        assert left.stress_pa == -right.stress_pa
        assert left.internal_energy_j_m3 == right.internal_energy_j_m3
        assert left.entropy_j_m3_k == right.entropy_j_m3_k


def test_negative_reference_energy_is_valid_and_not_clipped():
    out = plate().evaluate([291., 291.])
    assert out.total_internal_energy_j < 0.
    for point in out.points:
        assert point.internal_energy_j_m3 == -900000.
        assert point.helmholtz_j_m3 < 0. and point.entropy_j_m3_k < 0.
        assert point.stress_pa == 0.


@pytest.mark.parametrize('changes, temperatures', [
    ({'linear_expansion_per_k': 0., 'outer_boundary': 'fixed_temperature'}, [304., 300.]),
    ({'conductivity_w_m_k': 0., 'outer_boundary': 'fixed_temperature'}, [304., 300.]),
    ({'outer_boundary': 'fixed_temperature', 'outer_temperature_k': 300.}, [300., 300.]),
])
def test_zero_coefficient_or_isothermal_modes_and_finite_output(changes, temperatures):
    out = plate(**changes).evaluate(temperatures)

    def finite(value):
        if isinstance(value, dict):
            return all(finite(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return all(finite(v) for v in value)
        return math.isfinite(value) if isinstance(value, float) else True

    assert finite(asdict(out))
    if changes.get('linear_expansion_per_k') == 0.:
        assert out.temperature_rates_k_s == pytest.approx((-.4, -.6))
    else:
        assert out.temperature_rates_k_s == (0., 0.)
    assert out.cell_mechanical_power_w == (0., 0.)


def test_bounds_and_input_arrays_are_snapshotted_and_outputs_frozen():
    t_bounds, e_bounds, temperatures = [290., 310.], [-.01, .01], [304., 300.]
    op = plate(temperature_bounds_k=t_bounds, strain_bounds=e_bounds)
    out = op.evaluate(temperatures)
    t_bounds[0], e_bounds[0], temperatures[0] = 999., 999., 999.
    assert op.temperature_bounds_k == (290., 310.) and op.strain_bounds == (-.01, .01)
    assert out.temperatures_k == (304., 300.)
    with pytest.raises(FrozenInstanceError):
        op.reference.cells = 3
    with pytest.raises(FrozenInstanceError):
        out.points[0].stress_pa = 0.
    assert isinstance(out.face_heat_outward_w, tuple)
