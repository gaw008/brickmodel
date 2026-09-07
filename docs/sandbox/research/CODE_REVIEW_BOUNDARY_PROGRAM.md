# Independent review: continuous boundary program

Reviewed 2026-09-07 UTC. Scope: `src/sludge_sandbox/boundary_program.py`, `tests/sandbox/test_boundary_program.py`, and `docs/sandbox/BOUNDARY_PROGRAM.md`. Root/concurrent-agent changes were preserved. No implementation edits or Git commit by reviewer.

## Approved binding

- Source SHA-256: `fcf6736c699aea3bb759472d48358dc76d1bce1e9e4cd61a823f3e0e1b378319`.
- Tests SHA-256: `2141bd3335001e53c76308c86a94767fc67c1afa0af672827f38cf59d8345f45`.

## Checks and actual evidence

Read complete implementation, all tests, documentation, and existing `integration.integrate` knot/continuous-forcing contract. Executed focused suite after the implementer completed its extra cases: **41 passed in 0.06 s**.

Validated finite nonboolean real inputs, strictly increasing finite knots, positive boundary absolute temperatures and total pressure, explicit species uniqueness/counts, mole-fraction range and near-unity sum, and no extrapolation. All source/identity inputs are explicit and immutable under ordinary API use; nested mutable input containers are copied. Output fractions use a copied read-only mapping. Source classification remains an identity declaration and does not claim a resolved evidence source or material admission.

Exact-rational interpolation avoids overflow in the difference of extreme finite time endpoints and values. Independent seeded execution of **1000 extreme-sign/time/value cases** matched independently assembled Fraction convex combinations. Exact endpoints retain supplied float values. Adjacent representable times are accepted as a program domain without falsely claiming the integrator can resolve intermediate stages. Fractions are never normalized; the documented `8*ulp(1)` acceptance allowance is a numeric representation policy, not experimental uncertainty.

Executed an independent actual integration connection using a manufactured heat input derived explicitly as `program.at(t).gas_temperature_k - 300`, with knots 0, 1, 2 s and temperatures 300, 301, 300 K. This is a declared software fixture, not a physical furnace heat-transfer law. Passed `program.breakpoints_s(0,2)` to the real integrator with initial/max step 0.7 s. It completed at saved times `(0.0, 0.7, 1.0, 1.6, 2.0)`, landed exactly on the interior knot, never crossed it in an accepted step, and returned 11 J from 10 J initial energy, matching the independent triangular input integral of 1 J. No boundary extrapolation was needed.

The implementer subsequently added a persistent actual-integrator test with 7 s nominal steps, 10/20 s slope knots, independent piecewise-quadratic energy, every saved state, and every accepted work ledger. Independently read and reran that final test; its 15000 J cumulative input matches the exact trapezoidal ramp/hold/cool areas. Source code hash is unchanged.

## Scope boundaries

The generic ScalarProgram intentionally accepts signed values regardless of unit; physical positivity belongs to the typed BoundaryProgram channels or later caller. BoundaryState is documented as a generated output record rather than a independently validated external-input admission object. Those distinctions are not silently promoted to stronger validation claims.

The current implementation is continuous piecewise-linear input data, not discontinuous boundary handling or completed dynamic gas-reservoir coupling. Documentation explicitly preserves separate gas/radiation temperature semantics and warns against substituting gas temperature for a material-surface Dirichlet condition. Actual material-domain and complete-active-species consistency checks still belong to coupling. No material property or physical exchange coefficient is introduced by this module.

## Findings

No actionable correctness or security issue above the review confidence threshold in this bounded implementation. The independent knot integration check supplements focused unit coverage; it does not establish full coupled furnace-boundary physics.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — continuous boundary design and interpolation at the hashes above, not full dynamic boundary coupling or Goal completion.
