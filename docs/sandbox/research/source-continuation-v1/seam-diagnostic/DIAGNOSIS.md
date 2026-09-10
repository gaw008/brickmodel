The second manufactured trajectory fixture is correctly rejected by the original pressure gate. This is not a source-trajectory implementation failure. One passive decode of the saved record took 4.06880638 s with physical callbacks explicitly forbidden and zero forbidden attempts. Original record SHA: `bf5eaa8d630849a36a48e590a97a7be509eda56cd4d02f09e2f26bf0fe28f5a3`.

At both compared endpoint stages the wet cells 0 and 2 fail, while the selected dry cell passes. Wet joint pressure bounds are 0.000146999161438 and 0.000124604685918 Pa against the unchanged 1e-4 Pa gate. Their two retained actual fluid-pressure error terms already total 0.000144095851185 and 0.000121933946359 Pa. Removing every temperature contribution would still leave 0.000145640214238 and 0.000123248682958 Pa. The saved temperature inverse errors are about 2.11e-10 K, far below both 1e-6 and 1e-8 K, so further inverse-temperature tightening does not address this failure.

The original `rigid_storage.liquid_pressure_error_bound` divides abs(saved volume residual) + saved volume resolution + liquid inventory times declared liquid-volume error by the full-domain lower compliance NgRT/Pmax². That compliance is about 1.01332513e-11 m³/Pa. The actual saved residuals are 7.04027528e-16 and 5.91741452e-16 m³. The local mechanical root still used pressure_tolerance_pa=1e-5 and returned a 9.00402665e-6 Pa numerical bracket. The wide original pressure domain makes these small local residuals significant in the retained full-domain pressure error. Shared-volume treatment must not remove those original actual fluid terms.

A justified single new manufactured case is `pressure_policy.pressure_tolerance_pa=1e-7`, restoring inverse temperature tolerance to its original 1e-6. Keep the event P gate 1e-4, available-volume uncertainty 1e-12 m³, liquid-volume error 1e-16 m³/mol, other envelope/policy values and the real HEOS case unchanged. This controls the numerical root accuracy, without changing a physical law or accepting a larger error.

The unchanged bisection stops only once its bracket is within pressure_tolerance_pa; `finish` additionally checks pressure residual and resolution against that same tolerance. For this saved constant-volume manufactured liquid and common pressure support, allocating 4e-5 Pa of the original 1e-4 pair budget to each retained fluid term requires each absolute volume residual below 3.79278e-16 m³. The new tolerance yields a conservative saved-box allocation of about 1.26e-5 Pa per endpoint using L*(delta/2 + midpoint ULP) + 2*Gamma for the native residual (L=NgRT/Jlo², vP=0), then the unchanged original fluid-error formula. The fixed Gamma and volume-error terms remain included. This is a numerical allocation at saved state/support, not proof of a future run: its new full T/P support, return fields and every original gate must be evaluated and checked normally. See exact Fraction calculations in `derive.py` and `ALLOCATION.json`.

The proposed tolerance is representable: max initial-bracket endpoint ULP is 1.86264515e-9 Pa and the saved final pressure resolution is 1.30872178e-9 Pa, both below 1e-7. Seven further bisections would reduce the saved width to 7.03439582e-8 Pa; 41+7 iterations remain below the original 100. This supports trying the one registered case; it is not an assertion that it has passed.

Preserve the default manufactured false case as a refusal regression. A positive test must use either the new actually solved manufactured configuration, or a current-version actual HEOS study and explicitly new native continuation. A historical HEOS `true` record supports passive historical checks only; do not relabel its runtime/provider identity, force an accepted flag, or use a substituted liquid seam while claiming its original live identity. The old source-run resume contract remains unchanged.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | diagnostic only |
| HIGH | 0 | original rejection is correct |
| MEDIUM | 0 | no production change proposed |
| LOW | 0 | no EOS or new numerical run |

Verdict: the single derived manufactured pressure-solver tolerance change is justified for a new test; future success must be demonstrated by its actual result.
