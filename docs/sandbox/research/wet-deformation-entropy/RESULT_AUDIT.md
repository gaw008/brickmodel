# Independent result audit — wet entropy points and FAILED partial host smoke

Reviewed 2026-09-07. **Verdict: preserve FAILED partial component validation.** The saved point experiment completed, and actual host integration completed only its authorized 1/64-second prefix. Neither establishes a successful full original one-second, 10% isotropic trajectory. No EOS, benchmark, trajectory, installation or test rerun was performed. No original source/evidence was modified; RESULT_AUDIT.md is the sole write.

## Evidence and method

Read the two result JSON files, runners, retained logs and subprocess status JSON, entropy reference, preregistration, reports, manifests, and current imported fixture definitions. `git diff -- '*.py'` was empty. Standard-library AST, SHA-256, JSON, float arithmetic and exact Fraction checks were used. Static lint executables were unavailable in the prior same-session environment check. This is a bounded internal audit, not external scientific certification or an independent EOS solve.

All **60 recorded file hash bindings** passed: seven partial manifest entries, eleven verification.json entries, 37 production modules recorded in the partial result and five native water assets under `/Users/wanggaoying/Desktop/brickmodel-github/data/sandbox/water/`. WaterReference, asset identities and numerical limits agree across the point and partial results. Hash agreement proves current bundle consistency, not independent attestation of when or how many times execution occurred.

## Actual process outcomes and provenance limits

- `wet-probe-run-status.json`: child exited 0, finished in 2.0704304999962915 s; result says completed. Its retained log is empty, consistent with a successful quiet script.
- `partial-smoke-run-status.json`: child exited 1, finished in 14.06717112500337 s. `partial-smoke.log` and result traceback agree on the final component assertion at partial_smoke.py:68. Result says failed/AssertionError after saving the comparison stage, so this is a numerical gate failure, not a timeout.
- Both runners use an argument-list `subprocess.run(..., timeout=30)` in a separate supervisory process. This enforces a timeout independently of Python signal handling inside the EOS child; subprocess.run kills and waits for the direct child on expiry. It is not a precise upper bound on process creation/termination overhead or a process-tree supervisor. No child descendants are launched by the reviewed probe scripts. No actual timeout behavior was exercised here.
- The wrapper scripts do not propagate child return codes or timeout as their own exit status; absent another exception, the wrapper itself exits 0 even for this child exit 1. Consumers must read the saved child status and result status. Reusable automation should propagate a nonzero status.
- The two experiment kinds have distinct filenames, but neither has a unique per-attempt directory, run UUID, invocation timestamp or start/end source snapshot. Files are overwritten in place; logs open with `w`. Therefore the current bundle is internally linked by hashes and matching traceback, but the directory alone cannot independently prove the narrative “sole attempt/no second attempt.” No external terminal transcript beyond these retained child logs/status files was available in this review. A failed launch or killed write on reuse could leave older JSON. Preserve the current bundle and use unique attempt directories/atomic final records for future authorized work.

## Exact accepted-prefix reconstruction

The saved integrator status is completed with times `[0, 0.0078125, 0.015625]`, three states, two step ledgers, 15 operator evaluations and zero rejected trials. Recorded counters were checked for structural consistency; they were not remeasured. The accepted states preserve `[1, .01, 2]` mol and the same tagged energy-model identity. Every retained face-energy, face-species and reaction-species entry is zero. Body and dissipation components are zero on both steps.

Reconstructing the saved binary64 ledger values as exact Fractions reproduces every saved component prefix and energy residual. Inventory residuals are exactly zero. Energy residuals are 2.6561810910485928e-11 and 6.058047032769798e-11 J, both below 1e-6 J. This certifies bookkeeping against the saved accepted ledgers, not quadrature accuracy against independent physics.

Final component sums in J are elastic 3.5138107473613076e-9, interface -2.1735785300904804e-7, pore 0.009266504888184559, body 0 and dissipation 0. Reference pore work saved in the comparison is 0.009269478952543691 J. Their exact recomputed float difference is **2.974064359131945e-6 J > 1e-6 J**. This remains a validation blocker.

Saved T/P differences recompute exactly: 3.4774700452544494e-8 K < 2e-5 K and 3.360770642757416e-5 Pa < .2 Pa. Elastic/interface errors recompute to 2.0402877791441433e-10 and 7.201126948082145e-11 J. Actual mechanical volume residual -6.292031782748064e-16 m3 and pressure residual 2.3401807993650436e-6 Pa meet their separate 1e-13 m3/1e-5 Pa closure tolerances. The reported inverse temperature bound 4.053673344718757e-8 K is not a component quadrature error bound.

Original inverse settings are 1e-6 J/1e-6 K, maximum 100 iterations. The partial integration retains the formal dry-host comparison's relative tolerance 1e-6 and energy absolute tolerance 1e-6 J; the generic test policy's 1e-9 J default is explicitly overridden in that formal host test too. The partial's short endpoint, steps and resource caps were separately preregistered. No gate relaxation is inferred from using the named generic policy helper.

## Equations, units and independent coverage

Static reference inspection confirms `Vp=Vbulk-Ns*vs`, pressure residual `Nl*M/rho(T,p)+Ng*R*T/p-Vp` in m3, and entropy residual `Nl*M*(s-s0)+(Ng*(Cp_g-R)+Ns*Cp_s)*ln(T/T0)+Ng*R*ln(Vg/Vg0)` in J/K. Native liquid entropy in J/(kg K) is multiplied by water molar mass exactly once. The manufactured ideal carrier gas uses its declared mixture R; this does not replace native liquid R. Constant phase-inventory entropy/formation offsets cancel. This constrained adiabatic fixed-inventory limit excludes active transfer, dissipation, external heat and temperature-dependent recoverable potentials.

The pore reference formula is `Nl*M*(u95_final-u95_initial)+(Ng*(Cp_g-R)+Ns*Cp_s)*(Tf-T0)` in J. The script fixes Nl=1, Ng=.01, Ns=2, Cp_g=30 and Cp_s=5; hence its shortened expression is equivalent. Constant common energy shifts cancel. Elastic `.5*1000*V0*(3*ln(lambda))**2` and interface `.0015*(lambda**2-1)` differences match the current manufactured potential fixture and recompute exactly from saved lambda.

**Offline recomputation limit:** individual native `wi/wf.native_internal_energy_j_kg` and native entropy samples are not saved. The pore reference and full entropy residual can therefore be checked for correct formula/units and consistency with the saved derived values, but their EOS operands cannot be independently recomputed from this bundle without a forbidden new EOS evaluation. Future evidence should retain those native operands. Test fixture/helper files imported by the scripts are also absent from the original production-source hash map; current fixture definitions were inspected, but their exact at-run revision is not independently bound. These limitations do not erase the observed failure and must not be represented as complete independent numerical reproduction.

The entropy module calls only the native water provider for wet properties, not candidate storage, closure or inverse. The endpoint geometry comes from prescribed motion. The point experiment's optional storage forward/inverse uses the entropy endpoint T to initialize its energy target: its excellent roundtrip is consequently not evolved-trajectory validation. The half-xtol differences 2.502815732441377e-10 K and 4.898756742477417e-7 Pa recompute and meet the 2e-7 K/.002 Pa refinement gates; this is a local refinement observation, not an EOS/root interval enclosure.

At t=1/64, the original smooth motion yields lambda=0.9999275207519531, matching `1-.1*(3*t*t-2*t*t*t)`. Stretch loss is only 7.2479248046875e-5, versus .1 at the full endpoint. The independent full lambda=.9 entropy point exists, but no accepted host states bridge the prefix to that endpoint. Only the final accepted partial prefix has an independent entropy/component comparison; both prefixes have bookkeeping checks. No all-prefix independent component truth, convergence rate or successful full 10% host trajectory was established.

The 3406 counter is a saved public WaterProperties.state_tp count covering setup, integration, decode and reference, not an internal IAPWS solve count. The final reference's 71 calls/.2901128749945201 s and integration's 12.281541582997306 s are measurements in saved JSON; no general performance guarantee follows. The 450-second plan remains a proposal in the inspected evidence, not a completed run.

## Frozen file bindings at this review

Paths below are relative to `/private/tmp/brick-wet-deformation-oracle/`; hashes are SHA-256. This report is additive and is not retroactively added to the original manifests.

- `entropy_reference.py`: `d61e40dc96253394e534123daf578a45eb288da82b8853fd017dd44fcd03c323`
- `wet_probe.py`: `32df2f90e398c3dd50acd76d6f88144cd6a6fc0ead25195f32511bab5033735f`
- `run_wet_probe.py`: `7a19735d7a912dccfb38eb83be4bb13eb49ebf0a6c8c17abbe9bce45987e26c6`
- `wet-probe-result.json`: `09eddaed810d8ba495efe21847b639dfad5581c0dbeaa99948b8fd10ac5fe591`
- `wet-probe-run-status.json`: `70cb307c45e16c0d94b303e8c1d5439c0ab0d8511ee6ab4dec4530b230a465f8`
- `wet-probe.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `partial_smoke.py`: `175e5bb7a0d8ce4f549d70ce8791879e240cb4f7cf1ccd8201ddda17855291ca`
- `run_partial_smoke.py`: `1c654a5d9a69026774dc038d2bcf491a80e7ab03ce6f140a3d1f5e3f609e298e`
- `PARTIAL_SMOKE_PREREGISTRATION.md`: `4503b538e2cc61dbaff33a290dd0e5c20e599a19dc1166faa32ab178d45b2571`
- `partial-smoke-result.json`: `28579430fdca5d0ced746f01ab61773c9bcd1de296fcc30186cc8b6a1ef96d6a`
- `partial-smoke-run-status.json`: `908796c28c33e58819a6927bb92fb17fa90340d099c193e86d02d406f9d7dd53`
- `partial-smoke.log`: `e07e4981a2944e5656dcf6ca478ad44f20f8690e83635c9cf79e4a75d21c0f09`
- `partial-smoke-manifest.json`: `bad346dacf23956088f8500e31e7761a1e4c01ce2ec03fe93311ccc8f4606477`
- `verification.json`: `2a35934fe443c21ee0930d6ef91e47fb620f45481e881f7e745023077afc9adf`
- `PARTIAL_SMOKE_RESULT.md`: `95f07281820537966076e3d0bb64c07052752fb135675ddf9329dd1f3d0d4d10`
