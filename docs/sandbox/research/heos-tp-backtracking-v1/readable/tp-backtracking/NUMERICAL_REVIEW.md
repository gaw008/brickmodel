# Independent TP backtracking numerical/Python review

Decision: APPROVE candidate code for the next controlled integration/qualification stage, with the test-coverage limitations below. No EOS or test execution was performed by this reviewer. This is not approval of completed native validation or the wet model. The existing approved manifest cannot qualify changed source until the parent explicitly updates the reviewed identity chain.

Reviewed candidate SHA256: e2df0b8b7c7190ee9b40da5d9cbf4ec7be05801620b20fa6dbdaa260b457ebae.
Reviewed test file SHA256: 9a88d49897f41b5056d04342fa43c7839fff6227377dc704dfed70e53007e398.
Reviewed isolated runner SHA256: d58d75e2d6b930e7ef12803eab83e1d7d22b8a9f1253800337bed2fe3a4e2eec.
AST parsing passed for these three files. The exact source diff affects only the TP iteration body; saturation, transaction, snapshot, reference and source checks are unchanged. Static linters were unavailable and not installed.

## Numerical and native-state proof

The seed is evaluated exactly once. The loop visits at most eight accepted states indexed 0 through 7. At each nonconverged state before index 7, one search considers no more than six fixed fractions; at index 7 the function raises before computing another direction. Hence 1+7*6=43 actual density evaluations is a hard bound for this body, distinct from constructor, saturation, PT seed and snapshot work.

Every search uses rho and slope from the last accepted state. Rejected proposals mutate the native flash but never the accepted base variables. The next proposal always evaluates base_rho*exp(fraction*base_step), so it does not depend on the previous rejected density. After selection, the accepted candidate is already the flash state; its observed residual and derivative are carried forward without duplicate evaluation. On convergence, the final _snapshot therefore sees the last accepted actual native state, not a rejected trial. No interpolated thermodynamic state is introduced.

The original full-step abs(step)<0.1 check occurs before damping. Positive density, original saturation branch, finite positive slope and residual checks remain; trial phase checking is strengthened. Any domain, native, slope or phase failure propagates rather than trying a smaller fraction. The original phase finally, final density branch, _snapshot/Table-3 conditions and original source/config transaction surround the candidate unchanged. A transaction-exit failure prevents return even after snapshot computation.

The acceptance test permits a measured gate pass or strict normalized-merit reduction. Only a gate pass permits the outer loop to reach _snapshot. The exact gate min(1e-4,rho*1e-7) is retained. Zero-gate handling does not create acceptance for a nonzero residual; infinity merit is a control value, not a widened tolerance. A failed six-trial search raises explicitly. Healthy accepted full-step arithmetic retains the original expression and actual state. Diagnostics mark rejected completed observations and selected observations separately; native update failures can precede a completed observation, as documented, without implying an unobserved record.

## Independent test evidence and limitations

Read actual XML: first fixture baseline 15 tests/14 failures; corrected baseline 15 tests/5 failures; candidate plus existing coexistence controls 26 tests/0 failures. The test harness replacement is confined to the temporary process and does not modify production source. Parent's recorded pressure-fixture correction preserves dynamic residual gates and fixes the synthetic fixture's unintended saturation ambiguity. These synthetic native-response fixtures establish control flow and limits, not physical EOS accuracy.

Tests independently construct expected full/half density arithmetic, inspect exact native evaluation counts, check rejected records, constrain eight accepted states and the 43-evaluation worst case, propagate native/source/snapshot errors and check phase cleanup. Retaining all eleven existing coexistence controls complements the unchanged saturation diff.

[MEDIUM] Stagnation and new guard boundaries need explicit coverage
File: test_heos_tp_backtracking.py:test_equal_merit_stagnation_fails_after_six_trials
Issue: Fixed positive residual with decreasing liquid density makes the density-dependent gate decrease, so normalized merit normally worsens rather than remaining exactly equal. The test proves all-nonimproving termination but does not exercise exact-equality or identical-representable-density stagnation. The new per-trial phase rejection and explicit zero-gate branch also lack dedicated cases in the reviewed 15 TP controls.
Fix: Add bounded no-EOS cases where exp(step) rounds to 1 and residual remains nonzero, where the first trial reports the wrong phase, and where a synthetic positive density produces a zero gate with nonzero residual. Require explicit failure without snapshot, bounded trial count and phase cleanup. Keep these fixtures labelled numerical control only. This is a coverage warning, not a detected incorrect production branch.

Native exact-point/neighborhood qualification, existing broad water checks, source-identity binding and the unchanged coupled wet replay remain parent-owned next gates. A passing diagnostic or synthetic control suite alone does not certify them.

## Final attempt-record delta and extended control review

Final candidate SHA256 `c1ecb59c702382c78891f4fcf6b6ac5eb8c68cc57869b1e261ec8a3a4a796b12`; final controls SHA256 `00a318a45ac03cefed581c158dee3b60f0157bf5ee6753c153ac3712a11d7559`. Both parse. Compared candidate-before-attempt-log.py with the final candidate: the only incremental change creates an attempted-density record before native update, populates observed values after measurement, and records failed exception type/reason before a bare re-raise. Catching BaseException here does not swallow cancellation or native/source failures; it adds evidence and rethrows. Branch-invalid proposals still fail before native call and therefore are not falsely labelled measured attempts. Acceptance and native operation order are unchanged; the 43-density-evaluation proof and all prior source/state checks remain valid.

Read candidate-extended-tests.xml: 30 tests, zero failures/errors/skips, 0.064 s. This was an existing parent-run result, not reviewer execution. The added exact-stagnation test makes all seven evaluated densities exactly 1000 and checks one identical normalized merit. The wrong-phase trial joins fatal invalid-trial cases, with no smaller retry and failed-record identity assertions. The zero-gate tests separately exercise zero residual acceptance and nonzero 1e-320 residual rejection, checking actual zero gates and infinite nonzero-residual merits. These are explicit synthetic numerical boundaries and make no statement about physical states at such densities. Failed native attempts now retain rho/fraction/status even when no observation was completed.

The previous MEDIUM coverage finding is CLOSED by these additions. APPROVE final candidate code for the controlled source-identity integration and planned native qualification stage. No HIGH/CRITICAL finding remains. The parent-proposed 3x3 native neighborhood (295 K plus/minus 0.001 K; 53692.54782795906 Pa plus/minus 0.01 Pa), original baseline first, unchanged dynamic gate and full snapshot checks is a reasonable preregistered next experiment. No execution, grid result, installation or production identity binding is claimed in this review, and native validation remains required.
