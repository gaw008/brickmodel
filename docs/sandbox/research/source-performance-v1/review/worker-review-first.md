# Dedicated worker first implementation review

Reviewed source SHA `8381c1cb94ed3b57f90db396a3b34c00ad693c7aeb446d2c2bd174abe29ec16f`. Production files were not modified. Evidence is in `worker-first-red/RESULT.json`; that directory preserves the exact reviewed source/test. The independent probe uses explicit control-flow seams, bypassing the imported-module gate only within the test; it performs no native/model construction and does not establish real process isolation or numerical validity.

[HIGH] Completed terminal record precedes mandatory profile publication

File: `src/sludge_sandbox/source_managed_worker.py`, `_execute_request` success publication and final profile block.

Issue: a real `OSError` injected only at `PROFILE.txt` publication raises from the final block after `RESULT.json` with `status='completed'` has already been committed. No `FAILURE.json` exists. The process outcome and its only terminal record conflict, and the declared profiled experiment is incomplete.

Fix: finish required profile artifacts before committing the successful terminal result, and handle profile-publication failure through the same truthful failure-record path. Retain actual evaluation evidence and counts; do not retry the physical query.

[HIGH] Failure publication depends on a second unprotected audit extraction

File: `src/sludge_sandbox/source_managed_worker.py`, `_execute_request` exception handler.

Issue: the failure dictionary evaluates `_worker_audit(admission)` before `_publish` is invoked. In the control probe, an original evaluation ValueError plus a secondary audit RuntimeError leaves no terminal failure JSON even though ordinary output publication works. The original exception object survives with a note, but its persisted main failure record and count summary do not.

Fix: assemble the minimal main failure independently; obtain managed audit in its own protected step and persist any secondary audit error alongside the primary type/message/counts. Closing/audit bookkeeping must not prevent the primary failure record.

[MEDIUM] Noncanonical rational time is accepted then normalized

File: `src/sludge_sandbox/source_managed_worker.py`, `_load_request` exact-time guard.

Issue: `{numerator: 2, denominator: 128}` is accepted, then rebuilt as `1/64`. The closed request contract was intended to preserve canonical exact-time representation. A positivity check alone does not enforce it.

Fix: require gcd(numerator, denominator) == 1, including zero time represented as 0/1. Preserve the existing exact integer and digit-budget checks.

The normal control completes with four constructor starts/kernel returns/wrapper returns and one RHS start/return; original U and the selected dry index are preserved by the direct state/pack/mode sequence. Existing 20 author tests cover data admission and rejection of imported in-process entry; they do not exercise these execution/publication paths.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 2 | warn |
| MEDIUM | 1 | info |
| LOW | 0 | pass |

Verdict: WARNING — resolve the two failure-persistence defects and strict-time gap before the planned native measurement. The managed-scope implementation and manifest integration are still pending separate review.
