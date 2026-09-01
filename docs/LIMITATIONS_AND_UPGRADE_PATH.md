# Limitations and high-fidelity upgrade path

## Current validity domain

- Synthetic dry blends containing explicit component partitions/formulas and ordered PSD.
- Half-thickness <= the supplied geometry, fixed stationary spatial kiln map and declared synthetic speed ratio bounds.
- Temperatures inside parameter-pack validity and the solver's 1–3000 K hard state domain.
- Ideal gas, one exposed half-slab face, effective isotropic properties, four balanced gas-generating reaction classes and finite configured O2 transfer.
- Screening proxies only; no standards, compliance or production-control interpretation.

## Known limitations

1. **Thermodynamics** — `MinimalGibbsBackend` validates the constrained minimization interface on pure-phase cases and is invoked by Forward, but the bundled source has no adequate multicomponent oxide-liquid phases. Thermo is therefore `not_evaluated_*`; the composition-sensitive liquid value is only an unresolved screening proxy and cannot hard-pass.
2. **Kinetics/atmosphere** — reaction classes and source windows are plausible, but synthetic constants are not fitted to this sludge/matrix. Organic oxidation is stoichiometrically capped by initial plus boundary-supplied O2; CO/VOC/NOx chemistry and real kiln recirculation remain unresolved.
3. **Transport** — Fick flux now uses current pore concentration and deforming geometry, but 1D effective diffusion/surface transfer still omits cracks, anisotropy, hole channels, stacking contact and full Darcy-flow coupling. Pressure risk is a proxy with unknown normalization.
4. **Sintering/phase** — reduced isotropic SOVS-inspired shrinkage omits anisotropy, pore topology and explicit phase-field evolution.
5. **Mechanics/performance** — thermal-gradient stress, warpage, strength, water absorption, efflorescence and defects are unresolved or closure-dependent proxies.
6. **Boundary** — the bundled tunnel profile is synthetic. Varying speed assumes no feedback from loading/speed to combustion or gas flow.
7. **Inverse** — tiny budget is a reproducible constrained Sobol screening library, not proof of global optimality. Two L1 points produce `insufficient_points`, and ranges are only observed candidate envelopes. The current executable MVP does not add SciPy differential-evolution local expansion; that remains a declared upgrade rather than a hidden stub.
8. **Uncertainty** — policy-distribution quantiles are not empirical confidence/credible intervals. Required sample failures are fail-safe infeasible by default; a nonzero threshold requires an explicit scientific basis. Unknown model discrepancy is separate.
9. **Energy** — `reduced_effective_enthalpy_ode_relative_residual` checks the implemented fixed-effective-capacity ODE only. Complete variable-mass energy, escaped-gas sensible enthalpy and diffusive gas enthalpy are not evaluated and never hard-pass.
10. **Numerics** — 21/41 convergence covers selected metrics only. Extent projection is logged and bounded; it is not a license to hide large corrections.

All 12 inverse coordinates have direct model couplings and one-at-a-time metamorphic tests. This proves only non-phantom implementation sensitivity, not that the synthetic bounds or closures are physically calibrated.

## Upgrade sequence

1. Add redistributable NIST-JANAF/NASA pure-species polynomials with checksum/license metadata and wider manufactured equilibrium tests.
2. Add optional Thermochimica/pycalphad/Cantera adapters after securing an open oxide-liquid database whose composition domain covers the design space; retain backend cross-checks.
3. Replace single kinetic policies with source-linked distributed activation energy/multistep ensembles; preserve CHONS projection and unknown emissions.
4. Add coupled Darcy pressure and pore-network/model-form ensemble; retain current-pore Fick manufactured/deforming-cell conservation tests and add Darcy manufactured solutions.
5. Replace the reduced enthalpy ODE with an independently closed conservative inventory covering variable condensed/gas heat capacity, escaped-gas sensible enthalpy and diffusive enthalpy before enabling any full energy hard constraint.
6. Add bounded/scalarized SciPy differential-evolution expansions after the Sobol library, with every proposed point revalidated by the real forward model and `workers=1`.
7. Add geometry-aware 2D/3D local PC refinement for holes/corners/stacking and FEM stress; do not put it inside the 1-OCPU inverse loop.
8. If the owner voluntarily supplies real data, version it separately and calibrate only within batch-linked domains. Use held-out batches and report error; do not overwrite the synthetic pack.
9. Before any physical trial, require a human-approved safe envelope, offline review, instrumented small experiment, stop criteria and rollback. No automatic PLC/robot/kiln connection.

## Rollback

Every run records case/source/parameter hashes, software versions and every non-manifest artifact's SHA-256/size. Output writes reject a nonempty directory unless `--overwrite`; explicit overwrite preserves the old directory as a rollback sibling before atomic rename. If conservation, bounds, grid convergence or inverse recovery fails, restore the previous content-addressed pack; do not silently loosen tolerances.
