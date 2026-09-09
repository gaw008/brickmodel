# Exact affine clock/writeback code review

APPROVE isolated primitive scope. Source SHA256 8448d3196084116b4b80c5348c48692665017490f969b2b94f505c7bb8601548. Read full module, tests and original DepletionRoundoffTotals budget validation. No repo edits, EOS or test rerun. Numerical root/integration review is separately retained in NUMERICAL_REVIEW.md.

ExactAffineSamples requires exact typed ordered times, finite numeric samples, complete immutable signed triples and unique explicit source labels. Its monotonic bracket requirement excludes first/second-root ambiguity in this admitted primitive. Evidence validates typed samples/policy, bounded integer refinement level, exact aligned dyadic-bin width, sign bracket, original time tolerance and original absolute/fraction correction budgets. inventory_residual revalidates evidence before comparing every signed term, so equal net totals cannot substitute for the actual component vector.

Writeback retains exact original state/policy/totals types, index bounds and distinct phase columns; reconstructs raw liquid from the saved once-rounded panel terms; binds clock policy and positive evaporation; and checks local residual, absolute correction and original gross-fraction limits. The zero-liquid return follows these checks, rather than bypassing them. The newly constructed totals enforce the original cumulative correction, storage, mass and element budgets before any new state is returned. Input immutable state/totals are not modified on rejection; only liquid/vapor columns change on success, preserving energy and mechanical arrays.

Positive evaporation uses the positive part of its own affine diagnostic rather than net liquid removal. Exact semantic times are never projected for evidence identity or panel duration; only individual integrated terms and explicit downward gross are converted to binary64. Exhausted root refinement fails explicitly. The result/clock types remain independent of old affine evidence and do not add codec, phase mode selection or coupled-trajectory admission.

Tests cover the actual retained failing float-clock data under unchanged local gates, origin translation, per-component mismatches, both evaporation sign crossings, zero-liquid binding checks, invalid sample types, malformed evidence bins and atomic cumulative-budget failure. No concrete validation bypass or original-budget weakening found. This does not certify arbitrary physical sampled rates as a globally affine law or establish a successful coupled native packet.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — exact affine primitive and writeback accounting only.
