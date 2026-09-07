# Independent reacting prescribed-deformation Python review

Status: numerical/control review passes; one new public-API typing issue remains pending at the initial reviewed bytes. No native EOS or full suite run by this reviewer. Production/tests were not edited. Ruff, mypy, pylint and black unavailable on PATH.

## Initial reviewed SHA-256

- reacting_skeleton_energy.py: `8a2c25764d8e47a232f5298b27f54204ad630afdefd63cc346144e6907a93ba7`
- deforming_solid_storage.py: `c51278bae2c1f4043c804cf198c1180d81f64b147f149c5c86080004ada6a3fd`
- deforming_solid_heat.py: `ba538d706b6843e48ca27239d71bca84c9eea13a353f37bda8be94309a902823`
- integration.py: `98be85230f031c9245c8b3a9a4f9015a9a9200bb8c135b31eb968683ebef9c28`
- test_reacting_skeleton_energy.py: `550b75be9243e5addd0fd01ecc35f1d7947fe21ed582d591c35e5c38c9f30752`
- test_reacting_deforming_solid_heat.py: `fd02fc0f504fee094e7b3b762dc092cc8fd46f1a32642a16f5b30cdc317a2d43`

## Findings

[HIGH] New production provider public API lacks type annotations
File: src/sludge_sandbox/reacting_skeleton_energy.py:105
Issue: evaluate and public properties have no annotated return/argument contracts; new composition mappings and weight tuple use unparameterized collection types. This is a new production API rather than a one-off research converter; the active Python-review criteria classify missing public-function annotations as HIGH.
Fix: annotate evaluate's numeric/inventory parameters and ReactingSkeletonEnergyState return, the public properties, tuple[tuple[str,float],...] weights and Mapping[str,float] derivatives. No rewrite of inherited modules requested.

## Numerical and integration assessment

The new provider is explicitly manufactured and temperature independent. A positive offset and nonnegative complete weights/inventories make q strictly positive; all-zero solid inventory remains an explicit domain exit. It wraps the immutable reference model without relaxing that model's fixed-inventory guard. Scalar and tensor energies/powers/stresses and Rayleigh potential are scaled using exact represented Fraction q and outward reconstruction of reference value-plus/minus-bound intervals. Composition derivatives are w_i times the reference recoverable/interface energies, reported as immutable mappings with individual bounds. Overflow/underflow fail explicitly rather than clipping.

Point storage uses current amounts for both occupied solid volume and q-dependent mechanical storage. Because q has no temperature dependence, subtracting current composition mechanical energy before the thermal inverse remains valid; existing thermal error propagation is retained. Current host reaction config is reconstructed with exactly the same current storage tuple used by the thermal host; the old reference bulk concentration cannot accidentally survive prescribed deformation. Binding tags distinguish the new regime, while unchanged fixed-mode providers preserve their existing default checks and schema.

Only fixed-composition deformation derivatives enter external work. Composition-energy change is already in total storage and does not become an invented reaction heat source. Pressure work is -p*dV_bulk/dt, not a pore-rate term that would double-count reaction-driven solid-volume change. The base host still supplies species rates with no added reaction enthalpy source. Positive viscous dissipation is retained. These statements apply to the declared manufactured prescribed mechanics, not free-sintering or thermodynamic qualification of empirical reaction rates.

Independent no-EOS probes (exit 0): accepted old schema, new schema and shared body-only subset; rejected all three representative mixtures of old/new exclusive labels. Simultaneously varied composition and both stretches and compared a central finite difference of each energy with fixed-N deformation power plus sum(dE/dN_i * Ndot_i): absolute errors 3.798535271049008e-12 W (elastic), 3.511652367548315e-13 W (interface), below the declared 1e-10 W probe check. The probe did not call a thermal inverse or native water EOS.

Read the actual new provider and host tests. They cover explicit identity/domain rejection, immutable derivatives/bounds, exact interface scaling, composition finite differences, q=1 compatibility, nonrepresentability, current reaction geometry with nontrivial concentration order, reused inverse identity, changed occupied volume and chemistry/total-storage temperature balance. The dry transient oracle uses independent analytic extent and a scalar temperature ODE. Root-owned running test results and broader regressions remain separate evidence; this reviewer does not assert their outcome.

## Final reread and finding closure

Final verdict: APPROVE. The public-API typing finding is CLOSED. Reread actual provider source and independently AST-checked every function return and all non-self positional/keyword-only argument annotations. The new derivative mappings and weights tuple are parameterized; ReferenceSlab, inventory and state returns are explicit. No new numerical change accompanied this typing fix.

Final hashes are exactly the six values in the initial SHA list above. Timing clarification: the first source read preceded the worker annotation fix, but the later hash collection had already observed the annotated file. Thus the first report's missing-annotation finding describes that earlier read, not the subsequently listed `8a2c2576...` bytes. The final reread resolves this asynchronous review ordering; all listed final bytes are now explicitly approved.

Checked the source motion implementation: deformation_program.py uses blend=q*q*(3-2*q), derivative=6*q*(1-q)/(tb-ta). The test fixture interval is 0..1, so the corrected independent scalar oracle's lambda=1-0.1*t*t*(3-2*t) and bulk derivative=-1.4e-5*6*t*(1-t) match the existing prescribed motion. This is a correction to the erroneous linear-time oracle, not a new production mechanism or relaxed comparison gate. The oracle still uses an explicit independent equation rather than invoking the production storage or motion callback.

Inspected actual XML: host-tests-04.xml has five tests, one failure, zero errors/skips; host-tests-05.xml has five tests, zero failures/errors/skips, 1.434 s. Prior failure and host-test-linear-oracle.py are present. The successful corrected result is not substituted for the preserved failed evidence. Broader root-owned targeted/installed/full-suite and trajectory validation remain separately pending at this review.
