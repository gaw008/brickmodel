# Independent review: final numerical pressure bracket diagnostics

Reviewed 2026-09-07 UTC. Scope: additional RigidWaterGasState diagnostics, propagation from existing solver paths, tests and documentation. The prior mechanical-closure review is retained; this report covers the new increment only. No implementation edits by reviewer.

Source SHA-256: `37267b199214308b57223f334a9a7ed4d06334dffe341ea75ecddce17de6c84a`.
Tests SHA-256: `1faf5d95de864d6b683f7000b70fdd0780922bedd3168614c7eb233fb13b3d40`.

## Behavior and compatibility

Old `pressure_bracket_pa` preserves the caller's original input domain. New fields record the actual final numerical lo/hi interval and the cached endpoint F values. Their position after old fields and optional defaults preserves legacy constructor argument positions; legacy instances explicitly show unavailable diagnostics rather than synthesized historical bounds.

Normal bisection returns the actual cached endpoints before their next update, with pressure at the tested midpoint and unchanged stopping/precision policies. Pure-gas analytic and originally exact numerical endpoint paths produce explicitly labeled single-point representations. The latter only means a floating-function endpoint has zero computed residual and passed existing checks, not that the exact EOS or physical pressure has zero uncertainty. Every new result declares `numerical_forward_function_only_excludes_eos_error`. Failures do not return a successful-looking bracket.

Read all six added test cases, including both liquid endpoints, pure-gas no-liquid-EOS check, legacy construction, failure and independent root/endpoint comparisons. Documentation separately preserves pre-registration, implementation failure history and original model restrictions.

## Independent numerical verification

Ran this suite together with new/local water and original-water regressions: **122 passed in 2.68 s**, including **23 rigid closure tests**.

Reused three independently obtained brentq references from the previous mechanical review and recomputed endpoint F from separate calls to actual liquid density plus ideal gas volume. For cases (T,nl,ng,V)=(300,1,.01,1e-4), (450,1,.1,1e-4), (300,10,.1,2e-4), final widths were approximately 0.0007275700, 0.0007208129, 0.0007275697 Pa, each below explicit 0.001 Pa policy. Every independent reference lay inside the reported interval. Recomputed endpoint residuals exactly matched stored floating values and had nonnegative-low/nonpositive-high signs:

- +7.45720e-14 / -1.21203e-13 m³.
- +6.43382e-15 / -5.85146e-15 m³.
- +7.04125e-16 / -5.44286e-16 m³.

This checks honest capture of the solver's actual numerical bracket rather than a reconstructed interval around its answer. Independent reference inclusion for these cases does not certify inclusion under all upstream EOS errors.

## Findings

No actionable issue above review confidence threshold. Qualification and documentation correctly distinguish a numerical forward-function bracket from a rigorous total-error interval. Using these diagnostics later for temperature-error guarantees still requires handling EOS/state-solver error and any interval derivative bounds explicitly.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — final numerical bracket reporting at current hashes; no stronger physical/EOS error or Goal-completion claim.
