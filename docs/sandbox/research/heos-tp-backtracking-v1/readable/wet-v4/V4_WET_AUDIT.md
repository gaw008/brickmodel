# Independent V4 wet failed-prefix audit

Audited actual saved callback/depletion and supervisor records with standard-library exact Fraction arithmetic and file hashes only. No model imports, EOS, tests, source/script/install edits or reruns. Detailed per-prefix arithmetic is retained in v4-wet-audit.json.

Depletion result SHA256: `f8fbecaa84256e0dd27bcc3941aa3b3ee3588777793288d33405877ed5636014`.

## Actual failure and input provenance

Depletion supervisor is failed, child exit 1, elapsed 121.78095804099576 s. Inner solver is resource_limit / wall_time_limit at 120.12714812500053 s. Full returned ledger was saved before the outer completion assertion failed. This is not an accepted event or completed trajectory.

All 177 depletion input hashes and 176 callback input hashes match normalized before/after manifests and current files. Fresh callback supervisor is complete, child 0, 2.087811707999208 s; callback result is passed and its full initial state equals depletion initial state exactly. No v3 callback evidence was substituted. There is no depletion1 result or cross-run comparison acceptance in this audit.

## All six accepted prefixes

Recomputed every species ledger using exact binary64 Fractions, including face and reaction contributions; recomputed every total-energy work/face prefix. Their sums equal recorded cumulative rational totals exactly. All accepted states preserve the initial energy identity and carrier amount. All face species and energy fluxes are zero. Liquid remains positive, the final interface is existing_liquid, and there are no committed events/corrections or nonzero correction totals.

Maximum residuals over all accepted prefixes:

| Quantity | Absolute maximum |
|---|---:|
| C = A+B | 1.2053617652607596e-16 mol |
| H = 2(vapor+liquid) | 1.9190590211230242e-22 mol |
| O = vapor+liquid | 9.595295105615121e-23 mol |
| Accounted solid+water mass | 1.4464358469310402e-18 kg |
| Each species versus integrated ledger | 1.205336354272342e-16 mol |
| A versus analytic first-order solution | 2.220446049250313e-16 mol |
| Total energy versus integrated ledger | 1.7920981904939563e-11 J |

Mass uses the declared 0.012 kg/mol solids and source-provided water molar mass. The inert carrier is unchanged and no unprovided elemental composition is invented for it. These prefix residuals satisfy original specified gates.

Every step's body/bulk-pressure/dissipation/elastic-deformation/interface-deformation component sum plus its exact recorded residual equals total work. Body is zero; there is no extra mechanical composition power term. Sum of absolute component residuals exactly matches the recorded cumulative Fraction, 2.8720641446030243e-20 J. These are ledger consistency checks, not an independent wet temperature or constitutive oracle.

All accepted physical amounts/energies, times, full steps and cumulative ledgers match v3 exactly. The energy model identity differs, consistently with the reviewed new source-bound implementation. Therefore complete serialized states must not be called identical across versions even though their physical numbers are identical. Accepted endpoint remains 0.5002341642497935 s.

## Speculative work and remaining gate

Actual phase evaluations are ordinary 55, approach 240, terminal 6, dry 54 and comparison 10, exactly 365 total. Panels are 6+26+6+6+0 = 44 with zero rejected trials. Per-refinement evaluation counts equal their phase sums. Reuse is separately counted as 32 observations and 27 panels, not added to actual execution totals.

Levels 4 and 5 pass the original terminal comparison gates, with amount differences 9.97847847712262e-11 and 3.797651082493303e-11 mol below 1e-10. This represents real progress beyond v3's HEOS failure. The required independent halved-controls branch then ends in wall_time_limit without comparison acceptance or commit. Two terminal passes alone do not satisfy the full prescribed event acceptance rule. No event, dry continuation or cross-cap convergence is approved. Original resource/event thresholds remain unchanged and this failed run stays failed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: input provenance, failed-prefix preservation and numerical ledgers are consistent. V4 event completion remains unfulfilled at the original resource gate; no second trajectory is justified by a successful first-run claim.
