# Frozen workflow implementation review

Approved: no unresolved blocking finding in the reviewed implementation. This is code/control-flow approval for one registered attempt after Root completes final installed identity and regression checks; it is not a claim that the physical workflow has passed.

Reviewed the actual new workflow worker, service and ordinary-session lifecycle changes, scope bootstrap/deadline changes, profile/manifest selection, three affected test files, frozen case, request, supervisor launcher and NATIVE_PLAN. The 159 files in Root's FREEZE.json match current bytes; exact review and freeze hashes are in REVIEW_FINAL.json.

The parent runs under one lease and closes it before encoding its result. Reconstruction has no lease. Each ordinary advance independently admits and closes a lease; a paused checkpoint stores data without managed authority. Actual returned execution is retained when close/audit/publication fails, and secondary exceptions do not replace the original operation failure. Paused audit/cost/policy bindings reject mutation. Admission and close time count toward the ordinary resource checks, including the original 180 s segment limit.

The worker charges the parent once plus each session's incremental observed counters; it does not count the paused session twice. Failed admission recovers the saved partial constructor counters or explicitly reports a lower bound if the diagnostic was not durable. Sticky user cancellation and the private budget-stop signal preserve separate terminal classifications. Exact-cap cooperative cancellation remains conservative and is explicitly documented; no cap was raised.

The new case changes only profile and the one execution-manifest asset row. All native constants, source assets, physical inputs, uncertainty bounds, scientific tolerances and resource settings equal the original V2 case. Both native kernels and old manifests are unchanged. The prior V2 execution files are preserved as historical bytes, not passed off as the current implementation. Shared whole-workflow deadline, per-operation lease deadline, isolation gate, and one-shot supervision are present. The new runtime does not authorize replayed live object identities or archived source-session resume.

Independent validation: 34 standard-library source/manifest/case checks passed. Five supplemental pure worker control seams passed in 0.24 s: cancellation after both branches, deadline exhaustion after both branches, final acceptance-file publication failure, deadline-cleanup primary/secondary failure, and a normal control. They exercise real worker publication/classification/counter logic with explicitly substituted numerical returns, and therefore supply no EOS or numerical-method evidence. All failures preserve 76 RHS / 12 constructor test counters, preserve the original exception, and leave no ACCEPTANCE.json. No EOS, model construction, installation or old scientific suite was run by this reviewer.

The registered native attempt must still establish the original parent event gate and both actual three-step branches, complete state/observation/ledger equality, resolved nonzero thermal motion, original budgets, and closed verified audits. Material, full-cycle, training and archived-resume qualifications remain false.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — frozen code and one registered attempt, subject to the final installed checks above.
