# Independent Python/numerical candidate review

Code verdict: APPROVE for continued bounded no-EOS validation; no CRITICAL/HIGH numerical or accounting defect found in the inspected candidate. Production/native signoff remains pending the explicitly missing preregistered cases below. No source edits, imports, EOS, tests or probes performed by this reviewer. Only static source/diff/AST inspection.

Reviewed candidate SHA: `298fe64e1cbdf3d0bf88d179d6c462a9f089df3573f9f9d8d27f618474929ad6`.
Reviewed independent-test SHA: `0d3bac204ecb626ce2cf5ebabd2f23cbfda5fc82ee60496c231f6943ab9f1bdd`.
Read PLAN.md and IMPLEMENTATION.md in full. Both Python ASTs parse.

## Numerical and ledger assessment

The legacy nested_approach=None path retains the former cap-coupled proposal. The terminal code changes only cost classification/observation labels: frozen Euler rates, downward root timestamp, DepletionClockEvidence, exact term integration, gross evaporation, correction limits and dry-mode transition are unchanged. All five original event/common-time comparison expressions and two consecutive terminal passes remain intact.

In nested mode, ordinary desired step length depends on fixed approach cap, current tau, fixed safe fraction and current horizon; it is independent of the terminal threshold. A cached segment is reused only for the same starting state object and requested endpoint, under a root binding that includes initial state/operator/time, energy identity, horizon, mesh controls, event identity, interface modes and source descriptors. Only fully completed ordinary segments enter the cache. Each proposal owns new lists; no terminal/dry path or correction totals are inserted. The unchanged commit audits the entire selected candidate before any global append or totals/mode mutation.

After two terminal passes, a completely uncached proposal halves both ordinary cap and safe-inventory fraction. This prevents an inactive maximum-step setting from creating merely nominal independence. Its grid must actually differ, and its event/common state and T/P-with-error observations are compared under the same original gates. Failure aborts without committing an event; success commits the original twice-terminal-verified candidate and records the componentwise maximum of the two sets of differences. This is an event-local convergence indicator, not verification of the earlier globally committed history or a proof of asymptotic error. The unchanged outer whole-trajectory comparison remains required.

Horizon replanning explicitly creates an empty spine and resets terminal pass history while retaining actual cost already incurred. Event identity mismatch rejects before reuse crosses a different event. Cancellation/resource checks occur during cache traversal. Fresh observations, normal integrations, terminal panels and comparison work are classified separately; reused observations/panels do not increment fresh evaluations or attempted panels. Static inspection found no double-charge or skipped commit edge.

## Source/determinism boundary

A nonempty immutable deterministic contract is required for manufactured callback caching; it is correctly presented as a caller promise, not automatic proof of purity. The actual oracle's counter changes call counts but not returned rates, so it is a valid deterministic-output test. Runtime fingerprints bind static provider/source descriptors, not arbitrary mutable native runtime configuration. The implementation document explicitly retains a fixed-runtime assumption between evaluations. Actual terminal/common-time decodes remain fresh and retain source/configuration guards before commit. This boundary must be stated in final evidence; the code must not be described as intercepting arbitrary monkey-patching at every cache hit.

## Existing independent tests

The five-case file checks constant and time-linear liquid sinks against an independent 70-digit Decimal integral/root, nonzero exponential A/B spectator, nonzero/cancelling component work, exact represented prefix sums and cache-on/off semantic equality over states, ledgers, events, corrections and accumulated totals. Equality excludes only true work/cost metadata; callback counters check actual evaluation accounting. Immediate cancellation, a low early panel budget and missing deterministic contract are covered. The tests never call production event helpers as their event oracle.

These five cases do not prove all PLAN conditions. In particular, current cancellation happens before any evaluation and current panel exhaustion occurs before useful cache reuse. Do not cite them as post-cache rollback validation.

## Required missing validation before production/native acceptance

1. Construct a deliberately biased coarse approach whose shared terminal thresholds pass but independent halved controls fail. Assert independent_approach_comparison_failed, original wet mode, no committed event/correction and unchanged global correction totals. This directly tests the main new scientific acceptance gate.
2. Check sum of each phase's evaluation/panel/rejection counts against result.evaluations/attempted_steps/rejected_trials and callback counters, for successful and interrupted paths. Verify reuse counts are nonzero where expected and not included in fresh totals.
3. Check deep freezing/detachment of comparison_details, phase_costs and reuse_counts, including nested caller-owned input containers.
4. Interrupt or exhaust resources after a cache node/segment has actually been reused; ensure no terminal/dry branch or correction is committed. The existing immediate/early cases are insufficient.
5. Exercise horizon replan / competing event, and a changed immutable source/model descriptor while a spine exists. Retain legacy tests for simultaneous/event-node rejection, but distinguish default-path coverage from the new nested path.

Ruff/mypy/pylint/black availability has not changed in the previously inspected environment. Public added policy fields are annotated; inherited compact code style and large existing integration function were not expanded into unrelated refactoring requests. No full-regression, native performance or wet-event success is claimed by this code review.

## Candidate corrections and 14-case extended rereview

Final candidate SHA: `88a9e4f613a0b7cc2fa6c5543b3a5c9ce02c6203a5fc5cba5c8205e00682c8d9`.
Isolated extended-test SHA: `8125005ccedabf08930c0b6576b9abc7499ae79fb131ef877e5ec525d3be5879`.

Reviewed the exact candidate-before-review diff: observations now detach all five potentially caller-buffered numeric sequences to tuples before storage/reuse; immutable Rates already owns copied arrays. This closes an actual mutable-output aliasing hazard while retaining numerical values. The independent-recorded flag prevents recording a failing independent comparison's cost twice when its explicit failure is then caught. It does not suppress failure propagation or erase the first complete detailed comparison record.

Inspected actual XML: independent-extended-first.xml has 14 tests, six failures, zero errors/skips, 3.180 s. independent-extended-second.xml has 14 tests, zero failures/errors/skips, 4.819 s. Five initial failures were isolated-module exact-class fixture mismatches; the corrected harness constructs candidate DepletionEvaluation while retaining the existing multicell physical assertions. The sixth was a negative counterexample that exhausted 14 refinements before reaching its unchanged 1e-11 mol event gate. PLAN explicitly records raising only that manufactured negative-test refinement count to 20 before rerunning, and requires subsequent independent-approach rejection. This is test reachability for a deliberately inaccurate approach, not acceptance through weakened physics/event gates. Prior failing source/XML remain preserved.

The extended tests now cover independent shared-bias rejection without event/correction commit, cancellation after nonzero cache reuse, phase/global cost sums, immutable nested diagnostics, a deterministic callback reusing mutable buffers, two-cell separated/accelerating events, horizon restart and resource-failure rollback. These materially address the missing cases from the initial review. A source/model descriptor-change test remains separately prepared/root-owned; deterministic-contract absence is not a substitute for that test.

Also read the proposed tracked-import transformation test_depletion_spine.py. The diff only removes the isolated dynamic loader in favor of the installed/standard module import, adjusts its descriptive docstring and merges new dataclass keys into old field dictionaries so the new fields are not passed twice. It preserves oracle values, numerical gates, assertions and the deliberate counterexample's 20-refinement scope. Approval of this transformation does not assert it has already run against installed production.

Code assessment remains APPROVE; source-guard tests and actual applied/installed checks remain required before the bounded v3 native execution approval becomes executable.

## Final late-boundary source fix and complete 20-case review

Final code verdict: APPROVE, including bounded v3 execution after the root's applied/installed identity gate. Current candidate SHA `ab465ad7a1da9d39787afd7dd2c6dfc24e680936e9a6c99593b345ddbc49135a`; source-guard test SHA `377ab5d4f4bfb8952dcba7afb8e102517d6d414a55ac6978fd6ea8bc8c5fe8da`.

Read the exact diff against candidate-before-final-binding.py. The root binding is now retained even when caching is disabled, checked before the independent approach and immediately before commit, and checked before a horizon reset can adopt a new root binding. After a legitimate horizon change it is rebuilt with that new horizon. This closes the final-transition gap: mutating the original operator after creation of a terminal switched operator can no longer leave a stale branch eligible for commit merely because no further ordinary cache loop occurs. All numerical gates, terminal clock/quadrature, immutable ledger work and correction budgets remain unchanged. Added guard calls preserve the original monotonic cancellation/resource deadline.

Reviewed the strengthened tests: an actual successful baseline identifies the last two terminal switches, then faults source_ids or deterministic_contract at those boundaries; four cases require binding failure and zero speculative commit. This use of the baseline only schedules a control-flow fault and supplies no physical numerical oracle. A fresh terminal WaterSourceError after reuse must remain failed with the failed observation charged once. A two-cell simultaneous event retains the original unsupported result and untouched state. Deep/cumulative totals and wet modes are checked on failure.

Inspected actual source-guards-boundary-first.xml: six tests, four failures, zero errors/skips, 1.737 s. This preserves the real late-switch defect rather than relying on the weaker earlier four-pass guard run. Inspected candidate-final-tests.xml: 20 tests, zero failures/errors/skips, 5.828 s. ASTs parse. No tests/EOS were rerun by this reviewer.

The previously missing descriptor mutation, fresh source failure and simultaneous nested event coverage is now supplied. Approval remains confined to this algorithm and the scoped fixed-runtime/provider assumptions: the manufactured mutation tests are not a new native-runtime uncertainty certificate. Applied byte identity, installed regression and actual v3 outcome remain root-owned verification steps.
