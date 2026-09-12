# Independent saved-result review — short split refinement

**PASS / APPROVE.** One passive JSON/Fraction/XML audit completed with **132 independent grouped checks, zero failures, 0.113 s**. The original acceptance contains **826 distinct passing gates**; their driver logic was read against the preregistration. No application import, EOS, trajectory replay, installation or test execution occurred. The separate long-probe proposal is outside this review.

All three runs use the identical saved original states, construction points, source nodes and column provenance. The case file is byte-identical to the previous fast-inverse case. **2/4/8 accepted steps, 5/9/17 RHS calls**, and the common final time of represented **0.05 s** match the plan. One local stage and one transport stage advance one h, not 2h. Measured integrator times were **9.5040 / 17.5259 / 33.6621 s**; driver **62.5378 s**, supervisor **67.8210 s**, within the original **60/80/100 + 5 s** limits.

Exact rational recomputation confirms every cell's local and slow Nc, all three gas inventories, U update, positivity and cumulative water/U prefix. Actual frozen coefficients, shared BE J/E/H, absent internal reservoir, zero slow gas flux and heat-only bath agree with the saved contexts. Both state-writeback charges, applied face decomposition/carried-water projection charges and bath projection were recomputed independently. Total energy fees were **2.18032e-12 / 3.97943e-12 / 7.54846e-12 J**; inventory fees **8.83844e-18 / 1.46173e-17 / 2.56674e-17 mol**, below the unchanged **1e-8 J / 1e-12 mol** budgets.

The **56 saved after-local/final inverse records** satisfy reconstructed complete U, actual target/residual, retained dry excess reference, exact inventory W, pressure bounds and original energy/minimum-Cv/temperature gates. Maximum U residual plus stated error was **6.72887e-6 J** and maximum T bound **4.19163e-7 K**. This checks saved arithmetic and certificates; it independently evaluates no EOS.

Recomputed successive-difference ratios are **1.9303427569430607** for outer Nv and **1.9303423109954385** for cumulative E, within the preregistered **[1.5, 2.5]** interval with nonzero differences. Saved field differences and summed endpoint bounds match independent calculations. The temperature differences are smaller than those summed bounds, so these two observable passes establish neither temperature/all-field nor spatial convergence. Freezing/truncation errors remain unknown; material qualification remains false.

The process exited **0** with its leader reaped. All **2,787** normalized before/after input hashes agree, including the exact plan/driver/case. **184 package files / 177 Python modules** match source, installed package and freeze before tests, after tests and after native; these package identities are also present in the supervisor snapshot. The original installed XML records **46 passed, 0 failures/errors/skips, 39.446 s**. Containment remains limited to the original process group, as recorded by the supervisor.

Evidence: `audit_saved01.py`, `AUDIT01.log`, `SAVED_REVIEW01.json`, and `REVIEW_SHA256.json`. No failed audit was produced or overwritten.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — this saved short conditional refinement only; full-field, spatial, material and complete-Goal qualification remain unestablished.
