# Independent review of saved-data audit

Scope: read-only review of audit.py, PLAN.md and fixed case.json; no EOS, no inspection or polling of the running native result. Initial review concerns the script version before author closeout fixes. No production audit function is used as an oracle; standard-library Fraction arithmetic is appropriate for represented floating-point ledger sums.

Correct mathematical checks in the initial script: face contributions use left minus right; phase correction removes the represented liquid remainder and adds the actual rounded vapor increment; signed and cumulative absolute storage roundoff are kept distinct. Each accepted endpoint is paired with steps[k] and states[k+1]; event terminal panels must match exactly once. Independent reconstruction of terminal raw N/E/stretch prevents treating a missing small correction as zero. Depleted modes remain zero. Event cell order is unrestricted while times increase, so events in cells 1 then 0 remain admissible. Represented and exact stretch quadrature residuals, including cumulative absolute roundoff, are compared to the original stretch budget.

Initial actionable gaps sent directly to author: independent refinement record needs same root start/common time/level; source/runtime/case-initial/catalog bindings and exact manifest membership need explicit checks; completed resource counters/budgets and phase-cost totals need auditing. If both result.integration and depletion_result.json exist they must agree. Saved local ULP/clock correction allowances require independent reconstruction rather than trusting stored bounds.

Global E + pe*(V−Vinitial) minus boundary/body input and constraint cancellation are useful independent metrics. They must not acquire a new retrospective nonlinear time-truncation gate absent from the preregistered plan. For this slab V=A0*(H/N)*t^2*sum(n_i). These metrics do not prove spatial/time convergence or source-material validity. The original component and N/E ledger tolerances remain the acceptance gates.

Disposition: pending author closeout. No native acceptance conclusion has been reviewed or inferred while its process is live.

## Closeout formula review

Reviewed intermediate closeout SHA6d1032dca1d039d0f1362b5f174994bcbea8b3e91e3b9bc301be7222e111ce9e and subsequent runtime-binding delta. The author added same-root independent comparison, source runtime/catalog bindings, initial inventory/mechanics, resource totals, local ULP and affine clock reconstruction. These resolve the initial substantive coverage gaps. The raw correction formulas and adjacent downward-root checks agree with the represented arithmetic contract for this registered affine-midpoint case. Null correction requires exactly zero reconstructed liquid.

The parent has now explicitly registered global targets before result inspection: final absolute E+peΔV−boundary−body and cumulative absolute cross-cell constraint sum each <=2e-8 J. This is an addendum, not a consequence of per-cell ledger tolerances. The pressure-work check is at the final endpoint; all-prefix claims refer to N/E/component/mechanical ledgers. A later failure must remain a failure.

Three final integrity adjustments requested: exclude only the root manifest from membership, bind archived case bytes to the preregistered input, and require attempted_steps>=len(accepted steps). Final disposition follows after their narrow reread. AST parsing passed; imports are exclusively standard-library fractions/pathlib/hashlib/json/math/sys. No script execution or native result inspection occurred in this review.

## Final disposition

Final reviewed audit.py SHA256: f9fbc4a6d64f97bb486e2746d05c03cd75510391767d404993a79e142c45a702. All three final integrity checks are present. The parent also requested global pressure-work calculation at every accepted endpoint: this version now accumulates matching boundary/body terms inside each step, computes the correct initial-to-current volume/energy difference, retains its maximum and worst state index, and applies the registered 2e-8 J target to that maximum. This supersedes the earlier final-endpoint-only limitation. Cumulative absolute cross-cell constraint residual is monotone, so its final value bounds all prefixes.

APPROVE for the bounded saved-data audit purpose; no remaining blocking formula/index/integrity finding in the reviewed changes. This is approval of the verifier code, not of the native experiment. Parent/author reported that the native attempt has terminated unsuccessfully; this reviewer has not opened its results or run the audit. The script must retain acceptance=failed unless completion, fixed horizon, actual event, and every applicable gate pass. Saved thermodynamic observations/refinement differences are not independently re-evaluated physical truth, and no convergence/material/full-cycle claim follows.
