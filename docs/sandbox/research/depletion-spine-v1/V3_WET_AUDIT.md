# V3 native wet failed-run independent audit

Read-only audit of the saved result and supervisor metadata/status; no model imports, EOS, tests or trajectory reruns. Arithmetic evidence is in `v3-wet-audit.json`.

Result SHA256: `bfae0402e7a3502dd475914948e2d77d3527e36ed3ca1542ceb06f2f59711a25`.

## Actual outcome and provenance

The supervisor terminated failed, child exit 1, elapsed 47.38957912499609 s. The saved solver returned `numerical_failure`, reason `liquid_property_solution:heos_tp_not_converged`, inner elapsed 45.760554042004514 s. This is a numerical failure before the unchanged 120 s solver resource gate, not a resource-limit success. The outer script saved the full returned ledger before its completion assertion failed.

All 175 named input hashes match between supervisor metadata and after-status, and independently match current file bytes. Metadata stores hash/byte-count records whereas status stores hash strings; comparison normalized these representations. No input drift was found.

## Complete accepted prefix

All six committed steps and seven states/times exactly match v2, as do complete step ledgers, cumulative amounts/energy, component residual totals and correction totals. The accepted endpoint remains t = 0.5002341642497935 s. Every accepted state retains positive liquid, the same total-energy identity and unchanged carrier amount. The final interface remains existing_liquid; the phase-transfer coefficient remains 1e-6 mol/s/Pa. There are no committed events or corrections.

Recomputed each prefix from the saved binary64 values using exact Fraction arithmetic. All species and energy cumulative totals equal the recorded rational totals exactly. Maximum absolute residuals across the six prefixes:

| Quantity | Residual |
|---|---:|
| Solid carbon A+B | 1.2053617652607596e-16 mol |
| Total water vapor+liquid | 9.595295105615121e-23 mol |
| A against 2 exp[-0.1(t-0.5)] | 2.220446049250313e-16 mol |
| Every species versus integrated ledger | 1.205336354272342e-16 mol |
| Total energy versus integrated work/face ledger | 1.7920981904939563e-11 J |

These are below the original prefix gates. Water hydrogen/oxygen conservation follows with residuals twice/equal the water residual; solid mass residual is carbon residual times the declared 0.012 kg/mol. All external face species and energy fluxes are zero. Each step's five work components (body, bulk pressure, dissipation, elastic deformation, interface deformation), plus its exact declared sum residual, exactly equals total cell work. Body is zero and there is no added mechanical-composition work term. Absolute component-sum residual accumulation equals the recorded rational total, 2.8720641446030243e-20 J. This verifies accepted ledgers, not independent constitutive accuracy of unrecorded internal stages.

## Actual work, reuse, and unfinished localization

Actual evaluations by phase are ordinary 55, approach 58, terminal 3, dry 27 and comparison 4: exactly 147 total. Actual panels are 6+6+3+3+0 = 18; rejections are zero. Reused observations 12 and panels 9 are separately reported, not added to actual execution totals. Every refinement's evaluation count equals its phase-bucket sum. Refinement actual evaluations total 92 and account for all non-ordinary work; ordinary work accounts for the remaining 55. Some actual approach work is speculative and absent from the six committed steps, as expected.

Completed refinement levels 0–2 have exactly the same event times, terminal caps, common times and all five difference metrics as v2. Levels 1 and 2 still fail the amount gate: 5.579376084445943e-9 and 1.7686775075932953e-9 mol versus 1e-10 mol. The finer level 3 has no completed event time or comparison: it records 12 actual approach observations and one attempted approach panel before the liquid property failure. Therefore there is no two-pass terminal agreement, independent-approach acceptance or event convergence. The failed artifact supports accounting and rollback correctness and demonstrated reuse, not a completed trajectory speedup ratio against v2's different termination.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: saved failure evidence and accepted-prefix accounting are internally consistent. Native wet event completion remains unfulfilled because the liquid-property numerical solve failed; no event or full-model success is approved.


## Independent diagnostic replay audit

The instrumented replay remains failed, child exit 1, supervisor elapsed 49.48451983300038 s. Exactly one matching exception was captured, with no logging errors. All 176 supervisor input hashes match before/after and current files. Snapshot SHA256 is `dd707eed205fa5162f5fe8c78479bc086dda465f107441161fad25fd1f3929d5`.

Compared every saved run field with original v3, excluding only elapsed_seconds at top level and within refinements: all values match exactly. Thus the six accepted prefixes, 147 evaluations, 18 panels, reuse counts, all completed comparison details and the original numerical failure are preserved. Prior full-prefix audit applies without reconstruction. This does not claim tracing has zero overhead.

The actual failure arguments are liquid T=295 K (`0x1.2700000000000p+8`) and P=53692.54782795906 Pa (`0x1.a379187ce8000p+15`). All eight iteration rows alternate exactly between two records, excluding their iteration index: rho 997.7857491595237 and 997.7857491595711 kg/m³; pressure residuals -0.00010403933993075043 and +0.00010410800314275548 Pa. Both exceed their original min(1e-4,rho*1e-7) gates, respectively 9.977857491595236e-5 and 9.97785749159571e-5 Pa. This is direct evidence of a full-step two-cycle under these evaluated inputs, without inferring that any untested alternate density passes.

The final frame-local rho is the next post-update density, not the density corresponding to the final residual/slope: the arithmetic rho_last*exp(-residual_last/slope_last) equals that captured local rho. It happens to equal the earlier even-iteration density, already evaluated on prior iterations, but is not a ninth evaluation. The eight-row record supplies the valid density/residual pairing. Further exact-point probing or numerical changes remain separately preregistered work; no EOS was run for this audit.
