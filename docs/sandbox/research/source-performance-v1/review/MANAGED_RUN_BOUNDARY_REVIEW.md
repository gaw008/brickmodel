# Actual managed RHS execution-boundary review

Approved within the saved single-query execution scope. 36 independent standard-library checks passed; no model construction, EOS call, numerical integration or full returned scientific-graph comparison was repeated.

The 15 durable events are exactly four `heos_started → heos_kernel_returned → heos_returned` chains, one query-admission record and one RHS start/return. They agree with all reported counts: four real provider constructor chains, one RHS, zero initial-U calculations, zero wet-pair collector requests and zero accepted steps. The actual isolated `-I -m` command used the preregistered 120 s supervisor with 1 s cleanup. It exited 0, every declared input remained unchanged and the process was reaped without cleanup errors. All required result/profile artifacts exist and no contradictory failure terminal exists.

The closed admission contains exactly one verified RHS, no primary or exit errors, four entry checks and four exit checks. Each records the expected complete configuration hash and water-fluid hash. The four live registered kernel objects are established by the reviewed constructor/graph logic; the repeated saved kernel hashes identify equal implementations, not four distinct persistent object IDs.

Actual times: worker total 3.233242 s, reconstruction/admission 1.461461 s, profiled RHS 1.719230 s, inner scope 1.661648 s and supervisor 4.342557 s. These scopes differ and include instrumentation. The prior RHS profile was 6.382242 s. Both pstats files show 2,045 kernel state calls and 4,090 context-generator resumptions. New live `native_operations` also equals 2,045. No physical-point reduction is claimed.

Getter accounting uses caller edges because Cython getters are not standalone pstats rows. Old `_transaction → json.loads` and `_transaction → sha256` each execute 4,090 times, matching the preserved full per-call configuration and fluid verification code. New `_verify` runs twice, with eight configuration JSON decodes and sixteen SHA calls: eight fluid hashes plus eight configuration hashes recorded in the audit. All eight boundary records confirm those successful operations. Thus this profiled RHS used eight configuration and eight fluid verification requests instead of 4,090 each; reconstruction is outside this region. The `_transaction` cumulative time changed from 4.612766 s to 0.039481 s; new scope verification is separately represented and nested times must not be added as independent totals.

Complete old/new physical and diagnostic graph equality is the other reviewer's responsibility and is not asserted by this boundary audit. This successful query does not complete the previously timed-out ordinary continuation, grant source-session resume, or validate a real material/full firing cycle. Exact evidence hashes and counters are in MANAGED_RUN_BOUNDARY_REVIEW.json; the reproducible standard-library checker is managed-run-boundary-audit.py.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — actual diagnostic execution boundaries only.
