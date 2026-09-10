# Preregistered candidate: native_water_mixed_near_events_inventory_v1

Proposal only; no EOS, native call, solver or terminal preparation has been executed. This defines a new manufactured numerical test case, not a resumed native trajectory or observed physical specimen. Root must approve and freeze the full derived input before its single measurement.

## Fixed selection from saved data

Use the actual initial full-step sample in native_stage_study/attempt01/trial.json. At the saved initial temperatures300.125 K/305.25 K, both original liquid inventories are0.02 mol. Their actual phase evaporation rates are:

| Cell | Original liquid mol | Saved evaporation mol/s | Chosen old-rate target seconds | New liquid mol, binary64 |
|---|---:|---:|---:|---:|
| 0 | 0.02 | 1.0613949693066351e-5 | 1/5000 =0.0002 | 2.12278993861327e-9 |
| 1 | 0.02 | 2.2460995872763542e-5 | 1/2500 =0.0004 | 8.984398349105417e-9 |

The exact rule is new_Nl[i] = binary64_nearest(Fraction(saved_binary64_phase_rate[i]) * target[i]). Pin the output floats with hex0x1.23c107f3fb070p-29 and0x1.34b39a8751a66p-27. These are strictly positive ordinary binary64 numbers, not tiny values that underflow to zero. The saved rates as exact fractions are6265370035175137/590295810358705651712 and6629315880088249/295147905179352825856. The target spacing0.0002 s is20000 times the original1e-8 s time gate; it is a deliberate old-rate design margin, not an event-order certificate or a new minimum-gap acceptance rule.

Only the two liquid inventory entries change relative to the current native stage's initial design. Keep both solid-kg vectors, three gas-mol vectors, temperatures, bulk geometry, reaction coefficients, transfer coefficients, shared face coefficients, source providers, formation reference and declared error envelopes identical. Initialize each new total U from a fresh forward evaluation at its unchanged temperature; do not reuse the old energy with reduced liquid. Save the old and new input tables and this deterministic rule. The previous case's original0.02 mol inventories are larger by factors about9.42million and2.23million, respectively. This is a substantial explicit initial-condition change and must never be reported as the same original case.

No old returned state, mode, pressure certificate or recorded rate certifies the new state. Smaller liquid inventory changes occupied volume and total U, and can change pressure, water chemical potential, heat capacity and subsequent reaction/temperature feedback. Both initial modes must remain existing_liquid. A failed new forward/observation stops the study without clamping or replacing the values.

## Original gates and small-inventory limitation

Retain kg1e-8, fluid amount4e-7 mol, U0.001 J, T0.001 K, P1 Pa, time1e-8 s; minstep1e-12 and maxstep0.01 s. Keep the original per-cell water roundoff policy exactly: local correction/storage1e-15 mol, element2e-15 mol, mass1e-16 kg; cumulative correction/storage1e-14 mol, element2e-14 mol, mass1e-15 kg; fraction of actually integrated positive evaporation1e-8; original-liquid-fraction limit1e-8. Bind the same source-water molar mass, nominal0.018015267999999997 kg/mol, through the actual provider rather than replacing its literal convention.

For these proposed original inventories, the original-inventory fraction limits alone are about2.12279e-17 and8.98440e-17 mol, already stricter than local absolute1e-15 mol. A later short terminal panel's own positive evaporation may make its local fraction bound much smaller. No correction is performed in the proposed measurement; these arithmetic limits do not predict writeback acceptance. Positive float representation is ample, but actual pressure/thermal domains and terminal accuracy remain untested.

Both proposed inventories are below the existing4e-7 mol comparison gate. Retaining that gate is mandatory here, but it means a later passing absolute amount comparison alone cannot demonstrate relative resolution of such a small water inventory. Strict positive-panel tests, actual event times and per-cell roundoff bounds still apply; none can be waived or replaced by the loose amount gate. The eventual study must state this limitation explicitly. This is a virtual continuum numerical fixture; no evidence here establishes the experimental applicability of a bulk liquid phase at these very small total inventories.

If this inventory scale is considered unsuitable for the intended validation, do not silently enlarge the inventories or tighten/loosen gates after the measurement. Reject this proposal or preregister a separate longer-time case before observing results. The present proposal is useful narrowly for testing the real-water mathematical branch and future event seam with a finite runtime, not for material drying prediction.

## Sole authorized prospective measurement

After root review, reuse the current native_stage_study initial-construction approach and supervisor, with a new output directory/case name and the pinned new inventory entries. Freeze the original input tree, original builder, derived case and temperature/inventory table, current installed source membership, water/backend sources and this proposal. Verify only the intended inventory fields and descriptive identity differ. No alternate source or test liquid backend is admitted.

Perform exactly two new initial forward energy evaluations, save full points and new initial states, then exactly one actual WetPair.evaluate of those states. Save its full observations/phase rates, pressure/temperature and error/domain outputs, source/mode binding and attempted/completed counts. Native internal call count remains unknown: source/reference construction itself may call the backend. Do not run a stage, pressure certificate session, terminal preparation, root-order selection, projection or controller in this measurement.

Use initialization maximum30 s, whole measurement maximum40 s and external watchdog50 s, declared before execution. The previous fresh setup consisting of two initial forwards plus one pair observation measured about6.480168 s;40 s is an approximately sixfold planning margin, not a physical cost theorem. The independently measured native ordinary stage showed roughly48.65 s outside its four queries for nine callbacks, consistent with keeping this first one-observation request much smaller than a whole controller. Enforce2 forward/1 pair attempt counts, source/caller guards before and after calls, no retries, external process-group kill/reap, and preserve any partial outputs or errors. These resource limits do not alter scientific thresholds.

The measurement can establish actual new initial state construction, wet-domain admissibility, signs of both phase rates and new tangent diagnostics. Report new tau=Nl/positive_phase_rate only where rate is positive; otherwise report unavailable with the actual reason. Even positive separated new tangents do not prove nonlinear affine root order. Root must review the saved result before separately proposing any terminal or complete-controller experiment. This document explicitly does not authorize either.
