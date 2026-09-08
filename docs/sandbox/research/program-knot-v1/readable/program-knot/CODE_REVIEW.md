# Program-knot endpoint Python review

Scope: `src/sludge_sandbox/depletion_integration.py`, new `_ordinary_program_endpoint` and ordinary caller; `tests/sandbox/test_depletion_program_knots.py`. Review performed from actual `git diff -- '*.py'` and surrounding ordinary-integrator, candidate and commit code. No source or test edits and no EOS calls. The expanded test file is frozen and reviewed below.

## Implementation assessment

No CRITICAL or HIGH implementation issue found in the inspected candidate. The helper only extends an existing cap-selected endpoint to its immediate program boundary. Both the original nominal cap and full adjusted exact endpoint duration must respect the exact inventory safety duration. In particular, a rounded limiter and cap can alias without authorizing an unsafe extension. Fraction conversions precede duration subtraction and safety comparisons.

The one-boundary-ULP guard is additionally bounded by local cap ULPs, and an independent exact duration-versus-cap bound prevents large absolute clocks from authorizing a large relative step change. Existing already-target panels remain unchanged. Nonfinite API times and invalid policies are validated upstream; the private helper is not a new public input boundary.

The caller passes the chosen endpoint to `normal`; `integrate` derives actual endpoint durations for every RK stage and ledger. There is no timestamp relabeling, discarded positive interval, synthetic correction, or changed terminal-event path. Existing midpoint-resolvability, stage validity, adaptive error, source/schema, cancellation, resource and exact cross-segment prefix guards remain on their existing paths. The dry branch already targets the whole boundary and returns unchanged from the helper.

## Tests and outstanding verification

The first eight tests inspect whole constant-source trajectories against independently integrated sources, knot inclusion, conservation, ordinary control, genuine small intervals, cancellation, and explicit one-sided piecewise restarts. The evidence writer preserves result state before assertions and creates files exclusively, protecting baseline evidence. Restart coverage is explicitly two operators across two calls; it does not establish arbitrary discontinuous callback endpoint semantics in one run.

Before broad regression, add the coordinated inventory-safe tie and numerical-edge counterexamples. Exact safe endpoint equality and a cap-safe but target-unsafe tail must be distinguished. Public behavior tests are preferable where they isolate the issue; private-helper adversarial cases are appropriate for extreme clocks and ULP limits. Root must execute the resulting frozen test set and retained original .005 fixtures before claiming the defect fixed.

AST parsing passed for both changed files. `ruff`, `mypy`, and `black` executables were absent from PATH and the installed test environment, so no lint/type/format pass is claimed. No security-sensitive input handling was added. Existing compact module style is retained; broad formatting is out of scope.

Status: implementation approved for the coordinated targeted validation, pending review of the expanded tests and actual results. Not a material-physics or full Goal approval.

## Frozen-candidate follow-up

Source SHA256: `d5620710820e313c334468bd2f180ee43a63e677e6f4d355b9844498d8806ba5`.
Test SHA256: `0ecb4151afb8ba3e641048f009d279056dcb18be98ca58f25a1aced37de32f4c`.
Both files passed AST parsing after the expanded tests were frozen.

Compared the actual helper against every condition in NUMERICAL_REVIEW.md. The exact target-duration and nominal-cap safety checks, separate duration/cap representation bound, and local one-boundary-ULP limit are present. Finite validated inputs are an upstream precondition of this private helper, rather than repeated public validation. No new caller skips a committed physical interval.

The added public tests cover an exact inventory safety boundary whose rounded cap aliases the proposed endpoint, negative clocks and a zero knot, and a large-origin/sub-ULP cap that must not be inflated. These are behavior-level counterexamples, not restatements of the helper implementation. Two affine-event regressions explicitly use the current configured tighter ordinary accuracy; they cannot substitute for the separately retained original coarser-accuracy failures. No additional private condition-mirroring tests are required for this bounded implementation approval.

[MEDIUM] Saved knot reference metadata is constant across fixtures
File: tests/sandbox/test_depletion_program_knots.py:44
Issue: `_save` records `.05` as `knot_hex` and the reference for `remaining_to_knot_exact_s` even for negative/zero/no-knot fixtures. The full times and result are intact, but these auxiliary fields do not describe every fixture's configured boundary.
Fix: Identify them explicitly as legacy .05 reference diagnostics in archived evidence interpretation, or parameterize those fields in a future evidence-writer change. This does not invalidate the actual trajectory assertions.

Final code-review disposition: approve the frozen implementation and expanded tests for targeted/installed regression. No CRITICAL or HIGH issue found. The evidence-metadata caveat above must remain visible. Actual regression outcomes remain root's responsibility; this review does not claim they passed.
