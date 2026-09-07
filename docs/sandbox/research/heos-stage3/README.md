# Isolated HEOS water candidate: stage 3

Research code only; production remains source-verified Python IAPWS 1.5.5. No mixture/storage/phase-transfer host accepts this class, and no speedup is claimed. This is progress toward tractable wet simulation, not a complete sludge model.

## Implemented

Native-SI immutable result snapshots with a distinct implementation digest; original public mass/reference and exact fitted R convention; source checks on all 28 installed .py/.so files, actual loaded extension path, full fluid JSON, version/revision, adapter source and effective runtime configuration. Descriptor includes the runtime manifest and Python water source assets. It records local installation provenance, not independent verification of how a wheel was built. Original source-verified Python is used at construction for reference and ideal h/s anchor comparison; it is not called as the runtime EOS checker.

Flash and derivative-check AbstractState objects are separate and per-instance. Transactions hold a reentrant lock and reject changed configuration/fluid or native warnings. Table 3 caloric, mechanical stability, Gibbs and derivative identities retain the old gates. Full transaction/concurrency/monkeypatch/source/ref-state adversarial coverage remains incomplete; the lock does not serialize unrelated code mutating CoolProp global state. No saturation cache or production backend selection is provided yet.

Saturation QT values seed an EOS coexistence calculation in two log-densities. The equations are pL=pV and gL=gV; dp/dlogrho=rho*R*T*D and dg/dlogrho=R*T*D define the analytic 2x2 Newton Jacobian. At most eight evaluations and explicit branch/step checks; no clipping. Final code accepts a seed already satisfying both EOS targets without forcing a gratuitous update. EOS coexistence acceptance checks 1e-4 Pa and 1e-6 J/kg, followed by all original phase-state gates. The converged/accepted vapor EOS pressure supplies common pressure; liquid pressure agreement and BOTH h-u-p/rho identities are independently checked. h/u/s are obtained from native DmassT evaluations, never algebraically reset to force conservation.

## Actual history

- attempt01: failed, exit1,1.186s. QT saturation vapor h-u-p/rho=2.7409987524e-6 J/kg exceeds original1e-6 gate. Failed state raw operands were not saved, so the pressure/density amplification explanation is an inference from residuals, not independently proven root cause.
- attempt02: same initial kernel, process-start COOLPROP_ENABLE_SUPERANCILLARIES=false; failed,exit1,1.057s, h-u-p/rho=.0018257398 J/kg. Disabling the shortcut did not fix it. Configuration adjustment affected only that isolated child at startup; no global runtime setter or production change.
- attempt03: EOS coexistence path, default config, four states passed,exit0,1.088s. Both 300K saturation branches and liquid TP at304469.31354/567435.65536Pa. Six domain rejections passed. The DmassT-re-evaluated seed ALREADY met coexistence gates; forcing one Newton step increased pressure/Gibbs residuals while remaining below limits. This does not demonstrate Newton residual improvement or full-domain convergence.
- attempt04: immutable adapter fields, source/config/entropy-anchor hardening; same4states+6domain+3identity-write rejections passed,exit0,1.126s. Largest native h-u-p/rho9.8181e-8J/kg<1e-6; saturation Gibbs3.0268e-8J/kg<.001. Saved raw fields independently recomputed these checks. Source differences and summary04.json are retained.
- fault-attempt01: five deliberate faults rejected,exit0,1.097s: u corruption, nonfinite derivative, native warning, runtime configuration mutation, and adapter manifest mismatch. Test-only global configuration mutation is restored in finally in its dedicated child process; the adapter never invokes a setter.

- attempt05 (final): removed forced Newton step and added post-transaction fluid identity check. Combined4physics/6domain/3immutability/5fault checks passed,exit0,1.1699s, all declared inputs unchanged. This case accepts the EOS-evaluated seed at iteration0, so zero Newton updates; it does not validate a difficult iterative-convergence path. Native h-u-p/rho maximum remains9.8181e-8J/kg. Both result05.json and fault-results05.json plus actual process exit are required; the physics JSON is written before the fault checks.

Every process used the reviewed external supervisor, separate attempt directory, actual return code, unchanged-input bindings and preserved diagnostics. No run was relabelled from failed to passed, and no original numerical limit was increased. Plan02/03 document bounded follow-ups; those two plan files were saved but not included in those run input_path lists (base PLAN.md was). This limits their cryptographic before-run binding, not the recorded kernel/child hashes or actual return code.

## Remaining admission work

Official wider check points, broader admitted-domain liquid/vapor and pressure extremes, initial guesses that actually require Newton convergence, finite-difference response validation, source/ref-state mutations, thread behavior and cache contracts. Descriptor must propagate through caloric/chemical bridges, provider signatures and closed-storage inverse before any wet host can accept HEOS. Then rerun original short wet gates and measure complete adapter/inverse costs before scaling. Source coverage for real sludge, whole-cycle physics, three mechanism validation groups, UI and generation search remain separate mandatory Goal gaps.

## Sources consulted

- https://coolprop.org/coolprop/LowLevelAPI.html — actual AbstractState input/phase/check-object semantics.
- https://coolprop.org/coolprop/Configuration.html — effective config JSON and process-start COOLPROP_ variables; ENABLE_SUPERANCILLARIES controls pure-fluid VLE shortcut.
- Original IAPWS95 Table3 and source-gated water assets in data/sandbox/water; full design in ../water-backend-feasibility/ADAPTER_DESIGN.md.

Frozen local CoolProp8.0.0 installation and MIT license came from the earlier feasibility probe. Full fluid-runtime.json is the actual API string in this stage, unlike the earlier pretty-serialized file. Canonical digest includes the enclosing array; do not compare it with a first-object-only digest as if they were identical byte representations.
