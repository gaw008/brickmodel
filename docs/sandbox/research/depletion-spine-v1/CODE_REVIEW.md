# Independent candidate review: nested ordinary wet spine

Reviewed candidate_depletion_integration.py against the current production depletion module, its PLAN/IMPLEMENTATION documents, the full independent test module and surrounding immutable state/rates, correction and integrator contracts. Review was read only except this report. No tests, model imports, EOS or production edits. Initial reviewed candidate SHA256: `298fe64e1cbdf3d0bf88d179d6c462a9f089df3573f9f9d8d27f618474929ad6`; initial reviewed test SHA256: `0d3bac204ecb626ce2cf5ebabd2f23cbfda5fc82ee60496c231f6943ab9f1bdd`.

## Findings

[HIGH] Cached observations retain caller-owned mutable buffers

File: candidate_depletion_integration.py:475 (also DepletionEvaluation at lines 78–85).
Issue: `_WetSpine.observations` stores the original `obs` without detaching its five observation sequences. DepletionEvaluation is a frozen dataclass but does not normalize its tuple-annotated fields; accepted deterministic callbacks may supply lists or arrays. A callback can deterministically calculate correct values while reusing an output list as a buffer on each call. A later dry observation can then mutate an earlier cached wet observation's evaporation rate to zero or alter its error radii. Cached traversal reads that changed buffer and can reject a valid evaporation as non-evaporative or use incorrect cached diagnostics, unlike uncached execution. The explicit same-input/same-output contract does not itself require ownership/immutability of returned containers. No malicious callback or object.__setattr__ bypass is needed.
Fix: detach the accepted observation sequences into immutable scalar tuples before any cache insertion (or normalize DepletionEvaluation at construction). Preserve validated Rates as its immutable copied record. Add a regression with a deterministic callback that reuses mutable observation buffers, comparing cached/uncached complete semantic results. Native WaterPhaseTransfer currently emits tuples, but manufactured adapters are a supported caching route and must meet the same ownership guarantee.

[MEDIUM] Failed independent approach records its actual cost twice

File: candidate_depletion_integration.py:637–644 and 659–664.
Issue: an independent comparison failure first appends `independent_approach_fail` with the full branch evaluations/costs, then raises _Failure inside the same try. Its except appends `independent_approach_comparison_failed` with the same full branch evaluations/costs. Global counters remain correct, but per-refinement cost records double-report a single executed branch and undermine unambiguous cost attribution.
Fix: keep one complete failed-comparison record and raise outside the logging try, or suppress the duplicate exception record after the comparison has been logged. Preserve ordinary exception diagnostics and add an independent-approach-failure cost-count assertion.

Both issues were sent to root; this review did not modify the candidate.

## Confirmed structure and remaining verification

The optional None/default path retains the old ordinary/terminal step decisions and five numeric gates; terminal Euler quadrature, nearest-downward clock evidence, correction budgets and commit function are unchanged. Additional comparison/cost metadata adds Python overhead but no extra default EOS observations. Full default regression remains an execution requirement, not proven by source similarity.

Spines are scoped to one accepted root, operator, common-time horizon, actual ordinary cap/safe fraction and event identity. Horizon restart creates a new spine and resets terminal-pass history. Cached edges contain only successful ordinary integrate results, while terminal panels, dry mode, dry continuation, corrections and independent approach remain freshly calculated. Path list containers are new; global commit still validates the full selected branch before any global mutation. Current state/rate arrays are copied and non-writeable through the existing integration types. The observation-container alias finding above is the specific gap in this otherwise isolated reuse design.

The independent approach halves BOTH ordinary cap and safe-inventory fraction and requires different actual endpoint grids. It compares full event and common-time N/E/T/P plus event time under unchanged gates, then commits the original twice-terminal-verified candidate. This avoids presenting identical shared-prefix trials as an independent approach refinement. It is still local to the event-search root, so the full outer trajectory discretization needs its separate check.

Actual cost counters increment only newly executed observations/panels/rejections; cache reuse has separate counters. Reuse traversal retains wall/cancel and energy-state guards. Global cost logic is distinct from the duplicate diagnostic record finding. Testing should assert each phase bucket sum matches global totals and each independent branch appears once.

Source admission binds stored source/model descriptors and fresh terminal/common evaluations continue to execute native source/config guards. There is no new guard-only revalidation of actual native files/config at each cache hit. Thus approval of reuse requires the documented fixed-runtime boundary and tests showing detectable source/model changes abort before commit; immutable descriptors alone cannot establish arbitrary external runtime immutability. The source-mutation/horizon/rollback/biased-approach tests requested by PLAN are not all present in the initial independent test module. Existing constant/linear sink, cache equality, immediate cancel, early panel limit and missing-determinism tests cover useful subsets, not the entire preregistered gate list.

## Exact corrective delta review

The two findings above are resolved in candidate SHA256 `88a9e4f613a0b7cc2fa6c5543b3a5c9ce02c6203a5fc5cba5c8205e00682c8d9`; `candidate-before-review.py` preserves the reviewed earlier bytes. This section supersedes the findings' open status, not their historical description.

`observe` now constructs detached tuples for all five numerical observation sequences before caching or event-state retention. This covers deterministic adapters that reuse lists or ordinary one-dimensional NumPy output buffers; immutable numerical scalar elements are preserved. Rates already owns copied non-writeable arrays. The new test explicitly reuses all five list buffers on every callback and compares full cached/uncached physical results.

Independent approach logging now sets a local `independent_recorded` flag only after successfully appending its completed comparison record. The exception handler records failures only if that completed record is absent. Thus a failed completed comparison remains exactly one detailed failure record; earlier exceptions still get their cost evidence. No global counting, solver criterion or rollback behavior changes.

Read the expanded independent tests: they now cover frozen diagnostic mutation attempts and cost sums, five existing multicell/horizon/restart rollback contracts executed through candidate adapters, the mutable-buffer regression, a deliberately biased fast reacting spectator that must fail independent approach despite two shared-terminal passes, and cancellation after cache reuse. The biased fixture intentionally loosens only its manufactured ordinary integrator to expose a rejection; it does not alter production wet gates. `check_costs` checks global phase totals exactly and prevents refinement costs from exceeding actual totals. An explicit count of one independent failure record would be an even more specific regression for the prior duplication, but code inspection confirms that path is now single-record.

Syntax parsing passed for the corrected candidate and expanded test file; no imports/tests were run by this reviewer. Root's extended test process was live during this review, so no outcome is claimed. Native source mutation behavior and default/legacy integrated regression still require their actual checks under the documented fixed-runtime boundary.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE the corrected candidate implementation; both reported defects are resolved. Actual no-EOS, default-regression and native runtime evidence remain separate execution gates.


## Final source-binding boundary correction

Final reviewed candidate SHA256: `ab465ad7a1da9d39787afd7dd2c6dfc24e680936e9a6c99593b345ddbc49135a`. The current production depletion module is byte-identical at this review. Compared the exact final delta against `candidate-before-final-binding.py`; no tests, imports or EOS were executed by this reviewer.

The strengthened fault schedule exposed a real HIGH defect in the earlier candidate: mutating the original operator source or deterministic descriptor during the last candidate terminal transition or independent transition could complete using a switched operator carrying the old descriptor. The original failing XML is retained: `source-guards-boundary-first.xml`, 6 tests, 4 failures, 0 errors, 1.737 seconds. This failure is not superseded as historical evidence.

The final correction retains a root binding independently of the optional cache. It validates that binding after terminal agreement before starting the independent branch and immediately before committing the selected path. Both checks apply with reuse enabled or disabled. Both ordinary and independent common-time restart handlers compare the OLD binding before changing the horizon and constructing the replacement binding, so a restart cannot silently adopt a changed descriptor. These checks are outside global mutation; failures return the previously committed wet prefix, preserving mode, event and correction rollback. The pre-independent and pre-commit resource guards additionally enforce cancellation/time limits at those boundaries. No acceptance tolerance, physical ledger, independent refinement or cost counter was changed by this correction. Existing native evaluations retain their actual source checks; this descriptor-binding fix does not claim continuous arbitrary external file immutability.

Read the complete strengthened source-guard tests: the baseline is used solely to locate the final two actual switch boundaries, with each of source_ids and deterministic_contract independently faulted. Tests require failure and no speculative events/corrections/mode commit, while checking actual evaluation accounting and positive accepted wet inventories. The fresh-source exception test and simultaneous-event rejection also retain original behavior. The final actual XML `candidate-final-tests.xml` records 20 tests, 0 failures/errors/skips, 5.828 seconds. This verifies the root's reported bounded no-EOS run, not a new execution by this reviewer.

Reviewed test SHA256 values:
- `test_spine_source_guards.py`: `377ab5d4f4bfb8952dcba7afb8e102517d6d414a55ac6978fd6ea8bc8c5fe8da`.
- `test_independent_spine.py`: `8125005ccedabf08930c0b6576b9abc7499ae79fb131ef877e5ec525d3be5879`.
- Transformed `test_depletion_spine.py`: `3cf526c20a9d0d95b13981295b7b3c3960f029e8e1b4de007a46c82ba1fc4a53`.

The transformed test replaces only the isolated dynamic module load with the standard package import and uses dictionary overrides for newly present policy/adapter fields, preventing duplicate keyword arguments. Numerical fixtures and assertions remain identical. Its installed-package execution remains a distinct subsequent gate.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE final candidate and reviewed test transformations. The mutable-buffer, duplicated-cost and final-source-binding defects are resolved. Approval covers implementation review and the inspected no-EOS evidence; installed regression and the source-qualified wet experiment remain separate execution gates.
