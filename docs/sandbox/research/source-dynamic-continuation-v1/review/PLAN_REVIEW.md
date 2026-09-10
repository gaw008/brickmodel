The proposed slice is coherent: preserve the original stationary case, register a new manufactured N3 temperature/conductivity case, and give its newly started ordinary segment explicit initial/maximum step sizes. This is not restoration of the old study's adaptive controller. Baseline read: 92e5b85; no production changes or model/EOS execution by this reviewer.

The current config already represents two `(left, right)` conductivity rows, three initial temperatures, the original closed outer boundaries and the three mixed interface modes. Use `(0.5, 0.7)` on each intended internal face explicitly, not as a replacement for other grid fields. These are existing manufactured-test values, not measured material conductivity. Record a new config digest; retain the old case unchanged and all existing source/domain/uncertainty classifications.

`SourceOrdinaryStepSizes(1/64, 1/64, rationale)` is a numerical choice for the new segment. Before any new constructor/physical call, validate explicit finite positive values, exact accepted types (no bool/NaN/inf/string), nonempty rationale, minimum_step <= initial <= maximum. Snapshot and bind the original reference policy, the selected sizes/rationale and the resulting complete ordinary policy. Only initial/maximum may differ from the original policy; all tolerance/scales, minimum step and 4 steps / 4 rejections / 180 seconds remain identical. Default None must retain old behavior and output scope. An ordinary checkpoint resumes only its already selected policy; a caller cannot select again, swap/remove the choice, mutate the original reference policy, or replace checkpoint state to obtain a fresh budget.

The target should be exact `candidate1.reference.times_s[-1] + Fraction(3, 64)`, with the new segment beginning at that candidate's already admitted final state. 1/64 is an exactly represented binary64 duration. Step limits and endpoint clipping remain the original integrator's responsibility: three accepted steps are an expectation for this case, not permission to force h, skip a rejected trial, enlarge budgets or grant an event if a second wet cell depletes. Existing wet depletion/dry nucleation/domain exits retain their real attempted history and stop; no new event controller is implied.

For the independent continuous and pause/continue paths, compare complete numerical states/times/ledgers, controller/rejection history and actual callback observations. Exclude only measured wall time and live object identities whose scope differs explicitly. The paths must use fresh actual operators from the same accepted parent/config rather than copying or relabelling physical captures. The paused path must not redo its initial domain probe on continuation. Compare old whole-chain balances and their new ordinary rows from the original wet initial state; new segment-local balances alone are insufficient.

Budget both alternatives explicitly. Expected no-rejection cost is parent 32 RHS + continuous (1+7*3) + paused/continued (1+7*3) = 76 actual RHS; provider constructions are 4 parent + 4 + 4 = 12, while initial U remains the original 3. Each session correctly carries parent+its own segment for branch accounting. A combined runner must also enforce one aggregate actual 97-RHS and 510-second experiment ceiling, including reads/reconstructions/rejected paths, rather than independently allowing both sessions to spend another 65 calls. Do not double count the shared parent's 32 calls as physically executed twice. Timing and live constructor counts must come from actual observer events, not predicted counts or a selected successful branch.

Meaningful dynamic evidence requires actual nonzero shared-face conduction/integrated heat and at least one changed accepted U and inverse T (preferably distinguishable under saved numerical error boxes), not merely a larger end time. Check the actual signed energy transfers and closed-boundary global balance. Do not assert that a cold cell must warm or every middle cell must warm: nonuniform thermal resistance and active local phase change can change temperature signs. Initial temperatures and positive conductivities alone do not prove the executed segment is nonstationary.

Minimum regression/refusal coverage:

1. Default step_sizes=None preserves the original policy and stationary regression; the old original case digest is unchanged.
2. Invalid sizes/types/rationale and initial<minimum or initial>maximum fail before constructor/RHS and retain correct preflight behavior.
3. Only the two permitted step fields change. Attempts to alter tolerance, minimum, max steps/rejections/wall or original parent policy are rejected.
4. Mutating/removing/swapping sizes, rationale, policy, target or checkpoint after pause is rejected before new RHS; original ledger and resource debt cannot reset.
5. End/step timing stays exact Fraction at a large origin and at any supported real program breakpoint; clipped tails do not relax minimum step.
6. Continuous vs pause-after-one+continue retains identical full numerical callback/history and original cumulative N/U gates; at least one full-chain cumulative budget trap remains sensitive.
7. Physical second-depletion/out-of-domain, real returned failure, cancel and budget exhaustion keep all actual work and grant no false continuation/event.
8. Combined two-branch count/wall exhaustion stops before a new physical attempt and preserves both branches plus the one parent.
9. New checkpoint codec must refuse malformed/resealed controller or observation data, preserve exact times/arrays/order and original arithmetic admission; its existence alone does not grant SourceTrajectorySession cross-process resume or historical live-id authority.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | design only |
| HIGH | 0 | required guards above |
| MEDIUM | 0 | no execution yet |
| LOW | 0 | read-only review |

Verdict: the design can proceed with the explicit budget/identity boundaries above. This is plan feedback, not approval of unimplemented code or an unexecuted dynamic case.
