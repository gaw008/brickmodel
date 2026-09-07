# Independent fixed-inventory entropy reference review

Scope: isolated reference solver, plan and dry tests. No wet EOS was evaluated and no repository source/tests were changed. Actual native-water/host comparisons remain pending a separately authorized bounded run.

## Physical and independence assessment

For closed, fixed liquid/gas/solid inventories at common T and p, with constant intrinsic solid volume, zero viscosity/dissipation and temperature-independent recoverable skeleton/interface stores, subtracting their reversible rates from total power leaves dUthermal=−p dVp. The Gibbs relation gives dUthermal=T dS−p dVp, hence dS=0. The oracle is valid for this constrained limit, not active evaporation, changing Ns, heat exchange or viscous motion.

Liquid entropy uses native mass-specific s in J/(kg K), multiplied exactly once by Nl times its own native-water molar mass. Ideal gas contributes Ng*(Cp−R)*ln(T/T0)+Ng*R*ln(Vg/Vg0); constant incompressible solid contributes Ns*Cp_s*ln(T/T0), with no subtraction of R. Fixed-N entropy/formation offsets cancel. The registered ideal-gas R does not overwrite the native liquid EOS constant. The first planned gas is the explicitly manufactured carrier, not unreported water vapor. No NIST entropy alignment or temperature-dependent surface free/internal-energy equivalence is assumed.

The pressure equation is Nl*M/rho(T,p)+Ng*R*T/p−Vp=0. Stable liquid compressibility and ideal-gas compressibility give a decreasing pressure residual; entropy at fixed Vp increases with T for the stable fixed-composition closed capacity. Actual sign brackets and admitted liquid states remain required. Nested brentq imports no candidate closure, storage or temperature inverse. Only the source-gated native liquid TP provider can be shared. Separate endpoint brackets, xtol/rtol, iteration and forward residual gates are numerical solver contracts; they are not interval enclosures of EOS/model/root error. The planned endpoint tighter-tolerance comparison remains unexecuted here.

## Independent execution and finding

Actual original dry suite: **8 passed in 0.26 s**, `independent-dry-review.xml`. ForbiddenWater prevents any dry water access. Independently reproduced one missing validation branch:

[MEDIUM] The dry analytic `_pressure` branch returned its recomputed volume residual without checking `volume_residual_tolerance_m3`, unlike the liquid branch. With the same fixture and tolerance 1e-100 m³, `solve(0.00013502023808)` successfully returned residual 1.3552527156068805e-20 m³. This does not fail the planned 1e-14 m³ fixture gate, but violates the configurable residual contract. Requested the same explicit residual rejection in the dry branch and a RED regression; no formula or threshold change is needed.

## Independent analytic limit probes

Saved and executed `independent_limits_probe.py`, using no tested storage/closure and no wet EOS calls:

- Pure ideal gas with Ns=Nl=0: three volumes at factors .8,1,1.2 agree with T=300*(V0/V)^(R/(Cp−R)) within 2e-9 K.
- A clearly manufactured incompressible liquid replaces native `state_tp` only inside the probe process: v=18e-6 m³/mol, Cp=75 J/(mol K), s=75/M*ln(T/300), density=M/v. With Nl=1, Ng=.01 and Ns=2, three volume factors agree with T=300*(Vg0/Vg)^[Ng R/(Nl Cp_l+Ng Cv_g+Ns Cp_s)] within 2e-9 K and analytic p within 1e-5 Pa. All 400 liquid callbacks were this analytic mock; the original method was restored in finally. Loading source assets to satisfy the exact WaterProperties type check was not a real liquid EOS computation or a material validation.

These probes independently check gas Cv, liquid mass/molar conversion, solid Cp and gas-available volume. They do not substitute for the planned real-water endpoint test.

Initial bindings: source `63b975d30bd0ba653accbe69da4c52c1293e891a43be162364da1cca5981e3e9`; test `bd4a003c953e07203bd1ade2cd1d44c661eb5ccabc914014f0cd3d3475265aa4`; plan `3a8c1345a11bbf38f22e4b9f4729def161183517054200c73e831400f75534be`.

## Review Summary

| Severity | Unresolved count | Status |
|----------|------------------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | repair requested |
| LOW | 0 | pass |

Verdict: PENDING residual-gate repair; no physical derivation blocker found within the declared constrained limit.

## Final repair and binding

The author retained an actual dry-residual RED, then added the same explicit residual-tolerance rejection before the dry analytic return. No physical formula or planned tolerance changed. Independent final suite: **9 passed in 0.26 s**, `independent-final-review.xml`, including the strict-gate regression. Only dry/analytic work was run; native wet EOS remains unexecuted by this review.

- Final source SHA256: `d61e40dc96253394e534123daf578a45eb288da82b8853fd017dd44fcd03c323`.
- Final test SHA256: `992a419963eb8560421f6a75d5085f3d98d0d3dacedeea4223ebb80886fa9ee3`.

## Final Review Summary

| Severity | Unresolved count | Status |
|----------|------------------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | repair verified |
| LOW | 0 | pass |

Verdict: APPROVE — independent constrained fixed-inventory entropy reference is ready for the separately authorized bounded actual-water point experiment. This approval does not claim real-water results, EOS-error certification or agreement with an integrated wet host.
