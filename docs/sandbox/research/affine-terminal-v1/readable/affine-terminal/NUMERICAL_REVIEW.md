# Affine terminal candidate: independent numerical review

Interim static review of live implementation, not frozen release approval. No EOS, tests, model imports or production modifications. Existing git diff was inspected; stdlib AST parsing passed. Files are actively being implemented by their owners, so this report records the observed snapshot rather than assuming a final hash.

Observed SHA256:
- depletion_integration.py: 46e9f168fc81c43e55b6418c0cefa72b27cc080ec95997e9169c619fdf417ee0
- depletion_roundoff.py: 8ee6d7253397af8d4d28edf52198b0b041fdc341ee3a6f9e49c6ee7788270fec
- affine_depletion_clock.py: 0475e625120811a457dd4bb21e03c262d7fcf9986ecfe7afc28683ac765f242a

## Correct numerical structure

The predictor uses hm=Fraction(represented_midpoint)-Fraction(start), and integral coefficients use that same hm. Initial/midpoint samples form h*r0+h^2*(rm-r0)/(2hm) for all face, reaction and energy fields; named components use the same formula with explicit exact-to-float rounding terms. Predictor and endpoint state reconstruction accumulate rounded ledger fields with Fraction sums. Midpoint evaluate goes through observe(...,'terminal'), charging actual attempted source work; it remains a speculative state rather than an accepted panel.

Each inventory's exact reconstructed polynomial is checked at both endpoints and its interior convex minimum. Competing existing liquid that touches zero at these minima is rejected. Endpoint rounding is independently checked by advance(), retaining nonnegative stored inventories. This correctly addresses interior negative dips hidden by positive endpoints.

Gross evaporation uses the SIGNED phase-transfer samples, an exact rational zero and piecewise integral of the positive part. Conversion is downward when necessary, so the correction-fraction budget is not loosened. Signed state ledgers are not clamped. This is consistent positive-gross accounting for the declared affine approximation.

The clock module checks exact per-term integrated values, validates starting inventory, negative derivative and first crossing, and locates the greatest binary64 endpoint with nonnegative polynomial using bounded float-bit search. The returned evidence is validated by the locator even when no positive remainder requires writeback. The event retains clock, predictor and both observations even without a correction record. event_time_rounding_s is a conservative bound, not an invented exact quadratic-root value. The roundoff union keeps the original Euler branch and original correction budgets, maps affine certificate errors, and does not grant extra unverified inventory tolerance.

The speculative path owns any provisional totals and phase switch; main state commits only after original terminal and independent comparisons. Midpoint source/energy identity and final pre-switch binding checks are present. Error propagation is preserved; affine ValueError subclasses reach the existing failed-result boundary. No extra reaction, latent or composition heat appears.

## Actionable integration issues

[MEDIUM] Validate the whole wet predictor domain before sampling
File: src/sludge_sandbox/depletion_integration.py:affine_terminal
Issue: The observed snapshot requires positive target liquid only. Another cell with existing_liquid mode can have zero predictor inventory and still be passed to the wet observation before the later full-polynomial check. Also the represented midpoint is checked against the 2*tau upper bound, but not explicitly against the original Euler crossing.
Fix: Before observe(), require all existing-liquid predictor cells to be strictly positive and Fraction(midpoint)<Fraction(start)+tau. Reject unrepresentable/invalid predictor stages before invoking a phase-domain-incompatible callback. Add boundary tests that verify no midpoint callback is attempted on such a state. This is an early domain-defense gap, not evidence of a silently committed bad event in a saved run.

[MEDIUM] Persist and bind numerical terminal method explicitly
File: src/sludge_sandbox/depletion_integration.py:spine_binding / DepletionResult
Issue: terminal_method is an explicit policy field, but the observed cache binding omits it and failed run diagnostics before an event do not directly identify it. Successful event evidence identifies affine execution only after the fact.
Fix: Include the selected method in event-local binding and result/refinement execution diagnostics, preserving Euler defaults/old record compatibility. Keep this numerical identity distinct from the physical material energy identity. Ordinary segments do not themselves depend on terminal quadrature, but explicit binding prevents policy changes from silently reinterpreting one event attempt.

## Required independent integration evidence

The initial integration tests cover constant/affine sink analytic roots, reaction inventory, evaluation cost, independent approach pass and midpoint failure. At review time they do not establish the following new-path edges: positive-endpoint/negative-vertex rejection; competing liquid touch and near-event separation; signed phase-transfer sign reversal gross integral; named-component exact rounding under differing midpoint power; source mutation/cancellation during midpoint with no committed event; an independently biased approach still failing under affine mode; smooth nonlinear convergence rather than affine exactness alone. Root is preparing additional tests; no results are inferred here.

The existing dry check still guards successive events at actual dry observations/stages. A test should additionally challenge a competing affine liquid root near the selected event while its old Euler estimate was separated, ensuring event ordering is not assumed from the initial candidate alone.

Root search is bounded to 64 rational polynomial evaluations; no EOS is performed inside. Cancellation is currently checked immediately around this bounded work, not at each bisection. That is a limited latency bound rather than an unbounded wait. Future API expansion must not silently make this loop unbounded.

No high/critical arithmetic or ledger defect identified in the observed snapshot. Final approval awaits the owner's stabilized integration snapshot, closure/disposition of the two issues, and actual independent no-EOS results. Native wet completion remains a separate validation gate.

## Independent clock-module follow-up

Reviewed clock source SHA 0475e625120811a457dd4bb21e03c262d7fcf9986ecfe7afc28683ac765f242a and clock tests SHA 161a2900c10bbec9c9a48f1751219e065ee274f7a34ec979b04e5207a8495bd7. The current property event_time_rounding_s independently calls inventory_residual before reporting any bound, so a manually forged endpoint cannot obtain an unvalidated clock allowance merely by accessing the property. Positive initial inventory, exact represented hm, per-component shape/integral checks and immutable inventory equality are enforced.

The float-bit search maintains a monotone first-root predicate on a finite bracket; the original amount is positive and derivative is strictly negative throughout the enclosure, and the upper polynomial is nonpositive. Sixty-four bounded iterations suffice over the ordered binary64 integer span. Exact roots yield zero rounding bound; otherwise the endpoint must be the greatest representable value below the root, its next neighbor must be strictly beyond the root, and the original time budget is checked by exact polynomial evaluation. This justifies min(time_budget, neighbor_gap) as an upper gap bound.

Independent tests use 100-digit Decimal roots for accelerating/decelerating quadratic cases, exact Fraction tests for large origins, cancelling-term forgery, skipped exact neighbor roots, invalid enclosures and actual represented midpoint spacing. Read saved first-tests.xml: 21 pass; second-tests.xml: 24 pass, no failures/errors. These are worker-run existing results; no reviewer execution. No blocking issue found in this clock module. The interim integration observations above remain separate pending owner changes and additional integration evidence.

## Stabilized integration/source-guard follow-up

Reviewed integration SHA 4bea596f4a2b9dcd5d04aa398fa28a80ca5efa6c80e67fc93235f8f822edb220; roundoff and clock hashes remain as above. Guard tests SHA 4748539c668a2227cd4778cab303942ca664449fd126644d64692bde8af27e3e; integration tests SHA 6c59a2b45e5a899dbc36999133d6824d829b5275e07ce2cd60c1439a1c2ca104.

Both MEDIUM implementation findings are CLOSED: midpoint must be before the exact Euler crossing, every existing-liquid predictor remains strictly wet, terminal_method is strictly validated as a string, included in source/spine bindings and exposed in DepletionResult. The final switch and event observation additionally recheck the ORIGINAL operator binding. Affine mode now retains a root binding even without NestedApproachPolicy and rechecks it before commit and common-time replan. This closes late mutation after constructing a replacement operator while preserving default Euler behavior.

Cross-reviewed test_affine_depletion_guards.py. It first executes a no-fault synthetic baseline to count actual final switch/comparison boundaries, then faults the last actual boundary, not a guessed early call. It covers source_ids and deterministic_contract mutation across no-nesting, uncached nesting and cached nesting. It requires failure and complete ledger/operator rollback. Midpoint cancellation is triggered only after one actual wet evaluation, checks exact evaluation counts and uncommitted totals. Malformed method types are rejected. Saved guards/first-tests.xml contains 21 tests, no errors/failures; reviewer did not execute them.

Actual retained integration evidence must be read accurately:
- First integration XML: 29 cases, two failures; root diagnosed global ordinary reaction error, while local terminal error was about 4e-15. Subsequent stricter ordinary relative tolerance does not weaken the event or endpoint oracle.
- Third integration XML: five cases pass.
- Second integration XML: four failures are unresolvable_stage_time at the historical .005 knot schedule. That behavior is retained and uncorrected, and must remain visible as a known limitation, not be silently deleted from validation claims.
- Nonlinear integration XML: six cases, one failure.
- The currently present nonlinear-strict-tests.xml ALSO has six cases/one failure, specifically numerical_failure/unresolvable_amount_increment. Tightening the ordinary test accuracy is reasonable for isolating terminal error, but this saved attempt is not a successful nonlinear-oracle result.

Code review finds no new blocking arithmetic/ledger/source-binding defect in this snapshot. Readiness for a bounded native experiment is CONDITIONAL on completing and reviewing the remaining independent integration checks, particularly a passing nonlinear event/energy oracle or a precisely scoped alternate fixture that isolates its numerical resolution failure without weakening event gates. Full-panel interior-negative and signed-gross-crossing tests remain important new-code boundary evidence. Do not equate affine exactness, source-guard success, or the five passing initial tests with completion of that coverage. The .005 knot failure remains explicitly retained even if an unrelated native fixture is later run.

## Frozen final review and bounded native readiness

Final source hashes:
- depletion_integration.py: bb8c9c04a595c22d187d2b9858ca4607622e52955f165f089b3e33bedfaa89f3
- depletion_roundoff.py: 8ee6d7253397af8d4d28edf52198b0b041fdc341ee3a6f9e49c6ee7788270fec
- affine_depletion_clock.py: 0475e625120811a457dd4bb21e03c262d7fcf9986ecfe7afc28683ac765f242a

Final test hashes:
- test_affine_depletion_integration.py: b5f9661c77ecf3ccd888e3ba5bd900b8b294e180e4f08fbaf64be34df2a2bb6f
- test_affine_depletion_guards.py: 4748539c668a2227cd4778cab303942ca664449fd126644d64692bde8af27e3e
- test_affine_depletion_clock.py: 161a2900c10bbec9c9a48f1751219e065ee274f7a34ec979b04e5207a8495bd7

All six files parse. The final change extracts the existing exact polynomial minimum and positive-affine-integral calculations into two pure helpers used directly by production. Four independent analytic minima cover an interior touch, a negative interior with positive endpoints, concavity and a linear crossing. Four exact gross-area cases cover both sign reversal directions, wholly negative and constant positive transfer. The callers still supply Fraction coefficients, reject negative/competing-zero minima and round gross downward. Extraction changes no formula or physical gate.

Read nonlinear-resolvable-tests.xml: six tests, zero failures/errors/skips, 2.565 s. Its test-only ordinary amount tolerance is 1e-14 and relative tolerance 1e-13; independent event/energy assertions and event gates remain unchanged. This supplies the formerly missing nonlinear sink/time-dependent-work evidence. Earlier over-strict unresolvable increment failures and the historical .005 knot failures remain preserved and are not relabelled as passes.

Read related-final-tests.xml after root's terminal notification: 99 tests, zero failures/errors/skips, 34.213 s. The new 24 clock + 14 integration + 21 guard tests account for 59 of these; the rest exercise existing related behavior. Reviewer performed no tests/EOS. The nonlinear and pure-helper additions close the outstanding evidence requirements for this bounded candidate stage. These tests do not establish universal continuous-domain admissibility or replace physical validation.

FINAL DECISION: APPROVE this frozen source candidate for the next bounded v5 native experiment after installed/source byte identity is verified and its fresh script/PLAN delta is independently reviewed. Keep v4 physical inputs, source assets/uncertainties, inverse/event/comparison gates and 120/150 s limits unchanged; the only intended opt-in numerical change is terminal_method='affine_midpoint'. This approval does not claim that unseen v5 scripts are correct, that native depletion succeeds, or that the known historical knot limitation has been fixed. No blocking numerical/source/ledger finding remains in the reviewed scope.
