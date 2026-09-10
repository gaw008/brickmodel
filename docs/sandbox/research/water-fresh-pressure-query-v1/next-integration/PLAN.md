# Minimal ordinary-stage, then event-controller pressure integration

Read-only design against the applied stage/controller/provider and fresh_query/propose_boxes.py. No running result files were read; no EOS, installation or source edits. A single-query success is not presumed. First acceptance target is one actual ordinary full-versus-two-half trial with unchanged scientific policy; full event-path admission comes afterward.

## 1. Exact connection points and fixed semantics

`src/sludge_sandbox/mass_wet_exact_stage.py:86` currently accepts one cell state and inverse, so it cannot authenticate the full two-cell request or access the already-evaluated equilibrium liquid snapshot. Add keyword-only context after the existing positional `fixture` argument: `states=None, cell_rate=None, pressure_session=None, query_context=None`. Leave the current dry and explicit constant-fixture calculation byte-for-byte unchanged. Reject simultaneous fixture and native pressure selection at the trial entry to avoid implicit precedence. With neither option, ordinary wet still refuses `pressure_temperature_envelope_unavailable`.

Only a positive-liquid cell with explicit session takes the new branch. Require `states[cell] == state`, `cell_rate.inverse is inverse` (or exact captured value binding if restoration is later supported), and actual `WetCellRate.equilibrium.liquid.state`. Construct a fresh `BoundLiquidPressureRequest.capture(pair, states, cell_rate, cell)`. Do not call water again. Delegate to the concrete source-bound session, retain its result before checking status, and return only its proved Fraction radius. A missing/unresolved proof refuses this trial; no fallback to the old fixed-T error, an analytic fixture, a cached successful point, or a smaller epsilon.

`try_step_doubling`, around current line 336, already holds both required contexts:

- full: `whole.endpoint_state` and `whole.endpoint_sample.rates.cells[i]`;
- fine: `half2.endpoint_state` and `half2.endpoint_sample.rates.cells[i]`.

Pass these actual values into the two calls. Record exact time, full/fine role, cell, sample source binding, original state/inverse digest and query digest. The two-cell all-wet comparison makes four pressure queries, each independently proved. It does not require any additional host/native evaluation beyond the existing nine stage evaluations. Mathematical work is additional and separately charged.

The existing comparisons remain exactly: kg, mol, U, `|Ta−Tb|+epsA+epsB`, `|Pa−Pb|+radiusA+radiusB`, exact endpoint-time difference, each against its ORIGINAL threshold. No adjustment to min/max step, safety factor, error envelope, epsilon or pressure gate is part of this change. A tight existing policy may correctly refuse the trial.

## 2. One explicit operation-local session, not a per-query budget reset

Add a small new module, proposed `mass_wet_pressure_session.py`, rather than adding mutable accounting to the frozen provider. It owns a synchronous invocation's cumulative mathematical counters and immutable output snapshots. It has no global state, disk cache, native provider substitution or cross-run reuse.

Frozen policy fields should include the concrete provider/branch model policy, original seed policy (bounded iterations and box widths), maximum cumulative seed evaluations, maximum cumulative proof operations, per-primitive box cap, original mathematical wall allowance, and precision. Proof operations and seed evaluations are distinct; do not call either count native evaluations or full residual evaluation counts. The provider's bottom-level residual count remains unknown. Seed/box widths are numerical search settings, never replacements for science gates.

`PressureSession.query(pair, states, cell_rate, cell, context)` must:

1. Validate original session policy/source bytes, current actual request and remaining budgets before any seed math.
2. Append an immutable started query attempt identifying role/time/refinement/cell/current mode host.
3. Generate proposals under the SAME outer guard and cumulative seed budget, preserving actual attempted/completed seed records even on failure.
4. Call the concrete provider with `maximum_proof_operations = remaining_operations`, explicit per-primitive cap and a wall allowance no larger than remaining session wall AND remaining caller wall.
5. On return, charge actual provider attempted/completed operations exactly once before testing result status. Retain all primitive records/internal counters and failure bytes. Recheck original source, policy and caller wall/cancel.
6. Only return the Fraction radius for a fresh matching request with `proved_conditional_query`; otherwise raise an explicit stage cancellation/resource/domain/unresolved error AFTER preserving evidence.

The session's own immutable mathematical deadline begins once at public stage entry or once at controller entry. Controller supplies its existing outer `guard` and remaining-wall function. Standalone stage supplies its local guard/deadline. Convert residual wall to float conservatively downward; if nonpositive, refuse without invoking a primitive. A child stage may shorten local wall but must never recreate the session, original mathematical deadline, counters or budget.

Provider currently returns unresolved with a textual reason. Before production session wiring, minimally add a structured failure category/stage to provider evidence, preserving the original reason and costs. Do not classify cancellation/resource errors by substring matching. Operation-boundary cancellation is cooperative; coex/coupled calls are not hard-preemptible. Tube/native-query already receive remaining wall. Any overrun still rejects after recording completed work; do not promise a real-time interrupt guarantee.

## 3. Numerical seed extraction

`fresh_query/propose_boxes.py` is the current bounded, untrusted proposal implementation. Extract its mathematics unchanged into a formal module/API returning an immutable `SeedAttempt` plus optional `QueryBoxes`, with actual counts and all Newton iterates. The current callback `save(dict)` should become immutable event recording; keep the original helper and failed history as evidence.

Keep current source/hash checks and exact full-query `parameters()` call. The ancillary is only an initial guess; the bounded point-Newton convergence is only a proposal condition. Neither licenses a pressure radius. The existing fresh proof still verifies the full actual inverse-T coexistence box, mechanical rectangle, expanded whole tube and native query box. If a proposal fails, keep the failed query; do not shrink the physical query domain or reuse a previous proof. Any future proposal widening/search must have its own preregistered numerical limits and consume the same budgets.

The helper's current 12 iterations, precision 60, stopping residual 1e−30, log widths 4e−6/1e−3 and density expansion 0.2 must be explicit source-bound seed-policy values if retained. They are not new scientific acceptance thresholds. A completed seed evaluation that fails during matrix inversion or final guard remains charged and stored.

## 4. Failure and export boundary for the first ordinary step

An accepted candidate remains speculative; pressure proof work does not publish a state. Existing `steps`, samples, predictors, endpoint attempts and ledgers survive a pressure failure after all nine host callbacks. Append immutable native-pressure evidence and cumulative math costs even when the final candidate is None. A second/third/fourth query failure must keep earlier completed query evidence and the entire original stage work.

Avoid quietly adding fields to the old dataclasses: `mass_wet_exact_record.py` currently serializes ALL dataclass fields and strictly checks their sets, so a trailing field breaks old bytes despite `omit_when_none` metadata. For the first opt-in stage, use an explicit `NativePressureMixedTrialResult` subclass (base fields unchanged plus original native policy, proof trace and counters), returning the old exact class for default/fixture calls. Its type is deliberately unknown to the old codec and must be refused until a versioned codec branch is implemented. Do not export only its base fields or silently drop proof metadata. A later v2 mixed record must bind native policy/source, initial mathematical budgets and each proof to its actual comparison context; no resume admission is implied.

## 5. Controller extension comes only after ordinary-step acceptance

`mass_wet_exact_controller.py:126`: add explicit optional native pressure configuration. Create ONE session at controller entry. Include original native/seed policies and math budgets in the immutable original digest alongside original initial/time/stage/roundoff/controller policy. Existing host-evaluation and panel counters keep their exact meanings; append separate session statistics to the opt-in result.

At line 215, pass the SAME session through every ordinary trial, reject/retry, terminal refinement and independent approach. Never charge the same query again when copying a trial's result into its path; session charges at execution, path records reference already-issued immutable attempt IDs. Failed speculative branches and independent validation keep their spent costs.

At `differences` around line 242, pass complete `a`/`b` states plus actual `ca`/`cb` from the supplied observations. The post-transition event frame already has `fa.operator`, `fa.state` and `fa.observation`; these are the right contexts. A depleted cell with exact zero liquid uses the unchanged dry formula and incurs zero pressure proof operations. The remaining wet cell uses its new current mode host and a fresh request; an old pre-transition certificate is not inherited merely because storage/material coefficients are unchanged. Original branch policy may be reused only after checking the same concrete source/domain model; request and host identity are always new.

Keep event sequence/mode alignment, each event's six gates including both root-width errors, common-endpoint six gates, two consecutive passes, genuinely independent halved approach controls and distinct pre-first grids. Keep full original-initial kg/mol/U accounting and original local/cumulative correction budgets. No pressure proof can authorize root selection, writeback or mode change. Global publication still occurs once after ALL required packet comparisons and final source/resource checks. A late pressure failure publishes none of that speculative packet.

For opt-in controller output, use a new explicit result subtype/wrapper retaining the complete base history PLUS session policy/evidence/costs. Old exact mixed codec must fail closed until its new schema explicitly supports this type. There is no service/resume route in this integration increment. Native qualification must remain conditional ordinary-water branch plus original U/Cp/volume assumptions; do not relabel it the manufactured constant-liquid fixture or full material admission.

## 6. Minimal validation order

1. Pure orchestration/default regression: exact dry and constant-fixture values, existing nine host callback pattern and base result bytes unchanged; generic wet without explicit policy still refuses. Full/fine requests bind the correct four real samples/states, never extra native observations.
2. Pure negative controls: wrong cell/rate/inverse/time/source/mode; altered original epsilon/domain; source mutation during seed/proof; budget exhaustion after prior completed work; cancellation and wall overrun; changed query proposals; query 2–4 failure retains previous evidence and no candidate. Verify zero proofs for exact dry cells. Structured failure statuses must match their actual category.
3. ONE fresh actual ordinary full/fine stage, using a fixed before-run case, scientific policy and separately explicit mathematical budgets. Save all nine host observations and seed/proof traces before assertions. Require all original six gates and independent ledger checks; if a gate fails, preserve failure and diagnose rather than choose a looser threshold. This establishes only this local step's conditional numerical acceptance.
4. Only then wire/validate controller scenarios: wet/wet→dry/wet→dry/dry, pressure evidence at every event/common comparison, two passes and independent controls, cumulative resources across all branches, original source/mode transitions, and a late-comparison failure with atomic no-commit. Start with bounded pure tests; a full native event run requires separate source freeze and measured cost plan.

No new all-phase/global-density/global-T-domain theorem is proposed as a prerequisite. Each requested box is either conditionally proved in the explicit ordinary-liquid model or refused. The unresolved original material and U/Cp/native error assumptions remain visible in every result.
