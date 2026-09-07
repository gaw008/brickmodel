# Independent review: prescribed-pressure phase storage

Reviewed 2026-09-07 UTC. Scope: `phase_storage.py`, its tests and documentation. Reviewer owns this report only; no implementation edits.

## Independently reproduced defects and corrections

1. False temperature precision from quantized energy: manufactured `u=1e10+20*T`, `h=u+1`, `v=1/p`, T domain 300–400 K, n=1 mol, p=1e5 Pa. Forward T=350.123456789 K, energy tolerance 1e-5 J, temperature tolerance 1e-12 K. Initial inverse returned T=350.12345671653725 K, error -7.246e-8 K, while its stored energy residual was -1.907e-6 J. Merely narrowing a bracket in the rounded forward function did not justify the temperature precision. Implementer added per-phase and total representation allowance, including cancellation between large terms, conversion through the declared derivative lower bound, and endpoint/interior precision checks. Independently reran the exact counterexample: now `unresolvable_energy_temperature_precision`.
2. Identity loss in bare Shomate segment wrapping: root identified possible default H2O/derived labeling of another gas or fixture. Final inspected design instead takes an identity-bearing `ShomateGas` and explicit single segment, preserving species/classification and declared molar-mass source. No cross-seam curve is inferred. Root also requested provider metadata/domain mutation snapshots; inspected before/after provider checks and regression tests.
3. Inverse provenance: requested actual participating MonotonicPath metadata and explicit conditional result status. Current result includes immutable path mapping and their source IDs, and `conditional_on_declared_monotonic_paths_not_independently_admitted`. Numerical samples/endpoint checks are not presented as a proof of global monotonicity or source admission.
4. Tiny positive derivative bound underflow: n=0.1 and bound=5e-324 yielded aggregate zero and unhandled ZeroDivisionError. Implementer added finite-positive checks to every extensive bound and total. Independently reran original input: now structured `PhaseStorageError: invalid_extensive_derivative_bound`.

## Independent physical checks

At fixed pressure, liquid `du/dT = Cp - p*dv/dT`, not Cv. Independently checked WaterProperties/LiquidWaterPhase central differences with dT=0.01 K:

| T K | p Pa | du/dT J/(mol K) | Cp-p dv/dT | native Cv |
|---:|---:|---:|---:|---:|
| 300 | 100000 | 75.3148446209 | 75.3148446236 | 74.4062746377 |
| 350 | 100000 | 75.5633510737 | 75.5633510603 | 70.0678461348 |
| 450 | 10000000 | 78.2300520514 | 78.2300520353 | 61.2692260650 |

Maximum derivative identity residual <1.7e-8 J/(mol K). The difference from Cv is material and must not be discarded in later mechanical closure.

Independently exercised actual liquid water 2 mol plus ideal water bridge 0.2 mol at externally prescribed 1e5 Pa. Used explicitly conditional derivative lower bounds 70 and 20 J/(mol K) on 293–350 K, not claimed as independently admitted material evidence. Forward/inverse at 300/320/345 K produced maximum T error 4.37e-10 K and maximum U residual 6.80e-8 J, within declared 1e-8 K/1e-7 J numerical policies. Conditional status was preserved.

## Scope

This is species thermal U/H and volume at fixed supplied phase pressure and inventory. It is neither a pressure-volume mechanical closure nor an equilibrium/kinetic phase transfer model. Provider reference-ID agreement is a declaration, not verification of all material evidence. Zero inventory skips property evaluation and pressure requirements; metadata identity may still be checked. Manufactured solids remain explicit software fixtures.

Final documentation has been read. It distinguishes the representation budget from a rigorous upstream property-algorithm error bound and requires independent later material/path admission. Reviewer initially suggested that specifying `abs` alone retained pytest default relative tolerance. That assertion was incorrect. Root checked pytest 8.4.2 source, and reviewer independently inspected `ApproxScalar.tolerance`: when abs is provided and rel is None it uses absolute tolerance alone. Direct check `600.0000125 == pytest.approx(600, abs=2e-6)` is false. The added explicit `rel=0` is readability clarification only, with no semantic or acceptance-threshold change. Independently reran that final suite: **22 passed in 0.89 s**. No earlier false pass or test-strengthening claim is supported.


## Final binding and findings

Source SHA-256: `35c96268af0e7ab7f338a7edacfa2940f50d82a9cf7df70360eb06ba92784bec`.
Tests SHA-256: `ab082b99fed2f1c4b8b8d2b14f2a48c348551d43a7b9889b3c77d597324c713d`.

No unresolved actionable issue above the review confidence threshold. The identified numerical precision and traceability issues were corrected and independently rechecked. Frozen-provider metadata checking does not certify arbitrary nested callback implementations or validate user-declared monotonic bounds; those limitations remain explicit.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — prescribed-pressure species storage and explicitly conditional temperature inversion at final hashes; not mechanical/volume closure, phase equilibrium, admitted raw-sludge properties, or full Goal completion.
