# Longer physical-time spatial study: staged original-case plan

Design only. No source edits, case execution or EOS. Original15.258789µs2/4/8 spatial study remains FAIL/unresolved; this plan cannot change its recorded gates or result. New endpoint pressure strategy has actually completed the original2-cell0.32ms window in67.79s,30accepted steps/2events/592evaluations with source and full-prefix checks. That validates the short event window under its explicit numerical/uncertainty policy, not long-time spatial resolution.

## Physical target and the first practical stage

Same original wet initial state,300/301K parent jump, initial inventories,2cm half thickness and reference area0.01m² (=100cm²), unchanged. Preserve exact source case values rather than this prose's units. k=1W/(mK), waterD=1e-8m²/s, reaction/mechanics/pressure/water sources all unchanged.

Initial thermal scale alpha≈k/(10J/K per .0001m³)=1e-5m²/s. At8cells dx=.0025m, alpha*t/dx² reaches~1 at t=.625s; sqrt(alpha*t)=dx then, still only one cell across a characteristic layer, not demonstrated asymptotic resolution. A later sequence t=.625s then2.5s would give characteristic widths2.5/5mm, but evolving calorics, free geometry and reaction make these design indicators, not solution predictions. Mass diffusion still needs~625s for this grid scale; no claim of species spatial resolution from thermal resolution.

The next runnable step is **one2-cell pilot to elapsed .01s**, an explicit new case ending at absolute .51s. Thermal length~.316mm remains unresolved at8cells; its purpose is measuring post-depletion adaptive cost and checking domain survival on the route to .625s, not serving as the spatial validation endpoint. Do not substitute its completion for a space-convergence result.

## Exact pilot case changes

Start from the actual endpoint-strategy paired-event case that passed67.79s (bind its saved case and implementation SHA; do not silently use an older repository default lacking strategy). Deep-copy, new case_id suffix '-longer-pilot-001s-v1'. Change only:

- numerics.end_s:0.51 (start_s stays0.5).
- numerics.integration.maximum_step_s:0.001953125 (=2^-9s), allowing the post-event smooth branch to grow rather than forcing the old6.1e-5s cap forever.

Retain initial_step_s=2^-14, nested_approach.maximum_step_s=2^-14, all event windows/common horizon/safe fraction, all six gates, independent pressure comparison declaration, all roundoff budgets, relative/absolute integration tolerances/scales, inverse/source envelopes, minimum step, rejection and512trial budgets. Keep explicit pressure strategy. No dry-start shortcut, removed water, unequal child perturbation, smoothed temperature, changed diffusivity or prescribed strain.

Retain integration maximum_wall_seconds=800 cumulative and840s external supervision. Forty seconds is not justified: the measured original event work alone took67.79s. A first120s cooperative observation/cancel checkpoint is reasonable as a bounded *partial outcome*, using already reviewed cancellation/service lifecycle; actual accepted progress and remaining budget determine whether continuation is useful. An external840s watchdog remains responsible for eventual kill/reap. Cancellation must preserve accepted prefix, all event/correction history and cumulative wall/evaluation/trial budgets. Resume through the existing service API, original end=.51 and original policy unchanged; never reset the800s allowance or reconstruct from a dry replacement initial state. Only one native process at a time.

Before launching, preregister either uninterrupted pilot or explicit120s cancellation lifecycle, rather than choose after seeing a favorable result. Prefer uninterrupted pilot if root only needs cost; existing lifecycle validation need not be repeated gratuitously. Report build/diagnostics separately from integrate time. Save complete failure before audit; use existing reviewed prefix audit, no invented new pass threshold.

## Domain gate before extension

Actual free-case parser only requires start<end; prescribed motion knot coverage does not apply. Current dynamic storage error bounds use stretch and temperature domains, not an independent time range; do not invent permission from an unused prescribed-time field. Check actual built errors/source ranges from the selected case before launch. Current inverse/reaction coverage is295–310K, stretches[.5,2], maxabsolute logarithmic rate2/s; retain all restrictions. A longer requested horizon does not certify staying within them.

Initial evaporation scales~.27ms correctly warn of early depletion; actual two events now demonstrated, so the pilot must traverse them normally. Initial latent-only total drop~.004K is not a full temperature bound; reaction, pressure-volume work, heat exchange and composition-dependent recovery energy continue after depletion. Initial stretch rates suggest seconds-scale domain changes but cannot guarantee survival to.625s or2.5s. On actual T/strain/rate/source exit, retain structured prefix and stop; no widening295–310 or manufacturing missing properties to complete a plot.

## Transition to an actual spatial study

If pilot completes or yields enough verified dry accepted intervals, measure actual step sizes/rejections, nativecall counts and phase-specific time. Forecast reaching .625s from the observed post-event regime with a stated safety margin, not by multiplying67.79s by elapsed-time ratio. If adaptive time tolerance prevents step growth or domain exit occurs early, the larger horizon is not yet feasible and must not be scheduled as a blind full matrix.

Only then preregister a2-cell elapsed .625s feasibility case, with explicit maximum time cap justified by the pilot and a second half-cap control. Increasing resource cap beyond800s requires a new recorded budget; it is not a continuation reset. This .625s target addresses a plausible thermal resolution scale; it does not guarantee convergence.

For4/8cells, same parent subdivision/extensive scaling as the original study, and original parent-space norms: sum N/E, reference-volume-average T with saved inverse bounds, normal stretches mapped by reference weights, common tangent once. Preserve registered10×available temporal+point bound resolution screen and require decreasing D24→D48 before even discussing apparent order. Refined-grid local extensive tolerances/scales scale2/cells; do not loosen parent aggregate gates. Each mesh needs genuinely distinct coarse/fine accepted time grids, sufficient temporal separation, unchanged original conservation/roundoff audits, and all failed outcomes.

## Critical4/8cell event blocker, before a full matrix

Current candidate selection explicitly rejects two estimated depletion times within time_absolute_s ('simultaneous_events_not_separated'). Refined children share parent T/N/phase coefficients and may be identical away from the central face; same-parent liquid exhaustion can therefore be simultaneous or insufficiently separated. Weak heat/gas coupling may split near-interface children, but it is not legitimate to rely on roundoff breaking symmetry. Initial N/rate ratios can be checked algebraically from saved/refreshed callbacks before allocating a long run; this is only a screening observation, not an event-time proof.

Do not perturb inventories/temperatures, change event time gate, arbitrarily pick a child order, or silently drop sibling events. If actual multi-child separation is unresolved,4/8 long wet runs need a separately designed coupled simultaneous-event certificate and ledger/correction/continuation audit before admission. Alternatively a scientifically explicit proof that all relevant events are separated under original gates is required. Starting fine grids after the2cell wet phase would change the discretized initial-value problem and is not the same full original-case spatial study.

## Deliverable boundaries

First deliverable: exactly one new2cell pilot with original wet start and frozen sources, complete prefix evidence, measured long-branch resource profile and any domain/cancellation outcome. No new full matrix until this and the multi-child event issue are resolved. Original short-time spatial FAIL stays visible. No raw-sludge, full firing/cooling, long-time species resolution or spatial convergence claim follows from this pilot.
