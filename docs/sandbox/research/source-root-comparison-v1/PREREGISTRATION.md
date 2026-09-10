# Single actual source/HEOS partitioned root comparison

Baseline b7466e3. Execute once after source/installed checks and independent runner review.
Reuse the prior source-approach-v1/run_native.py construction and exact test inputs:
real source dry-mass Cp, source O2/N2, manifest-checked HEOS liquid/ideal vapor,
manufactured fixed fluid volume, geometry and 1e-9mol/s/Pa transfer coefficient.
N1, closed boundaries, no interior face, existing liquid, no chemistry. Liquid1e-6mol,
gas(.125,.25,1e-12)mol, T325K; one actual forward evaluation determines initial U.
Four backend provider constructors/reference anchors are counted individually.
No original control, source envelope or scientific tolerance is changed.

One actual initial phase probe determines H=1.5*N/phase if phase is finite positive.
Coarse failed full-prefix seed retains actual first/midpoint. One root-guided actual
approach supplies its completed reference endpoint. From that actual state/time,
one fresh shifted trial ends at original H and independently supplies two samples.
If it cannot provide a supported unique liquid root, stop; do not alter parameters.
This shifted partition is not 2:1 Richardson refinement and uses no /3 factor.

Clock comparison retains absolute exact-time intervals for the two numerical roots.
Ordering, positive-lower and comparison narrowing share each original32-round limit.
Further narrowing aims at width<=original time_absolute_s/4, stopping at the remaining
budget; distance upper bound=max(|LA-UB|,|UA-LB|) includes both widths. Insufficient
resolution or a failed gate remains visible, without changing original time tolerance.

Select common positive endpoint from the shifted start using the original safe fraction
of the interval before BOTH refined lower bounds, with original minimum-step/domain checks.
The new extension is capped by maximum_step_s. A complete coarse trial may span multiple
reference steps: maximum_step_s limits each integrate_exact step, not total trial duration;
its longer affine prefix is independently checked against that actual reference by original D.
Run two actual SourcePrefixTrial instances: original initial state->common end and
approach-reference endpoint->same common end. Each must complete its original reference
and direct N/U discrepancy<=1. Compare actual reference captures; fine path's two
reference segments must meet the original cumulative N/U ledger budget at EVERY prefix
from the original origin. No budget is restarted for that conservation check.

Report root-time, N/U/T/reported-P, conditional full-T pressure and numerical success
separately. In particular, neither root agreement nor this positive common endpoint
certifies event states, a wet/dry switch, drainage correction, EOS error bounds or
real sludge material applicability. No event/material qualification may be granted.
The source-approach-v1 native experiment already showed the original pressure gate
can be uncertified; this experiment will preserve that outcome if it recurs.

Resources: each trial16 actual source callbacks and original180s wall; overall81 callback
cap=1 initial probe+5*16, expected38=1+2+11+2+11+11 for minimal paths. Prior actual N1
14 callbacks took32.312s, so38 callbacks suggest roughly88s at the prior average; that
is an estimate, not a measurement. Keep the existing210s outer SIGALRM request covering
construction, all trials, checks and file writing. Native calls may only observe the
signal when returning to Python; this is not a hard C-level interrupt guarantee.
No automatic native retry; save every attempted/returned callback and partial trials
before diagnostic assertions. Retain budgets, counts, real elapsed time and failures.
