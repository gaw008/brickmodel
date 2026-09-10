# Observer and four hook review

APPROVE, limited to the six exact file hashes in `OBSERVER_REVIEW_FINAL.json`. Service, journal, config and builder remain separately reviewed.

Read the final ContextVar delivery/restoration implementation, exact-source started/returned/failed lifecycle, HEOS started/kernel-returned/wrapper-returned lifecycle, shared-wet request lifecycle, candidate/transition pre-check notifications, and all new observer tests. No kernel or HEOS manifest change. The numerical formulas are unchanged; actual sink exceptions remain identifiable before the adapter's legacy ValueError translation. The HEOS wrapper embeds its own source hash, so these new hook bytes change that implementation fingerprint: this review does not claim old and new provider identities or complete records are byte-identical. Failure notification does not replace the primary exception.

One precise issue was found statically: cancellation before a second wet request paired that next request with the previous iteration's returned state. Author reset `state=None` at each loop entry. The independent control probe now observes the second request with `state=None` while the original exception retains only the first attempt and its return. This is an event-order test with a controlled sentinel, not a physics or material validation. Zero water EOS calls. Evidence: `observer-service-probe01/RESULT.json`.

The author reports 61 combined tests passed in 12.80 s (`observer/FINAL01.log`); those tests preceded only the per-iteration state reset and were not repeated here. No additional finding remains in this bounded observer scope. Sink persistence, actual counters and summary/canonical correspondence are the service's responsibility; its open findings are not covered by this approval.

## Review Summary

| Severity | Count | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — final observer/hook bytes only.
