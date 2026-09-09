# Bounded measurement before performance changes

Design only; no EOS execution, repository edit, or installation. Reported event-run baseline: 592 evaluations / approximately348s for0.32ms physical advancement. The ratio is about0.588s per counted evaluation, but this is NOT a measured FreeSolidSlab.evaluate cost: integration includes discarded branches, phase callbacks, paired endpoint calls, guards, audit and bookkeeping with different counters. Do not assign percentages from this ratio.

## Smallest measurement

Use the exact installed runtime, frozen water package, actual original case and original tolerances. Root owns one supervised process, at most two actual `FreeSolidSlab.evaluate` calls after construction. No concurrent native task. Suggested external cap40s includes setup, profiling and artifact saving; if expired, retain partial report and stop, no automatic retry.

Build the original case once, measure construction wall separately, and select a saved accepted wet state from the actual348s run with its exact time, conserved N/E, full normal vector and common tangent. Verify source/case/energy identity and decode saved state with the existing white-listed state codec. Do not manufacture a new easier state. If the saved input cannot be bound to this exact model, fail before native evaluation.

Call1: `cProfile.Profile().runcall(actual_base.evaluate, state, time)`; use `time.perf_counter` and `time.process_time` around the call. Save binary .prof, complete pstats table (all functions, counts, primitive calls, self and cumulative time) and actual returned rates plus inverse numerical diagnostics in JSON before any parity assertion. Avoid serializing current_host/provider graphs. Record profiling wall separately from JSON/output costs. cProfile observes Python/C-call boundaries; native work hidden inside an extension call remains attributed to that call, not resolved into its internal functions.

Call2, only if remaining wall budget permits: repeat the exact same unmodified evaluate input without cProfile, measure wall/CPU, and compare full selected returned rates/temperatures/pressures/inverse bounds/geometry/free closure diagnostics exactly with call1. Label repeated-state warm/cache-history effects and profiler overhead as confounded: two calls cannot identify either separately, and absence of a second call is a valid bounded outcome. Do not infer production speedup from this pair. No extra evaluate for extracting diagnostics.

Record: actual module/source hashes before/after, platform/Python/backend versions, input raw hashes and floathex N/E/time/stretch values, call order, profiler settings, native backend existing iteration records if exposed without another property call, result/exception/traceback, parent process elapsed/CPU, and external termination status. Runtime must remain unchanged within attempt. Past runtime changes are displayed, not asserted equal. No output writes or checkpoint audit inside the profiled function unless that function normally performs them.

## Read the actual call tree, not overlapping percentages

Relevant actual boundaries:

- FreeSolidSlab.evaluate first performs _check_state, then one CurrentSolidStorage.temperature_from_total_energy per cell, constructs current transport/reactions, calls SolidFluidHeat._assemble_decoded using existing thermal inverses, and solves free_slab_rates. This seam already avoids a redundant thermal inverse. Count calls before proposing another reuse.
- CurrentSolidStorage._prepare checks _digest(template), builds current geometry/skeleton/pore volume and error budgets; identity/target also accesses digests. deforming_solid_storage._digest recursively canonicalizes and JSON-encodes before SHA256. Count recursion/serialization/hash time separately using pstats call sites where possible.
- SolidFluidStorage.temperature_from_energy repeatedly evaluates closure/storage within original brackets. Separate number of inverse forward evaluations from cost per evaluation; do not assume iterations are redundant.
- water_heos.HybridHEOSWater guard/dispatch and _heos_kernel.HEOSCandidate._transaction, state_tp, saturation_pair/_saturation_pair_locked, evaluate_density and _snapshot delimit source/config verification, coexistence solves, TP Newton/backtracking, native calls and derivative checks. Preserve transaction and final source guards during measurement.
- Fraction construction/arithmetic, geometry allocation, dataclass replacement validation, source-union construction and free traction solution can be visible Python costs. Report absolute self/cumulative seconds and call counts. Cumulative times nest and cannot be summed into disjoint percentages.

The host-only profile deliberately excludes WaterPhaseTransfer.evaluate chemical-potential work and paired-pressure endpoint comparison overhead. Therefore it can diagnose a host bottleneck but cannot explain all348s. Existing event counters and elapsed phase costs can bound the uncovered part without running more EOS now. If the host is a minority of measured total, next measurement must profile a bounded actual WPT/comparison unit under its own plan rather than claiming the current profile explains the whole event.

## Optimization classification after measurement

Potential numerical-path-preserving changes: eliminate repeated pure serialization within a *single explicitly immutable, already guarded operation*; reuse an already computed inverse/geometry/result rather than recomputing it; reduce transient Python allocations without altering evaluation/arithmetic order. These still require mutation/source invalidation tests, actual output/iteration parity and new runtime hashes. They cannot preserve literal implementation identity SHA when source bytes change, even if physical/source-asset identity and numerical values are unchanged.

Guard-sensitive changes: cached digests, endpoint/native result memoization, longer-lived geometry/property reuse or fewer filesystem checks. A frozen dataclass alone does not make nested providers immutable. Such changes need an explicit immutable-content or mutation-generation contract, cache keys including full state/source/config/phase and invalidation, before/after transaction checks, concurrency/cancellation tests and uncommitted-branch rollback. Never silently bypass source validation to improve timing.

Changes requiring new numerical analysis/evidence: looser Newton/inverse tolerances; alternate brackets/warm-start paths; EOS interpolation/surrogates; approximate derivatives; merging nearby states; changing quadrature/time stepping; mixed precision/vectorized arithmetic that changes rounding or acceptance; altered error-envelope correlations. These are not transparent performance changes. Some may preserve accuracy after proof, but require fresh error/domain/guard validation and independent references. Omitting phase transitions or prescribing strain changes physics and is outside optimization.

## Decision and next spatial cost

Deliver a measured call-count/cost table and a single identified candidate only if the profile supports it. Otherwise report inconclusive. Current evidence does not justify a numerical speedup factor or a percentage attributed to hashing versus EOS. A sufficiently long wet spatial experiment still needs phase-event feasibility, temperature/stretch/kinetic domain checks and an adaptive resource plan; wall time must be forecast from actual accepted/discarded evaluation counts and measured per-unit costs, not extrapolated solely from0.32ms or from an assumed hash bottleneck. Preserve original spatial failure and all numerical gates.
