# Affine terminal integration: independent design review

Preparation-only review of current depletion_integration.py and depletion_roundoff.py and archived NEXT_NUMERICAL_STEP.md. No EOS, tests, provider import or production edits. Root owns integration/roundoff wiring; clock worker owns the new certificate. This report approves a design contract, not an unseen implementation.

## Represented midpoint and second-order scope

Let the initial time be binary64 t0, initial Euler depletion estimate tau0 a Fraction, and represented midpoint tm near t0+tau0/2. Require t0<tm and hm=Fraction(tm)-Fraction(t0)>0, with tm strictly before the initial Euler crossing. Use that ACTUAL hm for the predictor, slope denominator and clock certificate, never nominal float(tau0)/2. Construct the Euler predictor by exact accumulation of each face/reaction/energy term then one state rounding. Every predictor inventory must be nonnegative; target liquid and every other existing liquid must remain strictly positive. Preserve energy identity. Run the actual wet operator through observe() at tm, so current geometry/storage/reaction bindings and source qualifications are re-evaluated at the predictor, rather than manually reusing initial storage.

For any rate field f, with actual samples f0/fm, set b=(Fraction(fm)-Fraction(f0))/hm. Integrate J(h)=h*f0+h*h*b/2. Every face species, face energy, reaction species, total power and named power component uses the SAME h and hm. Component schema must match at both observations; reject missing/mismatched labels. Use exact Fraction values before each prescribed float ledger conversion, and retain exact component rounding terms against J(h), replacing the old interval*rate formula. No separate reaction, latent or composition heat may be added.

Under smooth rates, this midpoint predictor/affine integral is second-order accurate locally; the polynomial is a numerical approximation, not a certified continuous solution of the real EOS dynamics. Existing two terminal passes and independent halved-approach comparison remain required to reject false agreement or approach bias.

## Inventory admissibility throughout the polynomial panel

For every cell/species, form q(s)=N0+a*s+c*s*s from the exact sum of the signed face and reaction coefficients. For 0<=s<=h check q(0), q(h), and q(-a/(2*c)) when c>0 and the vertex lies strictly inside. Use exact Fraction comparisons. Endpoints alone miss a negative dip followed by recovery. For c<=0 the minimum is at an endpoint.

Target liquid needs the clock's strictly decreasing, first-root proof; choose endpoint at or before that root. Every competing existing liquid must remain STRICTLY positive over the panel, including vertex equality, to prevent silently crossing another phase event or touching zero and reappearing. Any competing clock within the original event-time separation tolerance should remain unsupported, not silently resolved by picking one cell. Non-liquid inventories must remain nonnegative throughout. A positive polynomial does not by itself guarantee rounded ledger endpoint positivity: separately validate the actual stored endpoint, preserving current roundoff/negative-state guards.

The physical thermal/source envelope still must hold at all actual evaluated predictor/event states; do not invent a guarantee for an unobserved continuous path. This limitation is precisely why refinement/independent validation remains necessary.

## Gross positive evaporation with possible sign reversal

Current observe() copies cell_transfers[i].rate_mol_s into evaporation_mol_s: it is SIGNED, not pre-clipped positive gross transfer. Affine phase transfer e(s)=e0+b*s must use the same represented hm. Define positive gross G(h)=integral_0^h max(e(s),0) ds exactly for the numerical rate reconstruction.

For b=0 use h*max(e0,0). Otherwise locate the exact rational zero z=-e0/b; split [0,h] at z only if 0<z<h. On each of the at most two intervals, test the exact sign at its midpoint and, if positive, add e0*(right-left)+b*(right*right-left*left)/2. Endpoint zeros contribute no area. This handles positive-to-negative and negative-to-positive cases without extra EOS calls. Clipping the two samples first and then interpolating changes the function and can overstate permitted correction; net signed integral can understate gross and is a different quantity.

Gross G is ONLY the correction-fraction denominator/accounting field. State/energy transfer ledgers continue integrating the signed original rate. Do not replace their rates by max(e,0). Convert G to a finite nonnegative float conservatively at or below its exact rational value (nextafter down only if float(G)>G), because the existing test delta<=positive_evaporated*correction_fraction would otherwise be fractionally relaxed by upward rounding. Exact zero gross cannot authorize a positive correction. If the implementation chooses not to support phase-rate sign reversals yet, reject them explicitly before committing; do not silently mix net and gross semantics. A first bounded implementation may restrict the domain, but this must be declared and tested.

## Certificate, representation and integration API

The certificate must bind initial time, represented midpoint, represented endpoint, both actual signed LIQUID RATE TERMS (left face, negative right face, reaction) and any bounded root interval. inventory_residual(start,terms) must check each supplied panel term equals float of its corresponding exact affine integral, not merely equality of the net sum: net-only validation can hide altered cancelling ledgers. Its validated initial amount comes from writeback, never an unverified separate caller value. Arrays/term tuples must be immutable detached values.

Prove first positive root and decreasing liquid polynomial over the certified interval using exact rational signs/derivative bounds. Choose the nearest representable endpoint at or below the root, or otherwise explicitly bound its downward time gap with the original time budget. Do not pass nominal tau0 or constant-rate clock evidence to the affine panel. Bound the unresolved inventory by the validated polynomial residual at the endpoint; do not use a caller-chosen amount tolerance. The old clock path and old serialized records must continue to validate unchanged.

The event's event_time_rounding_s must reflect the conservative certified upper bound from root to represented endpoint, including exact-root endpoint cases; assigning zero to an uncomputed quadratic root would corrupt comparison(). Liquid residue correction must still satisfy original ULP+clock residual, absolute, evaporation-fraction, species/element/mass and cumulative budgets. Actual rounded endpoint and exact polynomial residual are distinct, handled by the existing ULP part plus truthful clock allowance.

## Policy identity, costs and transaction boundaries

Use an explicit frozen opt-in terminal method/policy with validated method identifier; default remains old Euler. Preserve all existing numerical tolerance values and resource limits. Record the chosen method in run/refinement diagnostics. Bind the method and its fixed root-work parameters into any event-local cache identity that depends on terminal semantics; do not silently reuse cached results after policy mutation. Physical energy/source identity should not be misrepresented as a new material definition solely because the numerical method changes, but the saved execution identity must expose the method.

The midpoint is a speculative stage, never an accepted panel or main path state. Its single observation must go through observe(...,phase='terminal') so evaluations are charged even on source/native failure. Root search uses a bounded number of exact operations and guard/cancellation checks; no provider calls inside bisection. Run guard before/after midpoint evaluation and before writing/switching the final phase. Do not increment committed panel totals for a predictor. On failure retain attempted cost and diagnostic input state while leaving committed inventory/operator/roundoff totals unchanged. Any approach-spine terminal/dry result remains noncacheable; independent-halved branch must remain independent.

## Independent integration checks required

Constant-rate parity with old Euler; analytic affine sink/event root and independent reaction inventory/energy oracle; nonlinear smooth refinement order; exact same represented hm in predictor and every integral; interior-negative quadratic with positive endpoints rejected; competing liquid touch/root rejected; signed evaporation crossings compared with hand-derived rational positive areas; root and float-neighbor sign tests; altered cancelling per-term clock evidence rejected; component sum residual accounting; midpoint source/domain/cancel failure with charged evaluation and no commit; unchanged false-convergence rejection from an independently biased approach. Performance evidence must count original AND independent approach plus extra midpoint observations, not just terminal panel calls.

No successful affine implementation or native wet completion is claimed here.
