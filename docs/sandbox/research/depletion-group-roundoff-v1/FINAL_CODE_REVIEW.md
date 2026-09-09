# Required review: depletion_group_roundoff

Read-only source/test inspection; no execution/EOS or edits. Verdict: **request changes** before integration.

## HIGH — affine root is not bound to the numerical panel

`depletion_group_roundoff.py:45–66` validates raw state against represented StepLedger increments. Lines102–110 bind only the initial liquid amount to each AffineInventory and check nonmember polynomial positivity. No check binds the panel's integrated liquid face/source terms to domain.rate_mol_s / acceleration. Yet lines117–118 conclude that every represented discrepancy is roundoff about an ideal exactzero polynomial endpoint. That implication is unsupported.

For example, a ledger with constant net loss .01 over one second can be paired with any accepted polynomial having initial .01 and root1, including a nonconstant descending polynomial with net coefficients −.005 and quadratic −.005. The final increment agrees but its path/minimum/competing roots may have different meaning. More seriously, arbitrary cancelling face/source components can produce the same net terminal loss while completely bypassing the proposed polynomial quadrature. This is numerical-evidence inconsistency even under the explicitly nonphysical scope; no true-RHS proof is being demanded.

Current test fixture reinforces the gap: model integral is exact Fraction(−.01), while the sole nonzero ledger source term is nextafter(−.01,0). That is not float(exact integral). The residual is under the existing local ULP allowance, but no actual per-component affine quadrature proves how it arose. Passing the generic deletion budget does not prove a claimed exact-common-root clock.

Required minimal fix: accept immutable complete per-component initial/midpoint rate evidence (shared midpoint delta) or equivalent exact component-integral evidence plus coefficients. Verify each represented face/source term equals the correctly rounded exact affine integral, and verify net initial/slope coefficients equal the domain polynomial. Include all wet members and nonmembers used by root/order/positivity analysis. A single net integral comparison is insufficient to establish affine path coefficients or correct shared-face quadrature. Reuse the actual single-clock discipline (`affine_depletion_clock.inventory_residual`: per-term float(exact integral) plus bound initial coefficients), but also bind these coefficients to AffineDomain.

If a different explicit integral-rounding certificate is used, it must prove the particular represented component errors from original terms, not merely introduce another arbitrary tolerance. Do not loosen correction gates. Gross evaporation remains a caller-supplied diagnostic as documented; future event caller must bind it to actual positive affine transfer quadrature separately.

## HIGH — exactzero branch bypasses the missing proof

Lines119–121 skip depletion_writeback for a zero represented remainder. That is valid only after the entire polynomial/component binding has passed. Currently an arbitrary panel that happens to subtract all liquid gets correction=None under an unrelated exact-root polynomial. Perform the universal binding before entering either positive-residual or zero-residual branch. Add a tampered exactzero case explicitly; it must fail without incrementing totals or changing caller state.

## Test corrections and acceptance

Keep existing atomicity/local fraction/cumulative/membership tests. Replace the arbitrary nextafter fixture by a real multi-component affine integration whose individually rounded terms produce the desired small positive residual while their exact sum reaches the common root. Add:
- changed domain coefficients preserving same root and initial inventory;
- altered cancelling face/source pair preserving terminal raw state;
- one term shifted by one ULP with unchanged claimed exact integral;
- exactzero with invalid polynomial/component binding;
- nonmember polynomial inconsistent with its panel;
- valid mixed exactzero/positive residual with all component proofs, unchanged original budgets.

The existing immutability and atomic local-copy behavior are appropriate. The layer's rejection of nonrepresentable shared clocks is explicit and conservative. Default single-event behavior is untouched. No additional rigorous physical root localization is required to fix this issue: it is solely the missing connection between the numerical polynomial being certified and the numerical ledger being corrected.

Additional nonblocking scope note: _panel_binding checks mechanical represented increments but not mechanical quadrature roundoff or full energy component decomposition. That is acceptable only if this helper explicitly remains phase-accounting-only and the caller's complete terminal/event auditor validates those shared ledger fields before commit. Do not describe this helper alone as a complete panel audit.

## Re-review of corrected module

Corrected source ec092b36ab69cea2cd6bae139a55c77522d85217ce246dc9b74ea4076f6e5a13 reviewed read-only. `AffineLiquidTerms` now carries exact signed left/right/source initial rates and accelerations for every cell. `_affine_panel` checks their sums against each domain polynomial, each represented integral against one rounding of its exact affine integral, and shared-face coefficients against neighboring opposite sign. The complete check runs before member writeback, including exactzero and nonmember paths. The fixture now constructs a genuine component-rounding residual. These changes address both HIGH findings above. Approval for this limited exact-common-root accounting module; no claim of complete terminal/mechanical quadrature audit or physical localization. Reported20 tests passed by author/root; this reviewer did not execute them.
