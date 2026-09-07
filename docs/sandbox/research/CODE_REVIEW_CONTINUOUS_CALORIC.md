# Independent review: continuous Shomate caloric derivation

Reviewed 2026-09-07 UTC. Scope: `continuous_caloric.py`, its tests and `CONTINUOUS_CALORIC.md`; original thermochemistry was read for source/branch/caloric contracts and not modified.

Source SHA-256: `f3a6009df0514bfbe73c5db728e46a3515baa0e81d03f2eb2f8076df3e04e8de`.
Tests SHA-256: `4c3b6c126c248e9203e35228313d2d15008b80fdfce2dbbbc6014894427f7165`.

## Reviewed physics and traceability

Original immutable Shomate gas identity, classification, coefficients and adjacent temperature ranges are retained. A specified in-domain original h anchor fixes a derived reference; integration proceeds in either direction across original Cp segments. The integral has the correct 1000 scale and `E*(1/x-1/y)` term. It does not use the difference of two rounded large h values as its small-heat oracle. Exact Fraction propagation maintains identical segment endpoint h/u; Cp discontinuities remain, with the higher segment owning a shared node.

The original Shomate constructor rejects range gaps; this wrapper does not invent gap fills or extend domains. Manufactured sources retain manufactured classification and require opt-in. Method/model/version, original branch sources, and separately required gas-constant source IDs are exposed. Per-segment offsets compare against the exact binary-coefficient original primitive and correctly document differences from subtracting two rounded display values. Source links are declarations, not proof of material admission or independently verified assets.

No new entropy, chemical-potential, IAPWS join, inverse-temperature algorithm or direct replacement of the old Thermochemistry interface is claimed. Changing the anchor can change constant energy offsets, and documentation explicitly requires a separate derived configuration identity.

## Independent numerical evidence

Focused suite executed: **20 passed in 0.32 s**. Read tests for three-segment reversal/cycles, seams, class/source gates, published NIST quadrature, all Cp terms, very close temperatures, and large energy baselines.

Independently implemented an **80-digit Decimal** antiderivative from original coefficients, without importing the module's integral helper. For all four original gases and all 10 segments, selected each gas's lower/middle/upper-domain anchors and each segment's lower/middle/upper/nextafter points: **120 cases**. Derived absolute h agreed with the independent original-float anchor plus Decimal piecewise Cp integral. Adjacent-float heat changes agreed within two ULP of the independently rounded tiny increment, and reverse increments were exact sign reversals. Original Cp values were unchanged at every sampled point; separately checked exact h and u equality across every seam for every anchor.

Recomputed the documented per-segment offset diagnostics with each first-segment midpoint anchor. Values match the table: O2 later offsets about 1.714022032 and 0.476855365 J/mol; N2 -0.768385417 and -0.874218750; CO2 3.167188533; H2O 2.928677143. First-segment offsets are approximately zero with anchor rounding retained. These are model-reference shifts, not experimental uncertainties.

Absolute binary64 h/u can still hide tiny differences beside a large reference; the module supplies separately integrated changes and explicit ULP diagnostics, and does not falsely promise lossless subtraction of absolute outputs. This is a representation diagnostic, not an upstream fit-error bound.

## Findings

No actionable issue above the review confidence threshold in this bounded derived caloric component.

## Follow-up: actual runtime pack/integration connection

Preserve the original 20-test binding above as historical evidence. Reviewed the two added tests and accompanying documentation, then independently ran the final suite: **22 passed in 0.50 s**. Production source is unchanged at `f3a6009df0514bfbe73c5db728e46a3515baa0e81d03f2eb2f8076df3e04e8de`; final tests SHA-256 is `e6dee468d6046959dda1efccd242cb9093ee74d3ee835baf7a0f754ef90cce91`.

The manufactured integration explicitly constructs a new Thermochemistry pack containing the derived object, then passes it to the actual GasHeatModel. Each operator evaluation calls the actual model before adding declared 1000 W electrical power to its unchanged face/reaction rates. It is not a replaced ODE or merely a mocked caloric result. The single mole has Cv=22 below 600 K and 32 above, so 500-to-600 K requires 2200 J, and 600-to-700 K requires another 3200 J. Independently checked the test's piecewise analytic temperature and 5400 J total work calculations. Tests compare every saved temperature and energy, every accepted work ledger, zero face heat, constant amount, and actual operator-call count with absolute tolerances and zero relative tolerance. Zero rejected trials and successful seam crossing are asserted.

The known 2.2 s seam crossing is supplied explicitly as an integration breakpoint. This verifies crossing with a known event time, not automatic detection of arbitrary future state-dependent seam events. Other reactions, matter transport, liquid phases, spatial coupling and unknown seam timing are not covered by that test.

The second test explicitly builds a distinct derived O2 pack and executes the existing actual energy inverse at 699.9, 700 and 700.1 K. Read the inverse's branch selection and upper-endpoint ownership code to verify that the exact shared endpoint is not counted as two distinct roots. The original nonzero fit seam diagnostic remains present. This is a forward/inverse consistency check around the 700 K seam; the earlier independently derived Cp-integral comparisons supply separate caloric-reference evidence. It is not a new O2 experiment or proof for every multicomponent inverse.

Current runtime duck-typed interfaces support this explicit assembly; legacy static ShomateGas annotations and the old source-JSON loader are unchanged. No general derived-model JSON serialization, automatic old-pack replacement, IAPWS low-temperature join or material admission is established. Approval extends to this bounded test/documentation increment.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — continuous h/u derivation over existing Shomate Cp coverage at these hashes; not a low-temperature water bridge join, material validation, or full Goal completion.
