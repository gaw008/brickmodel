# Independent review: separated multicell depletion

Verdict: APPROVE for the bounded sequential-event extension. The source-gated two-cell host attempt has separate execution evidence; no outcome is inferred from the numerical oracles.

Reviewed the complete stage-check/horizon-restart diff, surrounding event transaction/resource/ledger logic, final five new tests, preregistration and documentation. The public integrator and physical operators remain unchanged. The post-first-event continuation evaluates the full host and checks remaining wet-cell predictions at actual ordinary RK evaluations, not just the beginning of the common-time preview. These predictions are scheduling indicators from numerical stage states, not measured physical event roots.

If a predicted second event enters the preview horizon, the new common time is strictly earlier and separated from both the first event and the predicted second crossing by the declared time threshold. All old coarse/fine paths and successes are discarded; level zero restarts at that common time. Each reduction records old/new times and cost. Restart count is explicitly bounded per event by maximum_refinements and all paths also share wall-time, accepted-panel and rejection budgets. Thus repeated same-state replan cannot form an unbounded loop; an unresolved separation can fail honestly.

The checked ordinary operator calls observe once and returns that evaluation's Rates. Internal horizon/resource requests are caught as a controlled IntegrationError so the original integrator returns its already performed evaluations/panels/rejections before the request is rethrown. Global observation counting is not duplicated in this branch. Discarded preview modes and corrections never enter the committed prefix. The previously attempted last-valid-state fallback is absent from the final implementation. After accepting the first separated event, the actual outer trajectory retains the other cell's wet mode, processes its event and advances both dry cells to the end.

## Independently executed numerical evidence

Final suite: 36 passed in 2.09 s (5 new multicell plus 31 prior event/clock/write-back tests), XML `/private/tmp/depletion-multicell-review.xml`. No root physical-host or complete installed suite was run concurrently by this reviewer.

Independently checked the reference algebra: cell 0 liquid decreases at 0.0012 mol/s from 4.8e-6 mol, hence its first event is 0.004 s. While both are wet, cell 1 gains 0.0002 mol/s from the shared face; its initial 7.2e-6 plus the accumulated 0.8e-6 leaves a second event at 0.008 s under its 0.001 mol/s evaporation. Shared gas flow and the continued X→Y source give the per-column piecewise formulas in the tests. The shared 5 W energy face gives U0=600−5t+2 max(t−0.004,0), U1=700+8t. Tests check all saved states against those formulas, not just global conservation, and independently reconstruct each per-cell Fraction prefix with both terminal corrections.

For the accelerating case, cell 1 has 1.2e-6 mol at 0.004 s; the subsequent sink integral is 0.0001 Δt+(100/3) Δt³, giving the second root at Δt=0.003 s, or absolute 0.007 s. The declared tighter ordinary integration policy for that cubic sink is retained, and the 1e-8 s event gate is unchanged. This case specifically exposes why a beginning-only prediction is insufficient. Tests also require horizon changes to restart comparisons, charge discarded work, preserve shared-layout arithmetic and leave committed modes/prefix untouched on resource failure.

Initial rejection of a second event, the accelerating minimum-step failure and the unsuccessful fallback are author-recorded development history retained in separate artifacts. This reviewer independently inspected and executed the final correction, without presenting those earlier author invocations as reviewer executions.

## Read-only root coupled-host audit

Reviewed `test_depletion_coupled_host.py`, `coupled_depletion_run.py` and COUPLED_DEPLETION_PLAN before a long run. The fixture uses actual water providers with explicitly manufactured solid caloric/reaction/transport parameters. Its column vectors correctly map carbon, hydrogen, oxygen, inert tracer and water for (char,H2O vapor,H2O liquid,fixture,O2,feed,CO2). External boundary fluxes, not closed-system invariance, govern total water/elements/mass. The exact pair/storage numerical projections are separated from physical face/source terms before the independent system balance; full per-cell amount/U prefixes and both events remain required.

The zero bare tracer diffusivity does not imply zero corrected mixture flux. The recorded initial failed assumption was corrected in the audit rather than by changing the diffusion model: tracer face flux and its actual declared 0.028 kg/mol mass enter the open-system balances. The runner preserves failures, refuses output overwrite and checks complete source/test/runner hashes before and after execution.

The audit checks nonzero cumulative liquid mol flow and complete energy-face ledgers; these alone do not separately identify integrated liquid advective enthalpy inside the total face energy. That scope distinction was sent to the root before execution. Initial nonzero liquid enthalpy flux may be checked as instantaneous evidence, but it must not be called an independently separated cumulative h integral unless such stage evidence is actually saved.

## Limits

This is demonstrated separated two-event scheduling with full shared-face conservation and continued reactions. It is not a simultaneous/chattering/arbitrary-stiff-event solver, proof of event ordering under all constitutive laws, whole-trajectory error certificate, real sludge reaction qualification or independent EOS validation. All prior ordinary-prefix accuracy limitations remain. Physical coupled-host results, when available, must be appended as root execution plus independent artifact audit rather than invented from these 36 tests.

## SHA256 bindings

- `src/sludge_sandbox/depletion_integration.py`: `74682b80794798ff67e2496c91b3e4391473d981c51daa5a7b217730cea25148`
- `tests/sandbox/test_depletion_multicell.py`: `1f393a69b5e4a60cdaf68cc20b8ba6c535577641369ac8397ab81eab4d9b6343`
- `docs/sandbox/DEPLETION_MULTICELL.md`: `3b82a45d2629c5c936a01c83ef39152fcdb73d7f4b4acf24221e56496af50220`
- `tests/sandbox/test_depletion_coupled_host.py`: `5fd2262db1dbd5c55c5d5ef61598beeaa5101f38dfc04073646e435033d4a61b`
- `docs/sandbox/research/coupled_depletion_run.py`: `25692c1c309e04d689ec44f15d917d9b4cab8ad20c20cfe61ae0ab0e4ab3d647`
- `docs/sandbox/research/COUPLED_DEPLETION_PLAN.md`: `34159f7eb167526bcf2bc1fcbfffb57a58b93bdaf2391ed524462b5c9512e330`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE for the explicit separated-event numerical scope; physical-run outcomes remain separately evidenced.


## Root coupled attempt 01: preserved failure

Read the saved `coupled-depletion-attempt-01.json` without rerunning the physical experiment. It reports resource_limit/wall_time_limit after 360.9708 s, 314 evaluations, 35 accepted trial panels and 3 rejected trials, with unchanged run dependencies. Ten committed states remain, last time 0.00023739636134257572 s, and no event was globally committed. The shared-horizon reduction was actually requested and recorded. Subsequent comparisons reduced the local time difference to 9.1941e-9 s, but U difference was still 1.5432e-5 J, exceeding the original 1e-6 J event gate; the next refinement timed out. Thus the physical coupled case has not passed, notwithstanding the separately passing manufactured two-event tests.

A proposed smaller terminal window (1/1048576 s) is a numerical setting intended to compute more safe ordinary wet prefix once and reduce terminal Euler transport/enthalpy error. It does not authorize weakening physical liquid flow, the U gate, or claiming earlier ordinary-prefix error is certified. Actual resource/accuracy outcome remains to be measured in a separately named run.

- Failure artifact `docs/sandbox/research/coupled-depletion-attempt-01.json`: `aee4bf4581679ad480ae2ad11f08ea34c417a06016199da276eb743d48c11b65`


## Explicit inventory-step policy and continuous dry integration

Reviewed the final minimal follow-up source diff and new 14 safe-fraction / 5 dry-continuation tests. safe_inventory_fraction defaults to 0.25, rejects boolean/nonfinite/nonpositive values and values >=0.5, and is recorded in the result. It replaces the same three ordinary tau/4 caps consistently. Terminal root reconstruction, refinement gates, physical rates, clock/storage audits and original stage positivity/error rejection are unchanged. For a constant sink the original SSPRK2 second Euler stage requires h<=tau/2; the strict sub-half policy provides margin in that frozen-rate model only. It is not a proof of positivity for arbitrary time-varying rates, which still require actual stage checks.

When and only when every interface is explicitly depleted_no_nucleation, the outer driver now calls the original normal integrator through the current program boundary tb rather than restarting it at each maximum-step interval. This retains its adaptive step history and avoids repeated initial-step rejections. It still obeys the same maximum_step, error policy, domain checks, complete ledger, cancellation and remaining global resource budgets. If any wet interface remains, even with currently zero/no-negative liquid rate, the prior bounded progression remains. No program node is crossed in one normal segment and no rate is clipped.

Independent final verification: **55 passed in 7.36 s**, XML `/private/tmp/depletion-safe-dry-review.xml`; source afff823dd48ca2bc4eeb650bf2e7ab4bf12a70d60f45a32ce6bc35091d0b3355. The new tests verify default versus explicit .25 equivalence, .4 two-cell shared-face/reaction formulas, accelerating/strong sinks, invalid policy values and resource exit. Dry heating/cooling use an independent exact exponential solution with k=.01 and unchanged 1e-4 J final gate; a linear change in forcing at 300 s has its own analytic solution. Every dry energy prefix and node boundary is checked. A wet initially-zero-rate case later evaporates and produces a real event, preventing accidental classification by current rate. This is not a claim of bitwise equivalence with the prior driver: preserving dry adaptive history intentionally changes its time grid.

The reported earlier memory-only timing comparisons are performance observations, not a guarantee that source-gated EOS workloads improve. The next physical two-cell attempt explicitly selects .4 and terminal_window=1/1048576 s with a recorded 600 s resource cap, based on the saved 360 s failure. This is an acknowledged resource-budget change for a separately named attempt; no physical coefficient or error/result gate was weakened. Actual outcome remains separately measured. The worker also reports a preexisting decimal-node wet-grid exploratory failure; this patch does not claim to fix all representable-time/node combinations.

Final verdict for this follow-up: APPROVE within these explicit numerical-policy and dry-continuation contracts. No unresolved HIGH finding in the reviewed diff.

- Final policy binding `src/sludge_sandbox/depletion_integration.py`: `afff823dd48ca2bc4eeb650bf2e7ab4bf12a70d60f45a32ce6bc35091d0b3355`
- Final policy binding `tests/sandbox/test_depletion_safe_fraction.py`: `d110d983f847feaf816a19a0f81f7d11143c06d4fc7c4f8ade1f2f8693e75d5c`
- Final policy binding `tests/sandbox/test_depletion_dry_continuity.py`: `207232f63d8c71b6a5ceb29d7ee67da0522109b02e34ca3d7f059111cda1f8ce`
- Final policy binding `tests/sandbox/test_depletion_coupled_host.py`: `fb29fdd1b37ca5b8939f186eab93da0d727740d494fde823454d63196f94efed`
- Final policy binding `docs/sandbox/research/COUPLED_DEPLETION_PLAN.md`: `4e8468d85cbb981cedc04cba1424b9dd0227abd4b1e77b18a1815e50a196b4bf`

Final documentation read after completion: descriptions accurately distinguish isolated safe-fraction default equivalence from the intentionally changed dry time grid, preserve the unsuccessful .001 reproduction and canonical .01 regression, and do not claim to fix the recorded decimal wet-node limitation.

- Final documentation `docs/sandbox/DEPLETION_SAFE_FRACTION.md`: `7531c0d7a411c7ca68757fabe0d9d2b48558be0d29731e7bd2a060e85d21aa89`
- Final documentation `docs/sandbox/DEPLETION_INTEGRATION.md`: `6fc05ad8ffff280c898d6a1cb0525cd95ad84c1cbdff053e7a02a8a328931fa3`
