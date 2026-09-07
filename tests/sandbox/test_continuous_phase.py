"""Explicit continuous caloric phase assembly; no automatic source-pack replacement."""
from dataclasses import replace
from pathlib import Path

import pytest

from sludge_sandbox.continuous_caloric import ContinuousShomateGas
from sludge_sandbox.phase_storage import IdealGasPhase, PhaseStorageError, InversePolicy
from sludge_sandbox.rigid_storage import RigidStorage, DeclaredNumericalEnvelope, RigidStorageError
from sludge_sandbox.rigid_water_gas import RigidWaterGas, PressurePolicy
from sludge_sandbox.thermochemistry import load_thermochemistry, ShomateGas, ShomateSegment
from sludge_sandbox.water_properties import load_water_properties

ROOT = Path(__file__).resolve().parents[2]
R = 8.31446261815324


def derived(gas=None):
    if gas is None:
        gas = load_thermochemistry(ROOT/'data/sandbox/thermochemistry/nist_gases_v1.json').species('O2')
    return ContinuousShomateGas(source_gas=gas, model_id='explicit-phase-continuous-v1', version='1',
        anchor_temperature_k=500., method_source_ids=('piecewise-cp-integral',),
        gas_constant_source_ids=('nist-codata-2022',), allow_manufactured=True)


def test_continuous_phase_preserves_reference_sources_and_entire_domain():
    c = derived()
    phase = IdealGasPhase(c, .0319988)
    assert phase.temperature_range_k == c.temperature_range_k
    assert phase.metadata.classification == 'derived_from_evidence'
    assert set(c.source_ids) <= set(phase.metadata.source_ids)
    for t in (699.9, 700., 700.1):
        out = phase.evaluate(t, 2e5)
        assert out.enthalpy_j_mol == c.enthalpy_j_mol(t)
        assert out.internal_energy_j_mol == c.internal_energy_j_mol(t)
        assert out.molar_volume_m3_mol == pytest.approx(R*t/2e5, abs=1e-14, rel=0)
    with pytest.raises(PhaseStorageError, match='segment'):
        replace(phase, segment_index=0)


def test_original_shomate_still_requires_explicit_single_segment():
    c = derived()
    with pytest.raises(PhaseStorageError, match='single_segment'):
        IdealGasPhase(c.source_gas, .0319988)
    old = IdealGasPhase(c.source_gas, .0319988, 0, ('nist-codata-2022',))
    assert old.temperature_range_k == c.source_gas.segments[0].temperature_range_k


def test_actual_closed_inverse_crosses_caloric_seam_with_independent_heat_integral():
    pytest.importorskip('iapws')
    source = ShomateGas('fixture', (
        ShomateSegment((300., 600.), (30., 0., 0., 0., 0., 100., 0., 0.), 0., R, ('fixture',)),
        ShomateSegment((600., 1000.), (40., 0., 0., 0., 0., 200., 0., 0.), 0., R, ('fixture',)),
    ), 'manufactured_test_fixture', ('fixture',))
    curve = derived(source)
    phase = IdealGasPhase(curve, .028)
    water = load_water_properties(ROOT/'data/sandbox/water')
    mechanical = RigidWaterGas(water, ('fixture',), 1e-3, (1e4, 1e8),
        'planar_interface_no_capillary_pressure', PressurePolicy(1e-13, 1e-5, 150))
    envelope = DeclaredNumericalEnvelope((400., 900.), (1e4, 1e8), 1e-8, 1e-16, 1e-4,
        {'fixture': 1e-9}, {'fixture': 20.}, 'manufactured-caloric-test-contract', ('fixture',))
    model = RigidStorage(mechanical, {'fixture': phase}, envelope, True)
    start_u = source.segments[0].internal_energy_j_mol(500.)
    for target_t in (599.9, 600., 600.1, 700.):
        # Independent constant-Cv path relative to the unchanged original anchor.
        target = start_u + (30.-R)*(min(target_t, 600.)-500.) + (40.-R)*max(target_t-600., 0.)
        out = model.temperature_from_energy(target, 0., {'fixture': 1.}, (450., 800.), InversePolicy(1e-6, 1e-6, 100))
        assert out.state.mechanical.temperature_k == pytest.approx(target_t, abs=1e-6, rel=0)
    with pytest.raises(RigidStorageError, match='opt_in'):
        replace(model, allow_manufactured=False)
