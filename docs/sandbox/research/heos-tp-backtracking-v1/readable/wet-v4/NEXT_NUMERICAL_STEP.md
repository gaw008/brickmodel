# Saved v4 failure: next bounded numerical subtask

Read-only diagnosis from depletion-result-0.json and current depletion_integration.py. No EOS, imports of model code, tests, or production changes. Full-suite execution is left untouched.

## Actual failure location

This is not failure to obtain two consecutive terminal comparisons. Levels 4 and 5 already pass all five original comparison gates. The run reaches 365 evaluations, 44 attempted panels and 120.127148125 s, with six globally committed ordinary steps and no committed event. It then times out inside the mandatory independent-halved-controls approach, before that branch reaches its terminal panel, dry continuation or comparison. No TP convergence failure appears in this result.

The independent branch alone spends 49.370028459 s / 122 evaluations / 13 approach panels. Its terminal, dry and comparison counts are all zero. Its failure cannot be relabelled as an independent comparison failure, nor may the original branch be committed without this independent check.

Original terminal refinement data:

| Level | Event amount difference mol | Common-time amount difference mol | Status |
|---|---:|---:|---|
| 1 | 5.579376084445943e-9 | 1.0068168521115695e-11 | fail |
| 2 | 1.7686775075932953e-9 | 3.1941116418465754e-12 | fail |
| 3 | 6.737170821224936e-10 | 1.2171680763978232e-12 | fail |
| 4 | 9.97847847712262e-11 | 1.8052226380405045e-13 | pass |
| 5 | 3.797651082493303e-11 | 6.863563536962936e-14 | pass |

The only failing metric in levels 1–3 is event inventory difference, dominated by A/B, against 1e-10 mol. At those levels time, energy, temperature and pressure all already pass. A/B discrepancies are approximately 0.1996 mol/s times event-time discrepancies: different event timestamps along the active reaction cause the event-state mismatch. Common-time reaction inventories are much closer. This supports improving event-time accuracy, not deleting the event-state gate. Pressure uncertainty is now about 0.0048 Pa in the final comparisons, far below the unchanged 1 Pa gate.

## Why the independent branch costs so much

proposal() advances ordinary wet panels by min(ordinary_cap, remaining common horizon, safe_fraction*tau), until tau<=terminal_cap. At level 5 the threshold is 1.59887950451403e-6 s, starting from tau about 5.116414414444896e-5 s. The independent branch halves both ordinary cap and actual safety fraction to 0.125; here the inventory fraction, not the maximum step cap, controls the approach. For a locally constant sink, tau contracts by approximately 0.875 per panel. Reducing tau by about 32 therefore requires about ceil(log(1/32)/log(0.875))=26 panels. The saved partial independent branch has only completed 13. This is a cost estimate explaining the observed failure, not an assertion of unseen states or exact eventual cost.

Total actual phase costs are ordinary 55, approach 240, terminal 6, dry 54 and comparison 10 evaluations. The existing ordinary-spine cache already reports 32 observation and 27 panel reuses. Reusing the original spine as the independent branch would invalidate the independent-error check. Increasing budgets or removing that check would avoid rather than solve the problem.

## Recommended next implementation: opt-in second-order terminal event panel

Scope the next change to terminal event construction and its clock evidence; preserve default Euler behavior and every current comparison, independent-mesh, source, physical, rollback and resource gate. Do not begin another broad mechanics/chemistry redesign. The target is to achieve accurate event times at larger terminal caps, reducing both main refinement levels and the length of the independent geometric approach.

A concrete candidate is an explicit midpoint-based affine rate reconstruction:

1. From the current wet state and observation, compute the existing Euler depletion estimate tau0. Build a conservative predictor at hmid=tau0/2 using the existing rate fields and exact Fraction ledger arithmetic. Require every inventory nonnegative, target liquid strictly positive, correct energy/source/geometry binding, representable interior time and no competing event. Evaluate exactly one additional wet observation at that predictor/time.
2. For each face, reaction, energy and named power component use the same affine-in-time rate reconstruction between initial and midpoint rates. Its integral is I(h)=h*f0+h*h*(fm-f0)/(2*hmid). The midpoint state predictor has second-order local state error, giving a second-order event-panel method under smooth rate assumptions. This is not a validated physical interpolation outside the source model: both rate samples remain actual source-qualified evaluations, and existing successive/independent comparisons remain mandatory.
3. Locate the first positive zero of the target liquid polynomial using a bounded safeguarded calculation. Require a unique decreasing crossing in a preregistered small interval, for example 0<h<=2*tau0 and before the common-time horizon, with strictly negative liquid derivative throughout the chosen enclosure. Degenerate, nonmonotone, unresolved or competing crossings must fail explicitly. Do not silently fall back or extend the interval. Cancellation/resource checks apply before the additional observation and during bounded root refinement.
4. Integrate ALL inventories and ALL energy/component ledgers at the same selected representable endpoint. No independent adjustment of event time, reaction amounts or energy is allowed. Record predictor/rate samples, coefficient provenance, chosen clock bracket, integrated fields and component roundoff. Preserve the existing small phase/storage correction budgets and retain the actual correction separately.

The clock change is essential: current DepletionClockEvidence proves a constant-rate Euler crossing using rate terms and exact Fraction(t)+tau. Reusing that object with a quadratic crossing would be false evidence. Introduce a separate narrowly typed affine-rate clock certificate containing exact rational coefficients from observed binary values and a rational bracket of the first root. Use exact polynomial/derivative checks at rational endpoints, choose a floating endpoint at/before the lower certified root boundary, and bound the unresolved time by the upper boundary minus chosen endpoint. A finite binary64 search or bounded rational bisection can certify this without claiming an irrational root is exact. Require the remaining liquid correction to pass all original budgets. If rounding cannot establish a usable positive-time bracket, fail; do not label residual inventory as roundoff by assertion.

This extra wet observation per terminal panel is a deliberate small cost in exchange for potentially eliminating several levels of geometric approach. It is plausible from the saved event-time-dominated errors, not yet proven to fit 120 s. Keep the 120/150 s budgets and treat the next unchanged wet replay as the performance test.

## Independent tests before any native replay

- Constant sink and linear-in-time sink with analytic event root and a separate A-to-B reaction oracle; compare actual event A/B amounts as well as common-time amounts. Derive the oracle outside candidate helpers.
- Smooth nonlinear sink with an independent analytic or high-accuracy numerical oracle: verify refinement reduces event-time and event-inventory error at the expected order. Do not infer accuracy only from adjacent agreeing candidates.
- Independently forced shared approach bias must still fail the existing halved-control comparison. Cache sharing between independent/main paths remains forbidden.
- Exact affine clock sign/monotonicity certification, nearly degenerate quadratic, no positive root, two roots, nonmonotone derivative, unrepresentable time, source/native failure at midpoint, and competing inventory depletion.
- Closed species/energy ledgers, identical weights for named components, no duplicate reaction/latent power, unchanged phase-roundoff budgets, cancellation and failed speculative paths cannot commit.
- Deterministic synthetic evaluation-count comparison at the original amount gate demonstrating that the higher-order panel reduces total original-plus-independent approach work, including its extra observation. Do not optimize only the terminal call count.

The smallest meaningful next deliverable is that opt-in affine terminal panel plus a truthful clock certificate and these independent controls. Native validation should then use the same frozen v4 physical fixture/gates in a fresh preregistered attempt after the live full suite terminates. Neither this report nor the saved partial run establishes completed wet depletion.
