"""Version selection does not silently upgrade historical cases or physics."""
import hashlib
import json
from pathlib import Path

import pytest

from sludge_sandbox.heos_runtime_registry import RHS_MANIFEST_ASSET
from sludge_sandbox.source_run_config import (PROFILE, RHS_PROFILE, REQUIRED_ASSETS,
    SourceRunConfigError, load_source_run_config, required_source_assets, source_heos_manifest,
    validate_source_run_assets)

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'data/sandbox/cases/source-nonstationary-heos-v2.json'
NEW = ROOT / 'data/sandbox/cases/source-nonstationary-heos-rhs-v3.json'


def test_new_profile_changes_only_declared_runtime_asset_and_profile():
    old = json.loads(OLD.read_bytes())
    new = json.loads(NEW.read_bytes())
    assert old['profile'] == PROFILE and new['profile'] == RHS_PROFILE
    changed = [i for i, (a, b) in enumerate(zip(old['assets'], new['assets'])) if a != b]
    assert len(old['assets']) == len(new['assets']) == 17 and changed == [10]
    assert new['assets'][10] == dict(zip(('path', 'bytes', 'sha256'), RHS_MANIFEST_ASSET))
    new['profile'], new['assets'] = old['profile'], old['assets']
    assert new == old  # All physical inputs, source data, tolerances and caps.


def test_both_profiles_bind_their_exact_manifest():
    for path, profile in ((OLD, PROFILE), (NEW, RHS_PROFILE)):
        config = load_source_run_config(path.read_bytes())
        config.check()
        assets = validate_source_run_assets(config, assets_root=ROOT)
        assert assets.files == required_source_assets(profile)
        assert source_heos_manifest(config) == assets.files[10][0].rsplit('/', 1)[-1]
    assert required_source_assets(PROFILE) == REQUIRED_ASSETS


@pytest.mark.parametrize('path,other', [(OLD, RHS_PROFILE), (NEW, PROFILE)])
def test_profiles_cannot_exchange_unmodified_asset_lists(path, other):
    raw = json.loads(path.read_bytes())
    raw['profile'] = other
    with pytest.raises(SourceRunConfigError, match='pinned_assets'):
        load_source_run_config(json.dumps(raw).encode())


def test_legacy_kernel_is_original_and_v2_changes_no_native_constants():
    source = ROOT / 'src/sludge_sandbox'
    legacy = json.loads((ROOT / REQUIRED_ASSETS[10][0]).read_bytes())
    raw = (ROOT / RHS_MANIFEST_ASSET[0]).read_bytes()
    assert (len(raw), hashlib.sha256(raw).hexdigest()) == RHS_MANIFEST_ASSET[1:]
    current = json.loads(raw)
    assert hashlib.sha256((source / '_heos_kernel_v1.py').read_bytes()).hexdigest() == legacy['adapter_sha256']
    assert current.pop('adapter_sha256') == hashlib.sha256((source / '_heos_kernel.py').read_bytes()).hexdigest()
    for name, sha in current.pop('execution_sources').items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == sha
    assert current.pop('execution_contract') == 'explicit_managed_single_rhs_v1_default_per_call_preserved'
    legacy.pop('adapter_sha256')
    assert current == legacy
