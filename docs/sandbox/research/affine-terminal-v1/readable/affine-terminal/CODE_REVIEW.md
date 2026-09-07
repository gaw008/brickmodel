# Affine terminal initial code review

Read current integration/roundoff diff, surrounding observation/schema/binding/commit contracts and new integration tests. Clock helper is still worker-owned/in progress; this report does not give final clock certification approval. No tests, imports, EOS or production edits.

Reviewed snapshot hashes:
- src/sludge_sandbox/depletion_integration.py: `46e9f168fc81c43e55b6418c0cefa72b27cc080ec95997e9169c619fdf417ee0`
- src/sludge_sandbox/depletion_roundoff.py: `8ee6d7253397af8d4d28edf52198b0b041fdc341ee3a6f9e49c6ee7788270fec`
- tests/sandbox/test_affine_depletion_integration.py: `1e9df186435a7fa899df264a7c1f2a7fbb1e86d5ac9930d6e22b5e81356c940f`

## Finding

[HIGH] Affine terminal can commit a stale original operator when nested approach is disabled

File: src/sludge_sandbox/depletion_integration.py, affine_terminal final binding check / with_depleted_cells, and event commit checks.
Issue: terminal_method=affine_midpoint is valid with nested_approach=None. The final affine binding check occurs before with_depleted_cells. A switch callback can return a new operator retaining the old source/contract while changing the original operator descriptor. All later event/common observations then use the new operator. Existing outer pre-independent/precommit root checks run only when nested is enabled; the affine-only mode can therefore commit a speculative path whose original source binding changed during the final terminal switch or subsequent comparison. This is the same concrete stale-parent-operator mechanism previously caught by the spine boundary faults, now reachable in a newly supported affine-only configuration.
Fix: retain and validate the original root/operator binding through the entire affine proposal and precommit boundary independently of whether nested reuse/refinement is enabled. Check after switching as well, and avoid rebaselining a mutated source during horizon restart. Add boundary-timed source_ids/deterministic_contract mutation regressions with nested_approach=None and require no event/correction/mode commit. Existing nested modes should retain their checks.

## Confirmed arithmetic and scope

Both midpoint predictor and final affine update include every face-species, face-energy, reaction-species and cell-power field. Final fields and component quadratures use exact Fraction interval arithmetic before binary64 storage. The reconstructed inventory polynomial checks endpoints and any interior minimum, so endpoint positivity alone does not conceal a competitor crossing. The gross evaporation integral uses the positive part of the signed affine transfer observation, handles an interior sign crossing, and rounds downward before using it in correction budgets. It is not replaced by net depletion.

Roundoff acceptance still checks original absolute/fraction/storage/element/mass budgets and panel reconstruction; the new clock evidence adds only a conditional numerical clock residual allowance with exact term matching delegated to the helper. Cancellation/resource guards run before/after actual observations and before phase switch; speculative path construction still avoids global commit until original prefix audit. Failure propagates through the established result boundary. Unknown terminal method strings are rejected. This review does not assert coverage of arbitrary malformed Python container objects, nor require expanding the supported API beyond its declared values.

Current tests cover independent constant/linear evaporation roots, reacting spectator/energy, real midpoint failure rollback, terminal selector rejection and relative work reduction. They do not cover the affine-without-nested source-binding boundary identified above. No runtime result is claimed by this read-only inspection.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — resolve the new affine-only source-binding hole before final approval. Clock/helper final review remains pending stable bytes.


## Root source-binding fix and independent guards

The HIGH affine-only binding finding is resolved in inspected integration SHA256 `4bea596f4a2b9dcd5d04aa398fa28a80ca5efa6c80e67fc93235f8f822edb220`. The affine terminal retains original_op and validates its old binding after switch and after event observation. Root proposal binding is now captured for affine even when nested_approach=None, checked before any horizon rebinding and immediately before commit. Original nested checks remain. This prevents a returned dry operator hiding a mutated original descriptor.

Implemented only the independently owned test_affine_depletion_guards.py, SHA256 `4748539c668a2227cd4778cab303942ca664449fd126644d64692bde8af27e3e`. It adds 12 source/contract boundary faults over None/uncached/cached modes, dynamically schedules each fault at the actual final switch or final common-time comparison observed in a successful baseline, and checks no event/correction/dry-mode commit plus complete cost accounting. Three tests trigger cancellation after the actual wet midpoint observation and require cancelled status with retained wet prefix. Six malformed method cases require explicit rejection. Fixtures use original policies and remove program knots solely to isolate these boundaries, without the unrelated .005 cap/knot failure or numerical-gate changes.

Actual reviewer-owned no-EOS execution completed session 63019, exit 0: 21 tests passed, XML elapsed 25.819 seconds. Evidence: guards/first-tests.xml and guards/reviewed-hashes.json. No native provider/model EOS was invoked and no integration/clock source was modified by this reviewer. Root was asked to arrange an independent cross-review of this newly written test file.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE the root's source-binding correction with independently passing guard/cancellation regressions. This resolves the reported HIGH item; final clock certification and broader numeric/native validation remain separately owned gates.


## Final stable helper, clock and V5 preparation cross-review

Read final pure-Fraction helper extraction and strict type(method) is str validation. Inventory minimum uses endpoints and only an interior convex vertex; gross transfer splits at an interior affine zero and integrates positive subintervals. The eight small parabola/triangle tests use closed-form known answers, including positive endpoints hiding a negative interior and zero net transfer with positive gross area. No threshold or integration behavior changes in this extraction.

Cross-reviewed the final worker clock and tests. Certificate is immutable and binds start_inventory_mol explicitly. End-relative inventory and each individual rounded panel term are checked with exact Fractions; matching only net terms cannot authorize a different ledger. Monotone derivative endpoints establish a decreasing polynomial over the enclosure. Ordered-float binary search chooses the largest represented endpoint with nonnegative residual in at most 64 steps, and revalidation requires the immediate next representable point to be strictly past the root unless endpoint is exact. Exact-next-root skipping and insufficient time budget are rejected. The residual allowance is conditional on this numerical interpolant and is not an ODE accuracy certificate. No mutable cached certificate state remains.

Tests independently cover constant, irrational and decelerating roots, nearly-zero quadratic coefficients, large/negative time origins and actual represented midpoint separation, exact maximum root, inventory/term mismatch, invalid/empty/rate-shape inputs, unresolvable midpoint, nonmonotone enclosure and too-small clock budget. No new confirmed defect was found. Final targeted XML is directly inspected: 99 passed, no failures/errors/skips, 34.213 seconds. Prior nonlinear strict-fixture failures remain historical evidence, while the passing independently resolved nonlinear check does not alter wet experiment gates.

Reviewed final snapshot hashes:
- src/sludge_sandbox/depletion_integration.py: `bb8c9c04a595c22d187d2b9858ca4607622e52955f165f089b3e33bedfaa89f3`
- src/sludge_sandbox/depletion_roundoff.py: `8ee6d7253397af8d4d28edf52198b0b041fdc341ee3a6f9e49c6ee7788270fec`
- src/sludge_sandbox/affine_depletion_clock.py: `0475e625120811a457dd4bb21e03c262d7fcf9986ecfe7afc28683ac765f242a`
- tests/sandbox/test_affine_depletion_clock.py: `161a2900c10bbec9c9a48f1751219e065ee274f7a34ec979b04e5207a8495bd7`
- tests/sandbox/test_affine_depletion_integration.py: `b5f9661c77ecf3ccd888e3ba5bd900b8b294e180e4f08fbaf64be34df2a2bb6f`

V5 preparation: four callback/depletion/compare/run scripts are byte-identical to v4; fixture differs solely by adding terminal_method='affine_midpoint' to event policy. All five script hashes match PLAN. Original physical inputs, nested independent check, budgets, gates and ordered fresh-callback execution remain. source-freeze.json is explicitly a pending placeholder with null installed evidence, and PLAN correctly prohibits EOS until actual installed43-module identities and source freeze are supplied. This review approves preparation and install verification; it does not claim that still-pending freeze metadata is already valid or that a V5 callback/trajectory has run.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE reviewed affine implementation/clock and V5 preparation. Execute only after actual installed source freeze metadata is verified. Original reported source-binding issue is resolved; native wet/cross-cap/full-regression acceptance remains outstanding.
