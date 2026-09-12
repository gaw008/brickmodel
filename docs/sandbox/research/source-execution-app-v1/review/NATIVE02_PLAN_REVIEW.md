# Native02 plan review after the diagnosed missing dependency

Verdict: **APPROVE this new numbered attempt at the exact files below.** This is a read-only protocol/harness review and byte comparison. It is not execution or acceptance of native02. No production code, original failure, runtime identity record or physics setting was changed by this reviewer; no EOS construction or integration was performed.

## Compared files

- `NATIVE_PLAN_V2.md`: `ef1d555cfa590059d5d17748b30c43d165b67514671fd5c1f36f3b30ce0ced07`
- `native_driver02.py`: `596a6d70e2cc5ee9f8a4c406897b7f9b6137455d34f8684adbbaef3b2f1b3490`
- `run_supervised_native02.py`: `25d4d01a2d2b056649b4991052ac9a024a8c1bb75d6bf9446d0a6e7ab6d4dd91`
- Inherited original `NATIVE_PLAN.md`: `3d13f41fef084fed946318688524c1223cc13731f1e609ac4691b34564762a93`

`NATIVE02_PLAN_CHECKS.json` records these and the original driver/wrapper, freeze, passive dependency validation and current original-failure file digests. Both new scripts parse successfully with the standard-library AST parser; no script was executed.

The driver differs from native01 by exactly one output-directory substitution: `native01` → `native02`. An exact string comparison after that single substitution passed. All original physical requests, exact endpoint arithmetic, step sizes, pause count, outcome/qualification gates, prefix comparisons, cumulative count thresholds, elapsed limits and repeated-restore refusal assertions are unchanged.

The wrapper selects the new driver and new output directory, includes the V2 protocol, and additionally fingerprints the installed `iapws`/`CoolProp` dependency files and passive dependency check. At this reviewer's request, root also included the inherited original `NATIVE_PLAN.md` in the frozen input list; the final wrapper hash above includes that correction. No unresolved finding remains.

## Failure and dependency evidence checked

The saved native01 job reports worker PID 9269, return code 1, `child_reaped=true`, no hard kill, and `source_execution_operation_failed:required_fixed_water_sources_unavailable`. Its original failure counts are one HEOS constructor start, zero kernel/constructor returns, and zero RHS, initial-energy or wet calls. The original study/event files retain `ModuleNotFoundError` / missing `iapws`; the native01 runtime record has `iapws:null`, while NumPy 2.5.2, SciPy 1.18.1 and CoolProp 8.0.0 are recorded. The original outer supervisor reports failed, return code 1, reaped leader and unchanged recorded inputs. There is no original pause/resume/acceptance output.

The installed dependency correction is explicitly recorded as iapws 1.5.5. The supplied local wheel bytes independently hash to `97810dca5155cce1e2ec964dd254fc9e4858fbb1c9967da6c4f817adaf3a818e`. The saved passive validation reports verification of declared source and installed-wheel bytes without native construction. This reviewer did not rerun that validation or import the EOS; the dependency validation is attributed to its saved report.

All **169** current source package files and their installed counterparts independently match `install/SOURCE_FREEZE.json`; mismatches are empty. Installing iapws naturally changes the environment's new runtime identity. The old native01 identity remains unedited, and native02 must create a fresh parent under the corrected environment; it does not resume or relabel the failed old parent.

At final review, both `native02` and `supervised-native02` are absent, including no dangling symlink at those names. The driver creates its new directory exclusively and writes outputs using exclusive creation; the wrapper also uses the existing exclusive attempt directory. Original native01/supervised-native01 file digests were captured without modifying them.

## Unchanged acceptance and scope

Driver total 510 s; each application job at most 180 s with 5 s grace and remaining-time clamping; outer supervisor 570 s with 10 s cleanup grace. Original source/ordinary limits, 97 RHS/16 wet caps and all recorded numerical policies remain unchanged. This is one diagnosed new attempt, with no automatic retry or continuous fourth physics branch.

The required journey is fresh parent → one-new-step pause → completion from that packet. Exact end is the fresh candidate-1 time plus 3/64 s, with initial/maximum step 1/64 s. Acceptance still requires three workers reaped with zero exit, three accepted steps, 22 observations, cumulative 54 RHS / 12 HEOS / 3 initial-energy / 8 wet counts, the original first step/eight observations and event prefix retained, and consumed-packet refusal with the exact reason before any fourth worker launches. All material/training/full-cycle flags remain false.

The outer supervisor's containment scope remains its original process group, not independently escaped worker sessions. The driver's SIGTERM path still delegates cleanup to the application supervisor owning the live worker handle. No stronger containment or hard real-time guarantee is asserted.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — unchanged physical/numerical acceptance, corrected dependency, fresh output names and retained original failure. Actual native02 results remain to be audited separately.
