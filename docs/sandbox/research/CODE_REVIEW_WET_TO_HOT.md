# Independent review: wet-to-hot verification design and code

Verdict: APPROVE for the bounded verification fixture, conditional dry reference and failure-preserving runner. This pre-run code review does not claim that the long trajectory has passed.

Read test_wet_to_hot_host.py, WET_TO_HOT_PLAN.md, wet_to_hot_run.py, their actual fixture dependencies and the earlier independently reviewed source-Cp helper. No wet/high-temperature experiment was repeated during the root's two-cell run.

## Physics and independent reference

The actual host begins wet at 300 K with complete (solid, water vapor, liquid, tracer) inventories (2,1e-8,1e-6,.001) mol. The event integrator must locate real liquid depletion, retain K=1e-6 and continue the same full storage host. Only exactly zero liquid selects the explicit dry inverse bracket. JoinedWaterVapor supplies high-temperature caloric storage; it does not extend liquid chemical potential or confer real-material qualification. The dry branch is explicitly metastable_no_nucleation and its above-500 K chemical demand remains unknown.

For the specified constant-volume solid and fixed dry gas inventories, the independently written dry energy is 2*(-100000+50T−p0*v)+Nv*u_water(T)+Ntracer*(30−R)T. The tracer fixture has zero enthalpy offset and Cp=30; solid Cp=Cv=50 applies only to its stated incompressible fixture. Therefore Cclosed=100+Nv*(Cp_water−R)+Ntracer*(30−R). Serial half-cell/film conductance is G=A/(dx/(2k)+1/h)=1/15 W/K, so dt=15*Cclosed(T)/(1000−T)dT. The code's quadrature and root formulation match this equation, and it explicitly splits at the 500 K Cp seam.

The dry reference reconstructs event temperature from the actual accepted event U and inventories. High-water h is obtained via the earlier Decimal integration of original Shomate coefficients and the stored low 500 K anchor; high Cp is evaluated directly from source coefficients. Low-water Cp/h shares the separately verified original low model. It never uses the candidate final temperature as the oracle root. The test is thus an independent check of the dry caloric/heat evolution conditional on the accepted event state/time, not an independent measurement of the correct depletion time, EOS model error or physical sludge behavior. Subtracting the helper's manufactured solid contribution recovers its water u; the resulting rounding scale is immaterial to the declared 5e-4 K final gate for these small fixed water inventories.

## Audit and evidence contracts

The fixture retains zero Darcy/diffusive gas transport, checks every stored face-species integral is zero, keeps solid/tracer inventories unchanged and checks total water at each saved state. It reconstructs the total-U prefix from saved boundary heat/work, requires exact final time 600 s and one event, verifies unchanged K and explicit final dry mode, and requires final temperature minus inverse error to exceed 500 K. It also checks the final surface heat against G*(1000−T) and requires the explicit unknown-condensation diagnostic. The final dry reference gate is 5e-4 K absolute; original event and ordinary policies remain explicit.

This particular audit does not independently decompose every per-phase correction record or reconstruct each liquid/vapor column separately; earlier event-helper/integrator tests cover those contracts. Its complete U-prefix and water checks should not be renamed a separate audit of every raw event field without adding that record reconstruction. This scope observation was sent to the root before running.

The runner refuses an existing output path, captures every source/test dependency hash before and after the run, serializes trajectory/StepLedger/events/roundoff/refinements, retains assertion failures and requires unchanged dependencies for successful exit. The 240 s wall budget is explicit; a timeout must remain a failed artifact. Initial-state-only test success is author-reported and is not used as evidence of completed wet-to-hot continuation. No change to source coefficients, original chemical domain or acceptance tolerance is authorized by a failed attempt.

## Pre-run SHA256 bindings

- `tests/sandbox/test_wet_to_hot_host.py`: `f6bfcdf92464cf5b07331a9ddd9d865127a910c9be3a0bfcffc7458a4a413289`
- `tests/sandbox/test_joined_water_host.py`: `b37d5c4037b2dc743dbcbbbe0ed869792d385318507c47902670115d8f46017e`
- `docs/sandbox/research/wet_to_hot_run.py`: `57bfb28b6fe1332b67c6c2a46b396e9980e9caab452f3a2c4646432ad6a3d1b0`
- `docs/sandbox/research/WET_TO_HOT_PLAN.md`: `25dd0b4a5ea6065ed03d8b80fa3dcbbe598f0dde57aba64f93cdd6e34fe223cc`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE for the stated verification code; actual experiment success remains pending its separate result.


## Pre-run audit completion

The final audit was expanded before the long run: it now verifies every step's time correspondence and U change, every liquid/vapor (and inert) column's physical face/source plus explicit event projection, exact cumulative arrays, actual vapor write-back versus ideal paired transfer, all signed/absolute/correction totals, native-water mass/H/O, and exact zero liquid at every post-event saved state. Terminal StepLedger identity is checked against the event. This closes the earlier limited-audit scope observation without another physical integration or loosened gates.

A reviewer-found false-failure condition was corrected before execution: an event is not required to have a nonzero numerical correction. When the physical terminal panel already reaches exact zero liquid, correction=None is valid; the final audit requires empty corrections, zero totals and zero paired-sum residual in that branch. Otherwise all detailed paired/storage checks apply. It does not demand artificial residual liquid merely to exercise write-back.

No experiment outcome is inferred from these code checks. The unique bounded run may now proceed with frozen tests and original acceptance gates.

- Final pre-run binding `tests/sandbox/test_wet_to_hot_host.py`: `76175d3e1be9edf2d484683e6ec8017fb99bafd51993d08bd0c186288403a25a`
- Final pre-run binding `docs/sandbox/research/WET_TO_HOT_PLAN.md`: `f2528c8def413657571144bfd158eb8b098c9ab6b7c8cea92e5a4b9fc49ce025`
- Final pre-run binding `docs/sandbox/research/wet_to_hot_run.py`: `57bfb28b6fe1332b67c6c2a46b396e9980e9caab452f3a2c4646432ad6a3d1b0`


## Attempt 01: actual partial wet/dry continuation, not completion

Read `wet_to_hot_attempt01.json` without repeating the run. It has unchanged dependency hashes and one actual depletion event, followed by dry continuation, but ends at 198.0041396847951 s with resource_limit/rejected_trial_limit (100 rejections, 4523 evaluations, 526 accepted trial panels, 179.8826 s). It did not reach the 600 s target, so the full final-temperature oracle was not passed. Independently reconstructed the saved energy prefix (maximum residual 4.44123e-10 J) and total water (maximum drift 5.39322e-22 mol); these passing partial ledgers do not convert the failed run into success. Repeated ordinary dry-segment restarts are being addressed separately without enlarging the rejection budget or relaxing physical/error gates.

- Failure binding `docs/sandbox/research/wet_to_hot_attempt01.json`: `4049fb85b16c8931116bb7b6fd14e017bfabd46609886e4a9d5579284554fe9f`
