# Prospective native controller cost and case review

Do not schedule a complete native controller from the successful ordinary stage yet. The saved original native initial liquid inventories have initial tangent depletion estimates approximately 1884.31 s and 890.43 s, whereas the demonstrated stage covers 0.001 s. These are sampling diagnostics, not nonlinear event times. Simply extending that case to the estimated times would demand enormous numbers of steps under the original 0.01 s maximum step, and may leave the thermal/model domain. Its current success does not establish an economical event case.

This review reads existing saved numerical JSON and current controller source only. count_saved.py uses standard-library decoding/Fraction arithmetic; counts.json preserves the exact derived counts. No controller, native EOS, mathematical proof, installation or old artifact modification occurred. Tesla's proposed opt-in route is not reviewed here as a frozen implementation.

## Required full work

The current controller starts each proposed path from the original state, original context and empty correction totals. It needs a complete coarse path, two further complete terminal-window paths with consecutive passing comparisons, and a fourth independent complete path with both approach cap and safe fraction halved. Failed comparison resets the consecutive-pass counter. The independent actual pre-first-event grid must differ; a reused spine or relabelled grid cannot substitute. Every event and common endpoint retain kg/mol/U/T/P/time gates, including both clock enclosure widths. Exactly coincident/unresolved roots and any physical/domain failure remain failures.

For a completed no-rejection path with n ordinary trials and e terminal events, actual host calls equal 10n+4e+1: ordinary9 plus one preceding observation; terminal2 plus preceding observation and post-mode endpoint; final common observation1. Rejections add9 per fully evaluated rejected trial without necessarily another outer observation. Failed attempts contribute only reached work and must stay in cumulative accounting. Charged panels are 3n+e, not the number of accepted ledger halves.

The actual saved manufactured two-event run has four paths:

| Path | Ordinary trials | Events | Host calls | Charged panels |
|---|---:|---:|---:|---:|
| coarse | 4 | 2 | 49 | 14 |
| terminal level1 | 6 | 2 | 69 | 20 |
| terminal level2 | 8 | 2 | 89 | 26 |
| independent | 18 | 2 | 189 | 56 |
| total | 36 | 8 | 396 | 116 |

These counts are extracted from actual saved per-path attempts and independently satisfy the formula. The accepted18-panel path does not represent total cost. Copying its accepted work alone would underbudget by more than fourfold.

With the same saved grids/modes, native pressure queries would number92 during ordinary full/fine comparisons (two queries per remaining wet cell) plus6 for three path comparisons: each first-event pair has one surviving wet cell, while second-event and final common states are dry. Thus98 queries and392 whole proof operations would be needed. The measured five seed evaluations per query would suggest490 seed evaluations; that is an observed planning rate, not a bound. The fixed seed policy permits up to24 evaluated Newton points per query (12 for each of two temperatures), so a finite budget that admits all such attempts requires up to2352 seed evaluations for98 queries. Primitive box limits remain independently bounded. A failed proof may do fewer operations; counters cannot be filled with fictional completions.

Even an unusually small two-event complete experiment with one ordinary approach trial per path needs at least76 host calls and22 wet pressure queries under this structure. This is a structural lower-work illustration, not proof that one ordinary step can meet the original gates or independent controls.

## Actual timing interpretation

Saved native stage elapsed60.742859 s already includes four session queries totaling12.089176 s. The remainder48.653683 s covers nine host calls plus all stage bookkeeping and source guards. Consequently 60.74/9 is not a pure host timing. A useful conservative accounting proxy at the observed points is5.406 s per host-call-equivalent and3.022 s per pressure query, without double-counting math. It is not a global cost upper bound: native near-depletion roots, inverse iterations, proof boxes and input guards may be slower.

On the saved396-call/98-query shape this proxy predicts about2437 s (40.6 min) before setup and any cost growth. Even the structural76-call/22-query illustration is roughly477 s (8 min). Scaling the source's 120 s controller resource allowance cannot certify completion; retain its scientific gates but preregister any separate resource-policy change openly. Existing maximum4000 callbacks and2000 charged panels are bounds, not a reasonable requested workload for this first native controller study.

## Minimal next useful choice

First keep native full/fine stage as the completed ordinary-step milestone. Before a full controller request, register one explicit positive-liquid manufactured initial-inventory case intended to reach both distinct depletion events inside the existing short time/temperature domain. Keep solid/gas/transport/kinetic/source/envelope values and all scientific gates unchanged. Any change to liquid inventory or horizon is a new named case, recorded before results; it cannot be described as continuation of the saved .02 mol case. Do not set epsilon liquid to mimic dry, tune values after failures, or borrow another cell's gross evaporation.

Use a single bounded actual preparation measurement for that registered state before committing to all four paths: initial actual forward construction and one current pair observation to check wet domain, true chemical directions and tangent sampling estimates; then, if separately preregistered and budget permits, one exact terminal preparation and post-projection mixed observation with one surviving-wet pressure query. This would directly test the currently unmeasured native near-depletion inverse/proof cost and dry/mixed seam. It is not controller acceptance and must never bypass original terminal/root/writeback gates. Failed or insufficiently separated evidence stops the study and remains saved. Numerical selection from old rates alone is insufficient because changing liquid inventory changes pressure and reaction/phase dynamics.

Only after that measurement should a full two-event candidate be costed. Count a proposed complete four-path schedule using the formula and actual wet-mode query counts, reserve rejection/refinement allowances explicitly, and choose a finite cumulative work budget. A deterministic budget formula is Q_max <= 4*ordinary_trial_limit + 2*(wet_cells summed across all compared frames/common states), proof_max=4*Q_max, seed_max=24*Q_max, with tighter mode-specific counts when known. Maximum refinements bounds the number of comparison calls; every failed/rejected path still consumes the same session budget.

Set controller wall and shared session elapsed wall at the original controller entry, including intervening native host work; no query-level reset. Choose the whole process bound from setup plus that single cumulative lifetime and a modest save/cleanup allowance. The measured timing proxy supplies an estimate only; finite work/wall caps and the external process-group watchdog supply enforceable stopping. A timeout produces an uncommitted failed candidate, never a shortened accepted packet. Preserve all original samples, attempted work, source/mode lineage and previous candidate comparisons.

No complete-controller execution is recommended or authorized by this report. The next decision needs a frozen native event case and one bounded near-event cost/domain measurement, not a larger blind wall budget on the present long-drying initial condition.
