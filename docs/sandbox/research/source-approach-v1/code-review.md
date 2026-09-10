# Source approach implementation review

Verdict: APPROVE for the reviewed candidate. No additional concrete defect found. Production was read-only; this review ran only three bounded tests using the existing actual source adapter with its explicitly manufactured liquid fixture.

Reviewed `src/sludge_sandbox/source_approach.py` SHA-256 `5364e5dd471523d6f47e512924c884aff1329938632779cbe051795c3139c007` and `tests/sandbox/test_source_approach.py` SHA-256 `de129eb80d833f6a061f4b349efb1b75006ed83df950e0d4ef1ab9ffec3050d1`, against baseline `ee0ed24` and the surrounding existing trial, root-order, policy codec, endpoint, inverse-pressure and exact-integration interfaces. Both new production/test files were untracked during review; no unrelated tracked changes were present.

The selected first liquid root shares the original ordering/refinement budget, obtains a strictly positive lower bound, and uses the original safe fraction plus horizon/maximum-step caps. Conversion uses the existing downward binary64 control-duration function. All 4N polynomial minima remain strictly positive; sub-minimum durations remain unexecuted. Gas-first, ties, tangency, zero initial, no-root and stopped-seed outcomes do not authorize an approach trial. A failed full prefix can reuse the two original successful first/midpoint captures without inventing an endpoint or replacing its Euler midpoint.

The complete nested event policy uses the existing strict codec and binding; an explicit effective 256 refinement limit does not mutate the original policy. The implementation checks original source/integration bindings and the fresh trial's interval and callback count. It executes the existing source trial once, preserves its original N/U discrepancy test, and retains original endpoint gates plus separate conditional pressure results without granting physical-event/material qualification.

The author's postprocessing fix was reviewed: a completed expensive trial is retained in a chained `SourceApproachAssessmentError`, together with the failing stage and any completed comparison/pressure evidence. There is no fabricated successful result. The detached nested event policy protects against caller mutation during callbacks, and final `result.check()` catches changes in other saved bindings.

## Independent bounded verification

`test_additional_approach.py`, `additional01.log`, `additional01.xml`: **3 passed in 7.97 s**.

- A DomainExit at new callback 6 is recovered by the original reference integrator. The approach remains valid with 20 total callbacks, one rejected reference attempt and the original failed capture retained. This test uses a declared 32-callback test budget; it is not evidence that a 16-callback native run could accommodate that recovery.
- A callback mutating the original seed IntegrationPolicy cannot silently produce a validated approach. Final assessment raises at `result_check`, retaining the completed 11-callback trial, comparison and pressure evidence. The completed trial's own copied policy still validates.
- A cancelled seed with two physically evaluated and bound samples is refused for restart, even though those samples could form a panel. Proposal/result checking makes zero new source calls.

No RED arose in these three probes. Earlier fixture-search failure remains separately retained in the existing probe files. No native EOS, package installation, source-suite rerun or production modification was performed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — reviewed candidate is suitable for the bounded numerical approach stage. Native runner approval and actual scientific evidence remain separate.
