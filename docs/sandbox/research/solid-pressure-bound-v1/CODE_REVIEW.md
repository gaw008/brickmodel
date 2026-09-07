# Independent review: one-bootstrap solid-volume pressure bound

Reviewed the actual ten-line addition to `src/sludge_sandbox/solid_fluid_storage.py` and the complete new `tests/sandbox/test_solid_pressure_bound.py`. Read the full surrounding thermal/energy assembly, original fluid error propagation and rigid wet/dry mechanical closure; checked the preregistration and archived failure diagnosis. Production and tests were read only. No model imports, native EOS, tests or trajectories were run by this reviewer. Review-time hashes and syntax checks are in code-review-files.json.

No reportable implementation defect found.

## Proof and implemented arithmetic

Let Q=Ng*R*T>0, epsilon be the unchanged exact available-volume uncertainty, e0 the unchanged fluid-only pressure error and phi the unchanged envelope upper pressure. The existing d0=epsilon*phi²/Q calculation and outward addition e0+d0 remain before the new code. Crucially, the complete ORIGINAL bracket acceptance check is executed before any tightening. A state rejected by that original global uncertainty interval remains rejected, even if an informal local calculation might fit. No source error or physical domain is reduced.

The accepted globally enclosing interval contains the baseline root and both volume-perturbed roots. The new certified upper endpoint is min(phi, p + original outward global radius), formed from exact Fraction operands; no nearest-downward float conversion occurs before squaring. The preceding domain check and positive original bracket guarantee a strictly positive endpoint. On the connecting root segment, the ideal gas contributes Q/P² >= Q/U² to minus the volume derivative. Stable liquid contributes nonnegative compliance, matching the existing rigid-water/gas closure's explicit stable-branch assumption. Thus epsilon*U²/Q bounds the volume-induced root displacement, and triangle inequality retains e0 unchanged.

The implementation computes that additional radius using exact rational division followed by the existing outward `_directed`, then outward `_sum_upper` with e0. U<=phi implies the exact additional bound cannot increase; monotonic outward rounding preserves this ordering. Zero epsilon retains the original fluid error. The positive-gas guard, positive-pore/uncertainty checks and final complete bracket check remain. The local slope is an analytic lower bound over a certified interval, not a sampled derivative at the nominal state.

The same newly computed `extra_p` flows into the existing liquid internal-energy uncertainty term N_liquid*declared_abs_du_dp*extra_p. This avoids inconsistent pressure and energy bounds. Existing liquid caloric, fluid root, solid caloric, geometry and rounding contributions remain. The proof concerns pressure at fixed represented T/N and retains the existing conditional error-envelope qualification; it does not convert a declared envelope into an independent material certification or include a new inverse-temperature error model.

## Test review and actual XML evidence

The new dry tests independently use rational P=Q/V uncertainty-endpoint roots, including asymmetric shifts. Three cases separate solid molar-volume and bulk-volume uncertainty. The nonzero original fluid closure error is explicitly retained. Their tightness requirement distinguishes the old envelope-wide bound from the valid tighter one. Additional tests cover exact zero volume error, a near-upper-bracket interval with both roots enclosed, preservation of the old global-domain rejection even when exact roots alone would fit, and uncertainty reaching zero pore volume. The test fixture's declared u bound is adjusted only to satisfy its own unchanged p_reference*delta_v invariant; no production material error was changed.

Independently parsed actual XML files: corrected baseline02 has seven testcase nodes, three failures and no errors/skips; candidate has seven testcase nodes, zero failures/errors/skips. These demonstrate the intended dry tightening regression and boundary contracts. They do not execute a wet compressible-liquid analytic fixture or independently verify native EOS response. The wet proof relies on the same stable-liquid branch contract used by the pre-existing global bound; actual wet host/failed-trajectory replay and full installed regression remain necessary evidence before reporting runtime recovery. No future pass is inferred from these tests.

Approved source SHA256: `67e407cdce28a159902f292d53d4076b507a2bb43c6fb2989b8699423f8580e6`.
Approved test SHA256: `a7fcb5a3919d2102a581c0fc4ab2d93e0d90659735b873311db649067751b6ae`.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE the reviewed local enclosure implementation and dry analytic regressions. Runtime recovery, wet verification and full-suite completion require their own actual evidence.
