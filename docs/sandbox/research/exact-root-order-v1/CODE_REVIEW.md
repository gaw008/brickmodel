# Exact root order code review — pending typed verifier fix

[HIGH] Public record verification accepts invalid field types through numeric equality.
File: exact_root_order.py, verify_exact_root_order.

Only the outer ExactRootOrder type is checked before ordinary dataclass equality. Python treats True == 1 and False == 0. A pure-data reproduction using the retained test inputs returned a valid selected cell 1; replace(record, selected_cell=True, wet_cells=(False, True)) passed verify_exact_root_order without exception. This violates explicit index/type admission and the stated promise not to trust public records. Nested candidates and exclusions require the same protection. Use exact-type-sensitive recursive comparison or complete strict validation of every record field before comparing recomputed contents. Preserve the failing reproduction as a regression. No EOS was executed.

Other inspected scope: all initial positive-liquid cells are required in canonical order; input digest covers whole state/rates/clocks/evaporation/policy. Positive exclusions use full interval minimum. Potential roots require the original strict decreasing sample contract, which makes a shared in-domain gcd root the unique first crossing; earliest coincidence is checked only once proven ahead of noncoincident candidates. Later ties do not block a strictly earlier candidate. Every candidate must meet original evidence gates; bounds refine at most 256 times. Failure diagnostics are immutable tuples of frozen sample/evidence values and are explicitly not accepted event evidence. Midpoint/source provenance and full-state terminal commit remain caller responsibilities.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — close the typed verifier gap before application.

## Final type repair review

Final source SHA256 1cc3b7868b5a4f6bf7f654063602cb058d984b10e59848afe0a1feb8250d69a5; test b92502d5c9b5e632f6711fb6243097ed2aac112f8096eafc25be45d605ec6244. Prior HIGH closed. Comparator first requires exact identical types, then recursively compares all recomputed dataclass fields and tuple members. Only explicit scalar/Fraction leaves are accepted. It does not reuse the lossy serialization tree, and unexpected record structures fail closed. Full root recomputation and input binding remain unchanged.

Read actual type-green.log: 17 passed in 0.22 s. Regressions cover top-level and nested bool indices, tuple/list substitution, exact-time Fraction replaced by bool, evidence iteration int replaced by float, float gate replaced by Fraction, and exclusion Fraction replaced by equal float. Earlier failing implementation and type-red.log are retained. No repeated test/EOS execution in this final review.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE for caller-bound numerical affine root ordering and strict record verification. Not a true-RHS or event-commit certificate.
