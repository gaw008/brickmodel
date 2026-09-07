# Independent TP backtracking candidate review

Compared the complete candidate delta against production _heos_kernel.py and read surrounding state_tp/snapshot/transaction contracts, PLAN, test controls and candidate test runner. AST parsing and saved XML inspection only; no imports, tests, native EOS or production changes.

Reviewed SHA256: candidate `e2df0b8b7c7190ee9b40da5d9cbf4ec7be05801620b20fa6dbdaa260b457ebae`; test `9a88d49897f41b5056d04342fa43c7839fff6227377dc704dfed70e53007e398`; runner `d58d75e2d6b930e7ef12803eab83e1d7d22b8a9f1253800337bed2fe3a4e2eec`.

## Finding

[MEDIUM] Failed actual native trial has no retained attempted-density record

File: candidate_heos_kernel.py:308–315.
Issue: evaluate_density appends a diagnostic record only after native update and derivative/pressure/energy calls. If one of those calls raises, a real attempted trial has occurred but its density, fraction and iteration are absent from last_tp. PLAN requires tracking every actual trial separately. The invalid-native control confirms fatal propagation and actual call count but does not require retaining failed trial context. The original numerical failure is preserved, so this does not admit an invalid state; it loses the specific attempted state needed to diagnose a failing search.
Fix: append an attempted record with iteration/density/fraction before the actual native evaluation, then populate fields/status as they become available. Preserve the original exception and fatal behavior, and extend the native-failure test to require the failed attempt's identity. Distinguish incomplete records from fully evaluated residuals and from accepted states.

## Confirmed behavior

The original residual gate min(1e-4,rho*1e-7), phase/domain checks, finite positive slope, original undamped abs(log step)<0.1, native transaction, final snapshot and cleanup remain. Every bounded fraction is computed from the same accepted rho/direction; rejected candidates never become a new base. Gate passage or strict normalized merit decrease admits an iteration, while only original gate passage can reach the final snapshot. A passing final iteration uses the currently evaluated native state without duplicate evaluation. Accepted-state budget is exactly eight including seed, hence at most 1+7*6=43 density evaluations. Healthy seed/full-step paths retain one/two density evaluations respectively. The final-budget check now raises before an unused ninth update; this does not add a native evaluation or permit extra work.

Native/domain/source/invalid-slope failures remain fatal with no shorter-fraction retry. Source transaction exit must succeed before returning. Phase is restored in finally. Snapshot checks and saturation behavior are unchanged; no EOS/reference/target pressure/host bracket alteration is present. Existing source identity must be separately rebound if the candidate becomes production, since adapter bytes change.

The test runner explicitly loads the isolated candidate into the kernel import slot only for scripted no-native controls; this is appropriate to these tests and must not be used to bypass native source admission. Tests cover seed/full-step cost, same-base half-step, six-trial failure, native/slope/nonfinite faults, undamped oversized step, branch crossing, vapor dynamic gate, eight-state/43-evaluation bounds, source failures and snapshot failure. XML directly records candidate 26 tests passed in 0.072 s; corrected old baseline 15 tests, 5 failures, 10 passes in 0.074 s. The earlier unreachable saturation-ambiguity fixture is preserved and its correction is explicitly documented. Those are numerical-control results, not native candidate acceptance.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | info |
| LOW | 0 | pass |

Verdict: APPROVE numerical control structure with one MEDIUM diagnostic completeness issue to resolve before claiming every attempted native trial is retained. No production/native validation is approved by these controls alone.


## Exact attempted-trial logging correction

The MEDIUM finding is resolved in candidate SHA256 `c1ecb59c702382c78891f4fcf6b6ac5eb8c68cc57869b1e261ec8a3a4a796b12`. Reviewed the exact delta against preserved candidate-before-attempt-log.py. The record now exists immediately before native evaluation with rho, target pressure, iteration, fraction, accepted=false and status=started. Completed native evaluations fill their actual values and status=complete. Any exception marks the attempted record failed with original type/reason and is immediately re-raised; no retry or invalid acceptance is introduced. Pre-native density/domain failures remain uncounted as native attempts, correctly. A partially completed failing observation is explicitly distinguishable from a complete residual record.

The loop, trial count, original dynamic gate, strict merit rule, final snapshot and all source/cleanup behavior are untouched by this corrective delta. BaseException is caught only to add evidence and then re-raised, not swallowed.

Read expanded tests SHA256 `00a318a45ac03cefed581c158dee3b60f0157bf5ee6753c153ac3712a11d7559`. Native/slope/nonfinite/phase failures now require exact failed trial density/fraction, false acceptance, failed status and two actual calls. Same-density/same-merit stagnation must exhaust six trials without snapshot. Underflow-zero gate tests require an actual zero residual to pass and retain failure for nonzero residual; infinite normalized merit cannot admit an invalid state. Existing budget/source/snapshot assertions remain. Direct XML inspection records 30 tests, 0 failures, 0 errors, elapsed 0.064 seconds. This reviewer ran no tests, EOS or imports.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE corrected candidate and expanded scripted controls. The attempted-trial evidence finding is resolved; native source rebinding and independently preregistered native/coupled checks remain distinct gates.


## Production application and native-grid review

Verified source kernel is byte-identical to approved candidate c1ecb59c702382c78891f4fcf6b6ac5eb8c68cc57869b1e261ec8a3a4a796b12. Both applied test files are byte-identical to reviewed temporary copies. All four current hashes match source-binding-change.json. Actual diff outside the kernel consists ONLY of adapter_sha256 in the approved manifest and that manifest's resulting hash in water_heos.py and source JSON. Runtime/native files, fluid/configuration data, published references and physical constants are unchanged; this rebinds the approved numerical implementation without bypassing source checks.

Read the nine-case native test and supervisor. Fixed Cartesian neighborhood is T0 +/-0.001 K and P0 +/-0.01 Pa around the exact captured hex point. Calls use the public qualified provider and liquid branch. Assertions require returned T/P/phase, implementation binding, actual last evaluated density/residual and original density-dependent residual gate, within 43 diagnostic rows. Public return also necessarily passes existing snapshot/source guards. A module-scoped provider intentionally gives the same test-order history to baseline/candidate; prior isolated exact-point evidence separately establishes fresh-provider reproduction. importorskip means a missing CoolProp runtime would be skipped, not native success; actual reports must check zero skips.

The supervisor runs the same temporary nine-case source for baseline/candidate against installed code, with source-recorded inputs and 30-second cap, and requires complete status plus zero child exit. No candidate monkeypatch or alternate source bypass occurs here. Native testing still requires verifying the installed build matches applied source independently.

Direct XML inspection: applied controls 30 tests pass. Original-source native baseline has 9 cases, 8 passes and 1 failure at the captured central point, with no skipped cases; original failure remains preserved. Candidate native execution is not claimed by this review. No tests/EOS/source edits were performed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE exact production application, hash-only source rebinding and reviewed fixed native test runner. Candidate installed/native/coupled checks remain execution gates.
