# N1 native runner review

Verdict: APPROVE the final prepared runner for one execution after the required final source/installed verification. This review did not execute native EOS or the actual HEOS construction.

Final runner: `/private/tmp/brick-source-approach-v1/root/run_native.py`, SHA-256 `ed1a38aad00a7b21758bbc39b01879a14c958abcb84bd369106157b90cb4a87e`. Preregistration SHA-256 `b68806f0e81e447357eba553da5a5593b10c6d5951930c38198d7a5c7a08778b`. Production candidate remains source `5364e5dd471523d6f47e512924c884aff1329938632779cbe051795c3139c007`, tests `de129eb80d833f6a061f4b349efb1b75006ed83df950e0d4ef1ab9ffec3050d1`.

Both pinned helper hashes match actual files. Importing the runner and its two helpers is passive; the serializer supports actual numeric/source records without evaluating physics. Runtime adapter fields and inverse-bound storage providers are deliberately omitted while preserving their identities and all numeric observations. Explicit assessment-exception handling retains the actual completed trial and any completed endpoint/pressure evidence.

The final N1 constructor uses `liquid_transport=None`, no interior faces and no unused mobility model. It uses the original real source storage helper, explicit HEOS chemical backend/manifest, one initial-U forward evaluation and one actual phase observation. H is computed only from finite positive actual phase using the preregistered represented Fraction ratio. The IntegrationPolicy fields, complete keyword-only DepletionRoundoffPolicy, and DepletionPolicy match the declared controls. The latter equals the existing `policies()[1]` except maximum_refinements=32, including all defaults and nested roundoff fields.

The 210 s outer timer covers construction through persistence; each trial retains 180 s and a 16-callback limit, with 33 as the total observed source-call cap. The seed must actually retain its first/midpoint negative-prefix failure before the single new trial is allowed. A failed/nonapplicable seed or new trial is not silently retried. Actual attempts are saved before evaluation and their returned/failed observations afterward. Outer-timeout classification is driven only by the runner's own signal flag; its final signal handler is restored. The preregistration correctly avoids promising a hard native interrupt.

One static defect was resolved before execution: the earlier runner assigned constructor totals only after each pair of providers completed, losing partial-success counts if the second provider failed. The final wrapper persists started before every HEOSCandidate constructor and completed/reference-anchor counts after each successful return. A successful four-provider construction is explicitly checked; these counts are not presented as all internal EOS updates.

## Bounded verification

`test_runner_static.py`, `runner02.xml/log`: **3 passed in 0.20 s**, with no actual native constructor or EOS execution.

1. Native constructors are forbidden while importing the runner/helpers. Both helper hashes match. AST-selected original policy constructor calls instantiate passively and exactly match the declared/default policies; fixed callback/time constants also match.
2. The actual runner is executed with a deliberately substituted loader/constructor that succeeds once and fails on its second call. It persists failed RuntimeError, started=2, completed=1, anchor-counter=1, zero source callbacks and zero initial-U attempts. These are mock constructor-path checks, not real reference anchors.
3. The same isolated failure harness invokes the registered SIGALRM handler on the second mock constructor. The persisted result is resource_limit with TimeoutError and the same accurate partial counts, without a source callback.

`runner01.xml/log`, its test snapshot and JSON are preserved: the first review run encountered the already-fixed runner but still asserted the removed `constructor_paths_completed` key, producing one KeyError and one pass. That is a stale review-test schema failure, not a demonstrated failure of the corrected runner. The second test run changed the assertion to the real fields and added the signal-handler case. The counter-fixed runner snapshot matches the final SHA above.

Native success, physical phase sign, root applicability and runtime remain unobserved at review time. Conditional pressure bounds, endpoint gate outcomes and false material/event qualification must remain separately reported after the actual run.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — resolved constructor accounting, reviewed exact runner bytes and preregistered single-run scope.
