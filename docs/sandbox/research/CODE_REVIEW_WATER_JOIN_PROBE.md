# Independent review: water caloric endpoint probe

Verdict: APPROVE as an endpoint discrepancy measurement only. No production model or source asset was modified; the probe neither joins the providers nor certifies their absolute accuracy.

Read water_caloric_join_probe.py and its JSON, then independently loaded the existing source-gated low-temperature IdealWaterVapor and NIST H2O Shomate provider. Recomputed all four fields and high-minus-low differences directly without invoking the probe's main function or overwriting its artifact. Every recorded float matched exactly. Verified every listed code/input hash and the low-water asset mapping against the current providers/files.

500 K lies at the shared included endpoint of the stated low 293–500 K and high 500–6000 K caloric domains. This is a caloric endpoint comparison, not a proof of a continuous admissible joined domain or a real high-pressure water EOS. The high provider is the original Shomate table, not a previously adjusted continuous fit.

| At 500 K | Low provider | High provider | High minus low |
|---|---:|---:|---:|
| h (J/mol) | -234901.93001966586 | -234901.7552083333 | +0.17481133254477754 |
| u (J/mol) | -239059.16132874248 | -239058.98651740994 | +0.17481133254477754 |
| Cp (J/(mol K)) | 35.22628069595986 | 35.21836175 | -0.007918945959858092 |
| Cv (J/(mol K)) | 26.91181807780662 | 26.90389913184676 | -0.007918945959858092 |

Both use R=8.31446261815324 J/(mol K). Therefore equality of the h/u jumps and of the Cp/Cv jumps follows from u=h-RT and Cv=Cp-R; those equalities are consistent identities, not four independent validations. As a further check, directly applying the high branch's explicit Shomate coefficients at t=T/1000=.5 using exact decimal rational arithmetic gives Cp=35.21836175 and h=-234901.75520833334, agreeing with the saved high results to roundoff. The low provider's underlying ideal-water formula was not re-audited here; its existing source/method qualification remains in force.

The shared energy reference does not imply zero endpoint discrepancy between two source models. The measured jump is not an uncertainty estimate, a statistical confidence interval, a fitted correction, latent heat, or new reaction heat. A future offset/interpolation would need its own explicit reference and derivative policy, source identity and tests. This probe correctly stops at measurement. Its high_source_ids describe the species table; the input-pack hash also binds the common constant setting. No unrecorded material accuracy conclusion is drawn from those labels.

The script writes its measurement JSON directly rather than maintaining numbered attempts; this review reran only independent field calls, preserving the supplied artifact. No heavy or installed-suite rerun was needed.

| Reviewed evidence | SHA256 |
|---|---|
| `docs/sandbox/research/water_caloric_join_probe.py` | `e07f251d305dd23a837601fd6c5188c48aa9b739e4a0b609dd8763a586eb4ea0` |
| `docs/sandbox/research/water_caloric_join_probe.json` | `2c12f591fdc008bae919d561c87501ba515ccf0e24530f868c8b915fe5f2879b` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — source-bound endpoint measurement, with no joining, extrapolation or accuracy-certificate claim.
