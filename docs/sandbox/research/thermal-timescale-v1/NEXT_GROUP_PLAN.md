# Simultaneous depletion: bounded certificate design

Design only. No source edits or EOS. Actual current4cell initial callback completed1.790s; /private/tmp/brick-four-cell-candidate-probe-v1/attempt01/selection.json reports exact first-candidate gap0: cells2/3 N/−Ndot≈.26711293310121675ms, cells0/1≈.28317333188279605ms. This reproduces the current selector rejection condition, not a full-integrator run or proof of simultaneous true roots.

## First distinction: candidate time is not an event-time enclosure

N(t)/−Ndot(t) is a tangent estimate. Two equal estimates can lead to different roots when acceleration differs; distinct estimates can lead to the same root. Heat/gas coupling can split identical parent children, and interface mode changes alter later derivatives. An exact Fraction equality removes representation ambiguity in the estimate only. It supplies no bound on subsequent rates or event order.

Current selector rejects before an ordinary advance whenever its two smallest estimates differ by at most time_absolute_s. It is therefore conservative but can reject states whose actual events are well separated. Do not fix that by picking one sibling by index or zeroing the candidate set.

## Safe positive-inventory advance is a separate operation

A bounded pre-event advance may be permitted when every liquid inventory remains strictly positive on the ENTIRE proposed panel and all actual stage/rate/source/domain/energy/mechanical checks pass. Endpoint/stage positivity alone does not certify between-stage positivity for a general RHS. The current safety fraction based on the instantaneous rate is not a global derivative bound, so it is not by itself a proof of a safe physical panel.

Two possible declared numerical contracts:
1. Preserve current ordinary-RK semantics: a normal accepted positive-state panel may advance, with original embedded error gates and transaction ledger, then reassess candidates. Explicitly call this a numerical positive-stage advance, not certified exclusion of an unseen physical event. It may not serve as the rigorous event-order certificate requested here.
2. Stronger event exclusion: provide a source-conditioned bound on each liquid derivative over a state/time tube, so N_i(t0)−h sup(loss_i)>0 for all i; or a validated dense polynomial plus a rigorous remainder bound over the panel. Then the entire panel is certified event-free. Such bounds are not currently supplied by native phase transfer just because the initial rate is known.

For an explicitly affine manufactured liquid-rate model, the exact quadratic inventory polynomial can be checked positive throughout [0,h] by endpoints and its interior stationary point; this does give a bounded pure test mechanism. It does not automatically extend to the actual wet coupled RHS. If a safe panel is unavailable, retain the original unsupported outcome rather than crossing an uncertain event unnoticed.

## Group semantics: unresolved ordering, not asserted exact simultaneity

A group contains cells whose individually certified event-time intervals overlap or cannot be strictly ordered within the original time gate. Membership must be derived from certified intervals, not equal tangent estimates. Canonical serialization may sort cell indices, but numerical order must not be chosen from that sorting.

Let member i have root interval I_i=[l_i,u_i]. Record each interval plus group union [min l_i,max u_i]. Distinguish:
- proven same exact root, available only for explicitly certified identical/analytic cases;
- a narrow unresolved-order cluster whose union width meets the original time_absolute_s;
- unresolved wide cluster, which fails/refines.

Pairwise overlap is not enough to establish one common root; a chain of overlapping intervals can span more than the gate, and even a nonempty intersection is not proof roots coincide. Never replace the union by the intersection as a fabricated event-time bound.

## Physical mode switch and correction are not free

A single shared switch time is acceptable only under an explicit certificate bounding ALL consequences of replacing the unknown ordered events by that representative time. Choosing the earliest end can delete positive liquid; choosing the latest can integrate a wet model through negative liquid. Neither is automatically valid.

For each member, retain its terminal inventory polynomial/enclosure and a per-cell bound on liquid moved to/from the chosen shared time. This amount must independently satisfy original absolute correction, correction_fraction_evaporated using that cell's actual gross evaporation, storage/element/mass roundoff budgets, AND N/E/T/P/stretch comparisons at event and common time. A finite physical timing shift is not floating-point roundoff; if existing correction types are specifically roundoff-only, introduce a separately named bounded event-localization contribution rather than misclassify it as roundoff. No relaxation of the original gates follows from adding the field.

If those timing-displacement bounds are unavailable, a clustered one-time switch is not admitted. The rigorous fallback is to certify order, or to enclose each admissible ordering's piecewise mode evolution and show all resulting full states/ledgers agree under the original six gates. This is more expensive, but honestly exposes what a real coupled group certificate requires.

At accepted group switch, all members' liquid columns are exactly zero only AFTER their own bounded corrections are accepted. Vapor transfer is per cell with exact global water/element/mass preservation. Total energy remains the same conserved target; do not add latent heat. Full normal vector plus one common tangent is retained. Recompute the actual dry/mixed host at shared state; its inverse/domain/source checks must pass. Nonmembers remain strictly positive or are separately included by certified event intervals; never omit an earlier possible event.

## Whole-state comparison and ledger requirements

For each successive terminal refinement and independent finer approach, compare all cells at candidate event time(s) and a common later time, not only group liquid columns. Original N,E,T,P,time and stretch limits remain. Report per-member maxima and whole-state maxima, unchanged reported-T pressure qualification, original independent pressure diagnostic, and exact group time union. Require the existing two consecutive passes plus genuinely independent approach grid, with group membership stable or explicitly reconciled by enclosing all candidate members.

All source/face/work quadratures are computed once for the shared multi-cell trajectory. Group events must not duplicate terminal panel ledgers or reset cumulative component/roundoff/energy budgets. Each member correction has its own evaporation fraction and atom/mass/amount accounting; global sums include all member corrections once. A failure for one member aborts the whole speculative group, retaining only the prior accepted prefix.

## First implementable pure module (no host admission yet)

Propose isolated `depletion_group_clock.py` for explicit immutable affine inventory polynomials, not arbitrary function callbacks. Inputs: original represented start time, time domain, complete per-cell initial liquid and exact affine rate coefficients (using actual represented midpoint delta), per-cell candidate root enclosures, original time gate, and explicit cells whose rate model is certified affine for the experiment. Exact Fraction arithmetic.

Outputs: individual downward represented root/time enclosures, positive-domain intervals, canonical membership candidates, certified ordering edges (u_i<l_j), union width, and one of ordered / exact_common_root / unresolved_cluster / no_depletion / inadmissible_domain. It must NOT emit a wet-to-dry state or mutate inventory. A separate pure group-correction proposal can accept proven exact-common-root members with per-cell original roundoff evidence; general finite-width cluster switching remains unavailable without the timing-displacement proof described above.

This is small and independently testable, establishes the missing multi-root/time-interval primitives, and cannot masquerade as actual coupled wet support. Production candidate selector still rejects unsupported real clusters until full closure is supplied.

Independent analytic/adversarial tests:
- Identical initial N/r but different affine acceleration: distinct roots and possibly reversed order.
- Different initial N/r with analytically equal roots; exact common-root proof.
- Three overlapping intervals forming a long chain; do not declare common event or shrink union.
- Exact constant sinks for two cells, reversed cell-index order, one nonmember with earlier certified root.
- Positive endpoints but negative interior quadratic; reject pre-advance.
- Roots adjacent to float endpoints at a large absolute start time; outward interval and original time gate, no fake exactzero.
- One member passes global total correction but fails its local evaporation fraction; reject group.
- Simultaneous analytic evaporation with energy-reference-preserving liquid/vapor transfer and unchanged mechanical state, exact independent conservation.
- Different admissible event orderings alter a coupled cell's energy/pressure beyond gate; refuse one-time group collapse.

## Existing interfaces that must change coherently

`depletion_integration.candidate`: return a typed selection with ordered candidate or certified cluster status, preserving current default single-event behavior. No bare tuple tie-break replacement. Terminal builders must support shared vector inventory evidence and full mechanical stage positivity. `_Path`/comparison/commit carry one group trajectory and member certificates.

`DepletionEvent`/correction schema: add an explicit group record with membership, per-member root/time/correction/gross evaporation, group interval and representative-time justification. Preserve old single-cell event records and correction=None exactzero semantics. Do not encode one shared panel as several old independent events whose common states differ or whose cumulative costs double count.

`event_record`: versioned strict codec/audit, recompute all polynomial/interval/ordering/correction claims, validate all actual phase modes and source bindings, one shared panel ledger, two-pass/independent-grid gates and original budgets. Public frozen objects are not trusted merely by type. Old record audit unchanged.

Continuation/service: checkpoint only after atomic group acceptance, restore all affected modes together, preserve original full initial state and cumulative history/costs, reject policy or group-contract changes. UI/trace must disclose an unresolved-order cluster versus proven exact simultaneity; no claims from synthetic group tests about real sludge or full spatial convergence.

## Next decision

Start with pure affine multi-root primitives and adversarial tests, plus a read-only check whether existing affine terminal evidence can provide genuine per-member localization/remainder bounds for the actual cluster. If it cannot, state that missing proof explicitly. Do not run a long4/8 wet study assuming the group primitive alone solves the coupled event. The completed2cell longer-time pilot can continue independently; it does not remove the refined-grid group requirement.
