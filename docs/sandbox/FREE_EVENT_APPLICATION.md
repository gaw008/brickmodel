# Explicit free-slab depletion application and continuation

Status: implemented and tested for the stated numerical/manufactured scope. This is progress under the full Goal, not material qualification or a completed firing cycle.

The new `sludge_sandbox_free_event_case_v1` case schema selects the existing manufactured reacting free-slab model with an explicit `numerics.depletion` record. The original ordinary case schema remains unchanged. Every depletion policy field is required, including the nested-approach choice and roundoff budgets; the application admits `affine_midpoint` explicitly. Actual water molar mass must match the source-backed operator before initial energy construction. No new physical parameters or real-sludge evidence are introduced.

`run_case`, replay and resume dispatch this schema to `integrate_depletion`. Event results retain states, accepted steps, terminal evidence, refinements, modes, corrections, exact cumulative totals and discarded-trial resource costs. `event_record.py` reconstructs typed data without loading saved code. It binds actual WaterPhaseTransfer configuration, chemical constants and backend identity. Final snapshots use the actual depleted operator.

Continuation requires the freshly rebuilt original state, original integration/event policies, case/runtime/source hashes and audited saved history. The core returns the complete cumulative result; the service records a continuation boundary and does not merge the parent twice. `depletion_result.json` preserves the raw full result before audit or diagnostic reconstruction. Failed reconstruction retains evidence and does not upgrade its acceptance status. Construction and snapshots remain outside the core integrate-only wall budget.

The event equation catalog binds the actual depletion integration, affine clock, writeback and record-audit symbols. All seven existing free-slab output roots reach these numerical declarations. The graph does not certify experimental validation. A manufactured callback's declared identity cannot authenticate arbitrary Python callback semantic equivalence.

## Actual validation

- Source tests: 100 passed in 3.31 s; six portable event-service tests passed in 2.49 s.
- Frozen offline noneditable installation: completed successfully. From `/private/tmp`, without PYTHONPATH, 106 targeted tests passed in 5.77 s, with no failures/errors/skips. All 62 actual installed Python modules match source; packaged catalogs/assets also checked by the retained identity script.
- The installed coupled native short-prefix run also completed: two accepted steps, zero depletion events, 19.188 s. It uses the original physical inputs and clock range with the new explicit numerical schema/policy. All seven trace roots resolve with no missing assets and unchanged runtime. The first run completed in 19.339 s but its supervisor passed the wrong evidence root; its sealed incomplete-evidence bundle is retained alongside the corrected run in `native-smoke-evidence.zip`. Neither run validates an actual depletion event.
- The source-backed water constructor tests execute real reference thermodynamics. They establish changed coefficient/configuration bindings, not a coupled trajectory. The first four constructor tests failed because a rigid host has no energy_model_identity attribute; the compatible fallback fixed this, and the failed logs remain.
- Service lifecycle tests use explicitly analytic manufactured callbacks and a substituted builder/snapshot. They exercise actual service/core/record/provenance code, repeated cancellation/resume, replay, changed original initial state, final mode reconstruction, and raw-evidence preservation on audit/diagnostic failure. They are not native-water coupled event runs.
- Record tests include exact-zero events with no correction, reversed cell depletion order, deleted small corrections, altered clocks, malformed numeric diagnostics, cumulative budgets and source/configuration changes. The independent review prompted the exact affine endpoint reconstruction and strict diagnostic checks; prior failed candidates remain archived.
- Default None continuation was compared against saved pre-change code: numerical values, ledgers and resource counters agree, excluding measured wall time. That historical comparison is retained as evidence rather than a permanent duplicate implementation in tests.

Evidence: `research/free-event-application-v1/raw-evidence.zip` and its SHA manifest. Reviews are internal independent code reviews, not external scientific certification.

## Next execution

Run an explicitly registered, resource-bounded native coupled free-slab event case through the installed service, then native replay and before/after-event cancellation/resume. Keep original versus deliberately changed manufactured inventories and every budget visible. No such coupled native application result is claimed by this stage. The UI has not gained a dedicated event-policy editor.

The prior 2/4/8 study still does not support spatial convergence. Raw-sludge material closure, three public mechanism validation groups with held-out data, the full wet-to-fired/cooled coupled cycle, and the remaining Goal section 11 gates remain required.
