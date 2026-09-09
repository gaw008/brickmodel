# Independent prefix audit script review

Reviewed audit_prefix.py SHA256 b187bc7d6b1acc35a74566bf3f466a03aa44b4db165e869aa2c2e02bb1f8ceb8, read-only. No EOS, model imports, script edits or repeated audit execution by this reviewer.

APPROVE for the stated saved-prefix accounting scope. Strict finite numerical arrays and reduced rational clocks are checked. Every terminal frame maps uniquely to one accepted ledger and its preceding/following full states. Paired liquid/vapor correction and actual vapor storage residual are reconstructed; other state fields remain equal to raw, cumulative correction totals are charged once, and original local/cumulative amount/element/mass/correction limits are checked. Every accepted prefix is reconstructed against original N/E/stretch using shared faces, sources and work. Component residual absolute accumulation and represented/exact stretch budget accounting preserve original thresholds. Final cumulative absolute correction quantities are monotone and therefore final checks also bound earlier values.

Limitations correctly declared: this does not independently rebuild root/gross polynomials, endpoint EOS values or actual stage quadrature. Saved gross and stretch-quadrature roundoff values are consumed as evidence; the script verifies their accounting consequences. It does not perform a separate nonlinear external-pressure work or constraint-cancellation test. Generic hostile-record/full-codec validation is not claimed. For this all-initially-wet four-cell case, event-cell reporting is valid. Root comparison/source-domain audit is separate.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE retained prefix arithmetic audit in its stated scope.
