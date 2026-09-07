# Candidate TP Newton backtracking implementation

Candidate only. Production source, approved manifest and installed package are untouched. No EOS import, tests or native execution performed; candidate AST parsing passed. Parent owns independent control tests and subsequent source qualification/installation decisions. Baseline repository commit 9ab4b659c539dcc790e4286c241a92016f9de670.

## Bounded algorithm

Only state_tp density-iteration body changes. Evaluate the initial density once. Preserve at most eight accepted outer density states (seed plus at most seven updates). Each update checks the original full Newton logarithmic step is finite and abs(step)<0.1 BEFORE damping. Try exactly the ordered fractions 1, 1/2, 1/4, 1/8, 1/16, 1/32 until a candidate meets the unchanged dynamic residual gate or strictly decreases abs(residual)/gate. Every trial originates from the last accepted density; rejected trials cannot become the base. Thus at most 1+7*6=43 density evaluations, excluding unchanged constructor/saturation/seed/snapshot work.

Every trial retains finite positive density, stable density branch and finite positive slope/residual guards. Native phase is explicitly checked for each evaluated trial. Invalid native, branch, phase, slope or source results remain fatal; they never continue backtracking. Six unsuccessful valid trials raise heos_tp_backtracking_failed. Eight accepted states without residual convergence raise existing heos_tp_not_converged. Existing transaction, source/configuration checks, phase cleanup, final snapshot and final density branch are unchanged.

The actual accepted trial is already the native state and its derivative/residual are retained for the next outer iteration. There is no duplicate native evaluation. Healthy full-step paths retain original density arithmetic, native values and density-evaluation count. The original dynamic gate is min(1e-4,rho*1e-7), never widened. At a floating zero gate only an actual zero residual passes (as before); normalized merit is represented as zero for zero residual and infinity otherwise. No tolerance, target pressure, temperature bracket, physical parameter, EOS selection or thermodynamic value averaging changes.

## Actual evaluation diagnostics

_tp_iterations keeps the existing iteration/rho/native_p/target_p/h/u/residual_pa/slope fields, adding fraction, accepted, gate_pa and normalized_residual. Initial fraction is None and iteration 0; each trial iteration is the target accepted-state index, so rejected trials share that index with later trials. Every completed native evaluation is appended before slope/phase validation; invalid records retain accepted=False and may lack merit fields. Native update exceptions propagate before a complete observation exists, preserving prior completed records and existing structured failure behavior. Only validated selected trials have accepted=True. Final snapshot does not reuse a rejected native state.

All records represent actual native evaluations; no interpolated residual is accepted. Strict decrease alone never returns a property solution. This temporary candidate file is not directly source-qualified by the existing approved manifest, and must not be loaded as a production provider until parent separately updates identity evidence following review. A one-point diagnostic passing shorter steps does not establish coupled wet-model completion or real-sludge material validity.

## Frozen hashes

- Original kernel SHA256: `88bbbdd91fbe12d351faf6415883c177fec2fec4a7e51d77d98d864b49d51d93`
- Candidate SHA256: `e2df0b8b7c7190ee9b40da5d9cbf4ec7be05801620b20fa6dbdaa260b457ebae`

## Attempt logging review correction

Preserved the previous e2df0b8b7c7190ee9b40da5d9cbf4ec7be05801620b20fa6dbdaa260b457ebae candidate bytes as candidate-before-attempt-log.py. This supersedes the earlier diagnostic paragraph: immediately after density/branch guards and before native update, append an attempted evaluation with rho, target_p, iteration, fraction, accepted=False and status=started. Successful native/derivative/phase validation populates the existing actual values and merit and sets status=complete. Any exception during that attempted native evaluation or its validity checks sets status=failed, error_type and reason, then re-raises the exact same exception. The existing outer exception translation and phase cleanup remain unchanged. A failed native call may legitimately lack fields that were never obtained; it is now identifiable by its exact attempted density/fraction. Density guards still fail before an actual native attempt and therefore do not create a fictional native evaluation record.

No extra EOS calls, acceptance changes or source/manifest edits. AST parsed only, no tests/EOS executed. Updated candidate SHA256: `c1ecb59c702382c78891f4fcf6b6ac5eb8c68cc57869b1e261ec8a3a4a796b12`.
