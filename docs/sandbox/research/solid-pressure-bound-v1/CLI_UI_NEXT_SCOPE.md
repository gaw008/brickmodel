# CLI/UI next scope — read-only authoritative audit

Inspected the current repository while installed regression session 36717 is live. No tests, EOS, probes, imports, installation, runtime files or browser/server processes were run. Only this report was written. Command forms below are derived from actual source; they are not newly executed acceptance evidence.

## Current user-operable surface

`pyproject.toml` has exactly one console script: `sludge-vme = sludge_vme.cli:main`. It describes a research-only synthetic VME. `sludge_sandbox/__init__.py` only supplies a package description and version. There is no sandbox console entry, `__main__.py`, case loader, public run service, persisted experiment runner or local UI found in the tracked application sources. No frontend package manifest or local HTTP/UI application is present. Historical Brickops UI in another checkout must not count as this Goal's interface.

The existing **legacy synthetic** forms are:

```text
sludge-vme validate examples/tiny_synthetic.json --json
sludge-vme sources --json
sludge-vme forward examples/tiny_synthetic.json --fidelity L1 --out runs/tiny_L1
sludge-vme inverse examples/tiny_synthetic.json --budget tiny --out runs/tiny_inverse
sludge-vme verify runs/tiny_L1 --strict
sludge-vme benchmark examples/tiny_synthetic.json --out runs/benchmark
```

These follow `src/sludge_vme/cli.py:build_parser`, `command_sources` and `command_verify`. `verify --strict` does perform semantic replay through legacy `sludge_vme.models.simulate` in `sludge_vme/io/artifacts.py`; it is not a generic replay function for sandbox states or depletion ledgers. `sources` reads the legacy `data/sources.json` relative to the module's source-tree parents. It does not traverse an individual sandbox output's equation/parameter dependencies. That checkout-relative data lookup is also a portability concern to avoid in the new package, rather than copy unmodified. None of these commands meets the new complete-cycle requirement.

The root README expressly separates the legacy commands from the new sandbox. Its numerical test count is an old historical snapshot; use current run XML and module identities, not that paragraph, for current verification. The acceptance matrix still marks U01–U04 and A03/A05 pending; this matches the missing application layer.

## Existing sandbox interfaces that can be composed

| Actual Python interface | What exists | What it does not yet provide |
|---|---|---|
| `EvidenceRegistry.from_file/from_dict`, `.trace(node_id)`, `.assess(roots, context, mode=...)` in `evidence.py` | Strict JSON/DAG metadata, dependency traversal, source records, unknown/applicability blocks and explicit lanes | No CLI; no complete runtime material resolver or output-to-root registration; `source_assets=not_checked` and `scientific_validation=not_established_by_registry` remain explicit |
| `MaterialIdentity`, `MassAnalysis`, `FeedPortion`, `prepare_green_batch` | Distinct raw sludge/ash identity, declared bases, moisture bookkeeping | Presence of evidence IDs is not qualification, mineral reconstruction or a constitutive material pack |
| `SolidFluidHeat`, `DeformingSolidHeat`, `ProgrammedSolidFluidHeat`, `WaterPhaseTransfer` | Existing actual thermal/species/mechanical operators with strict identities | No universal JSON constructor or assurance these operators cover every required mechanism together |
| `ConservedState`, `IntegrationPolicy`, `integrate` | Actual accepted states, ledgers, breakpoints, failure status and cancel callback | No durable identity-checked checkpoint/resume; docstring explicitly assigns this to the application layer |
| `integrate_depletion`, `DepletionPolicy`, `DepletionResult` | Events, mode transitions, corrections, roundoff totals, refinement evidence and cancellation | No persistent cross-process continuation protocol preserving all cumulative budgets/event modes |
| `audit_conservation` | Independent checks for its declared ordinary integration contract | Do not assume it alone handles all depletion corrections and total-mechanical-energy semantics without an adapter/review |

No runtime `EvidenceRegistry` schema JSON was found under `data/sandbox` by the inspected schema search. Research candidate/source files are heterogeneous and the evidence-policy document explicitly prohibits treating their existence as material admission. `test_evidence.py` has a manufactured registry fixture, not a production material registry. A source-query Python call can be written today against a supplied compliant registry, but there is no delivered source-query command for the actual case result.

Actual joined wet operation currently lives in research scripts, including `/private/tmp/brick-reacting-wet-v1/run.py`. Its prepared/earlier command forms are:

```text
/private/tmp/brick-water-backend-probe/venv/bin/python /private/tmp/brick-reacting-wet-v1/run.py callback callback-attempt01
/private/tmp/brick-water-backend-probe/venv/bin/python /private/tmp/brick-reacting-wet-v1/run.py depletion0 depletion0-attempt01
/private/tmp/brick-water-backend-probe/venv/bin/python /private/tmp/brick-reacting-wet-v1/run.py depletion1 depletion1-attempt01
```

These rely on explicit test-fixture imports and fixed paths; they are research probe entrypoints, not application commands. They must not be run during the live regression, and existing attempt directories must not be reused. No newly successful wet trajectory or replay is asserted here.

## Smallest coherent application increment

Build one **shared case compiler and durable run service**, then put a CLI and Chinese local interface on it. This advances missing operating requirements using actual kernels, while scientific work continues. An interface that only displays existing JSON, fabricated evolution curves or synthetic full-cycle output would not advance the requested end state.

Suggested ownership/file boundaries (new implementation, not current APIs):

1. `sludge_sandbox/cases.py`: a versioned, strictly validated JSON case plus `resolve_case(...) -> ResolvedCase`. Include declared material/batch IDs and mass basis; explicit species columns; geometry; thermal/atmosphere/motion program; material parameter values/units/source-node IDs; requested mechanisms/outputs; numerical policy; time/resource limits. The supported builder list is closed and maps directly to actual kernel classes—no arbitrary dotted imports, pickle, dynamic expression evaluation or silently inserted physics defaults. A requested raw-sludge wet-to-cooled case retains every mandatory mechanism in its requirements. If chemistry, free sintering or cooling closure is missing, resolution yields a persisted `evidence_insufficient` or `capability_missing` result identifying exact dependencies; it does not drop a stage or substitute the manufactured A/B model.
2. `sludge_sandbox/application.py`: `validate_case`, `run_case`, `cancel_run`, `compare_runs`, `trace_result`, `export_run` as the sole business/application surface consumed by Python, CLI and UI. Compile actual operators and invoke the existing integrators. A separate explicit manufactured case may execute the already reviewed reacting/deformation or wet path; its identity and qualification stay manufactured in every output. This operational case does not satisfy the source-complete raw-sludge full-cycle acceptance condition.
3. `sludge_sandbox/run_artifacts.py`: write a started manifest before source resolution/native work, atomic immutable revisions and structured terminal failures. Persist original/resolved input, case/source/parameter/equation/software hashes, actual selected native backend identity, policies, platform, complete accepted trajectory, space/time coordinates, all event/refinement/correction/component ledgers, and a Chinese report. Keep `software_status`, `scientific_status`, `deployment_status` separate from execution status. Resource/cancel/unknown/domain/numerical failure and physical-constraint violations remain distinct. A domain error does not label the material infeasible.
4. `sludge_sandbox/result_sources.py`: immutable `output quantity -> equation node -> parameter/derived conversion -> citation/location/cache digest` mapping. Adapt reviewed provider descriptors and research-source metadata explicitly. Unknown dependencies have a reason and next evidence need, not an invented value. Registry metadata checks, byte-integrity checks and independent scientific validation remain separate statuses. A specific pressure or energy point must identify the actual model/run version and material sources; a generic bibliography panel is insufficient.
5. `sludge_sandbox/cli.py` plus an installed entrypoint `sludge-sandbox`: call the service, not test fixtures or legacy VME. Initial real operations should include `validate`, `sources`, `run`, `status`, `cancel`, `compare`, `export`, `resources`. Add durable `replay`/`resume` only with their verified semantics below, then `batch`/`sensitivity`/`search` through the same runner. Install legal runtime assets via explicit data-package or user-selected content-addressed cache paths; do not resolve them by assuming a checkout above `site-packages`.
6. A packaged local Chinese UI bound to localhost, sharing the service. First real journey: select case/material -> edit only admitted variables and temperature program -> preflight showing missing dependencies -> start actual run -> see accepted progress -> cancel or inspect preserved failure -> compare actual runs -> select time/cell/quantity -> view its trace and source location. Display actual trajectories/profiles only when produced. An uncomputed cooling segment or unsupported strength output stays visibly unavailable; no extrapolated filler or success badge.

Proposed commands below describe the implementation target, **not currently available commands**:

```text
sludge-sandbox validate cases/raw-sludge-full-cycle.json --json
sludge-sandbox sources --case cases/raw-sludge-full-cycle.json --quantity temperature_K
sludge-sandbox run cases/manufactured-reacting-deformation.json --out runs/case-001
sludge-sandbox status runs/case-001
sludge-sandbox cancel runs/case-001
sludge-sandbox trace runs/case-001 --quantity pressure_Pa --cell 0 --time 0.5
sludge-sandbox compare runs/case-001 runs/case-002
sludge-sandbox export runs/case-001 --format csv
sludge-sandbox replay runs/case-001 --out runs/replay-001
sludge-sandbox serve --host 127.0.0.1
```

The CLI naming should settle on either quantity tracing under `sources` or a distinct `trace`; implement and document the chosen actual forms together rather than carrying two inconsistent specifications.

## Resume and replay are real numerical contracts

Replaying from a frozen full initial condition is different from viewing a saved trajectory. Reconstruct the actual providers/operators and recompute, then compare with preregistered software-owned criteria. A changed software/native/source hash creates a new experiment/version or an explicit incompatibility result. Do not permit stored artifacts to choose arbitrary comparison tolerances.

Restarting `integrate` at `last_state/last_time` alone must not be advertised as exact persisted resume. A continuation record needs the accepted state and total-energy identity, material/provider/source identities, boundary/program time and side, active/depleted water mode, event/correction counts, signed/absolute/numerical-phase roundoff totals, cumulative component and conservation ledgers, already consumed wall/panel/rejection budgets, and next numerical scheduling state or a documented tested restart policy. Existing APIs may need explicit continuation inputs/results to carry these correctly; resetting budgets can make a failed event appear admissible. Cancellation should persist the last committed accepted checkpoint; a hard process stop records that only the earlier persisted checkpoint is recoverable.

## Experiment/search increment and completion boundary

After the shared runner exists, `batch` and sensitivity evaluations become sets of immutable case runs with separate statuses. Multi-generation search records candidate IDs, parent IDs, actual variable mutations, frozen objective definitions, seed, stops and all failed evaluations. Unknown strength/sintering metrics cannot be scores, and an all-inadmissible generation must remain so. DoE/sensitivity precedes expensive search; selected candidates require direct recomputation and independent scenarios. Reusing the legacy synthetic inverse engine without replacing its model/material/objective contracts would be a scope substitution.

The minimum application acceptance evidence should include clean non-editable install without tests on PYTHONPATH; identical resolved input/model and numerically consistent trajectories through Python/CLI/UI; real browser editing/start/cancel/failure/source-link and profile checks; tampered source, absent source, NaN/unit errors, missing material closure, out-of-domain cases, replay mismatch and interrupted-resume tests; success and failure artifact audits. A manufactured operating case proves these software paths only.

Goal sections 7/9/11 still require a source-complete domain explicitly containing raw sludge, actual wet-to-cooled full-cycle physics, public drying/reaction/sintering comparisons and held-out predictions, multi-generation execution and the same user-operable application. None of the proposed wrappers supplies missing chemistry, free-sintering/cooling constitutive laws, empirical validation or a material-admitted full-cycle case. Keep those original requirements in the case capability matrix and overall acceptance matrix until actual evidence proves them.
