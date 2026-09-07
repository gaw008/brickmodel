# Independent code review: reacting wet experiment scripts

Reviewed the exact temporary fixture.py, callback.py, depletion.py, compare.py, run.py and PLAN.json against production commit 69a14f4. Production was clean at entry. Read imported fixture constructors, actual water-transfer/depletion interfaces, correction record definitions, and existing research supervisor behavior. No scripts were imported or executed; no EOS, tests, probes, installation or production edits. Initial file hashes match all five declared PLAN hashes; syntax-only AST parsing passed, recorded in code-review-initial-files.json.

## Finding resolved before execution

[MEDIUM] Comparison failures before numeric checks do not write current failure evidence

File: compare.py:main.
Issue: loading a missing/invalid file or failing the passed/initial-state assertions exits before writing comparison-result.json. A failed comparison therefore has no current structured failure artifact and may leave an older result visible. This contradicts the requested failure-evidence discipline even though valid inputs proceed to a correctly persisted numeric gate result.
Fix applied by this reviewer at root request: compare.py now records each available input SHA/size, persists status/error/traceback through try/except/finally, and records finite numeric differences before assigning pass/fail. Nonfinite differences raise an explicit failure before JSON serialization. Original compare-before-review.py preserves the initial script. The separate Python reviewer subsequently approved this exact final delta and PLAN hash; see PYTHON_REVIEW.md. No execution was performed.

## Confirmed implementation and scientific limits

The fixture explicitly builds a complete A/B/H2O/H2O_liquid/carrier layout and actual A/B providers. A/B Cp, molar volumes, common formation reference, standard-pressure correction, and declared uncertainties match the preregistration. First-order A→B is nonzero with prefactor 0.1 and activation energy zero; its new 295–310 K manufactured validity interval is declared rather than borrowing the old incompatible lower bound. Actual reaction configuration construction binds complete providers, current storage and gas constant. The new manufactured q has positive q0 and wB=10/mol. The interface coefficient remains 1e-6, reference interface energy changes explicitly to 0.3 J, and initial E is freshly computed under the new reacting identity.

HEOS, ideal vapor and chemical bridge are constructed with the same approved water backend manifest. Their original runtime source gates remain active. The installed identity function checks actual loaded sludge_sandbox module paths and byte equality against source. Supervisor input manifests additionally observe installed/source package files, all imported test-helper files, water data, scripts, PLAN and supervisor code. These manifests are hash observations, not immutable snapshots. Callback stores actual water implementation/source metadata and is required to match the newly constructed initial state before either depletion run.

Callback assertions jointly require nonzero solid reaction and evaporation, equimolar sources, no carrier source, closed faces, exact current reaction storage identity and reused original thermal inverse. The wrapper must preserve all five new mechanical components and total cell power. No additional composition, latent or reaction heat term is introduced. The finite energy/temperature gates and pore-volume arithmetic are tested before callback can be marked passed.

Depletion saves the complete returned states, steps, events, refinement records, correction records and totals before status/event assertions. Failure later in prefix or final diagnostics retains that original run data in the final failed record. Every accepted prefix checks A+B, analytic A(t)=2 exp[-0.1(t-START)], water sum, unchanged carrier, closed faces, total E and exact Fraction component-sum residual. Event error fields are individually bounded at the preregistered five gates. Three correction sums are separate: signed vapor-storage rounding, absolute vapor-storage rounding, and ideal numerical phase correction; each is independently reconstructed from correction records. The three values are not conflated with net physical evaporation.

The script requires exact dry mode, exactly one event, liquid zero after the event, a retained nonzero interface coefficient, zero post-event phase-transfer rate, and continuing nonzero A→B reaction plus an actual further decline of A between event and final state. Thus disabling either mechanism cannot trivially satisfy the experiment. Final solid/pore geometry is checked against actual A/B and current bulk volume.

The prefix water bound is a total conservation check; correction-only accounting does not by itself separate every per-step species update rounding residual. Complete returned ledgers permit that later independent audit. Similarly, per-step power components establish bookkeeping but do not supply an independent wet thermal oracle or RK stage replay. The two-run comparison uses all inventory columns and total E/T/P/event time, with unchanged gates; the wet amount comparison 1e-10 mol is explicitly the event gate, not the separate A analytic 1e-9 mol gate. Neither single-run success nor two-cap agreement qualifies raw sludge or free sintering.

The supervisor runs children without a shell, with test helpers as PYTHONPATH while requiring actual package imports from site-packages. Callback and integration have explicit 30/150 s external deadlines; integration retains 120 s and 500-panel internal bounds. Frozen-script execution order remains a root responsibility; no concurrent EOS or automatic retry is introduced by these scripts.

## Final supervisor delta and file identity

Independently reviewed the Python reviewer's run.py delta: successful exit now requires supervisor status `complete` AND child returncode 0. This prevents supervisor-reported timeout/input-integrity failure from being flattened to success merely because the child exit code is zero. It matches the actual supervisor status contract. Approved run.py SHA: `dcc9ba014c8f642824f25662dc0ac39961f5580e0db85d367f7032bb7369e612`.

Final compare.py SHA: `b2f9385f489f3362f88bea79e21b8e9c40a3557a359a45945f8e20b687ede3c3`. PLAN was updated sequentially after the other reviewer released it, preserving their run hash. Re-read and matched all five final script hashes, and parsed AST without importing: `code-review-final-files.json`. Callback, fixture and depletion bytes remain unchanged from the initial reviewed freeze.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE the callback, fixture, depletion and supervisor logic for bounded execution. The corrected offline comparison has been independently cross-reviewed and approved by the separate Python reviewer. Runtime validity remains unproven until execution.
