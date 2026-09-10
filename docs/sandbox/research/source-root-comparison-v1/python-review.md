# Independent Python review — source-root-comparison-v1

Decision: APPROVE the final reviewed bytes. One local exact-clock input validation issue was found and fixed; the two actual RED cases now pass. All eight distinct independent cases have final passing evidence. No native or HEOS work was performed.

## Scope

Read-only review of `src/sludge_sandbox/source_root_comparison.py` and its author tests, with narrow reads of reused exact integration, exact clock, source trial, endpoint, and record comparison helpers. The new files are untracked; the requested initial `git diff -- '*.py'` was empty, so the actual full files were read directly. Production files and author tests were not edited.

Initial reviewed production SHA-256: `67833a38bb5956bacb08ebfd2ce367ac5163db8ce2413cb53db5c3a19fad8486` (17,533 bytes). Author tests SHA-256: `8741c81c72469a56af2e8664a67ab33e038030b4dbae68f1ae627a502b219d85` (9,105 bytes). The exact pre-fix files are saved as `before-source_root_comparison.py` and `before-test_source_root_comparison.py`.

## Finding, now fixed

[MEDIUM] Exact-clock nested scalar is not revalidated

File: `src/sludge_sandbox/source_root_comparison.py`, `compare_source_root_clocks` input guard.

The function requires each start to have exact `ExactEventTime` type, but does not require its nested `seconds` value to remain an exact `Fraction`. After constructing a valid time and replacing its frozen field with `object.__setattr__`, both integer `1` and boolean `True` are accepted. Rational addition subsequently produces valid new interval endpoints, so the malformed original start remains accepted instead of being rejected. These are actual independent RED cases, not merely static observations.

The parent applied the local fix: exact `Fraction` seconds are revalidated for both starts before arithmetic and for the common endpoint input. No global clock code changed. The complete production difference was reviewed: these two guards plus explanatory docstrings about per-reference-step maximum limits. The associated author tests add malformed clock and common endpoint regressions. No incorrect physical event or material claim was observed in the original cases.

Final reviewed production SHA-256: `b9328c5620d6bf27e6b7cbd75430aaf7a7bba136c7760ad9c6cb6843ba3c1c87` (17,986 bytes). Final author tests SHA-256: `500d8eb55002365ecfea2a8a334cc419f9bb5628247c4d9e93261a19a232b199` (9,686 bytes). Both final files parse successfully; `git diff --check` passes. Exact before/after diffs and hash manifests are preserved.

## Execution evidence

- `first.xml` / `first.log`: 4 passed and 2 actual RED cases, 0.21 s pytest wall time. Passed cases cover cumulative amount and energy rejection and exact large positive/negative origins. RED cases are the nested clock scalar mutations described above.
- `failure-retention.xml` / `failure-retention.log`: 2 passed, 6 deselected, 6.18 s pytest wall time. These execute the existing manufactured source fixture, not a native backend.
- `clock-green.xml` / `clock-green.log`: the two previously failing cases pass, 6 deselected, 0.21 s pytest wall time, after the local fix. Unchanged passing cases were not rerun. Total independent pytest wall time is approximately 6.60 s, below the 30 s budget. There was no single eight-case final batch; the preserved runs establish final passing evidence for eight distinct cases.

The cumulative ledger fixtures are deliberately `SimpleNamespace` helper inputs and are not represented as actual `SourcePrefixTrial` evidence. Each of two segments has residual 1 within tolerance 1.5; joining them correctly rejects residual 2 from the shared original state. Both amount and energy are checked independently. Separate accepted helper examples keep exact ledger times at origins ±10**400.

The two actual source failure probes verify:

1. Cancellation of the second common path retains the first completed reference trial and the second cancelled trial, including zero actual captures on the cancelled path. The failure stage and chained cause are preserved.
2. An exception in shifted root assessment retains the preceding approach and the actual shifted trial with its two completed source attempts, original failure reason, stage, and RuntimeError chain.

The review confirms that the common endpoint uses the final captured actual reference states, the shifted path begins at the preceding actual reference endpoint, and the cumulative fine ledger is measured from the original shared state. Reported endpoint gates, conditional pressure gate, and surrogate clock comparison remain separate, with event/material qualification false.

AST parsing passed for the captured production and author test files. Ruff, mypy, pylint, Black, and Bandit are unavailable in the existing interpreter and were not installed. Parent owns author-suite, integration, installed identity, and native evidence; this review does not duplicate or claim those checks.

Machine-readable before/after identities and actual XML suite summaries are saved in `FINAL.json`. The original RED log and pre-fix source remain intact. No review blocker remains within this bounded scope.
