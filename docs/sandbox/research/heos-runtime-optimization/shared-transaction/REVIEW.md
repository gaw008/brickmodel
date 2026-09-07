# Stage8 independent source and result review

Approve this isolated optimization and its completed four-step wet-prefix evidence. Reviewer changed only reviewer-owned tests/reports, ran no EOS and made no candidate/production edits. Application must retain explicit backend identity and bind the new kernel/approved manifest; installed locked-environment evidence remains separate.

## Source equivalence and guards

Compared stage7 to stage8 by AST: the entire original saturation try/except body is exactly identical to the new private _saturation_pair_locked body, including all branch, Newton, EOS, energy/Gibbs and exception gates. Public saturation_pair still validates temperature then holds a transaction around this body. state_tp still validates T/P/phase and holds its full outer transaction, but invokes the private body instead of creating another public transaction. No cache, arithmetic or physical tolerance change. _transaction itself is AST-identical to stage7: lock, warning capture and before/after fluid/config checks remain. This removes redundant nested checks during one public operation; it does not promise safety from unsynchronized global native changes mid-operation.

Kernel SHA `9b122e529efe60573e27105098081d7376cba41c505ae64375050cd259688bd8` matches expected adapter SHA. Actual approved manifest SHA `38296d993f21193a011aaa0ef31faaa9ccb83385cf97c79f39fed133d2659219` is the new wrapper admission value. Scientific identity changes intentionally with these sources.

Actual reviewer-owned review_faults.py tests the real transaction and public-method ASTs using stub native objects, not EOS. Nine transaction checks pass (unchanged, pre/post content, pre/post equivalent-JSON whitespace, pre/post config, warning, nested reads). Eight additional public-route checks pass for both saturation_pair and state_tp: stable operations perform exactly two raw reads; private-body fluid/config changes or warnings prevent successful return; private body sees the held lock. Native numerical work is stubbed only for these routing checks. Results are retained in review-fault-results.json and tied to the kernel SHA.

## Actual numerical evidence

Grid-attempt01 completed exit0 in1.305438084 s; derivative-attempt01 in1.156051208 s; wet-attempt01 in16.757266209 s. All recorded inputs independently match before/after/current hashes. Thirty grid states and seven derivative cases pass original gates. Recomputed all21 finite differences from saved snapshots and verified the original expected-value relative scale, not only symmetric math.isclose.

Wet child status completed_partial_smoke; integrator completed in14.502015542 s,29 evaluations,four accepted steps,zero rejections. Original25 s internal/30 s external limits and original inverse/scientific tolerances remain unchanged. Independently reconstructed all four accepted-prefix component sums and N/E residuals using exact Fraction arithmetic against saved ledgers. Inventories remain exactly fixed and every energy residual is within1e-6 J. These are ledger checks, not independent component truth at every prefix.

Independent oracle remains original byte-identical Python WaterProperties entropy solver. Recomputed native-water pore truth from saved Python u operands and original M/gas/solid coefficients:0.009269478952543691 J. All endpoint component errors recompute and pass1e-6 J; pore error7.359925505625448e-7 J. T error8.606377832620637e-9 K passes2e-5 K and P error1.1998112313449383e-5 Pa passes.2 Pa. Native entropy reconstruction gives-3.383434174784915e-11 J/K, below1e-8 J/K; its approximately8.31e-17 J/K difference from saved oracle arises from reconstructing initial gas volume as NRT/P. This is independent saved-operand arithmetic, not a new EOS run.

This qualifies the registered0..1/64 s four-step fixed-inventory wet prefix of the original one-second10% prescribed motion. It does not qualify full wet motion, active phase change/depletion, arbitrary coupled hosts or general material physics. Stages6/7 remain resource-limited failures and are not relabeled. More completed evaluations and shorter observed runtime motivate this change, but these isolated runs are not a controlled broad performance benchmark.

Final wet result SHA: `6478eaa2e70e7d291d16ea810fec9182d3ce9a4745ded6efff01cc7c02178b02`. Current isolated runtime uses NumPy2.5.3; project-locked2.5.2 and installed-module path verification are separate forthcoming evidence, not implied by this report.

No remaining blocking source finding for applying the reviewed kernel/wrapper and corresponding fixed manifest/source digest was identified. Preserve originals and verify actual installed package plus target dependency environment before labeling installed validation complete.

Also independently compared stage7/8 saved common prefixes directly: first four time/state entries have exactly equal inventories and energies, the first three accepted ledgers are entirely equal, and implementation tags differ as intended. This is useful observed numerical-preservation evidence for the extracted-body optimization; stage7 still lacks the fourth accepted step and endpoint comparison.
