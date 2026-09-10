# Final implementation interface: source-run-service-v1

The earlier RECONSTRUCTION_MAP.md is a design record. This file describes the implemented API at FREEZE.json, without superseding any original native evidence.

```python
config = load_source_run_config(raw_bytes)  # source_run_config
assets = validate_source_run_assets(config, assets_root=Path(...))
built = build_source_run(config, assets)   # source_run_builder
# The run service now evaluates each (storage, unset_energy_state, temperature)
# exactly once as an observed initial-U attempt, retains point, then replaces U.
# The actual original probe yields H from phase + right face - left face loss.
controls = build_source_controls(config, built, horizon=H)  # exact Fraction
```

`SourceRunConfig` has canonical_bytes, sha256, immutable nested values, and check(). The schema is closed `source_run_config_v1`, profile `source_multicell_wet_to_dry_heos_v1`. The first runnable profile is explicitly three initially wet cells, selected cell 1, dry shared cell 1, wet shared cells 0 and 2. Numeric scenario fields remain explicit and validated. JSON float fields require finite binary64 float spellings; bool and integer spellings are rejected there, without silently changing units or precision. Exact clocks use reduced numerator/denominator mappings. No Python factory or import path can be selected from JSON.

`SourceRunAssets` has root, files (tuple of path/size/SHA tuples), sha256 (canonical manifest identity), config_sha256, and check(). The 17 files are a closed pinned source bundle, relative to the caller's explicit root. Bundle validation rejects escapes, non-regular files, missing files and any size/content mismatch. It downloads or redistributes nothing. The four private Arlabosse source cache files remain separately supplied local inputs, not wheel package data. The water runtime still performs its own installed-module/manifest/anchor checks on actual construction.

`BuiltSourceRun` has config, assets, storages, chemical, column, adapter, unset_energy_states, initial_temperatures_k, original_binding and check(). The three storage and volume instances are distinct. Provider/Cp/template sharing is preserved; future cloned path adapters must retain the same per-cell instances. Builder returns three zero-U placeholders, never claims them to be initialized thermodynamic states, and executes no SourceWetStorage.evaluate or RHS. Actual HEOS construction nevertheless performs its existing reference-anchor calls, observed by Root's separate hook.

`SourceRunControls` has integration_policy, event_policy, horizon, config_sha256, original_binding and check(). It builds fresh policy objects from the immutable config, takes water M from actual chemical.reference, and strictly checks every storage's public binary64 M. It retains the old float(H) conversion for initial and maximum reference-step size and separately stores exact H. It does not shrink an unrepresentable H or a below-minimum step.

## Root orchestration fields

- `config.values['study']`: selected_cell_index, start_seconds, horizon_multiplier, shared_dry_cell_index, shared_wet_cell_indices. Use `exact_config_fraction` for the two exact-rational mappings.
- `resources`: callback_cap=16, dry_path_callback_cap=24, total_callback_cap=97, wet_pressure_request_cap=16, outer_seconds=510. These are hard upper bounds for this profile, never post-failure extensions.
- `initial`: exact original N3 liquid/gas inputs, temperatures and original modes. All actual U evaluations and results remain Root-owned observations.
- Integration/event/roundoff policy sections map directly to their corresponding existing constructors. Only initial/max step and original source M are derived. Default tolerances remain relative=1e-8, N=1e-7 mol, U=1e-3 J; no field-label swap.
- Envelope, pressure/inverse policies and all geometry/transport fields are read from config. New liquid-table source_asset_sha256 records `('source_run_config_v1', config.sha256)`, not the older research runner SHA. This makes a new explicit experiment identity while keeping its original numeric relation and manufactured classification.
- Shared volume declarations are created by Root from the explicit selected indices and current live built.storages. Config/codec reading does not restore or imply live shared identity.

## Actual local verification

44 tests passed in 0.83 s; config-final01.xml/log and exact command/hashes in FREEZE.json. This includes a 17-file independent bundle, real package SourceWetStorage/SourceWetColumn/ExactSourceColumn construction with explicitly replaced Python provider factories, no initial-U/RHS or native-liquid calls, all numerical policy fields/source M, and old pinned make_case model_identity/envelope equality. The manufactured factory-seam test validates the public HEOS request arguments; it is not an actual HEOS execution result.

Original missing-module collection RED and unsupported WetMixedState pack setup failure are retained. The latter was fixed only in new builder binding by using the existing state's five explicit fields; no global registry/codec changed. No installed/native execution or commit was performed by this worker. Ruff/mypy/black/pylint are unavailable in the existing venv; all three Python files parsed successfully with the standard-library AST.
