# Independent numerical review — draft, changes requested

Reviewed source SHA256: `39da99110b28ca0cbbf241c9008f825a6851c2cd02a22871ece5e15273a2b9e4`. Read-only source review; no EOS or tests executed by this reviewer. The author is still modifying the candidate; this is not final frozen approval.

[HIGH] Independent approach evidence includes post-event continuation
File: exact_depletion_integration.py, ordinary / independent branch
`path.grid` collects all ordinary endpoints, including mixed/dry continuation after the first terminal. Comparing this entire grid can succeed when only post-event cap subdivision differs. The legacy proposal freezes `approach_grid` immediately before its first terminal (depletion_integration.py around 945). Preserve that pre-first-terminal grid and require its actual difference; keep full grids as separate diagnostics. Add a negative control where the first event is terminal immediately and only subsequent dry grids differ.

[HIGH] Global budget mixes attempted trials with accepted-panel callee limit
File: exact_depletion_integration.py, guard / remaining_policy / ordinary / audit_commit
The global remaining maximum_steps subtracts `ordinary_trials`, but integrate_exact bounds accepted ledgers, and pending local attempted/rejected trials are only accumulated on return. A local run with rejections can exceed the declared global trial limit before commit. The old kernel actually charged accepted ordinary panels plus interrupted replan panels, with rejections independently bounded. A faithful minimal resolution is to retain attempted trials as diagnostics and use that original panel-accounting definition consistently for global guards and callee remaining panels. Otherwise a new explicit attempted-trial budget requires enforcement at each trial boundary. Preserve accepted local prefixes on resource termination without accepting an over-budget packet.

Other inspected numerical properties

- Every matched event and exact common endpoint contributes full N/E/T/P/stretch comparisons. Point temperature and independent pressure uncertainty floors are retained; explicit paired pressure is selected only under the original opt-in policy, with independent bounds retained.
- Event time uses exact semantic differences plus both selected root enclosure widths, with zero width permitted only by exact polynomial zero. Original time tolerance is an upper error gate, not a minimum root spacing.
- Two consecutive successful terminal refinements precede a separately recomputed halved cap/safe branch. Failed comparisons reset the counter; uncommitted attempts and all event frames are retained.
- Root ordering/full-panel/writeback use the actual numerical executor; this proves surrogate accounting and empirical refinement, not rigorous true-RHS enclosure or material validity.
- Prospective commit reconstructs original-initial species/energy/mechanical/component cumulative balances and correction totals before installing any packet.
- Scope remains explicit autonomous exact core. No legacy codec, service, continuation or material admission is established by this review.

Final disposition pending the two fixes and frozen-source/test evidence.

## Frozen fix review — APPROVE

Final source SHA256: `be323c820fe9f0c0981bb3bc7b4db817c8931c2501e704e394ae85a4c815a16b`.
Final test SHA256: `3e96e5a57c69076183daf74da2c4d80bd713c860d1ed698fc43f42312bb790f2`.

Both HIGH findings are resolved. `charged_panels()` consistently uses accepted ordinary panels + interrupted stage replans + terminal panel attempts, matching the original kernel budget definition confirmed by root. Predictor attempts and all ordinary trial attempts remain separately exposed diagnostics; rejected trials retain their independent original limit. Remaining policies and terminal dispatch use the same accounting basis. This does not claim maximum_steps is a bound on every rejected RK trial or every native evaluation.

The actual approach grid now extends only while no terminal frame exists. Thus post-first-event mixed/dry continuation cannot make an otherwise identical pre-event grid qualify. The regression checks every recorded approach endpoint is at/before the first terminal start while continuation actually proceeds beyond it. Both cap and safe fraction are halved on the independent branch.

Final reread confirms original six event/common gates, exact bracket uncertainty, two consecutive terminal passes with reset on failure, actual independent branch, all-event matching and original-initial atomic balance audit remain present. No further blocking numerical finding in this bounded review. Existing autonomous/source/model and research-only schema restrictions remain in force.

Evidence inspected: tests18.log/XML reports 16 passed in 5.92 s, including the actual rejection/one-panel budget regression. Reviewer did not rerun tests or EOS. This approval is for the frozen numerical driver and its stated accounting/refinement contracts, not proof that the forthcoming four-cell native trajectory completes, nor material validation/service resume admission.
