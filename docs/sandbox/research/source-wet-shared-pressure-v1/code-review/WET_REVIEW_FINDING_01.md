# Finding 01: transient source numerical configuration is not bound per request

[HIGH] A cancel callback can temporarily change the actual water provider numerical limits while producing accepted observations.

File: src/sludge_sandbox/source_wet_shared_pressure.py (_water_metadata and collect_source_wet_pressure_pair), frozen SHA 836a9f15256e73159cfa7e15de919d3a08ac4dd0a12933e2335090d58761e057.

Issue: The initial complete source check runs before the user-supplied cancellation callback. Point-level metadata excludes water.numerical_limits, although the original storage identity includes it. A callback changes pressure_relative for the first request, restores it before the second, and returns False each time. The first observed request has a failing original storage._check(), yet all point metadata matches and the final pair and pair.check() succeed. This records a request under a different source configuration as if it used the original binding.

Actual evidence: transient-water-limits-red/RESULT.json and transient-water-limits-red.log; probe_transient_water_limits.py. Existing actual SourceWetStorage evaluate/invert plus the existing explicitly manufactured liquid seam. Setup: 1760 cheap seam calls; probe: 4 additional observation calls; 0 native EOS calls; 0.574995083 s. The original complete source check actually reported source_wet_provider_content_changed during the first request.

Fix: Recheck the original complete endpoint/shared binding after each cancellation callback and before adding/performing a new request, and include numerical_limits in per-point provider metadata so a changed return configuration is also rejected while preserving the raw return. Preserve original scientific inputs, thresholds and the initial RED.

Status: Confirmed; author notified and preparing a bounded fix.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — resolve the source-binding defect before the registered native run.
