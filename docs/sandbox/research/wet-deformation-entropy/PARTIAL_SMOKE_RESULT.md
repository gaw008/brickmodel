# Single authorized partial wet smoke — FAILED component gate

The sole subprocess attempt completed in 14.067171125 s with exit 1 (assertion failure, not timeout). Command: `.venv/bin/python /private/tmp/brick-wet-deformation-oracle/run_partial_smoke.py`. No second attempt was made. The original 450 s proposal remains unexecuted.

Actual DeformingSolidHeat / tagged ConservedState integration completed from 0 to 1/64 s on the original 1 s / 10% isotropic C1 motion, retaining liquid 1 mol, gas .01 mol and solid 2 mol. Accepted times were 0, .0078125, .015625 s: 2 accepted steps, 15 operator evaluations, 0 rejected trials. Integration plus setup reached the persisted trajectory stage at 12.459 s. The full trajectory, original per-step five-component/face/reaction ledgers, energy identity, and independent Fraction-based accepted prefix reconstruction are in `partial-smoke-result.json`. All inventory and total-energy prefix gates passed; dissipation and body power integrals were zero throughout. These checks are distinct from component truncation accuracy.

The exact rational manufactured volume fixture was used as separately audited; its uncertainty identity was not substituted into the older broad-uncertainty fixture. No sludge material qualification is implied. The inverse remains 1e-6 J / 1e-6 K; integrator numerical settings and endpoint comparison gates are recorded unchanged. Only the preauthorized short time/resource bounds differ from full-trajectory validation.

At the partial endpoint lambda = .9999275207519531, the independent nested entropy/pressure root gives T = 300.0001103613235 K and p = 304582.59242255014 Pa. Its entropy residual is −3.38342586e-11 J/K and volume residual 4.06575815e-20 m3. This truth calculation shares only the native water provider and reads the prescribed motion for geometry; it does not call tested storage/closure/inverse.

| Comparison | Absolute difference | Original gate | Result |
|---|---:|---:|---|
| Temperature | 3.47747005e-8 K | 2e-5 K | pass |
| Pressure | 3.36077064e-5 Pa | .2 Pa | pass |
| Elastic work | 2.04028778e-10 J | 1e-6 J | pass |
| Interface work | 7.20112695e-11 J | 1e-6 J | pass |
| Pore work | 2.97406436e-6 J | 1e-6 J | **FAIL** |
| Dissipation/body work | 0 J | 1e-6 J | pass |

Pore-work truth is `Nl*M*(u95_final-u95_initial) + (Ng*(Cp_g-Rmix)+Ns*Cp_s)*(T_final-T_initial)` for fixed phase inventories. Constant common energy offsets cancel. Elastic and interface work use their independent potential differences. Actual T is 300.0001103265488 K, p is 304582.59238894243 Pa, and reported inverse temperature bound 4.05367334e-8 K. A small T difference does not certify the stricter component-energy gate.

The instrumentation counted 3406 public `WaterProperties.state_tp` calls over setup, integration, final decode and reference; this is not an internal IAPWS solver-call count. Final entropy solve used 71 such calls and .290113 s. Full native WaterReference, five source asset hashes, numerical limits and all production source hashes are stored. `partial-smoke-manifest.json` binds original script, preregistration, result, status, log and oracle.

This is a successful execution of real wet stepping and an unsuccessful partial component-accuracy validation. It provides a measured cost of approximately .83 s per integration operator evaluation (including small setup overhead), not a full-trajectory performance guarantee. No complete 10% wet trajectory, convergence rate, active phase-transfer process or free-sintering material prediction has been validated. Any next run requires a separate predeclared cost/convergence plan; this result does not authorize one.
