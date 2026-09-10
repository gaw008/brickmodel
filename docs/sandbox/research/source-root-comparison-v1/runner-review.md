# Independent prepared native runner review

Verdict: APPROVE for one execution after the parent confirms matching final source/installed tests. This review did not run native EOS.

Reviewed run_native.py SHA-256: 5b8c0e650e051a0ab4eb36e919eaaef18b271f51bb499add23f5e534c8434f28.
Reviewed PREREGISTRATION.md SHA-256: 3e4470498e959232c9d746791a41c4abca7fb3bd79502f8189ba0e5bc595b327.

The diff from the previously reviewed source-approach runner adds the fresh shifted seed, exact root clock comparison, common endpoint selection and two fresh common trials. Initial state, actual constructor paths, full integration/event/roundoff parameters, source helper hashes and source envelopes remain unchanged. Total source cap is 81 = 1 probe + 5*16; 38 is an estimate for the expected successful path, not a forced result or observed measurement. Per-trial wall cap remains 180 s, outer SIGALRM request 210 s. The registration correctly says native calls may observe the signal only on returning to Python. Whole-study runtime includes checks and serialization and is not mislabeled a shared integration-policy budget.

The previously reviewed constructor wrapper records started before each call and completed/one reference-anchor check only after its successful return; four completed constructors are asserted after construction. These are provider and reference-anchor counts, not internal EOS update counts. The runner persists attempted source input before each actual callback, returned evaluation or actual exception after it, and returned trials before subsequent assertions. New SourceRootStudyError handling retains every returned SourcePrefixTrial, including a failed second common path. Common success is numerical execution/comparison completion; clock, four endpoint gates and conditional pressure remain separate, and event_admitted/material_qualified remain false.

The serializers omit live adapter/storage objects while preserving saved trial/clock/pressure evidence. The unchanged helper hashes were checked against current files. A new passive test compiled/imported the final runner and both helpers with the HEOS constructor forbidden, instantiated all three full policy objects directly from the runner AST, and compared their exact fields to the existing policies. It passed as part of the 3-test independent batch in 7.83 s. New failure-path production tests use manufactured source observations only; the native run was not emulated as scientific evidence.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — final reviewed runner bytes may be executed once under the unchanged preregistered conditions.
