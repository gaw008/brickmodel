# SolidFluidStorage target uncertainty review

Verdict: APPROVE for the additional upstream target-energy error budget. This is numerical propagation, not a mechanical material-error certificate.

Read the complete inverse, error-envelope helpers, surrounding storage implementation and new tests, and compared HEAD. The new keyword-only argument defaults to zero; the result adds one trailing default field, preserving prior positional construction. Real validation rejects bool, nonfinite, string and negative values; the extra exact Fraction sign test rejects a tiny negative that float validation alone would round to negative zero. Positive unrepresentable tiny bounds are rounded outward to the minimum subnormal. Overflow remains an explicit error.

The upward-rounded additional bound is added to the pre-existing target ULP. That combined uncertainty participates in strict initial endpoint signs, every evaluated residual budget, temperature radius, both acceptance gates, insufficient-resolution rejection and unresolved-direction rejection. Updating the bracket only after residual sign exceeds the full budget preserves containment of the target interval; accepted midpoint ± radius is outward rounded and intersected with that retained bracket. Conditional heat-capacity lower-bound and EOS-envelope assumptions are unchanged. No branch accepts the nominal target while discarding the extra bound.

For default-path independence, saved actual HEAD source to `/private/tmp/solid-fluid-before-target-error.py` (SHA256 `a592373dcc365ee121926eee2330ccad93b1d300822ab0eebcd7be2b1f45508c`), compiled its original inverse AST against unchanged helpers, and compared all returned dataclass fields with the new default call at 296, 300 and 307 K for fixed solid/pure-gas inventory. All three results were equal. This is not merely omitted-versus-explicit-zero comparison of the new implementation. Algebraically, `_sum_upper((ulp(target),0))` retains the exact old ULP value.

The new interval test uses independent constant capacity C=10+.01*(30−R), checks that both target-energy extremes map inside the returned temperature enclosure, and checks error-induced precision/sign failures. Independent bounded run of new and existing storage tests: **34 passed in 0.66 s**, XML `/private/tmp/solid-target-error-review.xml`. No full installation suite was repeated and no production code or tests were edited by the reviewer.

Final bindings:

- `src/sludge_sandbox/solid_fluid_storage.py`: `3eb71df199fae41aceb3d01eaa5b7b8069372ba63cd38d89b500a7218e02eb6b`.
- `tests/sandbox/test_solid_target_uncertainty.py`: `6492071238ab82a4c9a52db29b9472ab15498a37abd2682819170ee185bee396`.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — upstream mechanical-energy subtraction uncertainty can now be retained in the existing conditional thermal inverse.
