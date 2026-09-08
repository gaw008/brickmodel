# Native free-slab event attempt: retained failure

The installed 9121200 numerical model ran for 499.457 service seconds (496.887 integration seconds), then returned `failed: correction_exceeds_evaporation_fraction`. It retained 13 accepted steps, zero accepted events, 751 evaluations, 90 attempted panels and zero rejected ordinary trials. The accepted endpoint is 0.5002620305782048 s; the registered endpoint was 0.50032 s. No actual depletion event has passed this application experiment.

All physical inputs, initial inventories and source settings remain those of the existing manufactured reacting free slab. The simulation horizon, step controls, nested event approach and resource budgets were explicitly registered before execution. Tolerances were unchanged. The sole subprocess completed within its 840 s watchdog. This is a manufactured coupled numerical experiment with actual water properties, not a raw-sludge material validation.

## What the evidence establishes

- Every saved terminal comparison at levels 1–11 fails the pressure gate while the other five gates pass. At level 10 the nominal pressure difference is about 7.93e-10 Pa, but the two point pressure envelopes sum to about 0.00513489 Pa, above the existing 1e-4 Pa comparison gate. Refining terminal time does not materially reduce this observed envelope contribution. Level 12 reaches the correction-fraction restriction. Rejected candidate event times must not be presented as accepted physical predictions.
- Independent standard-library Fraction arithmetic passes all 13 accepted N/E/mechanical/component prefixes. Maxima are 5.58089e-16 mol, 2.92657e-11 J and 1.98409e-16 stretch. The global external-pressure-work maximum is 2.76765e-11 J at state 6; cumulative absolute cross-cell constraint imbalance is 9.25615e-21 J. Both pass the pre-result 2e-8 J targets. Overall acceptance remains failed because the fixed horizon and accepted event are absent.
- A separate 20 s bounded diagnostic at the last accepted state completed in 2.306 s. Its combined pressure envelopes are 0.00145538/0.00250779 Pa; fluid contributions are 6.81088e-5/0.00111581 Pa. Combined minus fluid is approximately 0.00139 Pa per cell, with stored volume envelopes approximately 2e-12 m3. This is same-model decomposition at the accepted wet state, not independent validation or a reconstruction of the rejected event state.
- The stored code shows two contributions: rigid fluid residual/resolution/liquid-volume bounds propagated through pressure compliance, then solid/current-volume uncertainty propagated through a locally certified compliance bound. The result is not evidence that only one contribution causes all failures.

Complete original case, plan, runtime bindings, accepted states, rejected comparison diagnostics, supervisor termination, audit script/review and point diagnostic are in `research/free-native-events-v1`. The first experiment was not overwritten or rerun with easier settings.

## Next action

Derive and independently test a paired pressure-closure difference bound using monotonicity and explicitly shared parameter identities. Common constant solid-volume uncertainty may contribute through differences of inventories only where the provider contract proves that correlation. Liquid and temperature terms still require certified domain/derivative bounds. Arbitrary approximation errors must not be assumed to cancel.

Preserve the original absolute output uncertainty envelopes, physical values and 1e-4 Pa comparison gate. Do not simply increase refinement depth, subtract point bounds, reduce declared errors, or change liquid inventories to force an event. A proposed tighter comparison needs a mathematical contract, independent adversarial tests and review before the native experiment is repeated.

The targeted Kim & Parker original-text retrieval also remained unsuccessful. Its source notes are archived; no heat-capacity or material admission was added. Spatial convergence, same-material raw-sludge closure, three public mechanism groups with held-out validation, and the full wet-to-fired/cooled Goal remain incomplete.
