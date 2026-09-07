"""Preregistered ideal-gas solid-volume bounds, without native water EOS.

Exact represented rational roots enclose both uncertainty signs. A tightness
regression distinguishes the certified local bound from the old global bound;
its oracle is p=nRT/V, not any production pressure-bound helper.
"""
from dataclasses import replace
from fractions import Fraction as F
import math

import pytest

from test_rigid_storage import water, model as fluid_model, R
from test_incompressible_solid import phase
from sludge_sandbox.solid_fluid_storage import SolidFluidStorage, SolidFluidStorageError


BULK = 1/8192
SOLID_V = 1/65536
SOLID_N = 2.
GAS_N = 1/1024
TEMPERATURE = 300.


def exact_binary_ceiling(value):
    """Smallest represented float >= rational value; independent test utility."""
    candidate = float(value)
    if F(candidate) < value:
        candidate = math.nextafter(candidate, math.inf)
    return F(candidate)


def pressure_fixture(water, monkeypatch, *, volume_error=1e-12, bulk_error=0., upper=1e6):
    def forbid(*args, **kwargs):
        pytest.fail('dry analytic pressure-bound test called native water EOS')
    monkeypatch.setattr(type(water), 'state_tp', forbid)
    fluid = fluid_model(water)
    fluid = replace(fluid, mechanical=replace(fluid.mechanical, pressure_bracket_pa=(1e4, upper)),
                    envelope=replace(fluid.envelope, pressure_range_pa=(1e4, upper)))
    # The fixture's declared u uncertainty must include p_ref*delta_v.
    # This adjusts only this analytic fixture, never production material data.
    u_error = float(max(F(2e-7), exact_binary_ceiling(F(1e5)*F(volume_error))))
    solid = phase(molar_volume_m3_mol=SOLID_V, declared_v_error_m3_mol=volume_error,
                  declared_u_error_j_mol=u_error)
    return SolidFluidStorage(fluid_template=fluid, solid_phases={'fixture_solid': solid},
        bulk_volume_m3=BULK, bulk_volume_error_m3=bulk_error,
        geometry_source_ids=('manufactured:analytic-pressure-bound',),
        geometry_id='manufactured:analytic-pressure-bound', geometry_version='1',
        geometry_classification='manufactured_test_fixture', allow_manufactured=True)


def evaluate(model):
    return model.evaluate_at_temperature(TEMPERATURE, 0., {'fixture': GAS_N}, {'fixture_solid': SOLID_N})


def exact_roots(volume_error, bulk_error=0.):
    numerator = F(GAS_N)*F(R)*F(TEMPERATURE)
    pore = F(BULK)-F(SOLID_N)*F(SOLID_V)
    delta = F(bulk_error)+F(SOLID_N)*F(volume_error)
    return numerator/(pore+delta), numerator/pore, numerator/(pore-delta)


@pytest.mark.parametrize('volume_error,bulk_error', [(1e-12, 0.), (1e-11, 0.), (0., 1e-11)])
def test_both_exact_perturbed_roots_inside_tight_local_bound(water, monkeypatch, volume_error, bulk_error):
    model = pressure_fixture(water, monkeypatch, volume_error=volume_error, bulk_error=bulk_error)
    point = evaluate(model)
    lower_root, nominal_root, upper_root = exact_roots(volume_error, bulk_error)
    pressure, error = F(point.mechanical.pressure_pa), F(point.pressure_error_bound_pa)
    assert pressure-error <= lower_root <= nominal_root <= upper_root <= pressure+error
    # The nonzero nominal closure/representation error is retained, not replaced.
    baseline = F(point.fluid_state.pressure_error_bound_pa)
    assert baseline > 0 and error >= baseline
    assert upper_root-nominal_root > nominal_root-lower_root
    numerator = F(GAS_N)*F(R)*F(TEMPERATURE)
    delta = F(bulk_error)+F(SOLID_N)*F(volume_error)
    global_extra = delta*F(1e6)**2/numerator
    # The old bound rounds the additional term outward, then rounds its
    # sum with the fluid bound outward: compare that exact two-stage ceiling.
    assert error <= exact_binary_ceiling(baseline+exact_binary_ceiling(global_extra))
    # Preregistered fixture nominal pressure is about 26.6 kPa, far below
    # the 1 MPa global envelope. One local bootstrap must improve >100-fold.
    assert error < global_extra/100
    # Positive-volume perturbation changes pressure asymmetrically; both
    # independent roots above are required, not a central derivative alone.
    assert F(point.volume_error_bound_m3) >= delta


def test_zero_volume_error_preserves_original_nonzero_fluid_error(water, monkeypatch):
    model = pressure_fixture(water, monkeypatch, volume_error=0.)
    point = evaluate(model)
    assert point.volume_error_bound_m3 == 0.
    assert point.pressure_error_bound_pa == point.fluid_state.pressure_error_bound_pa > 0
    exact = exact_roots(0.)[1]
    assert abs(F(point.mechanical.pressure_pa)-exact) <= F(point.pressure_error_bound_pa)


def test_near_upper_bracket_still_contains_both_roots_and_never_increases_bound(water, monkeypatch):
    roots = exact_roots(1e-12)
    upper = float(roots[1])+1.
    model = pressure_fixture(water, monkeypatch, upper=upper)
    point = evaluate(model)
    pressure, error = F(point.mechanical.pressure_pa), F(point.pressure_error_bound_pa)
    assert pressure-error <= roots[0] and roots[2] <= pressure+error <= F(upper)
    global_extra = 2*F(1e-12)*F(upper)**2/(F(GAS_N)*F(R)*F(TEMPERATURE))
    previous = exact_binary_ceiling(F(point.fluid_state.pressure_error_bound_pa)
                                    +exact_binary_ceiling(global_extra))
    assert error <= previous


def test_original_global_domain_rejection_is_not_bypassed_by_local_estimate(water, monkeypatch):
    # Exact perturbed gas roots are inside the bracket, but the old certified
    # global interval extends below it. Keep the original rejection contract.
    roots = exact_roots(0., 1e-6)
    assert F(1e4) < roots[0] < roots[2] < F(1e6)
    model = pressure_fixture(water, monkeypatch, volume_error=0., bulk_error=1e-6)
    with pytest.raises(SolidFluidStorageError, match='pressure_uncertainty_outside_envelope'):
        evaluate(model)


def test_volume_domain_rejects_uncertainty_reaching_zero_pore(water, monkeypatch):
    model = pressure_fixture(water, monkeypatch, volume_error=0., bulk_error=3/32768)
    with pytest.raises(SolidFluidStorageError, match='available_volume_uncertainty_excludes_positive_domain'):
        evaluate(model)
