# Final independent dry pressure review

Verdict: APPROVE for the hashes below. The single confirmed provenance finding in DRY_PRESSURE_RED.md is closed; its original two failing tests and source hashes remain preserved.

The fix adds only reconstruction of the original fluid source sequence: mechanical sources, envelope sources, then each nonzero gas phase's metadata in the bound storage.gas_ids order, preserving first occurrence. This matches RigidStorage's actual construction and does not trust saved mapping insertion order. It does not change pressure arithmetic, uncertainty, domain gates, the shared wet validator or scientific qualification.

Bounded independent recheck: the two original provenance REDs now pass (dry-fix02.xml/log). Only those affected tests were rerun; the three already passing independent interval checks and unchanged author suites were not repeated. The prior independent batch was 3 passed / 2 failed in 0.47 s before this fix. Native EOS, model installation and production edits were not performed by this reviewer.

The previously reviewed arithmetic forms an exact ideal-gas T/V corner interval and retains the original reported pressure radius plus the full-temperature sensitivity allowance; taking their hull cannot shrink the original error. Nonpositive volume ranges are rejected; full T or P domain exits remain unresolved. The actual dry record binds zero liquid/no liquid pressure/zero liquid volume, analytic gas closure, original residual and representation errors, source caloric total-U inverse evidence, and a separate dry qualification. The positive-liquid requirement remains at the wet entry. Existing three wet golden outputs were independently confirmed byte-identical at 98,601 bytes, SHA 84fc11db47fd1f622417535d0dbe2f4cabb1d4f9128900e5a46c49c479075056; the original author 64-test XML was read, not rerun.

Final SHA-256:

- source_dry_pressure.py: 1404797b0f9e4d7f8154d8d5937d745f9754b3e512b57833185f581152be33d8
- source_inverse_pressure.py: 27b90389a8b6ad6055cbe5cb4310122059ea605990ec84c41bd64f4022f949b1
- test_source_dry_pressure.py: 2b756bae563447409d7d4b339b2a6f1fc208e0b4fba0814888eb69b0ef8ee1d6

Scope remains conditional numerical dry pressure evidence. No event/phase-transition, material qualification, physical EOS accuracy certificate, or runtime transition acceptance is implied by this review.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — confirmed source-binding defect fixed and independently verified.
