# Managed full-workflow lifecycle review

Read-only baseline: 9544ec9. This is an implementation checklist for the new parent study followed by two ordinary-segment branches; no new EOS, model, old failure run or test suite was executed. Actual diffs still require review.

## Parent study

Reuse `run_source_case` and its original `_execute`; do not clone the source event driver. Build once under the existing recorder, then admit that actual graph. Each individual ExactSourceColumn RHS opens and closes the existing numerical scope; the worker admission may cover the bounded study execution, but must close before the function returns or persists a completed source record/summary. Initial-U calculations and direct wet-support queries outside ExactSourceColumn remain ordinary per-call water operations. Do not claim that the RHS scope audit accounts for those operations.

Place lease closure and audit collection before `result.update(status='completed',...)` and before the `finally` block constructs canonical study metadata. If `_execute` already produced transition/candidate records and closure fails, preserve those originals in roots/failure evidence, mark execution failed, and leave numerical acceptance flags false. Do not permit a completed parent with an active lease merely because its physics returned.

The existing code classifies ordinary Exceptions and KeyboardInterrupt separately. New lifecycle cleanup needs a BaseException-safe `finally` so cancellation, SystemExit or an observer failure cannot strand `_worker`. Cleanup must not mask a primary exception. Audit extraction and failure publication must be separate protected operations; the previous single-RHS worker's audit/publication REDs apply here too. Preserve a minimal failure/count record even if the richer managed audit cannot serialize.

## Ordinary branches and pause

Keep each `open_source_trajectory` a real reconstruction from the newly completed same-version parent. It performs four actual provider constructor/anchor chains before returning a session, with no initial-U recomputation. Those costs belong to the branch and workflow even if admission fails before the caller receives a session. Such partial construction is retained in `source_trajectory_admission_failed` and earlier events; do not report zero work just because the session variable is None.

Admit a fresh lease for each `advance` invocation after the original source/runtime/checkpoint/cost preflight. Close it before any ordinary completed/paused result is published or returned. Neither the session nor checkpoint may own an active lease across a pause, and `_active` and `_worker` must both be absent at the pause boundary. Continuing the same live session reuses its actual model and checkpoint; it must not silently reconstruct four more providers. The independent continuous and pause/continue branches each reconstruct once.

Important late-failure trap: `with lease: execution = integrate_exact_checkpointed(...)` assigns a real returned execution before the context's exit runs. If exit/close/audit then raises, the current `advance` exception handler only records an exception and counts. It would lose that returned numerical prefix and observations unless the new code explicitly retains `execution`. Initialize it before the protected block; on a late lifecycle failure persist the actual returned execution/observations, clear any resumable checkpoint, set the session closed, and preserve the primary/secondary failure chain. Do not manufacture a successful SourceTrajectoryResult to carry failure evidence.

Successful pause returns a clean committed checkpoint, one closed admission audit, and actual accumulated counts. A pause publication failure remains a closed failed session; an unpersisted checkpoint is not a resume grant. Keep the original `_audit_balance_fields` whole-path N/U audit from the parent wet state through terminal writeback, dry reference and the new ordinary prefix. Managed execution changes source-check placement only; it cannot reset the original physical conservation budget or adopt a per-branch zero origin.

## Time and count budgets

Use one workflow monotonic origin for the total 510 s, including imports/admission as declared, source copying/reading, provider reconstruction, physics, passive validation, publications and pauses. Keep each ordinary segment's original 180 s accounting and maximum four steps/four rejections. The continuous 3-step request and pause-after-1 then continuation retain the same original minimum step, tolerances and endpoint.

For source callback and wet-support counts, a session recorder already includes the parent's historical counts. The aggregate is `parent_once + sum(branch_counts - parent_counts)`, with each branch's latest cumulative snapshot counted once. Do not sum the two full parent-inclusive session counts. Do not add the paused snapshot and then add its entire resumed snapshot again. Keep starts/returns distinct and use attempted starts for admission caps; a failed physical call still consumed work. Four-parent plus four-per-reconstruction constructor counts must likewise remain explicit, including partial failures.

Apply the common original 97 RHS / 16 wet-request / 510 s limit before each relevant actual request. On aggregate exhaustion retain `resource_limit` and its exact limit reason. Passing `True` through the current generic cancel callback marks `_Recorder` as `cancelled`, so a shared resource guard must not mislabel budget exhaustion as a user cancellation. A genuine user cancellation remains distinct.

Compute ordinary `admission_elapsed_seconds = now - session.begin - prior_checkpoint_elapsed` after any newly added lease admission/checking work, not before it. Otherwise the new setup lies between the old debit snapshot and the integrator's own start timer. Scope/close/audit/publication time also remains charged to the real outer clock; any result/checkpoint elapsed field must retain its declared scope instead of being rewritten with an incompatible total. A late deadline failure cannot yield a paused/completed accepted session even if its last RHS returned.

The same global budget check must work while a branch is being created and while an advance is running, not only after a new session/result has been assigned to the workflow list. The supervisor remains a separate process bound; a cooperative numerical deadline is not native preemption. Do not expand the original limits to obtain the planned result.

## Isolated workflow worker

Extend the private scope bootstrap by an exact installed worker module name/path, not an arbitrary callback or generic context flag. Keep the old single-RHS entry and default per-call API behavior. The new manifest/profile must bind the changed execution files explicitly; do not make old same-version trajectory checks accept new identities. Run the parent and both branches within the same final installed implementation so their new source-run runtime identities really match.

All cancel/on_commit/pause/observer/publication callbacks remain outside the active numerical RHS scope. The process and closed collaborator graph remain an operational assumption; they do not attest against hostile transient raw CoolProp setters. No callable, live admission, model object or arbitrary module path should come from the serialized request.

Do not start ordinary branches unless the newly saved parent is completed and its original numerical event gate is true. Preserve a false parent gate as its actual result, with no attempted ordinary branch; do not grant material/full-cycle or archived-resume qualification. Likewise retain the continuous branch if the paused branch later fails; workflow failure must not erase completed work or imply the two paths matched.

## Minimal meaningful acceptance cases

1. Normal parent closes admission and saves an owned audit before returning/publishing; default nonmanaged behavior stays unchanged.
2. Parent execution failure plus close/audit failure preserves original exception, original candidates/captures and partial counts, with no leaked admission or true numerical acceptance flag.
3. Ordinary integration returns a prefix, then close/audit fails: that exact returned execution is retained, the checkpoint is unavailable, and the session is closed.
4. Pause after one committed step has no active scope/lease; resume opens a new lease on the same actual model, without reconstructing providers or resetting N/U/resource budgets.
5. Shared counts at the cap block the next attempted request across branch boundaries; paused cumulative counts are not double-counted; failures/cancellation preserve starts versus returns.
6. Wall spent in new admission, a pause, close or publication remains accounted for; resource exhaustion is not mislabeled cancellation or completion.
7. Parent-not-accepted, partially failed reconstruction, and late second-branch failure each preserve earlier completed evidence and avoid starting unauthorized later work.
8. Actual continuous 3-step and pause1+continue results match in all numerical state/observation/ledger fields under the same policy; nonzero conduction/U/T evidence remains required, separately from managed execution metadata.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: design risks and acceptance guidance only. No implementation or new native execution approved by this report.
