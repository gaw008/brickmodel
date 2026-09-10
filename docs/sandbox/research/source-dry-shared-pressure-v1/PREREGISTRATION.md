# Explicit shared-volume source wet-to-dry study — preregistered

Baseline `c684bce`. Run once after final code/physics review, focused source and
non-editable installed tests, and package identity verification. No result is
asserted here. The preceding experiment and its independent pressure failures
remain unchanged.

## Fixed experiment and one new assumption

This run reuses the complete physical state, source helpers, inverse, integration,
event and roundoff policies from [the prior preregistration](../source-dry-transition-v1/PREREGISTRATION.md).
Its frozen runner SHA-256 is
`a7916d30ee0eb0abf5852a76c5b92eec3a70acd1b0e130cd05a1dc556f2d6e71`;
the new runner checks that hash and both original helper hashes before execution.
No saved old trajectory is reclassified as a new accepted run.

The sole new comparison assumption is an explicit declaration made from the
actual checked `SourceWetStorage` and its constant available-volume object.
Both freshly executed dry paths must retain those same live objects, source
identity, fixed dry mass, reference conventions and original V ± eV. Equal
numbers or equal content digests from different objects do not establish this
correlation. Process-local IDs and runtime same-object admission are saved;
JSON alone does not prove a new live object's identity.

Use N1, V=0.001 m3 with unchanged eV=1e-12 m3, initial liquid 1e-11 mol,
gas (0.125, 0.25, 1e-12) mol, T=325 K and actual source forward initial U.
Retain the actual HEOS/water and O2/N2 providers and source dry Cp. Keep closed
boundaries, zero liquid transport, width 0.25 m, area 0.01 m2, phase coefficient
1e-9 mol/s/Pa and disabled reactions. Geometry and transfer coefficients remain
manufactured numerical inputs, not measured sludge material properties.

## Unchanged controls and acceptance

The initial actual positive evaporation probe sets H=(3/2)Nl/E. Retain
`InversePolicy(1e-5, 1e-6, 100)`, reference initial/max step float(H), minimum
2^-30 s, relative tolerance 1e-8, N tolerance 1e-7 mol, U tolerance 1e-3 J,
scales 1 mol and 1e5 J, maximum 4 steps/4 rejects and 180 s path policy.
Keep the actual source-bound water molar mass and all previous roundoff budgets.

Event thresholds remain time 1e-8 s, N 1e-11 mol, U 1e-7 J, T 1e-5 K and
P 1e-4 Pa; terminal window 0.001 s, maximum refinements 32, common horizon
0.01 s, safe fraction 0.25 and explicit affine_midpoint. The original mechanical
`DepletionPolicy.pressure_comparison` remains None. The new opt-in is the
separate `shared_volume` argument to the source transition evaluator.

Fresh seed, positive approach, shifted seed and both wet-terminal/writeback/dry
paths must execute through the existing production path. Compare the event and
same actual later time. Preserve original reported-T pressure and independent
full-T pressure values and gates beside the new pressure evidence.

The joint bound uses exact gas-inventory sums, both complete independent inverse
temperature intervals and one shared complete V interval. Retain each endpoint's
actual fluid error, strictly reconstructed total-bound projection remainder and
a separate full T/V-box arithmetic rounding bound. Require complete absolute
pressure boxes to remain in the original domains. Select the joint bound only;
the old independent bound has not been proved to cover the same full-box machine
error target, so taking their minimum is not allowed.

Numerical event acceptance requires the original clock/N/U/T and cumulative
ledger checks plus the new joint P bound <= the unchanged 1e-4 Pa at both
comparison locations. An unresolved enclosure cannot pass. Retain old P failures
even if the new conditional comparison passes. No event outcome is forced.
All single-endpoint and pressure-pair source/material/event qualifications retain
their original false values; transition numerical acceptance is separate.

## Resource bounds and saved evidence

Unchanged caps: each seed/approach/shifted trial 16 actual callbacks, each dry path
24; total 97=1+3*16+2*24. The previous 32 calls are a planning estimate, never an
asserted observation. Outer SIGALRM requests a stop after 210 s; it is not a hard
native interrupt. No automatic retry or increase in budget.

Keep the prior atomic before/after callback persistence, exact time and packed
inputs, returned candidates, failure context and nested causes. Save complete
transition, original gates, shared declaration, joint error decomposition and
selected strategy. Count actual source calls, provider constructors/reference
checks and initial U evaluation separately. Review saved observations without
another EOS run; preserve failures and unchanged historical evidence.

This conditional N1 numerical study does not validate real sludge drying,
reaction/sintering/cooling, N-grid liquid transport, rewetting, source persistence
and app integration, public mechanism holdouts, full-cycle or multigeneration
material predictions. Those original Goal requirements remain incomplete.
