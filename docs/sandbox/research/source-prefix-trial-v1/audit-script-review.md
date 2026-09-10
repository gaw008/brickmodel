# Independent native-audit script review

APPROVE for the stated frozen, successful N=3 native artifact. This review was read-only; it did not rerun the audit, production tests, solver or EOS.

Reviewed `physics/native-review/audit.py`, SHA-256 `40dea83507062bae8c939a31781bc2e633c05c915d9324485c57526f8745aba4`, together with actual `RESULT.json`, `AUDIT04.log`, and `REVIEW.md`. Verified the saved native input is 3,538,988 bytes at SHA-256 `7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505`. `RESULT.json` and `AUDIT04.log` match byte-for-byte and report 235 successful checks, 11 actual callbacks, eight reference callbacks, one accepted reference step and zero rejections.

The auditor imports only stdlib modules (`fractions`, `pathlib`, `hashlib`, `json`, `math`, `sys`, `time`). It contains no project/solver imports, dynamic imports, source callbacks or EOS calls. Its Euler and Heun arithmetic is independently written from saved rates, including represented incidence, exact-duration products and the two ledger summation levels. Prefix shared quadrature is independently recomputed using the actual midpoint sample. The direct cross-method discrepancy is recomputed separately from the reference fine/coarse estimator, without applying that estimator's one-third factor to the direct gate. Check failures raise; no catch, fallback or altered threshold hides an arithmetic failure.

Coverage is bounded. Polynomial minima are recomputed from the saved polynomial coefficients; their coefficient derivation from the original face rates is not independently repeated here. T/P bounds are checked against saved source records, including the positive volume-error contribution; this is not an independent EOS-uncertainty derivation. The decoder intentionally removes class/shape wrappers for arithmetic and several loops assume this frozen three-cell layout. The actual artifact has all eleven amount arrays at float64 shape [3,4], twelve inventory polynomials/minima, four face diagnostics and three terminal-bound rows; metadata was inspected directly and saved in `audit-static-metadata.json`. This script should not be described as a generic corruption-resistant decoder, arbitrary-grid audit or recovered-DomainExit replay validator. Those wider claims are not made by the reported native result.

The prior auditor mistakes and corrected attempts remain recorded in the physics review and historical logs. No input/result alteration or tolerance change is concealed by the final script. Source-record consistency and numerical accounting support the reported single positive trial; they do not grant event, material, plant or full-trajectory validation.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded independent arithmetic audit at the stated hash and input.
