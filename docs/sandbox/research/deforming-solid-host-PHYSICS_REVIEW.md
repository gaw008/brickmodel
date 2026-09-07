# Preliminary independent physics review: deforming solid host

Current status: **CONDITIONAL PHYSICS APPROVAL for the actual attempt06 dry manufactured oracle**. The predeclared fine-grid component gate is now met. The initial PENDING assessment below is preserved as historical evidence; final implementation approval and test-entry/initializer review remain separate. Read-only review of the current candidate/test and actual attempt05 output. The author is still iterating; this is not final artifact approval or a claim that a future run passed. No EOS or parallel integration was run by this reviewer, and no candidate source/test was changed.

## Physical equations checked

For fixed intrinsic solid volume Vs, no closed pores, isothermal-per-cell ideal gas and calorically constant solids in the closed dry manufactured oracle:

`C = Ns*Cs + Ng*(Cp_g-R)` and `Vp=Vbulk-Vs`.

After subtracting reversible skeleton/interface energy from total energy, eta=0 implies `C*dT=-p*dVp` with `p=Ng*R*T/Vp`. Integrating gives `T=T0*(Vp0/Vp)^(Ng*R/C)`. The test's Ns=2, Cs=5 J/mol/K, Ng=.01, gas Cp=30 J/mol/K, Vs=4e-5 m3 and initial Vbulk=1.4e-4 m3 produce its stated exponent. Formation-energy offsets are constant and do not enter this derivative. With isotropic lambda, `Vp=1.4e-4*lambda^3-4e-5`, not a gas volume that scales simply as lambda^3.

The log-strain deviatoric term vanishes under isotropic deformation. Therefore `Eelastic=.5*K*V0*(3 ln lambda)^2`; `Einterface=.0015*lambda^2` and its accumulated change subtracts the initial .0015 J. The independent closed thermal work is `C*(T-T0)`. These reference expressions are consistent with the declared energy split and are independent of the host's power calculation.

The host's five components are elastic energy rate, interface energy rate, nonnegative viscous dissipation, `-p*Vbulk_dot` and preexisting body power. Under fixed Ns and constant intrinsic grain volume, Vp_dot=Vbulk_dot, so this pore-work term is justified. It must not be reused after a changing solid inventory/closed-pore/finite-grain-compressibility extension without new derivatives. Fixed solid reaction rejection and per-stage inventory binding enforce the current scope. Enthalpy face exchanges are reused without another pQ. The wrapper does not add dissipation a second time after already including it in total work.

Mechanical validity is that of explicitly actuated quasi-static specimen cells with a complete constitutive skeleton/interface resistance. It is not arbitrary external atmospheric pressure acting on a brick, force-balanced free sintering, or a stress/momentum solution. The model retains manufactured transport in the moving reference frame and does not qualify real material coefficients. Current test evidence is dry; nonzero-liquid host transport, heat boundary and phase-transfer integration are not established by the point-storage wet test.

## Actual attempt05: unresolved numerical acceptance

Read attempt05.log/XML: **1 failed, 5 passed in 5.00 s**. The failing test retains its registered fine-level pore work gate of 1e-6 J.

| Maximum step | Accepted steps | max T error K | max elastic prefix J | max interface prefix J | max pore prefix J |
|---|---:|---:|---:|---:|---:|
| 1/32 | 35 | 2.4283448027517807e-4 | 1.1327713818464619e-6 | 6.142884145397733e-8 | 2.4799335332588157e-3 |
| 1/64 | 64 | 7.246134720162445e-5 | 4.5015125505528525e-7 | 1.7395019531241986e-8 | 7.398943418692738e-4 |
| 1/128 | 128 | 1.8114890167453268e-5 | 1.1253733233924229e-7 | 4.348754882783391e-9 | 1.849691513893248e-4 |

[HIGH — validation blocker] Fine pore-work accuracy is about 185 times the registered 1e-6 J gate. The fine temperature error passes its looser 2e-5 K condition, but that cannot replace the component condition. The last two pore errors decrease by approximately four under halved maximum step; this is useful evidence of truncation convergence, not success at the requested accuracy. A rough second-order extrapolation suggests a further factor 16 in step reduction might be needed, but it is not a guarantee and inverse/roundoff floors must be considered. Keep the failing evidence, physical inputs and gates unchanged; select any further bounded numerical experiment before running it.

The coarsest level has 35 accepted steps rather than 32: these are adaptive maximum-step refinements, not three proved uniform grids. Record actual time grids/step counts. Existing logs already expose the count; documentation must not claim uniform stepping.

Low-cost additional checks proposed on already computed trajectories: assert eta=0 dissipation and closed body components are zero on every ledger, and independently reconcile total U change with the three nonzero component sums. These require no added integrations. Net-energy adaptivity alone does not bound component truncation, particularly mutually cancelling terms. The existing component ledger controls decomposition roundoff; it is a different guarantee.

## Architecture observations

The host subtracts mechanical energies through explicit tagged point targets, uses original thermal inverses exactly once per cell, reconstructs current storage/transport with current V/A/d and preserves source identities. The complete reference shape is checked, including the equal-volume/wrong-area counterexample. The shared face is used once in opposite cell signs. The actual two-cell check is instantaneous; it does not certify a two-cell integrated energy/transport trajectory.

The private thermal assembly accepts original inverse objects and validates inventories, current geometry and source labels, without another EOS inverse. Its use by the new host is downstream of the point-storage full template binding. This review does not treat that private function as a standalone untrusted-data admission API.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | pending numerical gate |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: PENDING. No incorrect physical sign or energy double-counting was identified in the inspected narrow model, but the actual predeclared component accuracy test failed. Final source/test hashes and approval must wait for a frozen version and successful bounded validation.


## Attempt06 independent final physics supplement

Read actual attempt06.xml: one selected test, zero failures/errors/skips, 72.390 s. Outer status records exit0 and72.617779 s. Parsed captured metrics from the XML and compared them exactly to attempt06-metrics.json: identical. No 72-second integration was repeated by this reviewer. The recorded runner explicitly sets BRICK_FINE_SCAN=1 and uses a150-second subprocess timeout; the per-integrate90-second resource limit was registered before this run. Numerical policies, physical inputs and original acceptance thresholds were unchanged.

| Cap | Accepted | Reject | min=max dt | max T error K | elastic prefix J | interface prefix J | pore prefix J |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1/512 |512|0|.001953125|1.1321531019348186e-6|7.033573869164034e-9|2.7179718019429075e-10|1.1560369269858484e-5|
| 1/1024 |1024|0|.0009765625|2.830424250532815e-7|1.7583933501971738e-9|6.794929506212521e-11|2.8900834365686023e-6|
| 1/2048 |2048|0|.00048828125|7.078398311932688e-8|4.3959832995987824e-10|1.6987323765531304e-11|7.225205731486994e-7|

Independent arithmetic recomputation (not host calls) at lambda=.9 gives C=10.216855373818468 J/K, Vp=6.206000000000001e-5 m3, T=301.1669769570929 K, Eelastic=.006993528103600326 J, Delta Einterface=-.00028499999999999993 J and Wpore=11.922834795197057 J. Pore-error ratios are4.0000122915 and4.0000015833, consistent with the observed halved-grid truncation behavior. This evidence does not assert universal second order or certify arbitrary component cancellation.

The actual test now asserts every body and dissipation ledger entry is zero for this reversible closed limit. At every accepted prefix it accumulates the three nonzero component integrals with Fraction, adds the signed decomposition residual and checks the resulting extensive total-energy change within1e-6 J. Each nonzero component independently passes its1e-6 J reference gate at the finest grid, and T passes2e-5 K. These close the numerical blocker identified in attempt05 for this bounded dry case. Earlier failed runs remain valid history.

**Conditional physical conclusion:** the specified prescribed-motion, fixed-Ns, dry solid/ideal-gas model passes this independent analytic reference and the registered component-energy gates in the captured fine run. This does not establish wet transient coupling, free sintering, real sludge parameters, skeleton force balance or a full runtime error certificate. The initializer's tag/uncertainty admission is concurrently under separate code review.

**Outstanding test-entry note sent to author/root:** at the inspected snapshot, ordinary test execution without BRICK_FINE_SCAN=1 still selects the previously failed coarse caps. Before implementation/application approval, its default test entry or explicit slow-test policy must be reconciled with the verified acceptance run. Do not report a normally green whole candidate suite from this single environment-selected passing case. This is a test delivery issue, not failure of attempt06's actual physical accuracy evidence.

### Evidence binding for this supplement

- `attempt06.xml` SHA256 `5a9ea967770a55ac8b1e00bec3d7912d902a01b648a78c4d2d18350e31774cc8`.
- `attempt06-metrics.json` SHA256 `4edb95ef52695b60f4695d2dc0450013095924b782761ae00752bf9bbac381c5`.
- `attempt06-status.json` SHA256 `91543e931f87b29a456b320acdec531a07a000fd11b2514a74a54105200b18fb`.
- `run_attempt06.py` SHA256 `23556776b18aeb4a4c421b24a146818ae5c249209c0956dc74f30503a9a9a959`.
- `tests/test_deforming_solid_heat.py` SHA256 `e5fc17208e95d0a884de551d40f427594e55e5cbf86710fa1b0dea33f4f81e0e`.

## Formal test entry closure

Independently read the applied `tests/sandbox/test_deforming_solid_heat.py`: its oracle caps are unconditionally `(1/512,1/1024,1/2048)` with maximum_wall_seconds=90, and no BRICK_FINE_SCAN branch remains. This closes the test-entry note above without weakening the original accuracy gates. Test SHA256 `c48167d6aa293872dc41d3502438b602c8797541bf462e5d7b85f02a7d782947`. The earlier environment-selected attempt06 remains the actual run evidence; no fresh full run is claimed by this supplement. Conditional physical approval remains limited to that fixed-inventory, eta=0, manufactured dry specimen; wet entropy-oracle work is separate and not yet executed.
