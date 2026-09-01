# Limitations and high-fidelity upgrade path

## Current validity domain

- Synthetic dry blends containing explicit component partitions/formulas and ordered PSD.
- Half-thickness <= the supplied geometry, fixed stationary spatial kiln map and declared synthetic speed ratio bounds.
- Temperatures inside parameter-pack validity and the solver's 1–3000 K hard state domain.
- Ideal gas, one exposed half-slab face, effective isotropic properties, four balanced gas-generating reaction classes.
- Screening proxies only; no standards, compliance or production-control interpretation.

## Known limitations

1. **Thermodynamics** — `MinimalGibbsBackend` validates the constrained minimization interface on pure-phase cases. Forward oxide liquid is a coverage-limited ideal pseudo closure, not a complete CALPHAD result.
2. **Kinetics** — reaction classes and source windows are plausible, but synthetic constants are not fitted to this sludge/matrix. Organic chemistry cannot resolve every VOC/toxic species.
3. **Transport** — 1D effective diffusion/surface transfer omits cracks, anisotropy, hole channels, stacking contact and full Darcy-flow coupling. Pressure risk is a proxy with unknown normalization.
4. **Sintering/phase** — reduced isotropic SOVS-inspired shrinkage omits anisotropy, pore topology and explicit phase-field evolution.
5. **Mechanics/performance** — thermal-gradient stress, warpage, strength, water absorption, efflorescence and defects are unresolved or closure-dependent proxies.
6. **Boundary** — the bundled tunnel profile is synthetic. Varying speed assumes no feedback from loading/speed to combustion or gas flow.
7. **Inverse** — tiny budget is a reproducible constrained Sobol screening library, not proof of global optimality. Rank stability is limited by two L1 points. The current executable MVP does not add SciPy differential-evolution local expansion; that remains a declared upgrade rather than a hidden stub.
8. **Uncertainty** — policy-distribution quantiles are not empirical confidence/credible intervals. Unknown model discrepancy is separate.
9. **Numerics** — 21/41 convergence covers selected metrics only. Extent projection is logged and bounded; it is not a license to hide large corrections.

## Upgrade sequence

1. Add redistributable NIST-JANAF/NASA pure-species polynomials with checksum/license metadata and wider manufactured equilibrium tests.
2. Add optional Thermochimica/pycalphad/Cantera adapters after securing an open oxide-liquid database whose composition domain covers the design space; retain backend cross-checks.
3. Replace single kinetic policies with source-linked distributed activation energy/multistep ensembles; preserve CHONS projection and unknown emissions.
4. Add coupled Darcy pressure and pore-network/model-form ensemble; validate Fick/Darcy manufactured solutions.
5. Add bounded/scalarized SciPy differential-evolution expansions after the Sobol library, with every proposed point revalidated by the real forward model and `workers=1`.
6. Add geometry-aware 2D/3D local PC refinement for holes/corners/stacking and FEM stress; do not put it inside the 1-OCPU inverse loop.
7. If the owner voluntarily supplies real data, version it separately and calibrate only within batch-linked domains. Use held-out batches and report error; do not overwrite the synthetic pack.
8. Before any physical trial, require a human-approved safe envelope, offline review, instrumented small experiment, stop criteria and rollback. No automatic PLC/robot/kiln connection.

## Rollback

Every run records case/source/parameter hashes and software versions. A parameter/solver change should add an ADR and regression baseline. If conservation, bounds, grid convergence or inverse recovery fails, restore the previous content-addressed pack; do not silently loosen tolerances.
