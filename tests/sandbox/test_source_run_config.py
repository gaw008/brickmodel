"""Explicit real-provider configuration; tests use no native HEOS calls."""
import hashlib
import json
import shutil
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

import pytest

from sludge_sandbox.source_run_config import (SourceRunConfigError, exact_config_fraction,
    load_source_run_config, validate_source_run_assets, REQUIRED_ASSETS)
from sludge_sandbox.source_run_builder import build_source_run, build_source_controls

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / 'data/sandbox/cases/source-multicell-heos-v1.json'


def test_default_configuration_is_explicit():
    config = load_source_run_config(CASE.read_bytes())
    config.check()
    assert config.values['initial']['liquid_water_mol'] == (.25, 1e-11, .25)
    assert config.values['integration_policy']['relative_tolerance'] == 1e-8


def changed(*path, value):
    payload = json.loads(CASE.read_bytes())
    cursor = payload
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return json.dumps(payload).encode()


@pytest.mark.parametrize('path,value', [
    (('initial', 'liquid_water_mol', 1), True),
    (('initial', 'liquid_water_mol', 1), 1),
    (('initial', 'liquid_water_mol', 1), -1e-11),
    (('initial', 'temperature_k', 0), 400.),
    (('initial', 'interface_modes', 0), 'depleted_no_nucleation'),
    (('grid', 'cell_widths_m'), [.25, .375]),
    (('grid', 'face_area_m2'), 1e-9),
    (('grid', 'diffusivities_m2_s', 0, 0), float('nan')),
    (('liquid_transport', 'relative_permeability', 1), 1.1),
    (('classification',), 'measured_public_data'),
    (('resources', 'total_callback_cap'), 98),
    (('resources', 'outer_seconds'), 511.),
    (('inverse_policy', 'maximum_iterations'), True),
    (('roundoff_policy', 'correction_fraction_evaporated'), 1.1e-8),
    (('event_policy', 'terminal_method'), 'euler'),
    (('event_policy', 'pressure_comparison'), {}),
    (('study', 'selected_cell_index'), 0),
    (('study', 'start_seconds', 'denominator'), 0),
    (('study', 'start_seconds', 'numerator'), 0.0),
    (('assets', 0, 'path'), '../../outside'),
    (('assets', 0, 'sha256'), '0' * 64),
    (('envelope', 'gas_u_error_j_mol', 'O2'), -1e-7),
])
def test_invalid_input_rejected_before_any_provider(path, value):
    with pytest.raises(SourceRunConfigError):
        load_source_run_config(changed(*path, value=value))


@pytest.mark.parametrize('raw', [
    b'{"schema":"a","schema":"b"}', b'{"x":' + b'[' * 600 + b'0' + b']' * 600 + b'}',
    b' ' * 65537, b'{}', b'\xff', b'{"x":' + b'1' * 101 + b'}',
])
def test_bounded_closed_reader(raw):
    with pytest.raises(SourceRunConfigError):
        load_source_run_config(raw)


def test_canonical_numbers_and_config_mutation_binding():
    config = load_source_run_config(CASE.read_bytes())
    assert load_source_run_config(config.canonical_bytes).canonical_bytes == config.canonical_bytes
    assert config.sha256 == hashlib.sha256(config.canonical_bytes).hexdigest()
    assert exact_config_fraction(config.values['study']['horizon_multiplier']) == F(3, 2)
    with pytest.raises(TypeError):
        config.values['initial']['liquid_water_mol'][1] = .1
    object.__setattr__(config, 'sha256', '0' * 64)
    with pytest.raises(SourceRunConfigError, match='binding'):
        config.check()


@pytest.fixture(scope='module')
def copied_bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp('source-bundle')
    for relative, _, _ in REQUIRED_ASSETS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return root


def test_asset_bundle_is_minimal_external_and_rechecked(copied_bundle):
    config = load_source_run_config(CASE.read_bytes())
    assets = validate_source_run_assets(config, assets_root=copied_bundle)
    assert len(assets.files) == 17
    assert len(tuple(path for path in copied_bundle.rglob('*') if path.is_file())) == 17
    assert assets.root != ROOT and assets.config_sha256 == config.sha256
    target = copied_bundle / REQUIRED_ASSETS[-1][0]
    original = target.read_bytes()
    try:
        target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        with pytest.raises(SourceRunConfigError, match='asset_hash'):
            assets.check()
    finally:
        target.write_bytes(original)
    assets.check()


def test_bundle_cannot_escape_declared_root(tmp_path):
    config = load_source_run_config(CASE.read_bytes())
    relative = REQUIRED_ASSETS[0][0]
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.symlink_to(ROOT / relative)
    with pytest.raises(SourceRunConfigError, match='outside_root'):
        validate_source_run_assets(config, assets_root=tmp_path)


def test_bundle_fifo_is_rejected_without_blocking(tmp_path):
    import os
    config = load_source_run_config(CASE.read_bytes())
    target = tmp_path / REQUIRED_ASSETS[0][0]
    target.parent.mkdir(parents=True)
    os.mkfifo(target)
    with pytest.raises(ValueError, match='not_regular'):
        validate_source_run_assets(config, assets_root=tmp_path)


@pytest.fixture(scope='module')
def constructed(copied_bundle):
    """Actual storage classes, explicit Python-provider constructor seam, zero liquid EOS.

    Only backend factories are replaced. The public builder still requests HEOS
    and its approved manifest; this fixture makes no claim to native validation.
    """
    from sludge_sandbox import source_run_builder as module
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    config = load_source_run_config(CASE.read_bytes())
    assets = validate_source_run_assets(config, assets_root=copied_bundle)
    directory = copied_bundle / 'data/sandbox/water'
    water = WaterProperties(directory)
    vapor = IdealWaterVapor(directory)
    chemical = WaterChemicalPotential(directory)
    calls = []
    def factory(label, product):
        def construct(path, **kwargs):
            assert path == directory
            assert kwargs == {'backend': 'heos', 'backend_manifest': directory / 'heos-8.0.0-approved-manifest.json'}
            calls.append(label)
            return product
        return construct
    def forbidden(*args, **kwargs):
        raise AssertionError('builder_must_not_evaluate_initial_energy_or_native_EOS')
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, 'load_water_properties', factory('water', water))
        patch.setattr(module, 'IdealWaterVapor', factory('vapor', vapor))
        patch.setattr(module, 'WaterChemicalPotential', factory('chemical', chemical))
        patch.setattr(WaterProperties, '_solve', forbidden)
        patch.setattr(module.SourceWetStorage, 'evaluate', forbidden)
        built = build_source_run(config, assets)
    return built, calls


def test_actual_constructor_configuration_and_provider_selection(constructed, copied_bundle):
    built, calls = constructed
    assert calls == ['water', 'vapor', 'chemical']
    built.check()
    assert built.assets.root == copied_bundle
    assert len({id(storage) for storage in built.storages}) == 3
    assert len({id(storage.volume) for storage in built.storages}) == 3
    assert len({id(storage.caloric) for storage in built.storages}) == 1
    assert tuple(state.internal_energy_j for state in built.unset_energy_states) == (0.,) * 3
    assert tuple(state.liquid_water_mol for state in built.unset_energy_states) == (.25, 1e-11, .25)
    assert built.initial_temperatures_k == (325.,) * 3
    assert built.column.interface_modes == ('existing_liquid',) * 3
    assert built.column.transfer_coefficients_mol_s_pa == (0., 1e-9, 0.)
    for storage in built.storages:
        assert storage.volume.value_m3 == .001 and storage.volume.error_m3 == 1e-12
        assert storage.caloric.provider.repository_root == copied_bundle
        assert storage.fluid_template.mechanical.policy.volume_tolerance_m3 == 1e-12
    liquid = built.column.liquid_transport
    assert tuple(c.status for c in liquid.connections) == ('disabled', 'connected')
    assert liquid.relations[0].relative_permeability == (0., .5, .5)
    assert liquid.relations[0].source_asset_sha256 == (('source_run_config_v1', built.config.sha256),)
    assert all(face.permeability_m2 == 0. and face.conductivities_w_m_k == (0., 0.)
               and face.diffusivities_m2_s == (0., 0., 0.) for face in built.column.faces)


def test_actual_source_molar_mass_and_original_controls(constructed):
    built, _ = constructed
    h = F(1, 64)
    controls = build_source_controls(built.config, built, horizon=h)
    assert controls.horizon == h
    p, event = controls.integration_policy, controls.event_policy
    assert (p.initial_step_s, p.maximum_step_s) == (float(h),) * 2
    assert (p.relative_tolerance, p.amount_absolute_tolerance_mol, p.energy_absolute_tolerance_j) == (1e-8, 1e-7, 1e-3)
    assert (p.maximum_steps, p.maximum_rejections, p.maximum_wall_seconds) == (4, 4, 180.)
    assert event.terminal_method == 'affine_midpoint'
    assert event.roundoff_policy.molar_mass_kg_mol.hex() == built.chemical.reference.molar_mass_kg_mol.hex()
    assert event.pressure_absolute_pa == 1e-4 and event.temperature_absolute_k == 1e-5
    for section, policy in (('event_policy', event), ('roundoff_policy', event.roundoff_policy),
                             ('integration_policy', p)):
        for key, value in built.config.values[section].items():
            assert type(getattr(policy, key)) is type(value) and getattr(policy, key) == value
    object.__setattr__(event, 'pressure_absolute_pa', 1.)
    with pytest.raises(SourceRunConfigError, match='content_changed'):
        controls.check()
    fresh = build_source_controls(built.config, built, horizon=h)
    assert fresh.event_policy.pressure_absolute_pa == 1e-4


@pytest.mark.parametrize('horizon', [1, True, .1, F(0), F(-1), F(1, 10**100), F(10**400)])
def test_controls_reject_invalid_or_unrepresentable_duration(constructed, horizon):
    built, _ = constructed
    with pytest.raises(ValueError):
        build_source_controls(built.config, built, horizon=horizon)


def test_live_storage_identity_and_state_mutation_are_rejected(constructed):
    built, _ = constructed
    clone = replace(built.storages[0])
    forged = replace(built, storages=(clone, *built.storages[1:]))
    with pytest.raises(SourceRunConfigError, match='live_associations'):
        forged.check()
    forged = replace(built, unset_energy_states=(replace(built.unset_energy_states[0], internal_energy_j=1.),
                                                *built.unset_energy_states[1:]))
    with pytest.raises(SourceRunConfigError, match='content_changed'):
        forged.check()


def test_legacy_source_storage_identity_is_preserved(constructed, copied_bundle):
    """Read the pinned legacy make_case only as a direct constructor oracle."""
    import importlib.util
    legacy_path = ROOT / 'docs/sandbox/research/source-wet-storage-v1/run_native.py'
    assert hashlib.sha256(legacy_path.read_bytes()).hexdigest() == (
        '9a8bbf40651c7dfc31e81c85e8367904e441e210f1c7b1666c9080dbc81b93a6')
    spec = importlib.util.spec_from_file_location('legacy_source_storage_constructor', legacy_path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    built, _ = constructed
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
    water = WaterProperties(copied_bundle / 'data/sandbox/water')
    vapor = IdealWaterVapor(copied_bundle / 'data/sandbox/water')
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(legacy, 'load_water_properties', lambda *args, **kwargs: water)
        patch.setattr(legacy, 'IdealWaterVapor', lambda *args, **kwargs: vapor)
        old, _ = legacy.make_case(copied_bundle)
    assert all(storage.model_identity == old.model_identity for storage in built.storages)
    assert old.fluid_template.envelope == built.storages[0].fluid_template.envelope
