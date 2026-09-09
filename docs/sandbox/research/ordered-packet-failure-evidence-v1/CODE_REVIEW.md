# Frozen writeback failure evidence review

APPROVE scoped diagnostic candidate. Source SHA256 a2cdd548419c1f1129dbfa33c10051c230daed0313f39d3c574c1a44dc0dbb31; production-import test SHA256 03e626e78ba8699ffa5e5a796cd18f39fe0e8deb69c0b04e9a79d0ab0d3dd10e. Both actual bytes confirmed. Read complete diff and test file. No repo edits, EOS or test rerun. Retained green03 is4 passed .50s; portable-green is4 passed .27s.

The added try/except surrounds only the existing affine depletion_writeback call. On DepletionRoundoffError, diagnostics are attached only under ordered opt-in, then the same exception is re-raised. Existing raw/record/path.totals tuple assignment is unchanged and does not publish a partial successful result when writeback raises. No source callback, host rebuild, pressure inverse or altered event calculation is introduced.

_snapshot_failure_diagnostic recursively detaches dataclass fields, arrays, numpy scalars, mappings and sequences into immutable mapping proxies/tuples, converting exact Fraction values into numerator/denominator mappings. Snapshot includes the actual before/raw/midpoint states, observations, integrated fields, clock, exact gross and rounded evaporation, prior speculative frames and totals before failure. It does not append those frames to accepted packet/state histories. Tests check nested immutability and exact whole-state reconstruction from the captured ledger.

Expected capture failures are caught separately and replaced by an explicit available=False record containing original reason and capture error. The original DepletionRoundoffError remains authoritative. The failure-capture sentinel verifies this. The two enclosing exception handlers carry the diagnostic into refinement details without extra evaluation. The previously reported out-of-scope exc reference is absent from coarse_reference/success branches; successful packet regression completes with no writeback_failure keys.

Default ordered_event_policy=None does not invoke capture and retains original refusal/empty-refinement shape. Existing successful numerical path is unchanged except the inactive try boundary. Evidence labels remain uncommitted_numerical_terminal_diagnostic, not accepted event or native model proof. No concrete blocking issue found.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — failure-evidence capture only; no numerical gate or admission change.
