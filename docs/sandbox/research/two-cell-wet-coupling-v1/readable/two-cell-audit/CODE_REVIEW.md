# Two-cell frozen experiment and independent ledger review

Read all four scripts, PLAN, root's audit_ledgers.py and relevant existing transfer/transport/storage interfaces. AST parsing, file hashes and source reads only; no imports/tests/EOS or production edits. Verified all four PLAN script hashes, all 43 source/installed module pairs and declared water asset hashes. Reviewed PLAN SHA256 62c6f72747182d7da123d5d8e2afa527e61a4ca15c0d9918dd6f915db4910885.

## Finding

[MEDIUM] Failed independent ledger audit writes no failure artifact

File: /private/tmp/brick-two-cell-audit-v1/audit_ledgers.py, main block and audit function.
Issue: audit() completes all assertions before main creates output. An invalid prefix aborts with no audit JSON, input hash, failure reason or retained progress, while successful inputs get a hash and report. Original trajectory data remains preserved, but the independent failure itself cannot be traced through the intended artifact workflow.
Fix: create a report with input hash before validation; catch audit errors, retain failure type/reason/traceback and completed prefix progress where available, always publish audit JSON, and preserve nonzero exit on failure. Do not relabel failed/partial original trajectories as completed.

## Confirmed experiment and ledger contracts

The two-cell fixture expands storages, reaction bindings and transport coefficients consistently; reference length .02 m / 2 cells / area .01 m2 yields original per-cell volume 1e-4 m3. Distinct skeleton cell indices 0/1 bind to the same prescribed motion and current reacting storage reconstruction. Water interface_modes remains None from the helper, so its existing property correctly expands to two existing_liquid modes under the new host. Two actual interface coefficients remain nonzero. Ea=0 and manufactured transport/solid parameters are accurately scoped.

Snapshot uses already decoded host states to reconstruct transport._face and samples actual species caloric curves for face-temperature enthalpies, without adding a second thermal inverse. It is explicitly not an independent flux oracle. Carrier molar mass/enthalpy come from actual providers rather than invented constants, and zero bare carrier diffusivity is not treated as local carrier conservation. Reaction config/current storage and inverse-reuse identities are recorded and asserted. Current geometry/transport data needed for independent reconstruction is serialized.

Each mode requires its own fresh callback, passed status, exact initial state and energy identity match. The supervisor rejects existing result files and attempt reuse, snapshots same-mode callback for wet runs, and retains 30-second callback / 120-second integration / 150-second external limits with 100 steps. Both refinement caps are fixed; no automatic second trajectory or retry is present. Full IntegrationResult is saved before successful-completion or wet-inventory assertions. Final snapshot incurs one explicitly declared extra evaluation within external budget; success remains passed_pending_independent_ledger_audit. Failed construction/evaluation/identity states are saved with traceback in finally.

Independent audit reconstructs local species/energy ledgers using Fraction arithmetic and correct opposite uses of the shared internal face. Exact component sums and cumulative component residual are checked, along with global sealed water/carrier and energy-minus-work balances. Carbon and manufactured first-order A are checked per cell. It does not invent carrier elemental composition or mass. Failed/empty-prefix results may have all_saved_prefixes_pass=true only vacuously; solver_status is separately returned, so root must require actual completed solver/end time and mode-specific transport evidence before acceptance. This script is ledger arithmetic, not the separate transport formula or cross-mode/cap uncertainty audit.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | info |
| LOW | 0 | pass |

Verdict: APPROVE frozen experiment preparation and bounded callbacks/trajectories. Resolve independent audit failure-artifact gap before relying on that script as the complete auditable acceptance record. No native outcome is claimed.


## Ledger audit failure preservation resolved

Reviewed corrected audit_ledgers.py SHA256 `1858722f7d1cf8097ce9f8bd4b3fd019156ca141c81dbd1ca0c986212afc9aa3`; AST parsed without execution. Input hash is recorded before validation, errors retain original type/reason/traceback and partial verified-prefix list/current index, finally publishes JSON, and failure exits nonzero. trajectory_completed is separate from prefix_audit_passed so an intact failed-run prefix is not misreported as a completed solve. Original arithmetic thresholds and internal-face signs remain unchanged. MEDIUM finding is resolved; approve this corrected saved-JSON audit. Callback formula auditor remains pending preparation/review.


## Callback formula auditor cross-review

Reviewed audit_callback.py SHA256 `91018c52c72400f5a281a5bb595b8d257d76c9fedc38a8cfffe4dd1da81a4e95`, ALGEBRA_POLICY and relevant gas-face/Fourier/enthalpy assembly definitions. Standard-library AST only; no callback audit or EOS executed here.

The independent saved-data reconstruction derives concentration from N/V, mixture fractions/mass/density/ideal pressure from actual sampled constants, and the face mixture with actual geometry-weighted T/P/X and normalization. Species diffusion uses the correct serial coefficient and total face area, and upwind mass-frame correction donor matches the sign of the opposite total uncorrected mass flux. Carrier counterflux is permitted despite zero bare carrier diffusivity. Fourier uses half-cell resistances. Energy sums conduction plus diffusive species enthalpies sampled from the actual curves at face T; Darcy/advection must be zero. Both observed model face records and assembled rate arrays are checked, and coupled/control mode effects are explicit. This remains arithmetic validation of sampled source properties, not an independent caloric or temperature oracle.

The check bound is the frozen 1e-12 relative plus 64 summed ULP rule; its post-pilot adoption is disclosed by policy and is not retroactively called preregistered. Every check retains actual/expected/error/bound and failed checks stop with evidence. Input/plan/policy hashes are recorded before validation. Existing output is protected, final JSON is atomic, failures retain partial checks/traceback and exit nonzero. No source mutation, provider import or extra EOS call is present.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE corrected ledger auditor and frozen callback formula auditor for saved-JSON execution. Prior MEDIUM is resolved; actual audit outcomes and trajectory comparisons remain separate evidence.


## Archive adaptation

Reviewed archive helper SHA256 `65300d5259c610a70de4c143d97f7236b98dde803c05dbde92dd2428ca350c22` against the approved affine/V5 helper: exactly two SOURCES directory/key substitutions, no logic change. Existing fresh destination, exclusion/symlink, terminal supervisor cleanup, ZIP/source reread hash, membership stability and failure-manifest safeguards remain. Approve execution only after all EOS and audit/report writers have completed and frozen; the helper cannot independently fence unsupervised writers. No archive execution performed here.


## Four-run comparison static review

Reviewed compare_runs.py SHA256 `4328237930555682318b2f1a506318bd33ce5f15ea58d93165e49fc82398953f` and fixed comparison contract in NUMERICAL_REVIEW.md. AST parsing only; no script execution or EOS.

Amount/energy indicators implement exactly D > 4*max(sum of two within-mode cap differences, sum of two actual local integration scales), using Fraction arithmetic on saved numerical values. Temperature implements each R as within-mode cap difference plus both inverse bounds, then D > 4*(fine coupled/control bounds + R_c + R_z). Decoded interval separation is reported separately. Signs and per-cell outcomes are preserved; gradient magnitude decrease is explicitly nominal. Phase-rate differences remain unresolved without a certified sensitivity interval, regardless of nonzero observed differences. Unresolved screens do not force the comparison into physical success or failure.

Before calculating effects, all four saved runs require passed script status, nonempty completed solver/horizon and matching initial/final snapshot states. Ledger audit status/completion and exact run-byte SHA must match. Same-mode initial state/energy identity is exact; cross-mode registered N and inverse-enclosed T match without incorrectly requiring transport-dependent identities equal. Geometry/motion, water implementation/assets and dependency versions are checked; observed module hashes must belong to the registered 43-file snapshot. Exact policy equality allows only each prescribed initial/max cap change. Lazy module expansion is allowed while every observed file remains bound. No original physical/integration gate is relaxed.

Failure preserves hashed input records, completed gate/indicator progress, original exception/traceback and atomic output with nonzero exit. Existing output is protected. The status comparison_completed means the registered empirical screens were calculated, not that every effect resolved. Root must separately retain callback formula audit and supervisor actual before/after hash evidence; this comparison does not replace them. Reading saved hashes alone is not a new live-source verification, accurately consistent with saved-JSON-only scope.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE frozen compare_runs.py for saved-JSON execution once root confirms all four completed ledger audits. Archive helper remains approved only after all EOS and audit writers stop. No comparison or archive execution performed by this reviewer.
