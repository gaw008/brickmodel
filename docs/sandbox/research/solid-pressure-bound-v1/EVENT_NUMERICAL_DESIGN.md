# Next event algorithm: positive-weight quadratic terminal quadrature

Read-only numerical design during the frozen installed-suite run. No source edits, imports, EOS, tests or probes. Read NEXT_EVENT_SCOPE.md and actual depletion_integration.py/depletion_roundoff.py. There is no src/sludge_sandbox/depletion_heat.py in this checkout; the Euler terminal implementation is the nested terminal() in depletion_integration.py.

## Recommendation

Implement a versioned two-stage, positive-weight quadratic terminal quadrature with a certified *discrete* root clock, then retain independent approach-cap refinement. This directly reduces the terminal discretization defect that is forcing expensive refinements. Splitting the ordinary approach cap from the terminal threshold is useful, but should not be the only accuracy change: it can reduce cost while hiding shared ordinary-RK error. Do not remove event-state comparisons, change gates or increase budgets.

The existing terminal step freezes all rates, predicts h=N_l/(-r_l), and integrates every ledger term with h times its initial rate. Its smooth variable-rate event-time defect is generally O(h^2), unlike the ordinary second-order panels. Here the fast independent A->B reaction makes an event-time difference appear as approximately 0.2*delta_t mol in A/B. Thus the 1e-10 mol amount gate can demand event times much closer than the separate 1e-7 s clock gate. The saved aggregate maximum is consistent with this mechanism but is not sufficient to identify the sole maximizing species/location; preserve decomposed diagnostics next.

## Concrete next code

### 1. Two wet stage observations, one algebraic terminal polynomial

At the current accepted wet state y0,t0, reuse the already computed complete conservative rates k0 and frozen liquid tau0. Choose an interior stage offset delta=(3/4)*tau0, bounded by the next program knot/common-time limit and by positivity for every predicted inventory. Evaluate the full *wet* host once at:

    y_delta = y0 + delta*k0
    t_delta = t0 + delta

Here k0 includes face divergence, reactions and total-energy power. Construct the stage through the same exact represented ledger/state conventions; do not invent its temperature or pressure. Require positive candidate liquid at this stage, complete nonnegative other inventories, original model identity, and successful source/domain-checked host decoding. A physically invalid predictor is a signal to take an ordinary safe approach panel and retry; it is not permission to evaluate a negative-water or artificially dry state. Infrastructure/source failures remain fatal, following current error classification.

Let k_delta be the complete rates at that stage. For any prospective terminal duration h, define all conservative quadratures using:

    Q(h) = h*k0 + h^2/(2*delta)*(k_delta-k0)
         = w0*k0 + w1*k_delta
    w1 = h^2/(2*delta),  w0 = h-w1.

Restrict 0<h<=2*delta, so both weights are nonnegative. This is a second-order explicit two-stage family: w0+w1=h and w1*delta=h^2/2. With delta=O(h), a smooth vector field has local O(h^3) defect, including an O(h^3) event-time defect for a transverse liquid zero. This statement is conditional on smoothness/transversality; it is not a source/ODE accuracy certificate near singular kinetics or a tangent event.

The liquid inventory polynomial is N_l0 + Q_liquid(h). Solve its first downward zero using exact represented Fraction polynomial evaluations and a bounded rational/dyadic bisection, not repeated EOS calls. Enforce monotone decrease of this polynomial over the root bracket (its linear derivative can be checked at the bracket endpoints). Both initial and stage phase-evaporation diagnostics must support the intended evaporation event; do not infer gross evaporation from net liquid loss. If there is no bracketed downward root before 2*delta, a competing inventory event, a breakpoint or the common-time horizon, use an ordinary safe approach panel and retry. A no-root result must never be forced into depletion.

For the common decelerating case h may exceed tau0; choosing delta=3*tau0/4 permits roots up to 1.5*tau0 while retaining positive quadrature weights. The midpoint delta=tau0/2 would restrict h<=tau0 and unnecessarily reject such events. This is why a generic midpoint-time substitution is not the proposed algorithm.

### 2. A new exact clock-evidence contract

Do not reuse DepletionClockEvidence unchanged: it explicitly certifies a frozen-rate linear root and verifies panel_term = duration*rate. Introduce a separate versioned quadratic evidence record holding t0, delta, endpoint, both sets of liquid rate components, root bracket information and time budget.

It must independently check:

- each represented liquid panel term equals the correctly rounded exact w0*r0 + w1*r_delta expression;
- the exact liquid polynomial is nonnegative at the saved downward endpoint and negative at its next representable absolute time, with a monotone decreasing derivative throughout that tiny bracket;
- the root is inside the bounded terminal search region and its time bracket is within the original clock budget;
- the returned clock inventory remainder is the exact polynomial residual at that endpoint, not an estimate of ODE/truncation error.

This extends the explicit accepted evidence type set in depletion_roundoff.py. Preserve the original local-ULP, absolute correction, evaporation fraction, accumulated element/mass/storage and nearest-vapor-writeback checks without alteration. Root-localization truncation is assessed by independent refinement; it must never be charged as roundoff correction. Handle an exactly representable polynomial root explicitly rather than treating zero residual as missing evidence.

Use the same w0,w1 for face species, face energy, reaction species, total work and every work component. Nonnegative weights preserve nonnegative dissipation when both observed stages have it. Preserve component identities and exact represented sum residuals. Compute positive-evaporation quadrature from actual phase diagnostics, separately from net source. If individual rounded liquid terms yield an invalid state, reject/refine; do not clip a negative inventory or overwrite total energy. Only after a valid represented terminal state and authorized arithmetic writeback should the interface mode switch and dry observation occur.

### 3. Separate approach and terminal refinements without false confidence

A terminal threshold should determine when the terminal polynomial is attempted. Ordinary approach panels should remain controlled by normal RK local tolerances, the safe inventory fraction and an explicit approach cap, rather than automatically inheriting every halving of the terminal threshold. Otherwise the same expensive wet prefix is reconstructed at ever smaller panels.

However, two terminal-threshold passes with an identical approach discretization do not establish approach accuracy. Retain the original full event-state and common-time comparisons and two consecutive successful refinements, and additionally compare a candidate with an independently halved approach cap. If this approach comparison fails, refine the approach; do not accept identical terminal refinements as convergence. The outer existing two-run maximum-step experiment provides a further check, but it must record that the actual approach caps differ and actually influence a panel; a merely smaller configured cap that is never active supplies no new evidence.

Keep every speculative path uncommitted until all unchanged numerical/source/event conditions pass. Preserve separate failures and their clocks. No callback caching across different states/times/source identities is proposed.

## Required independent no-EOS tests

1. Constant liquid sink: exact linear root recovered, old clock path compatibility, nonzero external work, complete component ledgers and dry continuation.
2. Explicit time-linear sink: exact quadratic inventory and analytic event root; both accelerating and decelerating cases. Verify the decelerating root can exceed tau0 while weights stay nonnegative.
3. Smooth nonlinear/time-quadratic sink with independent analytic integral/root: show the new event error decreases at the expected higher order across at least three terminal scales, with unchanged gates and no production-root helper as oracle.
4. Independent fast reacting spectator A'= -kA, B'=kA: exact A(t_event), separate event/common-time per-species errors, and an amount gate tighter than the nominal time gate. Include composition-dependent energy and nonzero component work so state/ledger agreement cannot pass through a zero-energy fixture.
5. No finite event: exponential liquid decay N'=-kN and a tangent/nonmonotone polynomial case; reject or continue normally rather than manufacture a root.
6. Clock and arithmetic extremes: exact root, adjacent binary-time root, large time origin, cancellation in summed liquid source components, rational quadratic coefficients, zero/nonzero arithmetic remainder, invariant energy binding, correction-budget exhaustion and unchanged cumulative source/element/mass budgets.
7. Invalid or competing stages: another species would become negative, wet physical domain failure, a competing cell event, near-breakpoint event, successive-event horizon reduction. Verify current uncommitted-prefix isolation and explicit failure status.
8. False-convergence trap: choose a coarse ordinary RK approach with biased reaction/energy state and very fine terminal thresholds. Terminal comparisons can agree, but the separate approach-cap comparison must reject. Also test shared error floors from provider uncertainties are retained.

Pre-register actual quantitative oracle gates before execution. For polynomial inventory, use independent high-precision analytic roots/integrals; for spectator chemistry use the exact exponential at the *computed event time* as well as at the true event time to separate event-clock and state-integration error.

## Minimum diagnostic additions

Store already evaluated terminal stage records, quadrature weights and polynomial/root evidence, event and common-time states separately, per-species differences and maximizing index/location, nominal T/P differences and each error radius separately, and phase-specific observation/panel counters. Do not spend additional EOS calls solely on logging. These records are needed to identify whether remaining failure comes from approach bias, terminal defect, roundoff, provider uncertainty or resource limits.

This is a concrete numerical implementation proposal, not a guarantee that the original wet fixture finishes within 120 s. Implement and prove the polynomial/evidence layer with no-EOS oracles first, integrate it with complete conservative ledgers second, then run the unchanged source-bound wet experiment. The full sludge material, free-sintering and model-validation Goal remains unchanged.

## Revised implementation priority with nested ordinary-prefix reuse

Root identified an additional exact reuse opportunity. With that opportunity included, the best first integrated implementation is **split approach/terminal caps plus a per-event reusable ordinary wet-prefix tree**, keeping the existing Euler terminal and its exact clock/writeback contract initially. This is materially stronger than split caps alone: it removes repeated wet approach integration across levels instead of merely reducing its step count. The higher-order terminal design above remains the next mechanism if the retained Euler event defect still dominates after this coherent reuse change. Avoid deploying cap separation alone and repeating the same expensive experiment without reuse.

### Why reuse can be exact

For fixed initial accepted state/operator, common horizon, knot interval, ordinary approach cap and ordinary RK policy, the next ordinary panel is determined by:

    min(approach_cap, safe_inventory_fraction*tau_current, common_time-current_time)

It does not depend on the terminal threshold. That threshold only decides whether to stop the ordinary prefix and fork into a terminal/dry trial. A finer threshold therefore shares an identical earlier sequence of ordinary panels with the coarser trial. After a coarse terminal candidate is compared or discarded, retain its preceding *wet ordinary prefix*, not its terminal or dry state. The finer level resumes from the last wet node and extends it using the unchanged ordinary rule until its smaller threshold applies. This is memoization of an identical deterministic prefix, not interpolation or reuse of approximate terminal solutions.

An implementation can start with one append-only wet spine instead of a general tree. Each node owns immutable state/time, the accepted ordinary ledger edge, its evaluated observation and the original wet operator mode. A candidate path is a view/copy of the spine prefix plus independently computed terminal and dry continuation. Only the finally accepted complete candidate is committed globally.

### Exact scope and invalidation rules

- Cache lifetime is one event localization from one already committed global state, within one program-knot interval and one common-time horizon. Flush on horizon replan, changed approach cap/tolerance/policy, changed initial state or energy binding, changed operator/mode/source implementation, competing event identity, or cancellation.
- Do not share a cached prefix between the independently halved approach-cap verification branches; they must compute their own approach discretizations. After agreement is proved, still commit one complete candidate once.
- Preserve the original source guards. Determinism must be an explicit cache-admission contract: the shipped source-bound WaterPhaseTransfer host is eligible only with its immutable state/model descriptors and unchanged source/configuration guards. An arbitrary ManufacturedDepletionAdapter callback may be stateful or depend on call counts and is not automatically eligible merely because the adapter dataclass is frozen. Add an explicit deterministic-fixture opt-in for cache tests, or leave arbitrary adapters on the uncached path. Do not imply caching is semantics-preserving for arbitrary Python callbacks.
- No source/config changes may be concealed by reusing a saved observation. Validate the current source/runtime guard at reuse boundaries using a read-only no-EOS identity operation where available; the next actual observation must still run all its ordinary guards. If a complete guard cannot be checked independently, scope reuse to a frozen declared runtime and expose that assumption rather than dropping identity verification.
- Preserve immutable array ownership; do not expose a writable cached state/ledger through diagnostic output while the localization is active. Internal cache nodes are not global accepted states.

### Budgets, rollback and ledgers

Count only newly executed observations and accepted speculative panels against actual global evaluation/panel/resource budgets; report reused-node/panel counts separately. Do not pretend reused panels were re-executed, and do not reset prior actual costs when discarding a terminal trial. Wall time remains one original monotonic deadline.

The original DepletionRoundoffTotals at the cache root remains unchanged because the cached wet ordinary spine contains no depletion writeback. Each candidate receives its own totals snapshot; terminal corrections and dry continuation never mutate the spine or another candidate. Global cumulative inventory/energy and component residual accumulators remain untouched until commit. At commit, concatenate the spine's ledger prefix and chosen terminal/dry ledgers in time order, then execute the same full-prefix audit exactly once. No cached edge can be charged twice or omitted.

Do not cache an ordinary failure, a partially advanced run that did not complete its requested panel, an observation after terminal mode switch, or an event/common comparison. Preserve failed-attempt records separately. A candidate's event object and correction remain bound to its own terminal ledger.

### Expected cost improvement and its limits

Without reuse, refining terminal threshold geometrically requires a growing number of approach panels and repeats the earlier panels at every level: total approach work can grow quadratically in the number of geometric threshold levels. With nested reuse it is approximately the work of the finest ordinary prefix alone, plus one terminal/dry comparison per level. The wet EOS work before the event should therefore drop substantially. The claim is structural operation-count reduction, not a numerical prediction of wall-time success; post-event chemical diagnostics and mandatory independent approach verification still cost time.

A high-value first regression should compare cached and uncached **identical split-cap policies** with a deterministic manufactured counter. Require byte-identical candidate states/times/ledgers/diagnostics and identical final decisions, but fewer actual wet evaluations. That establishes exact reuse semantics separately from any accuracy improvement. Add cancellation midway through a reused prefix, failed terminal rollback, horizon-replan invalidation, source/model identity change, different approach-cap invalidation, and a deliberately stateful adapter that is rejected for caching or left uncached.

Maintain the false-convergence test and independent approach-cap comparison described above. Cache agreement at successively smaller terminal thresholds is not proof against a common approach error. This combined change provides a concrete bounded next event engine while preserving all current physical uncertainties, source qualification and exact terminal accounting.
