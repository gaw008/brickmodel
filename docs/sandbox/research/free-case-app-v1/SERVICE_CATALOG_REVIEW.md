# Final free application seam and equation catalog review

Verdict: **APPROVE** for the frozen service revision and inspected catalog. No blocking findings. This supersedes the earlier service-only review for the revised trace behavior.

## Inspected SHA-256

| File | SHA-256 |
|---|---|
| run_service.py | a51fba08e8695fe69289647decc2e4177d4ec6c77798c5151e938311bfd991e3 |
| run_provenance.py | 6a31f32b768298308c941e5e89b010d0e92f4213a210b9212e5e42b0b3c467e4 |
| test_selection.py | 942c8af1745d9cd5776f13d55e3187270a7950944f749eca251734114456ace2 |
| ../brick-free-catalog-candidate/free-wet-slab-equations-v1.json | 5f5374f7cb1d84ed94f40fdc57ef4d59bc7c039299223ff0d4e00de688debb5d |

## Service revision

Model-specific trace dispatch preserves the old four quantities for the prescribed model and adds mechanical_stretches, geometry, and free only for the free model. Unknown model IDs are rejected. Mechanical stretches come from the last accepted conserved state; geometry/free diagnostics come from the final snapshot. Trace anchors for the free model use CurrentSolidStorage, FreeSolidSlab, and solve_free_slab_rates rather than the prescribed deformation path. Existing artifact hash binding and optional graph query checks remain. The earlier fixed-filename allowlist, original catalog-byte return, model identity check, and model-selected resume catalog hash checks remain approved.

The revised tests inspect values and result pointers for all three new trace quantities, require free solver anchors and absence of Deforming symbols, and reject an unknown model. Their sealed bundles are deliberate software fixtures rather than executed physical runs. They do not establish successful native run/replay/resume behavior.

## Scientific catalog

The free catalog has a distinct model ID and ordinary-integration scope. Its geometry is reconstructed from accepted normal stretches and one common tangent; it does not import prescribed-motion claims. The reduced common-tangent qualification explicitly excludes pointwise free lateral traction and a general three-dimensional displacement field.

The free-traction equations match the implemented current-composition q*eta_ref denominator and volume-weighted tangent balance. The mechanical-power equation has the correct local constraint sign C_i=2 V0_i R_i tdot, preserves local power even when the global sum is enclosed by zero, and uses external power -pe*Vdot. The recoverable-power identity is explicitly fixed-composition. Composition-dependent stored energy is handled by current total-energy inversion, with no duplicate composition, viscous, latent, or reaction heat source.

Initial prolongation, beta/V0 weights, reference micro-area density, and parent extensive error semantics agree with the applied case builder. Ordinary accepted updates include mechanical variables and their numerical scales. Reconstructed outputs are described as computed values with conditional numerical bounds, not measurements or material qualification.

Water sources, the ideal-mixture bridge, and manufactured solid/carrier/transport/reaction inputs remain distinguished. Source locators are declarations with the existing availability and applicability limits; this review does not independently certify the cited literature or claim that a connected graph establishes material accuracy.

Every declared implementation path/symbol was resolved by read-only AST inspection against current repository files. Every equation case parameter pointer resolved against the applied sample and had metadata. No unresolved anchors or missing parameter metadata were found. All seven result roots correspond to the service quantities. The catalog declares its acyclic graph as stage-to-update dependency documentation rather than an assertion that physical feedback is acyclic.

## Evidence limits

No EOS, test rerun, installation, or repository modification was performed. The parent-reported 15 passing dry tests were not rerun by this reviewer. Static parsing/anchor inspection is not a successful actual graph build, installed-package run, replay, or cancelled-prefix resume; those remain integration evidence to collect before broader delivery claims.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: **APPROVE** for these exact scoped snapshots.
