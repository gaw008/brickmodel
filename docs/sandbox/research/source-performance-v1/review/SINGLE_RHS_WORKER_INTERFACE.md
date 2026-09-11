# Minimal dedicated source RHS worker

Read-only interface review of baseline 86d9733 and the current observation-record extraction. No worker or EOS was executed. This is a fresh implementation-equivalence experiment at a saved physical query, not cross-version source-session resume.

## Reuse the actual constructor

`source_run_builder.build_source_run(config, assets)` is sufficient. It validates the explicit config and asset bundle, constructs the original real fluid/caloric/chemical/transport objects, and creates three distinct SourceWetStorage/volume objects. The four HEOS constructors perform their actual reference anchors. The returned `unset_energy_states` are zero-U placeholders and must not be evaluated or substituted for the saved query.

The minimal worker operation is:

1. Parse the closed data-only request; validate the exact config and copied asset bundle with `load_source_run_config` and `validate_source_run_assets`.
2. Under the fixed internal observer, call `build_source_run` once. Preserve started/kernel-returned/wrapper-returned and failed constructor events.
3. For each actual new storage, call `storage.state(saved_nl, saved_gases, saved_U)`, then `built.adapter.pack(states)`. This associates the exact preserved physical coordinates with the fresh energy-model identity; it does not restore an old live object.
4. Convert only the explicitly saved `depleted_no_nucleation` cells through `adapter.with_depleted_cells(state, indices)`. Its original zero-inventory and mode guards remain. Require the final full mode vector and species order to equal the saved query.
5. Call one `adapter.evaluate(state, ExactEventTime(saved_fraction))`, with a fresh exact clock. No initial-U evaluation, source probe, root study, terminal operation, integrator, accepted step, or end-time calculation is needed.
6. Retain complete actual input, output or failure, counters, old/new implementation identities, all diagnostic fields and scope. Shut down the dedicated process after this request.

Do not call source_run_service._execute: it initializes U and executes the old event experiment. Do not call build_source_controls: a single RHS needs the pressure/inverse/physical parameters already in the column, not a probe-derived integration horizon. Do not bypass open_source_trajectory's same-runtime guard: that API remains for its original contract; use a separately named single-query experiment.

## Request and admission

The smallest useful transport carries a closed schema/version, canonical config, explicit verified asset-bundle reference, exact saved time, float64 N (3×4) and U (3), full modes and species order, and an origin/equivalence declaration. Preserve old sample/context/parent-study SHA and runtime as provenance. They do not authorize restoring old object IDs or calling arbitrary code. The controller preparing the request should read the saved parent through the existing passive artifact/association validator and extract the actual first continuous RHS input; do not claim an input hash alone validates an entire source study.

Reject unknown fields/classes, callable/module/pickle input, noncanonical rational time, bool-as-int, nonfinite or malformed float buffers, missing or reordered cells/species, mismatched config/assets, unsupported mode, nonzero inventory in a requested dry cell, and stale request bindings before actual construction where possible. Use the existing bounded regular-file JSON reader and immutable publication writer. The worker owns its observer; accept no user-supplied callbacks, cancellation functions, or plugin hooks inside the managed physics scope. The supervisor owns termination and request-level limits.

Keep the actual original parent counts/wall as reported historical cost, with this worker's four constructors and one RHS in separate explicit counters and, if required by the experiment, an aggregate debit. Do not relabel historical elapsed time as worker compute time. Preserve original 97-RHS/16-wet/510-s constraints and the separately preregistered one-request timeout. If construction, entry verification, evaluation, exit verification or journal publication fails, return a failed/partial measurement with actual prior attempts; no retry or extra query is implied.

## Implementation identity must change honestly

The wrapper descriptor binds wrapper source bytes and the real-fluid descriptor, and SourceWetStorage.binding includes provider implementations. Consequently a new approved kernel/wrapper manifest changes water implementation, storage identity, stored-U identity, and the wet/dry column/operator identities even when every physical formula and input is unchanged. Create new states from the saved numerical U using the actual new storage; keep the old record unchanged. Require equal references, constants, caloric reference, dry mass, V/eV, every envelope/error, physical table, pressure/inverse policy and units before treating the numbers as the same physical query.

`SourceRunAssets.files` must equal the explicit REQUIRED_ASSETS tuple. Updating the approved manifest requires a separately copied new bundle and a correspondingly explicit config asset row; do not rewrite old parent assets. Changing that config asset row also changes config.sha256, and builder._liquid uses that SHA in the mobility relation's `source_asset_sha256`. That derivative provenance change must be declared alongside the implementation changes, even if the physical table remains identical.

For comparison, keep the complete unmodified old and new raw evidence. Compare every physical float by exact bits, all Fraction coordinates, numerical residuals/iterations/error bounds, rates, mode and source labels, and full shape/order. Separately enumerate the exact authorized old→new implementation/config identity values and descriptor paths. Do not remove every field named identity/hash/implementation or broadly drop metadata: that could hide changed references, numeric limits, input error bounds, or material claims. If equality fails outside that finite mapping, the result is a retained mismatch, not a new pass tolerance.

## Managed scope boundary

An instance RLock does not stop raw CoolProp global setters. Aggregating full per-call checks into one RHS entry/exit check therefore needs an explicit dedicated single-executor, closed-operation assumption; it is not an equivalence proof for arbitrary in-process contexts. Keep the default public state methods' full per-call checks. Register actual kernel instances, prevent accidental nesting/concurrent context leakage, retain per-call locks, warning capture, phase cleanup and numerical checks. Enter after the original rhs_started observer and leave before successful rhs_returned publication. A failed exit check must retain any already-produced evaluation as failure evidence, never a certified success; the primary and secondary errors both remain available.

## Focused acceptance after implementation

- Closed request and malformed input reject before the first provider constructor.
- Exactly four real constructor anchors and one RHS; zero initial-energy and zero integration steps. Construction and late failure events retain actual counts.
- Three independent storage/volume objects survive the original binding checks; selected dry cell and the two wet cells use the original saved state coordinates.
- Full same-query physical and numerical output comparison, with a finite explicit implementation/config identity delta; no blanket metadata exclusion.
- Default nonmanaged path retains its existing before/after mutation/warning checks. Managed scope has explicit entry/exit, nesting/thread and secondary-error behavior.
- Supervisor timeout/publication failure is a partial failed experiment, never accepted evolution, material validation or resume authority.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: design interface recommendation only. Actual new worker/scope implementation still requires review; no new physical run approved here.
