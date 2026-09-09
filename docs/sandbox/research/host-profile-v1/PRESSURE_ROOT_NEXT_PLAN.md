# Guarded wet pressure-root acceleration — design only

No source edits, implementation, EOS calls or installation. Evidence: actual host profile attempt01 gives identical selected outputs for profiled/repeated calls, unprofiled ~.806s,320 liquid trial calls; _transaction self time .711s within .888s profiled call. This supports reducing repeated guarded native calls as a candidate. It does NOT justify skipping transactions/source checks or predict an event-run speedup.

## Preserve the current contract

Actual rigid_water_gas.PressurePolicy has volume_tolerance_m3, pressure_tolerance_pa, maximum_iterations. Add only an explicit trailing numerical strategy defaulting to 'bisection'; opt-in name proposed 'guarded_liquid_endpoint_interpolation_v1'. Default branch must retain the existing endpoint/trial arithmetic, midpoint order, counts, finish behavior and metadata exactly. Do not redirect existing policies automatically.

Current wet closure is F(P)=V_liquid(T,P)+Ng R T/P−V_available. Initial endpoints are actually evaluated; flo>=0>=fhi is required. Existing water source/config transactions and stable-liquid checks stay on every native call. Every new evaluated point must satisfy fhi<=f<=flo against the current retained bracket. Preserve original unresolvable-pressure/domain checks and all finish tests: open positive gas volume, representability allowances, volume and pressure residuals and partial pressure sum. A successful interpolation residual alone NEVER replaces the original **pressure bracket width** gate.

## Narrow candidate, before general Brent complexity

Use retained endpoint liquid volumes to propose tighter *trial points*, not to assert a certified bracket without evaluation. At a root, P=NgRT/(V−V_liquid). If liquid volume were exactly constant, both endpoint-liquid proposals would coincide at the exact analytical pressure. For the actual weakly compressible wet state they may bracket a much smaller interval; this is a performance hypothesis, not an assumed guarantee.

At each acceleration round:
1. From currently evaluated lo/hi and vl_lo/vl_hi, form proposals NRT/(V−vl_hi), NRT/(V−vl_lo) only when both denominators are finite/positive. Use overflow-safe/exact represented-input arithmetic to generate finite candidate floats, then select only strictly interior, distinct representable points. Outward neighboring floats may be proposed around a repeated estimate to obtain opposite signs, but remain merely trials.
2. Actually evaluate each proposed point through the unchanged trial/water path. Validate current-bracket monotonic ordering; use the ACTUAL sign to update exactly one endpoint. A proposed point outside the latest bracket is discarded without native work. A sign inconsistent with the current bracket, provider failure or nonfinite result remains structured failure; do not catch and retry as if harmless interpolation rejection.
3. If proposals are unusable or fail to give a prescribed geometric contraction, use original midpoint bisection. Guarantee a bisection at least after each bounded acceleration round that did not halve bracket width. Retain endpoint vl with its matching p/f; no stale cross-endpoint mix.
4. Only after the retained bracket satisfies the original width test, evaluate the same midpoint-style final candidate and call the unchanged finish function. Actual numerical endpoint F==0 special handling must retain the old finish checks and metadata; nearzero is not exactzero. Record endpoints and all trials before returning/failing.

This costs at most two acceleration proposals plus a fallback midpoint per round; importantly, maximum_iterations must continue to cap actual interior trial evaluations, not rounds, so opt-in cannot triple the native budget silently. Initial two endpoint calls retain their old accounting. Count final midpoint against that budget. A two-point proposal that consumes remaining budget without achieving original gates fails honestly. Do not introduce unbounded nextafter search.

If measured endpoint proposals do not reduce calls, consider safeguarded secant/inverse quadratic interpolation in reciprocal pressure as a separate candidate. Standard secant/Brent residual progress alone can leave one endpoint far away; the mandatory width gate means conventional 'root located' claims are insufficient. A textbook name is not evidence that the exact represented finite bracket and original gate are satisfied.

## Evidence and state fields

Retain pressure_bracket_pa as the original physical domain and final_numerical_pressure_bracket_pa / final_bracket_volume_residuals_m3 as the actual numerical enclosure, explicitly excluding EOS error. Add opt-in immutable diagnostic rows containing trial index, proposal kind, represented P/hex, before bracket/residuals, evaluated vl/f, after bracket/residuals, accepted sign update and any fallback reason. No fabricated residual0, fitted extrapolated endpoint or clipped pressure.

Existing independent source/volume pressure-error envelopes remain unchanged. The method changes the evaluated temperatures/pressures sequence through nested inverse calls and can change returned rounding, so it is a numerical strategy with a new implementation identity, not bit-identical physics outputs by assertion. Pure dry analytic branch must retain exact old behavior. New policy belongs in source/model identity, case schema and trace. Mutation checks and continuation must refuse policy changes mid-run.

## No-EOS tests before native

Use explicit manufactured monotone liquid functions and independently solved rational/Decimal roots. Preserve all old bisection tests and add:
- Constant-liquid root where endpoint estimates coincide, root near each boundary, exact initial numerical endpoint root, and pure-gas parity.
- Strongly compressible monotone liquid and highly curved monotone examples where proposals are poor; actual sign bracket remains valid, fallback terminates within original counted budget or returns structured limit failure.
- False-position endpoint stagnation: tiny residual while the other endpoint is distant must not pass width gate.
- Cancellation/rounding adversaries: P candidates round onto an endpoint, equal proposal floats, insufficient ULP resolution, cancellation in V−vl, narrow residual budget, exactzero whose finish residual fails.
- Nonmonotone sampled liquid, changed provider/source, native exception on second proposal: no accepted root, full prior bracket and attempted-call evidence preserved. No skipped native guard.
- Full trial-ledger audit: strict in-bracket trial P, monotonic sample consistency, true endpoint replacement sign, nested brackets, endpoint vl/f association, original width plus finish residual gates and exact evaluation counts. Independent root must remain inside every maintained bracket for the manufactured cases.

These tests establish numerical behavior under their explicit analytic providers, not real water correctness.

## Bounded native probe after independent review

Use the exact accepted wet state1 and input/runtime binding from brick-host-profile-v1, no physical edits. First collect baseline per-closure bracket/iteration/call counts from saved records if sufficient; do not rerun a full event just to obtain them. Then one original-strategy host evaluation and one opt-in host evaluation at the identical state, under a root-owned40s external limit, no concurrent EOS. Preserve full original source packages, unchanged tolerances, full trial records, failure artifacts and source identities. Profile overhead must be separately labelled.

Compare native call counts and wall/CPU, actual final sign brackets/widths, residuals, unchanged independent uncertainty bounds, returned N/E input identity and full thermo/mechanical output differences using original bounds. The old and new numerical brackets need not match bitwise; both must independently satisfy the original gates. Do not choose a looser case after failure. No claim of speedup until measured, and no speedup claim based on one profiled versus one unprofiled call.

## Revalidation boundary

A successful point probe permits candidate review, not global event acceptance. Next re-run representative wet/near-depletion/dry closure cases with original domains and actual source guard failures; then nested total-E inverse tests, actual paired pressure comparison, two-successive plus independent-finer event gates, correction budgets, source/mode transition, and accepted-prefix cancellation/resume. Historical default runs retain default policy. New event case is an explicit new numerical-policy run; preserve old failure records and compare full ledgers under original thresholds.

Spatial convergence remains unproved. Reduced pressure-root calls may improve feasibility, but longer-time physical events, temperature/kinetics/stretch domains and unresolved initial layers still control the next spatial study. Forecast costs only after actual closure-call reductions and event counts are measured.

## Additional measured localization evidence

Root read actual call1-output: both final mechanical solves report38 iterations; final pressures41582.265117431234 and41721.82029400574 Pa, final numerical width approximately7.2032e-6 Pa. Eight thermal forward evaluations account for320 pressure trials, matching8×(2 endpoints+38 midpoint evaluations). This is consistent with the explicit original bisection width demand from a broad bracket. The candidate target is reducing actual root-localization calls while preserving that demand, not deleting hash checks. These observed counts do not establish that endpoint interpolation will succeed; the guarded point experiment must measure it.
