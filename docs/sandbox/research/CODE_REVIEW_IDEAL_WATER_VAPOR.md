# Independent review: fixed-R ideal water vapor bridge

Reviewed 2026-09-07 UTC. Scope: `src/sludge_sandbox/ideal_water_vapor.py`, its tests, and `docs/sandbox/IDEAL_WATER_VAPOR.md`. Existing water loader and thermochemistry were read only for interfaces/reference context; this is not a repeat approval of their complete implementations. No implementation edits or commit by reviewer.

## Final binding

- Source SHA-256: `25dbe8b17791b5df2707d3af30011e793206ae31e83aedf231e1d7dd35b190d0`.
- Tests SHA-256: `8d0f8ce4c21aa901a55ac46fd195e736e5fe24703563ce0cc17a24297b627046`.

## Verified behavior

Construction requires an explicit source-directory path and invokes the existing verified water loader. An arbitrary provider or adjustable gas constant cannot be supplied through the public constructor. The fixed value 8.31446261815324 agrees with the existing `nist_gases_v1.json` registered constant. Identity and caloric method checks retain the actual water reference and reject mismatched backend results. Native loader domain/source/numerical errors are not swallowed or turned into a fallback constant.

The bridge reads already aligned ideal enthalpy and does not add the formation-reference offset again. It explicitly changes the ideal convention to `u=h-R_mix*T` and `Cv=Cp-R_mix`; Cp and h remain native aligned ideal values. Delta-u and Delta-Cv are the native-minus-registered R difference times T and unity, respectively, not additional heat inputs. Native identity checks precede derived calculations; finite h/u and positive Cp/Cv are required.

Executed the final focused suite: **28 passed in 0.32 s**. Includes reference anchor, endpoints, derivative checks, invalid source/provider arguments, immutable fields/assets, forbidden R overrides, nonfinite/invalid capacity output, and changed reference identity.

Independently evaluated **2071 temperatures from 293 through 500 K at 0.1 K increments**. Every h equalled the native aligned h and Cp > Cv > 0. Maximum residuals:

- `h-u-R_mix*T`: `1.4551915228366852e-11 J/mol`.
- `(u_bridge-u_native)-reported_delta_u`: `4.709512640976854e-11 J/mol`.
- Interior central-difference `du/dT-Cv`, step 0.001 K: `4.230345851397033e-08 J/(mol K)`.

These independently obtained numerical residuals support consistency of the declared derived model, not empirical uncertainty or mixed-gas validation.

## Review correction resolved

Initial bridge source IDs only exposed the three water sources while introducing the registered mixture R. Requested explicit constant provenance. Implementer added `constant_source_ids=('nist-codata-2022',)`, the exact Avogadro-times-Boltzmann derivation, and inclusion in public `source_ids`; checked final code/tests/documentation. Five verified asset hashes remain explicitly water assets only, rather than falsely claiming that their runtime validation covers the separate CODATA document. This correction changes traceability metadata, not the caloric calculations.

Final metadata also explicitly exposes `classification='derived_from_evidence'`; independently inspected and reran the accompanying assertion. Numerical logic did not change.

## Scope and limits

The immutable wrapper is not a security sandbox against malicious same-process monkeypatching. It supplies temperature-only h/u/Cp/Cv interfaces, not density, mixture fugacity, entropy, chemical potential, saturation or phase equilibrium. Its 293–500 K gate remains the underlying gate; the method ID and `mixture_qualification='not_established'` preserve that limitation. Matching another protocol or R alone is not qualification of a real mixture or sludge material. No underlying water-source or native-R compatibility gate was relaxed.

## Findings

No unresolved actionable issue above the review confidence threshold in this bounded bridge at final hashes.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — explicit fixed-R caloric transition and traceability; not mixed-gas material admission, phase equilibrium, or full Goal completion.
