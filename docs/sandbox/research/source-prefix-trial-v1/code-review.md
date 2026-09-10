# Final source-prefix trial code review

Baseline: `cc94ecb`. Scope: Euler extraction in `exact_integration.py`, new `source_prefix_trial.py`, its tests, the pre-extraction Euler fixture, and the prepared native runner. Read surrounding `integration.py`, `exact_source_column.py`, `source_net_panel.py`, existing source-prefix validation, and prior native construction/serialization helpers. No repository edits, installations, native HEOS evaluations, or commits were performed by this reviewer.

## Findings and closure

No confirmed unresolved defect in the final bytes listed in `FINAL.json`.

The extracted Euler predictor retains the original represented derivative/product/update sequence, energy identity, mechanical predictor positivity and original exception classes. The inherited small-product underflow behavior remains explicit and is not silently replaced with source-affine quadrature semantics. The golden test compares full deterministic callback inputs/rates, accepted states/ledgers, rejections and statuses for twelve cases captured before extraction.

The actual source trial evaluates the original state, the original Euler midpoint predictor, and the affine prefix endpoint. It requires actual endpoint storage inversion, all positive inventories and no interior forcing knot. It evaluates the existing exact integrator on the same exact interval using unchanged scientific tolerances, with only its remaining wall budget reduced. The direct amount/energy discrepancy has no one-third factor. Qualified success includes passive replay of retained reference rates and recoverable DomainExit attempts, comparing all deterministic reference-result fields. Replay does not call the source/EOS operator.

The root reviewer discovered and executed a recovery counterexample while this review was running. Before correction, a reference completed after recovering from its sixth callback DomainExit, but the trial's own check downgraded it to `numerical_failure` because all captures had been required to succeed. I read the actual root probe JSON and provider RED traceback. The final implementation binds a failure kind/message to every attempted input, permits retained recoverable reference DomainExit records, and recreates those failures in the same replay order. The new production regression passes. This is a corrected false failure; no physical event or material qualification is granted.

Previously closed mutated-reference-ledger, outcome/policy binding, finite discrepancy, and failed-attempt input/message defects remain covered by executable regressions. Failed trials retain their attempted inputs, observations where available, and failure classification/text. Cancellation and callback/wall limits do not silently authorize a prefix.

Prepared runner persistence and timeout behavior were independently executed using manufactured source fixtures only; see `RUNNER_REVIEW.md`. A final reviewed runner change marks its own SIGALRM timeout explicitly and reports the probe status `resource_limit`, retaining the nested trial classification and raw callback exception. Arbitrary source TimeoutError exceptions do not acquire that outer-alarm marker.

## Actual verification

Command:

```
PYTHONPATH=src:tests/sandbox /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest -q tests/sandbox/test_exact_euler.py tests/sandbox/test_exact_euler_legacy.py tests/sandbox/test_source_prefix_trial.py /private/tmp/brick-source-prefix-trial-v1/code-review/test_runner_persistence.py --junitxml=/private/tmp/brick-source-prefix-trial-v1/code-review/final-review.xml
```

Result: **46 passed in 39.17 s**, zero failures/errors/skips. This comprises ten Euler predictor tests, one full twelve-case legacy comparison, 31 source-trial tests, and four independent runner persistence tests. Earlier standalone runner persistence tests passed 4/4 in 2.94 s. All reviewed Python files parsed successfully. `git diff --check` passed. Installed-package and actual HEOS outcome verification belong to the root runner and are not claimed by these tests.

Final production hashes: `exact_integration.py` = `d65b6844141ff73f4ad23cee5950e4548062646072195b862e8bfb5125af4409`; `source_prefix_trial.py` = `d092a37fe69be5e5cae968f7c7967233ea8cdd4837428bf6236ddbed3c204b99`. Final runner = `cd194586d9ffd8455b26ac54e94656c6d0b1a1a719de4d3312ee027b8b690c78`. The five runner tests were then run on these final runner bytes: **5 passed in 3.02 s**, including invocation of the actually registered SIGALRM handler during a manufactured source callback. The raw TimeoutError, nested failure and top-level `resource_limit` were retained; original signal handler and disabled timer were restored. No production source changed after the 46-test run. Test/fixture sizes, hashes and parsed XML counts are retained in `FINAL.json`.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — stated source and runner bytes, with no native material-model validation claim.
