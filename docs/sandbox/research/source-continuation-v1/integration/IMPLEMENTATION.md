# Implemented exact checkpoint core

Baseline: 9d7beffeeb7c1c18f357f2b3ab5ce690bca35181. Author owns only exact_integration.py, new exact_integration_checkpoint.py, and test_exact_integration_checkpoint.py. Final bytes/command/XML are in FINAL_FREEZE.json. No EOS, native execution, installation or commit performed by this worker.

## Implemented API

`sludge_sandbox.exact_integration.integrate_exact_checkpointed` retains original initial/operator/start_s/end_s/policy/breakpoints_s/cancel arguments and adds continuation, pause_after_commit(checkpoint)->bool, on_commit(checkpoint), admission_elapsed_seconds:float=0.0.

It returns `ExactCheckpointRun(result, checkpoint, observations, committed_checkpoint, failure)`. `result` remains exactly the old ExactIntegrationResult type/field layout. `checkpoint` is non-None only for an interior clean pause with reason accepted_boundary_pause_requested. `committed_checkpoint` retains the most recent committed evidence even on later failures; it is not a general permission to resume. Original observer or unexpected callback exception is retained in failure. Returned known Rates (including invalid numerical values on a failed attempt) and all actual input/time/ordinal/attempt/role records remain in observations. An arbitrary non-Rates returned object is identified by its returned_type and ensuing validation failure; this API does not serialize arbitrary Python objects.

`ExactIntegrationCheckpoint.result` exposes the complete ordinary-segment accepted history and actual original counters. `elapsed_seconds` is a property of that result. on_commit sees a running result at a true atomic commit after the original next-h update. A clean returned pause has the final cancelled result and elapsed time after observer/pause work. Full completion is not relabelled as a pause at the final endpoint. Midtrial immediate cancellation yields checkpoint=None, with its actual uncommitted callback tail and attempted/evaluation counts retained.

The old integrate_exact delegates to one internal arithmetic loop. The opt-in tracker adds only snapshot/restore, observations and commit callbacks. No solver loop, SSPRK2 estimator, tolerance, minimum-tail rule, source rate calculation or physical admission rule was copied into a separate controller.

## Restore and cost boundary

The checkpoint retains the original initial/full exact interval/all breakpoints/full policy, next exact h, original knot position, component schema, complete original cumulative N/U and component bounds, represented/exact/absolute-roundoff stretch accumulators, accepted history, and all actual initial/rejected/accepted callback observations.

Admission first checks strict types/content and rebuilds saved Rates' constructor-derived component fields/order. It then calls the same arithmetic loop against the saved callbacks, matching each requested state/time and re-raising original DomainExit/_Reject. The replay must reproduce the exact controller, observations, costs, balances and accepted history. It performs no physical callback/EOS and does not inflate actual source evaluation counts. Its actual CPU/wall time is charged along with new execution to the original budget.

Elapsed time uses an outward conversion of the exact sum of original spent binary64 time, explicit external admission/reconstruction time, and new active monotonic duration. Historical wall measurements are retained execution evidence, not independently proved by arithmetic replay. This is an in-memory API, not a persistent/archived-record decoder or provider-restoration authority. The Root-owned source session must independently bind its fresh callable, source parameters, original context and resource scope.

After commit observers and pause decisions, the original cancellation/wall guard is checked. Guard callback errors are isolated from the RK rejection catch: a postcommit DomainExit or _Reject cannot turn an already accepted step into a rejected trial. The accepted prefix and original exception remain recorded.

## Actual evidence and review

- Before extraction: 17 tests passed 4.94 s, legacy-before.xml/log; original source snapshot exact_integration.before.py retained.
- Final author scope: 61 passed 5.85 s, XML 5.843 s, final04.xml/log. This is 44 new tests plus 17 original tests, including the existing 12 complete callback/result legacy golden records.
- Actual new tests cover nonlinear rejection/controller adaptation, repeated boundary pauses, exact large-origin clocks and breakpoints, inherited resource limits, no extra initial/replay physics callbacks, zero dry inventory, all RK cancellation boundaries, returned failure capture, original observer exceptions, type/derived-field tampering, and original cumulative N/U/stretch/component-budget traps. Each cumulative trap proves that a naive new segment would pass while proper continuation fails at the original cumulative gate.
- Initial missing API RED remains initial-red.xml/log.
- Actual hardening REDs retained: final-guards-red (2 callback wall failures + forged Rates component residual), postcommit-cancel-red (2 cancellation windows), mapping-order-red (constructor component order). Their pre-fix source snapshots are retained.
- Independent review identified and preserved the postcommit DomainExit guard defect in ../review/postcommit-domain-cancel-red/. The bounded repair was then independently verified.
- Reviewer reports final 9 independent checks passed in 0.03385 s, 0 EOS; original failure is retained, accepted=1/attempted=1/rejected=0 on the repaired guard case. Three final hashes match and no finding remains open. Review report: ../review/CHECKPOINT_REVIEW_FINAL.md and .json.

Production files remain frozen. The Root-owned source integration/service, installation and one registered actual native exercise are subsequent work, not claimed as completed by this core report.
