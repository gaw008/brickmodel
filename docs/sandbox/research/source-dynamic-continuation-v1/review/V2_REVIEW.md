Approved one new, separately registered V2 attempt. The strict recursive JSON comparison finds exactly two changed scalar values, with all types, array ordering, fields and other values preserved: pressure_tolerance_pa 1e-5 -> 1e-7 and inverse energy_tolerance_j 1e-5 -> 1e-6. The V1 case and failed evidence remain unchanged.

The V2 runner is an exact V1 clone except the case filename and the two corresponding expected-value assertions. Its actual branch construction, endpoint/callback checks, shared-parent accounting, whole-path auditing, pressure/event gates, checkpoint roundtrip, failure journals and qualification limits are unchanged. The launcher uses a new native02/supervised-native02 directory, the installed 146-module package, no PYTHONPATH, and the existing process supervisor with 570 s / 1 s cleanup; the scientific aggregate ceiling remains 97 RHS / 16 wet / 510 s and original per-segment 4 steps / 4 rejections / 180 s.

V2_CONFIG_CHECK.json hashes all match the current files. The installed checker's first raw-list/frozen-tuple comparison failure is explicitly preserved. The corrected checker compares raw JSON and independently loaded frozen structures; it does not invoke a model or decode source studies. All three V2 Python files parse. Original final source/test/runner freeze and codec identity remain unchanged. This reviewer executed only standard-library reads, strict data/delta/hash checks and AST parsing, with zero EOS, model or test execution.

The preregistration accurately carries forward the actual cell-2 pressure failure, the need to reduce both numerical residuals, the unchanged physical/error/event contracts, and the possibility that tighter inner solves exhaust the original budget. It neither treats the saved allocation as a future passing bound nor authorizes a repeated unchanged retry. Shared wet/dry numerical acceptance, when present, remains conditional and is not real-material or full-firing-cycle validation.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE one new V2 attempt with the frozen files in V2_REVIEW.json, retaining its actual result under the original limits.
