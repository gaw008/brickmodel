# Prepared actual-source runner review

Reviewer: independent code-review agent; no native HEOS evaluation performed.

Reviewed `/private/tmp/brick-source-prefix-trial-v1/root/run_native.py`, initial SHA-256 `c23bc0fb5e41986d61cf82fd64961b160090cb0ea89af8f7c6f61e79d6395edd`, then final SHA-256 `cd194586d9ffd8455b26ac54e94656c6d0b1a1a719de4d3312ee027b8b690c78`.

The runner is import-passive, verifies the three constructor-script hashes before loading the saved construction route, uses the declared exact duration 1/16384 s, and retains the original numerical amount/energy/error policy. The 180 s inner, 210 s outer, and 32 callback limits are execution-resource choices. The signal timer bounds a callback that does not return to the trial's soft guard. Trial review and installed-source identity remain separate preconditions for the actual run.

Before every actual callback the runner atomically persists the callback ordinal, exact time, packed input, and pending marker. It retains complete successful raw evaluations or an exception type/message for failed attempts. Returned trial fields are persisted before `trial.check()`. Failed trials remain failed, preserve their trial status/reason, and produce exit code 1. The top-level `failed` status intentionally describes the probe outcome; the nested trial retains the solver classification. A live adapter is represented by its source provenance, with `material_qualified=false`.

Independent executable validation used the actual source host with explicitly manufactured water/transport, substituting only the constructor so no HEOS call could occur. Four tests passed in 2.94 s (`runner-persistence.log`, `runner-persistence.xml`): normal 11-callback success and atomic pre-call persistence; initial DomainExit; terminal TimeoutError; constructor failure. Every observed callback remained in the saved record, exception text/type survived, pending markers were removed after terminal observations, and original resource policy was retained on construction failure. These results validate the runner mechanics only, not a native-model outcome.

The final narrow change records `outer_timeout_requested=true` only inside the runner's own signal handler, and uses that marker to report the probe as `resource_limit` while retaining the nested trial outcome and raw callback exception. Five final tests passed in 3.02 s (`runner-final.log`, `runner-final.xml`), including the unchanged four cases and a fifth case directly invoking the actually registered SIGALRM handler during a manufactured callback. The fifth case verifies explicit top-level resource failure, retained original TimeoutError and nested failure, restored original signal handler, and disabled timer. Arbitrary callback TimeoutError remains an unexpected callback failure without the outer marker.

No confirmed unresolved issue in these final runner bytes. Actual execution remains subject to root source/install verification and physics review.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — prepared runner mechanics at the stated hash; no native-result claim.
