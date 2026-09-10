# One actual source/HEOS positive approach

Baseline ee0ed24; run only after current implementation source/installed tests and runner review.
This is numerical integration evidence: no actual sludge domain, geometry, effective transport,
dryness, event-time, reaction, sintering, material or full-EOS-error certification.

Use the frozen source-wet-storage constructor with source Arlabosse dry-mass Cp, original
water/gas providers, declared conditional error envelope and manufactured fixed volume.
The separate chemical model explicitly uses the same HEOS manifest. Four provider constructors
are expected, each with its original reference anchor; count separately from source callbacks.
N1, closed boundaries, width .25m, area .01m2, coefficient 1e-9 mol/s/Pa and existing-liquid
are manufactured selections from the existing fixture. No interior faces or mobility law is needed.
Liquid1e-6mol and gas(.125,.25,1e-12)mol at325K are explicit test initial conditions.
One actual storage forward evaluation sets U; one additional actual source callback measures phase.

Only for finite positive phase compute exact H=3/2*N_liquid/phase. This is a proposed test
horizon, not measured time to depletion. Preserve IntegrationPolicy tolerances and scales
(rtol1e-8, N atol1e-7mol, U atol1e-3J, Nscale1mol, Uscale1e5J), maxsteps/rejections4.
Initial/maxstep=float(H); minstep2^-30s, per-trial wall180s, each callback cap16.
Use original native source inverse policy(1e-5J,1e-6K,100), not a relaxed error target.
Full explicit DepletionPolicy is identical to existing policies() except refinement32;
these are declared numerical controls, not physical/material accuracy claims.

One seed only. Require actual successful first/mid captures, negative full prefix and unique
positive numerical proposal. Otherwise stop and retain failure, with no parameter search.
Run exactly one new SourcePrefixTrial on the proposed interval and its existing integrate_exact
reference. Original normalized N/U discrepancy<=1 is the numerical success criterion. Keep the
four endpoint gates and conditional pressure separately whether satisfied or not; never loosen
them. They are not required to pass to record a positive approach integration test and cannot
be converted to an event admission.

Outer210s includes constructors, initial U, phase probe, seed, new trial, evidence and postprocessing.
SIGALRM requests timeout; native calls may only observe signals when returning to Python, so no
claim of a hard native interrupt. Total source callback cap33=1+16+16; expected14=1+2+11 if minimal.
The old N3 11callback81s is a measured cost reference, not an N1 prediction. Measure actual counts
and time. Save each attempted state/time before calling and each returned/failed observation.
Preserve partial trial on assessment exceptions. Check installed/source byte identity before run.
No rerun merely to improve outcome or measure omitted timing; failures are evidence to diagnose.
