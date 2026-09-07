# Actual depletion0 pressure-floor diagnosis

Read-only diagnosis from the saved failed result and current production code. No EOS, imports of the model, tests, simulations or source edits performed. Only standard-library exact arithmetic was used to evaluate the formula already present in the source. This diagnosis does not turn the failed run into a pass.

## Observed failure

`depletion-result-0.json` records resource_limit / wall_time_limit, 322 evaluations and 120.2988433749997 s. Six ordinary accepted panels survive, with no committed event. The speculative comparisons at levels 1, 2, 3 have pressure metrics 1.6033257416027111, 1.6024446977678064, 1.6021777617894093 Pa. Their event-time differences shrink from 2.794803886733984e-8 to 3.076243474631627e-9 s; amount differences shrink from 5.579376084445943e-9 to 6.141210976166531e-10 mol. Therefore even aside from pressure, the last available amount metric has not yet reached its 1e-10 mol gate. No future pass is inferred.

## Cause: a fixed conservative pressure-error enclosure, not a common-time geometry mismatch

1. `solid_fluid_storage.py:135-136` computes available-volume uncertainty as bulk geometry uncertainty plus representation error plus sum(N_i * declared_v_error_i). Both A and B retain the fixture's declared_v_error=1e-12 m3/mol. A+B is conserved at approximately 2 mol, so this part alone remains approximately 2e-12 m3 after depletion regardless of RK refinement.
2. `solid_fluid_storage.py:141-145` forms the derivative lower bound using the *whole declared envelope's* upper pressure: bmin=N_g R T / p_hi^2, extra_p=error_v/bmin. `test_rigid_storage.py` supplies p_hi=1e6 Pa. The actual pressure is approximately 5.45e4 Pa, but the implementation does not use a local pressure interval to tighten this bound. It then adds the fluid pressure-error bound rather than replacing it.
3. `depletion_integration.py:219-223` copies this storage pressure error into each observation. `comparison:385-386` adds both paths' error bounds to the absolute nominal pressure difference, for both common-time and event-time observations, taking their maximum. This reported metric is therefore not just the difference of nominal pressures.
4. The current-temperature/current-volume observations are rebuilt at tc (`comparison:379`) using each path's current operator. The reacting host computes current point storage and rebinds its reaction storages; no stale reference-volume pressure source was found in this path. q(N) alters stored energy and thereby temperature, but the pressure floor is directly determined by the declared volume uncertainty and the global slope bound.

## Independent arithmetic from declared inputs

After depletion, N_g is approximately 0.001 carrier + (1e-8+1e-6) water = 0.00100101 mol. At 300 K, the formula gives:

    one-path extra_p = (2e-12)*(1e6)^2 / (0.00100101*8.31446261815324*300)
                     = 0.8010066835344705 Pa
    two-path sum     = 1.602013367068941 Pa

This is the observed approximately 1.602 Pa plateau before small temperature, nominal-pressure, bulk-error and fluid-roundoff contributions. Cooling increases this bound. Even at the upper allowed 310 K the same two-path contribution is 1.55033551651833 Pa, already greater than the 1 Pa gate. A+B conservation and water/carrier conservation fix its inventory factor up to tiny represented-roundoff errors, which cannot eliminate a greater-than-0.55 Pa excess. Thus reducing time steps or increasing wall time cannot make the current conservative pressure enclosure pass the existing gate.

The saved result retains aggregate speculative differences, not each rejected speculative state's full pressure/error decomposition. Consequently the exact last-digit split of 1.6021777617894093 into nominal pressure difference and individual errors cannot be reconstructed from this file alone; no such split is claimed. The source formula and mandatory lower floor suffice to identify why refinement cannot pass.

## Next valid action

Keep declared solid-volume errors, original event gates, physical sources and time budget unchanged. Derive and test a tighter *certified propagation of the same uncertainty*, beginning with the dry branch used by these post-event comparisons. For dry ideal gas at fixed represented N and T, P=Q/V and V in [V0-epsilon,V0+epsilon] gives exact interval [Q/(V0+epsilon), Q/(V0-epsilon)], provided the lower volume remains positive and the entire pressure interval stays in the original admissible domain. Compare the returned nominal pressure against this interval with outward arithmetic, retaining existing representation/residual contributions. This is a tighter bound on the same uncertainty, not dropping that uncertainty or changing its declared source.

For scale only, using the saved callback pore volume 4.57375e-5 m3 in that dry formula gives approximately 0.002387146241034049 Pa one-path volume contribution. This illustrative arithmetic is not an executed dry state, not a proposed replacement tolerance and not a proof that the full coupled run will pass. A wet local-bound generalization, if needed, needs a separately proved monotone root enclosure; simply inserting nominal p into bmin is not a certified solution.

The appropriate next implementation must first retain a failing regression for the current global-bound behavior, prove positivity/domain/error containment of the tighter interval, test its uncertainty endpoints and reject invalid intervals, then rerun the identical source-bound experiment. The pressure refinement plateau currently demonstrates conservative error propagation, not erroneous physical chemistry or license to reduce source uncertainty.

## Assessment of root's proposed bootstrap tightening

The proposed refinement is mathematically valid under the same stable-liquid, uniform declared-error and fixed-represented-T/N assumptions already required by the existing global propagation. It can cover both dry and wet states without additional EOS calls:

    Q = N_g*R*T > 0
    epsilon = current available-volume error
    d0 = epsilon*phi^2/Q
    e0 = existing fluid-only pressure error
    I0 = [p_nom-e0-d0, p_nom+e0+d0]
    U = min(phi, p_nom+e0+d0)
    d1 = epsilon*U^2/Q
    final radius = e0+d1

Here phi is the same upper bound used in the original global derivative estimate. First prove/check that I0 lies wholly in the original admissible mechanical pressure interval, using outward/exact arithmetic. Do not use the tightened interval to rescue an I0 that failed that original domain test. Once I0 is certified, both the baseline-volume root (within p_nom +/- e0) and each volume-perturbed root lie at pressures no greater than U. The entire segment connecting these roots stays within the stable domain and below U. For F(P)=N_l*v_l(T,P)+Q/P-V, stable liquid gives -F'(P)= -N_l*dv_l/dP + Q/P^2 >= Q/U^2. The mean-value bound for a volume change at most epsilon then gives root displacement at most d1 from the baseline root. Triangle inequality with e0 gives the stated final radius. It is not permissible to replace U with the nominal pressure alone.

Existence/containment must not be asserted just from a small derivative at one point. It follows here from the pre-existing globally certified root/enclosure plus enough signed margin to the original domain boundaries: a bounded volume perturbation cannot move that root beyond d0 because the global derivative magnitude is bounded below by Q/phi^2. RigidWaterGas evaluates both original bracket endpoints and rejects absent/unstable roots; its documented stable-branch monotonicity is explicit at rigid_water_gas.py:174-179. The bootstrap adds no new liquid compressibility assumption, but it must not claim a proof for arbitrary physically different liquid laws whose errors or stability were never bounded by the declared envelope. The existing qualifications remain conditional numerical/source-envelope qualifications.

Implementation requirements:

- Q must remain strictly positive and finite/representable under existing failure rules; no all-gas-zero special escape. Keep the original positive-available-volume and complete uncertainty-domain checks.
- Derive d0, I0 and U using exact Fraction operands from represented p, declared errors, Q and phi, or explicitly outward rounded upper quantities. Never allow nearest-downward rounding of U before U^2 to invalidate the derivative bound.
- Preserve e0 unchanged, retain all declared solid/bulk/liquid errors and retain the existing rounding contribution in epsilon. Tightening the geometry contribution does not justify shrinking fluid-only error.
- Use a nonnegative outward final radius and retain original pressure-envelope membership checks. Exact epsilon=0 yields d1=0; U<=phi implies d1<=d0 in exact arithmetic. Consider explicit nonrepresentable intermediates and endpoint equality.
- The proof concerns pressure at fixed represented temperature, matching the existing SolidFluidState pressure-error semantics. It does not silently add or remove an inverse-temperature uncertainty contribution.

No code or runtime verification of this proposed change has been performed. Before integration, independent interval-endpoint tests should demonstrate that the same uncertainty is enclosed, including a nonzero liquid-compressibility manufactured analytic function, gas-only case, original-domain rejection and adverse rounding. Neither numerical guards nor the experiment's original gates/budget need to change for this derivation.
