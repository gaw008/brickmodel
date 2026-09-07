# Independent review: depletion integration and clock accounting

Verdict: APPROVE after the actual terminal-refinement correction and independent final recheck recorded below. Local event refinement is not a full-trajectory error bound. The additional nonlinear probe below demonstrates this distinction quantitatively. Source-gated physical-host run evidence is separate from the manufactured-oracle execution recorded here.

## Resolved HIGH finding after the first frozen review

[HIGH] Repeated identical terminal panels can count as two refinements.
File: `src/sludge_sandbox/depletion_integration.py`, refinement cap initialization.
Issue: when entering tau is much smaller than terminal_window, several successive window/2**level caps all exceed tau. Each proposal then performs the same initial Euler terminal panel and the same continuation; two zero differences can be accepted without actual refinement. Existing 30 passing tests did not exclude this case. The implementing worker identified it while inspecting the real-host preview history; this reviewer confirmed the control flow and requires correction before final approval.
Resolution: initialize the scale from min(terminal_window, entering_tau), then halve. The new tiny-liquid, strongly time-varying-rate regression previously had a root error 9.804864e-8 s despite repeated identical panels (author RED record). Its independent quadratic root gate is 1e-8 s, and it also requires the actual accepted terminal interval to be no more than a quarter of the entering local-root time. Independently read the minimal correction and final regression; all 31 bounded tests passed in 0.37 s, XML `/private/tmp/depletion-integration-refinement-review.xml`. The earlier 30-test result below remains the earlier-source execution. This finding is closed.

## Implementation and resolved review points

Read complete new integrator, original SSPRK2/StepLedger implementation, clock helper diff, interface mode adapter, tests, preregistration and root candidate checker. Ordinary wet panels use the existing SSPRK2 positivity checks. The terminal panel is explicitly first-order Euler with complete current face, reaction and work rates; it is not an RK2 step with an unrecorded inventory reset. Current liquid inventory and the exact sum of represented net liquid rates define the proposed root. A positive phase evaporation diagnostic is required, and non-evaporative loss is not relabeled evaporation.

A directed binary64 absolute endpoint does not have the same scale as tiny terminal liquid inventory. The initial clock failures exposed a remainder outside the old inventory-only ULP rule. The reviewed extension reconstructs the root from original panel inventory and signed rates, validates the nearest downward endpoint and explicit time budget, and verifies each stored liquid term against the same exact endpoint interval. The extra bound is |net liquid rate| times the exact clock gap, separately recorded as numerical clock inventory residual. It is not physical evaporation and is not an arbitrary extra mol tolerance. All original absolute, actual-positive-evaporation-relative, cumulative correction and storage/element/mass limits remain. All terminal face/source/work and evaporation integrals use one exact endpoint difference and one final float conversion; state update and StepLedger share these stored terms.

Each refinement proposal starts from the same committed state/prefix. Wet caps halve; each candidate switches only after reaching the terminal face, then independently evolves to the preselected common time. Two consecutive adjacent-level comparisons must pass. Comparisons include event-map and same-time full inventories/U and decoded T/P with observation error allowances; no inappropriate Richardson division by three is used. Ordinary dry continuation uses the unchanged user adaptive policy and maximum step, avoiding exponential repeated dry work as the terminal cap shrinks. This is an event-local refinement strategy, not uniform-step convergence of the entire trajectory.

Program nodes bound each outer interval and all inner proposals. Near-coincident node/event, unseparated cells or a predicted second event in the common-time horizon exit explicitly. Failed speculative proposals do not modify committed states, modes, events or correction prefix. Commit validates every prefix against original initial amounts/U using exact Fraction sums of shared face/source/work terms and explicit paired/storage corrections. It never resets this audit at a segment boundary. U receives no extra latent-heat source.

Resource semantics were clarified during review: maximum_steps counts accepted trial panels including discarded refinement paths, exposed as accepted_trial_panels; it does not claim to count rejected adaptive trials. Rejections have a separate global limit. The corrected >= guard prevents starting another segment after exhausting that rejection allowance, while original integrate enforces its remaining local allowance. All ordinary runs receive the remaining global wall-time budget and cancellation; terminal/observation boundaries check limits too. These checks cannot interrupt an individual synchronous EOS call. Per-level timing/evaluation/difference/failure diagnostics retain unsuccessful refinement evidence.

## Independently executed checks

First frozen bounded suite: 30 passed in 0.33 s (10 event, 4 clock, 16 prior write-back tests), XML `/private/tmp/depletion-integration-review.xml`. No real-water host or full installed suite was run by this reviewer in parallel with the root's physical experiment. The tests verify constant and linear-time sink roots with post-event heat, program node retention, exact node-event ambiguity rejection, non-evaporative/simultaneous exits, cancellation, resource-limited transactional previews, existing-dry continuation, and exact distinction between physical panels, paired correction and actual storage residual. The clock tests reject altered endpoints, rates and budgets and preserve the previous no-evidence rejection.

Additional independent nonlinear experiment, saved as `depletion_cubic_probe.py/.json`: r(t)=0.001+0.003 t² mol/s, initial liquid=1e-4 mol, so the independent event equation is 0.001t+0.001t³=1e-4. After the event an external 2 W source heats U from 600 J. Both executions complete, but the original ordinary policy gives event error −1.5039045996e-7 s and final U error +3.0078092550e-7 J. These fail this exploratory probe's 1e-7 s / 2e-7 J gates even though its reported local event indicator is only 6.7262345e-10 s. Keeping event policy and gates fixed while tightening ordinary amount relative/absolute tolerances by 100 produces event error −8.2040443e-9 s and U error +1.6408080e-8 J, passing the same exploratory gates. The original failure is retained. The saved rerun includes before/after hashes; it does not replace or loosen the project's constant/linear preregistration.

This is concrete evidence that accepted local event refinement cannot certify earlier ordinary wet integration error. A consumer must retain separate ordinary integration accuracy control and independent whole-trajectory validation. No 'trajectory certified' status is justified by completed alone. This limitation is consistent with the current explicit qualification; it is not represented here as a fixed physical/model error bound.

## Root physical-host checker: read-only audit

The root's `test_depletion_host.py` and `depletion_host_run.py` use the actual source-gated water host with manufactured solid, K and transport. The independent boundary resistance gives G=1/15 W/K. The checker reconstructs total water, H/O and mass from actual inventories and total-U step/prefix exchanges from raw StepLedger fields; it checks saved-state heat against G(Tgas−Tcell) and requires post-event warming to exceed the two inverse-temperature error bounds. Saved-state re-evaluation is correctly not described as reconstruction of every internal RK stage. Paired/storage corrections and totals are additionally checked explicitly. The script records pre/post source and fixture dependency hashes, refuses overwrite, preserves assertion failure results and requires unchanged dependencies for a successful exit.

The first real-host attempt's reported 120 s timeout must remain a failed, non-frozen-run artifact because production changed during that process. The revised real-host experiment is owned/executed by the root; no success is inferred from the light suites. Multi-cell non-simultaneous events, general reaction topology, material-valid sludge kinetics, nucleation/rewetting, full high-temperature wet brick and shrinkage remain outside this component validation.

## First frozen SHA256 bindings (retained history)

- `src/sludge_sandbox/depletion_integration.py`: `437a167cf6d758830a70759d01748f44ae54e371815ed8cba80873d278b27302`
- `src/sludge_sandbox/depletion_roundoff.py`: `be2d41b19c5ae7f9b7f0349f5e9aee79b4c85f1a2ad68777f060e3bbe5e130a8`
- `tests/sandbox/test_depletion_integration.py`: `d8e2fb172fc9ca0a593ad9011f045a1b0620dea0160e0cc8c462295c5fd78414`
- `tests/sandbox/test_depletion_clock.py`: `9389ffdff59f07ee82a47aa1d70184c063a9062afa91f2244004d507f9df9878`
- `tests/sandbox/test_depletion_roundoff.py`: `3ac1bfa367b4689c4a0f6ce9f4628a81d8f313371851cb7b630b5e1b6f3c63a6`
- `docs/sandbox/DEPLETION_INTEGRATION.md`: `abe5f8230ac21b31d147941f4e32fb3c3669481029fa22bebcfad851e5010aa2`
- `docs/sandbox/DEPLETION_ROUNDOFF.md`: `dd12420f8c14c05e9190f0511420092ed9600d7b9e9a8565eab6504e99ea0d8c`
- `tests/sandbox/test_depletion_host.py`: `918595f05bc2f00d87df251f562c09ae4e3fa5b0c8d68e5dcb3027da5d11b72a`
- `docs/sandbox/research/depletion_host_run.py`: `42ad295a581f9967e3dc1cf1b486e20731cc667b2870455d63e3d86bedcf1eb9`
- `docs/sandbox/research/WET_DRY_HOST_PLAN.md`: `aac8fac0f4f29c49d803215e406399a9c4ff3a0c82d862ca428d8fcf378348c7`
- `docs/sandbox/research/depletion_cubic_probe.py`: `aabf32676a5b107bcec415ac2687bb9ce458c8c994b187d0835b46f8da91d7ce`
- `docs/sandbox/research/depletion_cubic_probe.json`: `3e68b41debc4855792ca077bb619e54ea2bae691af89ef911728624a2a6846c7`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE after the recorded correction. Full-trajectory and material validation additionally require their separate evidence.


The root independently reviewed the cubic probe source and checked its event root with 60-digit Decimal bisection: 0.099028852405457313791659772675265306481631824005359751959461 s. The saved brent root differs by about 7.25e-18 s, and the two U-error + 2*time-error residuals are about 5.58e-15 / −8.38e-15 J. This is an independent review of the probe, not a material validation.


## Final correction recheck and bindings

Final 31-test suite adds the actual-refinement regression to the earlier 30 checks. A further unchanged-script nonlinear probe against this corrected integrator is saved as `depletion_cubic_probe_refined.json`, preserving the first JSON. The original ordinary policy still fails its exploratory whole-trajectory gates: event error −1.5035141057e-7 s, U error +3.0070270896e-7 J, while local event indicator is only 6.3764742e-10 s. With the same 100-fold ordinary tolerance tightening, event error −8.1650087e-9 s and U error +1.6329864e-8 J pass. Thus the ordinary-prefix accuracy limitation remains after fixing duplicate terminal proposals; it was not merely an artifact of that defect. This saved rerun took about 0.62 s and had unchanged source hashes. No real-water/full suite was repeated by the reviewer.

- `src/sludge_sandbox/depletion_integration.py`: `042edd30947e85b8164287addfdaf7d9be16cafe90204c9add1789e00cd086a0`
- `src/sludge_sandbox/depletion_roundoff.py`: `be2d41b19c5ae7f9b7f0349f5e9aee79b4c85f1a2ad68777f060e3bbe5e130a8`
- `tests/sandbox/test_depletion_integration.py`: `40ceed15316f8d348523892cc0d5e6e4cc878f98846652bd43ae7e376b55c783`
- `tests/sandbox/test_depletion_clock.py`: `9389ffdff59f07ee82a47aa1d70184c063a9062afa91f2244004d507f9df9878`
- `docs/sandbox/DEPLETION_INTEGRATION.md`: `a81e301eb1ec49d28111d5441497421001804f17517de23e4514f1a3f975fcd1`
- `docs/sandbox/DEPLETION_ROUNDOFF.md`: `dd12420f8c14c05e9190f0511420092ed9600d7b9e9a8565eab6504e99ea0d8c`
- `tests/sandbox/test_depletion_host.py`: `f9bb24a51069fd31c8454cc0d10e00841236ef65746b9ae4f6b794e22f7a11ee`
- `docs/sandbox/research/depletion_host_run.py`: `42ad295a581f9967e3dc1cf1b486e20731cc667b2870455d63e3d86bedcf1eb9`
- `docs/sandbox/research/depletion_cubic_probe_refined.json`: `2de9efa6ab8c3cf82fcd4c6db5c7c0bec5567d2fb7e1a55f8c826c30f0a83dce`


## Legacy baseline: independent read-only review

Read `depletion_legacy_baseline.py` and its saved JSON without rerunning it. The explicit manufactured constant sink has Nl(t)=1e-4−1e-3t and event time 0.1 s; the operator retains the zero-liquid interface exit. The original SSPRK2 implementation additionally validates the second Euler stage, explaining the finite-time approach obstruction. Saved output is consistent: numerical_failure/minimum_time_step, last t=0.09999999999883583 s, liquid=1.1641814894516605e-15 mol, 435 evaluations and 76 rejected trials. Independently recomputed all saved liquid values against the linear formula (maximum difference 1.36e-20 mol) and total water (maximum drift 3.47e-18 mol), and verified both recorded source hashes against current files. This supports a bounded legacy-obstruction demonstration, not the new solver's success. The script writes its fixed destination without a nonoverwrite guard; it is treated as the explicitly requested one-time historical reproducer and was not executed again.

- `docs/sandbox/research/depletion_legacy_baseline.py`: `7f965b5819a0a776a5edff95a733dee01ceaed57a397fbf90cc6d39513a85740`
- `docs/sandbox/research/depletion_legacy_baseline.json`: `900fe2351ed42f004c758410475b796c9ea5d86a650a40aef7fee29e4fb8bc93`


## Actual source-gated host attempt 03: root execution, independent artifact audit

The root executed `depletion-host-attempt-03.json`; this reviewer did not repeat the wet integration. It completed in 86.8175 s with 224 evaluations, 27 accepted trial panels including discarded previews, zero rejected ordinary trials, and 21 accepted states/20 accepted steps. One actual wet-to-dry event occurred at 0.00028422061165952946 s; the trajectory continued to 0.03125 s through the 0.015625 s program node. K remained 1e-6 and the final mode was depleted_no_nucleation. Two genuine refined comparisons passed. The final local time difference was 4.00937e-9 s, with common U difference 1.47556e-8 J; these remain local indicators.

Independently read the complete JSON and verified every pre/post source+fixture hash against current files. Independently reconstructed every saved amount/U prefix from raw shared-face/source/work integrals plus the explicit event correction. Maximum energy prefix residual was 6.81945e-11 J, maximum total-water drift 1.15805e-22 mol, and maximum individual-column prefix residual 6.61744e-23 mol. Exact event projection was 1.5881867761e-22 mol with separate +5.2939559203e-23 mol storage residual. Verified equal/opposite ideal phase increments, actual vapor difference, separate storage discrepancy and final cumulative ledgers. The root checker additionally passed native-water H/O/mass checks, saved-state G(Tgas−Tcell) and actual dry warming beyond the two temperature inverse bounds. Those EOS-dependent checks were reviewed in code and their successful root result is recorded; they were not independently rerun here.

Attempts 01 and 02 remain failed resource-limit artifacts. The final fixture reduced terminal_window from 1/1024 to 1/16384 s, moving more of the safe wet prefix into ordinary integration once; all original result gates, event tolerances, common horizon and 120 s budget stayed fixed. Along with the corrected actual refinement scale, this enabled the bounded run. It does not turn local comparisons into an independent true-event-time certificate; the nonlinear probe limitation and need for further whole-path refinement still apply. This is a genuine coupled single-cell source-gated wet/dry continuation with manufactured solid/kinetics/transport, not only a disabled-K or already-dry demonstration and not a full sludge-brick qualification.

- Final artifact `docs/sandbox/research/depletion-host-attempt-03.json`: `34f49223949df79b51d09f4a5a129040b149702b67b16b98bc91a1d47eb68876`
- Final artifact `docs/sandbox/DEPLETION_INTEGRATION.md`: `2c3ddb29deceb704871164e1f11026d3ace4e61f6a2db37069612c22e852e7c1`
