# Low-W native01 — independent saved-result review

**PASS**. The final passive audit completed **578 checks in 0.051 s**, with no failed checks. All **232 original native acceptance gates** were independently recomputed and match the saved report. The audit uses only the Python standard library and saved JSON/CSV plus byte identities; it never imports application modules, constructs an EOS, or replays integration.

## Confirmed outcome

- Actual native path: **2 accepted midpoint steps, 6 RHS calls, 0.05 s** model duration. Integrator **25.092409 s**, driver **26.357951 s**, supervisor **31.607637 s**. Original 60/80/100+5 s limits remain satisfied; supervisor returned 0 and reaped its leader. Containment remains limited to the original process group.
- The initially exact-dry cell retains zero liquid volume/no liquid pressure and its finite source dry-reference U offset. The saved first RHS preserves its named infinite local-phase and internal-moisture entropy limits. It rewets to **6.55708597041482e-8 mol** condensed water.
- Signed outward vapor totals **1.459816907207302e-07 mol**. The complete column loses that water with the saved signed projection terms; O2/N2 remain unchanged. Final condensed inventories are **6.55708597041482e-8 / 0.05999990791774635 mol**.
- Final T is **330.0000299215317 / 332.99993908405304 K**; P is **99598.59252809119 / 99815.86052220425 Pa**. Across the saved decoded predictor/middle/end contexts, maximum inverse residual-plus-U-error is **9.7382977875955e-6 J** (limit 1e-5 J), and maximum temperature bound is **6.066612255143385e-7 K** (limit 1e-6 K). Exact pressure-error intervals remain inside 90–110 kPa. Both final temperature changes exceed the registered resolution criterion.

## Accounting and source correspondence

Every predictor and accepted stage was checked separately: actual states/inverse/phase tuples, each shared face integral and decomposition, each cell's Nc, three gases and full U writeback, global stage balance, and accepted-prefix cumulative Nc/gas/water/U balance. Predictors do not enter the accepted physical total twice.

All declared arithmetic fees are now independently recomputable because both stage rate/integral records were saved. Recomputed cumulative U fee is **1.69848839622548e-12 J** (budget 1e-8 J); inventory fee is **3.746571886887304e-18 mol** (budget 1e-12 mol). These exactly equal the saved run's rational debits, including per-state writeback, face decomposition, internal moisture projection, and boundary vapor/enthalpy/heat projection from both stages.

Saved original source records reproduce the m/q nodes. At every retained context, exact low-W h and nominal-log s/F, md contributions, full U composition, pure-reference h/mu readouts, full condensed-water h/mu, activity, phase rates, internal D flux and carried enthalpy, factor, instantaneous entropy, k and conduction witness correspond. The common dry h0/s0 reference is preserved. This checks saved EOS native-reference transformations, not an independent EOS re-evaluation. The new source-resolution guard/model identity is included; this nonisothermal native case correctly leaves its equal-T/P residual field null and does not independently exercise the collapse rejection.

The constant low-W k branch receives the column's **binary64 W property**. Its source-excess and moisture-transport coordinates retain exact inventory-derived Fraction W. The audit compares each coordinate according to its actual declared path; constant k values agree with the original .30 source-provider evaluation.

## Runtime, freeze and export evidence

**2780 supervised inputs** match before/after. Category coverage includes all source/installed package files, numerical libraries and their distribution metadata, Python/venv, original water/gas/donor assets, protocol and final source-resolution model. All **181 source and installed files** match the frozen manifest. Installed regression XML records **213 passed**, zero failures/errors/skips, **146.930 s**; those tests were read, not rerun.

`TRACE.csv`: **6 rows / 84 numeric values** match saved state and actual decoded first/end observations. Its initial T correctly comes from the first inverse, distinct from the construction target T. `FACE_TRACE.csv`: **4 rows / 39 numeric values**, with predictor and accepted-middle times distinct and the initial singular entropy represented by an empty numeric cell plus its named state. All numeric and categorical fields correspond to RUN. The export script only reads saved JSON.

## Preserved audit failure and limits

`audit_saved01.py`, `AUDIT01.log` and `SAVED_REVIEW01.json` remain intact. The first audit passed the original 232 gates and all accounting/runtime checks but failed six k-coordinate comparisons because the auditor required exact inventory W at a deliberately binary64 property boundary. `AUDIT01_DIAGNOSIS.json` records that error. Version 02 changes that coordinate comparison, adds CSV and source-record-to-node checks, and passes; no model, native output, physical setting, budget or threshold changed.

The audit certifies correspondence of this bounded saved run. It does not certify independent EOS accuracy or its declared envelope, actual sludge/brick calibration, low-W or cross-material transfer error, a resolved kiln atmosphere, whole-step entropy, time/space convergence, long-duration complete drying, reactions/sintering/full firing cycle, material qualification or training eligibility. Nominal-log/physical uncertainties remain unknown. The fast-inverse draft was not part of this frozen native run.

Final reviewed transport SHA: `618486941301106095623ca6175b4ab7f3801ce05fb4feea55604e97cb68a3e0`.
Final source-resolution model SHA: `853ef0731172d091d965896a28d463464bb2d0c59ecc714228e012dbb0826b16`.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: **PASS** — saved run and bounded evidence are consistent; scientific qualifications remain unchanged.
