# V3 new HEOS T/P failure: bounded instrumented replay

Read-only design; no EOS, tests, imports, probes, patches or runtime changes performed. The existing v3 failure is authoritative and must remain preserved.

## What is known from actual result/code

The saved v3 depletion0 result is numerical_failure / liquid_property_solution:heos_tp_not_converged, 147 evaluations and 45.760554042004514 s, no committed event. Refinement level 3 fails during approach work after 12 new evaluations and one ordinary panel; it has zero terminal/dry/comparison evaluations at that level. Earlier complete comparisons now expose that the maximum amount difference is event-time B (then A), while common-time amount differences are much smaller. The local pressure-bound correction has removed the previous 1.6 Pa floor. This is a new liquid T/P EOS numerical solve failure, not another timeout or unchanged pressure-gate failure.

Actual call path:

    DeformingSolidHeat.evaluate
      -> point total-energy inverse / current SolidFluidStorage
      -> RigidStorage / RigidWaterGas liquid volume evaluation
      -> HEOSWaterProperties.state_tp or state_tp_response
      -> HEOSCandidate.state_tp

The source-gated wrapper calls the real HEOS kernel. _water_python_backend.py contains the stateless PythonIAPWS95Calls dispatcher for the *other* backend; switching through that path would change the evaluated implementation and is not a faithful failure replay. It must not be used as a fallback to manufacture success.

HEOSCandidate.state_tp first runs guarded saturation coexistence, checks phase stability, seeds density from native PT flash, then performs at most eight log-density Newton iterations. Its stopping rule remains abs(p_native-p_target)<=min(1e-4,rho*1e-7). Every iteration already records rho, native/target pressure, residual, slope, h and u in _tp_iterations. The guard restricts |log-density step|<0.1, checks density branch and finite positive slope, and resets imposed phase in finally. The explicit heos_tp_not_converged reason means the loop exhausted without satisfying the original residual gate; it does not identify whether the cause is cycling, rounding stagnation, insufficient iterations or an inaccurate derivative. Those distinctions require the actual failing T/P and trace.

## Preferred minimal instrumentation: exception-only Python tracing

Use a separate temporary diagnostic entry script, after the frozen full suite is terminal. Do not edit pinned production source, manifest, native files, water reference, solver limits or numerical gates. The entry script installs a narrowly filtered sys.settrace hook on the loaded HEOSCandidate.state_tp Python code object. The global call hook returns a local hook only for that code object; the local hook inspects the 'exception' event only when the exception is WaterNumericalError with exact message heos_tp_not_converged. It returns immediately for line events and all other exceptions. Python tracing does not bypass the original method, transaction or source checks and avoids monkey-patching their functions.

At that failure event, snapshot immediately from the actual frame:

- T, target P and phase, with repr and float.hex representations;
- iteration, rho, slope, residual, and every existing _tp_iterations row;
- saturation liquid/vapor densities and pressure already returned to the local frame;
- wrapper/kernel implementation identity and source/runtime hashes already loaded by the fixture;
- the exception type/message and formatted stack.

Walk the caller frames without evaluating model functions, selecting only known model code and a whitelist of locals: the host stage's time_s and ConservedState amounts/total energy/energy identity, point inverse target/bracket, liquid/gas/solid amounts, and the RigidWaterGas trial pressure. This distinguishes a pressure-bracket endpoint or inverse-temperature trial from the physically accepted cell pressure. Do not dump arbitrary locals/globals or invoke properties that perform EOS work. Copy existing immutable arrays/mappings to detached primitives. The frame's existing scalar values and stored diagnostics suffice; no new water call is needed for logging.

Write the failure snapshot promptly to a dedicated output before unwinding so a subsequent catch or external interruption cannot erase it. Use a temporary file plus atomic replace or an append-only one-event record. Logging errors must not mask or replace the original numerical exception. Restore sys.settrace(None) in an outer finally and retain the ordinary integration failure/result. The instrumented runtime must be explicitly labelled observational tracing; do not describe it as zero-overhead or claim byte identity proves no runtime instrumentation.

## Replay choice and bounded execution

For the first capture, use the same initial state, operator, policy, nested strategy, physical inputs and integration interval as v3, under the original 120 s internal / 150 s external budget. The original failed after about 46 s, so this is a bounded *instrumented reproduction yielding new evidence*, not an unchanged retry. The tracing hook adds no EOS calls, and trace overhead must be reported rather than hidden. Do not run concurrently with the full suite or another native probe.

A replay from the last committed wet state at the event-search root can save earlier work: load the exact saved amounts and total energy, preserve the energy-model identity, retain original policies/modes and use its saved time. However, this changes prior native-call history and resets per-run accounting. If used, explicitly call it a diagnostic suffix, never a continuation proving full original prefix conservation; do not reconstruct the state by recomputing temperature. If the suffix does not reproduce, that is evidence of history sensitivity or another unresolved cause, not permission to alter solver gates. The full original instrumented replay is preferred when avoiding this ambiguity matters more than its modest extra cost.

Do not preemptively rerun the existing callback just to warm the provider: it would add a different native call history. Build exactly as the original depletion script and use its source-verified setup. Preserve original v3 evidence in its directory; write all diagnostic script/PLAN/input hashes and new results to a separate attempt directory. Supervisor must require both complete status and the intended child exit policy; the target numerical failure should remain labelled as failure even though its capture succeeds diagnostically.

## After capture: one exact-state reproducer, then choose a fix

Only after the captured frame supplies exact T/P should a separate bounded reproducer load the same approved provider and call the public HEOS state method with float.fromhex captured arguments. Keep phase, source/configuration guards, original eight-iteration cap and original residual limit. Record the full existing last_tp diagnostics, baseline outcome and source identity. Do not independently run an uncontrolled grid or silently switch to Python IAPWS for acceptance.

Inspect the trace before choosing a numerical change:

- repeated density/pressure values with residual above threshold: rounding stagnation / resolvability;
- two or more alternating density values and residual signs: full-step Newton cycling, potentially motivating bounded residual-decrease backtracking;
- monotonically improving residual without completion: assess the original iteration-bound contract and root bracket strategy, not automatic budget inflation;
- wrong/nonpositive slope or unstable density would normally produce a different explicit failure and must remain distinct.

For a proposed TP backtracking or bracketed correction, preserve this exact failure and original gates first; then separately preregister the candidate, no-EOS control tests, native failing-state/neighborhood checks, and original coupled replay. A saturated coexistence backtracking fix elsewhere does not prove TP Newton requires the same repair. No fix is selected until the captured data identifies the mechanism.
