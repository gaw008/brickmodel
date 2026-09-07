# Independent review: local water TP response

Reviewed 2026-09-07 UTC. Scope: added `WaterResponse` and `WaterProperties.state_tp_response`, new tests and `WATER_RESPONSE.md`. Read surrounding source-gated state construction and stability/caloric checks. Existing state fields and API behavior were not changed. Reviewer made no implementation edits.

Source SHA-256: `2684a37586773b2a866ef0c923339e81044638ba701692962c9297cfcc3e289c`.
New tests SHA-256: `0a259725487b93fee1b8314d77297f66cc9913597331a41b2a07a2bff5bb0f59`.

## Formula and domain review

Let D=1+2 delta phi_r,delta+delta² phi_r,deltadelta. The expansion numerator 1+delta phi_r,delta-delta tau phi_r,deltatau and denominator T D are correct. Kappa is computed directly with rho*R_specific*T*D in SI, yielding 1/Pa without an omitted MPa conversion. M/rho gives molar volume; dv/dT=v alpha and dv/dP=-v kappa have consistent molar units. From hP=v-TvT and u=h-Pv, uP=-TvT-PvP is correct. Cp-Cv=T v alpha²/kappa is independently checked at the unchanged preregistered 1e-7 J/(mol K) numerical threshold.

The response first obtains the validated TP state, then checks exact state type, requested T/P/phase, reference identity and method. Stable liquid/vapor range and source/numerical failures remain governed by the original provider. No ideal u0, additional formation offset, mixed-gas partial-molar response or saturation ambiguity bypass is introduced. Alpha is finite but not arbitrarily constrained positive; kappa and mechanical stability are positive. Generated response/state are frozen and source IDs remain available.

## Executed checks

Independently ran new response tests, all original water tests and the concurrent bracket regression suite: **122 passed in 2.68 s** = 21 new response + 78 original water + 23 bracket tests. Read new negative tests: they preserve an already verified state before corrupting the response derivatives, so success is not merely rejection by the old state gate. They check nonfinite and finite-inconsistent derivatives, identity mismatch and immutability.

Additional independent finite differences used three states: liquid 300 K/1e5 Pa, liquid 450 K/1e7 Pa, vapor 450 K/1e5 Pa. Used T step 0.01 K and a different P step of 10 Pa, reevaluating full TP state each time. Relative discrepancies for dv/dT, dv/dP, du/dP respectively:

- 300 K liquid: 8.68e-9, 2.54e-7, 7.80e-6.
- 450 K liquid: -9.69e-10, 6.25e-8, -1.53e-7.
- 450 K vapor: -6.59e-11, -1.00e-8, 1.01e-9.

Maximum absolute Cp-Cv identity residual in these independent cases was 6.09e-11 J/(mol K). Comparisons use separate state finite differences, not the response formula as its own oracle. They establish numerical consistency of the sourced equation, not physical uncertainty bounds.

## Findings and limits

No actionable issue above review confidence threshold. The document accurately limits these outputs to local state sensitivities: a point value is not sup|du/dP| over a pressure interval, a certified upstream EOS error, or a complete closed-cell U-to-T error guarantee. Pure-water vapor response remains a pure-fluid derivative. Subsequent energy closure must propagate pressure-path and upstream property errors separately.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — local sourced water TP derivatives at these hashes, not interval certification or full Goal completion.
