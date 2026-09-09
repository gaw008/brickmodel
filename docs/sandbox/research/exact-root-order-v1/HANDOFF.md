# Complete numerical affine root-order candidate

Frozen source SHA256 38a4f6b0bdbe6044e4a927e4c473ec295bbd1563e3dfcb05867287a879817142.
Frozen tests SHA256 53165570c22ce0bf5ca19d5a7494dd2b7ba2b0644f9989b668d05eac6ae0765a.
Temporary directory only; no repository edits, EOS, installation, or mode changes.

`order_exact_affine_roots(state, first, midpoint_rates, *, start, midpoint, upper, liquid_index, wet_cells, evaporation_start_mol_s, evaporation_mid_mol_s, source_binding, time_absolute_s, policy, maximum_refinements=256)` returns frozen ExactRootOrder(selected_cell, candidates, exclusions, wet_cells, input_sha256, refinement_level, qualification).

All times are ExactEventTime, all cells share actual input state and Rates arrays and exact domain. The wet-cell tuple must exactly equal all cells with positive initial liquid inventory, in index order. Initial derivatives undergo the existing guard; midpoint shape/schema is checked without incorrectly applying its derivatives to the original state. Full arrays, E/stretch, components, evaporation observations, clocks, source labels and policies enter a SHA256 input binding. `verify_exact_root_order` recomputes the complete pure result against supplied inputs; a user-constructed public dataclass is not trusted.

For every wet cell the exact inventory polynomial includes separately signed left face, negative right face, and source components. Its whole-domain minimum includes a convex interior vertex. A strictly positive minimum produces an explicit NoRootEvidence with all coefficients, domain and minimum. Any remaining candidate must admit the existing strict monotone first-root sample contract; a possible zero with nonmonotone behavior is explicitly unsupported, never silently excluded.

Candidate enclosures refine on the same dyadic domain grid, using Fraction exclusively. A cell is selected only when its upper bound is strictly below every other lower bound AND every retained candidate satisfies original ExactAffineEvidence time/local/absolute/fraction gates. This latter all-candidate budget requirement is intentionally conservative and may refuse even when only the selected cell would otherwise be ready. No new scientific tolerance is introduced, and the original time gate is not used as minimum event separation.

Exact polynomial Euclidean gcd identifies common roots for strictly decreasing positive-start polynomials. Equal earliest roots are unsupported; equal later roots do not prevent accepting a proven earlier distinct candidate. Coincidence/refinement-budget failures retain immutable diagnostic tuples of the input digest, wet set, exclusions and every raw candidate bound/sample. Those failure bounds are explicitly not accepted ExactAffineEvidence. A no-root result carries its complete exclusions in the exception diagnostic. Invalid input or a nonmonotone possible crossing returns an error, not a fabricated complete proof.

Actual command: `PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest /private/tmp/brick-exact-root-order-v1/test_exact_root_order.py -q`. tests01 passed nine tests; tests02 passed eleven. No failed test run omitted. Tests cover tangent ties split by acceleration, exact roots separated by less than 1e-8, equal roots with different initial tangent estimates, three coincident roots, later coincident competitors, convex positive exclusions, interior negative nonmonotone refusal, missing/duplicate wet-cell rejection, source/full-array/result-tamper binding, zero-liquid cells, origin translation to 10^12, no-root and finite-refinement outcomes. Decimal analytic root expectations and rational polynomial arithmetic are independent of the tested selector.

This only orders NUMERICAL AFFINE roots. Input labels/hash cannot authenticate that actual host rates were sampled; the caller must preserve real source/mode binding and the midpoint state. Before a terminal commit the separately reviewed full-state panel builder must still check ALL remaining species and mechanical polynomial minima at the selected lower endpoint and construct matching shared exact ledger/raw state. The actual mode switch, mixed continuation, complete per-event/common comparisons, two successive passes, independent approach, global cumulative audits, packet atomicity and versioned record/resume remain integration responsibilities.

Copy exact_root_order.py and permanent test only after review. conftest.py is temporary candidate loading infrastructure. Independent numerical review requested from Averroes.

## Strict record-type correction

Superseding frozen source: 1cc3b7868b5a4f6bf7f654063602cb058d984b10e59848afe0a1feb8250d69a5.
Superseding tests: b92502d5c9b5e632f6711fb6243097ed2aac112f8096eafc25be45d605ec6244.
Tesla identified that ordinary dataclass equality treated bool/int and Fraction/float as equal. before-type-fix.py preserves the reviewed numerical source. The corrected verifier compares exact Python types recursively through every dataclass field and tuple element before comparing scalar values. It does not use the input hash serializer as a type proof. The root calculation itself is unchanged.
Actual type-red.log: five failed, twelve passed. type-green.log: seventeen passed in 0.22 seconds, including nested cell IDs, wet-cell tuple, forged event-time seconds, evidence iteration/time-gate types and exclusion Fraction-to-float replacement. Tesla was asked to review these final hashes. No repository or EOS work occurred.
