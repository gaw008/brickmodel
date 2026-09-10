# Source wet shared pressure implementation evidence

## Scope

Added source_wet_shared_pressure.py and test_source_wet_shared_pressure.py. The earlier paired_pressure extraction is separately frozen in KERNEL_FREEZE.json; no subsequent changes were made to those three files. No production fields, physical thresholds, EOS tolerance, temperature error, volume uncertainty or prior qualification were changed. No native EOS, installation or commit was performed by this implementation agent.

The new opt-in declaration is tied to the actual same SourceWetStorage and actual same ManufacturedFixedFluidVolume objects, with process-local identities plus original full content binding. An equal-content independent storage/volume is rejected. Each endpoint is an actual checked SourceInversePressure. Existing wet guards and caloric/source/closure validations are reused. Original wet_fluid_pressure_bounds global/extra/total are recomputed exactly; surplus records retain their old single-end validity but are refused by this new decomposition contract.

## Explicit collection and passive evidence

The declared common pressure support is the outward binary64 hull of the two original reported-temperature pressure boxes, within the original domain intersection. At most four unique water/T/P/liquid requests are executed; same water and exact same T/P are required for deduplication. No new point or retry is made after fixing this support. Cancellation is checked before each actual unique request. Each started request is recorded before the call; each returned WaterState is retained before post-validation. SourceWetPairCollectionError retains stage, endpoints, shared declaration, fixed support, all attempts, returned records and the chained cause. An unresolved support requires no call.

Every observation retains actual input, water object identity, reference/implementation/assets binding, full WaterState, exact mass/density ratio, native binary64 ratio and signed projection, and the original declared epsilon. This epsilon's whole-support interpretation is an explicit applicability condition of the new conditional certificate. Four observations do not establish it or certify liquid stability.

The passive enclose entry and pair.check use these saved records only. They validate complete evidence contents and reconstruct all derived quantities without any EOS call. These research pair records are not a complete SourcePrefixTrial/resume codec or an automatically reattached live model.

## Mathematical scope

Root existence signs at both support ends are required for every original common V. On the entire support, exact liquid interval subtraction and signed gas numerator division give the residual interval; exact residual/compliance gives the report-temperature root difference. The whole-support normal binary64 contract includes density, liquid multiplication/division, gas fsum/products/division and final closure summation. Its GL/GG/GS volume margin, saved closure residual, actual fluid pressure error and total projection remain separate and retained.

Temperature continuation starts from the larger hull-covering radius; each temperature contribution uses max(original L,new L). The original full independent bound is shown separately, while selected bound equals the new joint bound only. Failed root existence, domain continuation or normal ranges return unresolved with bound None. Source, event and material flags remain false.

## Actual checks

- Pre-implementation missing-module RED: wet-api-red.xml/log.
- First actual inverse/collection/control: wet-first.xml/log, 2 tests.
- Initial boundary suite: wet-boundary01.xml/log, 23 tests.
- Final scoped suite: wet-boundary02.xml/log, 30 passed, XML 1.854 s (pytest display 1.86 s).
- AST parse for both new files and scoped git diff --check passed; no installed static-analysis tools were available in the existing runtime.
- Fixed fixture rationale predates implementation in FIXTURE_PREREGISTRATION.md. Subsequent explicit stress inputs include a positive 1e-310 mol liquid inventory to exercise rejection of the full normal arithmetic box, and conservative saved-error inflation with matching caloric/eT inflation to prove actual fluid error is retained. These are labelled manufactured counterexamples, not altered scientific acceptance thresholds.
- Tests include actual SourceWetStorage evaluate/invert through the existing manufactured liquid seam, full T/V analytic root corners, negative signed numerator/reversal, exact outward support, same-end deduplication with independent epsilon/rounding retained, same-content different object refusal, error surplus refusal, saved-value/type/qualification tampering, root existence failure, callback/return/postprocess failure retention, cancellation prefixes, unresolved original domain with zero calls, and passive check with EOS forbidden.

Independent physics review is recorded in ../physics/PRODUCTION_BRIDGE_REVIEW.md: final source hash matches, 34 actual manufactured bridge checks and 20 independent Fraction constant-v full-T/V comparisons passed in 0.936627875 s. The separate analytic oracle had 1,414 checks and was not rerun. Code review is separate and authoritative for its own final approval.

Final code/test identities and exact test command are recorded in WET_FREEZE.json. Old kernel identities/goldens/test evidence remain in KERNEL_FREEZE.json and ../code-review/KERNEL_REVIEW.md.

## Independent finding and final narrow correction

The first 836a9f15 source freeze is retained in source_wet_shared_pressure.before-transient-limits.py and WET_FREEZE.before-transient-limits.json. Independent reviewer probe code-review/transient-water-limits-red/RESULT.json demonstrated that a cancel callback could temporarily change the actual water numerical_limits, execute one observation under a changed complete storage binding, then restore it before the next observation. The original successful pair.check did not detect this window. This is an actual preserved RED, not an inferred failure.

Final source 9a0b7af1742c91edab9a9999c106657136f491b3ef0ca5583494434fc6ce4e25 includes numerical_limits in the per-observation signature and rechecks complete original input binding after each cancel check, before starting each unique request. The change is four added source lines and changes no formula, qualification or numerical threshold. New regressions separately cover mutation before a request and after an actual return, retaining respectively zero attempts or the complete single returned state.

Final author suite: wet-limits-green.xml/log, **32 passed**, XML **2.924 s** (display 2.93 s). Final test hash dd874e7cdd5be0025708ab7e5892812c8eb0bfd25413e8f2b5e040f0301fe679. The old 30-test file and 836a source/installation evidence remain separate. Independent original probe recheck: code-review/transient-water-limits-fixed/RESULT.json, rejected at validate_inputs before the first new call, zero additional calls/attempts, 0.47765 s. No EOS or unchanged broad regression rerun was performed by this implementation agent.
