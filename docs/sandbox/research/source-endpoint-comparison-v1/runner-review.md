# Saved source-endpoint runner review

APPROVE for `/private/tmp/brick-source-endpoint-comparison-v1/root/run_saved.py`, SHA-256 `e552dffed39433816c72495685da2c427eb9ed34b9738f2b25cb192c2b84745b`. Read-only review; no native run, saved runner rerun or repeated production tests.

Read the complete runner, actual `saved-source.json` and log, existing pinned decoder, and independent physics extraction script/result/review. Verified the archived native input, native audit and decoder bytes match the hashes retained in the output. The independent extraction is SHA-256 `711d7716bf247b693c4c92b6d0a65150e5abffc94a2b3f1d112d8f3c57d0f7ab`; this matches the runner's recorded input. `saved-source.json` hash is `1709b3d6be75d8f17ab0b99d0fc8c59f0825fc5362d52c9d63236f6cf4ca30d8`. Every displayed log field matches that output. Read-only metadata evidence is in `runner-static.json`.

The actual 30 successful checks in 0.19880862499121577 s cover four pinned-file/audit associations; five saved trial/reference success, role, time and final-state associations; one original sample-binding comparison; one independent input/count association; eighteen per-cell checks (four exact N/U/T/reported-T-pressure comparisons and two positive available-volume pressure-error contributions for each of three cells); and one exact zero comparison-time offset. `measurement.check()` additionally rebuilds the passive measurement without being included in the explicit 30 counter. This is endpoint accounting, not another full trajectory audit.

The runner imports only the fixed hash-verified decoder path. The decoder admits 35 explicit passive record classes, validates complete fields, invokes their normal constructors, and checks canonical round-trip contents. It does not import a class name supplied by the input, restore a live adapter, bypass constructors or manufacture a successful `SourcePrefixTrial`. Seven source/storage/TP/equilibrium entry points are patched to raise during decode and measurement. The reviewed constructor/measurement path performs passive arithmetic and metadata validation; the zero-new-source-evaluations claim is supported by that path and those guards, not an EOS performance test.

The physics comparison source is independent of this production measurement: its stdlib-only script reads the same hash-verified native artifact and directly derives exact differences and error sums from the two endpoint captures. Only its N/U/T/reported-T-pressure rows are used for these 30 checks. Its additional conditional thermal pressure-propagation calculations are not imported as a pressure certificate or compared as implemented production behavior. This distinction agrees with the separate PRESSURE_PATH review.

No event policy is invented for the saved native record. The output retains `event_policy=null`, gates not evaluated, full inverse-pressure unresolved, event-time not evaluated, and both event/material admission false. The returned maxima therefore do not constitute event accuracy or source-certified pressure acceptance. Exceptions produce a failed saved record and propagate; no failure is converted to successful accounting.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — frozen saved-endpoint accounting, with the stated 30-check scope.
