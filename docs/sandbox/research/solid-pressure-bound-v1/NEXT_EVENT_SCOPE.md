# Read-only next event-localization opportunity

This assessment was prepared while v2 depletion0 session 87557 was reported live. It does not predict its outcome or treat an intermediate result as terminal. No source/script/install changes, EOS calls or tests were made. Only this scope document was written.

## Why the A/B event-state comparison can become the limiting gate

In the prior failed v1 result, amount differences approximately tracked 0.2 mol/s times the differences in the two event times. This is consistent with the declared A→B rate: even perfectly integrated A evaluated at two different event times differs by approximately |dNA/dt|*|delta t|. The unchanged amount gate 1e-10 mol therefore implies an effective event-time scale about 5e-10 s for this fixture, considerably below its separate 1e-7 s time gate. This is a legitimate coupled constraint, not grounds to remove event-state comparison or compare only common-time states. The actual max amount metric can also include numerical integration error and either A or B, so the approximation must be confirmed with decomposed diagnostics before calling it the exclusive limiter.

`depletion_integration.py:275–285` predicts tau=N_liquid/(-net_liquid_rate) using the current net source. `terminal`, lines 291–326, uses that exact represented frozen-rate tau and a nearest-downward floating endpoint. All terminal species and work quadratures are left-endpoint rate times duration: it is an explicit Euler terminal panel, unlike the ordinary RK2 panels. For a smooth variable liquid sink, its event-time defect is generally O(tau²) locally. Correction writeback subsequently accounts for represented arithmetic remainder; it does not correct the truncation error of that frozen-rate event prediction.

The correction contract is exact and specific: `DepletionClockEvidence.inventory_residual` reconstructs this frozen-rate root and requires the endpoint to be its nearest downward neighbor; panel terms must equal duration times each stored rate. Therefore directly substituting a secant/quadratic/dense-output event time into the existing terminal code would invalidate its evidence contract. Enlarging the roundoff correction to absorb numerical event error would also be invalid.

## Concrete cost opportunity without altering the event/correction definition

The current `proposal` uses the same refinement `cap` for TWO distinct purposes:

1. decide when remaining tau is small enough to switch to the Euler terminal panel;
2. cap every preceding ordinary RK2 integration segment (`desired=min(cap,...,safe_fraction*tau)` and `normal(...,cap)`).

Each refinement reconstructs the entire speculative approach from the same accepted state. Halving this global approach cap as well as terminal threshold makes the number of costly wet evaluations grow approximately with 2^level over the fixed approach interval. In v1 the completed level evaluation counts were 20, 40, 58, 94 before timeout. The terminal defect only requires a sufficiently short terminal panel; forcing all earlier ordinary panels to that same tiny size can waste work.

A bounded next numerical proposal, IF the current run establishes this cost bottleneck, is to **separate an ordinary approach-step cap from the terminal-switch threshold**. Keep the ordinary RK2 tolerances, stage positivity checks, safe_inventory_fraction=0.25 and a declared fixed or independently controlled approach cap. Refine only the terminal threshold inside the event-localization comparison. The existing safe fraction then approaches the event geometrically, approximately logarithmic in the terminal threshold, rather than marching the whole pre-event interval in uniformly tiny steps. The terminal panel itself, its nearest-downward frozen-rate clock evidence, positive-evaporation diagnostic, all correction budgets, complete event/common-state comparisons and two consecutive passes can remain unchanged.

This is a numerical algorithm change requiring its own explicit version, preregistration and tests; it is not automatically validated by the old implementation. A fixed shared approach cap can hide common ordinary-integration bias across terminal refinements, so retain a separate external approach-cap refinement (including endpoint and event-state comparisons) to test that error. Do not advertise event/global accuracy solely from two terminal thresholds. If ordinary RK2 error proves dominant, refine that approach discretization independently; do not loosen its error tolerance to gain speed.

A higher-order terminal scheme is a possible later alternative, but it needs a new quadrature/root enclosure and clock-evidence contract, positivity-safe interior stages, complete component quadrature and a proof that writeback still covers arithmetic only. It is not the smallest safe next change, and simply using a predicted dry-state rate or interpolating temperature/inventory would bypass current physical state checks.

## Diagnostics needed only after a terminal failure is established

Preserve the current run first. In a separate preregistered diagnostic run, save for each speculative refinement:

- terminal start time, tau, current liquid amount and each liquid net-source component; terminal duration and exact clock-rounding remainder;
- complete event states and both states at the common comparison time, with inventory layout and total-energy identity;
- per-species absolute differences at event time and at common time separately, identifying which cell/species and which time location determines the maximum;
- actual liquid-transfer and A/B rates at event approach, and the analytic A-event-time difference 2|exp(-k(te_a-t0))-exp(-k(te_b-t0))| as a diagnostic alongside the unchanged measured amount metric;
- pressure and temperature nominal differences separately from EACH provider error bound, at event and common time;
- evaluation/panel counts and elapsed time split into ordinary wet approach, terminal evaluation, post-event common-time continuation and comparison observations.

Prefer retaining already evaluated observations and states. Additional EOS evaluations should not be silently introduced just for logging; they change cost and may make a bounded experiment fail. Complete accepted/speculative-ledger records are necessary to check correction budgets and ensure no uncommitted state leaks into final result.

Before any algorithm implementation, use no-EOS manufactured adapters with constant and time-varying liquid sinks and an independent reacting spectator inventory. Include an accelerating sink, simultaneous-event rejection, fixed inventory/energy identity, nonzero component work, an event near a breakpoint and depleted dry continuation. Demonstrate the original correction limits and event/common comparisons unchanged. Only then rerun the same source-bound wet fixture under original physical gates and resource limits, followed by separate approach/time refinement.

This is an opportunity assessment, not a diagnosis of the still-running v2 case or a claim of completed reacting wet validation. Raw-sludge evidence, free-sintering closure and the complete physical Goal remain outstanding.
