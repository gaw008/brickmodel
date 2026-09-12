# Bounded Python/numeric review of V2 clock repair

**APPROVE for the separately registered, uniquely supervised V2 experiment.** No unresolved CRITICAL/HIGH issue was found in the reviewed scheduling diff. This is code/admission review, not successful execution of the full B trajectories.

The approval binds integration SHA256 `784d21f65c616bb435ec04ed35a67c6083d362ad9a8115a8a7705a2ebf4848d1`, V2 protocol SHA256 `ec8b69446df1c6b0d48338fb770a3a0c461f2031b3de6e71f72af47cb26ca740`, and formal execution freeze SHA256 `a30f6540e8703de7d2bc4f1b5e1ae8ec70f1b8d146aefd0295eab454591f2202`.

## Numeric and control-flow findings

- The extracted `stage_midpoint(at, endpoint)` is equivalent to the prior stage check: the actual midpoint must be strictly interior and both actual half-step quadrature weights must remain nonzero. Refactoring this guard changes no accepted-stage arithmetic. Nonfinite/underresolved midpoint cases still fail the strict inequalities; no artificial endpoint or positive weight is inserted.
- The new branch only considers an uncommitted candidate strictly between the current accepted time and current target whose remaining tail fails that original guard. The replacement midpoint must be strictly earlier than the candidate, and each prospective side must independently support the original stage guard. Thus the modification cannot push the candidate forward, cross the current knot, or lengthen this trial's actual interval.
- Reanchoring `proposed_clock` to `Fraction(split)` binds future nominal accumulation to the newly selected binary64 endpoint. Neither accepted times/states nor stored ledgers are edited. If the trial is rejected, the pre-existing rejection path reanchors to the unchanged accepted time.
- Full and half RK stages are evaluated only after the replacement is selected. Actual endpoint differences still determine RK weights, the unequal-half error factor, component quadratures and the accepted ledger. No heat, inventory or work is patched afterward; error controls and acceptance guards remain unchanged.
- No valid replacement means the existing scheduling/error path continues. Explicitly adjacent forcing knots are not merged. The strict-earlier and per-side-stage requirements also prevent using forward tail absorption to enlarge a nominal step at large absolute times. The old limited endpoint guard is retained unchanged and is not broadened by this patch.
- Nominal minimum/maximum policy values, error scales, rejection/accepted-step limits and wall-clock checks are unchanged. Adaptivity may subdivide again or reach an existing failure/resource limit; the patch does not guarantee a fixed number of additional panels.

The two added time-dependent flux/work regressions exercise integrated physical weights and inventories against analytic time integrals, rather than merely checking retagged output times. The adjacent-knot regression preserves the numerical-failure case. Root reports 183 source tests and 183 installed tests passed, and a separate reviewer reports four additional bounded tests. This reviewer did not rerun tests because no new issue required a probe; no host/model call or trajectory was run.

## Identity and preregistration admission

Independent hashing verified all 165 source and installed package files against the V2 environment inventory. Comparing the V1/V2 inventories shows only `integration.py` changed; the other 164 entries are identical. The formal V2 freeze's 351 registered files and 353 observed identities all matched through the existing read/hash preflight functions.

The original V1 protocol SHA remains `630c3c6586a63e8ee21a60b215d2e3d1bc4e6318b394bce1f0f2257fdf8e6c74`, and all seven original native01 artifacts previously independently hashed remain byte-identical. Native01 remains the original failed run; its accepted-prefix evidence is not promoted to full completion. The V2 protocol explicitly discloses the core change and a new-version experiment, retaining the original 101 comparison times, reference trajectories, storage/host, physical parameters, all numerical/conservation gates and the same 60/130-second policies.

Detailed identity checks are recorded in `IDENTITY_REVIEW.json`. Final scientific qualification still depends on the unique V2 execution and its saved acceptance evidence; this approval supplies no advance claim of completion or full-cycle/material qualification.
