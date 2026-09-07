# Six-fraction density-step diagnostic review

Read probe.py and the numerical preregistration. Input-manifest hashes and exact copies of the captured exception, failed exact-point result and numerical review are verified. AST parsing only; no provider imports, tests, EOS or source changes.

The diagnostic uses the captured first evaluated density and direction, with fixed fractions 1, 1/2, 1/4, 1/8, 1/16, 1/32 all calculated from the same base. It first demands exact native seed and complete base-record equality with the original failure. It demands original kernel identity and full-step density reproduction. It changes no provider, manifest, reference, constitutive source, solver acceptance gate or production code.

All trial densities are actually evaluated using native SI under the source/configuration transaction, retaining stable phase/density, finite positive slope, finite records and original full-step bound. Each trial gate remains min(1e-4,rho*1e-7). A strict merit decrease is only diagnostic metadata and never sufficient for final passing status. Gate-passing trials additionally undergo the existing complete snapshot/Table-3 and final branch checks. Invalid native/source results abort instead of becoming ordinary rejected candidates. Native work is explicitly bounded by six trial-density calls and at most six snapshot checks in addition to declared setup/base work; each snapshot itself performs existing derivative validation work.

Recorded trials append before snapshot validation, so a failing snapshot retains the observed trial and an overall failed result, without verified snapshot evidence. Overall success is set only after experiment completes including its final transaction/source guard. Post-identity failure also forces nonzero exit. Existing output is protected and final JSON publication is atomic. The script returns no replacement host/provider state and must remain diagnostic-only. Full installed/source hashes are checked before and after. No credentials or unrelated environment data are logged.

Final supervisor/PLAN review pending their preparation; probe implementation has no identified blocking finding at this stage.


## Final prepared files

Final probe.py SHA256 `179323379e85d4ee9f2ac1eabd486b2b448ff32ff6a152ac1c81542891879d9a`; run.py SHA256 `d660d46622a98200786d2e9eaeb6c35c8754cb0738eaf76a3ea5b7a8ad5d4df5`. Checked all six PLAN frozen hashes and parsed final scripts. The final probe adds active_trial fraction/density capture before native trial evaluation, preserving the failed candidate context without an extra native call.

Read final PLAN.md and run.py. The supervisor keeps the 30-second external cap, installed interpreter, unset PYTHONPATH and original complete-status/zero-child-return success conjunction. Its declared before/after inputs cover the frozen plan, scripts, native source assets and copied evidence. The plan explicitly handles possible missing child JSON on external interruption and preserves supervisor failure evidence. No further native attempts or physical acceptance follow automatically from diagnostic success.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE final frozen six-fraction diagnostic and supervisor under PLAN. No EOS or tests were run by this reviewer. Original exact-point and coupled failures remain unresolved pending actual new evidence.
