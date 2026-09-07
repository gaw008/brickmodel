# Independent review: depletion event numerical write-back

Verdict: APPROVE as a bounded numerical write-back and exact audit-prefix component. The previous wet/dry event design's unimplemented event localization, node handling, common-time error comparison, and dry constitutive-mode requirements remain open. This review does not close those implementation gates.

Read the preregistered plan, complete implementation and tests, ConservedState usage, and component documentation. The selected representation is an exact paired −δ/+δ numerical phase ledger plus separately recorded actual binary64 vapor-storage residual. It avoids the previously identified impossibility of requiring equal representable increments for arbitrary liquid/vapor magnitudes. The .01/.1 example can therefore succeed under explicit budgets even when the vapor float does not increase.

Fraction reconstruction rejects negative panel inventory and requires round-once agreement with the supplied stored liquid amount. Existing panel rounding is recorded separately and belongs to the future caller's ordinary panel audit. The event remainder δ is bounded by local liquid-panel ULP scale, absolute mol policy, and at most 1e-8 of separately supplied positive evaporation. A large vapor inventory cannot loosen the local liquid constraint. The positive evaporation argument is not certified as a physical rate integral by this helper.

The write-back uses exact represented vapor+δ followed by one nearest binary64 conversion. Its residual is checked against the actual adjacent spacing in the direction of the exact value, including power-of-two asymmetry and subnormals. Per-event water, H/O and mass limits are checked before returning any new state. Exact Fraction cumulative absolute residual prevents cancellation from defeating prefix limits; total numerical phase correction has its own prefix cap. U, other columns and input state remain unchanged. Versioned JSON records preserve rational prefix values and policy; they are consistency-checked serialized state, not a cryptographically authenticated run history. The future caller must retain the genuine prefix instead of creating a fresh one.

Independent execution: the first frozen 15 write-back tests plus 9 joined-host tests passed together (24 passed in 2.23 s), XML `/private/tmp/joined-host-roundoff-review.xml`. Read the actual regression assertions for swallowed increments, cumulative rejection, exact representable transfers, no negative clipping, reconstruction mismatch, large-vapor scale isolation, H/mass budgets, sign cancellation, power-of-two spacing, minimum subnormal and restored prefix. Additionally ran 120 independent exact-rational nearest-neighbor checks across exponents −1074, −1022, −100, −10, 0, 100 and 1023, including adjacent values and quarter/half/three-quarter intervals: all residuals satisfied the returned local half-spacing bound. No additional full or heavy suite was run.

No confirmed unresolved implementation defect in this bounded contract. Necessary future binding remains explicit: actual H2O phase-column identities and native molar mass; physically generated positive evaporation and full panel terms; authentic cumulative audit state; separate ordinary arithmetic budgets; event-time/direction/node and common-time convergence; actual total-U re-inversion after correction; and an explicit supported dry/no-nucleation policy. These cannot be inferred from this numerical function's successful return. Keeping U unchanged is consistent with total-energy storage, but a physical host must still validate the resulting state rather than add a second latent-heat source.

Final incremental correction: the root reviewer subsequently found that an accepted nonzero Real/Fraction panel term (1/10**400) could silently become zero during float conversion. Root recorded the new test failing, then added a nonzero-underflow rejection to `_number`. Independently inspected that two-line guard and executed only the new regression: 1 passed, 15 deselected in 0.05 s, XML `/private/tmp/depletion-underflow-review.xml`. Thus the final file contains 16 tests; the earlier 15-test execution is retained as earlier-source evidence rather than relabeled a final 16-test rerun. This resolved issue changes no accepted representable arithmetic path.

## Final SHA256 bindings

- `src/sludge_sandbox/depletion_roundoff.py`: `52031b8a034ea395045514e882cc7e05e342c7918e063cc709a47292ee621b85`
- `tests/sandbox/test_depletion_roundoff.py`: `3ac1bfa367b4689c4a0f6ce9f4628a81d8f313371851cb7b630b5e1b6f3c63a6`
- `docs/sandbox/DEPLETION_ROUNDOFF.md`: `29a1b76b3d0ad30ed2c20ae3ecdf383a3712e72a302f11896d6f8de3caa8b214`
- `docs/sandbox/research/DEPLETION_WRITBACK_PLAN.md`: `0816a0a74af41cfeffeca10384cd148b28632c70fdb671a700dfef9a32f8e8b3`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE within the explicitly stated component scope; the full Goal remains broader.
