# Measured native verification cost: bounded implementation proposal

Design only. No production edits, source/provider construction, EOS, setter, installation or physics rerun was performed. Read `review/SOURCE_CACHE_BOUNDARY.md`; retain its original content and validation timing boundaries.

## Measured evidence

Parent `rhs01` is one actual diagnostic three-cell RHS, 0 accepted steps, 4 new constructors, full original RHS payload equal. RHS 6.382242 s; `_transaction` 4.613 s cumulative / 4.374 s self across 4,090 generator executions (entry+exit of 2,045 kernel state_tp calls). Saturation solving was 0.170 s and 1,086 Arlabosse source checks 0.732 s. This establishes this observation's hotspot, not all ordinary-trajectory costs.

`measure_runtime_getters.py` made exactly 32 config getters and 32 Water JSON getters in existing CP 8.0.0, with no extra warmup calls. All actual results matched the approved manifest. Config was 1,256 bytes, Water JSON 76,556 bytes. Mean per call:

- Config getter: 0.019389 ms; original parse/sort: 0.023613 ms.
- Water JSON getter: 1.095146 ms; encode+SHA256: 0.035352 ms.
- Complete original one-sided transaction check: 1.173500 ms.
- Fluid parse+canonical hash, separately measured: 2.083824 ms. This is constructor-only work, NOT transaction work or claimed savings.

Water JSON retrieval is 93.3% of the measured check. 4,090 times that complete-check mean is 4.800 s, similar to the profiled 4.613 s despite different instrumentation. This is an estimate, not an achieved speedup. Full measurement process: 0.690490 s including 0.585846 s CP import. All samples are in `RUNTIME_GETTERS.json`.

## Contract that cannot silently be changed

The current `_transaction` acquires an instance RLock, fully checks config then fluid, preserves per-operation warnings, runs original native arithmetic, then on normal completion checks warning, fluid and config. Its post-yield statements are skipped on body exception. Preserve this default path, including its exception behavior.

That RLock protects `_flash`, `_check` and diagnostics for one candidate. It does not intercept raw CP global setters from other code. Installed primary headers expose `set_config_*`, `set_config_as_json_string`, `add_fluids_as_JSON`, `set_reference_state*`; no mutation lease/generation counter is used. A ContextVar, Python lock, thread-count test, monkeypatched Python setter or GIL assumption cannot prove transient mutation exclusion. Outer entry/exit hashes cannot detect a change restored before exit. Even original checks sample boundaries rather than continuously authenticating memory.

Therefore an arbitrary in-process `with verified_scope(...)` suppressing inner checks is NOT equivalent to the original guarantee. This limitation must remain explicit, not hidden as a cache.

## Recommended smallest path

An explicitly selected **managed single-RHS mode**, in a dedicated single-executor process running the closed approved RHS graph; ordinary public Python calls retain per-call checks by default. Reuse an existing supervised source CLI process if it has this lifecycle. If needed, add only a narrow source worker entry, construct providers once there, and account for actual constructor/anchor costs. Do not spawn a process per point/RHS or create a generic RPC framework.

The worker accepts data, never arbitrary callables/native objects, and executes no foreign observer or CP setter during the admitted RHS. The parent can signal cancellation/deadline and receive records. Isolation prevents client threads from changing worker CP globals; worker code must itself remain closed and setter-free. This is operational isolation, not cryptographic attestation or protection against hostile native code inside the worker. If the condition is unavailable, keep original checks. A weaker in-process boundary-only mode would be a separate assumption, not the recommended default.

Private interface sketch: a managed entry creates a non-deserialized `ManagedNativeExecution` lease bound to actual runtime and original deadline; `ExactSourceColumn.evaluate` opens `native_rhs_scope(lease, adapter, state, time)` internally once per actual RHS. Existing `evaluate(state,time)` and `__call__` signatures stay unchanged; unconfigured execution is a no-op scope and original per-call checks. Record the new execution mode/version explicitly. Never extend a token over a whole run, integral, pause, replay or resumed session.

First admission may be limited to the actual closed SourceWetColumn path profiled here. Arbitrary provider subclasses and user boundary callbacks are excluded. Programmed paths remain default unless their closed graph is separately confirmed. Mixed-mode clones retain the same actual water objects. Constructors, initial-U work outside RHS, standalone water calls and the wet-pair collector retain old checks in the first slice.

### Entry and inner operations

1. Emit `rhs_started` and run its external sink/resource admission before opening. Failure after this point preserves that actual attempt count.
2. Bind PID/thread/context, exact adapter and all actual reachable thermal/chemical kernels. Deduplicate only actual object identity. Equal digests cannot merge independent flash objects or admit a later replacement.
3. Acquire one managed runtime lock then kernel locks in deterministic order. Any participating default call must follow the same runtime-before-instance order. Reject nested RHS/wrong owner; never hold locks across observers, IPC waits or pauses.
4. Recheck original collaborator bindings and complete config/fluid values against each kernel's pinned expectations. Initially per-kernel getter pairs are cheap enough. A shared getter pair is valid only for the same actual CP module and identical expected values compared against EVERY actual member. No cached getter value.
5. Inner `_transaction` retains its original lock, warning context, phase reset, arithmetic, point diagnostics and local `_guard` checks. Only full global getters are omitted inside a live admitted token. Outside it, original path. Do not cache Cp, saturation, states, errors or model identity in this slice.
6. Limit scope to one finite configured RHS under the original deadline. Do not turn observed 2,045 calls into a universal cap. Any extra point cap needs prior registration from audited loop bounds; actual attempted work and elapsed remain charged.

### Exit, failures and publication

Open after `rhs_started`; close BEFORE `rhs_returned` and before returning rates to the integrator. The current closed SourceWetColumn/inverse/kernel path has no source observer event inside it. Wrapping all of current evaluate externally is unsafe because it emits rhs_returned before outer verification.

Retain actual computed evaluation locally. On normal completion fully recheck fluid/config and collaborators, then revoke token/release locks, then emit the return. Exit verification failure uses rhs_failed with that actual candidate and no success event. On body error/cancellation/warning, revoke in finally and attempt exit verification; preserve primary exception object/type plus secondary verification exception and completed diagnostics. No rerun to fabricate evidence. New scope failure semantics are explicit; default generator behavior remains unchanged.

External observers execute outside the scope, so their mutation cannot occur mid-admitted RHS. A failing observer preserves the completed return through current observer semantics; later mutation is detected at next entry. Provisional inner observations are not a verified RHS. Timeout/kill/missing exit validation leaves an attempted failure, no accepted step/checkpoint. The integrator receives rates only after successful verification. Do not extend this token to wet-pair collection, which has cancel callbacks between requests, without separate review.

## Concrete source changes and identity

Small coordinator, e.g. `_heos_rhs_scope.py`; scoped branch in `_heos_kernel._transaction`; exact-source internal entry/exit seam; managed execution owner/selection. No pressure, inverse, caloric equation or integrator change. Public default behavior remains.

Kernel source SHA is pinned by the approved manifest; water_heos pins that manifest and embeds implementation identity; source_run_config pins the asset. Real code changes require a separately reviewed version/manifest and execution provenance. Preserve old manifest/evidence; never overwrite the old approved evidence or bypass hash checks. A changed kernel/wrapper cannot honestly retain its old implementation hash. If the old artifact must stay live-loadable, version artifacts. Compare numerical/diagnostic projections explicitly while retaining expected new implementation metadata. Original reference coordinates, physical constants, error budgets and all material/source/event qualifications stay unchanged.

## Bounded validation

Pure fake-metadata/native-body seams first: default pre/post calls/order/warnings/errors; scoped one-body execution and exact live membership; equal-digest foreign kernel/wrong owner/nesting/leaked or closed token; deterministic lock order; persistent entry/exit config/fluid mutation; body failure plus secondary exit failure; actual candidate retained on exit error; observer only after closure; cancellation/deadline preserves actual cost and never commits. Restored transient mutation is NOT claimed detected: validate the worker isolation/closed-code admission that excludes it. No package-wide monkeypatch as proof.

After independent review, rerun only the same actual RHS under the newly registered implementation and original state/policies. Compare full numerical arrays/Fractions/response residuals/branches/diagnostics, separately noting declared implementation/execution identities. Measure actual getter counts and whole RHS time again; the 4.6 s estimate is not a promised saving. No automatic retry, enlarged budgets or looser tolerance. Broader ordinary execution follows only after this finite gate.

## Hashes and peer review

- rhs01 RESULT: 5e2addb79d727f85903f45be5b981ded178da69cf8fe45b6877c235d8ace535e
- rhs01 PROFILE: ec5b3e9e9c75bd6975efe932d566589ee37ec4298fc0dbb5d58b1caa5a0aaf64
- Getter script: f92c0cddff06d120bbf8c1afcadbd4f2c60343451a5c042e9e98a6e845f72038
- Getter results: e6ec60eefeebed58ff23e8174fdaa53de5bcfe55847357dd03775be45e9e0461
- Read kernel: c1ecb59c702382c78891f4fcf6b6ac5eb8c68cc57869b1e261ec8a3a4a796b12
- Read wrapper: dd3e742e0fd143fa092b0f483b0a6fe22504d6b1d10cf9746d7598055ed35cad
- Read exact adapter: 5060f304fedf9ccf7b78c463394c95e38f78fa22d08b99e763e527a2ee2ba944

source_trial_code_review independently confirmed these lock/global-setter, exact-object, observer/publication, warning and failure boundaries by message. No implementation is approved by that design concurrence. No static-analysis dependencies were installed.
