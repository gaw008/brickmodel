# Independent Python review — source-approach-v1

Decision: APPROVE the reviewed production bytes. No additional CRITICAL or HIGH correctness issue was found in this bounded review.

## Scope and identity

Read-only review of the new source approach module and author tests, with targeted reads of the reused exact-duration control, prefix trial callback guards, root ordering, and policy-copy/binding paths. No production edits, native reconstruction, new HEOS runs, or broad integrated suites were performed. Parent owns integration and native evidence.

- `src/sludge_sandbox/source_approach.py`: SHA-256 `5364e5dd471523d6f47e512924c884aff1329938632779cbe051795c3139c007`, 13,291 bytes.
- `tests/sandbox/test_source_approach.py`: SHA-256 `de129eb80d833f6a061f4b349efb1b75006ed83df950e0d4ef1ab9ffec3050d1`, 11,424 bytes.

These files were untracked, so the requested initial `git diff -- '*.py'` did not display them. Their actual full contents were reviewed. Both parse successfully with `ast.parse`; `git diff --check` passes. Ruff, mypy, pylint, Black, and Bandit are unavailable in the existing test interpreter; they were not installed for this review.

## Independent execution evidence

`test_independent.py` contains 12 distinct manufactured cases using the author's existing manufactured source fixture and exact rational polynomial fixtures. No claim of a single 12-case batch is made:

| Preserved XML | Actual result | Suite wall time |
| --- | --- | --- |
| `first.xml` | 10 passed | 3.703 s |
| `failure-paths.xml` | 1 passed, 1 reviewer-harness assertion failed | 1.157 s |
| `adapter-green.xml` | Corrected adapter case passed; 11 cases deselected | 0.954 s |

Thus all 12 distinct final cases have passing evidence. The failed harness originally expected two source callbacks after a callback changed its adapter identity. The existing callback guard correctly detected the change immediately after the first callback returned. The corrected test expects one callback and confirms the returned observation, failure, actual trial, and chained assessment exception are retained. No production change was needed for that failure; it is not a product RED. Raw logs and XML remain preserved.

Coverage includes:

- Completed record checking with new source evaluation forbidden.
- Rejection of duck-typed replacement proposals on both completed and unexecuted records. The exact-class guard was already present in the tested production bytes; this was not a discovered product defect.
- Rejection of a valid-looking relaxation to the saved nested roundoff policy.
- Rejection of boolean callback/count controls and event/material qualification upgrades.
- Downward adoption of a nonrepresentable exact duration without crossing the original rational bound.
- Subnormal positive candidate underflow remaining below the original minimum step instead of relaxing that minimum.
- A real second-callback `RuntimeError`, preserving the first observation and the second failed attempt, with no endpoint comparison or pressure record fabricated.
- Actual adapter mutation detected after the first callback, with trial and exception context retained even when final result checking fails.

## Assessment

The implementation uses the existing rational root ordering and exact duration control, retains separate endpoint and pressure evidence, copies and binds the complete event policy, and keeps `event_admitted` and `material_qualified` false. Failure paths retain actual callback evidence. The parent-identified postprocessing retention and external policy mutation fixes were present before this review's execution.

A small nonblocking type-annotation suggestion was sent to the parent: annotate the new public `SourceApproachAssessmentError.__init__` parameters and the `cancel` callback. This is an interface clarity suggestion, not a demonstrated runtime defect. It does not authorize physics, event, material, or full-model completion claims.

Machine-readable hashes and actual XML summaries are in `FINAL.json`. Review scope is bounded to this stage and does not certify all legacy code or physical model applicability.
