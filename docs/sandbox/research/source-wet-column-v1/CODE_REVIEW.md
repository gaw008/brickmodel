# Independent shared wet exchange and source column code review

Read mass_wet_transport.py extraction and complete new test module. Original phase and face arithmetic remains in order; AB-specific extent and energy account remain in original caller. Exact Fraction transfer coefficient is a rate-law input, not EOS inventory; phase result preserves it until represented output. Dry no-nucleation and source errors remain explicit. face_exchange itself checks equal left/right species masses and R.

Actual independent phase arithmetic/entropy, wrong vapor refusal before callback, and two face gas-state convention negatives passed alongside author tests; see initial-tests.log. These use manufactured liquid fixtures, not native EOS or material validation.

[HIGH] Public face helper accepted mismatched/fake caloric providers.
File: src/sludge_sandbox/mass_wet_transport.py evaluate_wet_face.
Actual probe swaps legitimate O2/N2 phase providers; wrong species enthalpies are accepted and energy changes 135.81982271568032 to 135.3347122045993 W. A SimpleNamespace fake curve executes twice and returns -496402462.65627235 W. See probe_face.py/face-probe.log. Existing host has upstream source binding, but new public entry point checks keys only.
Fix requested from owner: actual supported IdealGasPhase/leaf binding, per-key species/molar mass/R/basis checks before enthalpy callback. Caller still must bind common full left/right storage caloric identity because helper receives one map only. Root informed, worker repair pending. Preserve old complete observation/identity/trajectory golden.

SourceWetColumn pending author freeze. No final approval/hash yet.

## Post-fix shared face review

Worker repaired the demonstrated public entry issue. All adapters and supported caloric leaves are checked before enthalpy evaluation; selected Shomate/continuous/water adapters preserve their existing constructor constraints. Per-key species, mol basis/standard energy-reference labels, mass and gas constant now match both GasState objects. Full caloric energy origins remain explicitly a caller responsibility. Actual reviewer probes for swapped real curves and fake callbacks now reject. Current helper/test hashes match FREEZE-face-guard.json. Original full observation/identity/trajectory golden passes unchanged.

## Source column review

SourceWetColumn requires N actual SourceWetStorage objects, N policies/modes/widths, N-1 internal faces, two closed boundaries and explicit manufactured transport. It checks every storage binding, same source dry caloric and full gas caloric digest, thermal/chemical compatibility, chemical identity and available-fluid-volume upper bound within each slab cell. This does not infer physical solid volume. Rates use existing actual inverse, disabled chemistry, shared phase and shared face kernels. Each internal face is evaluated once, left i-1/right i; boundaries return explicit zero flux. Actual point and equilibrium source IDs propagate.

Integrator uses exact rational h, midpoint predictor, then full-step rates applied to prior accepted state. Face quantities are reused with opposite signs in neighboring cells; phase water subtracts liquid/adds vapor, no latent source is added to U. Each quantity projects to binary64 once and signed residual is recorded. Predictor arithmetic and face energy decomposition are counted in arithmetic budgets but kept separate from accepted inventory conservation. Neither budget is claimed to bound time discretization, inverse propagation or source fit. Full new state evaluation completes before append; failures/cancellation retain accepted prefix only.

Actual final reviewer invocation: 41 passed in 13.00s (10 independent checks, 22 shared exchange tests, nine source-column tests). Independent cases include Fraction rate/entropy reconstruction, vapor mismatch before chemical callback, both gas-state convention mismatches, actual public face attack rejection, four-cell distinct-width neighbor thermal-resistance reconstruction, cancellation during second step retaining exactly one committed step, tiny roundoff budget preserving initial state only, fake storage and source drift refusing before inverse. Source-column supplied tests additionally check N=1/2/3/4 topology, exact cell/global signed roundoff and complete-prefix failure/resource behavior. See final-tests.log and test_column_independent.py.

All four reviewed Python files parse. Ruff/mypy not available in current runtime; no static-lint-clean claim. No complete suite, native EOS or material-validation execution by reviewer. Source material/transport qualification remains false and physical fit remains unknown. No unresolved critical/high functional defect identified after face repair. REVIEWED_HASHES.json binds exact reviewed bytes pending author final freeze confirmation.

## Final freeze and native example read-through

Author confirmed source column and test final freeze. Re-read current four-file hashes and confirmed exact equality with tested snapshot; FINAL_FREEZE.json also includes reviewed example script. Native example delegates only construction to previously reviewed actual source-storage example, uses actual HEOS chemical provider and three cells, two distinct internal faces, explicit manufactured geometry/transport. One-step duration 1/1024 is exact binary64. Independent Fraction ledger reconstruction contains 20 assertions per accepted step. The script records actual status, reason and accepted count, and audit returns zero on an empty prefix; zero assertions must not be reported as a successful trajectory. No native script execution by reviewer. Parent owns external time supervision and actual execution report. Final scoped approval applies to frozen bytes, not material qualification.
