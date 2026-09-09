# Smallest coherent numerical multi-event integration

Read-only design against current source. No EOS or edits. **Proceed under the existing numerical acceptance contract:** sampled affine terminal model, two successive accepted refinements and independent finer approach, original cellwise tolerances and conservation/correction budgets. A new rigorous true-RHS enclosure is not a prerequisite for this numerical extension, because the current single-event integrator does not provide one either. Group records must state numerical affine-surrogate localization, not true physical root proof.

## 1. Remove the premature tie rejection only for a versioned opt-in path

Current candidate (depletion_integration.py:546–560) rejects initial N/−Ndot ties before any advance. The ordinary main-loop branch at1083–1090 already takes normal RK panels bounded by safe_fraction*min(tau), checks all stage inventories and commits accepted ledgers. Proposal approach at795–810 has the same safe advance structure.

For explicit group mode, return a typed candidate set with minimum tau and near-tie members instead of immediately raising. While minimum tau exceeds terminal cap/window, take exactly that existing ordinary positive-stage RK path, bounded using the minimum over ALL wet candidates. Recompute all rates/ties after each accepted panel. This can split the initial4cell tie through heat/gas dynamics without perturbing initial data or choosing a sibling by index. Preserve original RK domain rejection, errors, budgets and source checks. Describe it as the existing numerical positive-stage advance; do not claim rigorous between-stage true-ODE positivity.

If the candidates become sufficiently separated before terminal entry, use the unchanged single-event route. If a tie remains near the terminal cap, enter a group terminal path. Do not keep taking an unbounded chain of vanishing safety steps solely to avoid implementing the group. Existing maximum_steps/minstep/wall caps remain.

## 2. One shared affine terminal panel, not one panel per member

Reuse affine_terminal562–639: one Euler midpoint predictor for full N/E/mechanics; one actual midpoint observation; one common affine interpolation of every face/source/work/mechanical rate. Build an AffineInventory for EVERY wet liquid cell from the same initial/midpoint rates. `depletion_group_clock.py` already provides polynomial minimum/positive_panel (41–48,106–113), isolate_roots116 onward, group_roots147 onward and outward_absolute_times182 onward. Their intervals refer to this numerical polynomial, not the true nonlinear solution.

Use the earliest numerical root cluster; include all cells whose intervals are not separated from that cluster under the original time gate, with union width checked. A nonmember whose numerical polynomial reaches zero earlier is not permitted. Require full polynomial N and stretch positivity on the shared panel as current lines619–632 do; allow zero only for selected group liquids. All fields get one shared StepLedger.

## 3. Shared time and per-cell residual

Choose a represented shared endpoint at or below the smallest member polynomial root (downward enclosure), so no member is advanced past its numerical depletion into negative liquid. Tighten pure root isolation if endpoint rounding leaves ordering ambiguous. Preserve every member's individual interval and the group's union; require union width<=original time_absolute_s. Exact coincident polynomial roots naturally recover the single-clock special case.

At this common endpoint, each member may retain small positive liquid. Compute its exact polynomial residual and the represented cell inventory independently; transfer only that cell's accepted residual to its vapor column, leaving total E and mechanics unchanged. For EVERY member require original correction_absolute_mol and correction_fraction_evaporated based on its own positive-affine evaporation integral, plus original local storage/element/mass bounds and global cumulative totals. A large physical-looking residual does not become acceptable because another cell has smaller error. If any member fails, reject/refine the entire speculative path.

Crucial implementation distinction: current depletion_writeback expects an individual clock whose endpoint rounds that member's root (640–645). A later member at an earlier group time does NOT satisfy that clock proof. Add explicit GroupMemberLocalizationEvidence with shared endpoint, individual numerical root interval, polynomial terms and exact residual. Do not forge a same-time individual AffineDepletionClockEvidence. Mark the extra residual as numerical group-localization correction, not solely IEEE root-rounding. Charge it against the same unchanged correction limits; do not create an additional looser allowance. Default single-event correction schema stays intact.

A very near but genuinely separated pair may repeatedly fail local correction fractions even when union width passes time gate. Then try the ordered single-event route once intervals separate, or return structured group-localization failure. Do not widen time/correction thresholds or claim the group must succeed on all inputs. This is a useful outcome for the actual4/8 case.

## 4. Atomic mode switch and unchanged numerical acceptance

After all member corrections pass, call with_depleted_cells(raw,tuple(members)) once (existing call at663 is already plural-capable). Evaluate the actual new mixed/dry state once, then continue to a common post-event time. Keep source-content checks before/after terminal, correction and mode change. Any failure rolls back the entire uncommitted group.

Compare successive paths and independent finer approach over complete N/E/T/P/stretch arrays, not only selected cells. Add group time comparison using representative-time difference plus numerical root-rounding/union allowances conservatively; never drop the union width from time uncertainty. Keep original time threshold, two consecutive passes, genuinely distinct finer approach grids, source checks and all existing local/global ledgers. Group membership must agree across compared paths or be reconciled by explicit matching physical cell sets; do not treat a changed member set as convergence.

Store group as ONE event container with member records, one terminal panel, one common-time state and per-member correction/evaporation fields. Don't emit duplicated old DepletionEvents sharing a panel: commit/audit would double count work and costs. Full trajectory and numerical method qualification stay explicit.

## 5. Minimal coordinated file scope

- depletion_integration.py: trailing optional group policy (defaultNone), typed candidate set, safe ordinary tie approach, group affine terminal builder, group-aware matching/time comparison, atomic commit. Existing ordinary/default/single paths unchanged.
- depletion_group_clock.py: reuse existing pure polynomial root grouping; only add typed shared-endpoint/member-residual evidence if needed. No requirement to add a true-RHS derivative framework for this numerical contract.
- depletion_roundoff.py or a small dedicated group-localization module: validate exact polynomial-to-represented residual, per-member budgets and cumulative totals; reuse exact water/atom/mass transfer bookkeeping. Separate schema label prevents false roundoff claim.
- event_record.py: strict versioned group codec, reconstruct full shared panel and every member clock/residual, actual initial and corrected states/modes, group matching and unchanged acceptance gates; panel/count totals once. Preserve legacy audit.
- verification_case/service/checkpoint: explicit opt-in contract only after core tests; serialize full cumulative group history, restore all member modes together and original budgets. No changes to original physicalcase, source envelope or pressure threshold.

## Bounded implementation/actual validation sequence

1. No-EOS whole-integrator tests: equal constant sinks exact simultaneous group; equal initial tangent times but affine acceleration splits order; group correctionfraction failure with global cancellation tempting a false pass; a competing earlier nonmember; vector mechanics and shared local work; native-like callback failure after first member correction; cancellation before/after atomic commit and resume with original cumulative budgets. Independent closed-form solutions for N/E/time, not production clock as oracle. Retain default single-event regression.
2. Add actual4cell initial-tie approach plus terminal test under original wet case and unchanged gates, short event window only, source frozen and bounded external budget based on current measured4cell callback cost. Save failures before audit. If it succeeds, then the longer4cell trajectory is justified as the next measurement; if group fractions/order fail, inspect saved numerical intervals before any new algorithm choice.
3. Only after4cell passes,8cell group test; then longer-time spatial matrix with original norms/time refinement. This moves directly toward required refined runs, without claiming numerical group agreement proves exact physical simultaneity or full spatial convergence.

## Ordering refinement after actual positive advance

New actual4cell evidence: after one accepted2^-14s positive advance, the initial exact tangent-estimate tie splits into a3.371786427888473e-10s gap; candidate order3,2,1,0. This remains below the existing1e-8s time gate. It proves neither actual root order nor that ordinary advance alone solves the run; it does show why treating the time gate as a mandatory minimum physical event separation is unnecessarily restrictive.

The time gate bounds accepted numerical localization differences. It is not inherently a statement that two events closer than that cannot be processed separately. Under a separately versioned numerical ordering policy, isolate the affine-surrogate roots more finely (pure arithmetic, bounded bisections), inspect `group_roots.strict_order_edges`, and permit sequential processing if u_i<l_j is strictly established for those numerical roots, even when their gap is smaller than time_absolute_s. Use the strict interval comparison, not a float nominal-root tie-break. The earlier group-by-gate union can remain diagnostic; it must not automatically force a shared-time switch when strict numerical order exists.

After switching the earlier cell, recompute the actual mixed-mode RHS and localize the next event anew; the original wet polynomial for the later cell is no longer an accepted prediction after the mode change. A common-time comparison interval may contain several such sequential switches. Complete paths must reach the same common time/mode set and pass the SAME original N/E/T/P/stretch/time gates across two consecutive terminal refinements and the independent approach. Each event retains its own correction fraction and panel; shared ledger/cost totals are accumulated once. Ordering instability across refinements is a reason to refine or report unsupported, not silently swap members or accept a partial comparison.

This can avoid finite inventory deletion caused by collapsing distinct roots to one shared time. It does not lower the time gate, strengthen the problem to validated true-RHS roots, or claim the actual4cell case is solved. Required tests include roots closer than the time gate but strictly separated numerical intervals, ordering reversals after a mode switch, nonrepresentable inter-event gaps and full-path refinement disagreement. If no represented positive-time interval or original correction budget permits sequential processing, retain a structured failure or use a separately justified exact-common-root group; do not fabricate an epsilon-time step.
